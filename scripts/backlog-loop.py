#!/usr/bin/env python3
"""backlog-loop: the programmatic backbone for a supervised ralph loop over a backlog.

A guided foreground loop drives the whole open backlog of a repo to done. The
deterministic parts live here; the chatty judgment (deciding how to unblock a
stuck agent, talking it through with a human) is the supervisor's, who calls
these verbs. The loop is:

  1. select   - read open issues + their tier/mode labels, rank into two lanes
                (headless = auto-burndown, interactive = human-driven), persist a
                durable ledger so the loop survives a restart. A non-empty untriaged
                lane prints a one-line nudge to run triage; `select --triage` folds
                `ward exec goose-triage` in first so the loop owns its own inputs
                (#278), across the whole scope when one is given.
  2. dispatch - launch a headless agent on a queued issue (`ward agent headless`),
                first posting a structured-outcome protocol comment so the agent
                knows to end with a machine-readable WARD-OUTCOME line.
  3. poll     - find which dispatched containers have exited (docker ps by the
                `-issue-<N>-` name convention) and read each one's WARD-OUTCOME
                comment to classify done / blocked / failed.
  4. unblock  - record the human's guidance as a comment and re-queue the issue.
  Repeat dispatch -> poll -> unblock until the headless lane is drained.

A scope spans more than one repo. `--repo a/b,c/d` (comma-separated, the scope)
runs select / next / poll across the whole set in one invocation: each repo keeps
its own durable ledger, but the scope-aware verbs aggregate them into one ranked
view and poll every dispatched container together, instead of one `--repo` at a
time (agentic-os#279). Per-issue verbs (dispatch / outcome / unblock / mark) take
a `<num>` or, to disambiguate across a multi-repo scope, an `<owner/name>#<num>`
ref. Named scopes graduate into ward as a first-class type (`ward agent backlog
<scope>`); here the scope is just its repo list.

This is the supervised, foreground form of the heartbeat loop (agentic-os#237)
and it consumes the automation-mode axis the dispatch ceiling gate (agentic-os#246)
defines. The triage that writes those labels is `ward exec goose-triage`; this
loop reads them, it does not recompute them.

All forgejo I/O goes through `ward ops forgejo` (ward-kdl), which authenticates as
the `coilyco-ops` bot from SSM, so this script holds no token and needs no
FORGEJO_TOKEN (agentic-os#267). Dispatch shells `ward agent headless`.

The structured-outcome channel is injected at dispatch time as an issue comment
(the agent reads issue comments into its seed), so v1 needs no ward change. The
clean home for it is the ward headless seed; promoting it there is a follow-up.

See docs/backlog-loop.md and the tooling-backlog-loop skill.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

CACHE_DIR = Path.home() / ".cache" / "agentic-os" / "backlog-loop"
TRIAGE_CACHE = Path.home() / ".cache" / "agentic-os" / "goose-triage"

# ward-kdl ops forgejo + ward agent binary. Overridable for tests.
WARD = os.environ.get("WARD_BIN") or "ward"

# `select --triage` shells `ward exec goose-triage`, which runs several LLM passes
# per open issue, so it needs far more room than a forgejo read. Overridable.
TRIAGE_TIMEOUT = int(os.environ.get("BACKLOG_LOOP_TRIAGE_TIMEOUT") or "3600")

# Tier and mode label vocabularies, mirroring tooling-issue-prioritization. Order
# matters: TIER_ORDER ranks high-to-low, MODE_LANE maps a mode to a loop lane.
TIER_ORDER = ("P0", "P1", "P2", "P3", "P4")
MODE_LANE = {"headless": "headless", "interactive": "interactive", "consult": "consult"}

# Lanes the loop tracks. headless auto-dispatches; interactive surfaces to a human
# to hand-drive; consult/untriaged hold until triaged or promoted.
LANES = ("headless", "interactive", "consult", "untriaged")

# Ledger states an issue moves through. surfaced = shown to the human (interactive
# lane); blocked = agent raised its hand and is awaiting an unblock.
STATES = ("queued", "dispatched", "blocked", "done", "failed", "surfaced", "skipped")

# The structured-outcome protocol. A dispatched agent must end with a final comment
# whose first line is one of these; the loop parses it to classify the run.
OUTCOME_MARKER = "WARD-OUTCOME:"
OUTCOME_STATUSES = ("done", "blocked", "failed")
# HTML markers so the loop can find its own injected comments and never double-post.
DISPATCH_MARKER = "<!-- backlog-loop:dispatch -->"
UNBLOCK_MARKER = "<!-- backlog-loop:unblock -->"

DISPATCH_PROTOCOL = f"""{DISPATCH_MARKER}
\U0001f501 **backlog-loop dispatch** - this issue was auto-dispatched by the supervised backlog loop.

When you finish, your **final issue comment** must start with exactly one of:

- `{OUTCOME_MARKER} done` - landed/merged, nothing more needed.
- `{OUTCOME_MARKER} blocked - <the specific decision or information you need from a human>`
- `{OUTCOME_MARKER} failed - <why, briefly>`

Put your candid retrospective on the line(s) below it. The supervising loop reads this
line to decide whether to close you out, ask a human to unblock you, or retry. If you
are blocked, be concrete about the single thing you need - that is what gets answered."""


class WardError(RuntimeError):
    """A `ward` call exited non-zero; carries the captured stderr for the caller."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sh(cmd: list[str], timeout: int = 60) -> str:
    """Run a command, return stdout, raise WardError(stderr) on non-zero exit."""
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise WardError((proc.stderr or proc.stdout or "").strip()
                        or f"{' '.join(cmd)} failed")
    return proc.stdout or ""


def _split_repo(repo: str) -> tuple[str, str]:
    """Split an "owner/name" slug into (owner, name) for ward-kdl path args."""
    owner, _, name = repo.partition("/")
    if not owner or not name:
        raise ValueError(f"repo must be 'owner/name', got {repo!r}")
    return owner, name


def _fj(args: list[str], parse: bool = True, timeout: int = 60) -> object:
    """One `ward ops forgejo <args>` call, the auth boundary for all forgejo I/O.

    `--output json` is appended for reads (parse=True); stdout JSON is parsed and
    returned (None for an empty body). A non-zero exit raises WardError(stderr)."""
    cmd = [WARD, "ops", "forgejo", *args]
    if parse:
        cmd += ["--output", "json"]
    out = sh(cmd, timeout=timeout).strip()
    if not parse or not out:
        return None
    return json.loads(out)


def _default_repo() -> str | None:
    """Slug of the current git origin (owner/name), or None."""
    try:
        url = sh(["git", "remote", "get-url", "origin"], timeout=10).strip()
    except (WardError, OSError):
        return None
    if not url:
        return None
    u = url[:-4] if url.endswith(".git") else url
    u = u.split("://", 1)[-1].split("@", 1)[-1].replace(":", "/", 1)
    parts = [p for p in u.split("/") if p]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def parse_repos(repo_arg: str | None, default: str | None) -> list[str]:
    """Resolve the scope: a comma-separated `--repo` list, or the git-origin default.

    Splits on commas, trims blanks, and de-dupes while preserving order so the
    scope is stable. One repo is a scope of one; the verbs treat both the same."""
    raw = repo_arg if repo_arg is not None else default
    if not raw:
        return []
    seen: list[str] = []
    for slug in raw.split(","):
        slug = slug.strip()
        if slug and slug not in seen:
            seen.append(slug)
    return seen


def resolve_ref(repos: list[str], token: str) -> tuple[str, int]:
    """Resolve a per-issue verb's target to (repo, num) within the scope.

    `token` is either a bare `<num>` or an `<owner/name>#<num>` ref. A bare num
    needs no qualifier in a single-repo scope; across a multi-repo scope it must
    resolve to exactly one repo that tracks it (via the ledgers), else the caller
    is told to qualify with `<owner/name>#<num>`."""
    if "#" in token:
        repo, _, num = token.partition("#")
        repo, num = repo.strip(), num.strip()
        if not repo or not num.isdigit():
            raise ValueError(f"ref must be '<owner/name>#<num>', got {token!r}")
        return repo, int(num)
    if not token.strip().isdigit():
        raise ValueError(f"issue must be a number or '<owner/name>#<num>', got {token!r}")
    num = int(token)
    if len(repos) == 1:
        return repos[0], num
    holders = [r for r in repos if str(num) in load_ledger(r).get("issues", {})]
    if len(holders) == 1:
        return holders[0], num
    if not holders:
        raise ValueError(f"#{num} is not tracked in this scope - qualify it as '<owner/name>#{num}'")
    raise ValueError(f"#{num} is ambiguous across {', '.join(holders)} - qualify it as '<owner/name>#{num}'")


# --- ledger persistence ----------------------------------------------------

def ledger_path(repo: str) -> Path:
    return CACHE_DIR / (repo.replace("/", "-") + ".yaml")


def load_ledger(repo: str) -> dict:
    """Load the durable ledger for a repo, or a fresh empty one."""
    path = ledger_path(repo)
    if path.exists():
        data = yaml.safe_load(path.read_text()) or {}
        data.setdefault("repo", repo)
        data.setdefault("issues", {})
        return data
    return {"repo": repo, "updated": None, "issues": {}}


def save_ledger(led: dict) -> Path:
    """Persist the ledger atomically. Keys are issue numbers (ints) as strings."""
    led["updated"] = _now()
    path = ledger_path(led["repo"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(led, sort_keys=True, default_flow_style=False))
    tmp.replace(path)
    return path


# --- triage-score lookup (best effort, for intra-tier ordering) ------------

def _latest_triage_scores(repo: str) -> dict[int, float]:
    """Read per-issue scores from the most recent cached goose-triage YAML, if any.

    Scores only break ties within a tier; absence is fine (we fall back to issue
    number). Returns {issue_number: score}."""
    prefix = repo.replace("/", "-")
    cands = sorted(TRIAGE_CACHE.glob(f"{prefix}-*.yaml"), reverse=True)
    for path in cands:
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except (OSError, yaml.YAMLError):
            continue
        scores: dict[int, float] = {}
        for tier in data.get("tiers", {}).values() if isinstance(data.get("tiers"), dict) else []:
            for it in tier or []:
                if isinstance(it, dict) and "num" in it and it.get("score") is not None:
                    scores[int(it["num"])] = float(it["score"])
        if scores:
            return scores
    return {}


# --- selection -------------------------------------------------------------

def _label_names(labels: list) -> list[str]:
    """Normalize a forgejo labels field to plain name strings. `issue list` returns
    raw label objects ({"name": ...}); the lean projection returns strings already."""
    out = []
    for lab in labels or []:
        if isinstance(lab, dict):
            name = lab.get("name")
            if name:
                out.append(name)
        elif isinstance(lab, str):
            out.append(lab)
    return out


def _tier_of(labels: list[str]) -> str | None:
    for t in TIER_ORDER:
        if t in labels:
            return t
    return None


def _mode_of(labels: list[str]) -> str | None:
    for m in MODE_LANE:
        if m in labels:
            return m
    return None


def _lane_for(tier: str | None, mode: str | None) -> str:
    """Map (tier, mode) to a loop lane. Untriaged = missing either label."""
    if tier is None or mode is None:
        return "untriaged"
    return MODE_LANE.get(mode, "consult")


def fetch_open_issues(repo: str, limit: int) -> list[dict]:
    """Open issues (not pulls) with labels, via ward ops forgejo issue list."""
    owner, name = _split_repo(repo)
    raw = _fj(["issue", "list", owner, name, "--state", "open",
               "--type", "issues", "--limit", str(limit)])
    return raw if isinstance(raw, list) else []


def rank(issues: list[dict], scores: dict[int, float]) -> list[dict]:
    """Annotate each issue with tier/mode/lane/score and sort within the work-set.

    Sort key: lane priority (headless first, then interactive), then tier
    (P0..P4), then score desc, then issue number. The supervisor pulls from the
    top of each lane."""
    lane_rank = {"headless": 0, "interactive": 1, "consult": 2, "untriaged": 3}
    tier_rank = {t: i for i, t in enumerate(TIER_ORDER)}
    out = []
    for it in issues:
        labels = _label_names(it.get("labels") or [])
        tier = _tier_of(labels)
        mode = _mode_of(labels)
        num = int(it["number"])
        out.append({
            "num": num,
            "title": it.get("title") or "",
            "tier": tier,
            "mode": mode,
            "lane": _lane_for(tier, mode),
            "score": scores.get(num),
            "url": it.get("html_url") or "",
        })
    out.sort(key=lambda d: (
        lane_rank.get(d["lane"], 9),
        tier_rank.get(d["tier"], 9),
        -(d["score"] if d["score"] is not None else -1.0),
        d["num"],
    ))
    return out


def refresh_ledger(repo: str, limit: int) -> dict:
    """Build/refresh one repo's ledger from its live backlog; save and return it.

    A new issue lands as queued (headless), surfaced (interactive), or skipped
    (consult/untriaged). An issue already dispatched/blocked/done keeps its state
    so a re-select mid-loop never clobbers progress; only its metadata refreshes."""
    issues = fetch_open_issues(repo, limit)
    ranked = rank(issues, _latest_triage_scores(repo))
    led = load_ledger(repo)
    seen = set()
    for r in ranked:
        seen.add(r["num"])
        key = str(r["num"])
        prior = led["issues"].get(key, {})
        entry = {**prior, **r}
        if not prior:
            if r["lane"] == "headless":
                entry["state"] = "queued"
            elif r["lane"] == "interactive":
                entry["state"] = "surfaced"
            else:
                entry["state"] = "skipped"
            entry["unblock_history"] = []
        elif r["lane"] == "headless" and entry.get("state") in ("skipped", "surfaced"):
            # A re-triage promoted this issue into headless from a non-in-flight
            # holding state - re-queue so `next` sees it, not strand it (#277).
            entry["state"] = "queued"
        led["issues"][key] = entry
    # Drop issues that closed since the last select (gone from the open set),
    # unless they are still mid-flight and worth keeping visible.
    for key in list(led["issues"]):
        if int(key) not in seen and led["issues"][key].get("state") in ("done", "skipped", "surfaced"):
            del led["issues"][key]
    save_ledger(led)
    return led


def run_triage(repos: list[str]) -> None:
    """Run `ward exec goose-triage` across the scope so the loop owns its own inputs.

    Triage writes the tier + mode labels `select` reads. Running it inline (via
    `select --triage`) before the re-select populates the headless lane in one hop,
    instead of the separate manual `ward exec goose-triage` hop the loop used to
    need - an empty headless lane that was really just an un-run triage (#278). Each
    repo is triaged on its own, mirroring how the scope keeps one ledger per repo."""
    for repo in repos:
        print(f"backlog-loop: triaging {repo} (ward exec goose-triage) ...", file=sys.stderr)
        sh([WARD, "exec", "goose-triage", "--", "--repo", repo], timeout=TRIAGE_TIMEOUT)


def _untriaged_hint(leds: list[dict]) -> None:
    """Print a one-line nudge when any tracked issue across `leds` is still untriaged.

    The untriaged lane stays empty until `ward exec goose-triage` writes the tier +
    mode labels, so an empty headless lane is often just an un-run triage. Naming the
    count and the command (plus the inline `--triage` flag that does both) means the
    loop surfaces its own missing input rather than leaving the gap unexplained."""
    n = sum(1 for led in leds for e in led["issues"].values()
            if e.get("lane") == "untriaged")
    if not n:
        return
    print(f"\n  {n} untriaged - run `ward exec goose-triage` to label them, "
          f"or re-run `select --triage` to triage + re-select in one hop.")


def cmd_select(repo: str, limit: int, triage: bool = False) -> int:
    """Single-repo select: optionally triage inline, refresh the ledger, print lanes."""
    if triage:
        run_triage([repo])
    led = refresh_ledger(repo, limit)
    _print_status(led)
    _untriaged_hint([led])
    return 0


# --- status ----------------------------------------------------------------

def _by_lane(led: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {ln: [] for ln in LANES}
    for e in led["issues"].values():
        out.setdefault(e.get("lane", "untriaged"), []).append(e)
    for ln in out:
        out[ln].sort(key=lambda d: d["num"])
    return out


def _print_status(led: dict) -> None:
    lanes = _by_lane(led)
    print(f"backlog-loop: {led['repo']} ({len(led['issues'])} tracked, updated {led.get('updated')})")
    for ln in LANES:
        items = lanes.get(ln) or []
        if not items:
            continue
        print(f"\n  {ln} lane ({len(items)}):")
        for e in items:
            tier = e.get("tier") or "--"
            sc = f" {e['score']:.0f}" if e.get("score") is not None else ""
            print(f"    #{e['num']:<5} [{tier}{sc}] {e.get('state','?'):<10} {e['title'][:70]}")


def cmd_status(repo: str) -> int:
    _print_status(load_ledger(repo))
    return 0


def _actionable_picks(led: dict, lane: str) -> list[dict]:
    """The lane's entries that need action: queued/surfaced to start, blocked to unblock."""
    want = {"headless": ("queued", "blocked"), "interactive": ("surfaced", "blocked")}.get(lane, ("queued",))
    return [e for e in _by_lane(led).get(lane, []) if e.get("state") in want]


def cmd_next(repo: str, lane: str, count: int) -> int:
    """Emit the next actionable issues in a lane as JSON, for the supervisor.

    headless -> queued issues ready to dispatch; interactive -> surfaced issues
    for a human to drive. Blocked issues are returned too (they need a human)."""
    picks = _actionable_picks(load_ledger(repo), lane)
    picks.sort(key=lambda d: (0 if d["state"] == "blocked" else 1, d["num"]))
    print(json.dumps(picks[:count], indent=2))
    return 0


# --- dispatch --------------------------------------------------------------

def _container_for_issue(num: int, repo: str) -> str | None:
    """Best-effort: the running ward container name for this issue, via docker ps.

    Matches the `-issue-<N>-` segment of the ward container name convention. Returns
    the first match or None."""
    safe = _split_repo(repo)[1].replace("/", "-")
    try:
        out = sh(["docker", "ps", "--format", "{{.Names}}",
                  "--filter", f"name=-issue-{num}-"], timeout=15)
    except (WardError, OSError):
        return None
    for line in out.splitlines():
        nm = line.strip()
        if nm and f"-issue-{num}-" in nm and safe in nm:
            return nm
    return None


def _post_comment(repo: str, num: int, body: str) -> None:
    owner, name = _split_repo(repo)
    _fj(["issue", "comment", owner, name, str(num), "--body", body], parse=False)


def _has_marker(repo: str, num: int, marker: str) -> bool:
    owner, name = _split_repo(repo)
    raw = _fj(["issue-comment", "list", owner, name, str(num)])
    for c in (raw if isinstance(raw, list) else []):
        if marker in (c.get("body") or ""):
            return True
    return False


def cmd_dispatch(repo: str, num: int, no_preflight: bool, force: bool, dry_run: bool) -> int:
    """Launch a headless agent on one issue, after posting the outcome protocol.

    Idempotent on the protocol comment (posts once per issue). Records the launch
    in the ledger as dispatched + the resolved container name + a timestamp."""
    led = load_ledger(repo)
    key = str(num)
    entry = led["issues"].get(key) or {"num": num, "lane": "headless", "unblock_history": []}
    ref = f"{repo}#{num}"
    if dry_run:
        print(f"[dry-run] would post protocol + `ward agent headless {ref}`")
        return 0
    if not _has_marker(repo, num, DISPATCH_MARKER):
        _post_comment(repo, num, DISPATCH_PROTOCOL)
    cmd = [WARD, "agent", "headless", ref]
    if no_preflight:
        cmd.append("--no-preflight")
    if force:
        cmd.append("--force")
    print(f"backlog-loop: dispatching {ref} ...", file=sys.stderr)
    try:
        sh(cmd, timeout=600)
    except WardError as e:
        entry["state"] = "failed"
        entry["last_outcome"] = {"status": "dispatch-error", "text": str(e)[:300]}
        led["issues"][key] = entry
        save_ledger(led)
        print(f"backlog-loop: dispatch FAILED for {ref}: {str(e)[:200]}", file=sys.stderr)
        return 1
    entry["state"] = "dispatched"
    entry["dispatched_at"] = _now()
    entry["container"] = _container_for_issue(num, repo)
    led["issues"][key] = entry
    save_ledger(led)
    print(f"backlog-loop: dispatched {ref} (container {entry['container']})")
    return 0


# --- outcome parsing + poll ------------------------------------------------

def parse_outcome(comments: list[dict]) -> dict | None:
    """Find the latest agent WARD-OUTCOME across comments and parse it.

    The agent's final comment leads a line with the marker; match only at line
    start (after markdown bullet/quote chars), and skip the loop's own injected
    comments, whose examples embed the marker. Returns {"status":
    done|blocked|failed|unknown, "text": ...} for the latest match, else None."""
    hits = []
    for c in comments:
        body = c.get("body") or ""
        if DISPATCH_MARKER in body or UNBLOCK_MARKER in body:
            continue
        line = None
        for ln in body.splitlines():
            stripped = ln.strip().lstrip(">*-• ").strip()
            if stripped.upper().startswith(OUTCOME_MARKER):
                line = stripped
                break
        if line is None:
            continue
        rest = line[len(OUTCOME_MARKER):].strip()
        m = re.match(r"(done|blocked|failed)\b[\s:.-]*(.*)", rest, re.IGNORECASE)
        status = m.group(1).lower() if m else "unknown"
        text = (m.group(2).strip() if m else rest)
        hits.append((c.get("created_at") or "", {"status": status, "text": text[:500]}))
    if not hits:
        return None
    hits.sort(key=lambda h: h[0])
    return hits[-1][1]


def read_outcome(repo: str, num: int) -> dict | None:
    owner, name = _split_repo(repo)
    raw = _fj(["issue-comment", "list", owner, name, str(num)])
    return parse_outcome(raw if isinstance(raw, list) else [])


def cmd_outcome(repo: str, num: int) -> int:
    out = read_outcome(repo, num)
    print(json.dumps(out, indent=2) if out else "null")
    return 0


def poll_repo(repo: str) -> list[tuple]:
    """Reconcile one repo's dispatched issues against reality; save and return transitions.

    For each dispatched entry: if its container is gone, read the WARD-OUTCOME
    comment and move it to blocked / done / failed. A still-running container stays
    dispatched. An exited container with no outcome posted is left dispatched and
    flagged so the supervisor can inspect the container log."""
    led = load_ledger(repo)
    transitions = []
    for key, e in led["issues"].items():
        if e.get("state") != "dispatched":
            continue
        num = e["num"]
        if _container_for_issue(num, repo):
            continue
        outcome = read_outcome(repo, num)
        if outcome is None:
            transitions.append((num, "dispatched", "exited-no-outcome"))
            e["last_outcome"] = {"status": "exited-no-outcome", "text": ""}
            led["issues"][key] = e
            continue
        new = {"done": "done", "blocked": "blocked", "failed": "failed"}.get(outcome["status"], "blocked")
        e["state"] = new
        e["last_outcome"] = outcome
        led["issues"][key] = e
        transitions.append((num, new, outcome.get("text", "")[:120]))
    save_ledger(led)
    return transitions


def cmd_poll(repo: str) -> int:
    """Single-repo poll: reconcile dispatched issues and report transitions."""
    transitions = poll_repo(repo)
    if not transitions:
        print("backlog-loop: no transitions (nothing exited since last poll)")
    for num, st, txt in transitions:
        print(f"  #{num} -> {st}" + (f": {txt}" if txt else ""))
    return 0


# --- unblock + mark --------------------------------------------------------

def cmd_unblock(repo: str, num: int, note: str) -> int:
    """Post the human's unblock guidance to the issue and re-queue it.

    The guidance lands as a marked comment the re-dispatched agent reads as context,
    and is recorded in the ledger's unblock_history."""
    body = f"{UNBLOCK_MARKER}\n\U0001f513 **Unblock guidance** (backlog-loop)\n\n{note}"
    _post_comment(repo, num, body)
    led = load_ledger(repo)
    key = str(num)
    entry = led["issues"].get(key) or {"num": num, "lane": "headless"}
    entry.setdefault("unblock_history", []).append({"at": _now(), "note": note})
    entry["state"] = "queued"
    led["issues"][key] = entry
    save_ledger(led)
    print(f"backlog-loop: unblocked #{num} (re-queued for dispatch)")
    return 0


def cmd_mark(repo: str, num: int, state: str) -> int:
    if state not in STATES:
        print(f"backlog-loop: state must be one of {', '.join(STATES)}", file=sys.stderr)
        return 2
    led = load_ledger(repo)
    key = str(num)
    entry: dict = led["issues"].get(key) or {"num": num}
    entry["state"] = state
    led["issues"][key] = entry
    save_ledger(led)
    print(f"backlog-loop: marked #{num} -> {state}")
    return 0


# --- scope: one ranked view across many repos ------------------------------

def scope_name(repos: list[str]) -> str:
    """A stable display name for a scope: the single slug, or the joined set."""
    return repos[0] if len(repos) == 1 else ", ".join(repos)


def _scope_entries(repos: list[str]) -> list[dict]:
    """Every tracked entry across the scope's repos, each tagged with its repo."""
    out: list[dict] = []
    for repo in repos:
        for e in load_ledger(repo)["issues"].values():
            out.append({**e, "repo": repo})
    return out


def _scope_sort_key(e: dict) -> tuple:
    """Rank one entry within its lane across repos: tier, score desc, repo, num."""
    tier_rank = {t: i for i, t in enumerate(TIER_ORDER)}
    return (
        tier_rank.get(e.get("tier"), 9),
        -(e["score"] if e.get("score") is not None else -1.0),
        e.get("repo", ""),
        e.get("num", 0),
    )


def _print_scope_status(repos: list[str]) -> None:
    """Print one combined, lane-grouped, cross-repo-ranked view of the scope."""
    entries = _scope_entries(repos)
    print(f"backlog-loop scope: {scope_name(repos)} "
          f"({len(repos)} repos, {len(entries)} tracked)")
    by_lane: dict[str, list[dict]] = {ln: [] for ln in LANES}
    for e in entries:
        by_lane.setdefault(e.get("lane", "untriaged"), []).append(e)
    for ln in LANES:
        items = by_lane.get(ln) or []
        if not items:
            continue
        items.sort(key=_scope_sort_key)
        print(f"\n  {ln} lane ({len(items)}):")
        for e in items:
            tier = e.get("tier") or "--"
            sc = f" {e['score']:.0f}" if e.get("score") is not None else ""
            ref = f"{e['repo']}#{e['num']}"
            print(f"    {ref:<28} [{tier}{sc}] {e.get('state','?'):<10} {e['title'][:60]}")


def cmd_select_scope(repos: list[str], limit: int, triage: bool = False) -> int:
    """Refresh every repo's ledger in the scope, then print one combined view.

    With --triage the whole scope is triaged first (one `ward exec goose-triage` per
    repo) so a scope triages and selects together in one invocation (#278)."""
    if triage:
        run_triage(repos)
    leds = [refresh_ledger(repo, limit) for repo in repos]
    _print_scope_status(repos)
    _untriaged_hint(leds)
    return 0


def cmd_status_scope(repos: list[str]) -> int:
    _print_scope_status(repos)
    return 0


def cmd_next_scope(repos: list[str], lane: str, count: int) -> int:
    """Emit the next actionable issues across the whole scope as JSON (ref-tagged).

    Merges each repo's lane picks into one ranked list - blocked first (a human is
    waiting), then the cross-repo lane order - so the supervisor pulls the single
    most-actionable issue regardless of which repo it lives in."""
    merged: list[dict] = []
    for repo in repos:
        for e in _actionable_picks(load_ledger(repo), lane):
            merged.append({**e, "repo": repo})
    merged.sort(key=lambda d: (0 if d["state"] == "blocked" else 1, _scope_sort_key(d)))
    print(json.dumps(merged[:count], indent=2))
    return 0


def cmd_poll_scope(repos: list[str]) -> int:
    """Poll every dispatched container across the scope in one pass."""
    any_trans = False
    for repo in repos:
        for num, st, txt in poll_repo(repo):
            any_trans = True
            print(f"  {repo}#{num} -> {st}" + (f": {txt}" if txt else ""))
    if not any_trans:
        print("backlog-loop: no transitions (nothing exited since last poll)")
    return 0


# --- cli -------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Supervised ralph-loop backbone over a repo backlog.")
    ap.add_argument("--repo", help="owner/name, or a comma-separated scope 'a/b,c/d'; "
                                    "default: the current git origin's slug")
    sub = ap.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("select", help="build/refresh the ledger from the live backlog")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--triage", action="store_true",
                   help="run `ward exec goose-triage` across the scope first, then select")
    sub.add_parser("status", help="show the ledger")

    p = sub.add_parser("next", help="emit the next actionable issues in a lane (JSON)")
    p.add_argument("--lane", default="headless", choices=list(LANES))
    p.add_argument("--count", type=int, default=3)

    p = sub.add_parser("dispatch", help="launch a headless agent on one issue")
    p.add_argument("num", help="<num>, or '<owner/name>#<num>' to pick a repo in a multi-repo scope")
    p.add_argument("--no-preflight", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    sub.add_parser("poll", help="reconcile dispatched issues against docker + outcomes")

    p = sub.add_parser("outcome", help="parse one issue's WARD-OUTCOME comment")
    p.add_argument("num", help="<num>, or '<owner/name>#<num>'")

    p = sub.add_parser("unblock", help="post unblock guidance + re-queue an issue")
    p.add_argument("num", help="<num>, or '<owner/name>#<num>'")
    p.add_argument("--note", required=True)

    p = sub.add_parser("mark", help="manually set an issue's ledger state")
    p.add_argument("num", help="<num>, or '<owner/name>#<num>'")
    p.add_argument("--state", required=True)

    args = ap.parse_args(argv)
    repos = parse_repos(args.repo, _default_repo())
    if not repos:
        ap.error("--repo not given and no git origin found in the current directory")

    # Scope-aware verbs aggregate the whole repo set; per-issue verbs resolve to
    # a single (repo, num) ref - bare num in a one-repo scope, qualified across many.
    if args.verb == "select":
        return (cmd_select_scope(repos, args.limit, args.triage) if len(repos) > 1
                else cmd_select(repos[0], args.limit, args.triage))
    if args.verb == "status":
        return cmd_status_scope(repos) if len(repos) > 1 else cmd_status(repos[0])
    if args.verb == "next":
        return cmd_next_scope(repos, args.lane, args.count) if len(repos) > 1 else cmd_next(repos[0], args.lane, args.count)
    if args.verb == "poll":
        return cmd_poll_scope(repos) if len(repos) > 1 else cmd_poll(repos[0])

    if args.verb in ("dispatch", "outcome", "unblock", "mark"):
        try:
            repo, num = resolve_ref(repos, args.num)
        except ValueError as e:
            ap.error(str(e))
        if args.verb == "dispatch":
            return cmd_dispatch(repo, num, args.no_preflight, args.force, args.dry_run)
        if args.verb == "outcome":
            return cmd_outcome(repo, num)
        if args.verb == "unblock":
            return cmd_unblock(repo, num, args.note)
        if args.verb == "mark":
            return cmd_mark(repo, num, args.state)
    ap.error(f"unknown verb {args.verb}")


if __name__ == "__main__":
    raise SystemExit(main())
