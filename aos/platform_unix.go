//go:build !windows

package main

import (
	"os"
	"syscall"
)

func hostIdentity() (int, int) {
	return os.Getuid(), os.Getgid()
}

func chownPath(path string, symlink bool, uid, gid int) error {
	if symlink {
		return os.Lchown(path, uid, gid)
	}
	return os.Chown(path, uid, gid)
}

func execAs(uid, gid int, spec execSpec) error {
	path, err := lookPath(spec.Command[0])
	if err != nil {
		return err
	}
	if err := syscall.Setgroups([]int{}); err != nil {
		return err
	}
	if err := syscall.Setgid(gid); err != nil {
		return err
	}
	if err := syscall.Setuid(uid); err != nil {
		return err
	}
	return syscall.Exec(path, spec.Command, spec.Environment)
}
