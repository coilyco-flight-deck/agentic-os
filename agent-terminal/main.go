// Command agent-terminal launches one statically branded Alacritty window.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/urfave/cli/v3"
)

const (
	overlayFormat       = "agent-compose.overlay.v1"
	overlaySchema       = 1
	launchFormat        = "agent-terminal.launch.v1"
	defaultExpression   = "acting"
	defaultOverlayBin   = "agent-compose"
	defaultAlacrittyBin = "alacritty"
)

type commandDeps struct {
	lookPath func(string) (string, error)
	output   func(context.Context, string, ...string) ([]byte, error)
	run      func(context.Context, string, ...string) error
}

func systemDeps() commandDeps {
	return commandDeps{
		lookPath: exec.LookPath,
		output: func(ctx context.Context, name string, args ...string) ([]byte, error) {
			cmd := exec.CommandContext(ctx, name, args...)
			raw, err := cmd.Output()
			if err == nil {
				return raw, nil
			}
			var detail string
			if exitErr, ok := err.(*exec.ExitError); ok {
				detail = strings.TrimSpace(string(exitErr.Stderr))
			}
			if detail != "" {
				return nil, fmt.Errorf("%s: %w", detail, err)
			}
			return nil, err
		},
		run: func(ctx context.Context, name string, args ...string) error {
			return exec.CommandContext(ctx, name, args...).Run()
		},
	}
}

func main() {
	cmd := newCommand(systemDeps())
	if err := cmd.Run(context.Background(), os.Args); err != nil {
		fmt.Fprintln(os.Stderr, "agent-terminal:", err)
		os.Exit(1)
	}
}

func defaultWorkingDirectory() string {
	if projectsRoot := strings.TrimSpace(os.Getenv("PROJECTS_ROOT")); projectsRoot != "" {
		return projectsRoot
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "."
	}
	return filepath.Join(home, "projects")
}

func newCommand(deps commandDeps) *cli.Command {
	return &cli.Command{
		Name:      "agent-terminal",
		Usage:     "launch one agent-compose branded Alacritty window",
		ArgsUsage: "-- <command> [arguments...]",
		Flags: []cli.Flag{
			&cli.StringFlag{Name: "role", Required: true, Usage: "canonical agent-compose role"},
			&cli.StringFlag{Name: "seat", Required: true, Usage: "canonical harness seat"},
			&cli.StringFlag{
				Name:  "expression",
				Value: defaultExpression,
				Usage: "caller-supplied renderer expression",
			},
			&cli.StringFlag{Name: "task-title", Usage: "human-readable repository or issue label"},
			&cli.StringFlag{
				Name:  "working-directory",
				Value: defaultWorkingDirectory(),
				Usage: "director working directory (defaults to the projects root)",
			},
			&cli.StringFlag{
				Name:    "agent-compose-bin",
				Value:   defaultOverlayBin,
				Sources: cli.EnvVars("AGENT_COMPOSE_BIN"),
			},
			&cli.StringFlag{
				Name:    "alacritty-bin",
				Value:   defaultAlacrittyBin,
				Sources: cli.EnvVars("ALACRITTY_BIN"),
			},
			&cli.BoolFlag{
				Name:  "dry-run",
				Usage: "print the resolved identity and launch arguments without opening a window",
			},
		},
		Action: func(ctx context.Context, cmd *cli.Command) error {
			child := argvAfterDash(os.Args)
			return runLaunch(ctx, launchRequest{
				Role:             cmd.String("role"),
				Seat:             cmd.String("seat"),
				Expression:       cmd.String("expression"),
				TaskTitle:        cmd.String("task-title"),
				WorkingDirectory: cmd.String("working-directory"),
				AgentComposeBin:  cmd.String("agent-compose-bin"),
				AlacrittyBin:     cmd.String("alacritty-bin"),
				Child:            child,
				DryRun:           cmd.Bool("dry-run"),
			}, deps, cmd.Root().Writer)
		},
	}
}

func runLaunch(
	ctx context.Context,
	request launchRequest,
	deps commandDeps,
	stdout io.Writer,
) error {
	if len(request.Child) == 0 {
		return fmt.Errorf("a child command is required after `--`")
	}
	cwd, err := validateWorkingDirectory(request.WorkingDirectory)
	if err != nil {
		return err
	}
	agentCompose, err := requireBinary(deps.lookPath, request.AgentComposeBin)
	if err != nil {
		return fmt.Errorf("agent-compose binary: %w", err)
	}
	raw, err := deps.output(ctx, agentCompose, overlayArgs(request)...)
	if err != nil {
		return fmt.Errorf("load identity overlay: %w", err)
	}
	identity, err := parseOverlay(raw, request)
	if err != nil {
		return err
	}
	plan, err := buildLaunchPlan(identity, request, cwd)
	if err != nil {
		return err
	}
	if request.DryRun {
		encoded, err := json.MarshalIndent(plan, "", "  ")
		if err != nil {
			return fmt.Errorf("marshal launch plan: %w", err)
		}
		_, err = fmt.Fprintf(stdout, "%s\n", encoded)
		return err
	}
	alacritty, err := requireBinary(deps.lookPath, request.AlacrittyBin)
	if err != nil {
		return fmt.Errorf("Alacritty binary: %w", err)
	}
	if err := deps.run(ctx, alacritty, plan.Arguments...); err != nil {
		return fmt.Errorf("launch Alacritty: %w", err)
	}
	return nil
}

func overlayArgs(request launchRequest) []string {
	return []string{
		"overlay",
		"--role", strings.TrimSpace(request.Role),
		"--seat", strings.TrimSpace(request.Seat),
		"--expression", strings.TrimSpace(request.Expression),
		"--json",
	}
}

func requireBinary(lookPath func(string) (string, error), name string) (string, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return "", fmt.Errorf("binary name is empty")
	}
	resolved, err := lookPath(name)
	if err != nil {
		return "", fmt.Errorf("%q was not found on PATH: %w", name, err)
	}
	return resolved, nil
}

func validateWorkingDirectory(value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("working directory is empty")
	}
	absolute, err := filepath.Abs(value)
	if err != nil {
		return "", fmt.Errorf("resolve working directory: %w", err)
	}
	info, err := os.Stat(absolute)
	if err != nil {
		return "", fmt.Errorf("inspect working directory %q: %w", absolute, err)
	}
	if !info.IsDir() {
		return "", fmt.Errorf("working directory %q is not a directory", absolute)
	}
	return absolute, nil
}

func argvAfterDash(argv []string) []string {
	for index, arg := range argv {
		if arg == "--" {
			return append([]string(nil), argv[index+1:]...)
		}
	}
	return nil
}
