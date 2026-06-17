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
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
P0_RULES = REPO_ROOT / ".agents/skills/tooling-issue-prioritization/references/p0-content-rules.yaml"
CACHE_DIR = Path.home() / ".cache" / "agentic-os" / "goose-triage"

# Target shares of the non-P0 pool (centers 10/20/30/40, summing to 100).
TARGET = {"P1": 0.10, "P2": 0.20, "P3": 0.30, "P4": 0.40}
TIER_SCORE = {"P1": 3, "P2": 2, "P3": 1, "P4": 0}

P0_CONFIRM = """A keyword scan flagged this issue as a possible P0 (urgent incident). Your ONE job: decide if it describes an ACTIVE, LIVE incident or exposure happening NOW (a real outage, a real leaked credential, actual data loss, a live exploitable bypass, a currently-broken deploy) versus merely DISCUSSING, proposing, documenting, planning, or giving an example of such a topic (a design doc, a hardening proposal, a "set up X" task, a how-to). Output ONLY JSON, no prose, no code fence: {"active_incident":true|false,"reason":"<=12 words"}. When it is discussion / proposal / example / planning, active_incident=false."""

# Two independent rubrics for the urgency pass - different framings give a more
# robust signal than asking the same question twice.
SCORE_RUBRICS = [
    """You are triaging a software backlog. This issue is NOT an active incident. Pick ONE tier by near-term value:
P1 = important AND clearly the next thing to do, concrete committed-direction value.
P2 = real backlog you genuinely intend to act on, just not yet.
P3 = default - low but kept, or you are unsure.
P4 = icebox: speculative / parked / won't-do-soon (hobby or hardware toys, "try X" / "fork Y" wishes, reading-list adds, vague vision, far-future plays, one-line idea stubs).
Output ONLY JSON, no prose, no fence: {"tier":"P1|P2|P3|P4","reason":"<=12 words"}. If unsure, P3.""",
    """Triage this backlog issue by how much NOT doing it soon would hurt. It is NOT an active incident. Pick ONE tier:
P1 = real near-term pain or clearly the next committed step.
P2 = genuinely intended work with a path to done, mid-term.
P3 = minor or uncertain; the safe default.
P4 = parked / speculative / nice-to-have-someday; nothing is lost by deferring indefinitely.
Output ONLY JSON, no prose, no fence: {"tier":"P1|P2|P3|P4","reason":"<=12 words"}. If unsure, P3.""",
]


def sh(args: list[str], timeout: int = 60) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout


def goose(prompt: str, timeout: int = 90) -> dict | None:
    """One tamed Goose call returning the parsed JSON object, or None."""
    cmd = ["goose", "run", "--no-profile", "--quiet", "--no-session",
           "--max-turns", "1", "-t", prompt]
    for _ in range(2):  # one retry on parse/empty failure
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=timeout).stdout
        except subprocess.TimeoutExpired:
            continue
        obj = _extract_json(out)
        if obj is not None:
            return obj
    return None


def _extract_json(text: str) -> dict | None:
    """Pull the first {...} object out of Goose output (tolerates ``` fences)."""
    m = re.search(r"\{.*?\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


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


def percentile_cut(scored: list[dict]) -> None:
    """Rank by summed score desc, assign tiers by target share, snap cuts to
    natural score breaks, floor P1 at zero. Mutates each dict's 'tier'."""
    pool = sorted(scored, key=lambda d: (-d["score"], d["num"]))
    n = len(pool)
    if n == 0:
        return
    # nominal cumulative boundaries from target shares
    b1 = round(TARGET["P1"] * n)
    b2 = b1 + round(TARGET["P2"] * n)
    b3 = b2 + round(TARGET["P3"] * n)

    def snap(idx: int) -> int:
        # move boundary to the nearest rank where the score changes, so a run
        # of equal scores is never split across a tier line
        if idx <= 0 or idx >= n:
            return idx
        if pool[idx - 1]["score"] == pool[idx]["score"]:
            down = idx
            while down > 0 and pool[down - 1]["score"] == pool[idx]["score"]:
                down -= 1
            up = idx
            while up < n and pool[up]["score"] == pool[idx]["score"]:
                up += 1
            return down if (idx - down) <= (up - idx) else up
        return idx

    b1, b2, b3 = snap(b1), snap(b2), snap(b3)
    # P1 floors at zero: only keep a P1 band if its members actually read as P1
    # in at least one scoring pass (sum >= 5 of 6).
    for i, it in enumerate(pool):
        if i < b1 and it["score"] >= 5:
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
    print(f"goose-triage: P0 net flagged {len(cands)} candidate(s); confirming ...",
          file=sys.stderr)

    confirmed_p0 = []
    for num in sorted(cands):
        it = by_num[num]
        res = goose(issue_prompt(P0_CONFIRM, it))
        active = bool(res and res.get("active_incident"))
        if active:
            it["tier"] = "P0"
            it["reason"] = (res or {}).get("reason", "")
            confirmed_p0.append(it)
        print(f"  P0 confirm #{num}: {'CONFIRMED' if active else 'rejected'}",
              file=sys.stderr)

    p0_nums = {it["num"] for it in confirmed_p0}
    pool = [it for it in issues if it["num"] not in p0_nums]
    print(f"goose-triage: scoring {len(pool)} non-P0 issues (2 passes) ...",
          file=sys.stderr)
    for it in pool:
        votes, reasons = [], []
        for rubric in SCORE_RUBRICS:
            res = goose(issue_prompt(rubric, it))
            tier = (res or {}).get("tier", "P3")
            if tier not in TIER_SCORE:
                tier = "P3"
            votes.append(TIER_SCORE[tier])
            if res and res.get("reason"):
                reasons.append(res["reason"])
        it["score"] = sum(votes)
        it["reason"] = reasons[0] if reasons else "unscored -> default P3"
        print(f"  score #{it['num']}: {it['score']}/6", file=sys.stderr)

    percentile_cut(pool)

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
            score = f" [{it['score']}/6]" if "score" in it else ""
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Goose-driven issue triage (report-only).")
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--limit", type=int, default=50, help="max issues to fetch (coily cap is 50)")
    args = ap.parse_args(argv)

    result = run(args.repo, args.limit)
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
