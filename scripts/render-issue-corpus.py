#!/usr/bin/env python3
"""render-issue-corpus: a git-mirrored discovery index of Forgejo issues.

The motivating gap (agentic-os#297): a critical fact lived in a Forgejo issue and
neither Kai nor an agent could find it, because there is no way to *grep every
body and comment across every repo* offline. `ward ops forgejo issue list-all`
gives title/label filtering and one-issue-at-a-time reads; it cannot answer "which
issue anywhere mentions this phrase". This renderer closes that gap by rendering
the issue corpus to one markdown file per issue, committed to a private git mirror
repo that the warm-cache machinery hydrates into containers. An agent greps the
corpus offline to *locate* an issue, then confirms its live state with `ward ops
forgejo issue view <owner> <name> <N>`.

It is a DISCOVERY INDEX, not an offline source of truth. The render is a
point-in-time snapshot, so every file carries a disclaimer pointing back at the
live `issue view` verb - the anti-drift discipline AGENTS.md mandates (a snapshot
must never silently anchor a stale picture).

Scope: all tracked source repos (scripts/issue-corpus-repos.txt), open AND closed
issues, bodies and every comment. The needle could just as easily live in a closed
issue. The source list is a small config, deliberately distinct from the public
image seed (docker/dev-base/substrate-image-repos.txt): the corpus adds the
private coilysiren/inbox, which must never land in the public substrate image.

Output layout, under the mirror repo root (--mirror-dir):

    <owner>/<name>/<index>-<slug>.md   one file per issue
    manifest.json                      issue -> updated_at, for incremental runs

Each run is incremental where it matters: list-all returns every issue's
updated_at cheaply, so an issue whose updated_at is unchanged since the last run
(recorded in manifest.json) is skipped without the per-issue comment fetch, which
is the expensive call. Pass --force to re-render everything.

Token boundary: all Forgejo I/O routes through `ward ops forgejo` (ward-kdl),
which authenticates as the coilyco-ops bot from SSM, so this script holds no
FORGEJO_TOKEN - the same boundary scripts/goose-triage.py uses (agentic-os#267).

Privacy: the mirror repo MUST be private (it carries coilysiren/inbox). Before the
caller (the .forgejo/workflows/issue-corpus.yml cron) pushes, this script runs
trufflehog over the rendered corpus as the secret-scan backstop and exits non-zero
on any finding, so an unscanned or leaky corpus never reaches the push. Pass
--no-scan only for local dry runs.

Git is intentionally NOT in this script: the cron clones the private mirror with
credentials, runs this renderer to populate it, then commits and pushes. Keeping
git out keeps the renderer hermetic and unit-testable (the forgejo calls mock to
subprocess). See docs/issue-corpus.md and AGENTS.md (authoring vs rollout).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPOS_FILE = REPO_ROOT / "scripts" / "issue-corpus-repos.txt"
MANIFEST_NAME = "manifest.json"
SLUG_MAX = 50

# ward-kdl ops forgejo binary. Overridable for tests; defaults to the ward CLI on
# PATH, which dispatches the spec-driven ward-kdl forgejo surface.
WARD = os.environ.get("WARD_BIN") or "ward"


class WardForgejoError(RuntimeError):
    """A `ward ops forgejo` call exited non-zero. Carries the captured stderr so
    callers can surface the failure rather than silently drop it."""


# Bounded exponential backoff for the transient `ward` not-found window;
# rationale in `_fj`. Attempts total, base seconds for the first retry's sleep.
_FJ_MAX_ATTEMPTS = 5
_FJ_BACKOFF_BASE = 1.0


def _sleep(seconds: float) -> None:
    """Backoff wait between `_fj` retries, isolated so tests override it (no real sleep)."""
    time.sleep(seconds)


def _split_repo(repo: str) -> tuple[str, str]:
    """Split an "owner/name" slug into (owner, name). ward-kdl's `restrict owner
    matches coily*` gate still applies downstream (both source orgs match)."""
    owner, _, name = repo.partition("/")
    if not owner or not name:
        raise ValueError(f"repo must be 'owner/name', got {repo!r}")
    return owner, name


def _fj(args: list[str], parse: bool = True, timeout: int = 120) -> object:
    """One `ward ops forgejo <args>` call, the auth boundary for all Forgejo I/O.

    ward-kdl authenticates as the coilyco-ops bot from SSM, so nothing here needs
    FORGEJO_TOKEN (agentic-os#267). `--output json` is appended for read verbs and
    the stdout JSON parsed; an empty body returns None. A non-zero exit raises
    WardForgejoError(stderr) so a repo's failure is surfaced, not silently empty.

    A transient `ward` not-found (agentic-os#280) surfaces as an OSError from
    subprocess.run before ward ever runs, so nothing was written - the whole call is
    safe to retry. Bounded exponential backoff rides out the momentary window; the
    OSError is re-raised once attempts are exhausted, so a genuinely-missing ward
    still fails loudly rather than the retry masking it as an empty render."""
    cmd = [WARD, "ops", "forgejo", *args]
    if parse:
        cmd += ["--output", "json"]
    for attempt in range(_FJ_MAX_ATTEMPTS):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            break
        except OSError:
            if attempt + 1 >= _FJ_MAX_ATTEMPTS:
                raise
            _sleep(_FJ_BACKOFF_BASE * (2 ** attempt))
    if proc.returncode != 0:
        raise WardForgejoError((proc.stderr or proc.stdout or "").strip()
                               or f"ward ops forgejo {' '.join(args)} failed")
    out = (proc.stdout or "").strip()
    if not parse or not out:
        return None
    return json.loads(out)


def load_repos(path: Path) -> list[str]:
    """Parse the source-repo config: one owner/name per line, '#' comments and
    blank lines ignored. Mirrors the substrate-image-repos.txt format on purpose."""
    repos = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        _split_repo(line)  # validate shape early; raises on a malformed entry
        repos.append(line)
    return repos


def slugify(title: str) -> str:
    """A filesystem-safe, greppable slug from an issue title: lowercase, runs of
    non-alphanumerics collapsed to single hyphens, trimmed, length-capped. Empty
    or all-symbol titles fall back to 'untitled' so the path is always well-formed."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > SLUG_MAX:
        slug = slug[:SLUG_MAX].rstrip("-")
    return slug or "untitled"


def issue_relpath(repo: str, issue: dict) -> str:
    """Mirror-repo-relative path for one issue: <owner>/<name>/<index>-<slug>.md."""
    owner, name = _split_repo(repo)
    return f"{owner}/{name}/{issue['number']}-{slugify(issue.get('title') or '')}.md"


def list_issues(repo: str, since: str | None = None) -> list[dict]:
    """Every issue (open AND closed, not PRs) for a repo via one auto-paginated
    `ward ops forgejo issue list-all`. `--type issues` drops PRs at the API; the
    pull_request guard is belt-and-suspenders for older Forgejo. `--since` narrows
    the listing to issues updated after a timestamp when the caller wants it."""
    owner, name = _split_repo(repo)
    args = ["issue", "list-all", owner, name, "--state", "all", "--type", "issues"]
    if since:
        args += ["--since", since]
    data = _fj(args)
    issues = []
    for it in data if isinstance(data, list) else []:
        if it.get("pull_request") is not None:
            continue
        issues.append(it)
    return issues


def list_comments(repo: str, num: int) -> list[dict]:
    """Every comment on one issue via `ward ops forgejo issue-comment list`."""
    owner, name = _split_repo(repo)
    data = _fj(["issue-comment", "list", owner, name, str(num)])
    return data if isinstance(data, list) else []


def _label_names(issue: dict) -> list[str]:
    """Forgejo labels arrive as objects; pull just the names for the header."""
    out = []
    for lb in issue.get("labels") or []:
        name = lb.get("name") if isinstance(lb, dict) else lb
        if name:
            out.append(str(name))
    return out


def _user_login(obj: dict) -> str:
    """Author login from an issue or comment, or 'unknown' when absent."""
    user = obj.get("user") or {}
    return user.get("login") or obj.get("original_author") or "unknown"


def render_markdown(repo: str, issue: dict, comments: list[dict], rendered_at: str) -> str:
    """Render one issue (header + disclaimer + body + every comment) to markdown.

    The header carries number, repo, state, rendered-at (this render's timestamp
    plus the source issue's updated_at), title, labels, and author - the fields a
    grep hit needs to judge relevance - then the index disclaimer pointing back at
    the live `issue view` verb, then the body and the full comment thread."""
    owner, name = _split_repo(repo)
    num = issue["number"]
    state = issue.get("state", "unknown")
    title = (issue.get("title") or "").strip() or "(no title)"
    labels = _label_names(issue)
    author = _user_login(issue)
    updated = issue.get("updated_at") or "unknown"
    html_url = issue.get("html_url") or ""

    lines = [
        f"# {repo}#{num} - {title}",
        "",
        "> **Discovery index, not source of truth.** Point-in-time render for offline",
        f"> grep. Confirm live state via `ward ops forgejo issue view {owner} {name} {num}`.",
        "",
        f"- **repo:** {repo}",
        f"- **issue:** {num}",
        f"- **state:** {state}",
        f"- **title:** {title}",
        f"- **author:** {author}",
        f"- **labels:** {', '.join(labels) if labels else '(none)'}",
        f"- **source-updated-at:** {updated}",
        f"- **rendered-at:** {rendered_at}",
    ]
    if html_url:
        lines.append(f"- **url:** {html_url}")
    lines += ["", "## Body", "", (issue.get("body") or "").strip() or "_(empty)_", ""]

    if comments:
        lines += ["## Comments", ""]
        for i, c in enumerate(comments, 1):
            who = _user_login(c)
            when = c.get("created_at") or "unknown"
            lines += [f"### Comment {i} - {who} - {when}", "",
                      (c.get("body") or "").strip() or "_(empty)_", ""]
    else:
        lines += ["## Comments", "", "_(no comments)_", ""]

    return "\n".join(lines).rstrip() + "\n"


def load_manifest(mirror_dir: Path) -> dict:
    """Read manifest.json (issue-ref -> render metadata), or {} on first run."""
    path = mirror_dir / MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_manifest(mirror_dir: Path, manifest: dict) -> None:
    """Write manifest.json sorted for a stable, reviewable diff between runs."""
    path = mirror_dir / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def render_repo(repo: str, mirror_dir: Path, manifest: dict, rendered_at: str,
                force: bool) -> dict:
    """Render every issue of one source repo into the mirror dir, updating the
    manifest in place. Skips an issue whose updated_at is unchanged since the last
    run (the incremental fast path: no comment fetch). When a re-render lands at a
    new path (the title was edited), the stale file is removed. Returns per-repo
    counts {rendered, skipped, removed}."""
    counts = {"rendered": 0, "skipped": 0, "removed": 0}
    issues = list_issues(repo)
    for issue in issues:
        ref = f"{repo}#{issue['number']}"
        relpath = issue_relpath(repo, issue)
        updated = issue.get("updated_at") or ""
        prior = manifest.get(ref)
        unchanged = (prior and prior.get("updated_at") == updated
                     and (mirror_dir / relpath).exists())
        if unchanged and not force:
            counts["skipped"] += 1
            continue

        comments = list_comments(repo, issue["number"]) if issue.get("comments") else []
        body = render_markdown(repo, issue, comments, rendered_at)
        dest = mirror_dir / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body)

        if prior and prior.get("path") and prior["path"] != relpath:
            stale = mirror_dir / prior["path"]
            if stale.exists():
                stale.unlink()
                counts["removed"] += 1

        manifest[ref] = {"updated_at": updated, "state": issue.get("state"),
                         "path": relpath, "rendered_at": rendered_at}
        counts["rendered"] += 1
    return counts


def run_trufflehog(mirror_dir: Path) -> None:
    """Secret-scan the rendered corpus before the caller pushes, the privacy
    backstop the private mirror requires (the corpus carries coilysiren/inbox).
    Fail-closed: a missing binary or a finding raises, so an unscanned or leaky
    corpus never reaches the push. Mirrors the trufflehog pre-commit hook's flags
    (offline, no API verification) but scans the filesystem, not a git range."""
    cmd = ["trufflehog", "filesystem", str(mirror_dir),
           "--no-verification", "--no-update", "--fail"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError as e:
        raise RuntimeError(
            "trufflehog not on PATH; cannot secret-scan the corpus before push. "
            "Install it (agentic-os Brewfile) or pass --no-scan for a local dry run."
        ) from e
    if proc.returncode != 0:
        raise RuntimeError("trufflehog flagged a secret in the rendered corpus "
                           f"(exit {proc.returncode}); refusing to proceed:\n"
                           + (proc.stdout or proc.stderr or "").strip())


def _utc_now_iso() -> str:
    """This render's wall-clock stamp, RFC3339 UTC. Isolated for test override."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render the Forgejo issue corpus to a private git-mirrored "
                    "discovery index (one markdown file per issue).")
    ap.add_argument("--mirror-dir", required=True, type=Path,
                    help="path to the (cloned) private mirror repo to render into")
    ap.add_argument("--repos-file", type=Path, default=DEFAULT_REPOS_FILE,
                    help="source-repo list (default: scripts/issue-corpus-repos.txt)")
    ap.add_argument("--repo", action="append", dest="repos",
                    help="render only this owner/name (repeatable); default: all in the file")
    ap.add_argument("--force", action="store_true",
                    help="re-render every issue, ignoring the unchanged-since fast path")
    ap.add_argument("--no-scan", dest="scan", action="store_false",
                    help="skip the trufflehog secret scan (local dry runs only)")
    args = ap.parse_args(argv)

    mirror_dir = args.mirror_dir
    if not mirror_dir.is_dir():
        ap.error(f"--mirror-dir {mirror_dir} is not a directory")

    repos = args.repos or load_repos(args.repos_file)
    if not repos:
        ap.error("no source repos to render")

    rendered_at = _utc_now_iso()
    manifest = load_manifest(mirror_dir)
    totals = {"rendered": 0, "skipped": 0, "removed": 0}
    for repo in repos:
        print(f"render-issue-corpus: {repo} ...", file=sys.stderr)
        try:
            counts = render_repo(repo, mirror_dir, manifest, rendered_at, args.force)
        except WardForgejoError as e:
            print(f"  {repo}: FAILED to list/render ({e}); skipping repo", file=sys.stderr)
            continue
        for k in totals:
            totals[k] += counts[k]
        print(f"  {repo}: {counts['rendered']} rendered, {counts['skipped']} "
              f"unchanged, {counts['removed']} relocated", file=sys.stderr)

    save_manifest(mirror_dir, manifest)

    if args.scan:
        print("render-issue-corpus: trufflehog scanning the corpus ...", file=sys.stderr)
        run_trufflehog(mirror_dir)

    print(f"\nrender-issue-corpus: {totals['rendered']} rendered, "
          f"{totals['skipped']} unchanged, {totals['removed']} relocated "
          f"across {len(repos)} repo(s) -> {mirror_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
