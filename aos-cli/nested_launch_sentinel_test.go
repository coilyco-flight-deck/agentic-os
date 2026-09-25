package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// recordingSpecComposer serves `launch --spec-out` and records the launch
// markers it was handed, so a test can read what the composer actually saw.
func recordingSpecComposer(t *testing.T, spec nativeLaunchSpec, record string) {
	t.Helper()
	if runtime.GOOS == "windows" {
		t.Skip("the fake composer is a shell script")
	}
	// Pin it nonempty: a launch carrying an inline config is not also an
	// MCP-narrowing one, so a seat's ambient value cannot decide this test.
	t.Setenv(openCodeConfigEnv, `{"$schema":"https://opencode.ai/config.json"}`)
	bin := t.TempDir()
	raw, err := json.Marshal(spec)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(bin, "spec.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	script := "#!/bin/sh\n" +
		"if [ \"$1\" = launch ] && [ \"$2\" = --spec-out ]; then\n" +
		"  : > '" + record + "'\n" +
		"  echo \"AGENT_COMPOSE_LAUNCH=${AGENT_COMPOSE_LAUNCH-unset}\" >> '" + record + "'\n" +
		"  echo \"AGENT_COMPOSE_LAUNCH_DEPTH=${AGENT_COMPOSE_LAUNCH_DEPTH-unset}\" >> '" + record + "'\n" +
		"  cp '" + filepath.Join(bin, "spec.json") + "' \"$3\"\n" +
		"  exit 0\n" +
		"fi\n" +
		"exit 9\n"
	if err := os.WriteFile(filepath.Join(bin, "agent-compose"), []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", bin+string(os.PathListSeparator)+os.Getenv("PATH"))
}

// composerSaw reads back the markers the recording composer was handed.
func composerSaw(t *testing.T, record string) map[string]string {
	t.Helper()
	raw, err := os.ReadFile(record)
	if err != nil {
		t.Fatalf("the composer recorded no environment: %v", err)
	}
	seen := map[string]string{}
	for _, line := range strings.Split(strings.TrimSpace(string(raw)), "\n") {
		if name, value, ok := strings.Cut(line, "="); ok {
			seen[name] = value
		}
	}
	return seen
}

// inheritParentSeatMarkers stands for an aos running inside a live seat: the
// markers that seat was launched with are already in this process's env.
func inheritParentSeatMarkers(t *testing.T) {
	t.Helper()
	t.Setenv(agentComposeLaunchEnv, "1")
	t.Setenv(agentComposeLaunchDepthEnv, "0")
}

// TestSpecLaunchKeepsTheParentMarkersOffItsOwnHome separates the seat from the
// composer call that projects it. This launch has a shadow home of its own.
func TestSpecLaunchKeepsTheParentMarkersOffItsOwnHome(t *testing.T) {
	spec := specFixture(t, "opencode")
	record := filepath.Join(t.TempDir(), "composer-env")
	recordingSpecComposer(t, spec, record)
	inheritParentSeatMarkers(t)
	t.Setenv(agentComposeRuntimeHomeEnv, spec.RuntimeHome)
	t.Setenv(nativeCanonicalHomeEnv, t.TempDir())

	if _, err := resolveSpecLaunch(context.Background(),
		[]string{"agent-compose", "launch", "platform", "opencode"}); err != nil {
		t.Fatal(err)
	}

	for name, got := range composerSaw(t, record) {
		if got != "unset" {
			t.Errorf("%s reached the composer as %q, want unset", name, got)
		}
	}
	// The seat itself still carries the marker, or nothing would recognise it
	// as launched. Only the projection call is scrubbed.
	if got := os.Getenv(agentComposeLaunchEnv); got != "1" {
		t.Errorf("the seat's %s = %q, want 1", agentComposeLaunchEnv, got)
	}
}

// TestSpecLaunchKeepsTheParentMarkersOnASharedHome pins the other side: a launch
// with no home of its own is the nested case, so the markers must survive.
func TestSpecLaunchKeepsTheParentMarkersOnASharedHome(t *testing.T) {
	spec := specFixture(t, "opencode")
	record := filepath.Join(t.TempDir(), "composer-env")
	recordingSpecComposer(t, spec, record)
	inheritParentSeatMarkers(t)
	shared := t.TempDir()
	t.Setenv(agentComposeRuntimeHomeEnv, shared)
	t.Setenv(nativeCanonicalHomeEnv, shared)

	if _, err := resolveSpecLaunch(context.Background(),
		[]string{"agent-compose", "launch", "platform", "opencode"}); err != nil {
		t.Fatal(err)
	}

	seen := composerSaw(t, record)
	if got := seen[agentComposeLaunchEnv]; got != "1" {
		t.Errorf("%s reached the composer as %q, want 1 on a shared home", agentComposeLaunchEnv, got)
	}
	if got := seen[agentComposeLaunchDepthEnv]; got != "0" {
		t.Errorf("%s reached the composer as %q, want 0 on a shared home", agentComposeLaunchDepthEnv, got)
	}
}
