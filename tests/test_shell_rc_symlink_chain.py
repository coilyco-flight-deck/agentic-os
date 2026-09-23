"""A native session shadow home links each rc file to the canonical home's link, so the rc
resolves through two hops before it finds the repo. One-hop resolution read the canonical
home as the repo root and never sourced common.sh."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(os.name == "nt", reason="symlink chain needs POSIX links")


@pytest.mark.parametrize(
    ("shell", "rc", "target"),
    [("zsh", ".zshrc", "zshrc"), ("bash", ".bashrc", "bashrc")],
)
@pytest.mark.parametrize("relative_hop", [False, True])
def test_rc_behind_two_links_sources_common(
    tmp_path: Path, shell: str, rc: str, target: str, relative_hop: bool
) -> None:
    binary = shutil.which(shell)
    if binary is None:
        pytest.skip(f"{shell} not installed")
    canonical_home = tmp_path / "canonical"
    shadow_home = tmp_path / "shadow"
    canonical_home.mkdir()
    shadow_home.mkdir()
    (canonical_home / rc).symlink_to(REPO_ROOT / "shell" / target)
    hop = Path("..") / "canonical" / rc if relative_hop else canonical_home / rc
    (shadow_home / rc).symlink_to(hop)
    shims = shadow_home / ".local" / "umbra" / "shims"
    shims.mkdir(parents=True)

    env = {
        "HOME": str(shadow_home),
        "PATH": "/usr/bin:/bin",
        "AOS_NATIVE_SESSION": "test",
        "TERM": "dumb",
    }
    script = f'. "$HOME/{rc}" >/dev/null 2>&1; printf "%s\\n%s\\n" "$AOS_REPO_ROOT" "$PATH"'
    proc = subprocess.run(
        [binary, "-c", script],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    repo_root, path = proc.stdout.splitlines()[:2]
    assert Path(repo_root).resolve() == REPO_ROOT
    assert str(shims) in path.split(":")
