package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// HostPaths is the resolved per-OS layout. See docs/warp-paths.md.
type HostPaths struct {
	OS              string
	RepoRoot        string
	WorkspaceDir    string
	StartupDir      string
	ConfigDir       string
	SettingsPath    string
	ThemeDir        string
	ThemePath       string
	TabConfigDir    string
	TabConfigPath   string
	SQLitePath      string
	WallpaperPath   string
	PwshProfilePath string
}

const themeFileName = "coilysiren-sombra-wallpaper.yaml"

// resolveHostPaths builds the layout for the current OS.
func resolveHostPaths() (*HostPaths, error) {
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
		h.ConfigDir = filepath.Join(local, "warp", "Warp", "config")
		h.SQLitePath = filepath.Join(local, "warp", "Warp", "data", "warp.sqlite")
		// Theme chooser scans %APPDATA% (Roaming), see coilysiren/agentic-os#137.
		roaming := os.Getenv("APPDATA")
		if roaming == "" {
			return nil, fmt.Errorf("APPDATA is unset")
		}
		h.ThemeDir = filepath.Join(roaming, "warp", "Warp", "data", "themes")
	case "darwin":
		h.ConfigDir = filepath.Join(home, ".warp")
		// Kai runs Warp Preview on macOS, so target the Preview bundle's DB.
		// (Preview ships on every platform, but on Windows Kai runs Stable.)
		h.SQLitePath = filepath.Join(home, "Library", "Application Support",
			"dev.warp.Warp-Preview", "warp.sqlite")
	case "linux":
		h.ConfigDir = filepath.Join(home, ".config", "warp-terminal")
		h.SQLitePath = filepath.Join(home, ".local", "state", "warp-terminal", "warp.sqlite")
	default:
		return nil, fmt.Errorf("unsupported OS: %s", runtime.GOOS)
	}

	h.SettingsPath = filepath.Join(h.ConfigDir, "settings.toml")
	if h.ThemeDir == "" {
		h.ThemeDir = filepath.Join(h.ConfigDir, "themes")
	}
	h.ThemePath = filepath.Join(h.ThemeDir, themeFileName)
	h.TabConfigDir = filepath.Join(h.ConfigDir, "tab_configs")
	h.TabConfigPath = filepath.Join(h.TabConfigDir, "startup_config.toml")

	// StartupDir is where a fresh tab opens: the projects root. On Mac/Linux
	// the repos nest under a coilysiren/ grouping dir, so the root is one
	// level above WorkspaceDir. On Windows the layout is flat (projects-x\<repo>),
	// so WorkspaceDir already is the root.
	h.StartupDir = h.WorkspaceDir
	if runtime.GOOS != "windows" {
		h.StartupDir = filepath.Dir(h.WorkspaceDir)
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
