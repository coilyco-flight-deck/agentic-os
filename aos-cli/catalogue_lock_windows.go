//go:build windows

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

func lockCatalogueCache(cacheRoot string) (func(), error) {
	lockPath := filepath.Join(cacheRoot, "lock.excl")
	deadline := time.Now().Add(10 * time.Second)
	for {
		file, err := os.OpenFile(
			lockPath,
			os.O_CREATE|os.O_EXCL|os.O_WRONLY,
			0o644,
		)
		if err == nil {
			_ = file.Close()
			return func() { _ = os.Remove(lockPath) }, nil
		}
		if !os.IsExist(err) {
			return nil, fmt.Errorf("lock catalogue cache: %w", err)
		}
		if time.Now().After(deadline) {
			return nil, fmt.Errorf("catalogue cache is locked by another process")
		}
		time.Sleep(50 * time.Millisecond)
	}
}
