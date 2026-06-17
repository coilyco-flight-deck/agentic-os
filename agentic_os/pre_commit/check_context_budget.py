#!/usr/bin/env python3
"""Report the eager startup-context budget each harness loads, on demand.

Where agent-compose-size caps the AGENTS.COMPOSE.md *sources* at commit time,
this tool measures the *composed output* each harness actually loads at session
start, per harness, against a per-harness budget. It answers the question the
per-file caps cannot: "how heavy is Claude's baseline vs Codex's vs qwen's, and
which source is the biggest contributor." It is an on-demand report (the
`context-budget` ward verb), not a pre-commit hook, so it carries no weight in
the universal commit path and is free to grow heavier measurement later.

Why per-harness budgets differ (the three failure modes this serves):
  * claude   - attention dilution. Its composed slice alone gets the private
               overlay, so it is the heaviest, and a bloated baseline crowds the
               task and makes it miss the obvious. The budget is a forcing
               function: doc growth is zero-sum against it.
  * codex    - its eager MCP surface is ~0 (mcporter is lazy: codex shells
               `mcporter call` / `list` on demand, never loads schemas eagerly),
               so this only bounds the composed doc. Sweep blow-out is runtime
               accumulation a static report cannot govern.
  * opencode - small local qwen model, needs the most aggressive curation.

Token counting (v1): a deterministic chars/4 proxy. tiktoken has no qwen
encoding and the qwen BPE needs its vocab assets, so v1 ships a hermetic proxy
behind `count_tokens`; swapping in a real tokenizer is a one-function change.
The proxy is ~10% off in absolute terms but consistent across harnesses, which
is what a zero-sum budget needs.

Budgets are global (this is a host-wide, not repo-scoped, tool): module defaults,
overridable by a `budgets:` mapping in agent-compose.yaml or by CLI flags.

Usage:
    check-context-budget                  # report every harness vs its budget
    check-context-budget --check          # exit 1 if any harness is over budget
    check-context-budget --claude-budget 5000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentic_os.generators.generate_agent_compose import (
    COMPOSED_PATH,
    CONFIG_PATH,
    DEFAULT_LOAD_POINTS,
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

# Starting budgets, not laws: tune per host via agent-compose.yaml `budgets:` or
# the CLI flags. Rationale per harness lives in docs/context-budget.md.
DEFAULT_BUDGETS = {"claude": 6_000, "codex": 3_000, "opencode": 3_000}


def count_tokens(text: str) -> int:
    """Estimate tokens for text. v1: deterministic chars/4 (ceil)."""
    return -(-len(text) // CHARS_PER_TOKEN)


def _banner_tokens() -> int:
    """Token cost of the compose banner alone, to net it out of attribution."""
    return count_tokens(compose([]))


def harness_contributions(
    sources: list[Path], overrides: dict[Path, Path]
) -> tuple[int, list[tuple[Path, int]]]:
    """Return (total tokens, per-source tokens) for one harness's composed slice.

    Total is the real composed body the harness loads. Per-source nets out the
    banner so the breakdown sums close to the total and ranks contributors.
    """
    total = count_tokens(compose(sources, overrides))
    banner = _banner_tokens()
    per_source = [
        (
            src,
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


def plan_from_config(
    config_path: Path, composed_path: Path
) -> tuple[
    dict[str, Path], dict[str, list[Path]], dict[str, dict[Path, Path]], dict[str, int]
] | None:
    """Reproduce the per-harness compose plan, or None when agent-compose is off.

    Mirrors the composer's own resolution so the measured bytes are exactly what
    each load point holds (the drift hook guarantees they match). Returns
    (load_points, slices, overrides) or None when no config is present.
    """
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


def _bar(tokens: int, budget: int, width: int = 24) -> str:
    """A small filled/empty bar showing tokens against budget."""
    if budget <= 0:
        return ""
    filled = min(width, round(width * tokens / budget))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def build_report(
    load_points: dict[str, Path],
    slices: dict[str, list[Path]],
    overrides: dict[str, dict[Path, Path]],
    budgets: dict[str, int],
    top: int = 5,
) -> tuple[list[str], list[str]]:
    """Render the per-harness report. Returns (report_lines, over_budget_harnesses)."""
    lines = [f"context-budget report  ({TOKENIZER_NOTE})", ""]
    over: list[str] = []
    for harness in sorted(load_points):
        sources = slices.get(harness, [])
        total, per_source = harness_contributions(sources, overrides.get(harness, {}))
        budget = budgets.get(harness, DEFAULT_BUDGETS.get(harness, 0))
        flag = ""
        if budget and total > budget:
            over.append(harness)
            flag = f"  OVER by {total - budget}"
        lines.append(
            f"{harness:9} {total:6} tok  / {budget:6} budget  "
            f"{_bar(total, budget)}{flag}"
        )
        lines.append(f"          load point: {load_points[harness]}")
        for src, tokens in per_source[:top]:
            lines.append(f"            {tokens:6} tok  {src}")
        if len(per_source) > top:
            rest = sum(t for _s, t in per_source[top:])
            lines.append(f"            {rest:6} tok  (+{len(per_source) - top} more)")
        lines.append("")
    return lines, over


def read_mcporter_servers(path: Path) -> list[str] | None:
    """Return mcporter's exposed server names, or None when no config is found.

    Codex's eager MCP surface is the server inventory it reads to discover what
    to call, not the schemas (mcporter loads those lazily). This counts the
    inventory so the codex column carries that context line.
    """
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


def _fallback_report(load_points: dict[str, Path], budgets: dict[str, int]):
    """Report straight from installed load-point files when agent-compose is off."""
    lines = [
        f"context-budget report  ({TOKENIZER_NOTE})",
        "agent-compose config absent; measuring installed load points directly.",
        "",
    ]
    over: list[str] = []
    for harness in sorted(load_points):
        path = load_points[harness]
        if not path.is_file():
            lines.append(f"{harness:9} (no file at {path})")
            lines.append("")
            continue
        total = count_tokens(path.read_text(encoding="utf-8", errors="replace"))
        budget = budgets.get(harness, DEFAULT_BUDGETS.get(harness, 0))
        flag = ""
        if budget and total > budget:
            over.append(harness)
            flag = f"  OVER by {total - budget}"
        lines.append(
            f"{harness:9} {total:6} tok  / {budget:6} budget  "
            f"{_bar(total, budget)}{flag}"
        )
        lines.append(f"          load point: {path}")
        lines.append("")
    return lines, over


def run(
    config_path: Path,
    composed_path: Path,
    cli_budgets: dict[str, int],
    mcporter_path: Path,
    *,
    check: bool,
) -> int:
    plan = plan_from_config(config_path, composed_path)
    budgets = dict(DEFAULT_BUDGETS)
    if plan is None:
        load_points = dict(DEFAULT_LOAD_POINTS)
        budgets.update(cli_budgets)
        lines, over = _fallback_report(load_points, budgets)
    else:
        load_points, slices, overrides, config_budgets = plan
        budgets.update(config_budgets)
        budgets.update(cli_budgets)
        lines, over = build_report(load_points, slices, overrides, budgets)

    servers = read_mcporter_servers(mcporter_path)
    if servers is not None:
        lines.append(
            f"codex MCP surface: {len(servers)} servers exposed via mcporter "
            "(lazy - schemas load on demand, ~0 eager tokens)."
        )
    lines.append(
        "skills: only SKILL.md frontmatter is eager; bodies load on invoke "
        "(not counted here)."
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
        return run(args.config, COMPOSED_PATH, cli_budgets, args.mcporter, check=args.check)
    except RuntimeError as exc:
        sys.stderr.write(f"context-budget: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
