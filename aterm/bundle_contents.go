package main

import (
	"fmt"
	"io"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

const (
	plistPreamble = `<?xml version="1.0" encoding="UTF-8"?>` + "\n" +
		`<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ` +
		`"http://www.apple.com/DTDs/PropertyList-1.0.dtd">` + "\n" +
		`<plist version="1.0">` + "\n<dict>\n"
	plistEpilogue    = "</dict>\n</plist>\n"
	bundleFieldWidth = 11
)

var (
	bundleHeadingStyle = lipgloss.NewStyle().Bold(true)
	bundleLabelStyle   = lipgloss.NewStyle().Faint(true).Width(bundleFieldWidth)
)

// bundleInfoPlist describes the wrapper rather than the session. LSUIElement
// keeps it off the Dock, so only the window it opens claims a tile there.
func bundleInfoPlist(spec bundleSpec) string {
	body := &strings.Builder{}
	write := func(key, value string) {
		fmt.Fprintf(body, "\t<key>%s</key>\n\t<string>%s</string>\n", key, xmlEscape(value))
	}
	write("CFBundleDevelopmentRegion", "en")
	write("CFBundleExecutable", spec.executable())
	write("CFBundleGetInfoString", spec.Person+" // "+spec.DisplayName)
	write("CFBundleIdentifier", spec.identifier())
	write("CFBundleInfoDictionaryVersion", "6.0")
	write("CFBundleName", spec.displayName())
	write("CFBundleDisplayName", spec.displayName())
	write("CFBundlePackageType", "APPL")
	write("CFBundleShortVersionString", spec.Version)
	write("CFBundleVersion", spec.Version)
	if spec.Icon {
		write("CFBundleIconFile", bundleIconName)
	}
	write("ATermRole", spec.Role)
	body.WriteString("\t<key>LSUIElement</key>\n\t<true/>\n")
	return plistPreamble + body.String() + plistEpilogue
}

// bundleLauncher rebuilds the environment a Finder launch does not get, PATH
// included, since `agent-compose launch` resolves the harness. See docs/aterm.md.
func bundleLauncher(spec bundleSpec) string {
	invocation := strings.Join([]string{
		shellQuote(spec.ATermBin),
		"--working-directory", shellQuote(spec.WorkingDirectory),
		shellQuote(spec.Role),
		`"$@"`,
	}, " ")
	lines := []string{
		"#!/bin/sh",
		bundleMarker,
		"# Regenerate rather than editing: `aterm bundles`.",
		"set -u",
		"",
		"baked=" + shellQuote(spec.BakedPath),
		// A login shell keeps PATH current as tools move, and the baked copy
		// covers a profile that fails or never exports one.
		`live=$(/bin/zsh -lc 'printf %s "$PATH"' 2>/dev/null) || live=''`,
		`if [ -n "$live" ]; then PATH="$live:$baked"; else PATH="$baked"; fi`,
		"export PATH",
		"",
		"AGENT_COMPOSE_BIN=" + shellQuote(spec.AgentComposeBin),
		"AOS_BIN=" + shellQuote(spec.AOSBin),
		"ATERM_TERMINAL_BIN=" + shellQuote(spec.TerminalBin),
		"export AGENT_COMPOSE_BIN AOS_BIN ATERM_TERMINAL_BIN",
		"",
		`log=$(mktemp -t aterm-bundle) || exit 1`,
		"if " + invocation + ` >"$log" 2>&1; then`,
		"\trm -f \"$log\"",
		"\texit 0",
		"fi",
		"",
		// A window that never opened leaves nothing on screen to read, so the
		// failure gets an alert instead of a silent non-zero exit.
		`detail=$(cat "$log")`,
		`rm -f "$log"`,
		`osascript -e 'on run argv' \`,
		"\t-e 'display alert (item 1 of argv) message (item 2 of argv) as critical' \\",
		"\t-e 'end run' " + shellQuote(spec.displayName()+" could not launch") + ` "$detail" >/dev/null 2>&1`,
		"exit 1",
	}
	return strings.Join(lines, "\n") + "\n"
}

func shellQuote(value string) string {
	return "'" + strings.ReplaceAll(value, "'", `'\''`) + "'"
}

func xmlEscape(value string) string {
	replacer := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		`"`, "&quot;",
	)
	return replacer.Replace(value)
}

// renderBundlePlan is the operator's half of `bundles --dry-run`. Checking
// where seven apps land reads better as a list than as JSON. See docs/aterm.md.
func renderBundlePlan(writer io.Writer, plan bundlePlan) error {
	lines := &strings.Builder{}
	fmt.Fprintf(lines, "%s\n", bundleHeadingStyle.Render(plan.Output))
	icon := plan.Icon
	if icon == "" {
		icon = "none, the system app icon"
	}
	fmt.Fprintf(lines, "  %s%s\n", bundleLabelStyle.Render("icon"), icon)
	for _, item := range plan.Items {
		fmt.Fprintf(lines, "  %s%s\n", bundleLabelStyle.Render(item.Role), item.Name)
	}
	for _, path := range plan.Stale {
		fmt.Fprintf(lines, "  %s%s\n", bundleLabelStyle.Render("stale"), filepath.Base(path))
	}
	_, err := io.WriteString(writer, lines.String())
	return err
}
