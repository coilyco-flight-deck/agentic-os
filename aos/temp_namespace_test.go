package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestAOSTempPathNestsFunctionalNamespaces(t *testing.T) {
	want := filepath.Join(os.TempDir(), "aos", "native", "session")
	if got := aosTempPath("native", "session"); got != want {
		t.Fatalf("AOS temp path = %q, want %q", got, want)
	}
}
