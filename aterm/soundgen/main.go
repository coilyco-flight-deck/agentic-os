// Command soundgen renders the shipped sound-mark samples from the live roster.
//
// Run it through `just aterm-sounds`. The output is committed so a sample can
// be auditioned and rejected by ear before it ships. See docs/aterm.md.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"

	"forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/aterm/internal/soundspec"
)

type catalogRole struct {
	Slug  string `json:"slug"`
	Seats []struct {
		Harness string `json:"harness"`
	} `json:"seats"`
}

type catalog struct {
	Items []catalogRole `json:"items"`
}

type overlay struct {
	Personalities []struct {
		Name      string `json:"name"`
		SoundMark struct {
			Timbre  string `json:"timbre"`
			Contour string `json:"contour"`
			Pulse   string `json:"pulse"`
		} `json:"sound_mark"`
	} `json:"personalities"`
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "soundgen:", err)
		os.Exit(1)
	}
}

func run() error {
	target := "sounds"
	if len(os.Args) > 1 {
		target = os.Args[1]
	}
	binary := os.Getenv("AGENT_COMPOSE_BIN")
	if binary == "" {
		binary = "agent-compose"
	}
	raw, err := exec.Command(binary, "catalog", "roles", "--json").Output()
	if err != nil {
		return fmt.Errorf("read the roster: %w", err)
	}
	var roles catalog
	if err := json.Unmarshal(raw, &roles); err != nil {
		return fmt.Errorf("decode the roster: %w", err)
	}
	marks := map[string]soundspec.Mark{}
	names := map[string]string{}
	for _, role := range roles.Items {
		seat := ""
		for _, candidate := range role.Seats {
			if candidate.Harness == "claude" || candidate.Harness == "codex" {
				seat = candidate.Harness
				break
			}
		}
		if seat == "" {
			continue
		}
		raw, err := exec.Command(binary, "overlay",
			"--role", role.Slug, "--seat", seat, "--expression", "acting", "--json").Output()
		if err != nil {
			return fmt.Errorf("read the %s overlay: %w", role.Slug, err)
		}
		var document overlay
		if err := json.Unmarshal(raw, &document); err != nil {
			return fmt.Errorf("decode the %s overlay: %w", role.Slug, err)
		}
		for _, personality := range document.Personalities {
			mark := soundspec.Mark{
				Timbre:  personality.SoundMark.Timbre,
				Contour: personality.SoundMark.Contour,
				Pulse:   personality.SoundMark.Pulse,
			}
			if soundspec.FileName(mark.Timbre) == "" {
				continue
			}
			marks[mark.Timbre] = mark
			names[mark.Timbre] = personality.Name
		}
	}
	if len(marks) == 0 {
		return fmt.Errorf("the roster shipped no sound marks")
	}
	if err := os.MkdirAll(target, 0o755); err != nil {
		return err
	}
	timbres := make([]string, 0, len(marks))
	for timbre := range marks {
		timbres = append(timbres, timbre)
	}
	sort.Strings(timbres)
	for _, timbre := range timbres {
		mark := marks[timbre]
		path := filepath.Join(target, soundspec.FileName(timbre))
		if err := os.WriteFile(path, soundspec.EncodeWAV(soundspec.Render(mark)), 0o644); err != nil {
			return err
		}
		fmt.Printf("%-14s %-12s %-18s %s\n", names[timbre], mark.Timbre, mark.Contour, mark.Pulse)
	}
	fmt.Printf("%d sample(s) in %s, rendered from %s\n", len(timbres), target, soundspec.Revision)
	return nil
}
