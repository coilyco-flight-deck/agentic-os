package main

import (
	"fmt"
	"os"
	"path/filepath"
)

const (
	aosTempRootName  = "aos"
	aosTempAliasRoot = "/tmp"
)

func aosTempPath(parts ...string) string {
	elements := append([]string{os.TempDir(), aosTempRootName}, parts...)
	return filepath.Join(elements...)
}

func aosTempAliasPath(parts ...string) string {
	elements := append([]string{aosTempAliasRoot, aosTempRootName}, parts...)
	return filepath.Join(elements...)
}

// ensureAOSTempAlias links /tmp/aos at the opaque per-user temp root so session
// paths stay readable. Any failure returns that root instead of failing launch.
func ensureAOSTempAlias() string {
	return ensureTempAlias(aosTempPath(), aosTempAliasPath())
}

func ensureTempAlias(target, alias string) string {
	if alias == target {
		return target
	}
	if err := os.MkdirAll(target, 0o700); err != nil {
		return target
	}
	info, err := os.Lstat(alias)
	if err == nil {
		if info.Mode()&os.ModeSymlink == 0 {
			return target
		}
		if linked, readErr := os.Readlink(alias); readErr == nil && linked == target {
			return alias
		}
		return target
	}
	if !os.IsNotExist(err) {
		return target
	}
	if err := os.Symlink(target, alias); err != nil {
		// A concurrent launch may have won the race with the same target.
		if linked, readErr := os.Readlink(alias); readErr == nil && linked == target {
			return alias
		}
		return target
	}
	return alias
}

func ensureAOSTempNamespace(parts ...string) (string, error) {
	path := aosTempPath(parts...)
	if err := os.MkdirAll(path, 0o700); err != nil {
		return "", fmt.Errorf("create AOS temporary namespace %s: %w", path, err)
	}
	return path, nil
}
