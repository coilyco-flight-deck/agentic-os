package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestConvergeEnvironmentHydratesCataloguesAndProjectsMCP(t *testing.T) {
	root := t.TempDir()
	repository := filepath.Join(root, "catalogue")
	if err := os.MkdirAll(
		filepath.Join(repository, ".agents", "skills", "example"),
		0o755,
	); err != nil {
		t.Fatal(err)
	}
	testGit(t, root, "init", "--initial-branch=main", repository)
	testGit(t, repository, "config", "user.email", "test@example.com")
	testGit(t, repository, "config", "user.name", "AOS Test")
	if err := os.WriteFile(
		filepath.Join(repository, ".agents", "skills", "example", "SKILL.md"),
		[]byte("# Example\n"),
		0o644,
	); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", ".agents/skills/example/SKILL.md")
	testGit(t, repository, "commit", "-m", "catalogue")

	home := filepath.Join(root, "home")
	configDir := filepath.Join(root, "config")
	if err := os.MkdirAll(configDir, 0o755); err != nil {
		t.Fatal(err)
	}
	inventoryPath := filepath.Join(configDir, "mcporter.json")
	if err := os.WriteFile(
		inventoryPath,
		[]byte(`{"imports":[],"mcpServers":{"reader":{"baseUrl":"https://mcp.example.test/mcp","x-codex":{"defaultToolsApprovalMode":"approve"}}}}`+"\n"),
		0o600,
	); err != nil {
		t.Fatal(err)
	}
	configPath := filepath.Join(configDir, "converge.yaml")
	config := "catalogues:\n" +
		"  state_dir: state\n" +
		"  manifest: catalogues.json\n" +
		"  cache_ttl: 1h\n" +
		"  sources:\n" +
		"    - " + strconv.Quote(repository+"@main") + "\n" +
		"mcp:\n" +
		"  inventory: mcporter.json\n"
	if err := os.WriteFile(configPath, []byte(config), 0o600); err != nil {
		t.Fatal(err)
	}

	check, err := convergeEnvironment(context.Background(), environmentConvergeOptions{
		ConfigPath: configPath,
		Home:       home,
		Check:      true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if !check.Changed {
		t.Fatal("initial check did not report drift")
	}
	if _, err := os.Stat(filepath.Join(configDir, "catalogues.json")); !os.IsNotExist(err) {
		t.Fatalf("check wrote a catalogue manifest: %v", err)
	}
	if _, err := os.Stat(filepath.Join(home, ".codex", "config.toml")); !os.IsNotExist(err) {
		t.Fatalf("check wrote native MCP state: %v", err)
	}

	applied, err := convergeEnvironment(context.Background(), environmentConvergeOptions{
		ConfigPath: configPath,
		Home:       home,
	})
	if err != nil {
		t.Fatal(err)
	}
	if !applied.Changed || applied.Catalogues != 1 || applied.MCPServers != 1 {
		t.Fatalf("unexpected apply result: %+v", applied)
	}
	manifestRaw, err := os.ReadFile(filepath.Join(configDir, "catalogues.json"))
	if err != nil {
		t.Fatal(err)
	}
	var manifest catalogueManifest
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		t.Fatal(err)
	}
	if manifest.Format != catalogueManifestKind || len(manifest.Catalogues) != 1 {
		t.Fatalf("unexpected manifest: %+v", manifest)
	}
	entry := manifest.Catalogues[0]
	if entry.Source != repository+"@main" || entry.Commit == "" {
		t.Fatalf("unexpected catalogue entry: %+v", entry)
	}
	if _, err := os.Stat(filepath.Join(entry.Path, "example", "SKILL.md")); err != nil {
		t.Fatalf("hydrated catalogue path is unusable: %v", err)
	}
	codexRaw, err := os.ReadFile(filepath.Join(home, ".codex", "config.toml"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(codexRaw), `default_tools_approval_mode = "approve"`) {
		t.Fatalf("Codex approval policy was not projected:\n%s", codexRaw)
	}

	current, err := convergeEnvironment(context.Background(), environmentConvergeOptions{
		ConfigPath: configPath,
		Home:       home,
		Check:      true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if current.Changed {
		t.Fatalf("converged environment still drifts: %+v", current)
	}
}

func TestConvergeEnvironmentUsesVerifiedCacheWhenRefreshFails(t *testing.T) {
	root := t.TempDir()
	repository := filepath.Join(root, "catalogue")
	if err := os.MkdirAll(filepath.Join(repository, ".agents", "skills"), 0o755); err != nil {
		t.Fatal(err)
	}
	testGit(t, root, "init", "--initial-branch=main", repository)
	testGit(t, repository, "config", "user.email", "test@example.com")
	testGit(t, repository, "config", "user.name", "AOS Test")
	if err := os.WriteFile(
		filepath.Join(repository, ".agents", "skills", "SKILL.md"),
		[]byte("# Cached\n"),
		0o644,
	); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", ".agents/skills/SKILL.md")
	testGit(t, repository, "commit", "-m", "catalogue")

	now := time.Now()
	source, err := parseCatalogueLocator(repository + "@main")
	if err != nil {
		t.Fatal(err)
	}
	options := catalogueHydrateOptions{
		StateDir: filepath.Join(root, "state"),
		TTL:      time.Minute,
		Now:      func() time.Time { return now },
	}
	first, _, err := hydrateCatalogues(context.Background(), []catalogueSource{source}, options)
	if err != nil {
		t.Fatal(err)
	}
	if len(first) != 1 || first[0].State != "hydrated" {
		t.Fatalf("unexpected first hydration: %+v", first)
	}
	unavailable := repository + ".unavailable"
	if err := os.Rename(repository, unavailable); err != nil {
		t.Fatal(err)
	}
	options.Now = func() time.Time { return now.Add(2 * time.Minute) }
	second, _, err := hydrateCatalogues(context.Background(), []catalogueSource{source}, options)
	if err != nil {
		t.Fatal(err)
	}
	if second[0].State != "fallback" || second[0].Warning == "" {
		t.Fatalf("stale refresh did not use verified cache: %+v", second[0])
	}
	if second[0].Commit != first[0].Commit {
		t.Fatalf("fallback commit = %q, want %q", second[0].Commit, first[0].Commit)
	}
}

func TestParseCatalogueLocatorRejectsEmbeddedCredentials(t *testing.T) {
	_, err := parseCatalogueLocator(
		"https://user:secret@example.test/catalogue.git@main",
	)
	if err == nil || !strings.Contains(err.Error(), "must not embed credentials") {
		t.Fatalf("embedded credential error = %v", err)
	}
}

func TestConvergeEnvironmentDefaultMissingConfigIsNoOp(t *testing.T) {
	result, err := convergeEnvironment(
		context.Background(),
		environmentConvergeOptions{Home: t.TempDir()},
	)
	if err != nil {
		t.Fatal(err)
	}
	if result.Configured || result.Changed {
		t.Fatalf("missing default config result = %+v", result)
	}
}
