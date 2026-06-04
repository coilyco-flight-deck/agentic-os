package main

import (
	"fmt"
	"os"
)

// warpChannel is one macOS Warp release channel: config dir and SQLite bundle as
// a matched pair, never mixed. See docs/warp.md, docs/warp-host-setup.md.
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
