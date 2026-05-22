# Agent instructions

Workspace-level conventions (git workflow, voice, ops boundary) load globally via `~/.claude/CLAUDE.md` -> `agentic-os-kai/AGENTS.md`. This file exists so the symmetric trifecta (README / AGENTS / docs/FEATURES) is complete and grep-discoverable, and it carries the conventions generic and public-safe enough to belong in the public repo.

## Command Delivery

When handing a human operator a command to run themselves, write it to a file under `/tmp` and hand back a short launcher (`bash /tmp/<name>.sh`) instead of an inline command, whenever the command is multi-line or longer than 25 characters. Warp mangles pasted multi-line and long commands - leading whitespace is eaten or doubled, heredocs break - so a file sidesteps the paste path entirely. Trivial one-liners under the limit can still be handed back inline.

## Skills

`.agents/skills/` ships the generalizable, public-safe skills - tooling docs for the configs that live here, plus cross-repo skills that help any agentic-os user, not just Kai. agentic-os-kai's `setup.sh` walks this dir as a peer skill source and symlinks each entry into `~/.claude/skills/`. Edit the SKILL.md here, not a copy in agentic-os-kai.

## See also

- [README.md](README.md) - human-facing intro, per-OS install steps.
- [docs/FEATURES.md](docs/FEATURES.md) - inventory of what ships today.
- [.coily/coily.yaml](.coily/coily.yaml) - allowlisted commands. No dev verbs yet; agents route through coily, not bare `make` / `uv` / `python` / `npm` / `cargo` / `dotnet`.

Cross-reference convention from [coilysiren/agentic-os-kai#313](https://github.com/coilysiren/agentic-os-kai/issues/313).
