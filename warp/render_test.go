package main

import (
	"os"
	"strings"
	"testing"
)

func TestProfileUsesNativePowerShellEnvironment(t *testing.T) {
	data := templateData{
		RepoRoot:    "X:/projects/coilyco-flight-deck/agentic-os",
		ProjectsDir: "X:/projects",
		StartupDir:  "X:/projects/coilysiren/coilysiren",
	}
	rendered, err := render("profile.ps1.tmpl", data)
	if err != nil {
		t.Fatalf("render(profile.ps1.tmpl): %v", err)
	}
	got := string(rendered)
	if !strings.Contains(got, "Set-Location -Path 'X:/projects/coilysiren/coilysiren'") {
		t.Fatalf("profile should land in StartupDir, got:\n%s", got)
	}
	if !strings.Contains(got, "$_commonShellPath = 'X:/projects/coilyco-flight-deck/agentic-os/shell/common.sh'") {
		t.Fatalf("profile should read shared exports from RepoRoot, got:\n%s", got)
	}
	if !strings.Contains(got, "$env:WARD_LOCKDOWN_ROOT = 'X:/projects'") {
		t.Fatalf("profile should keep lockdown at ProjectsDir")
	}
	for _, forbidden := range []string{"bash.exe", "--norc", "--noprofile", "source '"} {
		if strings.Contains(got, forbidden) {
			t.Fatalf("profile should not launch Bash, found %q", forbidden)
		}
	}
}

func TestCommonShellSharedEnvironmentBlockIsDeclarative(t *testing.T) {
	commonShell, err := os.ReadFile("../shell/common.sh")
	if err != nil {
		t.Fatalf("read common.sh: %v", err)
	}
	text := string(commonShell)
	start := strings.Index(text, "# shared-environment: begin")
	end := strings.Index(text, "# shared-environment: end")
	if start < 0 || end <= start {
		t.Fatal("common.sh should contain the ordered shared-environment markers")
	}
	exports := 0
	for _, line := range strings.Split(text[start:end], "\n") {
		if strings.HasPrefix(line, "export ") {
			exports++
			continue
		}
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		t.Fatalf("shared environment block must stay declarative, got %q", line)
	}
	if exports == 0 {
		t.Fatal("shared environment block should contain exports")
	}
}

// The cleared name sat inside the exports block, where the PowerShell loader
// skipped it, so Windows never cleared it at all. agentic-os#849
func TestCommonShellClearBlockCarriesOnlyUnsetNames(t *testing.T) {
	commonShell, err := os.ReadFile("../shell/common.sh")
	if err != nil {
		t.Fatalf("read common.sh: %v", err)
	}
	text := string(commonShell)
	start := strings.Index(text, "# shared-environment-clear: begin")
	end := strings.Index(text, "# shared-environment-clear: end")
	if start < 0 || end <= start {
		t.Fatal("common.sh should contain the ordered shared-environment-clear markers")
	}
	unsets := 0
	for _, line := range strings.Split(text[start:end], "\n") {
		if strings.HasPrefix(line, "unset ") {
			unsets++
			continue
		}
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		t.Fatalf("clear block takes bare unset names, got %q", line)
	}
	if unsets == 0 {
		t.Fatal("clear block should clear at least one name")
	}
}

func TestRenderedProfileClearsWhatCommonShellUnsets(t *testing.T) {
	// Unix sources common.sh, so its unset runs. Windows renders a profile
	// instead, and until it parsed this block the two platforms disagreed.
	rendered, err := render("profile.ps1.tmpl", templateData{
		RepoRoot:    "X:/projects/coilyco-flight-deck/agentic-os",
		ProjectsDir: "X:/projects",
		StartupDir:  "X:/projects/coilysiren/coilysiren",
	})
	if err != nil {
		t.Fatalf("render(profile.ps1.tmpl): %v", err)
	}
	got := string(rendered)

	for _, want := range []string{
		"'# shared-environment-clear: begin'",
		"^unset ([A-Za-z_][A-Za-z0-9_]*)$",
		"SetEnvironmentVariable($Matches[1], $null, 'Process')",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("rendered profile does not clear unset names, missing %q", want)
		}
	}
}

// A `break` here made block order decide which block is read, and the losing
// one vanished with no error and no empty value (agentic-os#1208).
func TestProfileLoaderReadsBothBlocksInEitherOrder(t *testing.T) {
	rendered, err := render("profile.ps1.tmpl", templateData{RepoRoot: "X:/repo"})
	if err != nil {
		t.Fatalf("render(profile.ps1.tmpl): %v", err)
	}
	loop := string(rendered)
	start := strings.Index(loop, "foreach ($_line in")
	if start < 0 {
		t.Fatal("profile should read common.sh line by line")
	}
	body := loop[start:]
	if end := strings.Index(body, "\n    }\n"); end > 0 {
		body = body[:end]
	}
	if strings.Contains(body, "break") {
		t.Fatalf("the marker loop must not break, or block order decides "+
			"which block is read:\n%s", body)
	}
	for _, marker := range []string{
		"# shared-environment: end",
		"# shared-environment-clear: end",
	} {
		i := strings.Index(body, marker)
		if i < 0 {
			t.Fatalf("profile should handle %q", marker)
		}
		if !strings.Contains(body[i:min(i+160, len(body))], "$false") {
			t.Fatalf("%q should clear its flag rather than stop the read", marker)
		}
	}
}
