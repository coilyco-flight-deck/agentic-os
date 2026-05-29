# Features

What `agentic-os` does. Cross-platform shell, terminal, and secret-handling for every host Kai runs. Public, generic, leak-safe by construction.

This doc describes capabilities, not files. If you want a file inventory, run `ls`.

## Cross-platform shell

Single zsh config tree that boots cleanly on Mac, Linux (kai-server), and Windows (Git Bash). Picks the right host file via `uname -s` so there's no manual branching. Symlinked into `~/.zshrc` per host. Carries identity, history, AWS defaults, prompt, git helpers, aliases, an `rg` wrapper, and `COILY_LOCKDOWN_ROOT` for the coily security boundary.

## In-process AWS SSM secret loader

Pull secrets directly into the shell environment, never to disk. `ssm-load` reads every SecureString under the configured prefix and `load-env`s them. `ssm-get <name>` fetches a single value to stdout. Replaces the older cleartext-dump-to-cache pattern with a memory-only path.

## Cross-platform terminal

Single Warp config tree symlinked into `~/.warp/` on Mac and Windows. The repo wins over cloud sync (`is_settings_sync_enabled = false`) so theme, font, vertical tabs, AI/agent toggles, and the secret-redaction regex list stay reproducible across hosts. The redaction surface covers IPv4/IPv6, MAC, AWS keys, GitHub tokens (every variant), Stripe, Firebase, JWT, OpenAI/Anthropic/Fireworks/Google keys, Slack tokens, phone numbers.

## GPG signing without disk-cached passphrases

`gpg-ssm` is a wrapper around `gpg` that pulls the per-host signing-key passphrase from AWS SSM at sign time instead of caching it on disk. Per-host signing keys keep stolen-laptop blast radius bounded. Mac/Linux + Windows (`.cmd` shim for Git for Windows, which can't reliably exec extensionless shebang scripts). Wire it in once with `git config --global gpg.program`.

## Cross-repo pre-commit baseline

Ships the canonical hook IDs that every `coilysiren/*` repo pins via `rev:`: catalog doc-size enforcement, README/AGENTS/FEATURES trifecta presence, documentation layout, code-comment discipline, skill structural validation, dead cross-link detection, `closes #N` commit-msg enforcement, and the `catalog-block-present` check. Consumers don't stamp local copies of the validators; the `agentic-os` Python package is pip-installed into each repo's pre-commit env. Rolled out and audited from `agentic-os-kai`.

## Diagnostic + utility helpers

Small, single-purpose scripts that exist because the failure modes they handle are cryptic by default:

- AWS config linter that catches the `[profile default]` trap (SDKs read `[default]`, misplaced region surfaces later as a useless `NoRegion`).
- Verbatim-echo wrapper that fences command output and clips to mobile-readable size, for the `$$ <cmd>` chat convention.
- GPG signing doctor that walks every check needed to diagnose `failed to sign the data` and names the most-likely fix per failure mode.

## Agent self-name

Every Claude Code session gets a stable, human-readable name: `claude-<os>-<hostname>-<tag>-<pronouns>`, where `<tag>` is the last four characters of the session id and `<pronouns>` is the agent's pronoun slug (`she-her` for Claude). `setup.sh` wires it into `~/.claude/settings.json` two ways - a persistent status line so the operator always sees which host and session they are talking to, and a SessionStart hook so the agent knows its own name from the first turn. Codex and OpenClaw agents swap the `claude-` prefix and carry their own pronouns - Codex `he-him`, OpenClaw `they-them`. The wiring is idempotent and never clobbers a status line the operator set themselves.

`coily agent-name` is the single source of truth for the name. The status line script defers to coily and only falls back to computing the scheme locally when coily is absent.

## Session pulse

Generic SessionStart hook that cats `~/.cache/agentic-os/session-pulse.yaml` when present and no-ops otherwise. Zero compute at session start. Stale cache is acceptable signal - the file's mtime tells the operator how fresh the orientation is. The plugin point is "write to that path." Any consumer (a daily skill, a cron job, a one-off script) can hook in. YAML so secondary surfaces can reuse the same blob without re-parsing prose. The producer is out of scope here; it lives in consumer-specific tooling.

## Forgejo-canonical release actions

Composite Forgejo Actions for the brew release pipeline now that `forgejo.coilysiren.me` is canonical source. Three actions, each a forgejo-API-only replacement for a github-coupled marketplace action:

- `actions/tag-bump` - parse conventional commits, compute the next semver, create the tag via forgejo Tags API. Replaces `mathieudutour/github-tag-action`.
- `actions/create-release` - POST to forgejo Releases API. Idempotent on tag collision. Replaces `softprops/action-gh-release` for the release-create step.
- `actions/bump-formula` - rewrite a Homebrew Formula's `url ".."` line to pin the new tag + revision and PUT via forgejo Contents API. Same-repo write only; cross-repo bumps live in the consuming repo.

Consumed via `uses: coilysiren/agentic-os/actions/<name>@main` from a `.forgejo/workflows/*.yml`. Auto-issued `${{ github.token }}` (forgejo's compatibility name for its per-job token) covers same-repo writes; no extra secret to provision.

## Voice dictation auto-submit

Press Enter for you after a Wispr Flow dictation, so dictating into a prompt box auto-submits. Three implementations split by how the dictation ends. The macOS (`hammerspoon/init.lua`) and Windows (`autohotkey/wispr-auto-enter.ahk`) tools cover push-to-talk: they arm on releasing the Wispr hold and fire Enter when the clipboard paste lands. The Windows VAD daemon (`voice/vad-daemon.py`) covers hands-free toggle mode, which has no release gesture to arm on - it watches the raw mic with silero-vad and supplies the end-of-dictation signal itself, firing the toggle-off chord plus Enter after ~2s of silence after speech. A launcher signals session start over local UDP; `cancel` aborts without sending and `go` commits immediately. Tuning knobs are CLI flags, and off Windows the daemon dry-run-logs the keystrokes so the VAD pipeline stays testable anywhere. See [voice/README.md](../voice/README.md).

## Install surface

[README.md](../README.md) carries per-OS install steps. Mac/Linux use plain `ln -sf`. Windows uses symlinks via Git Bash, which requires Developer Mode + `MSYS=winsymlinks:nativestrict`.

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - agent-facing operating rules (delegates to `agentic-os-kai/AGENTS.md`).
- [.coily/coily.yaml](../.coily/coily.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/agentic-os-kai#313](https://github.com/coilysiren/agentic-os-kai/issues/313).
