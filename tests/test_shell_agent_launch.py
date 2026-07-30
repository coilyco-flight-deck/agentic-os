"""Behavioral coverage for shared-shell agent CLI launch functions."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_SH = REPO_ROOT / "shell" / "common.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_function(
    tmp_path: Path,
    function: str,
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
            "_SIREN_SHELL_ENV": "1",
        }
    )
    command = " ".join(
        [
            f"source {shlex.quote(str(COMMON_SH))}",
            "&&",
            function,
            *(shlex.quote(arg) for arg in args),
        ]
    )
    return subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-c", command],
        cwd=cwd or REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("harness", ["claude", "codex", "goose", "opencode"])
def test_agent_cli_launches_through_acompose(
    tmp_path: Path,
    harness: str,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "<%s>\\n" "$@"\n',
    )

    result = _run_function(tmp_path, harness, "one", "two words")

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "<compose>\n<-->\n<%s>\n<one>\n<two words>\n" % harness
    )


def test_agent_cli_falls_back_when_acompose_is_unavailable(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "codex",
        '#!/bin/sh\nprintf "real-codex <%s>\\n" "$@"\n',
    )

    result = _run_function(tmp_path, "codex", "one", "two words")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "real-codex <one>\nreal-codex <two words>\n"


def test_agent_cli_launches_outside_repo(tmp_path: Path) -> None:
    outside_repo = tmp_path / "outside"
    outside_repo.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "<%s>\\n" "$@"\n',
    )

    result = _run_function(
        tmp_path,
        "goose",
        "outside",
        cwd=outside_repo,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "<compose>\n<-->\n<goose>\n<outside>\n"


def test_agent_cli_uses_native_shadow_when_supported(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "aos",
        """#!/bin/sh
if [ "$1" = "_native-shadow" ] && [ "$2" = "--probe" ]; then exit 0; fi
printf "<%s>\\n" "$@"
""",
    )
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "unexpected agent-compose execution\\n"\nexit 9\n',
    )

    result = _run_function(tmp_path, "codex", "one", "two words")

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "<_native-shadow>\n"
        "<--harness>\n"
        "<codex>\n"
        "<-->\n"
        "<agent-compose>\n"
        "<compose>\n"
        "<-->\n"
        "<codex>\n"
        "<one>\n"
        "<two words>\n"
    )


def test_agent_cli_ignores_old_aos_without_native_shadow(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "aos",
        '#!/bin/sh\nexit 1\n',
    )
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "<%s>\\n" "$@"\n',
    )

    result = _run_function(tmp_path, "claude", "one")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "<compose>\n<-->\n<claude>\n<one>\n"


def test_explicit_non_director_role_uses_native_shadow(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "aos",
        """#!/bin/sh
if [ "$1" = "_native-shadow" ] && [ "$2" = "--probe" ]; then exit 0; fi
printf "<%s>\\n" "$@"
""",
    )
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "unexpected agent-compose execution\\n"\nexit 9\n',
    )

    result = _run_function(
        tmp_path,
        "acompose",
        "designer",
        "codex",
        "--model",
        "gpt",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "<_native-shadow>\n"
        "<--harness>\n"
        "<codex>\n"
        "<--assigned-role>\n"
        "<-->\n"
        "<agent-compose>\n"
        "<launch>\n"
        "<designer>\n"
        "<codex>\n"
        "<--model>\n"
        "<gpt>\n"
    )


def test_explicit_director_role_uses_warded_aos(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "aos",
        '#!/bin/sh\nprintf "<%s>\\n" "$@"\n',
    )
    _write_executable(bin_dir / "ward", "#!/bin/sh\nexit 0\n")
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "unexpected agent-compose execution\\n"\nexit 9\n',
    )

    result = _run_function(
        tmp_path,
        "acompose",
        "director",
        "codex",
        "--repo",
        "owner/repo",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "<--agent>\n"
        "<codex>\n"
        "<--role>\n"
        "<director>\n"
        "<--warded>\n"
        "<--composed>\n"
        "<--guarded>\n"
        "<-->\n"
        "<--repo>\n"
        "<owner/repo>\n"
    )


def test_explicit_acompose_role_runs_without_native_shadow(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "agent-compose",
        '#!/bin/sh\nprintf "<%s>\\n" "$@"\n',
    )

    result = _run_function(tmp_path, "acompose", "qa", "goose", "run")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "<launch>\n<qa>\n<goose>\n<run>\n"
