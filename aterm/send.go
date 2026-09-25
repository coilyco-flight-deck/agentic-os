package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/urfave/cli/v3"
)

const agentsFormat = "aterm.agents.v1"

func newDaemonCommand() *cli.Command {
	return &cli.Command{
		Name:  "daemon",
		Usage: "run the host daemon that owns every session's terminal, in the foreground",
		Description: "A session starts the daemon on its own, so this verb is for a service\n" +
			"manager or for watching one. It exits after five idle minutes.",
		Flags: []cli.Flag{
			&cli.StringFlag{Name: "socket", Value: daemonSocket(), Usage: "unix socket to serve"},
			&cli.StringFlag{
				Name:    "websocket",
				Value:   defaultDaemonWS,
				Usage:   "loopback address for browser clients, empty for none",
				Sources: cli.EnvVars(daemonWSEnv),
			},
			&cli.StringFlag{
				Name:    "tailnet-port",
				Value:   "7419",
				Usage:   "HTTPS port on this node's tailnet address, empty for none",
				Sources: cli.EnvVars(daemonTailnetPortEnv),
			},
			&cli.StringSliceFlag{
				Name:    "allow-tags",
				Value:   defaultAllowTags,
				Usage:   "tailnet tags whose devices may attach, besides this node owner's own",
				Sources: cli.EnvVars(daemonAllowTagsEnv),
			},
			&cli.StringSliceFlag{
				Name:    "allow-origins",
				Value:   defaultAllowOrigins,
				Usage:   "hosted client pages that may open a session socket on the tailnet",
				Sources: cli.EnvVars(daemonAllowOrigins),
			},
			&cli.StringFlag{Name: "client-dir", Value: defaultClientDir(), Usage: "built aterm client served at /"},
			&cli.DurationFlag{Name: "idle", Value: daemonIdle, Usage: "exit after this long with no session and no client"},
		},
		Action: func(_ context.Context, cmd *cli.Command) error {
			return runDaemon(daemonOptions{
				Socket:       cmd.String("socket"),
				Websocket:    cmd.String("websocket"),
				TailnetPort:  cmd.String("tailnet-port"),
				AllowTags:    cmd.StringSlice("allow-tags"),
				AllowOrigins: cmd.StringSlice("allow-origins"),
				ClientDir:    cmd.String("client-dir"),
				Idle:         cmd.Duration("idle"),
			}, cmd.Root().ErrWriter)
		},
	}
}

func newSendCommand() *cli.Command {
	return &cli.Command{
		Name:      "send",
		Usage:     "type a message into another live session, stamped with this session's seat",
		ArgsUsage: "<role|seat|session> <message...>",
		Description: "The daemon stamps `[from <role> <identity>]` from this session's token,\n" +
			"so the sender cannot choose that line. A message of `-` reads stdin.\n" +
			"It waits while Kai is typing in the target and lands after her draft.",
		Flags: []cli.Flag{
			&cli.BoolFlag{Name: "launch", Usage: "when no session answers to a role, open one and deliver into it"},
			&cli.BoolFlag{Name: "json", Usage: "print the message state as JSON"},
		},
		Action: func(_ context.Context, cmd *cli.Command) error {
			args := cmd.Args().Slice()
			if len(args) < 2 {
				return withExit(exitUsage, fmt.Errorf("aterm send needs a target and a message. `aterm agents` lists targets"))
			}
			body := strings.Join(args[1:], " ")
			if body == "-" {
				raw, err := io.ReadAll(os.Stdin)
				if err != nil {
					return err
				}
				body = string(raw)
			}
			state, err := sendMessage(args[0], body, cmd.Bool("launch"))
			if err != nil {
				return err
			}
			if cmd.Bool("json") {
				encoded, _ := json.MarshalIndent(state, "", "  ")
				_, err = fmt.Fprintf(cmd.Root().Writer, "%s\n", encoded)
				return err
			}
			_, err = fmt.Fprintln(cmd.Root().Writer, describeMessage(state))
			return err
		},
	}
}

// sendMessage is the one path both front doors take, the CLI and the MCP
// tool, so the two cannot drift.
func sendMessage(target, body string, launch bool) (peerMessage, error) {
	token := strings.TrimSpace(os.Getenv(sessionTokenEnv))
	if token == "" {
		return peerMessage{}, withExit(exitUsage, fmt.Errorf(
			"%s is unset: aterm send speaks for a session aterm launched, so run it from inside one", sessionTokenEnv))
	}
	c, err := dialDaemon(false)
	if err != nil {
		return peerMessage{}, withExit(exitMissing, err)
	}
	defer c.Close()
	reply, err := c.request(frame{Type: "send", Token: token, Target: target, Body: body, Launch: launch})
	if err != nil {
		if reply.Code != 0 {
			return peerMessage{}, withExit(reply.Code, err)
		}
		return peerMessage{}, err
	}
	if reply.Message == nil {
		return peerMessage{}, fmt.Errorf("the daemon answered without a message state")
	}
	state := *reply.Message
	if state.State == "launching" {
		if err := launchRole(target, ""); err != nil {
			return state, fmt.Errorf("the message waits for %s, but opening it failed: %w", target, err)
		}
	}
	return state, nil
}

// launchRole opens the role the way a person would, through this binary, so
// the roster check and the window are the ordinary ones.
func launchRole(role, seat string) error {
	self, err := os.Executable()
	if err != nil {
		return err
	}
	args := []string{role}
	if seat != "" {
		args = append(args, seat)
	}
	output, err := exec.Command(self, args...).CombinedOutput()
	if err != nil {
		return fmt.Errorf("%v: %s", err, strings.TrimSpace(string(output)))
	}
	return nil
}

func describeMessage(state peerMessage) string {
	where := state.Session
	if where == "" {
		where = state.Target
	}
	line := fmt.Sprintf("%s %s to %s", state.State, state.ID, where)
	if state.Reason != "" {
		line += ": " + state.Reason
	}
	return line
}

func newAgentsCommand() *cli.Command {
	return &cli.Command{
		Name:  "agents",
		Usage: "list the live sessions the daemon holds, the targets `aterm send` takes",
		Flags: []cli.Flag{&cli.BoolFlag{Name: "json", Usage: "machine-readable, as " + agentsFormat}},
		Action: func(_ context.Context, cmd *cli.Command) error {
			views, err := listAgents()
			if err != nil {
				return err
			}
			writer := cmd.Root().Writer
			if cmd.Bool("json") {
				encoded, _ := json.MarshalIndent(agentsDocument(views), "", "  ")
				_, err := fmt.Fprintf(writer, "%s\n", encoded)
				return err
			}
			if len(views) == 0 {
				_, err := fmt.Fprintln(writer, "no live session")
				return err
			}
			self := os.Getenv(sessionNameEnv)
			for _, view := range views {
				marker := " "
				if view.Name == self {
					marker = "*"
				}
				fmt.Fprintf(writer, "%s %-32s %-16s %-8s %s\n", marker, view.Name, view.Identity, view.Seat, agentState(view))
			}
			return nil
		},
	}
}

type agentsDoc struct {
	Format   string        `json:"format"`
	Self     string        `json:"self,omitempty"`
	Sessions []sessionView `json:"sessions"`
}

func agentsDocument(views []sessionView) agentsDoc {
	return agentsDoc{Format: agentsFormat, Self: os.Getenv(sessionNameEnv), Sessions: views}
}

func agentState(view sessionView) string {
	parts := []string{}
	if !view.Ready {
		parts = append(parts, "starting")
	}
	if len(view.Degraded) > 0 {
		parts = append(parts, "degraded: "+strings.Join(view.Degraded, " "))
	}
	if view.Drafted {
		parts = append(parts, "Kai drafting")
	}
	if view.Pending > 0 {
		parts = append(parts, fmt.Sprintf("%d pending", view.Pending))
	}
	parts = append(parts, fmt.Sprintf("%d client(s), up %s", view.Clients, time.Since(view.Started).Round(time.Second)))
	return strings.Join(parts, ", ")
}

func listAgents() ([]sessionView, error) {
	c, err := dialDaemon(false)
	if err != nil {
		// No daemon means no session it holds, which is an answer, not a fault.
		return nil, nil
	}
	defer c.Close()
	reply, err := c.request(frame{Type: "list"})
	if err != nil {
		return nil, err
	}
	return reply.Sessions, nil
}

// askChoice puts a question to whoever is at a client and waits for the pick.
// Both front doors take it, the CLI and the MCP tool.
func askChoice(ask choiceAsk) (choiceAnswer, error) {
	token := strings.TrimSpace(os.Getenv(sessionTokenEnv))
	if token == "" {
		return choiceAnswer{}, withExit(exitUsage, fmt.Errorf(
			"%s is unset: aterm ask speaks for a session aterm launched, so run it from inside one", sessionTokenEnv))
	}
	c, err := dialDaemon(false)
	if err != nil {
		return choiceAnswer{}, withExit(exitMissing, err)
	}
	defer c.Close()
	reply, err := c.request(frame{Type: "ask", Token: token, Ask: &ask})
	if err != nil {
		if reply.Code != 0 {
			return choiceAnswer{}, withExit(reply.Code, err)
		}
		return choiceAnswer{}, err
	}
	if reply.Answer == nil {
		return choiceAnswer{}, fmt.Errorf("the daemon settled the ask without an answer")
	}
	return *reply.Answer, nil
}

func newAskCommand() *cli.Command {
	return &cli.Command{
		Name:      "ask",
		Usage:     "put a multiple-choice question to Kai's client and print the pick",
		ArgsUsage: "<question> <option[::description]>...",
		Description: "The daemon stamps the asking seat from this session's token and shows the\n" +
			"question on every attached client. It exits 1 when the ask is cancelled or times out.",
		Flags: []cli.Flag{
			&cli.StringFlag{Name: "header", Usage: "a short label above the question"},
			&cli.BoolFlag{Name: "other", Usage: "allow a free-text answer"},
			&cli.BoolFlag{Name: "multi", Usage: "allow more than one pick"},
			&cli.BoolFlag{Name: "json", Usage: "print the answer as JSON"},
		},
		Action: func(_ context.Context, cmd *cli.Command) error {
			args := cmd.Args().Slice()
			if len(args) < 1 {
				return withExit(exitUsage, fmt.Errorf("aterm ask needs a question"))
			}
			ask := choiceAsk{Question: args[0], Header: cmd.String("header"), AllowOther: cmd.Bool("other"), Multi: cmd.Bool("multi")}
			for _, raw := range args[1:] {
				label, description, _ := strings.Cut(raw, "::")
				ask.Options = append(ask.Options, choiceOption{Label: label, Description: description})
			}
			answer, err := askChoice(ask)
			if err != nil {
				return err
			}
			writer := cmd.Root().Writer
			if cmd.Bool("json") {
				encoded, _ := json.MarshalIndent(answer, "", "  ")
				fmt.Fprintf(writer, "%s\n", encoded)
			} else {
				for _, label := range answer.Labels {
					fmt.Fprintln(writer, label)
				}
				if answer.Text != "" {
					fmt.Fprintln(writer, answer.Text)
				}
			}
			if answer.State != "answered" {
				return fmt.Errorf("the ask was %s: %s", strings.ReplaceAll(answer.State, "_", " "), answer.Reason)
			}
			return nil
		},
	}
}
