package main

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// A link to Homebrew's cask wrapper would hand the window back to kitty.app,
// so the script is followed to the binary it execs. See docs/aterm.md.
const terminalWrapperHops = 4

var machOMagic = map[uint32]bool{
	0xfeedface: true, 0xcefaedfe: true,
	0xfeedfacf: true, 0xcffaedfe: true,
	0xcafebabe: true, 0xbebafeca: true,
}

func resolveTerminalTarget(path string) (string, error) {
	for hop := 0; hop <= terminalWrapperHops; hop++ {
		resolved, err := filepath.EvalSymlinks(path)
		if err != nil {
			return "", fmt.Errorf("resolve the terminal %q: %w", path, err)
		}
		executable, err := isMachO(resolved)
		if err != nil {
			return "", err
		}
		if executable {
			return resolved, nil
		}
		next, err := wrappedExecutable(resolved)
		if err != nil {
			return "", err
		}
		path = next
	}
	return "", fmt.Errorf("the terminal wrapper chain is deeper than %d hops", terminalWrapperHops)
}

// bundleTerminal is that identity from the other direction, for a session
// started from a shell. Only a macOS bundle has the shape it looks for.
func bundleTerminal(role string) string {
	root := defaultBundleDir()
	entries, err := os.ReadDir(root)
	if err != nil {
		return ""
	}
	for _, entry := range entries {
		if !strings.HasSuffix(entry.Name(), ".app") {
			continue
		}
		path := filepath.Join(root, entry.Name())
		if owner, ours := generatedRole(path); !ours || owner != role {
			continue
		}
		terminal := filepath.Join(path, "Contents", "MacOS", bundleTerminalName)
		if info, err := os.Stat(terminal); err == nil && info.Mode()&0o111 != 0 {
			return terminal
		}
	}
	return ""
}

func isMachO(path string) (bool, error) {
	file, err := os.Open(path)
	if err != nil {
		return false, fmt.Errorf("read the terminal %q: %w", path, err)
	}
	defer func() { _ = file.Close() }()
	header := make([]byte, 4)
	if _, err := file.Read(header); err != nil {
		return false, fmt.Errorf("read the terminal %q: %w", path, err)
	}
	return machOMagic[binary.BigEndian.Uint32(header)], nil
}

// wrappedExecutable reads the one line that matters, the exec of the real
// binary. Any other shape is refused rather than linked and left unbranded.
func wrappedExecutable(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("read the terminal wrapper %q: %w", path, err)
	}
	defer func() { _ = file.Close() }()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 2 || fields[0] != "exec" {
			continue
		}
		if target := strings.Trim(fields[1], `"'`); filepath.IsAbs(target) {
			return target, nil
		}
	}
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("read the terminal wrapper %q: %w", path, err)
	}
	return "", fmt.Errorf("%q is neither an executable nor a wrapper naming one", path)
}
