//go:build !windows

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"syscall"
)

func lockCatalogueCache(cacheRoot string) (func(), error) {
	file, err := os.OpenFile(
		filepath.Join(cacheRoot, "lock"),
		os.O_CREATE|os.O_RDWR,
		0o644,
	)
	if err != nil {
		return nil, err
	}
	if err := syscall.Flock(int(file.Fd()), syscall.LOCK_EX); err != nil {
		_ = file.Close()
		return nil, fmt.Errorf("lock catalogue cache: %w", err)
	}
	return func() {
		_ = syscall.Flock(int(file.Fd()), syscall.LOCK_UN)
		_ = file.Close()
	}, nil
}
