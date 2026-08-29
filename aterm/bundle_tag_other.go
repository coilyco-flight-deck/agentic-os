//go:build !darwin

package main

// Only macOS has Finder tags, and only macOS grows .app bundles to carry them.
func tagBundle(_, _ string) error { return nil }
