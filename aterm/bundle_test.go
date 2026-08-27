package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func testSpec() bundleSpec {
	return bundleSpec{
		Role:             "platform",
		DisplayName:      "Agentic Platform Engineer",
		Person:           "Angie",
		Version:          "1.2.3",
		BakedPath:        "/opt/homebrew/bin:/usr/bin:/bin",
		WorkingDirectory: "/Users/kai/projects",
		ATermBin:         "/opt/homebrew/bin/aterm",
		AOSBin:           "/Users/kai/.local/bin/aos",
		AgentComposeBin:  "/opt/homebrew/bin/agent-compose",
		TerminalBin:      "/Applications/kitty.app/Contents/MacOS/kitty",
	}
}

// `agent-compose launch` resolves the harness off PATH, so pinning the three
// binaries aterm itself needs still left "claude not found" after shadow init.
func TestBundleLauncherRebuildsPathRatherThanOnlyPinningBinaries(t *testing.T) {
	launcher := bundleLauncher(testSpec())
	if !strings.Contains(launcher, "/opt/homebrew/bin:/usr/bin:/bin") {
		t.Fatalf("the generation-time PATH should be baked in as the fallback:\n%s", launcher)
	}
	if !strings.Contains(launcher, "/bin/zsh -lc") {
		t.Fatalf("a login shell should supply the current PATH:\n%s", launcher)
	}
	if !strings.Contains(launcher, "export PATH") {
		t.Fatalf("PATH has to be exported to reach the harness:\n%s", launcher)
	}
}

// A Finder launch starts on a login PATH carrying none of these, so a bare name
// in the wrapper is the failure this bundle is generated rather than written.
func TestBundleLauncherBakesInEveryResolvedBinary(t *testing.T) {
	launcher := bundleLauncher(testSpec())
	for _, binary := range []string{
		"/opt/homebrew/bin/aterm",
		"/Users/kai/.local/bin/aos",
		"/opt/homebrew/bin/agent-compose",
		"/Applications/kitty.app/Contents/MacOS/kitty",
	} {
		if !strings.Contains(launcher, binary) {
			t.Fatalf("the launcher should bake in %q:\n%s", binary, launcher)
		}
	}
}

// aterm stops reading flags at the first positional, so a working directory
// after the role would reach the harness as an argument instead.
func TestBundleLauncherPutsTheWorkingDirectoryBeforeTheRole(t *testing.T) {
	launcher := bundleLauncher(testSpec())
	directory := strings.Index(launcher, "--working-directory")
	role := strings.Index(launcher, "'platform'")
	if directory < 0 || role < 0 {
		t.Fatalf("the launcher should carry both the flag and the role:\n%s", launcher)
	}
	if directory > role {
		t.Fatalf("the working directory should precede the role:\n%s", launcher)
	}
}

func TestBundleLauncherQuotesAPathHoldingASingleQuote(t *testing.T) {
	spec := testSpec()
	spec.WorkingDirectory = "/Users/kai/kai's projects"
	if !strings.Contains(bundleLauncher(spec), `'/Users/kai/kai'\''s projects'`) {
		t.Fatal("the quote should be escaped rather than closing the string")
	}
}

// The wrapper exits as soon as the window is detached, so a Dock tile of its
// own would flicker while the session it opened keeps running.
func TestBundleInfoPlistKeepsTheWrapperOffTheDock(t *testing.T) {
	plist := bundleInfoPlist(testSpec())
	if !strings.Contains(plist, "<key>LSUIElement</key>\n\t<true/>") {
		t.Fatalf("the wrapper should declare LSUIElement:\n%s", plist)
	}
}

func TestBundleInfoPlistGivesEachRoleItsOwnIdentifier(t *testing.T) {
	second := testSpec()
	second.Role = "sysadmin"
	if !strings.Contains(bundleInfoPlist(testSpec()), "me.coilysiren.aterm.platform") {
		t.Fatal("the identifier should carry the role")
	}
	if strings.Contains(bundleInfoPlist(second), "me.coilysiren.aterm.platform") {
		t.Fatal("two roles sharing an identifier would collide in LaunchServices")
	}
}

func TestBundleInfoPlistEscapesTheIdentityLine(t *testing.T) {
	spec := testSpec()
	spec.DisplayName = "Research & Development"
	if !strings.Contains(bundleInfoPlist(spec), "Research &amp; Development") {
		t.Fatal("the display name should be XML-escaped")
	}
}

func TestBundleInfoPlistNamesAnIconOnlyWhenThereIsOne(t *testing.T) {
	if strings.Contains(bundleInfoPlist(testSpec()), "CFBundleIconFile") {
		t.Fatal("without an icon the bundle should fall back to the system one")
	}
	spec := testSpec()
	spec.Icon = true
	if !strings.Contains(bundleInfoPlist(spec), "CFBundleIconFile") {
		t.Fatal("an icon should be named in the plist")
	}
}

func writeFixtureBundle(t *testing.T, root, name, body string) string {
	t.Helper()
	path := filepath.Join(root, name+".app")
	executable := filepath.Join(path, "Contents", "MacOS", name)
	if err := os.MkdirAll(filepath.Dir(executable), 0o755); err != nil {
		t.Fatalf("create the fixture: %v", err)
	}
	if err := os.WriteFile(executable, []byte(body), 0o755); err != nil {
		t.Fatalf("write the fixture: %v", err)
	}
	return path
}

// A slug that turned over leaves a tile opening nothing, and its refusal only
// fires once someone clicks it. Naming it at generation is the earlier warning.
func TestStaleBundlesNamesWhatThisRunNoLongerWritesAndSkipsAForeignApp(t *testing.T) {
	root := t.TempDir()
	retired := writeFixtureBundle(t, root, "Rex :: Retired Role", "#!/bin/sh\n"+bundleMarker+"\n")
	kept := writeFixtureBundle(t, root, "Angie :: Agentic Platform Engineer",
		"#!/bin/sh\n"+bundleMarker+"\n")
	writeFixtureBundle(t, root, "Some Other App", "#!/bin/sh\nexit 0\n")
	stale := staleBundles(root, map[string]bool{kept: true})
	if len(stale) != 1 || stale[0] != retired {
		t.Fatalf("only the bundle this run no longer writes is stale, got %v", stale)
	}
}

// The scheme renamed once already. Matching on a filename would have orphaned
// every bundle the previous release wrote instead of reporting it.
func TestStaleBundlesFindsABundleWrittenUnderTheOldNamingScheme(t *testing.T) {
	root := t.TempDir()
	old := writeFixtureBundle(t, root, "aterm platform", "#!/bin/sh\n"+bundleMarker+"\n")
	stale := staleBundles(root, map[string]bool{})
	if len(stale) != 1 || stale[0] != old {
		t.Fatalf("an old-scheme bundle should still be recognized as ours, got %v", stale)
	}
}

func TestReplaceableGuardsAnAppThisCommandDidNotWrite(t *testing.T) {
	root := t.TempDir()
	mine := writeFixtureBundle(t, root, "Angie :: Agentic Platform Engineer",
		"#!/bin/sh\n"+bundleMarker+"\n")
	theirs := writeFixtureBundle(t, root, "Vera :: Systems Administrator",
		"#!/bin/sh\nexit 0\n")
	if err := replaceable(mine); err != nil {
		t.Fatalf("regenerating our own bundle should be allowed: %v", err)
	}
	if err := replaceable(theirs); err == nil {
		t.Fatal("an app this command did not write should stay untouched")
	}
	if err := replaceable(filepath.Join(root, "Nobody.app")); err != nil {
		t.Fatalf("a missing bundle is not a conflict: %v", err)
	}
}

func TestWriteBundleProducesAnExecutableLauncherAndAValidLayout(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("the bundle layout is macOS only")
	}
	spec := testSpec()
	item := bundleItem{
		Role:       spec.Role,
		Person:     spec.Person,
		Identifier: spec.identifier(),
		Path:       filepath.Join(t.TempDir(), spec.name()+".app"),
		Executable: spec.executable(),
		Launcher:   bundleLauncher(spec),
		Plist:      bundleInfoPlist(spec),
	}
	if err := writeBundle(item, ""); err != nil {
		t.Fatalf("write the bundle: %v", err)
	}
	info, err := os.Stat(filepath.Join(item.Path, "Contents", "MacOS", item.Executable))
	if err != nil {
		t.Fatalf("stat the launcher: %v", err)
	}
	if info.Mode().Perm()&0o111 == 0 {
		t.Fatalf("the launcher must be executable, got %v", info.Mode().Perm())
	}
	if _, err := os.Stat(filepath.Join(item.Path, "Contents", "Info.plist")); err != nil {
		t.Fatalf("stat the plist: %v", err)
	}
}

// `--dry-run` renders for a person and `--dry-run --json` carries the machine
// plan, matching what the launcher's own dry run does. See docs/aterm.md.
func TestRenderBundlePlanNamesEveryBundleAndItsStaleLeftovers(t *testing.T) {
	plan := bundlePlan{
		Output: "/Users/kai/Applications",
		Items: []bundleItem{{
			Role:   "platform",
			Person: "Angie",
			Name:   "Angie // Agentic Platform Engineer",
			Path:   "/Users/kai/Applications/Angie :: Agentic Platform Engineer.app",
		}},
		Stale: []string{"/Users/kai/Applications/Rex :: Retired.app"},
	}
	rendered := &strings.Builder{}
	if err := renderBundlePlan(rendered, plan); err != nil {
		t.Fatalf("render: %v", err)
	}
	// The rendered name is the one the Dock draws, not the one on disk.
	for _, want := range []string{"/Users/kai/Applications", "platform",
		"Angie // Agentic Platform Engineer", "Retired"} {
		if !strings.Contains(rendered.String(), want) {
			t.Fatalf("the rendered plan should name %q:\n%s", want, rendered)
		}
	}
	if strings.Contains(rendered.String(), "\"format\"") {
		t.Fatal("the rendered plan is for a person, not the JSON one")
	}
}

func TestRenderBundlePlanSaysWhenThereIsNoIcon(t *testing.T) {
	rendered := &strings.Builder{}
	if err := renderBundlePlan(rendered, bundlePlan{Output: "/tmp"}); err != nil {
		t.Fatalf("render: %v", err)
	}
	if !strings.Contains(rendered.String(), "system app icon") {
		t.Fatalf("an absent icon should be named rather than blank:\n%s", rendered)
	}
}

// Kai asked for "Angie // Agentic Platform Engineer", and a POSIX filename
// cannot hold a slash. macOS renders a stored colon as one, so it round-trips.
func TestBundleNameStoresTheHouseSeparatorAsMacOSRendersIt(t *testing.T) {
	spec := testSpec()
	if got := spec.name(); got != "Angie :: Agentic Platform Engineer" {
		t.Fatalf("on-disk name is %q", got)
	}
	if got := spec.displayName(); got != "Angie // Agentic Platform Engineer" {
		t.Fatalf("displayed name is %q", got)
	}
	if strings.Contains(spec.name(), "/") {
		t.Fatal("a slash in the basename would read as a path separator")
	}
}

// A display name reaching the filesystem is the one place a stray slash could
// still arrive, since the roster is not this binary's to constrain.
func TestBundleNameNeutralizesASlashComingFromTheRoster(t *testing.T) {
	spec := testSpec()
	spec.DisplayName = "Research/Development"
	if strings.Contains(spec.name(), "/") {
		t.Fatalf("the roster's slash should not survive into the basename: %q", spec.name())
	}
}

func TestBundleInfoPlistCarriesTheDisplayNameAndAPlainExecutable(t *testing.T) {
	plist := bundleInfoPlist(testSpec())
	if !strings.Contains(plist, "Angie // Agentic Platform Engineer") {
		t.Fatalf("the plist should carry the rendered name:\n%s", plist)
	}
	if !strings.Contains(plist, "<string>aterm-platform</string>") {
		t.Fatalf("the executable should stay a plain slug:\n%s", plist)
	}
}

// A generating session's scratch directories must not outlive it inside seven
// bundles, and a duplicate entry is noise in a file a person may read.
func TestLivePathEntriesKeepsOnlyRealDirectoriesAndDropsRepeats(t *testing.T) {
	real := t.TempDir()
	file := filepath.Join(real, "not-a-dir")
	if err := os.WriteFile(file, []byte("x"), 0o644); err != nil {
		t.Fatalf("write: %v", err)
	}
	joined := strings.Join([]string{real, "/nope/gone", file, real, ""},
		string(filepath.ListSeparator))
	got := livePathEntries(joined)
	if got != real {
		t.Fatalf("only the real directory should survive, got %q", got)
	}
}

// Kai's window options landed while the installed aterm stayed three releases
// back, so half the fix worked and nothing said why. See docs/aterm.md.
func TestBundlePlanWarnsWhenTheBundlesCallADifferentBuild(t *testing.T) {
	plan := bundlePlan{
		Output:        "/Users/kai/Applications",
		Launcher:      "/opt/homebrew/bin/aterm",
		LauncherBuild: "aos-v0.231.0",
		Build:         "aos-v0.242.0",
		Items:         []bundleItem{{Role: "platform", Name: "Angie // X"}},
	}
	if !plan.staleLauncher() {
		t.Fatal("a bundle calling an older aterm carries only what that one does")
	}
	written := &strings.Builder{}
	if err := announceBundles(written, plan); err != nil {
		t.Fatalf("announce: %v", err)
	}
	for _, want := range []string{"aos-v0.231.0", "aos-v0.242.0", "/opt/homebrew/bin/aterm"} {
		if !strings.Contains(written.String(), want) {
			t.Fatalf("the warning should name %q:\n%s", want, written)
		}
	}
	rendered := &strings.Builder{}
	if err := renderBundlePlan(rendered, plan); err != nil {
		t.Fatalf("render: %v", err)
	}
	if !strings.Contains(rendered.String(), "aos-v0.231.0") {
		t.Fatalf("the rendered plan should warn too:\n%s", rendered)
	}
}

func TestBundlePlanStaysQuietWhenTheBuildsMatchOrAreUnknown(t *testing.T) {
	same := bundlePlan{LauncherBuild: "aos-v0.242.0", Build: "aos-v0.242.0"}
	if same.staleLauncher() {
		t.Fatal("matching builds are the normal case and earn no warning")
	}
	unknown := bundlePlan{LauncherBuild: "", Build: "aos-v0.242.0"}
	if unknown.staleLauncher() {
		t.Fatal("a version that could not be read is not evidence of a mismatch")
	}
}
