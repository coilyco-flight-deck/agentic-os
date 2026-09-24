package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

// Per-role MCP narrowing for a spec-mode launch, moved from agent-compose
// mcpscope. docs/native-harness-config.md

type mcpScopeServer struct {
	Command string            `json:"command"`
	Args    []string          `json:"args"`
	Env     map[string]string `json:"env"`
	Cwd     string            `json:"cwd"`
	URL     string            `json:"url"`
	BaseURL string            `json:"baseUrl"`
	Headers map[string]string `json:"headers"`
	AOS     struct {
		Roles []string `json:"roles"`
	} `json:"x-aos"`
}

type mcpScopeSelection struct {
	Role     string
	Selected []string
	Omitted  []string
	Scoped   int
	servers  map[string]mcpScopeServer
}

var errNoMCPInventory = errors.New("no MCP inventory")

// loadMCPScopeInventory refuses a tag that names no roster role, so a renamed
// role cannot silently lose its servers. Retired aliases are not resolved here.
func loadMCPScopeInventory(path string, roles []string) (map[string]mcpScopeServer, error) {
	raw, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, errNoMCPInventory
	}
	if err != nil {
		return nil, fmt.Errorf("read MCP inventory %s: %w", path, err)
	}
	var top struct {
		Servers map[string]mcpScopeServer `json:"mcpServers"`
	}
	if err := json.Unmarshal(raw, &top); err != nil {
		return nil, fmt.Errorf("parse MCP inventory %s: %w", path, err)
	}
	known := map[string]bool{}
	for _, role := range roles {
		known[role] = true
	}
	for _, name := range mcpScopeNames(top.Servers) {
		for _, tag := range top.Servers[name].AOS.Roles {
			if !known[tag] {
				return nil, fmt.Errorf("MCP server %q is tagged for role %q, which is not a roster role", name, tag)
			}
		}
	}
	return top.Servers, nil
}

// selectMCPScope keeps every untagged server and every server tagged for role.
func selectMCPScope(servers map[string]mcpScopeServer, role string) mcpScopeSelection {
	selection := mcpScopeSelection{Role: role, servers: map[string]mcpScopeServer{}}
	for _, name := range mcpScopeNames(servers) {
		server := servers[name]
		tagged := false
		for _, tag := range server.AOS.Roles {
			tagged = tagged || tag == role
		}
		switch {
		case len(server.AOS.Roles) == 0:
			selection.Selected = append(selection.Selected, name)
			selection.servers[name] = server
		case tagged:
			selection.Selected = append(selection.Selected, name)
			selection.servers[name] = server
			selection.Scoped++
		default:
			selection.Omitted = append(selection.Omitted, name)
		}
	}
	return selection
}

func (selection mcpScopeSelection) summary() string {
	return fmt.Sprintf("aos: MCP for %s: %d servers (%d role-scoped), %d omitted",
		selection.Role, len(selection.Selected), selection.Scoped, len(selection.Omitted))
}

// codexOverrides disables each omitted server for one launch, since the Codex
// registry is a shared host file that cannot hold a per-seat list.
func (selection mcpScopeSelection) codexOverrides() []string {
	var args []string
	for _, name := range selection.Omitted {
		args = append(args, "-c", "mcp_servers."+name+".enabled=false")
	}
	return args
}

// writeClaudeConfig names the file by its content so seats of one role share it.
// ${HOME} expands against the inventory home, as the host projection does.
func (selection mcpScopeSelection) writeClaudeConfig(dir, home string) (string, error) {
	out := map[string]any{}
	for name, server := range selection.servers {
		out[name] = mcpScopeClaudeServer(server, home)
	}
	payload, err := json.MarshalIndent(map[string]any{"mcpServers": out}, "", "  ")
	if err != nil {
		return "", err
	}
	payload = append(payload, '\n')
	sum := sha256.Sum256(payload)
	path := filepath.Join(dir, fmt.Sprintf("%s-%s.json", selection.Role, hex.EncodeToString(sum[:])[:12]))
	if existing, err := os.ReadFile(path); err == nil && string(existing) == string(payload) {
		return path, nil
	}
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return "", err
	}
	tmp, err := os.CreateTemp(dir, ".mcp-*.json")
	if err != nil {
		return "", err
	}
	defer os.Remove(tmp.Name())
	if _, err := tmp.Write(payload); err != nil {
		tmp.Close()
		return "", err
	}
	if err := tmp.Close(); err != nil {
		return "", err
	}
	return path, os.Rename(tmp.Name(), path)
}

func mcpScopeClaudeServer(server mcpScopeServer, home string) map[string]any {
	expand := func(value string) string { return strings.ReplaceAll(value, "${HOME}", home) }
	expandPath := func(value string) string {
		if strings.Contains(value, "${HOME}") {
			return filepath.Clean(filepath.FromSlash(expand(value)))
		}
		return value
	}
	expandMap := func(values map[string]string) map[string]string {
		out := make(map[string]string, len(values))
		for key, value := range values {
			out[key] = expand(value)
		}
		return out
	}
	endpoint := server.URL
	if strings.TrimSpace(endpoint) == "" {
		endpoint = server.BaseURL
	}
	if strings.TrimSpace(endpoint) != "" {
		out := map[string]any{"type": "http", "url": expand(endpoint)}
		if len(server.Headers) > 0 {
			out["headers"] = expandMap(server.Headers)
		}
		return out
	}
	out := map[string]any{"command": expandPath(server.Command)}
	if len(server.Args) > 0 {
		args := make([]string, len(server.Args))
		for index, arg := range server.Args {
			args[index] = expand(arg)
		}
		out["args"] = args
	}
	if len(server.Env) > 0 {
		out["env"] = expandMap(server.Env)
	}
	if strings.TrimSpace(server.Cwd) != "" {
		out["cwd"] = expandPath(server.Cwd)
	}
	return out
}

func mcpScopeNames(servers map[string]mcpScopeServer) []string {
	names := make([]string, 0, len(servers))
	for name := range servers {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func agentComposeRoleSlugs(ctx context.Context) ([]string, error) {
	out, err := exec.CommandContext(ctx, "agent-compose", "catalog", "roles", "--json").Output()
	if err != nil {
		return nil, fmt.Errorf("agent-compose catalog roles: %w", err)
	}
	var catalog struct {
		Items []struct {
			Slug string `json:"slug"`
		} `json:"items"`
	}
	if err := json.Unmarshal(out, &catalog); err != nil {
		return nil, fmt.Errorf("parse role catalog: %w", err)
	}
	roles := make([]string, 0, len(catalog.Items))
	for _, item := range catalog.Items {
		roles = append(roles, item.Slug)
	}
	return roles, nil
}

// nativeSpecMCPArgs narrows the inventory at <home>/.mcporter/mcporter.json to
// the role. No inventory leaves the launch unscoped, as agent-compose did.
func nativeSpecMCPArgs(ctx context.Context, spec nativeLaunchSpec, role, inventoryHome, stateDir string, args []string) ([]string, error) {
	if spec.Harness != "claude" && spec.Harness != "codex" {
		return nil, nil
	}
	if spec.Harness == "claude" &&
		(nativeSpecArgsCarry(args, "--mcp-config") || nativeSpecArgsCarry(args, "--strict-mcp-config")) {
		return nil, nil
	}
	roles, err := agentComposeRoleSlugs(ctx)
	if err != nil {
		return nil, err
	}
	servers, err := loadMCPScopeInventory(filepath.Join(inventoryHome, ".mcporter", "mcporter.json"), roles)
	if errors.Is(err, errNoMCPInventory) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	selection := selectMCPScope(servers, role)
	fmt.Fprintln(os.Stderr, selection.summary())
	if spec.Harness == "codex" {
		return selection.codexOverrides(), nil
	}
	path, err := selection.writeClaudeConfig(filepath.Join(stateDir, "mcp"), inventoryHome)
	if err != nil {
		return nil, err
	}
	return []string{"--strict-mcp-config", "--mcp-config", path}, nil
}
