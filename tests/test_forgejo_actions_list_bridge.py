from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / ".ward" / "forgejo-actions-list.sh"


@pytest.mark.parametrize(
    ("kind", "tail"),
    [
        ("runs", "/actions/runs?page=1&limit=1"),
        ("tasks", "/actions/tasks?page=3&limit=1"),
    ],
)
def test_actions_list_bridge_defaults_page_and_honours_override(
    tmp_path: Path, kind: str, tail: str
) -> None:
    capture = tmp_path / "curl-args.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$@\" >\"${CAPTURE_FILE}\"\n"
        "printf '[]'\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "CAPTURE_FILE": str(capture),
            "FORGEJO_TOKEN": "token",
            "FORGEJO_BASE_URL": "https://forgejo.example",
            "PATH": f"{fake_bin}:{env['PATH']}",
        }
    )

    args = ["bash", str(SCRIPT), kind, "coilyco-flight-deck", "infrastructure", "--limit", "1"]
    if kind == "tasks":
        args += ["--page", "3"]

    proc = subprocess.run(args, env=env, check=True, capture_output=True, text=True)
    assert proc.stdout == "[]"
    assert proc.stderr == ""

    got = capture.read_text(encoding="utf-8")
    assert tail in got
    assert "Authorization: token token" in got
    assert "Accept: application/json" in got
