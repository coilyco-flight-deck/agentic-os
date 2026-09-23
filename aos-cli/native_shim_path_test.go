package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestPrependNativeShimPathFrontsShims(t *testing.T) {
	home := t.TempDir()
	shims := filepath.Join(home, ".local", "umbra", "shims")
	if err := os.MkdirAll(shims, 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", "/usr/bin:/bin")
	if err := prependNativeShimPath(home); err != nil {
		t.Fatal(err)
	}
	if got := os.Getenv("PATH"); got != shims+string(os.PathListSeparator)+"/usr/bin:/bin" {
		t.Fatalf("PATH = %q, want the shim dir first", got)
	}
	// A second launch step must not stack a duplicate.
	if err := prependNativeShimPath(home); err != nil {
		t.Fatal(err)
	}
	if n := strings.Count(os.Getenv("PATH"), shims); n != 1 {
		t.Fatalf("shim dir appears %d times", n)
	}
}

func TestPrependNativeShimPathLeavesPathWithoutShims(t *testing.T) {
	t.Setenv("PATH", "/usr/bin:/bin")
	for _, home := range []string{"", t.TempDir()} {
		if err := prependNativeShimPath(home); err != nil {
			t.Fatal(err)
		}
		if got := os.Getenv("PATH"); got != "/usr/bin:/bin" {
			t.Fatalf("home %q: PATH = %q, want it untouched", home, got)
		}
	}
}
