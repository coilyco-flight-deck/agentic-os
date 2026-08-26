package soundspec

import (
	"encoding/binary"
	"math"
	"testing"
)

func loudest(samples []float64) float64 {
	loudest := 0.0
	for _, sample := range samples {
		if magnitude := math.Abs(sample); magnitude > loudest {
			loudest = magnitude
		}
	}
	return loudest
}

// A shipped sample has to be reviewable, which means the same bytes on every
// host and on every run. agentic-os#1256
func TestRenderIsDeterministicAndAudible(t *testing.T) {
	mark := Mark{Timbre: "floor-tom", Contour: "rising-return", Pulse: "driving-two"}
	first := Render(mark)
	second := Render(mark)
	if len(first) == 0 {
		t.Fatal("the sample is empty")
	}
	if len(first) != len(second) {
		t.Fatalf("lengths %d and %d", len(first), len(second))
	}
	for index := range first {
		if first[index] != second[index] {
			t.Fatalf("sample %d differs between renders", index)
		}
	}
	if got := loudest(first); got < 0.5 || got > 1 {
		t.Fatalf("peak = %f, want the normalized %f", got, peak)
	}
}

// The grammar is read, so a value the roster has not shipped still speaks.
func TestAnUnshippedMarkStillSpeaks(t *testing.T) {
	samples := Render(Mark{Timbre: "kalimba", Contour: "tumbling-fall", Pulse: "hurried-three"})
	if len(samples) == 0 || loudest(samples) < 0.5 {
		t.Fatalf("an unknown mark rendered %d silent samples", len(samples))
	}
	if len(pulseHits("hurried-three")) != 3 {
		t.Fatal("the count word should still be read")
	}
	if len(pulseHits("nonsense")) != 1 {
		t.Fatal("an unreadable pulse should still strike once")
	}
}

func TestContourAndPulseReadTheirOwnWords(t *testing.T) {
	if contourBend("level-hold")(0.5) != 1 {
		t.Fatal("a level contour should not bend")
	}
	if contourBend("falling-cut")(1) >= 1 {
		t.Fatal("a falling contour should fall")
	}
	if contourBend("widening-rise")(1) <= 1 {
		t.Fatal("a rising contour should rise")
	}
	if got := len(pulseHits("single-accent")); got != 1 {
		t.Fatalf("single-accent struck %d times", got)
	}
	if got := len(pulseHits("shimmering-three")); got != 3 {
		t.Fatalf("shimmering-three struck %d times", got)
	}
	// Syncopation moves the second hit rather than adding one.
	even := pulseHits("measured-two")
	off := pulseHits("syncopated-three")
	if len(off) != 3 || off[1].At <= even[1].At {
		t.Fatalf("syncopated hits = %+v", off)
	}
}

func TestEncodeWAVWritesAReadableHeader(t *testing.T) {
	body := EncodeWAV(Render(Mark{Timbre: "wood-block", Contour: "low-return", Pulse: "steady-pair"}))
	if string(body[0:4]) != "RIFF" || string(body[8:12]) != "WAVE" {
		t.Fatalf("header = %q", body[0:12])
	}
	if got := binary.LittleEndian.Uint32(body[24:28]); got != Rate {
		t.Fatalf("sample rate = %d, want %d", got, Rate)
	}
	if got := binary.LittleEndian.Uint32(body[40:44]); int(got)+44 != len(body) {
		t.Fatalf("data size %d does not match the file length %d", got, len(body))
	}
	// A launch sound sits under a 400 ms card, so a long tail is a defect.
	seconds := float64(binary.LittleEndian.Uint32(body[40:44])) / 2 / Rate
	if seconds > maxSpan+0.01 {
		t.Fatalf("sample runs %.2fs, over the %.2fs cap", seconds, maxSpan)
	}
}

func TestFileNameSanitizesAndRefusesTheUnusable(t *testing.T) {
	if got := FileName("Floor Tom/../x"); got != "floortomx.wav" {
		t.Fatalf("file name = %q", got)
	}
	if got := FileName("  "); got != "" {
		t.Fatalf("an empty timbre should have no file, got %q", got)
	}
}
