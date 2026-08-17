package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// HostPaths is the resolved per-OS layout. See docs/warp.md.
type HostPaths struct {
	OS              string
	Channel         string // Warp channel ("preview"/"stable"); empty on linux
	RepoRoot        string
	WorkspaceDir    string
	StartupDir      string
	ConfigDir       string
	SettingsPath    string
	KeybindingsPath string
	ThemeDir        string
	ThemePath       string
	TabConfigDir    string
	TabConfigPath   string
	LaunchSrcDir    string
	LaunchDstDir    string
	SQLitePath      string
	WallpaperPath   string
	PwshProfilePath string
	DefaultShell    string // desired Warp default-shell pref; Windows-only, "" elsewhere
}

const themeFileName = "coilysiren-sombra-wallpaper.yaml"

// resolveHostPaths builds the layout for the current OS. On darwin and windows,
// channel selects the Warp channel ("" auto-detects); ignored on linux. See docs/warp.md.
func resolveHostPaths(channel string) (*HostPaths, error) {
	repoRoot, err := findRepoRoot()
	if err != nil {
		return nil, err
	}
	h := &HostPaths{
		OS:            runtime.GOOS,
		RepoRoot:      repoRoot,
		WorkspaceDir:  filepath.Dir(repoRoot),
		WallpaperPath: filepath.Join(repoRoot, "static", "wallpaper.jpg"),
	}

	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("resolving home dir: %w", err)
	}

	switch runtime.GOOS {
	case "windows":
		local := os.Getenv("LOCALAPPDATA")
		if local == "" {
			return nil, fmt.Errorf("LOCALAPPDATA is unset")
		}
		// Two Warp channels coexist, same as darwin: Preview under warp\WarpPreview,
		// Stable under warp\Warp. Config and DB are a matched pair. See docs/warp.md.
		ch, cerr := resolveWindowsChannel(channel, local)
		if cerr != nil {
			return nil, cerr
		}
		h.Channel = ch.Name
		h.ConfigDir = filepath.Join(local, "warp", ch.DirName, "config")
		h.SQLitePath = filepath.Join(local, "warp", ch.DirName, "data", "warp.sqlite")
		// Theme chooser scans %APPDATA% (Roaming), see the Warp config docs.
		roaming := os.Getenv("APPDATA")
		if roaming == "" {
			return nil, fmt.Errorf("APPDATA is unset")
		}
		h.ThemeDir = filepath.Join(roaming, "warp", ch.DirName, "data", "themes")
		// Default-shell pref lives only in warp.sqlite, resolved from disk.
		// See shell.go and docs/warp.md.
		h.DefaultShell = resolveWindowsDefaultShell()
	case "darwin":
		// Two Warp channels coexist; pick config dir and DB as a matched pair.
		// Preview (default) at ~/.warp-preview, Stable at ~/.warp. See docs/warp.md.
		ch, cerr := resolveDarwinChannel(channel)
		if cerr != nil {
			return nil, cerr
		}
		h.Channel = ch.Name
		h.ConfigDir = filepath.Join(home, ch.ConfigRel)
		h.SQLitePath = filepath.Join(home, "Library", "Application Support",
			ch.Bundle, "warp.sqlite")
	case "linux":
		h.ConfigDir = filepath.Join(home, ".config", "warp-terminal")
		h.SQLitePath = filepath.Join(home, ".local", "state", "warp-terminal", "warp.sqlite")
	default:
		return nil, fmt.Errorf("unsupported OS: %s", runtime.GOOS)
	}

	h.SettingsPath = filepath.Join(h.ConfigDir, "settings.toml")
	// Warp reads custom keybindings from keybindings.yaml, a sibling of
	// settings.toml in the config dir. See docs/warp.md.
	h.KeybindingsPath = filepath.Join(h.ConfigDir, "keybindings.yaml")
	if h.ThemeDir == "" {
		h.ThemeDir = filepath.Join(h.ConfigDir, "themes")
	}
	h.ThemePath = filepath.Join(h.ThemeDir, themeFileName)
	h.TabConfigDir = filepath.Join(h.ConfigDir, "tab_configs")
	h.TabConfigPath = filepath.Join(h.TabConfigDir, "startup_config.toml")

	// Launch configs are symlinked (not rendered): the repo dir is the source,
	// the Warp config dir is the mirror. See launch.go.
	h.LaunchSrcDir = filepath.Join(repoRoot, "warp", "launch_configurations")
	h.LaunchDstDir = filepath.Join(h.ConfigDir, "launch_configurations")

	// StartupDir is where a fresh tab opens: the projects root, one level above
	// WorkspaceDir. Every OS uses the <owner>/ grouping, Windows included.
	h.StartupDir = filepath.Dir(h.WorkspaceDir)
	// Operator-local override: WARP_STARTUP_DIR pins the landing dir per host
	// (e.g. a specific repo, not the projects root). See the tooling-warp skill.
	if override := strings.TrimSpace(os.Getenv("WARP_STARTUP_DIR")); override != "" {
		h.StartupDir = filepath.Clean(override)
	}
	return h, nil
}

// findRepoRoot walks up from cwd to the first .git entry.
func findRepoRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("not inside a git repository (no .git found above %s)", dir)
		}
		dir = parent
	}
}
