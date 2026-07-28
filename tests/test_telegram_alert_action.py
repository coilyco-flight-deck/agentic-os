"""Tests for the Telegram CI alert action payload and renderer."""

from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "actions" / "telegram-alert" / "telegram_alert.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("telegram_alert", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_message_includes_failure_context() -> None:
    mod = _load_script()
    message = mod.build_message(
        "coilyco-flight-deck/infrastructure",
        "lint",
        "scan",
        "refs/heads/main",
        "abc1234",
        "https://example.test/run/1",
    )
    for needle in (
        "CI failed on main",
        "repo: coilyco-flight-deck/infrastructure",
        "workflow: lint",
        "job: scan",
        "ref: refs/heads/main",
        "sha: abc1234",
        "run: https://example.test/run/1",
    ):
        assert needle in message


def test_main_dry_run_prints_message(capsys) -> None:
    mod = _load_script()
    rc = mod.main(
        [
            "--bot-token",
            "token",
            "--chat-id",
            "chat",
            "--repo",
            "coilyco-flight-deck/infrastructure",
            "--workflow",
            "lint",
            "--job",
            "scan",
            "--ref",
            "refs/heads/main",
            "--sha",
            "abc1234",
            "--run-url",
            "https://example.test/run/1",
            "--dry-run",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "CI failed on main" in out
    assert "repo: coilyco-flight-deck/infrastructure" in out


def test_main_uses_egress_proxy(monkeypatch) -> None:
    mod = _load_script()
    sent = {}

    def fake_send_message(bot_token, chat_id, message, api_base, proxy_url):
        sent.update(
            bot_token=bot_token,
            chat_id=chat_id,
            message=message,
            api_base=api_base,
            proxy_url=proxy_url,
        )

    monkeypatch.setenv("FORGEJO_EGRESS_PROXY", "https://proxy.example.test")
    monkeypatch.setattr(mod, "send_message", fake_send_message)
    rc = mod.main(
        [
            "--bot-token",
            "token",
            "--chat-id",
            "chat",
            "--repo",
            "coilyco-flight-deck/infrastructure",
            "--workflow",
            "lint",
            "--job",
            "scan",
            "--ref",
            "refs/heads/main",
            "--sha",
            "abc1234",
            "--run-url",
            "https://example.test/run/1",
        ]
    )
    assert rc == 0
    assert sent["proxy_url"] == "https://proxy.example.test"


def test_main_does_not_print_network_error_detail(monkeypatch, capsys) -> None:
    mod = _load_script()

    def fail_send_message(*args, **kwargs):
        raise urllib.error.URLError("credential-bearing proxy detail")

    monkeypatch.setattr(mod, "send_message", fail_send_message)
    rc = mod.main(
        [
            "--bot-token",
            "token",
            "--chat-id",
            "chat",
            "--repo",
            "coilyco-flight-deck/infrastructure",
            "--workflow",
            "lint",
            "--job",
            "scan",
            "--ref",
            "refs/heads/main",
            "--sha",
            "abc1234",
            "--run-url",
            "https://example.test/run/1",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "URLError" in err
    assert "credential-bearing" not in err
