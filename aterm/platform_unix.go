//go:build !windows

package main

import "syscall"

// detachAttr puts the window in its own session so the launching shell gets its
// prompt back immediately and the window survives that shell closing.
func detachAttr() *syscall.SysProcAttr {
	return &syscall.SysProcAttr{Setsid: true}
}
