package main

import (
	"bytes"
	"encoding/binary"
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func frontendOverlay(t *testing.T) overlayDocument {
	t.Helper()
	document, err := parseOverlay(fixture(t, "frontend-claude-overlay.json"), "frontend", "claude", "acting")
	if err != nil {
		t.Fatalf("parse the frontend overlay fixture: %v", err)
	}
	return document
}

// icnsWith builds a container holding one PNG per named entry, so a test can
// state what the walker should find without shipping a second fixture.
func icnsWith(t *testing.T, entries map[string]int) []byte {
	t.Helper()
	body := []byte{}
	for name, width := range entries {
		art := pngOfSize(t, width)
		chunk := make([]byte, 8, 8+len(art))
		copy(chunk, name)
		binary.BigEndian.PutUint32(chunk[4:], uint32(8+len(art)))
		body = append(body, append(chunk, art...)...)
	}
	container := make([]byte, 8, 8+len(body))
	copy(container, "icns")
	binary.BigEndian.PutUint32(container[4:], uint32(8+len(body)))
	return append(container, body...)
}

func pngOfSize(t *testing.T, width int) []byte {
	t.Helper()
	art := image.NewNRGBA(image.Rect(0, 0, width, width))
	art.Set(0, 0, color.NRGBA{R: 0xe5, G: 0x83, B: 0xf7, A: 0xff})
	buffer := &bytes.Buffer{}
	if err := png.Encode(buffer, art); err != nil {
		t.Fatalf("encode the fixture art: %v", err)
	}
	return buffer.Bytes()
}

func TestCreatureArtTakesTheLargestEntry(t *testing.T) {
	art := creatureArt(icnsWith(t, map[string]int{"ic07": 128, "ic14": 512, "ic11": 32}))
	width, ok := pngWidth(art)
	if !ok || width != 512 {
		t.Fatalf("expected the 512px entry, got %d (png %v)", width, ok)
	}
}

// A role with no committed art keeps a flat background rather than a broken
// reference, the same property `aterm bundles` holds for the system icon.
func TestCreatureArtRefusesWhatItCannotRead(t *testing.T) {
	container := icnsWith(t, map[string]int{"ic14": 64})
	for name, raw := range map[string][]byte{
		"nothing":       nil,
		"not an icns":   []byte("PNG really"),
		"truncated":     container[:20],
		"no png inside": icnsWith(t, map[string]int{}),
	} {
		if art := creatureArt(raw); art != nil {
			t.Fatalf("%s should yield no art, got %d bytes", name, len(art))
		}
	}
}

// A chunk claiming a length that does not advance would spin forever, and one
// running past the container would read whatever follows it.
func TestCreatureArtStopsOnAMalformedChunk(t *testing.T) {
	container := icnsWith(t, map[string]int{"ic14": 64})
	stalled := append([]byte{}, container...)
	binary.BigEndian.PutUint32(stalled[12:16], 0)
	if art := creatureArt(stalled); art != nil {
		t.Fatalf("a zero-length chunk should end the walk, got %d bytes", len(art))
	}
	overrun := append([]byte{}, container...)
	binary.BigEndian.PutUint32(overrun[12:16], 1<<20)
	if art := creatureArt(overrun); art != nil {
		t.Fatalf("a chunk past the container should end the walk, got %d bytes", len(art))
	}
}

func TestPlateHoldsTheArtAtItsOwnShare(t *testing.T) {
	source, err := png.Decode(bytes.NewReader(pngOfSize(t, 512)))
	if err != nil {
		t.Fatalf("decode the fixture art: %v", err)
	}
	plate := composeCreaturePlate(source).(*image.NRGBA)
	width := plate.Bounds().Dx()
	if share := 512 / float64(width); share < creatureWidthShare-0.01 || share > creatureWidthShare+0.01 {
		t.Fatalf("art covers %.3f of the plate, want %.2f", share, creatureWidthShare)
	}
	if got, want := plate.Bounds().Dy(), int(float64(width)*creaturePlateAspect); got != want {
		t.Fatalf("plate is %dpx tall, want %d", got, want)
	}
	// The art is anchored top right, so the left of the plate stays empty and
	// the window keeps its flat background where the session's text begins.
	if _, _, _, alpha := plate.At(0, plate.Bounds().Dy()/2).RGBA(); alpha != 0 {
		t.Fatalf("the left of the plate should be transparent, got alpha %d", alpha)
	}
	inset := image.Point{
		X: int(float64(width) * creatureInset),
		Y: int(float64(plate.Bounds().Dy()) * creatureInset),
	}
	corner := image.Point{
		X: width - 512 - inset.X,
		Y: min(inset.Y, plate.Bounds().Dy()-512),
	}
	if _, _, _, alpha := plate.At(corner.X, corner.Y).RGBA(); alpha == 0 {
		t.Fatalf("the art should start at %v, found nothing there", corner)
	}
}

func TestPlateIsCachedAndNamedForItsRecipe(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	art := pngOfSize(t, 64)
	first, err := creaturePlatePath("frontend", art)
	if err != nil {
		t.Fatalf("resolve the plate path: %v", err)
	}
	if !strings.HasPrefix(filepath.Base(first), "frontend-") {
		t.Fatalf("the plate should be named for its role, got %q", filepath.Base(first))
	}
	other, err := creaturePlatePath("frontend", pngOfSize(t, 65))
	if err != nil {
		t.Fatalf("resolve the second plate path: %v", err)
	}
	if first == other {
		t.Fatalf("re-drawn art should land on a new plate, both are %q", first)
	}
	if err := writeCreaturePlate(first, art); err != nil {
		t.Fatalf("write the plate: %v", err)
	}
	if _, err := os.Stat(first); err != nil {
		t.Fatalf("the plate should exist after writing: %v", err)
	}
	// The staging file is the one thing a reader of the directory must never
	// find, since kitty would open a half-written plate as a blank window.
	entries, err := os.ReadDir(filepath.Dir(first))
	if err != nil {
		t.Fatalf("read the cache directory: %v", err)
	}
	if len(entries) != 1 || entries[0].Name() != filepath.Base(first) {
		t.Fatalf("the cache should hold only the finished plate, got %v", entries)
	}
}

func TestCreatureReachesTheTerminalArguments(t *testing.T) {
	t.Setenv("HOME", t.TempDir())
	plate := bakeCreaturePlate("frontend", creaturePresence)
	if plate.Path == "" {
		t.Fatal("frontend ships committed art, so it should bake a plate")
	}
	if plate.Tint != "0.80" {
		t.Fatalf("tint is %q, want the inverse of the presence", plate.Tint)
	}
	document := frontendOverlay(t)
	request := launchRequest{
		Role: "frontend", Seat: "claude", StartAs: "fullscreen", FontSize: "14.5",
		Creature: plate,
	}
	plan, err := buildLaunchPlan(document, request, t.TempDir(), "/stub/aterm", "/stub/compose", "/stub/aos", false)
	if err != nil {
		t.Fatalf("build the launch plan: %v", err)
	}
	joined := strings.Join(plan.Arguments, " ")
	for _, want := range []string{
		"background_image=" + plate.Path,
		"background_image_layout=cscaled",
		"background_tint=0.80",
	} {
		if !strings.Contains(joined, want) {
			t.Fatalf("terminal arguments are missing %q: %v", want, plan.Arguments)
		}
	}
}

// A window without a creature must not carry a bare background_image, which
// kitty reads as a glob matching nothing and refuses.
func TestNoCreatureLeavesTheBackgroundFlat(t *testing.T) {
	document := frontendOverlay(t)
	request := launchRequest{Role: "frontend", Seat: "claude", StartAs: "fullscreen", FontSize: "14.5"}
	plan, err := buildLaunchPlan(document, request, t.TempDir(), "/stub/aterm", "/stub/compose", "/stub/aos", false)
	if err != nil {
		t.Fatalf("build the launch plan: %v", err)
	}
	if joined := strings.Join(plan.Arguments, " "); strings.Contains(joined, "background_image") {
		t.Fatalf("a flat window should pass no background image: %v", plan.Arguments)
	}
}

func TestCreatureWantedReadsTheEnvironment(t *testing.T) {
	t.Setenv(noCreatureEnv, "")
	if !creatureWanted(false) {
		t.Fatal("an unset environment should leave the creature on")
	}
	if creatureWanted(true) {
		t.Fatal("--no-creature should turn the creature off")
	}
	t.Setenv(noCreatureEnv, "1")
	if creatureWanted(false) {
		t.Fatalf("%s should turn the creature off", noCreatureEnv)
	}
}
