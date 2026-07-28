package main

import (
	"context"
	"encoding/json"
	"net/netip"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestTailnetAddressClassification(t *testing.T) {
	t.Parallel()
	for _, value := range []string{
		"100.64.0.1",
		"100.127.255.254",
		"fd7a:115c:a1e0::1",
	} {
		if !isTailnetAddress(netip.MustParseAddr(value)) {
			t.Errorf("%s was not classified as a tailnet address", value)
		}
	}
	for _, value := range []string{
		"100.63.255.255",
		"100.128.0.1",
		"192.0.2.1",
		"2001:db8::1",
	} {
		if isTailnetAddress(netip.MustParseAddr(value)) {
			t.Errorf("%s was classified as a tailnet address", value)
		}
	}
}

func TestTailnetForwardEncodingRoundTrip(t *testing.T) {
	t.Parallel()
	want := tailnetForward{
		Server:     "internal",
		TargetHost: "internal.example",
		TargetPort: 30082,
		ListenPort: 39000,
	}
	encoded, err := want.encode()
	if err != nil {
		t.Fatal(err)
	}
	got, err := decodeTailnetForward(encoded)
	if err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("decoded forward = %+v, want %+v", got, want)
	}
}

func TestProjectTailnetMCPInventoryPreservesUnrelatedConfiguration(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	source := filepath.Join(root, "source.json")
	target := filepath.Join(root, "projected", "mcporter.json")
	body := `{
  "imports": [],
  "mcpServers": {
    "public": {
      "baseUrl": "https://public.example/mcp"
    },
    "internal": {
      "baseUrl": "http://internal.example:30082/mcp?mode=stream",
      "x-codex": {
        "defaultToolsApprovalMode": "never"
      }
    }
  }
}
`
	if err := os.WriteFile(source, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	forward := tailnetForward{
		Server:     "internal",
		TargetHost: "internal.example",
		TargetPort: 30082,
		ListenPort: 39000,
	}
	if err := projectTailnetMCPInventory(source, target, []tailnetForward{forward}); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	var document struct {
		Imports    []string                              `json:"imports"`
		MCPServers map[string]map[string]json.RawMessage `json:"mcpServers"`
	}
	if err := json.Unmarshal(data, &document); err != nil {
		t.Fatal(err)
	}
	var publicURL string
	if err := json.Unmarshal(document.MCPServers["public"]["baseUrl"], &publicURL); err != nil {
		t.Fatal(err)
	}
	if publicURL != "https://public.example/mcp" {
		t.Fatalf("public URL changed to %q", publicURL)
	}
	var internalURL string
	if err := json.Unmarshal(document.MCPServers["internal"]["baseUrl"], &internalURL); err != nil {
		t.Fatal(err)
	}
	if internalURL != "http://127.0.0.1:39000/mcp?mode=stream" {
		t.Fatalf("internal URL = %q", internalURL)
	}
	if _, ok := document.MCPServers["internal"]["x-codex"]; !ok {
		t.Fatal("x-codex configuration was dropped")
	}
}

func TestStageMCPProjectionUsesAgentComposeProjector(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	source := filepath.Join(root, "mcporter.json")
	if err := os.WriteFile(
		source,
		[]byte(`{"imports":[],"mcpServers":{"public":{"baseUrl":"https://public.example/mcp"}}}`),
		0o600,
	); err != nil {
		t.Fatal(err)
	}
	runner := &fakeCommandRunner{}
	opts := bootstrapOptions{
		AgentHome:       filepath.Join(root, "home"),
		AgentComposeBin: "agent-compose",
		MCPInventory:    source,
	}
	if err := stageMCPProjection(context.Background(), opts, runner); err != nil {
		t.Fatal(err)
	}
	joined := strings.Join(runner.commands, "\n")
	want := "agent-compose mcp --inventory " + source + " --home " + opts.AgentHome
	if !strings.Contains(joined, want) {
		t.Fatalf("MCP projection command missing %q:\n%s", want, joined)
	}
}

func TestLoadMCPEndpointsSortsAndIgnoresCommandServers(t *testing.T) {
	t.Parallel()
	path := filepath.Join(t.TempDir(), "mcporter.json")
	if err := os.WriteFile(path, []byte(`{
  "mcpServers": {
    "zeta": {"url": "http://zeta.example:8080/mcp"},
    "command": {"command": "example"},
    "alpha": {"baseUrl": "https://alpha.example/mcp"}
  }
}`), 0o600); err != nil {
		t.Fatal(err)
	}
	endpoints, err := loadMCPEndpoints(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(endpoints) != 2 || endpoints[0].Server != "alpha" || endpoints[1].Server != "zeta" {
		t.Fatalf("unexpected endpoints: %+v", endpoints)
	}
}
