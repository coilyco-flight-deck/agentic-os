// Package soundspec renders one personality's sound_mark into audio.
package soundspec

import (
	"bytes"
	"encoding/binary"
	"math"
	"strings"
)

const (
	Rate = 22050
	span = 0.42
	// A launch sound sits under a 400 ms card. A long tail outlives its moment.
	maxSpan   = 0.80
	peak      = 0.62
	Revision  = "agent-compose v2.54.0 sound_mark vocabulary"
	extension = ".wav"
)

type Mark struct {
	Timbre  string
	Contour string
	Pulse   string
}

type voice struct {
	Base     float64
	Partials []float64
	Gains    []float64
	Noise    float64
	Attack   float64
	Decay    float64
}

// voices is the timbre table. A timbre outside it still speaks, on a soft
// mallet pitched from its own name. See docs/aterm.md.
var voices = map[string]voice{
	"snare-crack": {Base: 320, Partials: []float64{1, 2.7}, Gains: []float64{0.4, 0.2}, Noise: 0.8, Attack: 0.001, Decay: 0.06},
	"glass-tap":   {Base: 1480, Partials: []float64{1, 2.76, 5.4}, Gains: []float64{1, 0.4, 0.15}, Noise: 0.06, Attack: 0.001, Decay: 0.09},
	"wood-block":  {Base: 780, Partials: []float64{1, 3.1}, Gains: []float64{1, 0.3}, Noise: 0.12, Attack: 0.001, Decay: 0.05},
	"celesta":     {Base: 1046, Partials: []float64{1, 2, 4, 5.4}, Gains: []float64{1, 0.5, 0.22, 0.1}, Attack: 0.004, Decay: 0.22},
	"hull-hum":    {Base: 82, Partials: []float64{1, 2, 3}, Gains: []float64{1, 0.35, 0.12}, Attack: 0.07, Decay: 0.34},
	"brass-swell": {Base: 233, Partials: []float64{1, 2, 3, 4, 5}, Gains: []float64{1, 0.6, 0.4, 0.25, 0.15}, Attack: 0.06, Decay: 0.26},
	"toy-piano":   {Base: 880, Partials: []float64{1, 3, 6.2}, Gains: []float64{1, 0.45, 0.12}, Attack: 0.002, Decay: 0.12},
	"low-gong":    {Base: 110, Partials: []float64{1, 2.4, 3.7, 5.1}, Gains: []float64{1, 0.45, 0.25, 0.12}, Attack: 0.006, Decay: 0.4},
	"floor-tom":   {Base: 98, Partials: []float64{1, 1.6}, Gains: []float64{1, 0.25}, Noise: 0.1, Attack: 0.002, Decay: 0.16},
	"felt-mallet": {Base: 392, Partials: []float64{1, 2, 3}, Gains: []float64{1, 0.3, 0.1}, Attack: 0.012, Decay: 0.2},
}

func voiceFor(timbre string) voice {
	if voice, found := voices[strings.ToLower(strings.TrimSpace(timbre))]; found {
		return voice
	}
	// Silence would be the quiet failure this whole channel exists to avoid.
	sum := 0
	for _, character := range timbre {
		sum = sum*31 + int(character)
	}
	if sum < 0 {
		sum = -sum
	}
	return voice{
		Base:     220 * math.Pow(2, float64(sum%12)/12),
		Partials: []float64{1, 2, 3},
		Gains:    []float64{1, 0.3, 0.1},
		Attack:   0.01,
		Decay:    0.18,
	}
}

// contourBend reads the direction word out of the contour, so a value the
// roster has not shipped still bends rather than sitting flat.
func contourBend(contour string) func(float64) float64 {
	words := strings.Split(strings.ToLower(strings.TrimSpace(contour)), "-")
	shape := func(float64) float64 { return 1 }
	for _, word := range words {
		switch word {
		case "falling", "descending", "descent", "cut", "cover":
			shape = func(t float64) float64 { return 1 - 0.35*t }
		case "rising", "rise", "widening", "expanding", "arc", "embrace":
			shape = func(t float64) float64 { return 1 + 0.30*t }
		case "return":
			shape = func(t float64) float64 { return 1 + 0.22*math.Sin(math.Pi*t) }
		case "zigzag":
			shape = func(t float64) float64 { return 1 + 0.18*math.Sin(3*math.Pi*t) + 0.2*t }
		case "level", "hold", "sustained":
			shape = func(float64) float64 { return 1 }
		case "low":
			shape = func(t float64) float64 { return 1 - 0.18*math.Sin(math.Pi*t) }
		}
	}
	return shape
}

type hit struct {
	At   float64
	Gain float64
}

// pulseHits reads the count word and the manner word, which is why a pulse
// nobody has shipped still has a rhythm.
func pulseHits(pulse string) []hit {
	words := strings.Split(strings.ToLower(strings.TrimSpace(pulse)), "-")
	count := 1
	gain := 1.0
	spread := 0.34
	syncopate := false
	for _, word := range words {
		switch word {
		case "single":
			count = 1
		case "two", "pair":
			count = 2
		case "three":
			count = 3
		case "driving":
			spread = 0.22
		case "guarded", "measured":
			spread = 0.44
		case "syncopated":
			syncopate = true
		case "gentle", "shimmering", "soft":
			gain = 0.7
		case "slow", "long", "swell":
			count = 1
			gain = 0.85
		}
	}
	hits := make([]hit, 0, count)
	for index := 0; index < count; index++ {
		at := float64(index) * spread
		if syncopate && index == 1 {
			at += spread * 0.4
		}
		hits = append(hits, hit{At: at, Gain: gain * (1 - 0.18*float64(index))})
	}
	return hits
}

// Render turns one personality's sound_mark into samples. Rendering is
// deterministic, so the shipped files can be auditioned and rejected by ear.
func Render(mark Mark) []float64 {
	voice := voiceFor(mark.Timbre)
	bend := contourBend(mark.Contour)
	hits := pulseHits(mark.Pulse)
	length := span
	if len(hits) > 0 {
		if last := hits[len(hits)-1].At + voice.Attack + voice.Decay*3; last > length {
			length = math.Min(last, maxSpan)
		}
	}
	samples := make([]float64, int(length*Rate))
	noise := newNoise(mark.Timbre)
	for _, hit := range hits {
		start := int(hit.At * Rate)
		phase := 0.0
		for index := start; index < len(samples); index++ {
			elapsed := float64(index-start) / Rate
			amplitude := hitEnvelope(elapsed, voice)
			// The attack starts at zero, so the silence test only applies once
			// the note is past it. Otherwise every hit breaks on its first sample.
			if elapsed > voice.Attack && amplitude < 0.0005 {
				break
			}
			progress := math.Min(elapsed/length, 1)
			frequency := voice.Base * bend(progress)
			phase += 2 * math.Pi * frequency / Rate
			value := 0.0
			for partial, ratio := range voice.Partials {
				value += voice.Gains[partial] * math.Sin(phase*ratio)
			}
			if voice.Noise > 0 {
				value += voice.Noise * noise()
			}
			samples[index] += value * amplitude * hit.Gain
		}
	}
	return normalize(samples)
}

func hitEnvelope(elapsed float64, voice voice) float64 {
	if elapsed < 0 {
		return 0
	}
	if voice.Attack > 0 && elapsed < voice.Attack {
		return elapsed / voice.Attack
	}
	return math.Exp(-(elapsed - voice.Attack) / voice.Decay)
}

// newNoise is seeded from the timbre so a rendered file is byte-identical
// on every host, which is what makes the shipped samples reviewable.
func newNoise(seed string) func() float64 {
	state := uint32(2463534242)
	for _, character := range seed {
		state ^= uint32(character)
		state *= 16777619
	}
	return func() float64 {
		state ^= state << 13
		state ^= state >> 17
		state ^= state << 5
		return float64(int32(state)) / float64(math.MaxInt32)
	}
}

func normalize(samples []float64) []float64 {
	loudest := 0.0
	for _, sample := range samples {
		if magnitude := math.Abs(sample); magnitude > loudest {
			loudest = magnitude
		}
	}
	if loudest == 0 {
		return samples
	}
	scale := peak / loudest
	for index := range samples {
		samples[index] *= scale
	}
	return samples
}

func EncodeWAV(samples []float64) []byte {
	body := &bytes.Buffer{}
	for _, sample := range samples {
		clamped := math.Max(-1, math.Min(1, sample))
		_ = binary.Write(body, binary.LittleEndian, int16(clamped*32767))
	}
	out := &bytes.Buffer{}
	out.WriteString("RIFF")
	_ = binary.Write(out, binary.LittleEndian, uint32(36+body.Len()))
	out.WriteString("WAVEfmt ")
	_ = binary.Write(out, binary.LittleEndian, uint32(16))
	_ = binary.Write(out, binary.LittleEndian, uint16(1))
	_ = binary.Write(out, binary.LittleEndian, uint16(1))
	_ = binary.Write(out, binary.LittleEndian, uint32(Rate))
	_ = binary.Write(out, binary.LittleEndian, uint32(Rate*2))
	_ = binary.Write(out, binary.LittleEndian, uint16(2))
	_ = binary.Write(out, binary.LittleEndian, uint16(16))
	out.WriteString("data")
	_ = binary.Write(out, binary.LittleEndian, uint32(body.Len()))
	out.Write(body.Bytes())
	return out.Bytes()
}

// FileName keys the shipped sample by timbre, which is unique across the
// roster and is the field that decides the voice.
func FileName(timbre string) string {
	safe := strings.Map(func(character rune) rune {
		switch {
		case character >= 'a' && character <= 'z', character >= '0' && character <= '9', character == '-':
			return character
		case character >= 'A' && character <= 'Z':
			return character + 32
		default:
			return -1
		}
	}, strings.TrimSpace(timbre))
	if safe == "" {
		return ""
	}
	return safe + extension
}
