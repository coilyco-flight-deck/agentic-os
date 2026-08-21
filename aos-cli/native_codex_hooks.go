package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const codexHookTrustTimeout = 10 * time.Second

type codexRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type codexRPCMessage struct {
	ID     *int            `json:"id"`
	Method string          `json:"method"`
	Result json.RawMessage `json:"result"`
	Error  *codexRPCError  `json:"error"`
}

type codexHookMetadata struct {
	Key         string `json:"key"`
	EventName   string `json:"eventName"`
	HandlerType string `json:"handlerType"`
	Matcher     string `json:"matcher"`
	Command     string `json:"command"`
	SourcePath  string `json:"sourcePath"`
	Source      string `json:"source"`
	Enabled     bool   `json:"enabled"`
	IsManaged   bool   `json:"isManaged"`
	CurrentHash string `json:"currentHash"`
	TrustStatus string `json:"trustStatus"`
}

type codexHooksListEntry struct {
	CWD      string              `json:"cwd"`
	Hooks    []codexHookMetadata `json:"hooks"`
	Warnings []string            `json:"warnings"`
	Errors   []json.RawMessage   `json:"errors"`
}

type codexHooksListResponse struct {
	Data []codexHooksListEntry `json:"data"`
}

// trustNativeCodexAttributionHook persists only the converged attribution hook.
// Missing Codex stays a no-op for installations that use another harness.
func trustNativeCodexAttributionHook(
	parent context.Context,
	cwd string,
	home string,
	codexHome string,
) (int, error) {
	binary, err := exec.LookPath("codex")
	if errors.Is(err, exec.ErrNotFound) {
		return 0, nil
	}
	if err != nil {
		return 0, fmt.Errorf("resolve Codex executable: %w", err)
	}

	ctx, cancel := context.WithTimeout(parent, codexHookTrustTimeout)
	defer cancel()
	command := exec.CommandContext(ctx, binary, "app-server", "--listen", "stdio://")
	command.Dir = cwd
	command.Env = replaceEnvironment(os.Environ(), "CODEX_HOME", codexHome)
	stdin, err := command.StdinPipe()
	if err != nil {
		return 0, fmt.Errorf("open Codex app-server input: %w", err)
	}
	stdout, err := command.StdoutPipe()
	if err != nil {
		return 0, fmt.Errorf("open Codex app-server output: %w", err)
	}
	var stderr bytes.Buffer
	command.Stderr = &stderr
	if err := command.Start(); err != nil {
		return 0, fmt.Errorf("start Codex app-server: %w", err)
	}

	trusted, protocolErr := trustCodexAttributionHookRPC(
		json.NewEncoder(stdin),
		json.NewDecoder(stdout),
		cwd,
		home,
		codexHome,
	)
	closeErr := stdin.Close()
	waitErr := command.Wait()
	if protocolErr != nil {
		return 0, protocolErr
	}
	if closeErr != nil {
		return 0, fmt.Errorf("close Codex app-server input: %w", closeErr)
	}
	if waitErr != nil {
		detail := strings.TrimSpace(stderr.String())
		if detail != "" {
			return 0, fmt.Errorf("Codex app-server failed: %w: %s", waitErr, detail)
		}
		return 0, fmt.Errorf("Codex app-server failed: %w", waitErr)
	}
	return trusted, nil
}

func trustCodexAttributionHookRPC(
	encoder *json.Encoder,
	decoder *json.Decoder,
	cwd string,
	home string,
	codexHome string,
) (int, error) {
	if err := encoder.Encode(map[string]any{
		"method": "initialize",
		"id":     1,
		"params": map[string]any{
			"clientInfo": map[string]string{
				"name":    "agentic_os",
				"title":   "Agentic OS",
				"version": version,
			},
		},
	}); err != nil {
		return 0, fmt.Errorf("initialize Codex app-server: %w", err)
	}
	if _, err := readCodexRPCResponse(decoder, 1); err != nil {
		return 0, fmt.Errorf("initialize Codex app-server: %w", err)
	}
	if err := encoder.Encode(map[string]any{
		"method": "initialized",
		"params": map[string]any{},
	}); err != nil {
		return 0, fmt.Errorf("acknowledge Codex app-server initialization: %w", err)
	}
	if err := encoder.Encode(map[string]any{
		"method": "hooks/list",
		"id":     2,
		"params": map[string]any{
			"cwds": []string{cwd},
		},
	}); err != nil {
		return 0, fmt.Errorf("list Codex hooks: %w", err)
	}
	raw, err := readCodexRPCResponse(decoder, 2)
	if err != nil {
		return 0, fmt.Errorf("list Codex hooks: %w", err)
	}
	var response codexHooksListResponse
	if err := json.Unmarshal(raw, &response); err != nil {
		return 0, fmt.Errorf("decode Codex hooks: %w", err)
	}

	updates := map[string]map[string]string{}
	for _, entry := range response.Data {
		if !samePath(entry.CWD, cwd) {
			continue
		}
		for _, hook := range entry.Hooks {
			if !nativeCodexAttributionHook(hook, home, codexHome) {
				continue
			}
			switch hook.TrustStatus {
			case "trusted", "managed":
				continue
			case "untrusted", "modified":
			default:
				return 0, fmt.Errorf(
					"Codex attribution hook %q has unknown trust status %q",
					hook.Key,
					hook.TrustStatus,
				)
			}
			if strings.TrimSpace(hook.Key) == "" ||
				strings.TrimSpace(hook.CurrentHash) == "" {
				return 0, fmt.Errorf("Codex attribution hook is missing its trust key or current hash")
			}
			updates[hook.Key] = map[string]string{
				"trusted_hash": hook.CurrentHash,
			}
		}
	}
	if len(updates) == 0 {
		return 0, nil
	}

	if err := encoder.Encode(map[string]any{
		"method": "config/batchWrite",
		"id":     3,
		"params": map[string]any{
			"edits": []map[string]any{{
				"keyPath":       "hooks.state",
				"value":         updates,
				"mergeStrategy": "upsert",
			}},
			"reloadUserConfig": true,
		},
	}); err != nil {
		return 0, fmt.Errorf("trust Codex attribution hook: %w", err)
	}
	if _, err := readCodexRPCResponse(decoder, 3); err != nil {
		return 0, fmt.Errorf("trust Codex attribution hook: %w", err)
	}
	return len(updates), nil
}

func readCodexRPCResponse(
	decoder *json.Decoder,
	requestID int,
) (json.RawMessage, error) {
	for {
		var message codexRPCMessage
		if err := decoder.Decode(&message); err != nil {
			if errors.Is(err, io.EOF) {
				return nil, fmt.Errorf(
					"Codex app-server closed before response %d",
					requestID,
				)
			}
			return nil, err
		}
		if message.ID == nil || *message.ID != requestID {
			continue
		}
		if message.Error != nil {
			return nil, fmt.Errorf(
				"RPC error %d: %s",
				message.Error.Code,
				message.Error.Message,
			)
		}
		return message.Result, nil
	}
}

func nativeCodexAttributionHook(hook codexHookMetadata, home, codexHome string) bool {
	if !hook.Enabled ||
		hook.IsManaged ||
		hook.Source != "user" ||
		hook.EventName != "preToolUse" ||
		hook.HandlerType != "command" ||
		hook.Matcher != "Bash" ||
		!samePath(hook.SourcePath, filepath.Join(codexHome, "hooks.json")) {
		return false
	}
	command := strings.ReplaceAll(strings.TrimSpace(hook.Command), `\`, "/")
	candidates := map[string]bool{
		`"$HOME/.local/share/agent-git-attribution/hook-codex"`: true,
	}
	for _, path := range nativeCodexAttributionPaths(home) {
		normalized := strings.ReplaceAll(path, `\`, "/")
		candidates[normalized+" hook codex"] = true
	}
	return candidates[command] || candidates[strings.Trim(command, `"`)]
}

func nativeCodexAttributionPaths(home string) []string {
	paths := make([]string, 0, 6)
	seen := map[string]bool{}
	for _, name := range []string{
		"agent_git_attribution.py",
		"hook-codex",
		"hook-codex.cmd",
	} {
		path := filepath.Join(home, ".local", "share", "agent-git-attribution", name)
		for _, candidate := range []string{path, nativeCodexResolvedPath(path)} {
			if candidate == "" || seen[candidate] {
				continue
			}
			seen[candidate] = true
			paths = append(paths, candidate)
		}
	}
	return paths
}

func nativeCodexResolvedPath(path string) string {
	resolved, err := filepath.EvalSymlinks(path)
	if err != nil {
		return ""
	}
	return resolved
}
