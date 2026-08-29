package main

import (
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// stubPlanRegeneration replaces the only seam that shells out, so a test can
// never reach the host's Agent Compose or rewrite the host's plan.
func stubPlanRegeneration(t *testing.T, action func(nativeRuntime) error) *int {
	t.Helper()
	calls := 0
	previous := runPlanRegeneration
	runPlanRegeneration = func(runtime nativeRuntime) error {
		calls++
		return action(runtime)
	}
	t.Cleanup(func() { runPlanRegeneration = previous })
	return &calls
}

func writeTestPolicy(t *testing.T, projects, identity, body string) {
	t.Helper()
	policy := filepath.Join(projects, filepath.FromSlash(identity), ".agents", "roles.kdl")
	if err := os.MkdirAll(filepath.Dir(policy), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(policy, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestSealedProvenanceThatMatchesNeverRegenerates(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	testRuntime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	calls := stubPlanRegeneration(t, func(nativeRuntime) error {
		return errors.New("regeneration must not run for a plan that verifies")
	})

	plan, err := verifiedRepositoryPlan(testRuntime)

	if err != nil {
		t.Fatal(err)
	}
	if *calls != 0 {
		t.Fatalf("a matching plan regenerated %d times", *calls)
	}
	if plan.Unverified {
		t.Fatal("a verified plan reported itself unverified")
	}
}

// The digest is the trigger, so changed policy content at the same path is the
// case that must regenerate.
func TestChangedPolicyContentRegeneratesExactlyOnce(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	testRuntime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	writeTestPolicy(t, testRuntime.ProjectsRoot, "owner/policy", "role \"platform\" { moved }\n")
	calls := stubPlanRegeneration(t, func(runtime nativeRuntime) error {
		writeNativeTestPlan(t, runtime.PlanFile, "one")
		writeTestPolicy(t, runtime.ProjectsRoot, "owner/policy", "role \"platform\" { moved }\n")
		resealTestPlan(t, runtime, "owner/policy")
		return nil
	})

	plan, err := verifiedRepositoryPlan(testRuntime)

	if err != nil {
		t.Fatal(err)
	}
	if *calls != 1 {
		t.Fatalf("regeneration ran %d times, want exactly 1", *calls)
	}
	if len(plan.Residency) != 1 {
		t.Fatalf("the reloaded plan carries %d residency entries", len(plan.Residency))
	}
}

// No Agent Compose on PATH cannot refresh, and must still not be a wall.
func TestUnavailableRegenerationStillLaunches(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	testRuntime := nativeTestRuntime(t, root)
	var log strings.Builder
	testRuntime.Stderr = &log
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	writeTestPolicy(t, testRuntime.ProjectsRoot, "owner/policy", "role \"platform\" { moved }\n")
	previous := hostLookPath
	hostLookPath = func(string) (string, error) { return "", exec.ErrNotFound }
	t.Cleanup(func() { hostLookPath = previous })

	if _, err := prepareNativeLaunch(testRuntime, "claude"); err != nil {
		t.Fatalf("an unavailable refresh must not fail the launch: %v", err)
	}

	if !strings.Contains(log.String(), "could not refresh") {
		t.Fatalf("an unavailable refresh said %q, want one line naming it", log.String())
	}
}

// A refresh that errors names itself and gets out of the way, because a stale
// plan is a worse launch rather than an impossible one.
func TestFailedRegenerationStillLaunches(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	testRuntime := nativeTestRuntime(t, root)
	var log strings.Builder
	testRuntime.Stderr = &log
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	writeTestPolicy(t, testRuntime.ProjectsRoot, "owner/policy", "role \"platform\" { moved }\n")
	calls := stubPlanRegeneration(t, func(nativeRuntime) error {
		return errors.New("compose exited 1")
	})

	if _, err := prepareNativeLaunch(testRuntime, "claude"); err != nil {
		t.Fatalf("a failed refresh must not fail the launch: %v", err)
	}

	if *calls != 1 {
		t.Fatalf("a failed refresh ran %d times, want exactly 1", *calls)
	}
	if !strings.Contains(log.String(), "compose exited 1") {
		t.Fatalf("a failed refresh said %q, want the cause", log.String())
	}
}

// A stale digest is a refresh trigger, never a wall, and one that cannot
// converge is attempted once rather than looped.
func TestAPersistentMismatchStillLaunches(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	testRuntime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	writeTestPolicy(t, testRuntime.ProjectsRoot, "owner/policy", "role \"platform\" { moved }\n")
	calls := stubPlanRegeneration(t, func(nativeRuntime) error { return nil })

	if _, err := prepareNativeLaunch(testRuntime, "claude"); err != nil {
		t.Fatalf("a persistent mismatch must not fail the launch: %v", err)
	}

	if *calls != 1 {
		t.Fatalf("a persistent mismatch regenerated %d times, want exactly 1", *calls)
	}
}

// The refresh is plumbing, so a working launch says nothing about it at all.
func TestARefreshedPlanPrintsNothing(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	testRuntime := nativeTestRuntime(t, root)
	var log strings.Builder
	testRuntime.Stderr = &log
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	writeTestPolicy(t, testRuntime.ProjectsRoot, "owner/policy", "role \"platform\" { moved }\n")
	stubPlanRegeneration(t, func(runtime nativeRuntime) error {
		writeNativeTestPlan(t, runtime.PlanFile, "one")
		resealTestPlan(t, runtime, "owner/policy")
		return nil
	})

	if _, err := prepareNativeLaunch(testRuntime, "claude"); err != nil {
		t.Fatal(err)
	}

	if noise := log.String(); noise != "" {
		t.Fatalf("a refreshed launch printed %q, want silence", noise)
	}
}

// The reload has to be a full one: a plan regenerated from moved policy can
// select a repository the stale plan never named, and the launch must link it.
func TestARegeneratedPlanLinksANewlySelectedRepository(t *testing.T) {
	root := t.TempDir()
	createNativeTestRepository(t, root, "owner", "one")
	createNativeTestRepository(t, root, "owner", "two")
	testRuntime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, testRuntime.PlanFile, "one")
	writeNativeTestList(t, testRuntime.FleetFile, "owner")
	writeTestPolicy(t, testRuntime.ProjectsRoot, "owner/policy", "role \"platform\" { two }\n")
	stubPlanRegeneration(t, func(runtime nativeRuntime) error {
		writeNativeTestPlan(t, runtime.PlanFile, "one", "two")
		writeTestPolicy(t, runtime.ProjectsRoot, "owner/policy", "role \"platform\" { two }\n")
		resealTestPlan(t, runtime, "owner/policy")
		return nil
	})

	if _, err := prepareNativeLaunch(testRuntime, "claude"); err != nil {
		t.Fatal(err)
	}

	_, lease := onlyNativeLease(t, testRuntime)
	linked := make([]string, 0, len(lease.Artifacts))
	for _, artifact := range lease.Artifacts {
		linked = append(linked, filepath.Base(artifact.Repository))
	}
	if len(linked) != 2 {
		t.Fatalf("a regenerated launch linked %v, want both repositories", linked)
	}
}

func TestAMissingPolicySourceIsAMismatch(t *testing.T) {
	root := t.TempDir()
	testRuntime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, testRuntime.PlanFile)
	if err := os.RemoveAll(filepath.Join(testRuntime.ProjectsRoot, "owner", "policy")); err != nil {
		t.Fatal(err)
	}

	mismatches := verifyPlanProvenance(testRuntime, loadTestPlan(t, testRuntime))

	if len(mismatches) != 1 || !strings.Contains(mismatches[0].Reason, "missing") {
		t.Fatalf("a missing policy source produced %v", mismatches)
	}
}

// A checkout whose committed policy is behind the seal would hand the session
// policy newer than the plan that selected its repositories.
func TestAStalePolicyCheckoutIsCaughtAtTheWorktreeBase(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "policy")
	testRuntime := nativeTestRuntime(t, root)
	writeNativeTestPlan(t, testRuntime.PlanFile, "policy")
	sealed := filepath.Join(repository, ".agents", "roles.kdl")
	testGit(t, repository, "add", filepath.Join(".agents", "roles.kdl"))
	testGit(t, repository, "commit", "-m", "seal policy")
	testGit(t, repository, "push", "origin", "main")
	// Upstream moves on without the plan, exactly as a merged policy PR does.
	if err := os.WriteFile(sealed, []byte("role \"platform\" { newer }\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "commit", "-am", "newer policy")
	testGit(t, repository, "push", "origin", "main")
	if err := os.WriteFile(sealed, []byte("role \"platform\" {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	mismatches := verifyPlanProvenance(testRuntime, loadTestPlan(t, testRuntime))

	if len(mismatches) != 1 || !strings.Contains(mismatches[0].Reason, nativeWorktreeBase) {
		t.Fatalf("a stale policy checkout produced %v", mismatches)
	}
}

func TestRevisionDriftAloneIsReportedAndNotGated(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "policy")
	testRuntime := nativeTestRuntime(t, root)
	stderr := captureNativeStderr(t, &testRuntime)
	writeNativeTestPlan(t, testRuntime.PlanFile, "policy")
	testGit(t, repository, "add", filepath.Join(".agents", "roles.kdl"))
	testGit(t, repository, "commit", "-m", "seal policy")
	// An ordinary commit that leaves the policy byte-identical.
	if err := os.WriteFile(filepath.Join(repository, "unrelated.txt"), []byte("x\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", "unrelated.txt")
	testGit(t, repository, "commit", "-m", "unrelated work")
	testGit(t, repository, "push", "origin", "main")

	mismatches := verifyPlanProvenance(testRuntime, loadTestPlan(t, testRuntime))

	if len(mismatches) != 0 {
		t.Fatalf("revision drift gated a launch whose policy never moved: %v", mismatches)
	}
	if report := stderr(); !strings.Contains(report, "unchanged") {
		t.Fatalf("revision drift was not reported: %q", report)
	}
}

func TestALegacyJSONPlanWarnsWithARemovalBoundary(t *testing.T) {
	root := t.TempDir()
	testRuntime := nativeTestRuntime(t, root)
	stderr := captureNativeStderr(t, &testRuntime)
	testRuntime.PlanFile = writeLegacyRepositoryPlan(t, testRuntime.ProjectsRoot, "owner/one")

	plan, err := verifiedRepositoryPlan(testRuntime)

	if err != nil {
		t.Fatal(err)
	}
	if !plan.Unverified {
		t.Fatal("a plan that seals no provenance reported itself verified")
	}
	report := stderr()
	if !strings.Contains(report, legacyRepositoryPlanRemoval) ||
		!strings.Contains(report, agentComposeRepositoryPlanJSONFormat) {
		t.Fatalf("the legacy plan warning names no removal boundary: %q", report)
	}
}

// Regeneration must rewrite the plan AOS just read. A shadow that composes into
// its own HOME leaves the canonical plan stale.
func TestRegenerationTargetsTheHomeThatOwnsThePlan(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	plan := filepath.Join(home, ".agent-compose", "repository-plan.yaml")
	if got := repositoryPlanHome(plan, "/fallback"); got != home {
		t.Fatalf("plan home = %q, want %q", got, home)
	}
	if got := repositoryPlanHome("/elsewhere/plan.yaml", "/fallback"); got != "/fallback" {
		t.Fatalf("overridden plan home = %q, want the runtime home", got)
	}
}

func loadTestPlan(t *testing.T, runtime nativeRuntime) aosRepositoryPlan {
	t.Helper()
	plan, err := loadAOSRepositoryPlan(runtime.PlanFile)
	if err != nil {
		t.Fatal(err)
	}
	return plan
}

// resealTestPlan rewrites the sealed digest to whatever the policy file now
// holds, which is what a real Agent Compose run does.
func resealTestPlan(t *testing.T, runtime nativeRuntime, identity string) {
	t.Helper()
	policy := filepath.Join(runtime.ProjectsRoot, filepath.FromSlash(identity), ".agents", "roles.kdl")
	body, err := os.ReadFile(policy)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(runtime.PlanFile)
	if err != nil {
		t.Fatal(err)
	}
	sealed := fmt.Sprintf("sha256:%x", sha256.Sum256(body))
	stale := loadTestPlan(t, runtime).Inputs[0].Policy.SHA256
	if err := os.WriteFile(runtime.PlanFile,
		[]byte(strings.ReplaceAll(string(raw), stale, sealed)), 0o644); err != nil {
		t.Fatal(err)
	}
}

func assertNoNativeSessionWorktree(t *testing.T, runtime nativeRuntime) {
	t.Helper()
	entries, err := os.ReadDir(runtime.SessionsRoot)
	if err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("a stopped launch left %d session roots behind", len(entries))
	}
}
