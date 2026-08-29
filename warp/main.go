// Command warp establishes and verifies Kai's Warp config.
package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"

	"github.com/urfave/cli/v3"
)

func main() {
	channelFlag := func() []cli.Flag {
		return []cli.Flag{
			&cli.StringFlag{
				Name:    "channel",
				Usage:   "Warp channel (macOS/Windows): `preview` or `stable` (default: auto-detect, prefer Preview)",
				Sources: cli.EnvVars("WARP_CHANNEL"),
			},
		}
	}
	cmd := &cli.Command{
		Name:  "warp",
		Usage: "establish and verify Kai's Warp configuration across hosts",
		Commands: []*cli.Command{
			{
				Name:   "apply",
				Usage:  "host-aware, idempotent: render all three state layers",
				Flags:  channelFlag(),
				Action: func(_ context.Context, c *cli.Command) error { return runApply(c.String("channel")) },
			},
			{
				Name:   "doctor",
				Usage:  "verify only: PASS/FAIL per check, no mutation",
				Flags:  channelFlag(),
				Action: func(_ context.Context, c *cli.Command) error { return runDoctor(c.String("channel")) },
			},
		},
	}
	if err := cmd.Run(context.Background(), os.Args); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

// channelSuffix annotates the header with the resolved Warp channel, so
// apply/doctor show which config dir they target. Empty on linux.
func channelSuffix(h *HostPaths) string {
	if h.Channel == "" {
		return ""
	}
	return " (warp " + h.Channel + ")"
}

// renderedFile is one template-to-destination mapping for layers 1 -> 2.
type renderedFile struct {
	label    string
	template string
	dest     string
	// volatileKeys are TOML keys Warp rewrites from live state, neutralized
	// before doctor's content comparison so their drift never FAILs.
	volatileKeys []string
}

// volatileSettingsKeys are settings.toml keys Warp rewrites from live UI or
// cloud-account state, so doctor skips their values. See the tooling-warp skill.
var volatileSettingsKeys = []string{
	"zoom_level",
	"cloud_conversation_storage_enabled",
}

func layer2Files(h *HostPaths) []renderedFile {
	return []renderedFile{
		{"settings.toml", "settings.toml.tmpl", h.SettingsPath, volatileSettingsKeys},
		{"keybindings.yaml", "keybindings.yaml.tmpl", h.KeybindingsPath, nil},
		{"theme yaml", "theme.yaml.tmpl", h.ThemePath, nil},
		{"startup_config.toml", "startup_config.toml.tmpl", h.TabConfigPath, nil},
	}
}

func runApply(channel string) error {
	h, err := resolveHostPaths(channel)
	if err != nil {
		return err
	}
	data := newTemplateData(h)
	fmt.Printf("apply: %s host%s, workspace %s\n", h.OS, channelSuffix(h), h.WorkspaceDir)

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

	if err := applyLaunchConfigs(h); err != nil {
		return err
	}

	return applySQLite(h)
}

func applySQLite(h *HostPaths) error {
	// Stat first: opening read-write would create an empty warp.sqlite, and we
	// must not seed a stray DB before Warp itself has initialized one.
	if _, err := os.Stat(h.SQLitePath); os.IsNotExist(err) {
		fmt.Printf("  %-22s SKIP  (warp.sqlite not found; launch Warp once to init it)\n", "sqlite layer")
		return nil
	}

	db, err := openWarpDB(h.SQLitePath, false)
	if err != nil {
		fmt.Printf("  %-22s SKIP  %v\n", "sqlite layer", err)
		return nil
	}
	defer db.Close()

	if ok, err := db.hasStorageTable(); err != nil {
		fmt.Printf("  %-22s SKIP  %v\n", "sqlite layer", err)
		return nil
	} else if !ok {
		fmt.Printf("  %-22s SKIP  (no generic_string_objects table; launch Warp once to init it)\n", "sqlite layer")
		return nil
	}

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
	return applyShellPref(db, h)
}

// applyShellPref reconciles the Windows-only default-shell pref into warp.sqlite.
// See shell.go.
func applyShellPref(db *warpDB, h *HostPaths) error {
	if h.OS != "windows" {
		return nil
	}
	if h.DefaultShell == "" {
		fmt.Printf("  sqlite %-30s SKIP  (no PowerShell 7 found to set as default shell)\n", defaultShellStorageKey)
		return nil
	}
	cur, err := db.get(defaultShellStorageKey)
	if err != nil {
		return err
	}
	if cur != nil && valuesEqual(cur.Value, h.DefaultShell) {
		fmt.Printf("  sqlite %-30s ok\n", defaultShellStorageKey)
		return nil
	}
	if err := db.set(defaultShellStorageKey, h.DefaultShell); err != nil {
		return err
	}
	fmt.Printf("  sqlite %-30s WROTE %v\n", defaultShellStorageKey, h.DefaultShell)
	return nil
}

func runDoctor(channel string) error {
	h, err := resolveHostPaths(channel)
	if err != nil {
		return err
	}
	data := newTemplateData(h)
	r := &report{}
	fmt.Printf("doctor: %s host%s, workspace %s\n", h.OS, channelSuffix(h), h.WorkspaceDir)

	for _, f := range layer2Files(h) {
		want, err := render(f.template, data)
		if err != nil {
			return err
		}
		checkRendered(r, f.label, f.dest, want, f.volatileKeys)
	}
	if runtime.GOOS == "windows" {
		if profile, perr := resolvePwshProfile(); perr != nil {
			r.fail("pwsh profile", perr.Error())
		} else {
			want, err := render("profile.ps1.tmpl", data)
			if err != nil {
				return err
			}
			checkRendered(r, "pwsh profile", profile, want, nil)
		}
	}

	checkExists(r, "wallpaper image", h.WallpaperPath)
	doctorLaunchConfigs(r, h)
	doctorSQLite(r, h)

	r.print()
	if r.failed > 0 {
		return fmt.Errorf("%d check(s) failed", r.failed)
	}
	return nil
}

func doctorSQLite(r *report, h *HostPaths) {
	if _, err := os.Stat(h.SQLitePath); os.IsNotExist(err) {
		r.note("sqlite layer (skipped): warp.sqlite not found; launch Warp once to init it")
		return
	}

	db, err := openWarpDB(h.SQLitePath, true)
	if err != nil {
		r.fail("sqlite layer", err.Error())
		return
	}
	defer db.Close()

	if ok, err := db.hasStorageTable(); err != nil {
		r.note("sqlite layer (skipped): " + err.Error())
		return
	} else if !ok {
		r.note("sqlite layer (skipped): no generic_string_objects table; launch Warp once to init it")
		return
	}

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
	doctorShellPref(r, db, h)
}

// doctorShellPref reports drift on the Windows-only default-shell preference.
// See the tooling-warp skill.
func doctorShellPref(r *report, db *warpDB, h *HostPaths) {
	if h.OS != "windows" {
		return
	}
	if h.DefaultShell == "" {
		r.note("sqlite " + defaultShellStorageKey + " (skipped): no PowerShell 7 found to compare against")
		return
	}
	cur, err := db.get(defaultShellStorageKey)
	if err != nil {
		r.fail("sqlite "+defaultShellStorageKey, err.Error())
		return
	}
	switch {
	case cur == nil:
		r.fail("sqlite "+defaultShellStorageKey, fmt.Sprintf("absent; expected %v", h.DefaultShell))
	case !valuesEqual(cur.Value, h.DefaultShell):
		r.fail("sqlite "+defaultShellStorageKey, fmt.Sprintf("db=%v expected=%v", cur.Value, h.DefaultShell))
	default:
		r.pass("sqlite " + defaultShellStorageKey)
	}
}

// checkRendered: dest must match content byte-for-byte (modulo Warp-owned
// volatileKeys, whose values are neutralized first) and not be a symlink.
func checkRendered(r *report, label, dest string, want []byte, volatileKeys []string) {
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
	notes, wantCmp, gotCmp := reconcileVolatile(label, string(want), string(got), volatileKeys)
	for _, n := range notes {
		r.note(n)
	}
	if wantCmp != gotCmp {
		r.fail(label, "content drifted from canonical template: "+dest)
		return
	}
	r.pass(label)
}

// reconcileVolatile neutralizes each volatile key's value in want and got (so a
// Warp-rewritten value is not drift) and returns a NOTE per diverged key.
func reconcileVolatile(label, want, got string, volatileKeys []string) (notes []string, wantOut, gotOut string) {
	wantOut, gotOut = want, got
	for _, key := range volatileKeys {
		wv, wok := tomlScalarValue(wantOut, key)
		gv, gok := tomlScalarValue(gotOut, key)
		if wok && gok && wv != gv {
			notes = append(notes, fmt.Sprintf("%s %s (Warp-owned, skipped): template=%s live=%s", label, key, wv, gv))
		}
		wantOut = neutralizeKey(wantOut, key)
		gotOut = neutralizeKey(gotOut, key)
	}
	return notes, wantOut, gotOut
}

// volatileKeyPattern matches a `key = value` line, capturing the prefix (1) and
// value (2). Anchored + optional indent so `zoom_level` never hits a longer key.
func volatileKeyPattern(key string) *regexp.Regexp {
	return regexp.MustCompile(`(?m)^([ \t]*` + regexp.QuoteMeta(key) + `[ \t]*=[ \t]*)(.*)$`)
}

// tomlScalarValue returns the trimmed value of the first `key = value` line, or
// false if the key is absent.
func tomlScalarValue(content, key string) (string, bool) {
	m := volatileKeyPattern(key).FindStringSubmatch(content)
	if m == nil {
		return "", false
	}
	return strings.TrimSpace(m[2]), true
}

// neutralizeKey replaces every `key = value` line's value with a fixed sentinel
// so the value drops out of the content comparison while the key line stays.
func neutralizeKey(content, key string) string {
	return volatileKeyPattern(key).ReplaceAllString(content, "${1}<volatile>")
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
