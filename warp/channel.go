package main

import (
	"fmt"
	"os"
	"path/filepath"
)

// warpChannel is one macOS Warp release channel: config dir and SQLite bundle as
// a matched pair, never mixed. See the tooling-warp skill.
type warpChannel struct {
	Name      string // "preview" or "stable"
	ConfigRel string // config dir, relative to the home dir
	Bundle    string // Application Support bundle id holding warp.sqlite
	AppPath   string // /Applications bundle, used only for install detection
}

var darwinChannels = map[string]warpChannel{
	"preview": {
		Name:      "preview",
		ConfigRel: ".warp-preview",
		Bundle:    "dev.warp.Warp-Preview",
		AppPath:   "/Applications/WarpPreview.app",
	},
	"stable": {
		Name:      "stable",
		ConfigRel: ".warp",
		Bundle:    "dev.warp.Warp-Stable",
		AppPath:   "/Applications/Warp.app",
	},
}

// channelOrder is the auto-detect preference: Preview is the daily driver, so it
// wins when both are installed; Stable is the named fallback.
var channelOrder = []string{"preview", "stable"}

// resolveDarwinChannel picks the macOS Warp channel: explicit request wins, else
// auto-detect by installed bundle preferring Preview, else default Preview.
func resolveDarwinChannel(requested string) (warpChannel, error) {
	if requested != "" {
		ch, ok := darwinChannels[requested]
		if !ok {
			return warpChannel{}, fmt.Errorf("unknown warp channel %q (want preview or stable)", requested)
		}
		return ch, nil
	}
	for _, name := range channelOrder {
		ch := darwinChannels[name]
		if _, err := os.Stat(ch.AppPath); err == nil {
			return ch, nil
		}
	}
	return darwinChannels["preview"], nil
}

// windowsChannel is one Windows Warp release channel: DirName keys the config,
// data, and themes roots, AppDir under %LOCALAPPDATA%\Programs detects installs.
type windowsChannel struct {
	Name    string // "preview" or "stable"
	DirName string // channel subdir under the warp config/data roots
	AppDir  string // install dir relative to %LOCALAPPDATA%\Programs
}

var windowsChannels = map[string]windowsChannel{
	"preview": {
		Name:    "preview",
		DirName: "WarpPreview",
		AppDir:  "WarpPreview",
	},
	"stable": {
		Name:    "stable",
		DirName: "Warp",
		AppDir:  "Warp",
	},
}

// resolveWindowsChannel mirrors resolveDarwinChannel: explicit request wins,
// else auto-detect by installed app dir preferring Preview, else default Preview.
func resolveWindowsChannel(requested string, localAppData string) (windowsChannel, error) {
	if requested != "" {
		ch, ok := windowsChannels[requested]
		if !ok {
			return windowsChannel{}, fmt.Errorf("unknown warp channel %q (want preview or stable)", requested)
		}
		return ch, nil
	}
	for _, name := range channelOrder {
		ch := windowsChannels[name]
		if _, err := os.Stat(filepath.Join(localAppData, "Programs", ch.AppDir)); err == nil {
			return ch, nil
		}
	}
	return windowsChannels["preview"], nil
}
