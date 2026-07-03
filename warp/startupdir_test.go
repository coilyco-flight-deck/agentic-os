package main

import (
	"path/filepath"
	"testing"
)

// TestStartupDirDefaultsToProjectsRoot: with no override, a fresh tab lands at
// the projects root, one level above the workspace (org) dir.
func TestStartupDirDefaultsToProjectsRoot(t *testing.T) {
	t.Setenv("WARP_STARTUP_DIR", "")
	h, err := resolveHostPaths("")
	if err != nil {
		t.Fatalf("resolveHostPaths(\"\"): %v", err)
	}
	if want := filepath.Dir(h.WorkspaceDir); h.StartupDir != want {
		t.Errorf("StartupDir = %q, want projects root %q", h.StartupDir, want)
	}
}

// TestStartupDirEnvOverride: WARP_STARTUP_DIR pins the landing dir for a host
// whose desired start dir is not the projects root (e.g. a specific repo).
func TestStartupDirEnvOverride(t *testing.T) {
	override := filepath.Join("X:", "projects", "coilyco-flight-deck", "agentic-os")
	t.Setenv("WARP_STARTUP_DIR", override)
	h, err := resolveHostPaths("")
	if err != nil {
		t.Fatalf("resolveHostPaths(\"\"): %v", err)
	}
	if want := filepath.Clean(override); h.StartupDir != want {
		t.Errorf("StartupDir = %q, want override %q", h.StartupDir, want)
	}
}

// TestStartupDirOverrideTrimmedAndCleaned: surrounding whitespace is trimmed and
// the path normalized, so a hand-set env value renders cleanly into every layer.
func TestStartupDirOverrideTrimmedAndCleaned(t *testing.T) {
	t.Setenv("WARP_STARTUP_DIR", "  X:/projects/coilyco-flight-deck/../coilyco-flight-deck  ")
	h, err := resolveHostPaths("")
	if err != nil {
		t.Fatalf("resolveHostPaths(\"\"): %v", err)
	}
	if want := filepath.Clean("X:/projects/coilyco-flight-deck"); h.StartupDir != want {
		t.Errorf("StartupDir = %q, want cleaned %q", h.StartupDir, want)
	}
}
