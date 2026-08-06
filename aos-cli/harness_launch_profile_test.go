package main

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"testing"
)

func TestLoadHarnessLaunchProfilesUsesRoleAgents(t *testing.T) {
	t.Parallel()
	document, err := loadHarnessLaunchProfiles([]byte(`
roles:
  engineer:
    agent: codex
  director:
    agent: claude
`))
	if err != nil {
		t.Fatal(err)
	}
	if document.Roles["engineer"].Agent != "codex" {
		t.Fatalf("engineer role was not decoded: %+v", document.Roles["engineer"])
	}
	if document.DefaultAgents["director"] != "claude" {
		t.Fatalf("default agent was not decoded: %+v", document.DefaultAgents)
	}
}

func TestLoadHarnessLaunchProfilesRejectsMalformedRegistry(t *testing.T) {
	t.Parallel()
	for _, data := range [][]byte{
		[]byte(`{}`),
		[]byte("roles: {}\n"),
		[]byte("roles:\n  bad/role:\n    agent: codex\n"),
		[]byte("roles:\n  engineer: {}\n"),
		[]byte("roles:\n  engineer:\n    agent: other\n"),
		[]byte("roles:\n  engineer:\n    agent: codex\n    model: gpt-5\n"),
		[]byte("defaults:\n  codex: {model: gpt-5}\n"),
	} {
		if _, err := loadHarnessLaunchProfiles(data); err == nil {
			t.Fatalf("loadHarnessLaunchProfiles accepted %q", data)
		}
	}
}

func TestStandaloneDefaultAgentForRole(t *testing.T) {
	t.Parallel()
	tests := map[string]string{
		"engineer": "codex",
		"director": "claude",
	}
	for role, want := range tests {
		got, err := standaloneDefaultAgentForRole(role)
		if err != nil {
			t.Fatal(err)
		}
		if got != want {
			t.Fatalf("standaloneDefaultAgentForRole(%s) = %q, want %q", role, got, want)
		}
	}
	for _, role := range []string{"", "bad/role", "story-architect"} {
		if _, err := standaloneDefaultAgentForRole(role); err == nil {
			t.Fatalf("standaloneDefaultAgentForRole(%q) succeeded", role)
		}
	}
}

func TestConfiguredHarnessLaunchProfilesReadsAgentsFile(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".agents"), 0o755); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, harnessLaunchProfilesRelativePath)
	if err := os.WriteFile(path, []byte(`
roles:
  engineer:
    agent: goose
`), 0o644); err != nil {
		t.Fatal(err)
	}
	child := filepath.Join(root, "child")
	if err := os.Mkdir(child, 0o755); err != nil {
		t.Fatal(err)
	}
	t.Chdir(child)
	oldCompiled := compiledHarnessLaunchProfilesBase64
	compiledHarnessLaunchProfilesBase64 = base64.StdEncoding.EncodeToString([]byte(`
roles:
  engineer:
    agent: codex
`))
	t.Cleanup(func() { compiledHarnessLaunchProfilesBase64 = oldCompiled })

	agent, err := standaloneDefaultAgentForRole("engineer")
	if err != nil {
		t.Fatal(err)
	}
	if agent != "goose" {
		t.Fatalf("standaloneDefaultAgentForRole(engineer) = %q, want goose", agent)
	}
}

func TestConfiguredHarnessLaunchProfilesUsesCompiledFallback(t *testing.T) {
	t.Chdir(t.TempDir())
	oldCompiled := compiledHarnessLaunchProfilesBase64
	compiledHarnessLaunchProfilesBase64 = base64.StdEncoding.EncodeToString([]byte(`
roles:
  engineer:
    agent: opencode
`))
	t.Cleanup(func() { compiledHarnessLaunchProfilesBase64 = oldCompiled })

	agent, err := standaloneDefaultAgentForRole("engineer")
	if err != nil {
		t.Fatal(err)
	}
	if agent != "opencode" {
		t.Fatalf("standaloneDefaultAgentForRole(engineer) = %q, want opencode", agent)
	}
}
