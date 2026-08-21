package main

import (
	"bytes"
	"context"
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
)

func TestTrustCodexAttributionHookRPCWritesShadowHookKey(t *testing.T) {
	t.Parallel()
	home := t.TempDir()
	codexHome := filepath.Join(t.TempDir(), ".codex")
	cwd := t.TempDir()
	source := filepath.Join(codexHome, "hooks.json")
	shadowKey := source + ":pre_tool_use:0:0"
	input := strings.Join([]string{
		`{"method":"remoteControl/status/changed","params":{"status":"disabled"}}`,
		`{"id":1,"result":{"userAgent":"test"}}`,
		`{"id":2,"result":{"data":[{"cwd":` + jsonString(cwd) + `,"hooks":[` +
			codexHookJSON(
				"other",
				"untrusted",
				"/tmp/unrelated",
				source,
			) + `,` +
			codexHookJSON(
				shadowKey,
				"modified",
				filepath.Join(home, ".local", "share", "agent-git-attribution", "agent_git_attribution.py")+" hook codex",
				source,
			) + `],"warnings":[],"errors":[]}]}}`,
		`{"method":"config/updated","params":{}}`,
		`{"id":3,"result":{"status":"ok","version":"v1","filePath":"/tmp/config.toml","overriddenMetadata":null}}`,
	}, "\n")
	var output bytes.Buffer

	trusted, err := trustCodexAttributionHookRPC(
		json.NewEncoder(&output),
		json.NewDecoder(strings.NewReader(input)),
		cwd,
		home,
		codexHome,
	)
	if err != nil {
		t.Fatal(err)
	}
	if trusted != 1 {
		t.Fatalf("trusted = %d, want 1", trusted)
	}

	messages := decodeRPCMessages(t, output.String())
	if len(messages) != 4 {
		t.Fatalf("sent %d messages, want initialize, initialized, list, and write", len(messages))
	}
	write := messages[3]
	if write["method"] != "config/batchWrite" {
		t.Fatalf("write method = %v", write["method"])
	}
	params := write["params"].(map[string]any)
	edits := params["edits"].([]any)
	edit := edits[0].(map[string]any)
	if edit["keyPath"] != "hooks.state" || edit["mergeStrategy"] != "upsert" {
		t.Fatalf("unsafe trust edit: %#v", edit)
	}
	value := edit["value"].(map[string]any)
	if len(value) != 1 {
		t.Fatalf("trust edit changed %d hooks, want 1", len(value))
	}
	trust := value[shadowKey].(map[string]any)
	if trust["trusted_hash"] != "hash-"+shadowKey {
		t.Fatalf("trusted hash = %v", trust["trusted_hash"])
	}
}

func TestTrustCodexAttributionHookRPCIsIdempotent(t *testing.T) {
	t.Parallel()
	home := t.TempDir()
	codexHome := filepath.Join(t.TempDir(), ".codex")
	cwd := t.TempDir()
	source := filepath.Join(codexHome, "hooks.json")
	input := strings.Join([]string{
		`{"id":1,"result":{}}`,
		`{"id":2,"result":{"data":[{"cwd":` + jsonString(cwd) + `,"hooks":[` +
			codexHookJSON(
				"git-attribution",
				"trusted",
				filepath.Join(home, ".local", "share", "agent-git-attribution", "agent_git_attribution.py")+" hook codex",
				source,
			) + `]}]}}`,
	}, "\n")
	var output bytes.Buffer

	trusted, err := trustCodexAttributionHookRPC(
		json.NewEncoder(&output),
		json.NewDecoder(strings.NewReader(input)),
		cwd,
		home,
		codexHome,
	)
	if err != nil {
		t.Fatal(err)
	}
	if trusted != 0 {
		t.Fatalf("trusted = %d, want no write", trusted)
	}
	if messages := decodeRPCMessages(t, output.String()); len(messages) != 3 {
		t.Fatalf("sent %d messages, want no config write", len(messages))
	}
}

func TestTrustCodexAttributionHookRPCRejectsNearMatch(t *testing.T) {
	t.Parallel()
	home := t.TempDir()
	codexHome := filepath.Join(t.TempDir(), ".codex")
	cwd := t.TempDir()
	source := filepath.Join(codexHome, "hooks.json")
	input := strings.Join([]string{
		`{"id":1,"result":{}}`,
		`{"id":2,"result":{"data":[{"cwd":` + jsonString(cwd) + `,"hooks":[` +
			codexHookJSON(
				"near-match",
				"untrusted",
				"sh -c "+filepath.Join(home, ".local", "share", "agent-git-attribution", "agent_git_attribution.py")+" hook codex",
				source,
			) + `]}]}}`,
	}, "\n")
	var output bytes.Buffer

	trusted, err := trustCodexAttributionHookRPC(
		json.NewEncoder(&output),
		json.NewDecoder(strings.NewReader(input)),
		cwd,
		home,
		codexHome,
	)
	if err != nil {
		t.Fatal(err)
	}
	if trusted != 0 {
		t.Fatalf("trusted = %d for a command wrapper", trusted)
	}
}

func TestTrustCodexAttributionHookRPCReportsServerError(t *testing.T) {
	t.Parallel()
	var output bytes.Buffer
	_, err := trustCodexAttributionHookRPC(
		json.NewEncoder(&output),
		json.NewDecoder(strings.NewReader(
			"{\"id\":1,\"result\":{}}\n"+
				"{\"id\":2,\"error\":{\"code\":-32601,\"message\":\"method unavailable\"}}\n",
		)),
		t.TempDir(),
		t.TempDir(),
		t.TempDir(),
	)
	if err == nil || !strings.Contains(err.Error(), "method unavailable") {
		t.Fatalf("error = %v", err)
	}
}

func TestTrustNativeCodexAttributionHookWithoutCodexIsNoOp(t *testing.T) {
	t.Setenv("PATH", t.TempDir())
	trusted, err := trustNativeCodexAttributionHook(
		context.Background(),
		t.TempDir(),
		t.TempDir(),
		t.TempDir(),
	)
	if err != nil {
		t.Fatal(err)
	}
	if trusted != 0 {
		t.Fatalf("trusted = %d without Codex", trusted)
	}
}

func codexHookJSON(key, status, command, source string) string {
	return `{"key":` + jsonString(key) +
		`,"eventName":"preToolUse","handlerType":"command","matcher":"Bash","command":` +
		jsonString(command) +
		`,"sourcePath":` + jsonString(source) +
		`,"source":"user","enabled":true,"isManaged":false,"currentHash":` +
		jsonString("hash-"+key) +
		`,"trustStatus":` + jsonString(status) + `}`
}

func jsonString(value string) string {
	raw, err := json.Marshal(value)
	if err != nil {
		panic(err)
	}
	return string(raw)
}

func decodeRPCMessages(t *testing.T, raw string) []map[string]any {
	t.Helper()
	decoder := json.NewDecoder(strings.NewReader(raw))
	var messages []map[string]any
	for decoder.More() {
		var message map[string]any
		if err := decoder.Decode(&message); err != nil {
			t.Fatal(err)
		}
		messages = append(messages, message)
	}
	return messages
}
