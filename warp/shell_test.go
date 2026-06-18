package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFirstExistingFile(t *testing.T) {
	dir := t.TempDir()
	real := filepath.Join(dir, "pwsh.exe")
	if err := os.WriteFile(real, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	missing := filepath.Join(dir, "nope.exe")

	if got := firstExistingFile([]string{missing, real}); got != real {
		t.Errorf("firstExistingFile picked %q, want %q", got, real)
	}
	if got := firstExistingFile([]string{"", missing}); got != "" {
		t.Errorf("firstExistingFile = %q, want empty", got)
	}
	if got := firstExistingFile(nil); got != "" {
		t.Errorf("firstExistingFile(nil) = %q, want empty", got)
	}
	// A directory is not a regular file and must be ignored.
	if got := firstExistingFile([]string{dir}); got != "" {
		t.Errorf("firstExistingFile(dir) = %q, want empty", got)
	}
}

func TestResolveWindowsDefaultShellAbsent(t *testing.T) {
	// On the (non-Windows) test host the C:\ candidates do not exist, so the
	// resolver must fall back to "" - the signal that makes apply/doctor skip.
	if got := resolveWindowsDefaultShell(); got != "" {
		t.Skipf("PowerShell 7 present on this host (%q); skipping absent-case check", got)
	}
}

// newTestDB returns an open, writable warp.sqlite with the storage table.
func newTestDB(t *testing.T) *warpDB {
	t.Helper()
	path := filepath.Join(t.TempDir(), "warp.sqlite")
	db, err := openWarpDB(path, false)
	if err != nil {
		t.Fatalf("openWarpDB: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	if _, err := db.db.Exec(
		"CREATE TABLE generic_string_objects (id INTEGER PRIMARY KEY, data TEXT)",
	); err != nil {
		t.Fatalf("create table: %v", err)
	}
	return db
}

func TestApplyShellPrefRoundtrip(t *testing.T) {
	db := newTestDB(t)
	h := &HostPaths{OS: "windows", DefaultShell: `C:\Program Files\PowerShell\7\pwsh.exe`}

	if err := applyShellPref(db, h); err != nil {
		t.Fatalf("applyShellPref (insert): %v", err)
	}
	cur, err := db.get(defaultShellStorageKey)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if cur == nil || cur.Value != h.DefaultShell {
		t.Fatalf("stored value = %v, want %q", cur, h.DefaultShell)
	}
	// Second apply is a no-op and must not error.
	if err := applyShellPref(db, h); err != nil {
		t.Fatalf("applyShellPref (idempotent): %v", err)
	}

	// doctor on the converged DB passes.
	r := &report{}
	doctorShellPref(r, db, h)
	if r.failed != 0 {
		t.Errorf("doctorShellPref reported %d failures on converged DB: %v", r.failed, r.lines)
	}
}

func TestDoctorShellPrefDrift(t *testing.T) {
	db := newTestDB(t)
	if err := db.set(defaultShellStorageKey, `C:\Windows\System32\cmd.exe`); err != nil {
		t.Fatalf("seed drift: %v", err)
	}
	h := &HostPaths{OS: "windows", DefaultShell: `C:\Program Files\PowerShell\7\pwsh.exe`}

	r := &report{}
	doctorShellPref(r, db, h)
	if r.failed != 1 {
		t.Errorf("expected 1 drift failure, got %d: %v", r.failed, r.lines)
	}
}

func TestDoctorShellPrefAbsent(t *testing.T) {
	db := newTestDB(t)
	h := &HostPaths{OS: "windows", DefaultShell: `C:\Program Files\PowerShell\7\pwsh.exe`}

	r := &report{}
	doctorShellPref(r, db, h)
	if r.failed != 1 {
		t.Errorf("expected 1 absent failure, got %d: %v", r.failed, r.lines)
	}
}

func TestShellPrefNonWindowsNoop(t *testing.T) {
	db := newTestDB(t)
	for _, osName := range []string{"darwin", "linux"} {
		h := &HostPaths{OS: osName, DefaultShell: "irrelevant"}
		if err := applyShellPref(db, h); err != nil {
			t.Errorf("applyShellPref(%s): %v", osName, err)
		}
		if cur, _ := db.get(defaultShellStorageKey); cur != nil {
			t.Errorf("applyShellPref(%s) wrote a row: %v", osName, cur)
		}
		r := &report{}
		doctorShellPref(r, db, h)
		if len(r.lines) != 0 {
			t.Errorf("doctorShellPref(%s) emitted %v", osName, r.lines)
		}
	}
}

func TestShellPrefNoShellSkips(t *testing.T) {
	db := newTestDB(t)
	h := &HostPaths{OS: "windows", DefaultShell: ""}

	if err := applyShellPref(db, h); err != nil {
		t.Fatalf("applyShellPref: %v", err)
	}
	if cur, _ := db.get(defaultShellStorageKey); cur != nil {
		t.Errorf("applyShellPref wrote a row with no shell resolved: %v", cur)
	}
	r := &report{}
	doctorShellPref(r, db, h)
	if r.failed != 0 {
		t.Errorf("doctorShellPref should NOTE-skip, got %d failures: %v", r.failed, r.lines)
	}
	if len(r.lines) != 1 {
		t.Errorf("expected one NOTE line, got %v", r.lines)
	}
}
