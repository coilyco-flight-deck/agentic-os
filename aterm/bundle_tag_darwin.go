//go:build darwin

package main

import (
	"fmt"
	"strings"

	"golang.org/x/sys/unix"
)

// Spotlight reads Finder tags from this xattr, and matches them on a plain
// text query, so one shared tag makes the whole set findable by typing it.
const bundleTagAttribute = "com.apple.metadata:_kMDItemUserTags"

// tagBundle marks one .app so `acompose` in Spotlight surfaces every role at
// once. Finder writes a binary plist here; the XML form indexes identically.
func tagBundle(path, tag string) error {
	if strings.TrimSpace(tag) == "" {
		return nil
	}
	document := `<?xml version="1.0" encoding="UTF-8"?>` +
		`<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ` +
		`"http://www.apple.com/DTDs/PropertyList-1.0.dtd">` +
		`<plist version="1.0"><array><string>` + xmlEscape(tag) +
		`</string></array></plist>`
	if err := unix.Setxattr(path, bundleTagAttribute, []byte(document), 0); err != nil {
		return fmt.Errorf("tag %q: %w", path, err)
	}
	return nil
}
