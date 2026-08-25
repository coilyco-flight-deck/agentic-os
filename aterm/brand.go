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
)

var hexColorPattern = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)

type launchBrand struct {
	Title         string `json:"title"`
	Accent        string `json:"accent"`
	Background    string `json:"background"`
	SelectionText string `json:"selection_text"`
}

func buildBrand(document overlayDocument, taskTitle string) (launchBrand, error) {
	title, err := buildTitle(document, taskTitle)
	if err != nil {
		return launchBrand{}, err
	}
	accent := strings.ToLower(document.FavoriteColor)
	background, err := mixHex(baseBackground, accent, backgroundTint)
	if err != nil {
		return launchBrand{}, fmt.Errorf("derive background tint: %w", err)
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

func buildTitle(document overlayDocument, taskTitle string) (string, error) {
	parts := make([]string, 0, len(document.Personalities))
	for _, personality := range document.Personalities {
		if glyph := strings.TrimSpace(personality.Emblem.Glyph); glyph != "" {
			parts = append(parts, glyph)
		}
	}
	title := strings.TrimSpace(strings.Join(parts, " ") + " " + seatAnnotation(document))
	title += " // " + strings.TrimSpace(document.Expression)
	if taskTitle = strings.TrimSpace(taskTitle); taskTitle != "" {
		if containsControl(taskTitle) {
			return "", fmt.Errorf("task title contains a control character")
		}
		title += " // " + taskTitle
	}
	if containsControl(title) {
		return "", fmt.Errorf("derived title contains a control character")
	}
	if utf8.RuneCountInString(title) > maxTitleRunes {
		runes := []rune(title)
		title = string(runes[:maxTitleRunes-1]) + "…"
	}
	return title, nil
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
