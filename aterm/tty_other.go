//go:build !darwin && !linux

package main

// flushInput has no portable form here, so pending input is left alone.
func flushInput(uintptr) error { return nil }
