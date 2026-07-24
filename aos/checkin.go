package main

import (
	"fmt"
	"strings"
)

const acomposeCheckinPrompt = "Without using tools or editing files, identify the canonical " +
	"role assigned by your loaded role instructions. Begin exactly with ROLE-CONFIRMED: " +
	"followed by that role name. Then describe yourself in under 180 words."

const acomposeCheckinScript = `printf '\n'
blank=1
codex "$@" 2>&1 >/dev/null |
while IFS= read -r line || [[ -n "$line" ]]; do
	case "$line" in
		"--------")
			if [[ "$blank" -eq 0 ]]; then
				printf '\n'
			fi
			printf '%s\n\n' "$line"
			blank=1
			;;
		user|codex|"tokens used"|warning:*)
			if [[ "$blank" -eq 0 ]]; then
				printf '\n'
			fi
			printf '%s\n' "$line"
			blank=0
			;;
		"")
			if [[ "$blank" -eq 0 ]]; then
				printf '\n'
			fi
			blank=1
			;;
		*)
			printf '%s\n' "$line"
			blank=0
			;;
	esac
done
status=$?
printf '\n'
exit "$status"`

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
				"bash",
				"-o",
				"pipefail",
				"-c",
				acomposeCheckinScript,
				"aos-acompose-checkin",
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
