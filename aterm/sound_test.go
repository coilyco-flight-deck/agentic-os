package main

import (
	"encoding/binary"
	"os"
	"strings"
	"testing"

	"forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/aterm/internal/soundspec"
)

// Every sample the binary carries has to be a real file, or a launch plays
// nothing and says nothing about why.
func TestEmbeddedSamplesAreUsableWAVs(t *testing.T) {
	entries, err := soundSamples.ReadDir("sounds")
	if err != nil {
		t.Fatalf("read the embedded samples: %v", err)
	}
	if len(entries) == 0 {
		t.Fatal("no samples are embedded")
	}
	for _, entry := range entries {
		body, err := soundSamples.ReadFile("sounds/" + entry.Name())
		if err != nil {
			t.Fatalf("read %s: %v", entry.Name(), err)
		}
		if len(body) < 44 || string(body[0:4]) != "RIFF" {
			t.Fatalf("%s is not a WAV", entry.Name())
		}
		if binary.LittleEndian.Uint32(body[40:44]) == 0 {
			t.Fatalf("%s carries no audio", entry.Name())
		}
	}
}

// The fixtures are real overlay captures, so a timbre they ship with no sample
// means `just aterm-sounds` was not run after the vocabulary moved.
func TestTheFixtureTimbresAllHaveASample(t *testing.T) {
	for _, name := range []string{"platform-claude-overlay.json", "tpm-codex-overlay.json"} {
		role, seat := "platform", "claude"
		if strings.HasPrefix(name, "tpm") {
			role, seat = "tpm", "codex"
		}
		document, err := parseOverlay(fixture(t, name), role, seat, "acting")
		if err != nil {
			t.Fatalf("parse %s: %v", name, err)
		}
		for _, personality := range document.Personalities {
			file := soundspec.FileName(personality.SoundMark.Timbre)
			if file == "" {
				t.Fatalf("%s ships an unusable timbre %q", personality.Name, personality.SoundMark.Timbre)
			}
			if _, err := soundSamples.ReadFile("sounds/" + file); err != nil {
				t.Fatalf("%s ships timbre %q with no sample: run `just aterm-sounds`",
					personality.Name, personality.SoundMark.Timbre)
			}
		}
	}
}

func TestTheCardCarriesTheSoundMark(t *testing.T) {
	document := platformOverlay(t)
	card := buildSessionCard(document, launchPlan{})
	if len(card.Figures) != len(document.Personalities) {
		t.Fatalf("figures = %d", len(card.Figures))
	}
	for index, figure := range card.Figures {
		want := document.Personalities[index].SoundMark
		if figure.Timbre != want.Timbre || figure.Contour != want.Contour || figure.Pulse != want.Pulse {
			t.Fatalf("figure %d = %+v, want %+v", index, figure, want)
		}
	}
}

func TestASessionCanBeSilenced(t *testing.T) {
	if soundWanted(nil, false) {
		t.Fatal("a nil stdout is not a terminal")
	}
	if soundWanted(os.Stdout, true) {
		t.Fatal("--silent should win")
	}
	t.Setenv(silentEnv, "1")
	if soundWanted(os.Stdout, false) {
		t.Fatalf("%s should win", silentEnv)
	}
}

// Silence must cost nothing: no player resolved, no sample written.
func TestSilencePlaysAndCachesNothing(t *testing.T) {
	t.Setenv("XDG_CACHE_HOME", t.TempDir())
	playSoundMark(buildSessionCard(platformOverlay(t), launchPlan{}), false)
	entries, err := os.ReadDir(t.TempDir())
	if err == nil && len(entries) != 0 {
		t.Fatalf("a silenced launch wrote %d file(s)", len(entries))
	}
}

func TestSessionStageAcceptsSilent(t *testing.T) {
	options, err := parseSessionArgs([]string{"--silent", "--no-motion", "--", "true"})
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if options.Audible || options.Motion {
		t.Fatalf("options = %+v, want both channels off", options)
	}
}
