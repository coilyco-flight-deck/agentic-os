package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func machOFixture(t *testing.T, dir, name string) string {
	t.Helper()
	path := filepath.Join(dir, name)
	// The first four bytes are the whole test: a 64-bit little-endian Mach-O.
	if err := os.WriteFile(path, []byte{0xcf, 0xfa, 0xed, 0xfe, 0x00}, 0o755); err != nil {
		t.Fatalf("write the binary fixture: %v", err)
	}
	// A temporary directory reaches the caller through /var, and resolution
	// answers in /private/var, so the fixture answers there too.
	resolved, err := filepath.EvalSymlinks(path)
	if err != nil {
		t.Fatalf("resolve the binary fixture: %v", err)
	}
	return resolved
}

// Homebrew's kitty cask installs a shell script on PATH. Linking a bundle at
// that script hands the window back to kitty.app, which is the whole defect.
func TestResolveTerminalTargetFollowsACaskWrapperToItsBinary(t *testing.T) {
	root := t.TempDir()
	real := machOFixture(t, root, "kitty-real")
	wrapper := filepath.Join(root, "kitty")
	script := "#!/bin/bash\nexec \"" + real + "\"  \"$@\"\n"
	if err := os.WriteFile(wrapper, []byte(script), 0o755); err != nil {
		t.Fatalf("write the wrapper: %v", err)
	}
	got, err := resolveTerminalTarget(wrapper)
	if err != nil {
		t.Fatalf("resolve: %v", err)
	}
	if got != real {
		t.Fatalf("resolved %q, want the binary the wrapper execs", got)
	}
}

func TestResolveTerminalTargetPassesABinaryThrough(t *testing.T) {
	root := t.TempDir()
	real := machOFixture(t, root, "kitty")
	got, err := resolveTerminalTarget(real)
	if err != nil {
		t.Fatalf("resolve: %v", err)
	}
	if got != real {
		t.Fatalf("resolved %q, want %q", got, real)
	}
}

// A wrapper this cannot follow has to say so. Linking it anyway would look
// like it worked and leave every window credited to the terminal.
func TestResolveTerminalTargetRefusesAScriptItCannotFollow(t *testing.T) {
	root := t.TempDir()
	wrapper := filepath.Join(root, "kitty")
	if err := os.WriteFile(wrapper, []byte("#!/bin/sh\necho hello\n"), 0o755); err != nil {
		t.Fatalf("write the wrapper: %v", err)
	}
	if _, err := resolveTerminalTarget(wrapper); err == nil {
		t.Fatal("a script naming no binary should be an error rather than a link")
	}
}

// The window carries the identity of the bundle holding the binary that drew
// it, so `aterm platform` from a shell opens through the installed app too.
func TestBundleTerminalPrefersTheRolesInstalledApp(t *testing.T) {
	for _, dir := range []string{"Applications", "Desktop"} {
		t.Run(dir, func(t *testing.T) { bundleTerminalCase(t, dir, false) })
		t.Run(dir+" from a shadow", func(t *testing.T) { bundleTerminalCase(t, dir, true) })
	}
}

// bundleTerminalCase installs a role's app under dir in Kai's home. From a
// shadow, HOME is the session's and the canonical home is where the app is.
func bundleTerminalCase(t *testing.T, dir string, shadowed bool) {
	root := t.TempDir()
	t.Setenv("HOME", root)
	for _, name := range []string{nativeSessionEnv, nativeSessionRootEnv, canonicalHomeEnv, canonicalProjectsEnv} {
		t.Setenv(name, "")
	}
	if shadowed {
		t.Setenv("HOME", t.TempDir())
		t.Setenv(nativeSessionEnv, "ab12")
		t.Setenv(nativeSessionRootEnv, t.TempDir())
		t.Setenv(canonicalHomeEnv, root)
		t.Setenv(canonicalProjectsEnv, filepath.Join(root, "projects"))
	}
	apps := filepath.Join(root, dir)
	bundle := filepath.Join(apps, "Angie :: Agentic Platform Engineer.app", "Contents", "MacOS")
	if err := os.MkdirAll(bundle, 0o755); err != nil {
		t.Fatalf("stage the bundle: %v", err)
	}
	launcher := filepath.Join(bundle, "aterm-platform")
	if err := os.WriteFile(launcher, []byte("#!/bin/sh\n"+bundleMarker+"\n"), 0o755); err != nil {
		t.Fatalf("write the launcher: %v", err)
	}
	plist := bundleInfoPlist(testSpec())
	if err := os.WriteFile(filepath.Join(filepath.Dir(bundle), "Info.plist"), []byte(plist), 0o644); err != nil {
		t.Fatalf("write the plist: %v", err)
	}
	machOFixture(t, bundle, bundleTerminalName)
	terminal := filepath.Join(bundle, bundleTerminalName)
	if got := bundleTerminal("eng-platform"); got != terminal {
		t.Fatalf("bundleTerminal = %q, want %q", got, terminal)
	}
	if got := bundleTerminal("sysadmin"); got != "" {
		t.Fatalf("a role with no installed app should fall back, got %q", got)
	}
}

// A window launched from a seat bundle exports that bundle's own kitty as
// ATERM_TERMINAL_BIN, so the plan bakes the resolved target instead of it.
func TestResolveTerminalTargetLeavesTheGeneratingBundleBehind(t *testing.T) {
	root := t.TempDir()
	app := filepath.Join(root, "kitty.app", "Contents", "MacOS")
	seat := filepath.Join(root, "Evie :: Applied Scientist.app", "Contents", "MacOS")
	for _, dir := range []string{app, seat} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatalf("make %s: %v", dir, err)
		}
	}
	real := machOFixture(t, app, bundleTerminalName)
	link := filepath.Join(seat, bundleTerminalName)
	if err := os.Symlink(real, link); err != nil {
		t.Fatalf("link the seat terminal: %v", err)
	}
	// Resolving the seat's own symlink is what keeps one bundle out of the
	// other seven; the generating seat's path must not survive.
	got, err := resolveTerminalTarget(link)
	if err != nil {
		t.Fatalf("resolve: %v", err)
	}
	if got != real {
		t.Fatalf("resolved %q, want the app %q", got, real)
	}
}

func TestWindowEnvironDropsTheLaunchingBundlesTerminal(t *testing.T) {
	got := windowEnviron([]string{"PATH=/bin", terminalBinEnv + "=/Apps/Platform Engineer.app/Contents/MacOS/kitty", "AOS_BIN=/bin/aos"})
	if strings.Join(got, "|") != "PATH=/bin|AOS_BIN=/bin/aos" {
		t.Fatalf("windowEnviron = %v, want only the bundle's terminal gone", got)
	}
}
