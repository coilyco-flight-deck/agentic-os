package main

import (
	"context"
	"path/filepath"
	"strings"
)

// workspaceLabel names the checkout the window will sit in. Two windows of the
// same role differ by nothing else. See docs/aterm.md.
func workspaceLabel(ctx context.Context, deps commandDeps, cwd string, chosen bool) string {
	if repository, branch, ok := gitCheckout(ctx, deps, cwd); ok {
		if branch == "" {
			return repository
		}
		return repository + "@" + branch
	}
	// The default projects root is the same for every window, so naming it
	// would put a constant back in the slot this ordering exists to fill.
	if !chosen {
		return ""
	}
	return filepath.Base(cwd)
}

func gitCheckout(ctx context.Context, deps commandDeps, cwd string) (string, string, bool) {
	git, err := requireBinary(deps.lookPath, "git")
	if err != nil {
		return "", "", false
	}
	read := func(args ...string) string {
		raw, err := deps.output(ctx, git, append([]string{"-C", cwd}, args...)...)
		if err != nil {
			return ""
		}
		return strings.TrimSpace(string(raw))
	}
	toplevel := read("rev-parse", "--show-toplevel")
	if toplevel == "" {
		return "", "", false
	}
	// A detached HEAD has no symbolic ref, which is a nameless branch rather
	// than a missing checkout, so the repository still names the window.
	return filepath.Base(toplevel), read("symbolic-ref", "--quiet", "--short", "HEAD"), true
}
