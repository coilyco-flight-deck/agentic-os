package main

import (
	"fmt"
	"math"
	"regexp"
	"strconv"
	"strings"
	"unicode"
	"unicode/utf8"
)

const (
	baseBackground  = "#101216"
	lightForeground = "#f5f7fa"
	backgroundTint  = 0.08
	maxTitleRunes   = 120
	titleSeparator  = " // "
)

var hexColorPattern = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)

type launchBrand struct {
	Title         string `json:"title"`
	Accent        string `json:"accent"`
	Background    string `json:"background"`
	SelectionText string `json:"selection_text"`
}

func buildBrand(document overlayDocument, taskTitle, workspace string) (launchBrand, error) {
	title, err := buildTitle(document, taskTitle, workspace)
	if err != nil {
		return launchBrand{}, err
	}
	accent := strings.ToLower(document.FavoriteColor)
	background, err := windowBackground(document, accent)
	if err != nil {
		return launchBrand{}, err
	}
	selectionText, err := mostReadable(accent, baseBackground, lightForeground)
	if err != nil {
		return launchBrand{}, fmt.Errorf("derive selection text: %w", err)
	}
	return launchBrand{
		Title:         title,
		Accent:        accent,
		Background:    background,
		SelectionText: selectionText,
	}, nil
}

// The window manager truncates near 30 characters, so the segments run from
// the one that separates two windows to the one every window repeats.
func buildTitle(document overlayDocument, taskTitle, workspace string) (string, error) {
	if taskTitle = strings.TrimSpace(taskTitle); containsControl(taskTitle) {
		return "", fmt.Errorf("task title contains a control character")
	}
	glyphs := make([]string, 0, len(document.Personalities))
	for _, personality := range document.Personalities {
		if glyph := strings.TrimSpace(personality.Emblem.Glyph); glyph != "" {
			glyphs = append(glyphs, glyph)
		}
	}
	role := strings.TrimSpace(document.RoleDisplayName)
	if role == "" {
		role = strings.TrimSpace(document.Role)
	}
	segments := []string{
		strings.TrimSpace(workspace),
		taskTitle,
		role,
		strings.TrimSpace(strings.Join(glyphs, " ") + " " + seatName(document)),
		strings.TrimSpace(document.Expression),
	}
	present := make([]string, 0, len(segments))
	for _, segment := range segments {
		if segment != "" {
			present = append(present, segment)
		}
	}
	title := strings.Join(present, titleSeparator)
	if containsControl(title) {
		return "", fmt.Errorf("derived title contains a control character")
	}
	if utf8.RuneCountInString(title) > maxTitleRunes {
		runes := []rune(title)
		title = string(runes[:maxTitleRunes-1]) + "…"
	}
	return title, nil
}

// windowBackground prefers the roster-solved value, tinting only for an
// agent-compose too old to ship one. See docs/aterm.md.
func windowBackground(document overlayDocument, accent string) (string, error) {
	if solved := strings.ToLower(strings.TrimSpace(document.Background)); solved != "" {
		if !hexColorPattern.MatchString(solved) {
			return "", fmt.Errorf("the overlay background %q is not #RRGGBB", solved)
		}
		return solved, nil
	}
	background, err := mixHex(baseBackground, accent, backgroundTint)
	if err != nil {
		return "", fmt.Errorf("derive background tint: %w", err)
	}
	return background, nil
}

func containsControl(value string) bool {
	for _, char := range value {
		if unicode.IsControl(char) {
			return true
		}
	}
	return false
}

func mixHex(base, tint string, amount float64) (string, error) {
	baseRGB, err := parseHex(base)
	if err != nil {
		return "", err
	}
	tintRGB, err := parseHex(tint)
	if err != nil {
		return "", err
	}
	if amount < 0 || amount > 1 {
		return "", fmt.Errorf("mix amount %f is outside 0..1", amount)
	}
	mixed := [3]uint8{}
	for index := range mixed {
		value := float64(baseRGB[index])*(1-amount) + float64(tintRGB[index])*amount
		mixed[index] = uint8(math.Round(value))
	}
	return formatHex(mixed), nil
}

func mostReadable(background, dark, light string) (string, error) {
	backgroundRGB, err := parseHex(background)
	if err != nil {
		return "", err
	}
	darkRGB, err := parseHex(dark)
	if err != nil {
		return "", err
	}
	lightRGB, err := parseHex(light)
	if err != nil {
		return "", err
	}
	if contrastRatio(backgroundRGB, darkRGB) >= contrastRatio(backgroundRGB, lightRGB) {
		return strings.ToLower(dark), nil
	}
	return strings.ToLower(light), nil
}

func parseHex(value string) ([3]uint8, error) {
	if !hexColorPattern.MatchString(value) {
		return [3]uint8{}, fmt.Errorf("color %q is not #RRGGBB", value)
	}
	result := [3]uint8{}
	for index := range result {
		component, err := strconv.ParseUint(value[1+index*2:3+index*2], 16, 8)
		if err != nil {
			return [3]uint8{}, fmt.Errorf("parse color %q: %w", value, err)
		}
		result[index] = uint8(component)
	}
	return result, nil
}

func formatHex(value [3]uint8) string {
	return fmt.Sprintf("#%02x%02x%02x", value[0], value[1], value[2])
}

func contrastRatio(first, second [3]uint8) float64 {
	firstLuminance := relativeLuminance(first)
	secondLuminance := relativeLuminance(second)
	if firstLuminance < secondLuminance {
		firstLuminance, secondLuminance = secondLuminance, firstLuminance
	}
	return (firstLuminance + 0.05) / (secondLuminance + 0.05)
}

func relativeLuminance(value [3]uint8) float64 {
	channel := func(component uint8) float64 {
		normalized := float64(component) / 255
		if normalized <= 0.04045 {
			return normalized / 12.92
		}
		return math.Pow((normalized+0.055)/1.055, 2.4)
	}
	return 0.2126*channel(value[0]) + 0.7152*channel(value[1]) + 0.0722*channel(value[2])
}

// labDistance is the CIE76 difference between two colors. Hex distance says
// nothing about whether an eye can tell two windows apart. See docs/aterm.md.
func labDistance(first, second [3]uint8) float64 {
	firstLab, secondLab := cielab(first), cielab(second)
	total := 0.0
	for index := range firstLab {
		delta := firstLab[index] - secondLab[index]
		total += delta * delta
	}
	return math.Sqrt(total)
}

func cielab(value [3]uint8) [3]float64 {
	linear := func(component uint8) float64 {
		normalized := float64(component) / 255
		if normalized <= 0.04045 {
			return normalized / 12.92
		}
		return math.Pow((normalized+0.055)/1.055, 2.4)
	}
	red, green, blue := linear(value[0]), linear(value[1]), linear(value[2])
	// D65 white, the reference every sRGB screen is calibrated against.
	x := (red*0.4124 + green*0.3576 + blue*0.1805) / 0.95047
	y := red*0.2126 + green*0.7152 + blue*0.0722
	z := (red*0.0193 + green*0.1192 + blue*0.9505) / 1.08883
	shape := func(component float64) float64 {
		if component > 0.008856 {
			return math.Cbrt(component)
		}
		return 7.787*component + 16.0/116
	}
	fx, fy, fz := shape(x), shape(y), shape(z)
	return [3]float64{116*fy - 16, 500 * (fx - fy), 200 * (fy - fz)}
}
