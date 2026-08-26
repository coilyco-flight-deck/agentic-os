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
		WorkingDirectory: "/Users/kai/projects",
		ATermBin:         "/opt/homebrew/bin/aterm",
		AOSBin:           "/Users/kai/.local/bin/aos",
		AgentComposeBin:  "/opt/homebrew/bin/agent-compose",
		TerminalBin:      "/Applications/kitty.app/Contents/MacOS/kitty",
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
func TestStaleBundlesNamesARetiredRoleAndLeavesAForeignAppAlone(t *testing.T) {
	root := t.TempDir()
	retired := writeFixtureBundle(t, root, "aterm retired", "#!/bin/sh\n"+bundleMarker+"\n")
	writeFixtureBundle(t, root, "aterm platform", "#!/bin/sh\n"+bundleMarker+"\n")
	writeFixtureBundle(t, root, "aterm notmine", "#!/bin/sh\nexit 0\n")
	roster := rosterDocument{Items: []rosterRole{{Slug: "platform"}}}
	stale := staleBundles(root, roster)
	if len(stale) != 1 || stale[0] != retired {
		t.Fatalf("only the retired generated bundle is stale, got %v", stale)
	}
}

func TestReplaceableGuardsAnAppThisCommandDidNotWrite(t *testing.T) {
	root := t.TempDir()
	mine := writeFixtureBundle(t, root, "aterm platform", "#!/bin/sh\n"+bundleMarker+"\n")
	theirs := writeFixtureBundle(t, root, "aterm sysadmin", "#!/bin/sh\nexit 0\n")
	if err := replaceable(mine); err != nil {
		t.Fatalf("regenerating our own bundle should be allowed: %v", err)
	}
	if err := replaceable(theirs); err == nil {
		t.Fatal("an app this command did not write should stay untouched")
	}
	if err := replaceable(filepath.Join(root, "aterm absent.app")); err != nil {
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
		Executable: spec.name(),
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
		Items: []bundleItem{
			{Role: "platform", Person: "Angie", Path: "/Users/kai/Applications/aterm platform.app"},
		},
		Stale: []string{"/Users/kai/Applications/aterm retired.app"},
	}
	rendered := &strings.Builder{}
	if err := renderBundlePlan(rendered, plan); err != nil {
		t.Fatalf("render: %v", err)
	}
	for _, want := range []string{"/Users/kai/Applications", "platform", "Angie", "retired"} {
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
