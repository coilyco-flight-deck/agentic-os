package main

import (
	"os"
	"testing"
)

func TestListProcessesSeesThisProcessAndItsParent(t *testing.T) {
	entries, err := listProcesses()
	if err != nil {
		t.Skipf("this host's ps cannot list processes: %v", err)
	}
	for _, entry := range entries {
		if entry.PID == os.Getpid() {
			if entry.PPID != os.Getppid() || entry.Command == "" {
				t.Fatalf("entry = %+v, want ppid %d and a command", entry, os.Getppid())
			}
			return
		}
	}
	t.Fatalf("this process %d is missing from the listing", os.Getpid())
}
