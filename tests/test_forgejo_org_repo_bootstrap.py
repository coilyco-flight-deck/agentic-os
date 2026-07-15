from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import scripts.forgejo_org_repo_bootstrap as bootstrap


class _Response:
    def __init__(self, status: int, payload: dict[str, object]) -> None:
        self._status = status
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def getcode(self) -> int:
        return self._status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_bootstrap_creates_then_reconciles_repo(monkeypatch, capsys) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_urlopen(req, timeout=30):  # noqa: ARG001
        payload = None
        if req.data is not None:
            payload = json.loads(req.data.decode("utf-8"))
        requests.append((req.method, req.full_url, payload))
        if req.method == "GET":
            raise HTTPError(
                req.full_url,
                404,
                "Not Found",
                hdrs=None,
                fp=io.BytesIO(b'{"message":"repo missing"}'),
            )
        if req.method == "POST":
            return _Response(
                201,
                {
                    "html_url": "https://forgejo.example/coilyco-bridge/.github",
                    "private": False,
                },
            )
        if req.method == "PATCH":
            return _Response(
                200,
                {
                    "html_url": "https://forgejo.example/coilyco-bridge/.github",
                    "private": False,
                },
            )
        raise AssertionError(f"unexpected method: {req.method}")

    monkeypatch.setenv("FORGEJO_TOKEN", "admin-token")
    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", fake_urlopen)

    exit_code = bootstrap.main(
        [
            "coilyco-bridge",
            ".github",
            "--description",
            "Profile README for coilyco-bridge",
            "--public",
        ]
    )

    assert exit_code == 0
    assert requests == [
        ("GET", "https://forgejo.coilysiren.me/api/v1/repos/coilyco-bridge/.github", None),
        (
            "POST",
            "https://forgejo.coilysiren.me/api/v1/orgs/coilyco-bridge/repos",
            {
                "name": ".github",
                "description": "Profile README for coilyco-bridge",
                "private": False,
                "default_branch": "main",
                "auto_init": False,
            },
        ),
        (
            "PATCH",
            "https://forgejo.coilysiren.me/api/v1/repos/coilyco-bridge/.github",
            {
                "description": "Profile README for coilyco-bridge",
                "private": False,
                "default_branch": "main",
            },
        ),
    ]
    assert capsys.readouterr().out.strip().startswith("created coilyco-bridge/.github")


def test_bootstrap_updates_existing_repo(monkeypatch) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_urlopen(req, timeout=30):  # noqa: ARG001
        payload = None
        if req.data is not None:
            payload = json.loads(req.data.decode("utf-8"))
        requests.append((req.method, req.full_url, payload))
        if req.method == "GET":
            return _Response(
                200,
                {
                    "html_url": "https://forgejo.example/coilyco-flight-deck/.github",
                    "private": True,
                },
            )
        if req.method == "PATCH":
            return _Response(
                200,
                {
                    "html_url": "https://forgejo.example/coilyco-flight-deck/.github",
                    "private": False,
                },
            )
        raise AssertionError(f"unexpected method: {req.method}")

    monkeypatch.setenv("FORGEJO_TOKEN", "admin-token")
    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", fake_urlopen)

    exit_code = bootstrap.main(
        [
            "coilyco-flight-deck",
            ".github",
            "--description",
            "Profile README for coilyco-flight-deck",
            "--public",
        ]
    )

    assert exit_code == 0
    assert [method for method, _, _ in requests] == ["GET", "PATCH"]
