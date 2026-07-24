# Branded Alacritty directors

`agent-terminal` launches one warded director in one statically branded
Alacritty window. Agent-compose supplies canonical identity, agentic-os renders
the terminal brand, and Ward remains the terminal-agnostic child command.

## Launch

The repository-scoped entry point is:

```text
ward exec agent-terminal -- \
  --role director \
  --seat codex \
  --expression acting \
  --task-title agentic-os#730 \
  --working-directory . \
  -- ward agent director \
  --repo coilyco-flight-deck/agentic-os
```

The launcher calls `agent-compose overlay --json`, validates
`agent-compose.overlay.v1`, and derives:

* a title from personality glyphs, the named seat, expression, and task
* the canonical melded favorite color as the cursor and selection accent
* a subtle opaque background tint
* readable selection text selected by contrast

The launcher passes every value to Alacritty as an argument. It invokes no
shell and emits no terminal control sequences into the director process.

## Inspect

Add `--dry-run` before the child-command separator to print
`agent-terminal.launch.v1` JSON without requiring Alacritty. The document
contains the selected identity, derived brand, working directory, and complete
Alacritty argument vector.

`AGENT_COMPOSE_BIN` and `ALACRITTY_BIN` may select non-default executable
locations. The defaults are `agent-compose` and `alacritty` on `PATH`.

## Ownership

Agent-compose owns renderer-neutral identity and validates role, seat, and
expression. Agentic-os owns this Alacritty adapter. Ward owns runtime authority
and the director lifecycle. Infrastructure owns fleet installation and
default-terminal rollout.

## Deliberate first-slice limits

Branding is fixed at launch. The adapter manages no tabs, panes, sessions,
avatars, background images, or interactive loop. It does not remap the ANSI
palette because director TUIs use those colors semantically.

Runtime expression updates can follow only after the static surface has
cross-platform acceptance evidence.
