//go:build darwin

package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"golang.org/x/sys/unix"
)

func readBundleTag(t *testing.T, path string) string {
	t.Helper()
	size, err := unix.Getxattr(path, bundleTagAttribute, nil)
	if err != nil {
		return ""
	}
	buffer := make([]byte, size)
	if _, err := unix.Getxattr(path, bundleTagAttribute, buffer); err != nil {
		t.Fatalf("read the tag: %v", err)
	}
	return string(buffer)
}

// One shared tag is what makes `acompose` in Spotlight surface the whole set,
// so an untagged bundle is a silently unfindable one. See docs/aterm.md.
func TestABundleCarriesTheSharedFinderTag(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "Tagged.app")
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}

	if err := tagBundle(path, "acompose"); err != nil {
		t.Fatalf("tag: %v", err)
	}

	document := readBundleTag(t, path)
	if !strings.Contains(document, "<string>acompose</string>") {
		t.Fatalf("tag document = %q", document)
	}
}

// An empty tag writes no xattr rather than an empty one, so `--tag ""` opts out
// cleanly instead of leaving every bundle carrying a blank Finder tag.
func TestAnEmptyTagWritesNothing(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "Untagged.app")
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}

	if err := tagBundle(path, "  "); err != nil {
		t.Fatalf("empty tag: %v", err)
	}

	if document := readBundleTag(t, path); document != "" {
		t.Fatalf("an empty tag wrote %q", document)
	}
}
