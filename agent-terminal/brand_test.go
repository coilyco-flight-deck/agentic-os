package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

const directorOverlay = `{
  "format": "agent-compose.overlay.v1",
  "schema_version": 1,
  "person": "kai",
  "role": "director",
  "purpose": "Pair with the human on high level goals.",
  "seat": {
    "harness": "codex",
    "name": "solar director",
    "pronouns": "he"
  },
  "expression": "acting",
  "favorite_color": "#94974a",
  "personalities": [
    {"name": "bold", "color": "#e1514e", "emblem": {"glyph": "▲"}},
    {"name": "grounded", "color": "#5fa87a", "emblem": {"glyph": "◆"}},
    {"name": "diplomatic", "color": "#19a9b0", "emblem": {"glyph": "⇄"}}
  ]
}`

func directorRequest() launchRequest {
	return launchRequest{
		Role:             "director",
		Seat:             "codex",
		Expression:       "acting",
		TaskTitle:        "agentic-os#730",
		WorkingDirectory: ".",
		AgentComposeBin:  defaultOverlayBin,
		AlacrittyBin:     defaultAlacrittyBin,
		Child:            []string{"ward", "agent", "director", "--repo", "coilyco-flight-deck/agentic-os"},
	}
}

func TestBuildLaunchPlanUsesCanonicalIdentity(t *testing.T) {
	request := directorRequest()
	request.AlacrittyBin = "alacritty-preview"
	document, err := parseOverlay([]byte(directorOverlay), request)
	if err != nil {
		t.Fatal(err)
	}
	plan, err := buildLaunchPlan(document, request, "/workspace")
	if err != nil {
		t.Fatal(err)
	}
	if plan.Format != launchFormat {
		t.Fatalf("format = %q", plan.Format)
	}
	if plan.Identity.Name != "solar director" || plan.Identity.FavoriteColor != "#94974a" {
		t.Fatalf("identity = %+v", plan.Identity)
	}
	if plan.Brand.Title != "▲ ◆ ⇄ solar director · acting · agentic-os#730" {
		t.Fatalf("title = %q", plan.Brand.Title)
	}
	if plan.Brand.Background != "#1b1d1a" || plan.Brand.SelectionText != baseBackground {
		t.Fatalf("brand = %+v", plan.Brand)
	}
	if plan.Executable != "alacritty-preview" {
		t.Fatalf("executable = %q", plan.Executable)
	}
	if strings.Contains(strings.Join(plan.Arguments, ""), "\x1b") {
		t.Fatal("launch arguments contain an escape sequence")
	}
	wantTail := []string{
		"-e", "ward", "agent", "director", "--repo", "coilyco-flight-deck/agentic-os",
	}
	if !reflect.DeepEqual(plan.Arguments[len(plan.Arguments)-len(wantTail):], wantTail) {
		t.Fatalf("arguments tail = %#v", plan.Arguments)
	}
}

func TestParseOverlayRejectsContractAndSelectionDrift(t *testing.T) {
	request := directorRequest()
	for name, replace := range map[string][2]string{
		"format":     {`"agent-compose.overlay.v1"`, `"other"`},
		"schema":     {`"schema_version": 1`, `"schema_version": 2`},
		"role":       {`"role": "director"`, `"role": "engineer"`},
		"seat":       {`"harness": "codex"`, `"harness": "claude"`},
		"expression": {`"expression": "acting"`, `"expression": "blocked"`},
		"color":      {`"#94974a"`, `"olive"`},
	} {
		t.Run(name, func(t *testing.T) {
			raw := strings.Replace(directorOverlay, replace[0], replace[1], 1)
			if _, err := parseOverlay([]byte(raw), request); err == nil {
				t.Fatal("invalid overlay was accepted")
			}
		})
	}
}

func TestBuildTitleRejectsControlCharactersAndTruncates(t *testing.T) {
	request := directorRequest()
	document, err := parseOverlay([]byte(directorOverlay), request)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := buildTitle(document, "unsafe\nvalue"); err == nil {
		t.Fatal("control character was accepted")
	}
	title, err := buildTitle(document, strings.Repeat("x", 200))
	if err != nil {
		t.Fatal(err)
	}
	if len([]rune(title)) != maxTitleRunes || !strings.HasSuffix(title, "…") {
		t.Fatalf("truncated title = %q", title)
	}
}

func TestColorDerivationIsDeterministicAndReadable(t *testing.T) {
	first, err := mixHex(baseBackground, "#94974a", backgroundTint)
	if err != nil {
		t.Fatal(err)
	}
	second, err := mixHex(baseBackground, "#94974a", backgroundTint)
	if err != nil {
		t.Fatal(err)
	}
	if first != "#1b1d1a" || second != first {
		t.Fatalf("mixed colors = %q, %q", first, second)
	}
	text, err := mostReadable("#222222", baseBackground, lightForeground)
	if err != nil {
		t.Fatal(err)
	}
	if text != lightForeground {
		t.Fatalf("selection text = %q", text)
	}
}

func TestRunLaunchDryRunDoesNotRequireAlacritty(t *testing.T) {
	request := directorRequest()
	request.DryRun = true
	var lookedUp []string
	deps := commandDeps{
		lookPath: func(name string) (string, error) {
			lookedUp = append(lookedUp, name)
			if name == defaultOverlayBin {
				return "/bin/agent-compose", nil
			}
			return "", errors.New("missing")
		},
		output: func(_ context.Context, name string, args ...string) ([]byte, error) {
			if name != "/bin/agent-compose" || len(args) == 0 {
				t.Fatalf("overlay command = %q %#v", name, args)
			}
			return []byte(directorOverlay), nil
		},
		run: func(context.Context, string, ...string) error {
			t.Fatal("dry-run launched Alacritty")
			return nil
		},
	}
	var output strings.Builder
	if err := runLaunch(context.Background(), request, deps, &output); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(lookedUp, []string{defaultOverlayBin}) {
		t.Fatalf("binary lookups = %#v", lookedUp)
	}
	var plan launchPlan
	if err := json.Unmarshal([]byte(output.String()), &plan); err != nil {
		t.Fatalf("dry-run output: %v\n%s", err, output.String())
	}
	if plan.Identity.Name != "solar director" || plan.Executable != defaultAlacrittyBin {
		t.Fatalf("dry-run plan = %+v", plan)
	}
}

func TestRunLaunchValidatesChildDirectoryAndBinaries(t *testing.T) {
	request := directorRequest()
	request.Child = nil
	if err := runLaunch(context.Background(), request, commandDeps{}, &strings.Builder{}); err == nil {
		t.Fatal("empty child command was accepted")
	}

	request = directorRequest()
	file := filepath.Join(t.TempDir(), "not-a-directory")
	if err := os.WriteFile(file, []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}
	request.WorkingDirectory = file
	if err := runLaunch(context.Background(), request, commandDeps{}, &strings.Builder{}); err == nil {
		t.Fatal("file working directory was accepted")
	}

	request = directorRequest()
	deps := commandDeps{
		lookPath: func(string) (string, error) { return "", errors.New("missing") },
	}
	err := runLaunch(context.Background(), request, deps, &strings.Builder{})
	if err == nil || !strings.Contains(err.Error(), "agent-compose binary") {
		t.Fatalf("missing binary error = %v", err)
	}
}

func TestArgvAfterDash(t *testing.T) {
	got := argvAfterDash([]string{"agent-terminal", "--role", "director", "--", "ward", "agent"})
	want := []string{"ward", "agent"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("argvAfterDash = %#v", got)
	}
}
