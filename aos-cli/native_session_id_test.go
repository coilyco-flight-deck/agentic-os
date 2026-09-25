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
	// A pushed branch is what makes an ID taken. A bare local one no longer is:
	// the sweep reaps a landed session branch nothing leases, agentic-os#1260.
	testGit(t, repository, "branch", "aos/codex/bb55")
	testGit(t, repository, "push", "origin", "aos/codex/bb55")

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

func TestNativeLaunchTakesTheRequestedSessionID(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	runtime.RequestedID = "ab84"
	runtime.Random = bytes.NewReader([]byte{0, 0, 0, 0})
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")

	if _, err := prepareNativeLaunch(runtime, "claude"); err != nil {
		t.Fatal(err)
	}

	if _, lease := onlyNativeLease(t, runtime); lease.ID != "ab84" {
		t.Fatalf("native session ID = %q, want the requested ab84", lease.ID)
	}
}

func TestNativeLaunchDrawsFreshWhenTheRequestedIDIsTaken(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	runtime := nativeTestRuntime(t, root)
	runtime.RequestedID = "ab84"
	runtime.Random = bytes.NewReader([]byte{2, 2, 2, 2})
	writeNativeTestPlan(t, runtime.PlanFile, "one")
	writeNativeTestList(t, runtime.FleetFile, "owner")
	if err := os.MkdirAll(filepath.Join(runtime.SessionsRoot, "ab84"), 0o700); err != nil {
		t.Fatal(err)
	}

	if _, err := prepareNativeLaunch(runtime, "claude"); err != nil {
		t.Fatal(err)
	}

	if _, lease := onlyNativeLease(t, runtime); lease.ID != "cc66" {
		t.Fatalf("native session ID = %q, want a fresh cc66 past the taken ab84", lease.ID)
	}
}

func TestNativeValidSessionIDFollowsTheContract(t *testing.T) {
	for id, want := range map[string]bool{
		"ab84": true, "zz99": true, "AB81": false, "ab1": false,
		"ai84": false, "ab31": false, "../x": false, "ab841": false,
	} {
		if got := nativeValidSessionID(id); got != want {
			t.Errorf("nativeValidSessionID(%q) = %v, want %v", id, got, want)
		}
	}
}

// The host wrapper converges on `_native-shadow` calls, so minting must stay a
// root verb of its own or a launcher's metadata read waits on Ansible.
func TestSessionIDIsItsOwnRootVerb(t *testing.T) {
	if !isRootSubcommand("_session-id") {
		t.Fatal("_session-id should dispatch as a root subcommand")
	}
}
