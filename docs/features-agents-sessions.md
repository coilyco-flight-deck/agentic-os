# Features: agents and sessions

Agent naming, session orientation, and voice-dictation auto-submit.

## Agent self-name

Every Claude Code session gets a stable, human-readable name: `claude-<os>-<hostname>-<tag>-<pronouns>`, where `<tag>` is the last four characters of the session id and `<pronouns>` is the agent's pronoun slug (`she-her` for Claude). The claude-hooks ansible role wires it into `~/.claude/settings.json` two ways - a persistent status line so the operator always sees which host and session they are talking to, and a SessionStart hook so the agent knows its own name from the first turn. Codex and OpenCode agents swap the `claude-` prefix and carry their own pronouns - Codex `he-him`, OpenCode (qwen-opencode) `they-them`. The wiring is idempotent and never clobbers a status line the operator set themselves.

`coily agent-name` is the single source of truth for the name. The status line script defers to coily and only falls back to computing the scheme locally when coily is absent.

## Session pulse

Generic SessionStart hook that cats `~/.cache/agentic-os/session-pulse.yaml` when present and no-ops otherwise. Zero compute at session start. Stale cache is acceptable signal - the file's mtime tells the operator how fresh the orientation is. The plugin point is "write to that path." Any consumer (a daily skill, a cron job, a one-off script) can hook in. YAML so secondary surfaces can reuse the same blob without re-parsing prose. The producer is out of scope here; it lives in consumer-specific tooling.

## Voice dictation auto-submit

Press Enter for you after a Wispr Flow dictation, so dictating into a prompt box auto-submits. Three implementations split by how the dictation ends. The macOS (`hammerspoon/init.lua`) and Windows (`autohotkey/wispr-auto-enter.ahk`) tools cover push-to-talk: they arm on releasing the Wispr hold and fire Enter when the clipboard paste lands. The Windows VAD daemon (`voice/vad-daemon.py`) covers hands-free toggle mode, which has no release gesture to arm on - it watches the raw mic with silero-vad and supplies the end-of-dictation signal itself, firing the toggle-off chord plus Enter after ~2s of silence after speech. A launcher signals session start over local UDP; `cancel` aborts without sending and `go` commits immediately. Tuning knobs are CLI flags, and off Windows the daemon dry-run-logs the keystrokes so the VAD pipeline stays testable anywhere. See [voice/README.md](../voice/README.md).

## Composed cross-harness agent context

Opt-in composer (`agent-compose`) that synthesizes global context from a declared set of sources, then points each harness's global load point (Claude Code, Codex, OpenCode) at the result by symlink. Shared sources produce one canonical `~/.config/agent-compose/COMPOSED.md` with no content duplicated on disk. A source may declare `harnesses: [claude, codex, opencode]` in YAML frontmatter when its doctrine applies only to part of the fleet. If configured harnesses select different source slices, the composer writes `COMPOSED.<harness>.md` outputs instead. Sources are listed explicitly or discovered by walking declared roots for `AGENTS.COMPOSE.md` files, the disjoint always-global doctrine that no harness's own AGENTS.md/CLAUDE.md cascade loads. A root need not be a repo checkout: pointing one at an out-of-repo directory (the ansible role uses `~/.config/agent-compose/sources/`) gives host-local doctrine a home that stays untracked and uncommitted while still composing into every harness's global context. Scope tags independently pick what composes per machine: the machine declares `scopes`, each source declares its own `scopes` in frontmatter, and a source composes only where the two sets intersect. Activation is the presence of `~/.config/agent-compose/agent-compose.yaml`: with no config, the composer is a total no-op and every harness behaves exactly as it does without it. The agent-compose ansible role runs it idempotently on each host.
