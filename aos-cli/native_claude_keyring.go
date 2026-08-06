// Claude Code namespaces its macOS Keychain credential by a digest of
// CLAUDE_CONFIG_DIR, so a session-scoped config directory never finds the host
// login. See docs/native-claude-credentials.md.

package main

import (
	"context"
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"strings"
)

const claudeCredentialService = "Claude Code-credentials"

var (
	errClaudeKeyringNotFound    = errors.New("Claude Code keyring credential not found")
	errClaudeKeyringUnsupported = errors.New("Claude Code keyring is unsupported")
)

// nativeClaudeKeychainService mirrors Claude Code's own naming: the default
// directory keeps the bare service, every other one takes a digest suffix.
func nativeClaudeKeychainService(home, configDir string) string {
	configDir = strings.TrimSpace(configDir)
	if configDir == "" || configDir == filepath.Join(home, ".claude") {
		return claudeCredentialService
	}
	digest := sha256.Sum256([]byte(configDir))
	return fmt.Sprintf("%s-%x", claudeCredentialService, digest[:4])
}

// nativeClaudeSessionConfigDir is the exact CLAUDE_CONFIG_DIR spelling the
// launch chain exports, and the digest is taken over it byte for byte.
func nativeClaudeSessionConfigDir(sessionHome string) string {
	return filepath.Join(sessionHome, ".claude")
}

// nativeClaudeKeychainAccount matches the account Claude Code records, which is
// the operating-system user name.
func nativeClaudeKeychainAccount() string {
	if current, err := user.Current(); err == nil &&
		strings.TrimSpace(current.Username) != "" {
		return current.Username
	}
	return strings.TrimSpace(os.Getenv("USER"))
}

// claudeKeyringPorts isolates the platform keyring so the session lifecycle is
// testable without touching a real Keychain.
type claudeKeyringPorts struct {
	Read   func(ctx context.Context, service, account string) ([]byte, error)
	Write  func(ctx context.Context, service, account string, secret []byte) error
	Delete func(ctx context.Context, service, account string) error
}

func defaultClaudeKeyringPorts() claudeKeyringPorts {
	return claudeKeyringPorts{
		Read:   readClaudeKeyring,
		Write:  writeClaudeKeyring,
		Delete: deleteClaudeKeyring,
	}
}

// lendNativeClaudeCredential copies the host login onto the session service and
// reports it, so the lease can hand the refreshed token back later.
func lendNativeClaudeCredential(
	ctx context.Context,
	ports claudeKeyringPorts,
	home string,
	sessionHome string,
) (string, error) {
	account := nativeClaudeKeychainAccount()
	if account == "" {
		return "", errors.New("resolve Claude Code keychain account")
	}
	hostService := nativeClaudeKeychainService(home, filepath.Join(home, ".claude"))
	sessionService := nativeClaudeKeychainService(
		home,
		nativeClaudeSessionConfigDir(sessionHome),
	)
	if sessionService == hostService {
		return "", nil
	}
	secret, err := ports.Read(ctx, hostService, account)
	if err != nil {
		return "", err
	}
	if len(secret) == 0 {
		return "", errClaudeKeyringNotFound
	}
	if err := ports.Write(ctx, sessionService, account, secret); err != nil {
		return "", err
	}
	return sessionService, nil
}

// returnNativeClaudeCredential moves a finished session's token back to the host
// service and clears the session item, so a rotated token survives reaping.
func returnNativeClaudeCredential(
	ctx context.Context,
	ports claudeKeyringPorts,
	home string,
	sessionService string,
) error {
	sessionService = strings.TrimSpace(sessionService)
	if sessionService == "" {
		return nil
	}
	account := nativeClaudeKeychainAccount()
	if account == "" {
		return errors.New("resolve Claude Code keychain account")
	}
	hostService := nativeClaudeKeychainService(home, filepath.Join(home, ".claude"))
	if sessionService == hostService {
		return nil
	}
	secret, readErr := ports.Read(ctx, sessionService, account)
	if readErr != nil && !errors.Is(readErr, errClaudeKeyringNotFound) {
		return readErr
	}
	if readErr == nil && len(secret) > 0 {
		if err := ports.Write(ctx, hostService, account, secret); err != nil {
			return err
		}
	}
	if err := ports.Delete(ctx, sessionService, account); err != nil &&
		!errors.Is(err, errClaudeKeyringNotFound) {
		return err
	}
	return nil
}
