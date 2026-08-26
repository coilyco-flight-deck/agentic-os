package main

import (
	"context"
	"fmt"
	"strings"
	"testing"
)

// A window manager truncates near here, so this is the budget the ordering is
// competing for rather than a limit aterm enforces.
const truncatedRunes = 30

func head(title string, runes int) string {
	if trimmed := []rune(title); len(trimmed) > runes {
		return string(trimmed[:runes])
	}
	return title
}

// The workspace is the only thing separating two windows of the same role, so
// it leads and the expression every window repeats trails.
func TestTitleLeadsWithTheWorkspaceAndTrailsWithWhatRepeats(t *testing.T) {
	document := platformOverlay(t)
	title, err := buildTitle(document, "", "agentic-os@main")
	if err != nil {
		t.Fatalf("build title: %v", err)
	}
	if !strings.HasPrefix(title, "agentic-os@main"+titleSeparator) {
		t.Fatalf("title = %q, want the workspace first", title)
	}
	if !strings.HasSuffix(title, titleSeparator+document.Expression) {
		t.Fatalf("title = %q, want the expression last", title)
	}
	role := strings.Index(title, document.RoleDisplayName)
	name := strings.Index(title, document.Seat.Name)
	if role < 0 || name < 0 || role > name {
		t.Fatalf("title = %q, want the role before the seat name", title)
	}
}

// The defect: two windows differing only by workspace used to be byte-identical.
func TestTruncatedTitlesSeparateTwoWindowsOfTheSameRole(t *testing.T) {
	document := platformOverlay(t)
	first, err := buildTitle(document, "", "agentic-os@main")
	if err != nil {
		t.Fatalf("build title: %v", err)
	}
	second, err := buildTitle(document, "", "ward@main")
	if err != nil {
		t.Fatalf("build title: %v", err)
	}
	if head(first, truncatedRunes) == head(second, truncatedRunes) {
		t.Fatalf("both windows truncate to %q", head(first, truncatedRunes))
	}
}

// With no workspace to name, the role takes the front rather than a glyph pair
// and a seat name that only the identity card needs to spell out.
func TestTitleWithoutAWorkspaceLeadsWithTheRole(t *testing.T) {
	document := platformOverlay(t)
	title, err := buildTitle(document, "", "")
	if err != nil {
		t.Fatalf("build title: %v", err)
	}
	if !strings.HasPrefix(title, document.RoleDisplayName+titleSeparator) {
		t.Fatalf("title = %q, want the role first", title)
	}
}

// A caller-supplied task title is the most specific thing anyone said about
// this window, so it sits behind only the workspace.
func TestTaskTitleSitsBehindTheWorkspace(t *testing.T) {
	title, err := buildTitle(platformOverlay(t), "aterm#1252", "agentic-os@main")
	if err != nil {
		t.Fatalf("build title: %v", err)
	}
	if !strings.HasPrefix(title, "agentic-os@main // aterm#1252 // ") {
		t.Fatalf("title = %q", title)
	}
}

func gitDeps(t *testing.T, toplevel, branch string, found bool) commandDeps {
	t.Helper()
	return commandDeps{
		lookPath: func(name string) (string, error) {
			if name == "git" && found {
				return "/stub/git", nil
			}
			return "", fmt.Errorf("%s not found", name)
		},
		output: func(_ context.Context, _ string, args ...string) ([]byte, error) {
			switch {
			case indexOf(args, "--show-toplevel") >= 0:
				if toplevel == "" {
					return nil, fmt.Errorf("not a git repository")
				}
				return []byte(toplevel + "\n"), nil
			case indexOf(args, "symbolic-ref") >= 0:
				if branch == "" {
					return nil, fmt.Errorf("detached")
				}
				return []byte(branch + "\n"), nil
			}
			return nil, fmt.Errorf("unexpected git call: %v", args)
		},
	}
}

func TestWorkspaceLabelNamesTheCheckoutOrStaysQuiet(t *testing.T) {
	cases := map[string]struct {
		deps   commandDeps
		chosen bool
		want   string
	}{
		"checkout on a branch": {gitDeps(t, "/p/coilyco/agentic-os", "main", true), false, "agentic-os@main"},
		"detached checkout":    {gitDeps(t, "/p/coilyco/agentic-os", "", true), false, "agentic-os"},
		"chosen plain dir":     {gitDeps(t, "", "", true), true, "projects"},
		"default plain dir":    {gitDeps(t, "", "", true), false, ""},
		"no git on PATH":       {gitDeps(t, "/p/x", "main", false), false, ""},
	}
	for name, want := range cases {
		t.Run(name, func(t *testing.T) {
			got := workspaceLabel(context.Background(), want.deps, "/home/kai/projects", want.chosen)
			if got != want.want {
				t.Fatalf("workspace = %q, want %q", got, want.want)
			}
		})
	}
}
