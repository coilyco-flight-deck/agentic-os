#!/usr/bin/env python3
"""goose-triage: real issue triage driven by the local Goose+Qwen harness.

Implements the tooling-issue-prioritization method with Goose as the judgment
engine and Python owning the deterministic parts:

  1. Fetch open issues for a repo (coily forgejo issue list + view).
  2. P0 net: regex content rules (p0-content-rules.yaml) flag candidates.
  3. P0 confirm: an isolated yes/no Goose call per candidate - "active
     incident, or just discussing the topic?" - the over-match filter.
  4. Score the remainder: two independent Goose urgency passes (P1=3 P2=2
     P3=1 P4=0), summed. Unsure -> P3.
  5. Percentile cut into the target shape (P1 10% / P2 20% / P3 30% / P4 40%),
     boundaries snapped to natural score breaks, P1 floored at zero.
  6. Write a report (markdown + yaml) under ~/.cache/agentic-os/goose-triage/.

Report-only: it never writes to issues. Apply labels yourself after review.

The Goose calls use the anti-thrash config validated in the test harness:
`goose run --no-profile --quiet --no-session --max-turns 1` - no extensions
loaded (so no tool-call looping), banner suppressed, single turn.

See docs/test-harness-goose.md and the tooling-issue-prioritization skill.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goose_json import ask  # enforced JSON-schema Goose calls (the ward goose-json verb)

REPO_ROOT = Path(__file__).resolve().parent.parent
P0_RULES = REPO_ROOT / ".agents/skills/tooling-issue-prioritization/references/p0-content-rules.yaml"
CACHE_DIR = Path.home() / ".cache" / "agentic-os" / "goose-triage"

# Target shares of the non-P0 pool (centers 10/20/30/40, summing to 100).
TARGET = {"P1": 0.10, "P2": 0.20, "P3": 0.30, "P4": 0.40}
# P1 floors at zero: a top-band issue is only P1 if its mean clears this absolute
# anchor floor (the P2/P1 boundary). See docs/goose-triage.md.
P1_FLOOR = 70.0
SCORE_DEFAULT = 30.0  # unsure -> low-middle (P3 territory)
# Re-rank any tie this large against itself (run-off), so qwen's ceiling cluster
# orders by judgment, not by issue number. See docs/goose-triage.md.
RUNOFF_MIN_GROUP = 4

P0_CONFIRM = """A keyword scan flagged this issue as a possible P0 (urgent incident). Your ONE job: decide if it describes an ACTIVE, LIVE incident or exposure happening NOW (a real outage, a real leaked credential, actual data loss, a live exploitable bypass, a currently-broken deploy) versus merely DISCUSSING, proposing, documenting, planning, or giving an example of such a topic (a design doc, a hardening proposal, a "set up X" task, a how-to). Output ONLY JSON, no prose, no code fence: {"active_incident":true|false,"reason":"<=12 words"}. When it is discussion / proposal / example / planning, active_incident=false."""

# Numeric urgency rubrics: three framings on a 0-100 scale, averaged, for spread
# the percentile cut can land on. See docs/goose-triage.md.
_ANCHOR = """Anchors: 80-100 = important AND clearly the next thing (P1-worthy). 50-79 = real backlog you genuinely intend to act on, not yet (P2). 20-49 = low but kept, or unsure - the default (P3). 0-19 = icebox: speculative / parked / won't-do-soon, hobby toys, "try X" / "fork Y" wishes, reading-list adds, vague vision, far-future, one-line stubs (P4).
Use the FULL range and be decisive - spread your scores, do NOT cluster on round multiples of ten or default everything to the middle. Output ONLY JSON, no prose, no fence: {"score":<integer 0-100>,"reason":"<=12 words"}. If genuinely unsure, score 30."""
SCORE_RUBRICS = [
    "Score this software-backlog issue's priority as an integer 0-100. It is NOT an active incident.\n" + _ANCHOR,
    "Score this backlog issue by how much NOT doing it soon would hurt, as an integer 0-100. It is NOT an active incident. More near-term pain = higher.\n" + _ANCHOR,
    "Score this backlog issue by near-term value and whether it is the clear next step, as an integer 0-100. It is NOT an active incident.\n" + _ANCHOR,
]

RUNOFF = """These software-backlog issues all received a similar priority score, so break the tie. Rank them from MOST to LEAST important to do next - weigh real near-term impact, fleet-wide breakage, and whether each is the clear next step over mere cleanup or speculative work. Output ONLY JSON, no prose, no fence: {"order":[<issue numbers, most important first>]}. Include every issue number exactly once."""


def sh(args: list[str], timeout: int = 60) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout


# Response schemas Goose is forced to conform to (via goose_json.ask), one per
# judgment call. The provider constrains output to these - no regex scraping.
CONFIRM_SCHEMA = {"type": "object", "additionalProperties": False,
                  "required": ["active_incident", "reason"],
                  "properties": {"active_incident": {"type": "boolean"},
                                 "reason": {"type": "string"}}}
SCORE_SCHEMA = {"type": "object", "additionalProperties": False,
                "required": ["score", "reason"],
                "properties": {"score": {"type": "integer"},
                               "reason": {"type": "string"}}}
RUNOFF_SCHEMA = {"type": "object", "additionalProperties": False,
                 "required": ["order"],
                 "properties": {"order": {"type": "array", "items": {"type": "integer"}}}}


def _hms(secs: float) -> str:
    s = int(secs)
    return f"{s // 60}:{s % 60:02d}"


def _bar(done: int, total: int, t0: float) -> str:
    """Compact progress: done/total, percent, elapsed, ETA (calls are the unit)."""
    elapsed = time.monotonic() - t0
    pct = 100 * done / total if total else 100
    eta = elapsed / done * (total - done) if done else 0
    return f"[{done}/{total} {pct:.0f}% | {_hms(elapsed)} elapsed | eta {_hms(eta)}]"


def _clamp_score(raw) -> float:
    """Coerce a model 'score' to a float in [0, 100]; default on garbage."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return SCORE_DEFAULT
    return max(0.0, min(100.0, v))


def fetch_issues(repo: str, limit: int) -> list[dict]:
    raw = sh(["coily", "ops", "forgejo", "issue", "list",
              "--repo", repo, "--state", "open", "--limit", str(limit)])
    issues = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 4 or "[open]" not in line:
            continue
        num = int(parts[1].lstrip("#"))
        title = parts[3].strip()
        issues.append({"num": num, "title": title, "body": ""})
    for it in issues:
        view = sh(["coily", "ops", "forgejo", "issue", "view",
                   "--repo", repo, "--index", str(it["num"])])
        lines = view.splitlines()
        it["body"] = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    return issues


def p0_candidates(issues: list[dict]) -> set[int]:
    rules = yaml.safe_load(P0_RULES.read_text())["categories"]
    patterns = [re.compile(rx, re.IGNORECASE) for rx in rules.values()]
    flagged = set()
    for it in issues:
        blob = f"{it['title']}\n{it['body']}"
        if any(p.search(blob) for p in patterns):
            flagged.add(it["num"])
    return flagged


def issue_prompt(base: str, it: dict) -> str:
    body = it["body"][:1500]
    return f'{base}\nTitle: "{it["title"]}"\nBody: "{body}"'


def runoff(members: list[dict]) -> bool:
    """Ask Goose to rank a tied group against itself; write each member's
    'tiebreak' to its rank position (0 = most important). Returns True on a
    usable ranking, False on failure (caller keeps the issue-number fallback)."""
    listing = "\n".join(f'#{it["num"]} {it["title"]}' for it in members)
    res = ask(f"{RUNOFF}\nIssues:\n{listing}", RUNOFF_SCHEMA)
    order = (res or {}).get("order")
    if not isinstance(order, list):
        return False
    nums = [int(str(x).lstrip("#")) for x in order if str(x).lstrip("#").isdigit()]
    if not nums:
        return False
    pos = {num: i for i, num in enumerate(nums)}
    for it in members:
        it["tiebreak"] = pos.get(it["num"], len(nums) + it["num"])
    return True


def percentile_cut(scored: list[dict]) -> None:
    """Rank by mean score desc (run-off tiebreak, then issue number), assign
    tiers by target share, snap cuts to nearby natural score breaks, floor P1 at
    zero. Mutates each dict's 'tier'."""
    pool = sorted(scored, key=lambda d: (-d["score"], d.get("tiebreak", d["num"]), d["num"]))
    n = len(pool)
    if n == 0:
        return
    # nominal cumulative boundaries from target shares
    b1 = round(TARGET["P1"] * n)
    b2 = b1 + round(TARGET["P2"] * n)
    b3 = b2 + round(TARGET["P3"] * n)

    # Cap how far a boundary may snap, so an oversized quantized tie is split at
    # the target percentile rather than swallowing a tier. See docs/goose-triage.md.
    max_move = max(1, round(0.05 * n))

    def snap(idx: int) -> int:
        if idx <= 0 or idx >= n:
            return idx
        if pool[idx - 1]["score"] == pool[idx]["score"]:
            down = idx
            while down > 0 and pool[down - 1]["score"] == pool[idx]["score"]:
                down -= 1
            up = idx
            while up < n and pool[up]["score"] == pool[idx]["score"]:
                up += 1
            best = down if (idx - down) <= (up - idx) else up
            if abs(best - idx) > max_move:
                return idx  # tie too wide to snap - accept the split
            return best
        return idx

    b1, b2, b3 = snap(b1), snap(b2), snap(b3)
    # P1 floors at zero: a top-band issue is only P1 if its mean score clears the
    # absolute P1 anchor floor; otherwise it falls through to P2.
    for i, it in enumerate(pool):
        if i < b1 and it["score"] >= P1_FLOOR:
            it["tier"] = "P1"
        elif i < b2:
            it["tier"] = "P2"
        elif i < b3:
            it["tier"] = "P3"
        else:
            it["tier"] = "P4"


def run(repo: str, limit: int) -> dict:
    print(f"goose-triage: fetching open issues for {repo} (limit {limit}) ...",
          file=sys.stderr)
    issues = fetch_issues(repo, limit)
    n = len(issues)
    capped = n >= limit
    print(f"goose-triage: {n} issues fetched"
          + (f"  WARNING: hit the {limit} cap, backlog is larger - "
             "percentile math is over a partial set" if capped else ""),
          file=sys.stderr)

    by_num = {it["num"]: it for it in issues}
    cands = p0_candidates(issues)
    # Stable progress denominator: confirm calls + 3 score passes per issue. A
    # touch high if any candidate confirms P0 (those skip scoring) - negligible.
    t0 = time.monotonic()
    total = len(cands) + len(SCORE_RUBRICS) * n
    done = 0
    print(f"goose-triage: P0 net flagged {len(cands)} candidate(s); "
          f"~{total} Goose calls to make; confirming ...", file=sys.stderr)

    confirmed_p0 = []
    for num in sorted(cands):
        it = by_num[num]
        res = ask(issue_prompt(P0_CONFIRM, it), CONFIRM_SCHEMA)
        done += 1
        active = bool(res and res.get("active_incident"))
        if active:
            it["tier"] = "P0"
            it["reason"] = (res or {}).get("reason", "")
            confirmed_p0.append(it)
        print(f"  P0 confirm #{num}: {'CONFIRMED' if active else 'rejected':9} "
              f"{_bar(done, total, t0)}", file=sys.stderr)

    p0_nums = {it["num"] for it in confirmed_p0}
    pool = [it for it in issues if it["num"] not in p0_nums]
    print(f"goose-triage: scoring {len(pool)} non-P0 issues "
          f"({len(SCORE_RUBRICS)} numeric passes) ...", file=sys.stderr)
    for it in pool:
        scores, reasons = [], []
        for rubric in SCORE_RUBRICS:
            res = ask(issue_prompt(rubric, it), SCORE_SCHEMA)
            done += 1
            scores.append(_clamp_score((res or {}).get("score")))
            if res and res.get("reason"):
                reasons.append(res["reason"])
        it["score"] = round(sum(scores) / len(scores), 1)
        it["passes"] = scores
        it["tiebreak"] = it["num"]  # default order within a tie
        it["reason"] = reasons[0] if reasons else "unscored -> default 30"
        print(f"  score #{it['num']}: {it['score']:5.1f}  {_bar(done, total, t0)}",
              file=sys.stderr)

    # Run-off any tie large enough to otherwise split arbitrarily across a tier.
    groups: dict[float, list[dict]] = {}
    for it in pool:
        groups.setdefault(it["score"], []).append(it)
    for score, members in sorted(groups.items(), reverse=True):
        if len(members) >= RUNOFF_MIN_GROUP:
            ok = runoff(members)
            print(f"goose-triage: run-off on {len(members)} issues tied at "
                  f"{score:.0f}: {'ranked' if ok else 'failed, kept issue order'} "
                  f"[{_hms(time.monotonic() - t0)} elapsed]", file=sys.stderr)

    percentile_cut(pool)
    print(f"goose-triage: judgment complete in {_hms(time.monotonic() - t0)}",
          file=sys.stderr)

    tiers = {t: [] for t in ("P0", "P1", "P2", "P3", "P4")}
    for it in confirmed_p0:
        tiers["P0"].append(it)
    for it in pool:
        tiers[it["tier"]].append(it)
    return {"repo": repo, "n": n, "capped": capped, "tiers": tiers}


def write_report(result: dict) -> tuple[Path, Path]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    slug = result["repo"].replace("/", "-")
    md_path = CACHE_DIR / f"{slug}-{today}.md"
    yaml_path = CACHE_DIR / f"{slug}-{today}.yaml"

    tiers = result["tiers"]
    n = result["n"]
    lines = [f"# Triage report - {result['repo']} - {today}", ""]
    lines.append(f"{n} open issues triaged by Goose (qwen3-coder:30b). "
                 "Report-only - no issues were modified.")
    if result["capped"]:
        lines.append("")
        lines.append("**WARNING:** the fetch hit the list cap, so this is a "
                     "partial backlog and the percentile distribution is not "
                     "over the true total. Re-run with full pagination before "
                     "trusting the shape.")
    lines.append("")
    lines.append("## Distribution")
    lines.append("")
    for t in ("P0", "P1", "P2", "P3", "P4"):
        c = len(tiers[t])
        pct = (100 * c / n) if n else 0
        lines.append(f"- **{t}** - {c} ({pct:.0f}%)")
    lines.append("")
    for t in ("P0", "P1", "P2", "P3", "P4"):
        if not tiers[t]:
            continue
        lines.append(f"## {t}")
        lines.append("")
        for it in sorted(tiers[t], key=lambda d: d["num"]):
            extra = f" - {it.get('reason','')}" if it.get("reason") else ""
            score = f" [{it['score']:.0f}]" if "score" in it else ""
            lines.append(f"- #{it['num']} {it['title']}{score}{extra}")
        lines.append("")
    md_path.write_text("\n".join(lines))

    payload = {
        "repo": result["repo"], "date": today, "n": n, "capped": result["capped"],
        "tiers": {
            t: [{"num": it["num"], "title": it["title"],
                 "score": it.get("score"), "reason": it.get("reason", "")}
                for it in sorted(tiers[t], key=lambda d: d["num"])]
            for t in ("P0", "P1", "P2", "P3", "P4")
        },
    }
    yaml_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return md_path, yaml_path


def _default_repo() -> str | None:
    """Slug of the current git origin (owner/name), or None. Under `ward exec`
    cwd is the agentic-os root, so a bare `ward exec goose-triage` targets it."""
    url = sh(["git", "remote", "get-url", "origin"], timeout=10).strip()
    if not url:
        return None
    u = url[:-4] if url.endswith(".git") else url
    u = u.split("://", 1)[-1].split("@", 1)[-1].replace(":", "/", 1)
    parts = [p for p in u.split("/") if p]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Goose-driven issue triage (report-only).")
    ap.add_argument("--repo", help="owner/name; default: the current git origin's slug")
    ap.add_argument("--limit", type=int, default=50, help="max issues to fetch (coily cap is 50)")
    args = ap.parse_args(argv)

    repo = args.repo or _default_repo()
    if not repo:
        ap.error("--repo not given and no git origin found in the current directory")

    result = run(repo, args.limit)
    md_path, yaml_path = write_report(result)

    tiers = result["tiers"]
    print()
    print(f"goose-triage: {result['repo']} - {result['n']} issues")
    for t in ("P0", "P1", "P2", "P3", "P4"):
        print(f"  {t}: {len(tiers[t])}")
    print(f"\nreport -> {md_path}\n        {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
