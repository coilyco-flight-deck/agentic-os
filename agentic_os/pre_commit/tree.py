"""One tree walk for the hooks that each carried their own.

Thirteen hooks kept a private `SKIP_DIR_NAMES` and a private `rglob`, and the
copies had already drifted into five different sets. That is how a gitignored
bake stayed visible to eleven hooks after the two it actually broke were fixed
(agentic-os#1062). The skip set lives here now, and `is_repo_content` is the
single gate a walking hook asks.

Why the gate is two questions rather than one: `SKIP_DIR_NAMES` covers caches
and vendored trees that git may well carry, and `is_build_output` covers
everything git does not carry at all. Neither subsumes the other. Fail-open
behaviour comes from `is_build_output` unchanged, so a tarball or a machine
without git is walked exactly as before. See docs/build-output-is-not-content.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from agentic_os.config import is_build_output

SKIP_DIR_NAMES = frozenset(
    {
        ".claude",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".terraform",
        ".tox",
        ".venv",
        "venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "vendor",
    }
)


def should_skip(rel: Path | str) -> bool:
    """Whether a cache or vendored directory holds this path."""
    parts = Path(rel).parts if not isinstance(rel, Path) else rel.parts
    return any(part in SKIP_DIR_NAMES for part in parts)


def is_repo_content(rel: Path | str, root: Path | None = None) -> bool:
    """Whether a hook walking the repository root should read this path."""
    return not should_skip(rel) and not is_build_output(rel, root)


def carries_content(rel: Path | str, root: Path | None = None) -> bool:
    """The build-output half alone, for a hook whose walk root is skipped.

    `.claude/skills` and friends sit inside `SKIP_DIR_NAMES`, so asking
    `is_repo_content` there is not a filter on the walk but a veto on the whole
    hook: every entry answers False and the hook exits clean having read
    nothing. A hook that deliberately walks into a skip-set directory asks this
    instead, which still excludes a bake and still fails open. See
    agentic-os#1183.
    """
    return not is_build_output(rel, root)


def walk_files(root: Path, pattern: str = "*") -> Iterator[Path]:
    """Repo-relative files under `root` that the repository actually holds."""
    for path in sorted(root.rglob(pattern)):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_repo_content(rel, root):
            yield rel
