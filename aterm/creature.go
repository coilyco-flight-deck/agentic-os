package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"image"
	"image/draw"
	"image/png"
	"os"
	"path/filepath"
	"strings"
)

const (
	// Bump when the plate recipe changes, so a cached plate from the old one
	// stops being reused rather than outliving it.
	creatureRecipe = "aterm.creature.v1"
	noCreatureEnv  = "ATERM_NO_CREATURE"
	// The creature's share of the window width, and how far its own box sits
	// from the edge it is anchored to. Both are fractions of the plate.
	creatureWidthShare = 0.26
	creatureInset      = 0.08
	// How much of the art survives the tint, chosen against the identity card
	// rather than in the abstract. See docs/aterm.md.
	creaturePresence = 0.09
	// cscaled covers the window, so the plate carries the aspect a full-screen
	// window most often has and loses a band top and bottom on anything wider.
	creaturePlateAspect = 10.0 / 16.0
	// A path kitty reads as a glob is a path it may not open. See docs/aterm.md.
	globMetacharacters = "*?[]{}"
)

// creaturePlate is the background image one window draws behind its session,
// sized so kitty leaves the creature at creatureWidthShare of the window.
type creaturePlate struct {
	Path string `json:"path"`
	Tint string `json:"tint"`
}

// bakeCreaturePlate returns the plate, or a zero value on anything that would
// stop one. The background is decoration, so a window opens either way.
func bakeCreaturePlate(role string, presence float64) creaturePlate {
	art := creatureArt(roleIcon(role))
	if art == nil {
		return creaturePlate{}
	}
	path, err := creaturePlatePath(role, art)
	if err != nil {
		return creaturePlate{}
	}
	if strings.ContainsAny(path, globMetacharacters) {
		return creaturePlate{}
	}
	if _, err := os.Stat(path); err != nil {
		if err := writeCreaturePlate(path, art); err != nil {
			return creaturePlate{}
		}
	}
	return creaturePlate{Path: path, Tint: fmt.Sprintf("%.2f", 1-presence)}
}

// creatureArt reads the largest PNG out of an icns container, which is the one
// committed copy of this art. See docs/aterm.md.
func creatureArt(icns []byte) []byte {
	const header = 8
	if len(icns) < header || string(icns[:4]) != "icns" {
		return nil
	}
	total := int(binary.BigEndian.Uint32(icns[4:header]))
	if total > len(icns) {
		total = len(icns)
	}
	var best []byte
	var bestWidth uint32
	for offset := header; offset+header <= total; {
		size := int(binary.BigEndian.Uint32(icns[offset+4 : offset+header]))
		// A chunk that does not advance, or runs past the container, ends the
		// walk rather than looping or reading someone else's bytes.
		if size < header || offset+size > total {
			break
		}
		entry := icns[offset+header : offset+size]
		if width, ok := pngWidth(entry); ok && width > bestWidth {
			best, bestWidth = entry, width
		}
		offset += size
	}
	return best
}

func pngWidth(entry []byte) (uint32, bool) {
	const ihdr = 24
	if len(entry) < ihdr+4 || string(entry[:8]) != "\x89PNG\r\n\x1a\n" {
		return 0, false
	}
	return binary.BigEndian.Uint32(entry[16:20]), true
}

// creaturePlatePath names the plate after what produced it, so re-drawn art or
// a new recipe lands on a new file rather than a stale hit.
func creaturePlatePath(role string, art []byte) (string, error) {
	root, err := os.UserCacheDir()
	if err != nil {
		return "", fmt.Errorf("resolve the cache directory: %w", err)
	}
	// A plate re-cut to a new share is the same bytes in, so the geometry is
	// hashed beside the art or the name cannot tell the two apart.
	recipe := fmt.Sprintf(
		"%s\x00%g\x00%g\x00%g\x00",
		creatureRecipe, creatureWidthShare, creatureInset, creaturePlateAspect,
	)
	sum := sha256.Sum256(append([]byte(recipe), art...))
	name := fmt.Sprintf("%s-%s.png", role, hex.EncodeToString(sum[:6]))
	return filepath.Join(root, "aterm", "creature", name), nil
}

func writeCreaturePlate(path string, art []byte) error {
	source, err := png.Decode(bytes.NewReader(art))
	if err != nil {
		return fmt.Errorf("decode the creature art: %w", err)
	}
	plate := composeCreaturePlate(source)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("make the plate directory: %w", err)
	}
	// A half-written plate is a window kitty opens blank, so the file only ever
	// appears complete under its own name.
	staged, err := os.CreateTemp(filepath.Dir(path), ".plate-*.png")
	if err != nil {
		return fmt.Errorf("stage the plate: %w", err)
	}
	defer func() { _ = os.Remove(staged.Name()) }()
	if err := png.Encode(staged, plate); err != nil {
		_ = staged.Close()
		return fmt.Errorf("encode the plate: %w", err)
	}
	if err := staged.Close(); err != nil {
		return fmt.Errorf("close the plate: %w", err)
	}
	return os.Rename(staged.Name(), path)
}

// composeCreaturePlate places the art once and never resamples it: the canvas
// sets the size and kitty does the scaling. See docs/aterm.md.
func composeCreaturePlate(source image.Image) image.Image {
	art := source.Bounds()
	width := int(float64(art.Dx()) / creatureWidthShare)
	height := int(float64(width) * creaturePlateAspect)
	if height < art.Dy() {
		height = art.Dy()
	}
	inset := image.Point{
		X: int(float64(width) * creatureInset),
		Y: int(float64(height) * creatureInset),
	}
	origin := image.Point{
		X: max(0, width-art.Dx()-inset.X),
		Y: max(0, height-art.Dy()-inset.Y),
	}
	plate := image.NewNRGBA(image.Rect(0, 0, width, height))
	draw.Draw(
		plate,
		image.Rectangle{Min: origin, Max: origin.Add(image.Point{X: art.Dx(), Y: art.Dy()})},
		source,
		art.Min,
		draw.Src,
	)
	return plate
}

// creatureWanted is off wherever the window is being recorded or read by
// something other than a person, matching how the card reads its own motion.
func creatureWanted(disabled bool) bool {
	return !disabled && strings.TrimSpace(os.Getenv(noCreatureEnv)) == ""
}
