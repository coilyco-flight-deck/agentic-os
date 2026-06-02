// Command warp establishes and verifies Kai's Warp config.
package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/urfave/cli/v3"
)

func main() {
	cmd := &cli.Command{
		Name:  "warp",
		Usage: "establish and verify Kai's Warp configuration across hosts",
		Commands: []*cli.Command{
			{
				Name:   "apply",
				Usage:  "host-aware, idempotent: render all three state layers",
				Action: func(_ context.Context, _ *cli.Command) error { return runApply() },
			},
			{
				Name:   "doctor",
				Usage:  "verify only: PASS/FAIL per check, no mutation",
				Action: func(_ context.Context, _ *cli.Command) error { return runDoctor() },
			},
		},
	}
	if err := cmd.Run(context.Background(), os.Args); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

// renderedFile is one template-to-destination mapping for layers 1 -> 2.
type renderedFile struct {
	label    string
	template string
	dest     string
}

func layer2Files(h *HostPaths) []renderedFile {
	return []renderedFile{
		{"settings.toml", "settings.toml.tmpl", h.SettingsPath},
		{"theme yaml", "theme.yaml.tmpl", h.ThemePath},
		{"startup_config.toml", "startup_config.toml.tmpl", h.TabConfigPath},
	}
}

func runApply() error {
	h, err := resolveHostPaths()
	if err != nil {
		return err
	}
	data := newTemplateData(h)
	fmt.Printf("apply: %s host, workspace %s\n", h.OS, h.WorkspaceDir)

	for _, f := range layer2Files(h) {
		content, err := render(f.template, data)
		if err != nil {
			return err
		}
		changed, err := writeReal(f.dest, content)
		if err != nil {
			return err
		}
		fmt.Printf("  %-22s %s %s\n", f.label, statusWord(changed), f.dest)
	}

	// Windows-only pwsh profile, rendered to $PROFILE as a real file.
	if runtime.GOOS == "windows" {
		profile, perr := resolvePwshProfile()
		if perr != nil {
			fmt.Printf("  %-22s SKIP  %v\n", "pwsh profile", perr)
		} else {
			content, err := render("profile.ps1.tmpl", data)
			if err != nil {
				return err
			}
			changed, err := writeReal(profile, content)
			if err != nil {
				return err
			}
			fmt.Printf("  %-22s %s %s\n", "pwsh profile", statusWord(changed), profile)
		}
	}

	return applySQLite(h)
}

func applySQLite(h *HostPaths) error {
	db, err := openWarpDB(h.SQLitePath, false)
	if err != nil {
		fmt.Printf("  %-22s SKIP  %v\n", "sqlite layer", err)
		return nil
	}
	defer db.Close()

	for _, m := range settingMaps {
		if m.Kind == kindOpaque {
			fmt.Printf("  sqlite %-30s SKIP  (doctor-only; reconcile by hand)\n", m.StorageKey)
			continue
		}
		expected, ok := m.expected()
		if !ok {
			fmt.Printf("  sqlite %-30s SKIP  (unmappable value %v)\n", m.StorageKey, m.Canonical)
			continue
		}
		cur, err := db.get(m.StorageKey)
		if err != nil {
			return err
		}
		if cur != nil && valuesEqual(cur.Value, expected) {
			fmt.Printf("  sqlite %-30s ok\n", m.StorageKey)
			continue
		}
		if err := db.set(m.StorageKey, expected); err != nil {
			return err
		}
		fmt.Printf("  sqlite %-30s WROTE %v\n", m.StorageKey, expected)
	}
	return nil
}

func runDoctor() error {
	h, err := resolveHostPaths()
	if err != nil {
		return err
	}
	data := newTemplateData(h)
	r := &report{}
	fmt.Printf("doctor: %s host, workspace %s\n", h.OS, h.WorkspaceDir)

	for _, f := range layer2Files(h) {
		want, err := render(f.template, data)
		if err != nil {
			return err
		}
		checkRendered(r, f.label, f.dest, want)
	}
	if runtime.GOOS == "windows" {
		if profile, perr := resolvePwshProfile(); perr != nil {
			r.fail("pwsh profile", perr.Error())
		} else {
			want, err := render("profile.ps1.tmpl", data)
			if err != nil {
				return err
			}
			checkRendered(r, "pwsh profile", profile, want)
		}
	}

	checkExists(r, "wallpaper image", h.WallpaperPath)
	doctorSQLite(r, h)

	r.print()
	if r.failed > 0 {
		return fmt.Errorf("%d check(s) failed", r.failed)
	}
	return nil
}

func doctorSQLite(r *report, h *HostPaths) {
	db, err := openWarpDB(h.SQLitePath, true)
	if err != nil {
		r.fail("sqlite layer", err.Error())
		return
	}
	defer db.Close()

	for _, m := range settingMaps {
		cur, err := db.get(m.StorageKey)
		if err != nil {
			r.fail("sqlite "+m.StorageKey, err.Error())
			continue
		}
		if m.Kind == kindOpaque {
			actual := "<absent>"
			if cur != nil {
				actual = fmt.Sprintf("%v", cur.Value)
			}
			r.note("sqlite " + m.StorageKey + " (manual): db=" + actual)
			continue
		}
		expected, ok := m.expected()
		if !ok {
			continue
		}
		switch {
		case cur == nil:
			r.fail("sqlite "+m.StorageKey, fmt.Sprintf("absent; expected %v", expected))
		case !valuesEqual(cur.Value, expected):
			r.fail("sqlite "+m.StorageKey, fmt.Sprintf("db=%v expected=%v", cur.Value, expected))
		default:
			r.pass("sqlite " + m.StorageKey)
		}
	}
}

// checkRendered: dest must match content byte-for-byte and not be a symlink.
func checkRendered(r *report, label, dest string, want []byte) {
	info, err := os.Lstat(dest)
	if err != nil {
		r.fail(label, "missing: "+dest)
		return
	}
	if info.Mode()&os.ModeSymlink != 0 {
		r.fail(label, "is a symlink, must be a real file: "+dest)
		return
	}
	got, err := os.ReadFile(dest)
	if err != nil {
		r.fail(label, err.Error())
		return
	}
	if string(got) != string(want) {
		r.fail(label, "content drifted from canonical template: "+dest)
		return
	}
	r.pass(label)
}

func checkExists(r *report, label, path string) {
	if _, err := os.Stat(path); err != nil {
		r.fail(label, "missing: "+path)
		return
	}
	r.pass(label)
}

// writeReal writes a real file at dest, replacing any pre-existing symlink.
func writeReal(dest string, content []byte) (changed bool, err error) {
	if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
		return false, err
	}
	if info, err := os.Lstat(dest); err == nil {
		if info.Mode()&os.ModeSymlink != 0 {
			if err := os.Remove(dest); err != nil {
				return false, fmt.Errorf("removing stale symlink %s: %w", dest, err)
			}
		} else if cur, err := os.ReadFile(dest); err == nil && string(cur) == string(content) {
			return false, nil
		}
	}
	if err := os.WriteFile(dest, content, 0o644); err != nil {
		return false, err
	}
	return true, nil
}

func statusWord(changed bool) string {
	if changed {
		return "WROTE"
	}
	return "ok   "
}

type report struct {
	lines  []string
	failed int
}

func (r *report) pass(label string) { r.lines = append(r.lines, "  PASS  "+label) }
func (r *report) note(label string) { r.lines = append(r.lines, "  NOTE  "+label) }
func (r *report) fail(label, detail string) {
	r.failed++
	r.lines = append(r.lines, "  FAIL  "+label+" - "+detail)
}

func (r *report) print() {
	for _, l := range r.lines {
		fmt.Println(l)
	}
	if r.failed == 0 {
		fmt.Println("doctor: all checks passed")
	} else {
		fmt.Printf("doctor: %d check(s) failed\n", r.failed)
	}
}
