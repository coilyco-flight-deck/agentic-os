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

func TestAOSTempAliasPathNestsFunctionalNamespaces(t *testing.T) {
	want := filepath.Join("/tmp", "aos", "native", "session")
	if got := aosTempAliasPath("native", "session"); got != want {
		t.Fatalf("AOS temp alias path = %q, want %q", got, want)
	}
}

func TestEnsureTempAliasLinksAliasAtTarget(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	alias := filepath.Join(root, "alias")

	if got := ensureTempAlias(target, alias); got != alias {
		t.Fatalf("alias = %q, want %q", got, alias)
	}
	linked, err := os.Readlink(alias)
	if err != nil {
		t.Fatalf("read alias link: %v", err)
	}
	if linked != target {
		t.Fatalf("alias points at %q, want %q", linked, target)
	}
}

func TestEnsureTempAliasReusesMatchingAlias(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	alias := filepath.Join(root, "alias")

	first := ensureTempAlias(target, alias)
	if second := ensureTempAlias(target, alias); second != first {
		t.Fatalf("second alias = %q, want %q", second, first)
	}
}

func TestEnsureTempAliasFallsBackWhenAliasPointsElsewhere(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	alias := filepath.Join(root, "alias")
	if err := os.Symlink(filepath.Join(root, "other"), alias); err != nil {
		t.Fatalf("seed foreign alias: %v", err)
	}

	if got := ensureTempAlias(target, alias); got != target {
		t.Fatalf("alias = %q, want fallback to %q", got, target)
	}
}

func TestEnsureTempAliasFallsBackWhenAliasIsRealDirectory(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target")
	alias := filepath.Join(root, "alias")
	if err := os.MkdirAll(alias, 0o700); err != nil {
		t.Fatalf("seed alias directory: %v", err)
	}

	if got := ensureTempAlias(target, alias); got != target {
		t.Fatalf("alias = %q, want fallback to %q", got, target)
	}
}

func TestEnsureTempAliasSkipsWhenAliasEqualsTarget(t *testing.T) {
	target := filepath.Join(t.TempDir(), "aos")
	if got := ensureTempAlias(target, target); got != target {
		t.Fatalf("alias = %q, want %q", got, target)
	}
}
