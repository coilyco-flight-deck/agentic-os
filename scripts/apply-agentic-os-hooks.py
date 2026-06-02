#!/usr/bin/env python3
"""Roll out the coilysiren/agentic-os pre-commit hook suite to every catalog repo.

Inserts (or refreshes) a single managed `repo: <forgejo>/coilyco-flight-deck/agentic-os`
block in each consumer's `.pre-commit-config.yaml`. Block is delimited by marker
comments so re-runs are idempotent. Replaces the older per-hook stamping
rollouts that lived in coilysiren/agentic-os-kai/scripts/.

For each repo checked out under ~/projects/coilysiren/<name> (any owner -
coilysiren, coilyco-bridge, coilyco-flight-deck, post org-migration):
  1. Read or create `.pre-commit-config.yaml`.
  2. Strip legacy stamped `repo: local` blocks for the hooks now centralized
     here (catalog-block-present, catalog-doc-size, catalog-trifecta,
     documentation-layout, code-comments, validate-skills, dead-cross-links,
     closes-issue, skill-discipline).
  3. Insert/refresh the managed agentic-os block with the full hook set.
  4. Run `pre-commit install --hook-type pre-commit --hook-type commit-msg
     --hook-type prepare-commit-msg`.

Pin a release tag with `--rev`. Default tracks the latest known release.

Usage:
    python3 scripts/apply-agentic-os-hooks.py             # apply to all
    python3 scripts/apply-agentic-os-hooks.py --dry-run   # show plan
    python3 scripts/apply-agentic-os-hooks.py --repo X    # one repo
    python3 scripts/apply-agentic-os-hooks.py --skip X Y  # exclude
    python3 scripts/apply-agentic-os-hooks.py --rev v0.2.0  # pin a different tag

A repo carrying a .agentic-os-ignore file at its root is skipped entirely
(declarative, repo-owned opt-out). Use --skip for one-off exclusions, the
marker for durable ones. Honored fail-closed: presence skips, no override.

Stdlib only. Drives off the on-disk checkout set (every git working tree
under ~/projects/coilysiren), so it is owner-agnostic: the org migration of
active repos to coilyco-bridge / coilyco-flight-deck no longer strands them
the way a single hardcoded GitHub owner did. See coilysiren/agentic-os-kai#553.

See coilysiren/agentic-os#59 for the convention design.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REV = "v0.12.0"
SIBLINGS_ROOT = Path.home() / "projects" / "coilysiren"

# A repo carrying this marker at its root opts out of all baseline
# normalization (hook block, host-tracker hook wiring). Honored fail-closed:
# presence skips, no override flag. Remove the file to re-enroll.
IGNORE_MARKER = ".agentic-os-ignore"

BEGIN_MARKER = "# BEGIN managed by agentic-os/scripts/apply-agentic-os-hooks.py"
END_MARKER = "# END managed by agentic-os/scripts/apply-agentic-os-hooks.py"

# Canonical source for the shipped hook suite. Points at Forgejo, not the
# GitHub mirror: Forgejo is the consumable source of truth, the public repo
# is publicly readable so pre-commit clones it anonymously on every host, and
# release tags land here first (the GitHub mirror is visibility-only and may
# lag or never carry a given tag). See coilyco-flight-deck/agentic-os#129.
AGENTIC_OS_REPO_URL = "https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os"

# Legacy managed-block markers from the prior per-hook stamping rollouts.
# Strip these when present so consumers end up with one upstream-ref block.
LEGACY_BLOCK_MARKERS = [
    ("# BEGIN managed by agentic-os-kai/scripts/apply-catalog-block-hook.py",
     "# END managed by agentic-os-kai/scripts/apply-catalog-block-hook.py"),
    ("# BEGIN managed by agentic-os-kai/scripts/apply-catalog-doc-size-hook.py",
     "# END managed by agentic-os-kai/scripts/apply-catalog-doc-size-hook.py"),
    ("# BEGIN managed by agentic-os-kai/scripts/apply-catalog-trifecta-hook.py",
     "# END managed by agentic-os-kai/scripts/apply-catalog-trifecta-hook.py"),
    ("# BEGIN managed by agentic-os-kai/scripts/apply-skill-discipline-hooks.py",
     "# END managed by agentic-os-kai/scripts/apply-skill-discipline-hooks.py"),
    ("# BEGIN managed by agentic-os-kai/scripts/apply-commit-msg-hook.py",
     "# END managed by agentic-os-kai/scripts/apply-commit-msg-hook.py"),
]

# Legacy stamped scripts to delete; validators ship from the agentic_os package now.
LEGACY_STAMPED_SCRIPTS = [
    "scripts/check-catalog-block.py",
    "scripts/check-catalog-doc-size.py",
    "scripts/check-catalog-trifecta.py",
    "scripts/check-commit-closes-issue.py",
    "scripts/check-dead-links.py",
    "scripts/validate-skills.py",
]

# Default hook IDs to enable per repo. Consumers can hand-edit later.
DEFAULT_HOOK_IDS = [
    "catalog-doc-size",
    "catalog-trifecta",
    "documentation-layout",
    "context-load-points",
    "code-comments",
    "catalog-block-present",
    "validate-skills",
    "dead-cross-links",
    "repo-pointer-skills",
    "closes-issue",
    "conventional-commit",
    "trufflehog",
]

# Per-repo hook opt-outs. eco-* repos skip code-comments (Unity / C# conventions).
PER_REPO_HOOK_SKIPS: dict[str, set[str]] = {
    "infrastructure": {"code-comments"},
}
ECO_HOOK_SKIPS = {"code-comments"}


def hook_ids_for(repo: str) -> list[str]:
    skips: set[str] = set(PER_REPO_HOOK_SKIPS.get(repo, set()))
    if repo.startswith("eco"):
        skips |= ECO_HOOK_SKIPS
    return [h for h in DEFAULT_HOOK_IDS if h not in skips]


def managed_block(rev: str, hook_ids: list[str] | None = None) -> str:
    ids = hook_ids if hook_ids is not None else DEFAULT_HOOK_IDS
    hook_lines = "\n".join(f"      - id: {h}" for h in ids)
    return f"""\
  {BEGIN_MARKER}
  - repo: {AGENTIC_OS_REPO_URL}
    rev: {rev}
    hooks:
{hook_lines}
  {END_MARKER}
"""


def empty_config_template(rev: str, hook_ids: list[str] | None = None) -> str:
    return f"""\
repos:
{managed_block(rev, hook_ids)}"""


def list_local_repos() -> list[str]:
    """Every git working tree checked out under ~/projects/coilysiren.

    Owner-agnostic by design: this is a local-fleet tool (it runs
    `pre-commit install` inside each checkout), so the on-disk set is both
    the authoritative candidate list and the only set it can act on. Driving
    off disk instead of `gh repo list <single-owner>` means the org migration
    (coilyco-bridge / coilyco-flight-deck) can't silently strand repos.
    apply_to_repo() still filters the source repo, the opt-out marker, and
    non-git dirs; --skip handles one-off exclusions.
    """
    if not SIBLINGS_ROOT.is_dir():
        return []
    return sorted(
        p.name
        for p in SIBLINGS_ROOT.iterdir()
        if p.is_dir() and (p / ".git").exists()
    )


def strip_legacy_blocks(text: str) -> tuple[str, int]:
    """Drop every legacy per-hook managed block. Returns (new_text, n_removed)."""
    removed = 0
    for begin, end in LEGACY_BLOCK_MARKERS:
        pattern = re.compile(
            re.escape(begin) + r".*?" + re.escape(end) + r"\n?",
            re.DOTALL,
        )
        new_text, n = pattern.subn("", text)
        if n:
            removed += n
            text = new_text
    return text, removed


def upsert_managed_block(
    config_path: Path, rev: str, hook_ids: list[str] | None = None
) -> tuple[str, int]:
    """Insert or refresh the agentic-os upstream-ref block.

    Returns (status, legacy_blocks_removed).
    """
    if not config_path.exists():
        config_path.write_text(empty_config_template(rev, hook_ids))
        return "created", 0

    text = config_path.read_text()
    text, legacy_removed = strip_legacy_blocks(text)

    block = managed_block(rev, hook_ids)
    if BEGIN_MARKER in text and END_MARKER in text:
        before, _, rest = text.partition(BEGIN_MARKER)
        _, _, after = rest.partition(END_MARKER)
        before = before.rstrip()
        after = after.lstrip("\n")
        new_text = before + "\n\n" + block + (after if after else "")
        if new_text == config_path.read_text():
            return "unchanged", legacy_removed
        config_path.write_text(new_text)
        return "updated", legacy_removed

    if not text.endswith("\n"):
        text += "\n"
    text += block
    config_path.write_text(text)
    return "appended", legacy_removed


def drop_legacy_stamped_scripts(repo_dir: Path) -> list[str]:
    """Delete stamped check-*.py copies from the consumer's scripts/ dir."""
    dropped: list[str] = []
    for rel in LEGACY_STAMPED_SCRIPTS:
        p = repo_dir / rel
        if p.is_file():
            p.unlink()
            dropped.append(rel)
    return dropped


def install_pre_commit_hooks(repo_dir: Path) -> str:
    result = subprocess.run(
        [
            "pre-commit", "install",
            "--hook-type", "pre-commit",
            "--hook-type", "commit-msg",
            "--hook-type", "prepare-commit-msg",
        ],
        cwd=repo_dir, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return f"install-failed: {result.stderr.strip()}"
    return "installed"


def apply_to_repo(repo: str, rev: str, dry_run: bool) -> tuple[str, str]:
    if repo == "agentic-os":
        # Source repo dogfoods via repo: local; upstream-ref would duplicate IDs.
        return ("skipped", "self (source repo)")
    repo_dir = SIBLINGS_ROOT / repo
    if not repo_dir.is_dir():
        return ("skipped", "not checked out locally")
    if not (repo_dir / ".git").exists():
        return ("skipped", "not a git working tree")
    if (repo_dir / IGNORE_MARKER).exists():
        return ("skipped", f"opted out ({IGNORE_MARKER})")

    config_path = repo_dir / ".pre-commit-config.yaml"
    hook_ids = hook_ids_for(repo)

    if dry_run:
        if not config_path.exists():
            yaml_status = "would create config"
        else:
            text = config_path.read_text()
            n_legacy = sum(
                1 for begin, _ in LEGACY_BLOCK_MARKERS if begin in text
            )
            has_managed = BEGIN_MARKER in text
            parts = []
            if has_managed:
                parts.append("refresh agentic-os block")
            else:
                parts.append("insert agentic-os block")
            if n_legacy:
                parts.append(f"strip {n_legacy} legacy block(s)")
            n_stamped = sum(
                1 for rel in LEGACY_STAMPED_SCRIPTS if (repo_dir / rel).is_file()
            )
            if n_stamped:
                parts.append(f"drop {n_stamped} stamped script(s)")
            yaml_status = ", ".join(parts)
        return ("dryrun", yaml_status)

    yaml_status, legacy_removed = upsert_managed_block(config_path, rev, hook_ids)
    dropped = drop_legacy_stamped_scripts(repo_dir)
    install_status = install_pre_commit_hooks(repo_dir)
    parts = [yaml_status]
    if legacy_removed:
        parts.append(f"legacy-blocks={legacy_removed}")
    if dropped:
        parts.append(f"dropped={len(dropped)}")
    parts.append(install_status)
    return ("applied", ", ".join(parts))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", help="apply to a single repo by name")
    ap.add_argument("--skip", nargs="*", default=[])
    ap.add_argument(
        "--rev",
        default=DEFAULT_REV,
        help=f"agentic-os release tag to pin (default: {DEFAULT_REV})",
    )
    args = ap.parse_args(argv)

    if args.repo:
        repos = [args.repo]
    else:
        repos = [r for r in list_local_repos() if r not in args.skip]

    print(
        f"Rolling out agentic-os pre-commit suite "
        f"(rev={args.rev}) to {len(repos)} repo(s)"
    )
    if args.dry_run:
        print("(dry run)")
    print()

    counts: dict[str, int] = {}
    for repo in repos:
        action, detail = apply_to_repo(repo, args.rev, args.dry_run)
        counts[action] = counts.get(action, 0) + 1
        print(f"  {repo:24} {action:8} {detail}")

    print()
    print("Summary:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
