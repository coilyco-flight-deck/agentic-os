package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

// fakeSpecComposer puts an agent-compose on PATH that writes the given spec for
// `launch --spec-out` and serves the claude-ui snapshot fixture.
func fakeSpecComposer(t *testing.T, spec nativeLaunchSpec) {
	t.Helper()
	if runtime.GOOS == "windows" {
		t.Skip("the fake composer is a shell script")
	}
	bin := t.TempDir()
	raw, err := json.Marshal(spec)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(bin, "spec.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	snapshot, err := filepath.Abs(filepath.Join("testdata", "claude-ui", "snapshot.json"))
	if err != nil {
		t.Fatal(err)
	}
	script := "#!/bin/sh\n" +
		"if [ \"$1\" = launch ] && [ \"$2\" = --spec-out ]; then cp '" + filepath.Join(bin, "spec.json") + "' \"$3\"; exit 0; fi\n" +
		"if [ \"$1\" = catalog ] && [ \"$2\" = snapshot ]; then cat '" + snapshot + "'; exit 0; fi\n" +
		"exit 9\n"
	if err := os.WriteFile(filepath.Join(bin, "agent-compose"), []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", bin+string(os.PathListSeparator)+os.Getenv("PATH"))
	for _, name := range []string{"HOME", "USERPROFILE", "CODEX_HOME", "XDG_CONFIG_HOME", "CLAUDE_CONFIG_DIR",
		"AGENT_COMPOSE_LAUNCH", "AGENT_COMPOSE_SESSION_BUNDLE", "AGENT_COMPOSE_MODEL_TIER"} {
		t.Setenv(name, os.Getenv(name))
	}
}

func specFixture(t *testing.T, harness string) nativeLaunchSpec {
	t.Helper()
	home, bundle := t.TempDir(), t.TempDir()
	if err := os.WriteFile(filepath.Join(bundle, "manifest.json"), []byte(`{"role":"platform-eng"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	return nativeLaunchSpec{
		Format:      nativeLaunchSpecFormat,
		Role:        "platform",
		Harness:     harness,
		SeatName:    "Beetle-Ox-ab12",
		BundleDir:   bundle,
		RuntimeHome: home,
		EnvSet:      map[string]string{"AGENT_COMPOSE_LAUNCH": "1", "AGENT_COMPOSE_SESSION_BUNDLE": bundle},
		EnvUnset:    []string{"AGENT_COMPOSE_MODEL_TIER"},
	}
}

func TestSpecLaunchBuildsTheClaudeCommandAndEnvironment(t *testing.T) {
	spec := specFixture(t, "claude")
	fakeSpecComposer(t, spec)
	t.Setenv("AGENT_COMPOSE_MODEL_TIER", "frontier")

	got, err := resolveSpecLaunch(context.Background(),
		[]string{"agent-compose", "launch", "platform", "claude", "--model", "opus"})
	if err != nil {
		t.Fatal(err)
	}
	settings := filepath.Join(spec.RuntimeHome, ".claude", "settings.platform-eng.json")
	want := []string{"claude", "--name", "Beetle-Ox-ab12", "--settings", settings, "--model", "opus"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("argv\n got %q\nwant %q", got, want)
	}
	if _, err := os.Stat(filepath.Join(spec.RuntimeHome, ".claude", "themes", "aos-platform-eng.json")); err != nil {
		t.Errorf("theme not installed where CLAUDE_CONFIG_DIR points: %v", err)
	}
	for name, value := range map[string]string{
		"HOME":                 spec.RuntimeHome,
		"CLAUDE_CONFIG_DIR":    filepath.Join(spec.RuntimeHome, ".claude"),
		"XDG_CONFIG_HOME":      filepath.Join(spec.RuntimeHome, ".config"),
		"AGENT_COMPOSE_LAUNCH": "1",
	} {
		if got := os.Getenv(name); got != value {
			t.Errorf("%s = %q, want %q", name, got, value)
		}
	}
	if _, set := os.LookupEnv("AGENT_COMPOSE_MODEL_TIER"); set {
		t.Error("env_unset must remove the selector")
	}
}

func TestSpecLaunchLeavesCodexIdentityAndKeepsCallerFlags(t *testing.T) {
	spec := specFixture(t, "codex")
	fakeSpecComposer(t, spec)
	got, err := resolveSpecLaunch(context.Background(),
		[]string{"agent-compose", "launch", "platform", "codex", "--config", "x=1"})
	if err != nil {
		t.Fatal(err)
	}
	if want := []string{"codex", "--config", "x=1"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("argv %q, want %q", got, want)
	}
	if got := os.Getenv("CODEX_HOME"); got != filepath.Join(spec.RuntimeHome, ".codex") {
		t.Errorf("CODEX_HOME = %q", got)
	}
}

func TestSpecLaunchLetsTheCallerSettingsWin(t *testing.T) {
	spec := specFixture(t, "claude")
	fakeSpecComposer(t, spec)
	got, err := resolveSpecLaunch(context.Background(),
		[]string{"agent-compose", "launch", "platform", "claude", "--settings=/mine.json"})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Count(strings.Join(got, " "), "--settings") != 1 {
		t.Fatalf("a caller --settings must suppress aos's, got %q", got)
	}
}

func TestSpecLaunchRefusesWhatIsNotAnAgentComposeLaunch(t *testing.T) {
	if _, err := resolveSpecLaunch(context.Background(), []string{"claude"}); err == nil {
		t.Error("a bare harness command must be refused in spec mode")
	}
	spec := specFixture(t, "codex")
	fakeSpecComposer(t, spec)
	if _, err := resolveSpecLaunch(context.Background(),
		[]string{"agent-compose", "launch", "platform", "claude"}); err == nil {
		t.Error("a spec for another harness must be refused")
	}
}
