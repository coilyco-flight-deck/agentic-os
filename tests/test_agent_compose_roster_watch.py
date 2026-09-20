from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import urllib.error
from pathlib import Path

import pytest

from agentic_os import agent_compose_roster_watch as watch


BASE = watch.DEFAULT_BASE_URL
REPO = watch.DEFAULT_REPOSITORY
ASSET = "agent-compose-linux-amd64"

# Stands in for agent-compose: it reads roles.txt from the roster root it is pointed at
# and writes the person.json the real verb writes, so no real binary is needed.
FAKE_BINARY = f"""#!{sys.executable}
import json, pathlib, sys
argv = sys.argv[1:]
src = pathlib.Path(argv[argv.index("--person-source") + 1])
out = pathlib.Path(argv[argv.index("--out") + 1])
if (src / "fail").exists():
    print("boom", file=sys.stderr)
    sys.exit(3)
roles = (src / "roles.txt").read_text().split()
(out / "person.json").write_text(json.dumps({{"role_order": roles}}))
"""

OLD_ROLES = ["platform", "sysadmin", "science", "advocate"]
NEW_ROLES = ["platform", "senior-sysadmin", "science", "advocate", "junior-sysadmin", "admin-assist"]


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def roster_tarball(roles: list[str]) -> bytes:
    data = " ".join(roles).encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as bundle:
        info = tarfile.TarInfo("roster/roles.txt")
        info.size = len(data)
        bundle.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def shipped_root(tmp_path: Path, roles: list[str]) -> Path:
    root = tmp_path / "shipped"
    root.mkdir()
    (root / "roles.txt").write_text(" ".join(roles))
    return root


def serve_release(
    monkeypatch: pytest.MonkeyPatch, tag: str, roles: list[str], *, corrupt_sums: bool = False
) -> None:
    binary = FAKE_BINARY.encode()
    tarball = roster_tarball(roles)
    binary_sum = "0" * 64 if corrupt_sums else sha(binary)
    sums = f"{binary_sum}  {ASSET}\n{sha(tarball)}  {watch.ROSTER_ASSET}\n"
    download = f"{BASE}/{REPO}/releases/download/{tag}"
    files = {
        f"{BASE}/api/v1/repos/{REPO}/releases/latest": json.dumps({"tag_name": tag}).encode(),
        f"{download}/{watch.SUMS_ASSET}": sums.encode(),
        f"{download}/{ASSET}": binary,
        f"{download}/{watch.ROSTER_ASSET}": tarball,
    }
    monkeypatch.setattr(watch, "_fetch", lambda url: files[url])
    monkeypatch.setattr(watch, "binary_asset", lambda: ASSET)


def test_compare_reports_both_directions_and_ignores_order() -> None:
    drift = watch.compare_roles(OLD_ROLES, NEW_ROLES)
    assert drift.missing == ("admin-assist", "junior-sysadmin", "senior-sysadmin")
    assert drift.dropped == ("sysadmin",)
    assert not drift.in_sync
    assert watch.compare_roles(NEW_ROLES, list(reversed(NEW_ROLES))).in_sync


def test_role_order_reads_the_roster_through_the_binary(tmp_path: Path) -> None:
    binary = tmp_path / "agent-compose"
    binary.write_text(FAKE_BINARY)
    binary.chmod(0o755)
    assert watch.role_order(binary, shipped_root(tmp_path, OLD_ROLES)) == OLD_ROLES


def test_role_order_refuses_an_empty_list_and_a_failing_binary(tmp_path: Path) -> None:
    binary = tmp_path / "agent-compose"
    binary.write_text(FAKE_BINARY)
    binary.chmod(0o755)
    with pytest.raises(watch.WatchError, match="no usable role_order"):
        watch.role_order(binary, shipped_root(tmp_path, []))
    failing = tmp_path / "failing"
    failing.mkdir()
    (failing / "fail").write_text("")
    with pytest.raises(watch.WatchError, match="boom"):
        watch.role_order(binary, failing)


def test_main_names_the_roles_the_image_lacks_and_the_one_it_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    serve_release(monkeypatch, "v2.157.0", NEW_ROLES)
    status = watch.main(["--shipped-roster", str(shipped_root(tmp_path, OLD_ROLES))])
    err = capsys.readouterr().err
    assert status == watch.EXIT_DRIFT
    assert "missing from the image: admin-assist, junior-sysadmin, senior-sysadmin" in err
    assert "baked but dropped upstream: sysadmin" in err
    assert "AGENT_COMPOSE_VERSION to 2.157.0" in err


def test_main_passes_when_the_role_sets_match_in_any_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    serve_release(monkeypatch, "v2.157.0", NEW_ROLES)
    shipped = shipped_root(tmp_path, list(reversed(NEW_ROLES)))
    assert watch.main(["--shipped-roster", str(shipped)]) == 0
    assert "matches agent-compose v2.157.0 (6 roles)" in capsys.readouterr().out


def test_a_checksum_mismatch_is_not_agreement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    serve_release(monkeypatch, "v2.157.0", NEW_ROLES, corrupt_sums=True)
    status = watch.main(["--shipped-roster", str(shipped_root(tmp_path, NEW_ROLES))])
    assert status == watch.EXIT_UNCOMPARABLE
    assert "SHA256SUMS lists" in capsys.readouterr().err


def test_a_missing_shipped_roster_is_not_agreement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = watch.main(["--shipped-roster", str(tmp_path / "absent")])
    assert status == watch.EXIT_UNCOMPARABLE
    assert "run this inside agentic-os:release" in capsys.readouterr().err


def test_an_unreachable_upstream_retries_then_names_the_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    attempts: list[str] = []

    def refuse(request: object, **_: object) -> None:
        attempts.append(getattr(request, "full_url", ""))
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(watch.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)
    status = watch.main(["--shipped-roster", str(shipped_root(tmp_path, OLD_ROLES))])
    assert status == watch.EXIT_UNCOMPARABLE
    assert len(attempts) == watch.FETCH_ATTEMPTS
    assert "releases/latest" in capsys.readouterr().err
