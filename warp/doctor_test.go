package main

import (
	"strings"
	"testing"
)

// canonical is a settings.toml fragment with both volatile keys at their
// template values, plus a stable key whose drift must still be caught.
const canonical = `[appearance.window]
zoom_level = 150

[agents]
cloud_conversation_storage_enabled = true
is_any_ai_enabled = false
`

func TestReconcileVolatileWarpRewroteValues(t *testing.T) {
	// Warp persisted the live zoom and cloud-account state back into the file;
	// only the volatile values differ, so doctor must see a match plus NOTEs.
	got := strings.NewReplacer(
		"zoom_level = 150", "zoom_level = 125",
		"cloud_conversation_storage_enabled = true", "cloud_conversation_storage_enabled = false",
	).Replace(canonical)

	notes, wantCmp, gotCmp := reconcileVolatile("settings.toml", canonical, got, volatileSettingsKeys)
	if wantCmp != gotCmp {
		t.Fatalf("volatile-only drift still compared unequal:\nwant=%q\ngot=%q", wantCmp, gotCmp)
	}
	if len(notes) != 2 {
		t.Fatalf("expected 2 drift NOTEs, got %d: %v", len(notes), notes)
	}
	if !strings.Contains(notes[0], "zoom_level") || !strings.Contains(notes[0], "template=150 live=125") {
		t.Errorf("zoom_level NOTE wrong: %q", notes[0])
	}
	if !strings.Contains(notes[1], "cloud_conversation_storage_enabled") || !strings.Contains(notes[1], "template=true live=false") {
		t.Errorf("cloud_conversation NOTE wrong: %q", notes[1])
	}
}

func TestReconcileVolatileNoDriftWhenIdentical(t *testing.T) {
	notes, wantCmp, gotCmp := reconcileVolatile("settings.toml", canonical, canonical, volatileSettingsKeys)
	if wantCmp != gotCmp {
		t.Fatal("identical content compared unequal")
	}
	if len(notes) != 0 {
		t.Fatalf("identical content produced NOTEs: %v", notes)
	}
}

func TestReconcileVolatileRealDriftStillFails(t *testing.T) {
	// A non-volatile key (is_any_ai_enabled) flipping is real drift: even after
	// neutralizing the volatile keys the content must still compare unequal.
	got := strings.ReplaceAll(canonical, "is_any_ai_enabled = false", "is_any_ai_enabled = true")
	_, wantCmp, gotCmp := reconcileVolatile("settings.toml", canonical, got, volatileSettingsKeys)
	if wantCmp == gotCmp {
		t.Fatal("real drift on a stable key was masked by volatile neutralization")
	}
}

func TestNeutralizeKeyIsPrefixSafe(t *testing.T) {
	// zoom_level must not match a longer key that merely contains it.
	src := "max_zoom_level = 9\nzoom_level = 150\n"
	out := neutralizeKey(src, "zoom_level")
	if !strings.Contains(out, "max_zoom_level = 9") {
		t.Errorf("neutralizeKey clobbered max_zoom_level: %q", out)
	}
	if strings.Contains(out, "zoom_level = 150") {
		t.Errorf("neutralizeKey left the target value in place: %q", out)
	}
}

func TestTomlScalarValueAbsentKey(t *testing.T) {
	if v, ok := tomlScalarValue(canonical, "nonexistent_key"); ok {
		t.Errorf("absent key reported present with value %q", v)
	}
}
