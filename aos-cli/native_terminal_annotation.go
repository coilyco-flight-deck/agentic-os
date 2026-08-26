package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"unicode"
	"unicode/utf8"
)

const (
	nativeOverlayFormat           = "agent-compose.overlay.v1"
	nativeTerminalTitleMaxRunes   = 120
	nativeTerminalTitleBegin      = "\x1b]2;"
	nativeTerminalTitleTerminator = "\a"
)

type nativeOverlayIdentity struct {
	Format     string `json:"format"`
	Annotation string `json:"annotation"`
}

// projectNativeCodexTerminalTitle mirrors the canonical annotation into an
// interactive title for an assigned native launch in an existing window.
func projectNativeCodexTerminalTitle(ctx context.Context, command []string) error {
	role, agentCompose, ok := nativeAssignedComposeRole(command, "codex")
	if !ok || !nativeTerminalTitleSupported(os.Stdout, os.Getenv) {
		return nil
	}
	annotation, err := loadNativeTerminalAnnotation(ctx, agentCompose, role, "codex")
	if err != nil {
		return err
	}
	title, err := nativeTerminalTitle(annotation, os.Getenv(nativeSessionEnv))
	if err != nil {
		return err
	}
	return writeNativeTerminalTitle(os.Stdout, title)
}

func nativeAssignedComposeRole(command []string, harness string) (string, string, bool) {
	if len(command) < 4 || filepath.Base(command[0]) != "agent-compose" || command[1] != "launch" ||
		command[3] != harness || !safeRoleSlug(command[2]) {
		return "", "", false
	}
	return command[2], command[0], true
}

func loadNativeTerminalAnnotation(
	ctx context.Context,
	agentCompose string,
	role string,
	harness string,
) (string, error) {
	command := exec.CommandContext(
		ctx,
		agentCompose,
		"overlay",
		"--role", role,
		"--seat", harness,
		"--expression", "acting",
		"--json",
	)
	raw, err := command.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return "", fmt.Errorf("load Agent Compose terminal annotation: %s", strings.TrimSpace(string(exitErr.Stderr)))
		}
		return "", fmt.Errorf("load Agent Compose terminal annotation: %w", err)
	}
	var overlay nativeOverlayIdentity
	if err := json.Unmarshal(raw, &overlay); err != nil {
		return "", fmt.Errorf("decode Agent Compose terminal annotation: %w", err)
	}
	if overlay.Format != nativeOverlayFormat {
		return "", fmt.Errorf("Agent Compose terminal annotation has unsupported format %q", overlay.Format)
	}
	return validateNativeTerminalTitle(overlay.Annotation)
}

func nativeTerminalTitleSupported(stdout *os.File, getenv func(string) string) bool {
	if stdout == nil {
		return false
	}
	info, err := stdout.Stat()
	if err != nil || info.Mode()&os.ModeCharDevice == 0 {
		return false
	}
	for _, marker := range []string{"KITTY_WINDOW_ID", "ALACRITTY_WINDOW_ID"} {
		if strings.TrimSpace(getenv(marker)) != "" {
			return true
		}
	}
	terminal := strings.ToLower(strings.TrimSpace(getenv("TERM")))
	return terminal != "" && terminal != "dumb" && terminal != "unknown"
}

func validateNativeTerminalTitle(value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("Agent Compose terminal annotation is empty")
	}
	if utf8.RuneCountInString(value) > nativeTerminalTitleMaxRunes {
		return "", fmt.Errorf("Agent Compose terminal annotation exceeds %d characters", nativeTerminalTitleMaxRunes)
	}
	for _, r := range value {
		if unicode.IsControl(r) {
			return "", fmt.Errorf("Agent Compose terminal annotation contains a control character")
		}
	}
	return value, nil
}

func nativeTerminalTitle(annotation, sessionID string) (string, error) {
	annotation, err := validateNativeTerminalTitle(annotation)
	if err != nil {
		return "", err
	}
	sessionID = strings.TrimSpace(sessionID)
	if sessionID == "" {
		return annotation, nil
	}
	return validateNativeTerminalTitle(annotation + " // " + sessionID)
}

func writeNativeTerminalTitle(writer io.Writer, annotation string) error {
	annotation, err := validateNativeTerminalTitle(annotation)
	if err != nil {
		return err
	}
	_, err = fmt.Fprint(writer, nativeTerminalTitleBegin+annotation+nativeTerminalTitleTerminator)
	return err
}
