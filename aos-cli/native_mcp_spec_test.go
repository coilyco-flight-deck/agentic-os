package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

// An unscoped seat loads the whole user-level MCP set, so the spec path refuses
// without an inventory, as agent-compose's own launch does (#8260).
func TestNativeSpecMCPArgsRefusesWithoutAnInventory(t *testing.T) {
	bin := t.TempDir()
	stub := "#!/bin/sh\necho '{\"items\":[{\"slug\":\"eng-platform\"}]}'\n"
	if err := os.WriteFile(filepath.Join(bin, "agent-compose"), []byte(stub), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", bin+string(os.PathListSeparator)+os.Getenv("PATH"))
	spec := nativeLaunchSpec{Harness: "claude"}
	_, err := nativeSpecMCPArgs(context.Background(), spec, "eng-platform", t.TempDir(), t.TempDir(), nil)
	if !errors.Is(err, errNoMCPInventory) {
		t.Fatalf("a host with no inventory should refuse, got %v", err)
	}
	got, err := nativeSpecMCPArgs(context.Background(), spec, "eng-platform", t.TempDir(), t.TempDir(), []string{"--mcp-config", "mine.json"})
	if err != nil || got != nil {
		t.Fatalf("a caller's own scope is used as given, got %v, %v", got, err)
	}
}
