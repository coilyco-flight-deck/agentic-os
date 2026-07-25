from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _fake_kubectl(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    log = tmp_path / "kubectl-argv"
    if os.name == "nt":
        script = fake_bin / "kubectl.cmd"
        script.write_text(
            '@echo off\r\necho %*>>"%KUBECTL_FIXTURE_LOG%"\r\n',
            encoding="utf-8",
        )
    else:
        script = fake_bin / "kubectl"
        script.write_text(
            """#!/bin/sh
printf '%s\\n' "$*" >> "$KUBECTL_FIXTURE_LOG"
""",
            encoding="utf-8",
        )
        script.chmod(0o755)
    return fake_bin, log


def _run_observe(
    tmp_path: Path,
    *args: str,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    ward = shutil.which("ward")
    if ward is None:
        pytest.skip("ward binary is required for bundle integration coverage")
    fake_bin, log = _fake_kubectl(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "CLIGUARD_NO_SANDBOX": "1",
            "KUBECTL_FIXTURE_LOG": str(log),
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "WARD_CONFIG_REF": f"file://{REPO_ROOT / '.ward'}",
        }
    )
    result = subprocess.run(
        [ward, "ops", "observe", "--", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, log


@pytest.mark.parametrize(
    "args",
    [
        ("get", "pods"),
        ("describe", "deployments", "example"),
        ("logs", "example"),
        ("events", "--for", "pod/example"),
        ("top", "pods"),
        ("get", "componentstatuses"),
        ("rollout", "status", "deployment/example"),
    ],
)
def test_observe_allows_bounded_read_only_evidence(
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    result, log = _run_observe(tmp_path, *args)

    assert result.returncode == 0, result.stderr
    assert log.exists()


@pytest.mark.parametrize(
    "args",
    [
        ("get", "secrets"),
        ("describe", "secrets", "example"),
        ("apply", "-f", "deployment.yaml"),
        ("create", "deployment", "example"),
        ("replace", "-f", "deployment.yaml"),
        ("delete", "pod", "example"),
        ("edit", "deployment", "example"),
        ("patch", "deployment", "example"),
        ("scale", "deployment", "example", "--replicas=2"),
        ("run", "example", "--image=example"),
        ("exec", "example", "--", "sh"),
        ("attach", "example"),
        ("cp", "example:/tmp/file", "."),
        ("port-forward", "pod/example", "8080"),
        ("proxy",),
        ("debug", "example"),
        ("drain", "example"),
        ("cordon", "example"),
        ("uncordon", "example"),
        ("taint", "nodes", "example", "key=value:NoSchedule"),
        ("label", "pods", "example", "key=value"),
        ("annotate", "pods", "example", "key=value"),
        ("set", "image", "deployment/example", "app=example"),
        ("rollout", "restart", "deployment/example"),
        ("rollout", "undo", "deployment/example"),
        ("auth", "token", "example"),
        ("config", "view"),
    ],
)
def test_observe_denies_mutation_shell_and_secret_surfaces(
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    result, log = _run_observe(tmp_path, *args)

    assert result.returncode != 0
    assert not log.exists()
