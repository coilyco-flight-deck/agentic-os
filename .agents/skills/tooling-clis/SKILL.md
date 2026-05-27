---
name: tooling-clis
description: The five-tier information model for agent-facing CLI commands - description, body, intro, help, outro - plus push-short/pull-long. Use when documenting a CLI agents invoke, not humans.
---

# Agent-facing CLI documentation

How an agent-facing CLI command carries its own documentation. The motivating command is `coily dispatch`. The model generalizes to every command an agent invokes and a human does not.

## The premise: these commands are agent-parsed, not human-read

Markdown skills are the human-to-agent interface. They earn their keep on fuzzy matching - aliases, synonyms, dictation-miss tolerance. A command like `coily dispatch` is different. It is hard-triggered. The agent runs `coily dispatch`, not something it might confuse for another command, so there is no synonym work to do. A human never runs it directly either, because the privileged op is wrapped for a reason.

That means the documentation for the command is entirely agent-parsed. It does not need to read like a skill. It needs to reach the agent at the right moment, and a skill markdown can only deliver once, at trigger time.

## The five tiers

Every agent-facing CLI command has five distinct information surfaces. They differ by who reads them and when.

1. **Description** - match time. Skill frontmatter `description:`. Aliases and triggers. The only surface doing fuzzy-matching work. Eager-loaded into every turn, so it stays under the 500-byte cap (see `tooling-skill-authoring` in agentic-os).
2. **Body** - orient time. Skill body. Read after the description matched but before the agent commits to running anything. Three to five lines: what the command does, its blast radius, and a pointer to `help`. Not a bare "aliases for `coily X`" line.
3. **Intro** - pre-run, pushed. CLI-emitted at the start of a real run. Short, two to three lines, because it hits the agent's context on every single invocation. Ends with "run `coily X help` for the full thing."
4. **Help** - pre-run, pulled. CLI-emitted on demand via `coily X help`. The exhaustive long-form reference. Safe to read with no side effects.
5. **Outro** - post-run, pushed. CLI-emitted at completion. The next-action nudge ("dispatch finished, run `coily session end`, merge back to main").

## Rule: push short, pull long

Intro and Help share one subject. They are not the same length.

Intro is pushed - emitted on every invocation whether asked or not. It pays a context cost every run, so it stays short: a two-to-three-line head plus a pointer.

Help is pulled - loaded only when the agent runs `coily X help` because it wants to know. It pays nothing on a normal run, so it can be exhaustive.

**Why:** a pushed surface that is long taxes every invocation forever, the same failure mode as alias-packing a skill description. A pulled surface that is short forces the agent to guess or re-run. Match the length to the delivery.

**How to apply:** when writing Intro, if it runs past three lines, the overflow belongs in Help. When writing Help, do not trim it for length - it is the place length is free.

## Rule: top and bottom never collapse into one

Intro and Outro look like two styles of one block. They are not. They are two times.

**Why:** the entire advantage of moving docs into the CLI instead of a skill is that the CLI controls *when* text enters the agent's context. A skill blob enters once, at trigger. A CLI injects at start, during, and at completion. The agent's context at completion is not its context at start - it has done the work, the window has churned. Outro content like "now end the session" is only knowable at the bottom (it depends on how the run went) and only actionable at the bottom. Front-load it and the agent reads it, works for 40 minutes, and the nudge is stale or evicted before it is relevant. Bottom-emission is recency placement: the next action goes where the agent reads it last, so it is freshest when it is needed.

**How to apply:** never answer "can all the info live at the top" with yes. The five tiers have a hard floor of distinct pre-run and post-run surfaces. Collapsing them throws away the only reason to leave a skill markdown behind.

## Where the docs live in code

Not loose block comments scattered in the source. One markdown file per documentation surface, embedded into the binary and emitted by the CLI.

For a Go CLI, `//go:embed` a markdown file per command. The file stays editable as plain markdown, legible to a human reviewing it, while the CLI owns delivery and timing.

**Why:** the markdown file versions in the same commit as the command code. A skill markdown describing command behavior is a second copy of the truth that rots on its own. Embedded-and-emitted docs cannot drift from the command, because changing the command and changing its docs is one diff.

**How to apply:** new agent-facing command - author `intro.md`, `help.md`, `outro.md` (or one file with delimited sections), `//go:embed` them, emit Intro and Outro from the command body and Help from a `help` subcommand. Existing command with docs in a skill - move the behavioral half into embedded files on next touch, leave only Description and Body in the skill.

## What stays in the skill

After the move, the skill shrinks to tiers 1 and 2 - Description and Body. That is the part that is genuinely human-to-agent and genuinely fuzzy-matched. Everything past Body is agent-parsed reference that belongs next to the code.

The Body ends with a one-liner: "for command behavior, run `coily X help`."

## Applying it to coily dispatch

`coily dispatch` is the first command to take this shape. The current `coily-dispatch` skill body mixes the dictation-collision table (genuine tier-1/2 fuzzy-matching content, stays) with behavioral reference - headless vs interactive, detach mechanics, refusal conditions (tiers 3 to 5, moves into the CLI). The dispatch-side change is tracked on `coilysiren/coily`. This skill is the general model that change is one instance of.

Origin: [agentic-os-kai#711](https://github.com/coilysiren/agentic-os-kai/issues/711).
