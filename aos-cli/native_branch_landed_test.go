package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// squashMerge lands a branch the way Forgejo's squash style does: one new
// commit on main carrying the whole diff, then the remote branch is deleted.
func squashMerge(t *testing.T, repository, branch string) {
	t.Helper()
	testGit(t, repository, "switch", "main")
	testGit(t, repository, "merge", "--squash", branch)
	testGit(t, repository, "commit", "-m", "squashed "+branch)
	testGit(t, repository, "push", "origin", "main")
	testGit(t, repository, "push", "origin", "--delete", branch)
	testGit(t, repository, "fetch", "--prune", "origin")
}

func commitFile(t *testing.T, repository, name, body string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(repository, name), []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	testGit(t, repository, "add", name)
	testGit(t, repository, "commit", "-m", "add "+name+" "+body)
}

// A squash rewrites every commit and the remote ref that would have proved the
// branch pushed is gone, so it was unreapable forever. agentic-os#1260
func TestASquashMergedBranchIsReapableOnceItsRemoteRefIsGone(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	testGit(t, repository, "switch", "-c", "aos/claude/aa44")
	commitFile(t, repository, "one.txt", "first")
	commitFile(t, repository, "two.txt", "second")
	testGit(t, repository, "push", "-u", "origin", "aos/claude/aa44")
	squashMerge(t, repository, "aos/claude/aa44")

	// Two commits squashed into one, so patch identity cannot see it landed.
	if unmerged := testGit(t, repository, "cherry", "origin/main", "aos/claude/aa44"); !strings.Contains(unmerged, "+") {
		t.Fatalf("the fixture is not a squash merge: git cherry said %q", unmerged)
	}
	if !nativeBranchLanded(repository, "aos/claude/aa44") {
		t.Fatal("a squash-merged branch whose remote ref is gone should be landed")
	}
	cleaned, err := deleteNativeBranchIfRemote(repository, "aos/claude/aa44")
	if err != nil || !cleaned {
		t.Fatalf("delete = %v, %v", cleaned, err)
	}
	if strings.Contains(testGit(t, repository, "for-each-ref", "--format=%(refname:short)", "refs/heads/"), "aa44") {
		t.Fatal("the branch survived")
	}
}

func TestBranchesWorthKeepingSurviveTheLandedTest(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")

	// Never pushed. Its commits may have no second copy anywhere.
	testGit(t, repository, "switch", "-c", "aos/claude/bb55")
	commitFile(t, repository, "local.txt", "local")
	testGit(t, repository, "switch", "main")
	if nativeBranchLanded(repository, "aos/claude/bb55") {
		t.Fatal("a branch that was never pushed must not count as landed")
	}

	// Pushed, then the remote ref went away, but main never took the change.
	testGit(t, repository, "switch", "-c", "aos/claude/cc66")
	commitFile(t, repository, "kept.txt", "kept")
	testGit(t, repository, "push", "-u", "origin", "aos/claude/cc66")
	testGit(t, repository, "push", "origin", "--delete", "aos/claude/cc66")
	testGit(t, repository, "fetch", "--prune", "origin")
	testGit(t, repository, "switch", "main")
	if nativeBranchLanded(repository, "aos/claude/cc66") {
		t.Fatal("an abandoned branch main never took must not count as landed")
	}
	cleaned, err := deleteNativeBranchIfRemote(repository, "aos/claude/cc66")
	if err != nil || cleaned {
		t.Fatalf("delete = %v, %v, want a refusal", cleaned, err)
	}

	// Landed, then main moved on and changed the same file back.
	testGit(t, repository, "switch", "-c", "aos/claude/dd77")
	commitFile(t, repository, "churn.txt", "branch")
	testGit(t, repository, "push", "-u", "origin", "aos/claude/dd77")
	squashMerge(t, repository, "aos/claude/dd77")
	commitFile(t, repository, "churn.txt", "reverted on main")
	testGit(t, repository, "push", "origin", "main")
	testGit(t, repository, "fetch", "origin")
	if nativeBranchLanded(repository, "aos/claude/dd77") {
		t.Fatal("a path main has since changed should err toward keeping")
	}
}

// squashFromUnpushed lands a branch as a seat does when it pushes work under
// another name: main takes the content, the session branch never had an upstream.
func squashFromUnpushed(t *testing.T, repository, branch string) {
	t.Helper()
	testGit(t, repository, "switch", "main")
	testGit(t, repository, "merge", "--squash", branch)
	testGit(t, repository, "commit", "-m", "squashed "+branch)
	testGit(t, repository, "push", "origin", "main")
	testGit(t, repository, "fetch", "origin")
}

// A never-pushed branch whose content main already holds loses nothing when
// reaped, so the sweep releases it rather than holding it forever. #8277
func TestANeverPushedBranchMainHoldsIsReleased(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	testGit(t, repository, "switch", "-c", "aos/claude/hh22")
	commitFile(t, repository, "one.txt", "first")
	squashFromUnpushed(t, repository, "aos/claude/hh22")

	if nativeBranchWasPushedAndPruned(repository, "aos/claude/hh22") {
		t.Fatal("the fixture pushed the branch, so it is not the never-pushed shape")
	}
	reading := inspectNativeArtifact(nativeArtifact{Repository: repository, Branch: "aos/claude/hh22"})
	if !reading.Releasable || reading.Held != "" {
		t.Fatalf("reading = %+v, want releasable", reading)
	}
}

// Main rewrote a line the branch touched. Landed-only holds it, and says why,
// so the person deciding can see main has everything else. #8277
func TestANeverPushedBranchMainRewroteIsHeldAndNamed(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	commitFile(t, repository, "f.txt", eightLines)
	testGit(t, repository, "push", "origin", "main")
	testGit(t, repository, "switch", "-c", "aos/claude/jj33")
	commitFile(t, repository, "f.txt", strings.Replace(eightLines, "line4", "line4-branch", 1))
	squashFromUnpushed(t, repository, "aos/claude/jj33")
	commitFile(t, repository, "f.txt", strings.Replace(eightLines, "line4", "line4-tuned", 1))
	testGit(t, repository, "push", "origin", "main")
	testGit(t, repository, "fetch", "origin")

	reading := inspectNativeArtifact(nativeArtifact{Repository: repository, Branch: "aos/claude/jj33"})
	if reading.Releasable || !strings.Contains(reading.Held, "hunks it rewrote") {
		t.Fatalf("reading = %+v, want held and named superseded", reading)
	}
}

func TestANeverPushedBranchWithItsOwnContentStaysHeld(t *testing.T) {
	root := t.TempDir()
	repository, _ := createNativeTestRepository(t, root, "owner", "one")
	testGit(t, repository, "switch", "-c", "aos/claude/kk44")
	commitFile(t, repository, "kept.txt", "kept")
	testGit(t, repository, "switch", "main")

	reading := inspectNativeArtifact(nativeArtifact{Repository: repository, Branch: "aos/claude/kk44"})
	if reading.Releasable || strings.Contains(reading.Held, "hunks it rewrote") {
		t.Fatalf("reading = %+v, want held as branch-only work", reading)
	}
}
