package main

import (
	"bytes"
	"context"
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/urfave/cli/v3"
)

const harnessBoardFormat = "agentic-os.role-harness-board.v1"
const localLaneProfileFormat = "agentic-os.local-lane-profile.v1"

//go:embed role-harnesses.json
var embeddedHarnessBoard []byte

type harnessLane struct {
	Intent  string `json:"intent"`
	Harness string `json:"harness"`
}

type harnessRole struct {
	Role    string        `json:"role"`
	Intents []harnessLane `json:"intents"`
}

type harnessBoard struct {
	Format     string        `json:"format"`
	RoleSource string        `json:"role_source"`
	RoleCount  int           `json:"role_count"`
	LaneCount  int           `json:"lane_count"`
	Roles      []harnessRole `json:"roles"`
}

type laneProjection struct {
	Role    string `json:"role"`
	Intent  string `json:"intent"`
	Harness string `json:"harness"`
	Route   string `json:"route"`
}

func loadHarnessBoard(data []byte) (harnessBoard, error) {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	var board harnessBoard
	if err := decoder.Decode(&board); err != nil {
		return harnessBoard{}, fmt.Errorf("decode embedded harness board: %w", err)
	}
	if err := ensureJSONEnd(decoder); err != nil {
		return harnessBoard{}, err
	}
	if board.Format != harnessBoardFormat {
		return harnessBoard{}, fmt.Errorf("unsupported harness board format %q", board.Format)
	}
	if strings.TrimSpace(board.RoleSource) == "" {
		return harnessBoard{}, errors.New("harness board role_source is empty")
	}
	if board.RoleCount != len(board.Roles) {
		return harnessBoard{}, fmt.Errorf(
			"harness board role_count is %d, found %d roles",
			board.RoleCount,
			len(board.Roles),
		)
	}
	if board.RoleCount == 0 {
		return harnessBoard{}, errors.New("harness board contains no roles")
	}

	roles := make(map[string]struct{}, len(board.Roles))
	laneCount := 0
	for _, role := range board.Roles {
		if strings.TrimSpace(role.Role) == "" {
			return harnessBoard{}, errors.New("harness board contains an empty role")
		}
		if _, exists := roles[role.Role]; exists {
			return harnessBoard{}, fmt.Errorf("harness board repeats role %q", role.Role)
		}
		roles[role.Role] = struct{}{}
		if len(role.Intents) < 1 || len(role.Intents) > 2 {
			return harnessBoard{}, fmt.Errorf(
				"harness board role %q has %d intents, want one or two",
				role.Role,
				len(role.Intents),
			)
		}
		intents := make(map[string]struct{}, len(role.Intents))
		for _, lane := range role.Intents {
			if strings.TrimSpace(lane.Intent) == "" || strings.TrimSpace(lane.Harness) == "" {
				return harnessBoard{}, fmt.Errorf(
					"harness board %s contains an empty intent or harness",
					role.Role,
				)
			}
			if _, exists := intents[lane.Intent]; exists {
				return harnessBoard{}, fmt.Errorf(
					"harness board repeats lane %s/%s",
					role.Role,
					lane.Intent,
				)
			}
			intents[lane.Intent] = struct{}{}
			laneCount++
		}
	}
	if board.LaneCount != laneCount {
		return harnessBoard{}, fmt.Errorf(
			"harness board lane_count is %d, found %d lanes",
			board.LaneCount,
			laneCount,
		)
	}
	return board, nil
}

func ensureJSONEnd(decoder *json.Decoder) error {
	var extra any
	err := decoder.Decode(&extra)
	if errors.Is(err, io.EOF) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("decode embedded harness board trailer: %w", err)
	}
	return errors.New("embedded harness board contains multiple JSON values")
}

func resolveHarnessDefault(board harnessBoard, role, intent string) (string, error) {
	lane, err := resolveLaneDefault(board, role, intent)
	if err != nil {
		return "", err
	}
	return lane.Harness, nil
}

func resolveLaneDefault(board harnessBoard, role, intent string) (laneProjection, error) {
	for _, candidate := range board.Roles {
		if candidate.Role != role {
			continue
		}
		for _, lane := range candidate.Intents {
			if lane.Intent == intent {
				return laneProjection{
					Role:    role,
					Intent:  intent,
					Harness: lane.Harness,
					Route:   role + "/" + intent,
				}, nil
			}
		}
		return laneProjection{}, fmt.Errorf("role %q has no intent %q", role, intent)
	}
	return laneProjection{}, fmt.Errorf("unknown role %q", role)
}

func runHarnessDefault(_ context.Context, cmd *cli.Command) error {
	role := strings.TrimSpace(cmd.String("role"))
	if role == "" {
		return errors.New("harness-default needs --role")
	}
	intent := strings.TrimSpace(cmd.String("intent"))
	if intent == "" {
		return errors.New("harness-default needs --intent")
	}
	board, err := loadHarnessBoard(embeddedHarnessBoard)
	if err != nil {
		return err
	}
	harness, err := resolveHarnessDefault(board, role, intent)
	if err != nil {
		return err
	}
	fmt.Fprintln(cmd.Root().Writer, harness)
	return nil
}

func runLaneDefault(_ context.Context, cmd *cli.Command) error {
	role := strings.TrimSpace(cmd.String("role"))
	if role == "" {
		return errors.New("lane-default needs --role")
	}
	intent := strings.TrimSpace(cmd.String("intent"))
	if intent == "" {
		return errors.New("lane-default needs --intent")
	}
	board, err := loadHarnessBoard(embeddedHarnessBoard)
	if err != nil {
		return err
	}
	lane, err := resolveLaneDefault(board, role, intent)
	if err != nil {
		return err
	}
	if path := strings.TrimSpace(cmd.String("profile")); path != "" {
		if err := writeLocalLaneProfile(path, lane); err != nil {
			return err
		}
	}
	encoder := json.NewEncoder(cmd.Root().Writer)
	encoder.SetEscapeHTML(false)
	return encoder.Encode(lane)
}

func writeLocalLaneProfile(path string, lane laneProjection) error {
	profile := map[string]any{}
	mode := os.FileMode(0o600)
	current, err := os.ReadFile(path)
	switch {
	case err == nil:
		info, statErr := os.Lstat(path)
		if statErr != nil {
			return fmt.Errorf("stat local lane profile: %w", statErr)
		}
		if !info.Mode().IsRegular() {
			return errors.New("local lane profile is not a regular file")
		}
		mode = info.Mode().Perm()
		if decodeErr := json.Unmarshal(current, &profile); decodeErr != nil {
			return fmt.Errorf("decode local lane profile: %w", decodeErr)
		}
		if profile["format"] != localLaneProfileFormat {
			return fmt.Errorf("refuse to replace non-AOS local profile %q", path)
		}
	case errors.Is(err, os.ErrNotExist):
	default:
		return fmt.Errorf("read local lane profile: %w", err)
	}

	request, ok := profile["request"].(map[string]any)
	if profile["request"] != nil && !ok {
		return errors.New("local lane profile request must be an object")
	}
	if !ok {
		request = map[string]any{}
	}
	request["provider"] = "agent-proxy"
	request["model"] = lane.Route
	profile["format"] = localLaneProfileFormat
	profile["role"] = lane.Role
	profile["intent"] = lane.Intent
	profile["harness"] = lane.Harness
	profile["route"] = lane.Route
	profile["request"] = request

	rendered, err := json.MarshalIndent(profile, "", "  ")
	if err != nil {
		return fmt.Errorf("encode local lane profile: %w", err)
	}
	rendered = append(rendered, '\n')
	if bytes.Equal(current, rendered) {
		return nil
	}
	return replaceLocalLaneProfile(path, rendered, mode)
}

func replaceLocalLaneProfile(path string, rendered []byte, mode os.FileMode) error {
	directory := filepath.Dir(path)
	if err := os.MkdirAll(directory, 0o700); err != nil {
		return fmt.Errorf("create local lane profile directory: %w", err)
	}
	file, err := os.CreateTemp(directory, "."+filepath.Base(path)+".*")
	if err != nil {
		return fmt.Errorf("create local lane profile staging file: %w", err)
	}
	staging := file.Name()
	defer os.Remove(staging)
	if err := file.Chmod(mode); err != nil {
		file.Close()
		return fmt.Errorf("protect local lane profile staging file: %w", err)
	}
	if _, err := file.Write(rendered); err != nil {
		file.Close()
		return fmt.Errorf("write local lane profile staging file: %w", err)
	}
	if err := file.Sync(); err != nil {
		file.Close()
		return fmt.Errorf("sync local lane profile staging file: %w", err)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("close local lane profile staging file: %w", err)
	}
	if err := os.Rename(staging, path); err != nil {
		return fmt.Errorf("replace local lane profile: %w", err)
	}
	return nil
}
