package main

import "os"

// defaultShellStorageKey is the generic_string_objects key for Warp's Windows
// default shell. It is inferred and unverified - see docs/warp.md.
const defaultShellStorageKey = "DefaultShell"

// windowsPwshCandidates lists the standard, public-safe PowerShell 7 install
// locations. resolvePwshProfile in render.go shares the same list.
func windowsPwshCandidates() []string {
	return []string{
		`C:\Program Files\PowerShell\7\pwsh.exe`,
		`C:\Program Files\PowerShell\7-preview\pwsh.exe`,
	}
}

// resolveWindowsDefaultShell returns the path to the first PowerShell 7 binary
// on disk, or "" when none is installed (apply/doctor then skip the layer).
func resolveWindowsDefaultShell() string {
	return firstExistingFile(windowsPwshCandidates())
}

// firstExistingFile returns the first candidate that exists as a regular file,
// or "" when none match. Empty candidates are skipped.
func firstExistingFile(candidates []string) string {
	for _, c := range candidates {
		if c == "" {
			continue
		}
		if info, err := os.Stat(c); err == nil && !info.IsDir() {
			return c
		}
	}
	return ""
}
