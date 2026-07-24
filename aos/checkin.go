package main

import (
	"fmt"
	"strings"
)

const acomposeCheckinPrompt = "Without using tools or editing files, identify the canonical " +
	"role assigned by your loaded role instructions. Begin exactly with ROLE-CONFIRMED: " +
	"followed by that role name. Then describe yourself in under 180 words."

type acomposeCheckinSpec struct {
	Agent   string
	Layout  string
	Command []string
}

func resolveAcomposeCheckin(agent string) (acomposeCheckinSpec, error) {
	agent = strings.TrimSpace(agent)
	switch agent {
	case "":
		return acomposeCheckinSpec{}, fmt.Errorf("acompose-checkin needs --agent")
	case "codex":
		return acomposeCheckinSpec{
			Agent:  agent,
			Layout: "codex",
			Command: []string{
				"codex",
				"exec",
				"--ephemeral",
				"--sandbox",
				"read-only",
				"--skip-git-repo-check",
				"--color",
				"never",
				acomposeCheckinPrompt,
			},
		}, nil
	default:
		return acomposeCheckinSpec{}, fmt.Errorf(
			"unsupported --agent %q for acompose-checkin: want codex",
			agent,
		)
	}
}
