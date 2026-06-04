package main

import (
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
