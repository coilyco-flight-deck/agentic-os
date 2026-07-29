"""Tests for the in-process Forgejo registry read-token remint."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "remint-registry-read-token.py"
SPEC = importlib.util.spec_from_file_location("remint_registry_read_token", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
with mock.patch.dict(sys.modules, {"boto3": mock.Mock()}):
    SPEC.loader.exec_module(MODULE)


def test_dry_run_performs_no_external_calls(capsys) -> None:
    with (
        mock.patch.object(sys, "argv", [str(SCRIPT), "--dry-run"]),
        mock.patch.object(MODULE.boto3, "client") as client,
    ):
        assert MODULE.main() == 0

    client.assert_not_called()
    assert "read:package" in capsys.readouterr().out


def test_remint_replaces_fixed_token_verifies_and_stashes(monkeypatch) -> None:
    calls = []

    class FakeSsm:
        def get_parameter(self, **kwargs):
            calls.append(("ssm-get", kwargs))
            return {"Parameter": {"Value": "bot-password"}}

        def put_parameter(self, **kwargs):
            calls.append(("ssm-put", kwargs))

    def fake_api(method, path, auth, body=None):
        calls.append((method, path, auth, body))
        if method == "GET":
            return 200, [{"id": 7, "name": MODULE.TOKEN_NAME}]
        if method == "POST":
            return 201, {"sha1": "new-read-token"}
        return 204, None

    monkeypatch.setattr(MODULE.boto3, "client", lambda _service: FakeSsm())
    monkeypatch.setattr(MODULE, "api", fake_api)
    monkeypatch.setattr(MODULE, "verify_registry", lambda token: calls.append(("verify", token)))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])

    assert MODULE.main() == 0
    assert ("verify", "new-read-token") in calls
    assert (
        "ssm-put",
        {
            "Name": MODULE.TARGET_PARAM,
            "Value": "new-read-token",
            "Type": "SecureString",
            "Overwrite": True,
        },
    ) in calls
