#!/usr/bin/env python3
"""Report the eager startup-context budget each harness loads, on demand.

This measures everything a harness ingests at session start, per harness, against
a per-harness token budget, across three axes that each have a different growth
lever:

  * doc    - the composed AGENTS.md/CLAUDE.md load point (what agent-compose
             builds). Reuses the composer's own resolution, so the bytes match
             what the load point holds. Lever: edit the AGENTS.md sources.
  * skills - every mounted skill's SKILL.md *frontmatter* (name + description) is
             eager so the model knows the skill exists; bodies load lazily on
             invoke. With a large skill surface this is routinely the BIGGEST
             axis, larger than the composed doc. Lever: prune the skill set.
  * mcp    - native MCP tool schemas. Lazy through mcporter (codex shells
             `mcporter call`/`list` on demand) and deferred under ToolSearch, so
             the eager figure is near-0; reported as a server-count note, not a
             token sum, until a non-lazy path needs measuring.

Skill scope is cwd-dependent: `~/.claude/skills` is emptied by mount-skills.sh
and skills are symlinked into each repo's `.claude/skills`, so the eager set is
the global plugin skills plus the scoped skills discoverable from the cwd. The
tool dedups by resolved path, so the one canonical skill set mounted into many
repos counts once.

Token counting (v1): a deterministic chars/4 proxy. tiktoken has no qwen encoding
and the qwen BPE needs its vocab assets, so v1 ships a hermetic proxy behind
`count_tokens`; swapping in a real tokenizer is a one-function change. ~10% off
absolute but consistent across harnesses, which a zero-sum budget needs.

Budgets and skill roots are global (host-wide, not repo-scoped): module defaults,
overridable by `budgets:` / `skill_roots:` in agent-compose.yaml or CLI flags.

Usage:
    check-context-budget                  # report every harness vs its budget
    check-context-budget --check          # exit 1 if any harness is over budget
    check-context-budget --claude-budget 12000
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from agentic_os.config import iter_workspace_repos
from agentic_os.generators.generate_agent_compose import (
    COMPOSED_PATH,
    CONFIG_PATH,
    DEFAULT_LOAD_POINTS,
    _split_frontmatter,
    compose,
    gather_sources,
    load_config,
    plan_outputs,
    resolve_load_points,
    select_by_scope,
    _normalize_scopes,
)

# v1 proxy: chars/4, deterministic and hermetic; the single swap point for a real
# qwen tokenizer later. Consistent across harnesses (see docs/context-budget.md).
CHARS_PER_TOKEN = 4
TOKENIZER_NOTE = "tokens = chars/4 proxy (v1; swap for the qwen tokenizer later)"

# Whole-baseline (doc + skills) budgets, not laws. Tune via agent-compose.yaml
# `budgets:` / CLI flags; per-harness rationale in docs/context-budget.md.
DEFAULT_BUDGETS = {"claude": 13_000, "codex": 6_000, "opencode": 5_000}

# Per-harness skill roots scanned for SKILL.md frontmatter; absolute = global
# plugins, relative = expanded against cwd + workspace repos (docs/context-budget.md).
DEFAULT_SKILL_ROOTS = {
    "claude": ["~/.claude/plugins", ".claude/skills"],
    "codex": ["~/.codex/skills", ".codex/skills"],
    "opencode": ["~/.agents/skills", ".agents/skills"],
}


def count_tokens(text: str) -> int:
    """Estimate tokens for text. v1: deterministic chars/4 (ceil)."""
    return -(-len(text) // CHARS_PER_TOKEN)


def _banner_tokens() -> int:
    """Token cost of the compose banner alone, to net it out of attribution."""
    return count_tokens(compose([]))


def doc_contributions(
    sources: list[Path], overrides: dict[Path, Path]
) -> tuple[int, list[tuple[str, int]]]:
    """Return (doc tokens, per-source tokens) for one harness's composed slice.

    Total is the real composed body the harness loads. Per-source nets out the
    banner so the breakdown sums close to the total and ranks contributors.
    """
    total = count_tokens(compose(sources, overrides))
    banner = _banner_tokens()
    per_source = [
        (
            str(src),
            max(
                0,
                count_tokens(
                    compose([src], {src: overrides[src]} if src in overrides else {})
                )
                - banner,
            ),
        )
        for src in sources
    ]
    per_source.sort(key=lambda item: item[1], reverse=True)
    return total, per_source


def _expand_skill_roots(roots: list[str], cwd: Path) -> list[Path]:
    """Resolve configured skill roots to concrete dirs to scan.

    Absolute / ~-rooted entries are taken as-is (global plugin dirs). A relative
    entry (e.g. `.claude/skills`) is expanded against the cwd and every workspace
    repo, so an elevated cwd still sees the per-repo mounted skill sets.
    """
    out: list[Path] = []
    for raw in roots:
        p = Path(raw).expanduser()
        if p.is_absolute():
            out.append(p)
            continue
        out.append(cwd / p)
        for repo in iter_workspace_repos():
            out.append(repo / p)
    return out


def skill_contributions(
    roots: list[str], cwd: Path
) -> tuple[int, list[tuple[str, int]], int]:
    """Sum eager SKILL.md frontmatter (name + description) across skill roots.

    Dedups by resolved SKILL.md path, so the one canonical skill set symlinked
    into many repos counts once. Returns (total tokens, top contributors, count).
    """
    seen: set[Path] = set()
    per_skill: list[tuple[str, int]] = []
    for root in _expand_skill_roots(roots, cwd):
        if not root.is_dir():
            continue
        # followlinks: mount-skills.sh symlinks each skill dir into .claude/skills,
        # and rglob won't descend symlinked dirs (recurse_symlinks=False on 3.13).
        for dirpath, _dirs, files in os.walk(root, followlinks=True):
            if "SKILL.md" not in files:
                continue
            skill_md = Path(dirpath) / "SKILL.md"
            try:
                resolved = skill_md.resolve()
            except OSError:
                resolved = skill_md
            if resolved in seen:
                continue
            seen.add(resolved)
            meta, _body = _split_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
            name = str(meta.get("name", "") or skill_md.parent.name)
            desc = str(meta.get("description", ""))
            per_skill.append((name, count_tokens(f"{name}: {desc}")))
    per_skill.sort(key=lambda item: item[1], reverse=True)
    return sum(t for _n, t in per_skill), per_skill, len(per_skill)


def plan_from_config(
    config_path: Path, composed_path: Path
) -> tuple[
    dict[str, Path], dict[str, list[Path]], dict[str, dict[Path, Path]], dict[str, int]
] | None:
    """Reproduce the per-harness compose plan, or None when agent-compose is off."""
    if not config_path.is_file():
        return None
    config = load_config(config_path)
    gathered, _errors = gather_sources(config)
    sources = select_by_scope(gathered, _normalize_scopes(config.get("scopes")))
    if not sources:
        return None
    load_points = resolve_load_points(config)
    slices, overrides, _outputs, _harness_errors = plan_outputs(
        sources, load_points, composed_path
    )
    raw_budgets = config.get("budgets")
    budgets: dict[str, int] = {}
    if isinstance(raw_budgets, dict):
        budgets = {str(k): int(v) for k, v in raw_budgets.items() if isinstance(v, int)}
    return load_points, slices, overrides, budgets


def skill_roots_from_config(config_path: Path) -> dict[str, list[str]]:
    """Per-harness skill roots: module defaults overlaid by config `skill_roots:`."""
    roots = {h: list(r) for h, r in DEFAULT_SKILL_ROOTS.items()}
    if not config_path.is_file():
        return roots
    raw = load_config(config_path).get("skill_roots")
    if isinstance(raw, dict):
        for harness, value in raw.items():
            if isinstance(value, list):
                roots[str(harness)] = [str(v) for v in value]
    return roots


def _bar(tokens: int, budget: int, width: int = 24) -> str:
    """A small filled/empty bar showing tokens against budget."""
    if budget <= 0:
        return ""
    filled = min(width, round(width * tokens / budget))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _harness_block(
    harness: str,
    load_point: Path,
    doc_total: int,
    doc_top: list[tuple[str, int]],
    skill_total: int,
    skill_top: list[tuple[str, int]],
    skill_count: int,
    mcp_servers: int | None,
    budget: int,
) -> tuple[list[str], bool]:
    """Render one harness's doc/skills/mcp breakdown vs its total budget."""
    total = doc_total + skill_total
    is_over = bool(budget) and total > budget
    flag = f"  OVER by {total - budget}" if is_over else ""
    lines = [f"{harness:9} {total:6} tok  / {budget:6} budget  {_bar(total, budget)}{flag}"]
    lines.append(f"          doc    {doc_total:6} tok  ({load_point})")
    if doc_top:
        name, tok = doc_top[0]
        lines.append(f"            top: {tok:6} tok  {name}")
    lines.append(f"          skills {skill_total:6} tok  ({skill_count} skills, frontmatter only)")
    for name, tok in skill_top[:3]:
        lines.append(f"            top: {tok:6} tok  {name}")
    mcp_label = f"{mcp_servers} servers (lazy/deferred, ~0 eager)" if mcp_servers is not None else "not measured"
    lines.append(f"          mcp       n/a       ({mcp_label})")
    lines.append("")
    return lines, is_over


def read_mcporter_servers(path: Path) -> list[str] | None:
    """Return mcporter's exposed server names, or None when no config is found."""
    if not path.is_file():
        return None
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return None
    return sorted(servers)


def run(
    config_path: Path,
    composed_path: Path,
    cli_budgets: dict[str, int],
    mcporter_path: Path,
    cwd: Path,
    *,
    check: bool,
) -> int:
    plan = plan_from_config(config_path, composed_path)
    skill_roots = skill_roots_from_config(config_path)
    servers = read_mcporter_servers(mcporter_path)
    mcp_count = len(servers) if servers is not None else None

    budgets = dict(DEFAULT_BUDGETS)
    lines = [f"context-budget report  ({TOKENIZER_NOTE})", ""]
    over: list[str] = []

    if plan is None:
        load_points = dict(DEFAULT_LOAD_POINTS)
        budgets.update(cli_budgets)
        lines.append("agent-compose config absent; measuring installed load points directly.")
        lines.append("")
        doc_plan = {
            h: (p, count_tokens(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else 0, [])
            for h, p in load_points.items()
        }
    else:
        load_points, slices, overrides, config_budgets = plan
        budgets.update(config_budgets)
        budgets.update(cli_budgets)
        doc_plan = {}
        for h in load_points:
            doc_total, doc_top = doc_contributions(slices.get(h, []), overrides.get(h, {}))
            doc_plan[h] = (load_points[h], doc_total, doc_top)

    for harness in sorted(load_points):
        load_point, doc_total, doc_top = doc_plan[harness]
        skill_total, skill_top, skill_count = skill_contributions(
            skill_roots.get(harness, []), cwd
        )
        block, is_over = _harness_block(
            harness, load_point, doc_total, doc_top, skill_total, skill_top,
            skill_count, mcp_count, budgets.get(harness, 0),
        )
        lines.extend(block)
        if is_over:
            over.append(harness)

    lines.append(
        "skills = plugin + scoped SKILL.md frontmatter, deduped, discoverable across "
        "the workspace (elevated-cwd worst case; a session in one repo sees fewer). "
        "Bodies load lazily, not counted."
    )
    lines.append(
        "mcp eager surface is ~0: mcporter loads schemas on demand and ToolSearch "
        "defers them. A non-lazy harness would carry the full schemas here."
    )

    out = "\n".join(lines)
    if check and over:
        sys.stderr.write(out + "\n")
        sys.stderr.write(f"\nover budget: {', '.join(over)}\n")
        return 1
    print(out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Report per-harness eager context budget.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any harness is over budget (for CI), instead of just printing",
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="agent-compose.yaml path")
    parser.add_argument(
        "--mcporter",
        type=Path,
        default=Path.home() / ".mcporter" / "mcporter.json",
        help="merged mcporter config to read codex's exposed server inventory from",
    )
    for harness in DEFAULT_BUDGETS:
        parser.add_argument(
            f"--{harness}-budget", type=int, default=None, help=f"override the {harness} token budget"
        )
    args = parser.parse_args()
    cli_budgets = {
        harness: getattr(args, f"{harness}_budget")
        for harness in DEFAULT_BUDGETS
        if getattr(args, f"{harness}_budget") is not None
    }
    try:
        return run(
            args.config, COMPOSED_PATH, cli_budgets, args.mcporter, Path.cwd(), check=args.check
        )
    except RuntimeError as exc:
        sys.stderr.write(f"context-budget: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
