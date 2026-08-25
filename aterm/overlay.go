package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

const (
	overlayFormat = "agent-compose.overlay.v1"
	overlaySchema = 1
)

type overlaySeat struct {
	Harness  string `json:"harness"`
	Name     string `json:"name"`
	Pronouns string `json:"pronouns"`
}

type overlayEmblem struct {
	Glyph string `json:"glyph"`
}

type overlayPersonality struct {
	Name   string        `json:"name"`
	Color  string        `json:"color"`
	Emblem overlayEmblem `json:"emblem"`
}

type overlayDocument struct {
	Format          string               `json:"format"`
	SchemaVersion   int                  `json:"schema_version"`
	Person          string               `json:"person"`
	Role            string               `json:"role"`
	RoleDisplayName string               `json:"role_display_name"`
	Purpose         string               `json:"purpose"`
	Seat            overlaySeat          `json:"seat"`
	Annotation      string               `json:"annotation"`
	Expression      string               `json:"expression"`
	FavoriteColor   string               `json:"favorite_color"`
	Personalities   []overlayPersonality `json:"personalities"`
}

func loadOverlay(
	ctx context.Context,
	deps commandDeps,
	agentCompose string,
	role string,
	seat string,
	expression string,
) (overlayDocument, error) {
	raw, err := deps.output(
		ctx,
		agentCompose,
		"overlay",
		"--role", role,
		"--seat", seat,
		"--expression", expression,
		"--json",
	)
	if err != nil {
		return overlayDocument{}, fmt.Errorf("load the identity overlay: %w", err)
	}
	return parseOverlay(raw, role, seat, expression)
}

func parseOverlay(raw []byte, role, seat, expression string) (overlayDocument, error) {
	var document overlayDocument
	if err := json.Unmarshal(raw, &document); err != nil {
		return overlayDocument{}, fmt.Errorf("decode the identity overlay: %w", err)
	}
	if document.Format != overlayFormat || document.SchemaVersion != overlaySchema {
		return overlayDocument{}, fmt.Errorf(
			"the identity overlay has unsupported contract %q schema %d",
			document.Format,
			document.SchemaVersion,
		)
	}
	if document.Role != strings.TrimSpace(role) {
		return overlayDocument{}, fmt.Errorf(
			"the identity overlay role %q does not match requested role %q",
			document.Role,
			role,
		)
	}
	if document.Seat.Harness != strings.TrimSpace(seat) {
		return overlayDocument{}, fmt.Errorf(
			"the identity overlay seat %q does not match requested seat %q",
			document.Seat.Harness,
			seat,
		)
	}
	if document.Expression != strings.TrimSpace(expression) {
		return overlayDocument{}, fmt.Errorf(
			"the identity overlay expression %q does not match requested expression %q",
			document.Expression,
			expression,
		)
	}
	if strings.TrimSpace(document.Person) == "" || strings.TrimSpace(document.Seat.Name) == "" {
		return overlayDocument{}, fmt.Errorf("the identity overlay is missing person or seat name")
	}
	if !hexColorPattern.MatchString(document.FavoriteColor) {
		return overlayDocument{}, fmt.Errorf(
			"the identity overlay favorite color %q is not #RRGGBB",
			document.FavoriteColor,
		)
	}
	return document, nil
}

// seatAnnotation prefers the string agent-compose composed, so the window title,
// the harness prompt box, and the status row all read the same identity.
func seatAnnotation(document overlayDocument) string {
	if annotation := strings.TrimSpace(document.Annotation); annotation != "" {
		return annotation
	}
	name := strings.TrimSpace(document.Seat.Name)
	if name == "" {
		return ""
	}
	subject, _, _ := strings.Cut(strings.TrimSpace(document.Seat.Pronouns), "/")
	if subject = strings.TrimSpace(subject); subject != "" {
		name += " [" + subject + "]"
	}
	label := strings.TrimSpace(document.RoleDisplayName)
	if label == "" {
		label = strings.TrimSpace(document.Role)
	}
	if label != "" {
		name += " (" + label + ")"
	}
	return name
}
