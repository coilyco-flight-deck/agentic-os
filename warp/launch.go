package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// launchConfigExt is the suffix of the launch-config sources we mirror. The
// repo dir also holds sibling .sh bodies and a README that must not be linked.
const launchConfigExt = ".yaml"

// expectedLaunchLinks returns the sorted *.yaml basenames in srcDir, each of
// which should have a matching symlink in the Warp config dir.
func expectedLaunchLinks(srcDir string) ([]string, error) {
	entries, err := os.ReadDir(srcDir)
	if err != nil {
		return nil, err
	}
	var names []string
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), launchConfigExt) {
			continue
		}
		names = append(names, e.Name())
	}
	sort.Strings(names)
	return names, nil
}

// applyLaunchConfigs symlinks every warp/launch_configurations/*.yaml into the
// host Warp config dir and sweeps dangling links. Idempotent.
func applyLaunchConfigs(h *HostPaths) error {
	names, err := expectedLaunchLinks(h.LaunchSrcDir)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Printf("  %-22s SKIP  (no source dir: %s)\n", "launch configs", h.LaunchSrcDir)
			return nil
		}
		return fmt.Errorf("reading launch_configurations source: %w", err)
	}
	if err := os.MkdirAll(h.LaunchDstDir, 0o755); err != nil {
		return fmt.Errorf("creating %s: %w", h.LaunchDstDir, err)
	}

	want := make(map[string]bool, len(names))
	for _, name := range names {
		want[name] = true
		src := filepath.Join(h.LaunchSrcDir, name)
		dst := filepath.Join(h.LaunchDstDir, name)
		status, err := linkLaunchConfig(src, dst)
		if err != nil {
			return err
		}
		fmt.Printf("  launch %-32s %s\n", name, status)
	}

	swept, err := sweepDanglingLinks(h.LaunchDstDir, want)
	if err != nil {
		return err
	}
	for _, name := range swept {
		fmt.Printf("  launch %-32s SWEPT (was dangling)\n", name)
	}
	return nil
}

// linkLaunchConfig ensures dst is a symlink to src, returning a status word.
// A pre-existing real file is backed up to <name>.bak rather than clobbered.
func linkLaunchConfig(src, dst string) (string, error) {
	info, err := os.Lstat(dst)
	switch {
	case err == nil && info.Mode()&os.ModeSymlink != 0:
		if cur, _ := os.Readlink(dst); cur == src {
			return "ok   ", nil
		}
		if err := os.Remove(dst); err != nil {
			return "", fmt.Errorf("removing stale link %s: %w", dst, err)
		}
	case err == nil:
		bak := dst + ".bak"
		if err := os.Rename(dst, bak); err != nil {
			return "", fmt.Errorf("backing up real file %s: %w", dst, err)
		}
	case !os.IsNotExist(err):
		return "", err
	}
	if err := os.Symlink(src, dst); err != nil {
		return "", fmt.Errorf("linking %s -> %s: %w", dst, src, err)
	}
	return "LINKED", nil
}

// sweepDanglingLinks removes only non-resolving symlinks whose basename is not
// in keep. Real files and healthy links are left untouched.
func sweepDanglingLinks(dir string, keep map[string]bool) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var swept []string
	for _, e := range entries {
		name := e.Name()
		if keep[name] {
			continue
		}
		full := filepath.Join(dir, name)
		info, lerr := os.Lstat(full)
		if lerr != nil || info.Mode()&os.ModeSymlink == 0 {
			continue // real file or vanished entry; not ours to touch
		}
		if _, serr := os.Stat(full); serr == nil {
			continue // resolves fine; leave it
		}
		if err := os.Remove(full); err != nil {
			return nil, fmt.Errorf("sweeping dangling link %s: %w", full, err)
		}
		swept = append(swept, name)
	}
	sort.Strings(swept)
	return swept, nil
}

// doctorLaunchConfigs reports per-source link state without mutating anything.
func doctorLaunchConfigs(r *report, h *HostPaths) {
	names, err := expectedLaunchLinks(h.LaunchSrcDir)
	if err != nil {
		if os.IsNotExist(err) {
			r.note("launch configs (skipped): no source dir " + h.LaunchSrcDir)
			return
		}
		r.fail("launch configs", err.Error())
		return
	}

	want := make(map[string]bool, len(names))
	for _, name := range names {
		want[name] = true
		src := filepath.Join(h.LaunchSrcDir, name)
		dst := filepath.Join(h.LaunchDstDir, name)
		info, err := os.Lstat(dst)
		switch {
		case err != nil:
			r.fail("launch "+name, "missing link: "+dst)
		case info.Mode()&os.ModeSymlink == 0:
			r.fail("launch "+name, "not a symlink (real file): "+dst)
		default:
			cur, _ := os.Readlink(dst)
			switch {
			case cur != src:
				r.fail("launch "+name, "links to "+cur+", want "+src)
			default:
				if _, serr := os.Stat(dst); serr != nil {
					r.fail("launch "+name, "dangling link -> "+cur)
				} else {
					r.pass("launch " + name)
				}
			}
		}
	}

	// Surface dangling links that apply would sweep, so doctor and apply agree.
	entries, err := os.ReadDir(h.LaunchDstDir)
	if err != nil {
		return
	}
	for _, e := range entries {
		if want[e.Name()] {
			continue
		}
		full := filepath.Join(h.LaunchDstDir, e.Name())
		info, lerr := os.Lstat(full)
		if lerr != nil || info.Mode()&os.ModeSymlink == 0 {
			continue
		}
		if _, serr := os.Stat(full); serr != nil {
			r.note("launch " + e.Name() + " (apply would sweep): dangling link")
		}
	}
}
