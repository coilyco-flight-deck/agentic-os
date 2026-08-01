package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestBuildContextBundlePlanUsesAOSImageAsMaterializer(t *testing.T) {
	t.Parallel()
	plan, err := buildContextBundlePlan(contextBundlePlanOptions{
		Image:    "aos:test",
		Role:     "engineer",
		Agent:    "codex",
		Delivery: "native-skills",
		Composed: true,
		Guarded:  true,
		Output:   "/cache/staging",
		UID:      1000,
		GID:      1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	joined := strings.Join(plan.DockerArgs, "\n")
	for _, want := range []string{
		"type=bind,source=/cache/staging,target=/output",
		"type=volume,source=aos-substrate-cache,target=/var/cache/aos/git",
		"--entrypoint\n/usr/local/bin/aos",
		"aos:test",
		"--role\nengineer",
		"--agent\ncodex",
		"--composed",
		"--guarded",
		"_container-context-bundle",
	} {
		if !strings.Contains(joined, want) {
			t.Errorf("context materialization plan missing %q:\n%s", want, joined)
		}
	}
}

func TestStageAOSGuardContextCreatesOnlySelectedLoadPoints(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	source := filepath.Join(root, "source")
	home := filepath.Join(root, "home")
	if err := os.MkdirAll(filepath.Join(source, "references"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(source, "SKILL.md"), []byte("---\nname: aosguard\n---\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(source, "references", "commands.yaml"), []byte("commands: []\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := stageAOSGuardContext("codex", "engineer", home, source); err != nil {
		t.Fatal(err)
	}
	if err := validateStagedHome(home, "codex"); err != nil {
		t.Fatal(err)
	}
	instruction, err := os.ReadFile(filepath.Join(home, ".codex", "AGENTS.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(instruction), "grants no authority") {
		t.Fatalf("guarded instruction omitted authority boundary:\n%s", instruction)
	}
	if _, err := os.Stat(filepath.Join(home, ".agents", "skills", "aosguard", "references", "commands.yaml")); err != nil {
		t.Fatalf("generated skill was not staged: %v", err)
	}
}

func TestValidateStagedHomeRejectsProducerBookkeeping(t *testing.T) {
	t.Parallel()
	home := t.TempDir()
	if err := os.MkdirAll(filepath.Join(home, ".codex"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(home, ".codex", "AGENTS.md"), []byte("context\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(home, ".agent-compose"), 0o755); err != nil {
		t.Fatal(err)
	}
	err := validateStagedHome(home, "codex")
	if err == nil || !strings.Contains(err.Error(), ".agent-compose") {
		t.Fatalf("producer bookkeeping error = %v", err)
	}
}

func TestValidateContextBundleOutputBindsRoleAndAgent(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "home", ".codex"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(
		filepath.Join(root, "home", ".codex", "AGENTS.md"),
		[]byte("context\n"),
		0o644,
	); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(
		filepath.Join(root, contextBundleManifestName),
		[]byte("{\"format\":\"ward.context-bundle.v1\",\"role\":\"engineer\",\"agent\":\"codex\"}\n"),
		0o644,
	); err != nil {
		t.Fatal(err)
	}
	expected := contextBundleMaterializeOptions{
		Role: "engineer", Agent: "codex", Composed: true,
	}
	if err := validateContextBundleOutput(root, expected); err != nil {
		t.Fatal(err)
	}
	expected.Role = "qa"
	if err := validateContextBundleOutput(root, expected); err == nil {
		t.Fatal("role-mismatched context bundle passed")
	}
}
