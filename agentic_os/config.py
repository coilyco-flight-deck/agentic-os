"""Consumer-side exclude loading for tree-walking hooks.

Hooks in this package use `always_run: true` + `pass_filenames: false` and
do their own filesystem walks, which means pre-commit's framework-level
`exclude:` directive is bypassed. This module reads a per-repo config so
consumers can opt specific paths out of specific hooks.

Config search order:
    1. pyproject.toml at REPO_ROOT, key path [tool.agentic-os.<hook_id>]
    2. .agentic-os.toml at REPO_ROOT, key path [<hook_id>]

Schema per hook:
    excludes = ["src/pages/", "src/pages/**", "*.guardfile.md"]

Path semantics (gitignore-style globs over repo-relative POSIX paths):
    "dir/"        directory prefix - excludes everything under dir/
    "dir/**"      same, spelled as a recursive glob
    "*"           any run of characters except "/"
    "**"          any run of characters including "/" (crosses dirs)
    "?"           a single character except "/"
A pattern containing a "/" is anchored to the repo root ("docs/*.md"
matches docs/x.md but not docs/sub/x.md). A pattern with no "/" matches
the file's basename at any depth, so one wildcard covers a generated file
wherever it lands - ward's specverb guardfiles, emitted both in docs/ and
beside the .kdl under cmd/ward-kdl/, collapse to a single
"ward-kdl.*.guardfile.md" instead of a line per generator
(coilyco-flight-deck/agentic-os#243). Patterns and paths use forward
slashes on every platform.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path.cwd()


# Workspace enumeration: one shared walk of ~/projects/<org>/* git trees, so
# cross-repo tooling spans every org dir. See coilysiren/agentic-os-kai#560.


def projects_root(root: Path | None = None) -> Path:
    """Root holding the per-org checkout dirs. Override with $PROJECTS_ROOT.

    ~/projects now holds per-org checkout dirs (coilysiren/, coilyco-bridge/,
    coilyco-flight-deck/), each a plain dir of git working trees rather than a
    repo itself, mirroring the GitHub org migration. This defaults to that
    ~/projects (also the global default cwd). An explicit `root` argument wins
    over the env var (used by tests).
    """
    if root is not None:
        return root
    env = os.environ.get("PROJECTS_ROOT")
    if env:
        return Path(env).expanduser()
    return Path.home() / "projects"


def iter_workspace_repos(root: Path | None = None) -> list[Path]:
    """Every git working tree in the workspace, owner-agnostic.

    Walks each immediate child of `projects_root()`:
      * a child that is itself a git working tree (carries .git) is yielded
        directly - this is the single-org-root layout (root already points at
        an org dir like ~/projects/coilysiren).
      * otherwise the child is a dir-of-checkouts (an org dir like coilysiren/,
        coilyco-bridge/, coilyco-flight-deck/) and its own git-working-tree
        children are yielded.

    Handling both shapes means the default ~/projects root covers every org
    dir, while a $PROJECTS_ROOT pointed straight at one org dir still works (it
    mirrors the old single-root behaviour). Hidden dirs (.dispatch-worktrees
    and other scaffolding) are skipped at both levels. Returns repo directory
    Paths sorted by (org dir, repo name).
    """
    base = projects_root(root)
    if not base.is_dir():
        return []
    repos: list[Path] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / ".git").exists():
            repos.append(child)
            continue
        for grandchild in sorted(child.iterdir()):
            if (
                grandchild.is_dir()
                and not grandchild.name.startswith(".")
                and (grandchild / ".git").exists()
            ):
                repos.append(grandchild)
    return repos


def _load_hook_section(hook_id: str, repo_root: Path | None = None) -> dict:
    root = repo_root or REPO_ROOT
    candidates = [
        (root / "pyproject.toml", ("tool", "agentic-os", hook_id)),
        (root / ".agentic-os.toml", (hook_id,)),
    ]
    for path, key_path in candidates:
        if not path.is_file():
            continue
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except (tomllib.TOMLDecodeError, OSError):
            continue
        section: object = data
        for key in key_path:
            if not isinstance(section, dict) or key not in section:
                section = None
                break
            section = section[key]
        if isinstance(section, dict):
            return section
    return {}


def load_str_list(
    hook_id: str, key: str, repo_root: Path | None = None
) -> list[str]:
    """Return a list-of-strings option for a hook, or [] if unset/non-list."""
    section = _load_hook_section(hook_id, repo_root)
    value = section.get(key)
    if isinstance(value, list):
        return [str(p) for p in value if isinstance(p, str)]
    return []


def load_excludes(hook_id: str, repo_root: Path | None = None) -> list[str]:
    """Return exclude patterns for a hook, or [] if none configured."""
    return load_str_list(hook_id, "excludes", repo_root)


def get_str_option(
    hook_id: str, key: str, default: str, repo_root: Path | None = None
) -> str:
    """Return a string option for a hook, or `default` if unset or non-str."""
    section = _load_hook_section(hook_id, repo_root)
    value = section.get(key, default)
    return value if isinstance(value, str) else default


def is_enabled(hook_id: str, repo_root: Path | None = None) -> bool:
    """Return False only if `enabled = false` is set in the hook's config."""
    section = _load_hook_section(hook_id, repo_root)
    value = section.get("enabled", True)
    return bool(value)


def has_hook_config(hook_id: str, repo_root: Path | None = None) -> bool:
    """Return True if a `[tool.agentic-os.<hook_id>]` section is present.

    The opt-in signal for hooks that default off and only enforce once a repo
    declares them (e.g. seed-skills, enabled fleet-wide by Ansible).
    """
    return bool(_load_hook_section(hook_id, repo_root))


def get_int_option(
    hook_id: str, key: str, default: int, repo_root: Path | None = None
) -> int:
    """Return an int option for a hook, or `default` if unset or non-int.

    `bool` is rejected (it is an int subclass but never a meaningful cap).
    """
    section = _load_hook_section(hook_id, repo_root)
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def get_bool_option(
    hook_id: str, key: str, default: bool, repo_root: Path | None = None
) -> bool:
    """Return a bool option for a hook, or `default` if unset or non-bool."""
    section = _load_hook_section(hook_id, repo_root)
    value = section.get(key, default)
    if not isinstance(value, bool):
        return default
    return value


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a gitignore-style glob to a regex.

    Semantics:
        * matches any chars except /
        ** matches any chars including /
        ? matches a single char except /
        Other characters are matched literally.
    """
    out: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def is_excluded(rel_path: Path | str, patterns: Iterable[str]) -> bool:
    """Match a repo-relative path against the exclude pattern list.

    A pattern containing a "/" is anchored to the repo root; a slash-less
    pattern matches the path's basename at any depth (the gitignore
    convention), so one wildcard covers a generated file wherever it is
    emitted. See the module docstring for the full glob grammar.
    """
    s = str(PurePosixPath(str(rel_path).replace("\\", "/")))
    basename = s.rsplit("/", 1)[-1]
    for raw in patterns:
        pattern = raw.replace("\\", "/")
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if s == prefix or s.startswith(prefix + "/"):
                return True
            continue
        if pattern.endswith("/"):
            if s.startswith(pattern):
                return True
            continue
        target = s if "/" in pattern else basename
        if _glob_to_regex(pattern).match(target):
            return True
    return False
