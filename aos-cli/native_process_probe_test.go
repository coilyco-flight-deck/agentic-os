package main

import (
	"os"
	"os/exec"
	"testing"
)

// deadPID returns the PID of a process that has exited, so tests exercise the
// real "not running" answer instead of a PID the platform would reject.
func deadPID(t *testing.T) int {
	t.Helper()
	command := exec.Command("go", "version")
	if err := command.Start(); err != nil {
		t.Fatal(err)
	}
	pid := command.Process.Pid
	if err := command.Wait(); err != nil {
		t.Fatal(err)
	}
	return pid
}

func TestProbeResolvesManyPIDsInOneQuery(t *testing.T) {
	self := os.Getpid()
	identity, err := processStartIdentity(self)
	if err != nil {
		t.Fatal(err)
	}

	gone := deadPID(t)
	identities, err := processStartIdentities([]int{self, self, gone})
	if err != nil {
		t.Fatal(err)
	}

	if identities[self] != identity {
		t.Fatalf("batched identity = %q, want %q", identities[self], identity)
	}
	if _, found := identities[gone]; found {
		t.Fatal("a dead pid resolved to an identity")
	}
}

func TestProbeReportsAnAbsentPIDDeadWithoutReasking(t *testing.T) {
	gone := deadPID(t)
	probe := probeNativeProcesses([]int{gone})
	if !probe.batched {
		t.Fatal("probe did not batch, so every dead lease would respawn ps")
	}
	if probe.leaseIsLive(nativeLease{PID: gone, ProcessStart: "gone"}) {
		t.Fatal("an absent pid reported live")
	}
}

func TestProbeKeepsALiveLeaseLive(t *testing.T) {
	self := os.Getpid()
	identity, err := processStartIdentity(self)
	if err != nil {
		t.Fatal(err)
	}

	probe := probeNativeProcesses([]int{self})
	if !probe.leaseIsLive(nativeLease{PID: self, ProcessStart: identity}) {
		t.Fatal("a running process reported dead")
	}
	if probe.leaseIsLive(nativeLease{PID: self, ProcessStart: "stale"}) {
		t.Fatal("a recycled pid with a different start time reported live")
	}
}

func TestUnbatchedProbeFallsBackPerPID(t *testing.T) {
	self := os.Getpid()
	identity, err := processStartIdentity(self)
	if err != nil {
		t.Fatal(err)
	}

	probe := nativeProcessProbe{}
	if !probe.leaseIsLive(nativeLease{PID: self, ProcessStart: identity}) {
		t.Fatal("fallback path reported a running process dead")
	}
	if probe.leaseIsLive(nativeLease{PID: deadPID(t), ProcessStart: "gone"}) {
		t.Fatal("fallback path reported an absent pid live")
	}
}

func TestBatchProcessPIDsDedupesAndChunks(t *testing.T) {
	if batches := batchProcessPIDs(nil); batches != nil {
		t.Fatalf("empty input produced %v", batches)
	}
	if batches := batchProcessPIDs([]int{7, 7, 0, -1, 8}); len(batches) != 1 ||
		len(batches[0]) != 2 || batches[0][0] != 7 || batches[0][1] != 8 {
		t.Fatalf("dedupe or filter failed: %v", batches)
	}

	many := make([]int, 0, 600)
	for pid := 1; pid <= 600; pid++ {
		many = append(many, pid)
	}
	batches := batchProcessPIDs(many)
	if len(batches) != 3 {
		t.Fatalf("600 pids produced %d batch(es), want 3", len(batches))
	}
	total := 0
	for _, batch := range batches {
		if len(batch) > 256 {
			t.Fatalf("batch of %d exceeds the query cap", len(batch))
		}
		total += len(batch)
	}
	if total != 600 {
		t.Fatalf("batches covered %d pids, want 600", total)
	}
}

func TestNativeLeaseIsLiveStillAnswersDirectly(t *testing.T) {
	self := os.Getpid()
	identity, err := processStartIdentity(self)
	if err != nil {
		t.Fatal(err)
	}
	if !nativeLeaseIsLive(nativeLease{PID: self, ProcessStart: identity}) {
		t.Fatal("direct helper reported a running process dead")
	}
	if nativeLeaseIsLive(nativeLease{PID: 0, ProcessStart: identity}) {
		t.Fatal("a lease without a pid reported live")
	}
}

func TestRejectedQueryFallsBackInsteadOfDeclaringEveryoneDead(t *testing.T) {
	self := os.Getpid()
	identity, err := processStartIdentity(self)
	if err != nil {
		t.Fatal(err)
	}

	// A PID above the platform maximum makes ps reject the whole query. The
	// empty result must not be read as proof that the live PID is gone.
	if _, err := processStartIdentities([]int{self, 1 << 30}); err == nil {
		t.Skip("this platform's ps tolerates an out-of-range pid")
	}
	probe := probeNativeProcesses([]int{self, 1 << 30})
	if probe.batched {
		t.Fatal("a rejected query was treated as an authoritative answer")
	}
	if !probe.leaseIsLive(nativeLease{PID: self, ProcessStart: identity}) {
		t.Fatal("a rejected query reported a running process dead")
	}
}
