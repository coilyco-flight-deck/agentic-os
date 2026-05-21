package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// HostPaths is the resolved, per-OS layout the tool reads and writes. All
// filesystem-operation fields are native paths (filepath.Join). Template
// substitution uses forward-slash variants (see slash) so rendered TOML never
// trips over backslash escape sequences on Windows.
type HostPaths struct {
	OS           string
	RepoRoot     string // the agentic-os repo root
	WorkspaceDir string // the coilysiren workspace (parent of RepoRoot)

	ConfigDir     string // Warp's config dir
	SettingsPath  string // <ConfigDir>/settings.toml (layer 2)
	ThemeDir      string
	ThemePath     string // rendered theme yaml
	TabConfigDir  string
	TabConfigPath string // rendered startup_config.toml

	SQLitePath    string // warp.sqlite (layer 3)
	WallpaperPath string // <RepoRoot>/static/wallpaper.jpg

	// PwshProfilePath is the pwsh 7 $PROFILE path. Windows only; empty
	// elsewhere. Resolved lazily by resolvePwshProfile because it depends on
	// the host's Documents/OneDrive layout.
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
		// Warp's theme chooser scans %APPDATA%\warp\Warp\data\themes
		// (Roaming), not the Local config dir that holds settings.toml and
		// warp.sqlite. A theme rendered into <ConfigDir>/themes never shows
		// up in the chooser. See coilysiren/agentic-os#137.
		roaming := os.Getenv("APPDATA")
		if roaming == "" {
			return nil, fmt.Errorf("APPDATA is unset")
		}
		h.ThemeDir = filepath.Join(roaming, "warp", "Warp", "data", "themes")
	case "darwin":
		h.ConfigDir = filepath.Join(home, ".warp")
		// Kai runs Warp Preview on the Mac; the Stable bundle id is the
		// best default. doctor reports clearly if the DB is absent here.
		h.SQLitePath = filepath.Join(home, "Library", "Application Support",
			"dev.warp.Warp-Stable", "warp.sqlite")
	case "linux":
		h.ConfigDir = filepath.Join(home, ".config", "warp-terminal")
		h.SQLitePath = filepath.Join(home, ".local", "state", "warp-terminal", "warp.sqlite")
	default:
		return nil, fmt.Errorf("unsupported OS: %s", runtime.GOOS)
	}

	h.SettingsPath = filepath.Join(h.ConfigDir, "settings.toml")
	// ThemeDir is set per-OS above on Windows (Roaming, not ConfigDir).
	// darwin/linux keep it under the config dir.
	if h.ThemeDir == "" {
		h.ThemeDir = filepath.Join(h.ConfigDir, "themes")
	}
	h.ThemePath = filepath.Join(h.ThemeDir, themeFileName)
	h.TabConfigDir = filepath.Join(h.ConfigDir, "tab_configs")
	h.TabConfigPath = filepath.Join(h.TabConfigDir, "startup_config.toml")
	return h, nil
}

// findRepoRoot walks up from the current directory looking for a .git entry.
// `coily exec warp` runs from the repo root, so this normally resolves on the
// first iteration; the walk just makes the tool robust to a deeper cwd.
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
