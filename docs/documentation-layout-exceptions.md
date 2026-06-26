# Documentation-layout exceptions

Every carve-out from the default `documentation-layout` rule: Markdown lives only at the root allowlist, `docs/*.md` (flat), or a skill dir, capped at 80 lines / 4000 chars. Enforced by [`check_documentation_layout.py`](https://github.com/coilyco-flight-deck/agentic-os/blob/main/agentic_os/check_documentation_layout.py); per-repo config under `[tool.agentic-os.documentation-layout]` in `pyproject.toml`. File lists are a snapshot and drift; the mechanisms do not.

## Active in this repo

- **`excludes` (config)** - fully exempt from location AND size checks, per the #22 escape hatch. Today: `warp/launch_configurations/**` (README), `warp/tab_configs/**` (wtab.md, claude-agent-work.md), `docs/ward-ops-forgejo-reference.md` (generated `ward ops forgejo describe` render, over-cap by design). This is the one hand-maintained surface, so it drifts - prune it when a file moves.
- **AGENTS.md size override** - config keys `agents_md_max_lines = 160` and `agents_md_max_chars = 12000` replace the 80/4000 default for `AGENTS.md` only. Load-bearing: the file is over 4000 chars, so it would fail the default.
- **Root allowlist** - present: `AGENTS.md`, `CLAUDE.md`, `README.md`. Any other root `*.md` fails the location check and would need either a move into `docs/` or an explicit exclude.
- **Skill-path location carve-out** - `*.md` under `.agents/skills/`, `.claude/skills/`, or `skills/` may live outside `docs/` at any depth (~220 files here). Location-only: the 80/4000 size cap still applies.

## Dormant carve-outs

These ship in the shared validator for other repos in the family but match nothing here:

- **`SIZE_CAP_EXEMPT_BASENAMES`** - `CODE_OF_CONDUCT.md` is exempt from the size cap by basename (verbatim-upstream file). Not present.
- **`examples/` carve-out** - any `*.md` under an `examples/` dir is allowed at any depth (Go/Rust idiom). No such file here.

## Suppressed wholesale

- **`SKIP_DIR_NAMES`** - never scanned at all: `.git`, `.claude`, `.venv`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.terraform`, `.tox`, `__pycache__`, `build`, `dist`, `node_modules`, `target`, `vendor`.

## Baseline (not an exception)

- `docs/` must stay flat - no subdirectories, use filename prefixes (`features-*.md`, `warp-*.md`, `skill-discipline-*.md`).
- A nested `SKILL.md` below a top-level skill dir fails: the loader only sees top-level dirs.
- A co-located **module `README.md`** is allowed in one of two capped shapes, each <= 3 non-blank lines (blank lines free, prose lines <= 90 chars). **Outpost** - a heading, optional one-sentence summary, and exactly one link to a single `docs/*.md` file that must link back to that exact README path (reciprocal, file-to-file). One doc may anchor many outposts. **Homestead** - heading plus up to 2 content lines, no `docs/` pointer (self-contained signage). The discriminator is whether the README links a `docs/*.md` file. This turns the per-repo `ansible/README.md` / `deploy/*/README.md` excludes into a rule - a conforming README needs no exclude.

## See also

- [README.md](../README.md) - repo intro.
- [warp.md](warp.md) - an example of the docs/ prefix split (`warp.md` + `warp-host-setup.md`).
