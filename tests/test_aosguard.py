"""Static contract for the independent aosguard specgen project."""

from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / ".specgen"
SOURCE = PROJECT / "aosguard"
EXPECTED_MEMBERS = {
    "actions.kdl",
    "aws.kdl",
    "forgejo.kdl",
    "kubectl.kdl",
    "tailscale.kdl",
}


@pytest.fixture(scope="module")
def aosguard_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    binary = tmp_path_factory.mktemp("aosguard") / f"aosguard{suffix}"
    subprocess.run(
        [
            "specgen",
            "--project-root",
            str(PROJECT),
            "build",
            "--out",
            str(binary),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return binary


def test_aosguard_has_one_static_binary_group() -> None:
    members = sorted(SOURCE.glob("*.kdl"))
    assert {member.name for member in members} == EXPECTED_MEMBERS

    wraps: set[str] = set()
    for member in members:
        text = member.read_text(encoding="utf-8")
        wraps.update(re.findall(r"(?m)^wrap\s+(\S+)", text))
        assert "wrap aos-agent " not in text
        assert "wrap aos-ward " not in text
        assert 'argv ".ward/' not in text

    assert wraps == {"aosguard"}


def test_aosguard_actions_use_packaged_python_modules() -> None:
    text = (SOURCE / "actions.kdl").read_text(encoding="utf-8")

    assert "exec python3" in text
    assert ".specgen/aosguard/scripts/" not in text
    for module in (
        "forgejo_actions_list",
        "forgejo_actions_logs",
        "forgejo_actions_rerun",
    ):
        assert f'"agentic_os.{module}"' in text
        assert (ROOT / "agentic_os" / f"{module}.py").is_file()


def test_aosguard_vendored_forgejo_contract_is_encoded_json() -> None:
    vendored = SOURCE / "forgejo.swagger.v1.json.gz"
    assert json.loads(gzip.decompress(vendored.read_bytes()))


def test_aosguard_forgejo_lock_is_encoded_json() -> None:
    encoded = SOURCE / "forgejo.swagger.lock.json.gz"
    legacy = SOURCE / "forgejo.swagger.lock.json"

    assert encoded.is_file()
    assert not legacy.exists()
    assert json.loads(gzip.decompress(encoded.read_bytes()))


def test_aosguard_dependency_lock_is_committed() -> None:
    lock = json.loads((PROJECT / "specverb.lock").read_text(encoding="utf-8"))
    cli_guard = lock["cliGuard"]
    assert re.fullmatch(r"v\d+\.\d+\.\d+", cli_guard)
    assert f"cli-guard {cli_guard}" in "\n".join(lock["goMod"])
    assert any(f"cli-guard {cli_guard} " in line for line in lock["goSum"])
    assert not list(SOURCE.glob("*.md"))


def test_aosguard_builds_a_native_skill_out_of_band() -> None:
    lock_script = (ROOT / "scripts" / "aosguard-lock.sh").read_text(
        encoding="utf-8"
    )
    ward = (ROOT / ".ward" / "ward.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "docker" / "dev-base" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "--skills-out dist/skills" in lock_script
    assert "--skills-out dist/skills" in ward
    assert "--skills-out /opt/agentic-os/aosguard-skill" in dockerfile


def test_native_release_wrapper_embeds_the_actions_bridge() -> None:
    wrapper = ROOT / "aosguard-release" / "main.go"
    text = wrapper.read_text(encoding="utf-8")

    assert "//go:embed payload/aosguard payload/agentic_os/*" in text
    assert "PYTHONPATH=" in text
    build = (ROOT / "scripts" / "aos-release-build.sh").read_text(encoding="utf-8")
    generate = build.index('"$specgen" --project-root "$source" gen')
    decode = build.index(
        'gzip -dc "$source/aosguard/forgejo.swagger.lock.json.gz"'
    )
    compile_binary = build.index('go build -trimpath -ldflags "-s -w -X main.Version=')
    assert generate < decode < compile_binary
    for module in (
        "forgejo_actions_list.py",
        "forgejo_actions_logs.py",
        "forgejo_actions_rerun.py",
        "forgejo_actions_web.py",
    ):
        assert f'"$repo_root/agentic_os/{module}"' in build


def test_repo_topic_replace_all_dry_run_builds_put_body(
    aosguard_binary: Path,
) -> None:
    result = subprocess.run(
        [
            str(aosguard_binary),
            "ops",
            "forgejo",
            "repo-topic",
            "replace-all",
            "coilyco-example",
            "sample",
            "--topics",
            "release-ready",
            "--topics",
            "documentation",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "method: PUT" in result.stdout
    assert "/repos/coilyco-example/sample/topics" in result.stdout
    assert "release-ready" in result.stdout
    assert "documentation" in result.stdout
    assert "Authorization: token <redacted>" in result.stdout


def test_repo_topic_replace_all_rejects_out_of_scope_owner(
    aosguard_binary: Path,
) -> None:
    result = subprocess.run(
        [
            str(aosguard_binary),
            "ops",
            "forgejo",
            "repo-topic",
            "replace-all",
            "outside-example",
            "sample",
            "--topics",
            "documentation",
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert 'owner="outside-example" is outside the allowed scope' in result.stderr
