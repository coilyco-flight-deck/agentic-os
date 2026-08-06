package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestNativeSessionIDMatchesDictatableContract(t *testing.T) {
	raw, err := os.ReadFile(filepath.Join("..", "agentic_os", "agent_id_vectors.json"))
	if err != nil {
		t.Fatal(err)
	}
	var contract struct {
		Letters string `json:"id_letters"`
		Digits  string `json:"id_digits"`
		Length  int    `json:"id_len"`
	}
	if err := json.Unmarshal(raw, &contract); err != nil {
		t.Fatal(err)
	}
	if nativeIDLetters != contract.Letters || nativeIDDigits != contract.Digits {
		t.Fatalf(
			"native ID alphabets = %q/%q, want %q/%q",
			nativeIDLetters,
			nativeIDDigits,
			contract.Letters,
			contract.Digits,
		)
	}
	runtime := nativeTestRuntime(t, t.TempDir())
	runtime.Random = bytes.NewReader([]byte{0, 1, 2, 3})
	id, err := nativeSessionID(runtime)
	if err != nil {
		t.Fatal(err)
	}
	if id != "ab67" || len(id) != contract.Length {
		t.Fatalf("native session ID = %q, want four-character dictatable ID ab67", id)
	}
}

func TestNativeLaunchRetriesOccupiedShortSessionIDs(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	runtime.Random = bytes.NewReader([]byte{
		0, 0, 0, 0,
		1, 1, 1, 1,
		2, 2, 2, 2,
	})
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if err := os.MkdirAll(filepath.Join(runtime.SessionsRoot, "aa44"), 0o700); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "branch", "aos/codex/bb55")

	if _, err := prepareNativeLaunch(runtime, "codex"); err != nil {
		t.Fatal(err)
	}

	_, lease := onlyNativeLease(t, runtime)
	if lease.ID != "cc66" {
		t.Fatalf("native session ID = %q, want collision retry cc66", lease.ID)
	}
	if got := filepath.Base(lease.SessionRoot); got != lease.ID {
		t.Fatalf("native session root suffix = %q, want %q", got, lease.ID)
	}
	if len(lease.Artifacts) != 1 || lease.Artifacts[0].Branch != "aos/codex/cc66" {
		t.Fatalf("native artifacts = %#v, want short collision-free branch", lease.Artifacts)
	}
}
