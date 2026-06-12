package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestResolveDarwinChannelExplicit(t *testing.T) {
	cases := []struct {
		req       string
		configRel string
		bundle    string
	}{
		{"preview", ".warp-preview", "dev.warp.Warp-Preview"},
		{"stable", ".warp", "dev.warp.Warp-Stable"},
	}
	for _, c := range cases {
		ch, err := resolveDarwinChannel(c.req)
		if err != nil {
			t.Fatalf("resolveDarwinChannel(%q): unexpected error %v", c.req, err)
		}
		if ch.Name != c.req {
			t.Errorf("resolveDarwinChannel(%q): Name = %q", c.req, ch.Name)
		}
		if ch.ConfigRel != c.configRel {
			t.Errorf("resolveDarwinChannel(%q): ConfigRel = %q, want %q", c.req, ch.ConfigRel, c.configRel)
		}
		if ch.Bundle != c.bundle {
			t.Errorf("resolveDarwinChannel(%q): Bundle = %q, want %q", c.req, ch.Bundle, c.bundle)
		}
	}
}

func TestResolveDarwinChannelUnknown(t *testing.T) {
	if _, err := resolveDarwinChannel("nightly"); err == nil {
		t.Fatal("resolveDarwinChannel(\"nightly\"): expected error, got nil")
	}
}

func TestResolveDarwinChannelAutoDetect(t *testing.T) {
	// Empty request auto-detects and must always yield a known channel, even when
	// neither bundle is installed (it defaults to Preview).
	ch, err := resolveDarwinChannel("")
	if err != nil {
		t.Fatalf("resolveDarwinChannel(\"\"): unexpected error %v", err)
	}
	if _, ok := darwinChannels[ch.Name]; !ok {
		t.Errorf("resolveDarwinChannel(\"\"): resolved to unknown channel %q", ch.Name)
	}
}

func TestResolveWindowsChannelExplicit(t *testing.T) {
	cases := []struct {
		req     string
		dirName string
	}{
		{"preview", "WarpPreview"},
		{"stable", "Warp"},
	}
	for _, c := range cases {
		ch, err := resolveWindowsChannel(c.req, t.TempDir())
		if err != nil {
			t.Fatalf("resolveWindowsChannel(%q): unexpected error %v", c.req, err)
		}
		if ch.Name != c.req {
			t.Errorf("resolveWindowsChannel(%q): Name = %q", c.req, ch.Name)
		}
		if ch.DirName != c.dirName {
			t.Errorf("resolveWindowsChannel(%q): DirName = %q, want %q", c.req, ch.DirName, c.dirName)
		}
	}
}

func TestResolveWindowsChannelUnknown(t *testing.T) {
	if _, err := resolveWindowsChannel("nightly", t.TempDir()); err == nil {
		t.Fatal("resolveWindowsChannel(\"nightly\"): expected error, got nil")
	}
}

func TestResolveWindowsChannelAutoDetect(t *testing.T) {
	// Nothing installed under Programs: default to Preview.
	ch, err := resolveWindowsChannel("", t.TempDir())
	if err != nil {
		t.Fatalf("resolveWindowsChannel(\"\"): unexpected error %v", err)
	}
	if ch.Name != "preview" {
		t.Errorf("resolveWindowsChannel(\"\") on empty host: Name = %q, want preview", ch.Name)
	}

	// Only Stable installed: detection must pick it over the Preview default.
	local := t.TempDir()
	if err := os.MkdirAll(filepath.Join(local, "Programs", "Warp"), 0o755); err != nil {
		t.Fatal(err)
	}
	ch, err = resolveWindowsChannel("", local)
	if err != nil {
		t.Fatalf("resolveWindowsChannel(\"\"): unexpected error %v", err)
	}
	if ch.Name != "stable" {
		t.Errorf("resolveWindowsChannel(\"\") with only Stable installed: Name = %q, want stable", ch.Name)
	}
}

func TestResolveHostPathsWindowsChannelPairing(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skipf("windows-only path layout (GOOS=%s)", runtime.GOOS)
	}
	cases := []struct {
		channel string
		dirName string
	}{
		{"preview", "WarpPreview"},
		{"stable", "Warp"},
	}
	for _, c := range cases {
		h, err := resolveHostPaths(c.channel)
		if err != nil {
			t.Fatalf("resolveHostPaths(%q): %v", c.channel, err)
		}
		if h.Channel != c.channel {
			t.Errorf("channel %q: HostPaths.Channel = %q", c.channel, h.Channel)
		}
		wantConfig := filepath.Join("warp", c.dirName, "config")
		if !strings.HasSuffix(h.ConfigDir, wantConfig) {
			t.Errorf("channel %q: ConfigDir = %q, want suffix %q", c.channel, h.ConfigDir, wantConfig)
		}
		wantSQLite := filepath.Join("warp", c.dirName, "data", "warp.sqlite")
		if !strings.HasSuffix(h.SQLitePath, wantSQLite) {
			t.Errorf("channel %q: SQLitePath = %q, want suffix %q", c.channel, h.SQLitePath, wantSQLite)
		}
		if filepath.Dir(h.SettingsPath) != h.ConfigDir {
			t.Errorf("channel %q: SettingsPath %q not under ConfigDir %q", c.channel, h.SettingsPath, h.ConfigDir)
		}
	}
}

func TestResolveHostPathsDarwinChannelPairing(t *testing.T) {
	if runtime.GOOS != "darwin" {
		t.Skipf("darwin-only path layout (GOOS=%s)", runtime.GOOS)
	}
	cases := []struct {
		channel   string
		configEnd string
		bundle    string
	}{
		{"preview", ".warp-preview", "dev.warp.Warp-Preview"},
		{"stable", ".warp", "dev.warp.Warp-Stable"},
	}
	for _, c := range cases {
		h, err := resolveHostPaths(c.channel)
		if err != nil {
			t.Fatalf("resolveHostPaths(%q): %v", c.channel, err)
		}
		if h.Channel != c.channel {
			t.Errorf("channel %q: HostPaths.Channel = %q", c.channel, h.Channel)
		}
		if filepath.Base(h.ConfigDir) != c.configEnd {
			t.Errorf("channel %q: ConfigDir = %q, want basename %q", c.channel, h.ConfigDir, c.configEnd)
		}
		if !strings.Contains(h.SQLitePath, c.bundle) {
			t.Errorf("channel %q: SQLitePath = %q, want it to contain %q", c.channel, h.SQLitePath, c.bundle)
		}
		// SettingsPath and other config-dir entries must follow the config dir, so
		// apply renders into the same channel doctor inspects.
		if filepath.Dir(h.SettingsPath) != h.ConfigDir {
			t.Errorf("channel %q: SettingsPath %q not under ConfigDir %q", c.channel, h.SettingsPath, h.ConfigDir)
		}
	}
}
