package main

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

type fakeClaudeKeyring struct {
	items   map[string][]byte
	reads   []string
	writes  []string
	deletes []string
}

func newFakeClaudeKeyring() *fakeClaudeKeyring {
	return &fakeClaudeKeyring{items: map[string][]byte{}}
}

func (fake *fakeClaudeKeyring) ports() claudeKeyringPorts {
	return claudeKeyringPorts{
		Read: func(_ context.Context, service, _ string) ([]byte, error) {
			fake.reads = append(fake.reads, service)
			secret, ok := fake.items[service]
			if !ok {
				return nil, errClaudeKeyringNotFound
			}
			return secret, nil
		},
		Write: func(_ context.Context, service, _ string, secret []byte) error {
			fake.writes = append(fake.writes, service)
			fake.items[service] = append([]byte(nil), secret...)
			return nil
		},
		Delete: func(_ context.Context, service, _ string) error {
			fake.deletes = append(fake.deletes, service)
			if _, ok := fake.items[service]; !ok {
				return errClaudeKeyringNotFound
			}
			delete(fake.items, service)
			return nil
		},
	}
}

// The suffix is Claude Code's own, so a golden digest guards against silently
// drifting away from the service name the harness actually reads.
func TestNativeClaudeKeychainServiceMatchesHarnessNaming(t *testing.T) {
	home := "/home/example"
	if got, want := nativeClaudeKeychainService(
		home,
		filepath.Join(home, ".claude"),
	), claudeCredentialService; got != want {
		t.Fatalf("default config dir service = %q, want %q", got, want)
	}
	if got, want := nativeClaudeKeychainService(
		home,
		"/tmp/example-session/home/.claude",
	), claudeCredentialService+"-0a5e8662"; got != want {
		t.Fatalf("session config dir service = %q, want %q", got, want)
	}
	if got, want := nativeClaudeKeychainService(home, ""), claudeCredentialService; got != want {
		t.Fatalf("empty config dir service = %q, want %q", got, want)
	}
}

func TestLendNativeClaudeCredentialCopiesHostLogin(t *testing.T) {
	fake := newFakeClaudeKeyring()
	fake.items[claudeCredentialService] = []byte("host-token")
	home := "/home/example"
	sessionHome := "/tmp/example-session/home"

	service, err := lendNativeClaudeCredential(
		context.Background(), fake.ports(), home, sessionHome,
	)
	if err != nil {
		t.Fatal(err)
	}
	want := nativeClaudeKeychainService(home, nativeClaudeSessionConfigDir(sessionHome))
	if service != want {
		t.Fatalf("session service = %q, want %q", service, want)
	}
	if !bytes.Equal(fake.items[want], []byte("host-token")) {
		t.Fatalf("session item = %q, want the host token", fake.items[want])
	}
	if !bytes.Equal(fake.items[claudeCredentialService], []byte("host-token")) {
		t.Fatal("host item must be left intact")
	}
}

func TestLendNativeClaudeCredentialReportsMissingHostLogin(t *testing.T) {
	fake := newFakeClaudeKeyring()
	service, err := lendNativeClaudeCredential(
		context.Background(), fake.ports(), "/home/example", "/tmp/example-session/home",
	)
	if !errors.Is(err, errClaudeKeyringNotFound) {
		t.Fatalf("error = %v, want %v", err, errClaudeKeyringNotFound)
	}
	if service != "" {
		t.Fatalf("service = %q, want empty", service)
	}
	if len(fake.writes) != 0 {
		t.Fatalf("writes = %v, want none", fake.writes)
	}
}

// A session home that resolves to the host config dir must never copy onto
// itself, which would delete the host login during harvest.
func TestLendNativeClaudeCredentialSkipsHostConfigDir(t *testing.T) {
	fake := newFakeClaudeKeyring()
	fake.items[claudeCredentialService] = []byte("host-token")
	home := "/home/example"

	service, err := lendNativeClaudeCredential(context.Background(), fake.ports(), home, home)
	if err != nil {
		t.Fatal(err)
	}
	if service != "" {
		t.Fatalf("service = %q, want empty", service)
	}
	if len(fake.reads) != 0 || len(fake.writes) != 0 {
		t.Fatalf("reads = %v, writes = %v, want none", fake.reads, fake.writes)
	}
}

func TestReturnNativeClaudeCredentialWritesBackAndClearsSession(t *testing.T) {
	fake := newFakeClaudeKeyring()
	fake.items[claudeCredentialService] = []byte("stale-token")
	home := "/home/example"
	session := nativeClaudeKeychainService(home, "/tmp/example-session/home/.claude")
	fake.items[session] = []byte("refreshed-token")

	if err := returnNativeClaudeCredential(
		context.Background(), fake.ports(), home, session,
	); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(fake.items[claudeCredentialService], []byte("refreshed-token")) {
		t.Fatalf("host item = %q, want the refreshed token", fake.items[claudeCredentialService])
	}
	if _, ok := fake.items[session]; ok {
		t.Fatal("session item must be deleted so no orphan accumulates")
	}
}

// An unclean exit can leave the lease recorded with no session item behind, and
// the harvest still has to clear the record rather than fail forever.
func TestReturnNativeClaudeCredentialToleratesMissingSessionItem(t *testing.T) {
	fake := newFakeClaudeKeyring()
	fake.items[claudeCredentialService] = []byte("host-token")
	home := "/home/example"
	session := nativeClaudeKeychainService(home, "/tmp/example-session/home/.claude")

	if err := returnNativeClaudeCredential(
		context.Background(), fake.ports(), home, session,
	); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(fake.items[claudeCredentialService], []byte("host-token")) {
		t.Fatal("host item must be left intact")
	}
	if len(fake.writes) != 0 {
		t.Fatalf("writes = %v, want none", fake.writes)
	}
}

func TestReturnNativeClaudeCredentialIgnoresEmptyService(t *testing.T) {
	fake := newFakeClaudeKeyring()
	if err := returnNativeClaudeCredential(
		context.Background(), fake.ports(), "/home/example", "  ",
	); err != nil {
		t.Fatal(err)
	}
	if len(fake.reads)+len(fake.writes)+len(fake.deletes) != 0 {
		t.Fatal("an empty service must not touch the keyring")
	}
}

func TestHarvestNativeClaudeLeaseClearsRecord(t *testing.T) {
	fake := newFakeClaudeKeyring()
	home := "/home/example"
	session := nativeClaudeKeychainService(home, "/tmp/example-session/home/.claude")
	fake.items[session] = []byte("refreshed-token")
	runtime := nativeRuntime{Home: home, Stderr: os.Stderr, ClaudeKeyring: fake.ports()}
	lease := nativeLease{ClaudeKeychain: session}

	if !harvestNativeClaudeLease(runtime, &lease) {
		t.Fatal("harvest reported no change, want the lease cleared")
	}
	if lease.ClaudeKeychain != "" {
		t.Fatalf("lease keychain = %q, want empty", lease.ClaudeKeychain)
	}
	if !bytes.Equal(fake.items[claudeCredentialService], []byte("refreshed-token")) {
		t.Fatal("host item must receive the refreshed token")
	}
	if harvestNativeClaudeLease(runtime, &lease) {
		t.Fatal("a cleared lease must not be harvested twice")
	}
}
