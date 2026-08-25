// Command aterm launches one composed agent session in its own branded window.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/urfave/cli/v3"
)

var version = "dev"

const (
	defaultExpression    = "acting"
	defaultOverlayBin    = "agent-compose"
	defaultAOSBin        = "aos"
	defaultAlacrittyBin  = "alacritty"
	defaultWorkingEnvVar = "PROJECTS_ROOT"
)

type commandDeps struct {
	lookPath func(string) (string, error)
	output   func(context.Context, string, ...string) ([]byte, error)
	run      func(context.Context, string, ...string) error
	spawn    func(context.Context, string, ...string) error
	self     func() (string, error)
	pick     func(rosterDocument) (string, string, error)
	tty      func() bool
}

func systemDeps() commandDeps {
	return commandDeps{
		lookPath: exec.LookPath,
		output: func(ctx context.Context, name string, args ...string) ([]byte, error) {
			raw, err := exec.CommandContext(ctx, name, args...).Output()
			if err == nil {
				return raw, nil
			}
			var exitErr *exec.ExitError
			if errors.As(err, &exitErr) {
				if detail := strings.TrimSpace(string(exitErr.Stderr)); detail != "" {
					return nil, fmt.Errorf("%s", detail)
				}
			}
			return nil, err
		},
		run: func(ctx context.Context, name string, args ...string) error {
			return exec.CommandContext(ctx, name, args...).Run()
		},
		spawn: func(_ context.Context, name string, args ...string) error {
			return spawnWindow(name, args)
		},
		self: os.Executable,
		pick: pickRoleAndSeat,
		tty:  func() bool { return interactiveTTY(os.Stdin, os.Stdout) },
	}
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == sessionCommand {
		hold, argv, err := parseSessionArgs(os.Args[2:])
		if err != nil {
			fmt.Fprintln(os.Stderr, "aterm:", err)
			os.Exit(2)
		}
		os.Exit(runSession(argv, hold, os.Stdin, os.Stdout, os.Stderr))
	}
	if err := newCommand(systemDeps()).Run(context.Background(), os.Args); err != nil {
		fmt.Fprintln(os.Stderr, "aterm:", err)
		os.Exit(1)
	}
}

func defaultWorkingDirectory() string {
	if projectsRoot := strings.TrimSpace(os.Getenv(defaultWorkingEnvVar)); projectsRoot != "" {
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
		Name:      "aterm",
		Usage:     "launch one composed agent session in its own branded window",
		ArgsUsage: "[role] [seat] [-- harness arguments...]",
		Description: "With no role, aterm asks. It validates the role and seat against the\n" +
			"live Agent Compose roster before opening anything, and the window it\n" +
			"opens runs the same native session `acompose` runs in place.",
		Version:               version,
		EnableShellCompletion: true,
		ShellComplete: func(ctx context.Context, cmd *cli.Command) {
			completeInvocation(ctx, deps, cmd)
		},
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:  "expression",
				Value: defaultExpression,
				Usage: "caller-supplied renderer expression",
			},
			&cli.StringFlag{Name: "task-title", Usage: "repository or issue label for the window title"},
			&cli.StringFlag{
				Name:  "working-directory",
				Value: defaultWorkingDirectory(),
				Usage: "agent working directory (defaults to the projects root)",
			},
			&cli.BoolFlag{
				Name:  "list",
				Usage: "print the live roster and exit",
			},
			&cli.BoolFlag{
				Name:  "hold",
				Usage: "keep the window open after a clean exit (a failure always holds)",
			},
			&cli.BoolFlag{
				Name:  "dry-run",
				Usage: "print the resolved identity and launch plan without opening a window",
			},
			&cli.StringFlag{
				Name:    "agent-compose-bin",
				Value:   defaultOverlayBin,
				Sources: cli.EnvVars("AGENT_COMPOSE_BIN"),
			},
			&cli.StringFlag{
				Name:    "aos-bin",
				Value:   defaultAOSBin,
				Sources: cli.EnvVars("AOS_BIN"),
			},
			&cli.StringFlag{
				Name:    "alacritty-bin",
				Value:   defaultAlacrittyBin,
				Sources: cli.EnvVars("ALACRITTY_BIN"),
			},
		},
		Action: func(ctx context.Context, cmd *cli.Command) error {
			return runLaunch(ctx, deps, cmd)
		},
	}
}

func runLaunch(ctx context.Context, deps commandDeps, cmd *cli.Command) error {
	stdout := cmd.Root().Writer
	agentCompose, err := requireBinary(deps.lookPath, cmd.String("agent-compose-bin"))
	if err != nil {
		return fmt.Errorf("agent-compose binary: %w", err)
	}
	roster, err := loadRoster(ctx, deps, agentCompose)
	if err != nil {
		return err
	}
	if cmd.Bool("list") {
		return writeRoster(stdout, roster)
	}
	cwd, err := validateWorkingDirectory(cmd.String("working-directory"))
	if err != nil {
		return err
	}
	role, seat, extra, err := resolveInvocation(deps, roster, cmd.Args().Slice())
	if err != nil {
		return err
	}
	request := launchRequest{
		Role:             role,
		Seat:             seat,
		Expression:       strings.TrimSpace(cmd.String("expression")),
		TaskTitle:        cmd.String("task-title"),
		WorkingDirectory: cwd,
		AgentComposeBin:  cmd.String("agent-compose-bin"),
		AOSBin:           cmd.String("aos-bin"),
		AlacrittyBin:     cmd.String("alacritty-bin"),
		Extra:            extra,
		Hold:             cmd.Bool("hold"),
	}
	aos, err := requireBinary(deps.lookPath, request.AOSBin)
	if err != nil {
		return fmt.Errorf("aos binary: %w", err)
	}
	self, err := deps.self()
	if err != nil {
		return fmt.Errorf("resolve the aterm executable: %w", err)
	}
	document, err := loadOverlay(ctx, deps, agentCompose, role, seat, request.Expression)
	if err != nil {
		return err
	}
	shadowed := nativeShadowAvailable(ctx, deps, aos)
	plan, err := buildLaunchPlan(document, request, cwd, self, agentCompose, aos, shadowed)
	if err != nil {
		return err
	}
	if cmd.Bool("dry-run") {
		encoded, err := json.MarshalIndent(plan, "", "  ")
		if err != nil {
			return fmt.Errorf("marshal the launch plan: %w", err)
		}
		_, err = fmt.Fprintf(stdout, "%s\n", encoded)
		return err
	}
	alacritty, err := requireBinary(deps.lookPath, request.AlacrittyBin)
	if err != nil {
		return fmt.Errorf("Alacritty binary: %w", err)
	}
	if err := deps.spawn(ctx, alacritty, plan.Arguments...); err != nil {
		return fmt.Errorf("open the window: %w", err)
	}
	return announce(stdout, plan)
}

func announce(writer io.Writer, plan launchPlan) error {
	_, err := fmt.Fprintf(writer, "%s // %s\n", plan.Identity.Annotation, plan.Identity.Seat)
	return err
}

// resolveInvocation turns the positional tail into a validated role and seat.
// A bare invocation asks, since the roster is what the caller usually lacks.
func resolveInvocation(
	deps commandDeps,
	document rosterDocument,
	args []string,
) (string, string, []string, error) {
	args = append([]string(nil), args...)
	role := ""
	seat := ""
	if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
		role = strings.TrimSpace(args[0])
		args = args[1:]
		if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
			seat = strings.TrimSpace(args[0])
			args = args[1:]
		}
	}
	if role == "" {
		if !deps.tty() {
			return "", "", nil, fmt.Errorf(
				"a role is required when aterm is not attached to a terminal. `aterm --list` names them",
			)
		}
		picked, pickedSeat, err := deps.pick(document)
		if err != nil {
			return "", "", nil, err
		}
		return picked, pickedSeat, args, nil
	}
	if !safeRoleSlug(role) {
		return "", "", nil, fmt.Errorf("role %q is not a safe role slug", role)
	}
	selected, ok := document.role(role)
	if !ok {
		return "", "", nil, unknownRoleError(role, document)
	}
	native := selected.nativeSeats()
	if len(native) == 0 {
		return "", "", nil, fmt.Errorf("role %s has no launchable native seat", role)
	}
	if seat == "" {
		resolved, err := defaultSeat(selected)
		if err != nil {
			return "", "", nil, err
		}
		return role, resolved, args, nil
	}
	if !isNativeHarness(seat) || !seatInRole(seat, selected) {
		return "", "", nil, unknownSeatError(seat, selected)
	}
	return role, seat, args, nil
}

// defaultSeat prefers the AOS-owned launch profile, then falls back to the
// catalogue's own order, whose first native entry is the frontier seat.
func defaultSeat(role rosterRole) (string, error) {
	profiled, err := defaultSeatForRole(role.Slug)
	if err == nil && isNativeHarness(profiled) && seatInRole(profiled, role) {
		return profiled, nil
	}
	return role.nativeSeats()[0].Harness, nil
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
