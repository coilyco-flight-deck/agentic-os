package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func writeRepositoryPlan(t *testing.T, root string, identities ...string) string {
	t.Helper()
	selections := make([]aosRepositorySelection, 0, len(identities))
	for _, identity := range identities {
		selections = append(selections, aosRepositorySelection{
			Identity: identity,
			Path:     filepath.Join(root, filepath.FromSlash(identity)),
			Source:   "test", Scope: "role-union", Reason: "test selection",
		})
	}
	plan := aosRepositoryPlan{
		Format: agentComposeRepositoryPlanFormat, ProjectsRoot: root,
		Roles:     map[string][]aosRepositorySelection{"engineer": selections},
		Residency: selections,
	}
	raw, err := json.Marshal(plan)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "repository-plan.json")
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestLoadAOSRepositoryPlanRejectsUnsortedResidency(t *testing.T) {
	root := t.TempDir()
	path := writeRepositoryPlan(t, root, "owner/two", "owner/one")
	_, err := loadAOSRepositoryPlan(path)
	if err == nil || !strings.Contains(err.Error(), "unsorted") {
		t.Fatalf("unsorted plan error = %v", err)
	}
}

func TestLoadAOSRepositoryPlanRejectsUnknownFields(t *testing.T) {
	root := t.TempDir()
	path := writeRepositoryPlan(t, root, "owner/one")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	raw = bytes.Replace(raw, []byte(`"format":`), []byte(`"unknown":true,"format":`), 1)
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := loadAOSRepositoryPlan(path); err == nil || !strings.Contains(err.Error(), "unknown") {
		t.Fatalf("unknown-field error = %v", err)
	}
}

func TestRepositoriesCommandEmitsCompiledResidency(t *testing.T) {
	root := t.TempDir()
	path := writeRepositoryPlan(t, root, "owner/one", "owner/two")
	command := newCommand()
	var output bytes.Buffer
	command.Writer = &output
	if err := command.Run(
		context.Background(),
		[]string{"aos", "repositories", "--plan", path, "--format", "lines"},
	); err != nil {
		t.Fatal(err)
	}
	if got := output.String(); got != "owner/one\nowner/two\n" {
		t.Fatalf("lines output = %q", got)
	}
}
