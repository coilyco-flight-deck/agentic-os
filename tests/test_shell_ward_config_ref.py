"""Smoke coverage for the shell-level WARD_CONFIG_REF propagation path."""
from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_REF_PREFIX = "forgejo.coilysiren.me/coilyco-flight-deck/agentic-os@"


def test_common_shell_exports_a_current_checkout_ref_and_children_inherit(tmp_path: Path) -> None:
    env = {
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/bin",
        "AOS_REPO_ROOT": str(REPO_ROOT),
    }
    proc = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{REPO_ROOT / "shell" / "common.sh"}"; '
            'printf "%s\n" "$WARD_CONFIG_REF"; '
            'bash -c \'printf "%s" "$WARD_CONFIG_REF"\'',
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    outer, inner = proc.stdout.splitlines()
    assert outer.startswith(EXPECTED_REF_PREFIX)
    assert inner == outer


def test_shell_entrypoints_derive_the_checkout_root_from_their_own_path() -> None:
    zshrc = (REPO_ROOT / "shell" / "zshrc").read_text()
    bashrc = (REPO_ROOT / "shell" / "bashrc").read_text()

    for text in (zshrc, bashrc):
        assert "AOS_REPO_ROOT" in text
        assert "_siren_aos_root" in text
        assert "coilyco-flight-deck/agentic-os/shell/" not in text
