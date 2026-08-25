//go:build windows

package main

import "syscall"

// detachAttr has no Setsid equivalent on Windows, so the spawned window relies
// on the default process behavior there.
func detachAttr() *syscall.SysProcAttr {
	return nil
}
