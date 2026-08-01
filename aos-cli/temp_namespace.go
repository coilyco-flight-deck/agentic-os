package main

import (
	"fmt"
	"os"
	"path/filepath"
)

const aosTempRootName = "aos"

func aosTempPath(parts ...string) string {
	elements := append([]string{os.TempDir(), aosTempRootName}, parts...)
	return filepath.Join(elements...)
}

func ensureAOSTempNamespace(parts ...string) (string, error) {
	path := aosTempPath(parts...)
	if err := os.MkdirAll(path, 0o700); err != nil {
		return "", fmt.Errorf("create AOS temporary namespace %s: %w", path, err)
	}
	return path, nil
}
