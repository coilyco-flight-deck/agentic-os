from __future__ import annotations

import io
import json
import urllib.request
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from agentic_os import signoz_logs


class FakeResponse:
    def __init__(self, data: bytes, *, headers: dict[str, str] | None = None):
        self._body = io.BytesIO(data)
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)


def _json_response(payload: Any, **headers: str) -> FakeResponse:
    return FakeResponse(
        json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
    )


def _write_inventory(
    path: Path,
    *,
    server: Any = None,
) -> None:
    if server is None:
        server = {
            "baseUrl": "https://signoz.example/mcp",
            "headers": {"X-Reader": "bounded"},
        }
    path.write_text(
        json.dumps({"imports": [], "mcpServers": {"signoz": server}}),
        encoding="utf-8",
    )


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[urllib.request.Request, dict[str, Any]], FakeResponse],
) -> list[urllib.request.Request]:
    requests: list[urllib.request.Request] = []

    def fake_urlopen(
        request: urllib.request.Request, *, timeout: int
    ) -> FakeResponse:
        assert timeout == signoz_logs.HTTP_TIMEOUT_SECONDS
        requests.append(request)
        payload = json.loads(request.data or b"{}")
        return handler(request, payload)

    monkeypatch.setattr(signoz_logs.urllib.request, "urlopen", fake_urlopen)
    return requests


def _successful_handler(
    _request: urllib.request.Request, payload: dict[str, Any]
) -> FakeResponse:
    method = payload.get("method")
    if method == "initialize":
        return _json_response(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": signoz_logs.MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "signoz", "version": "test"},
                },
            },
            **{"MCP-Session-Id": "session-1"},
        )
    if method == "notifications/initialized":
        return FakeResponse(b"", headers={"Content-Type": "application/json"})
    assert method == "tools/call"
    return _json_response(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "content": [{"type": "text", "text": "one matching record"}],
                "structuredContent": {"rows": [{"body": "one matching record"}]},
            },
        }
    )


def test_inventory_selects_only_the_signoz_http_server(tmp_path: Path) -> None:
    inventory = tmp_path / "mcporter.json"
    _write_inventory(inventory)

    server = signoz_logs.load_signoz_server(inventory)

    assert server.url == "https://signoz.example/mcp"
    assert server.headers == {"X-Reader": "bounded"}


@pytest.mark.parametrize(
    ("server", "message"),
    [
        ({"command": "signoz-mcp"}, "no HTTP URL"),
        ({"baseUrl": "file:///tmp/mcp"}, "configured signoz MCP server must use"),
        (
            {"baseUrl": "https://signoz.example/mcp", "headers": {"Accept": "x"}},
            "reserved or empty",
        ),
    ],
)
def test_inventory_rejects_non_http_and_protocol_overrides(
    tmp_path: Path, server: Any, message: str
) -> None:
    inventory = tmp_path / "mcporter.json"
    _write_inventory(inventory, server=server)

    with pytest.raises(signoz_logs.SignozLogsError, match=message) as raised:
        signoz_logs.load_signoz_server(inventory)

    assert raised.value.kind == "configuration"


def test_client_initializes_and_calls_only_signoz_search_logs(monkeypatch) -> None:
    requests = _install_transport(monkeypatch, _successful_handler)
    client = signoz_logs.MCPHTTPClient(
        signoz_logs.MCPServer(
            "https://signoz.example/mcp", {"X-Reader": "bounded"}
        ),
        max_bytes=4096,
    )

    client.initialize()
    result = client.call_tool(
        "signoz_search_logs",
        {"query": "service.name = 'runner'", "timeRange": "30m", "limit": 25},
    )

    payloads = [json.loads(request.data or b"{}") for request in requests]
    assert [payload["method"] for payload in payloads] == [
        "initialize",
        "notifications/initialized",
        "tools/call",
    ]
    assert payloads[-1]["params"] == {
        "name": "signoz_search_logs",
        "arguments": {
            "query": "service.name = 'runner'",
            "timeRange": "30m",
            "limit": 25,
        },
    }
    assert requests[-1].get_header("Mcp-session-id") == "session-1"
    assert requests[-1].get_header("Mcp-protocol-version") == (
        signoz_logs.MCP_PROTOCOL_VERSION
    )
    assert requests[-1].get_header("X-reader") == "bounded"
    assert result["structuredContent"]["rows"][0]["body"] == "one matching record"


def test_client_accepts_sse_tool_results(monkeypatch) -> None:
    def handler(
        _request: urllib.request.Request, payload: dict[str, Any]
    ) -> FakeResponse:
        if payload.get("method") != "tools/call":
            return _successful_handler(_request, payload)
        event = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": [{"type": "text", "text": "sse"}]},
            }
        )
        return FakeResponse(
            f"event: message\ndata: {event}\n\n".encode(),
            headers={"Content-Type": "text/event-stream"},
        )

    _install_transport(monkeypatch, handler)
    client = signoz_logs.MCPHTTPClient(
        signoz_logs.MCPServer("https://signoz.example/mcp", {}),
        max_bytes=4096,
    )

    client.initialize()

    assert client.call_tool("signoz_search_logs", {})["content"][0]["text"] == "sse"


def test_response_bound_fails_before_returning_partial_json(monkeypatch) -> None:
    def handler(
        _request: urllib.request.Request, _payload: dict[str, Any]
    ) -> FakeResponse:
        return FakeResponse(
            b"",
            headers={"Content-Type": "application/json", "Content-Length": "5000"},
        )

    _install_transport(monkeypatch, handler)
    client = signoz_logs.MCPHTTPClient(
        signoz_logs.MCPServer("https://signoz.example/mcp", {}),
        max_bytes=4096,
    )

    with pytest.raises(signoz_logs.SignozLogsError) as raised:
        client.initialize()

    assert raised.value.kind == "too_large"


def test_tool_arguments_keep_relative_and_absolute_windows_distinct() -> None:
    relative = signoz_logs._parse_args(
        [
            "--query",
            "service.name = 'runner'",
            "--search-text",
            "timeout",
            "--time-range",
            "30m",
            "--limit",
            "25",
            "--offset",
            "50",
        ]
    )
    absolute = signoz_logs._parse_args(["--start", "1000", "--end", "2000"])

    assert signoz_logs._tool_arguments(relative) == {
        "query": "service.name = 'runner'",
        "searchText": "timeout",
        "timeRange": "30m",
        "limit": 25,
        "offset": 50,
    }
    assert signoz_logs._tool_arguments(absolute) == {
        "start": 1000,
        "end": 2000,
        "limit": signoz_logs.DEFAULT_LIMIT,
        "offset": 0,
    }


@pytest.mark.parametrize(
    "argv",
    [
        ["--start", "1000"],
        ["--start", "2000", "--end", "1000"],
        ["--start", "0", "--end", str(signoz_logs.MAX_WINDOW_MS + 1)],
        ["--time-range", "8d"],
        ["--limit", str(signoz_logs.MAX_LIMIT + 1)],
        ["--max-bytes", str(signoz_logs.HARD_MAX_BYTES + 1)],
        ["--severity", "verbose"],
    ],
)
def test_cli_rejects_unbounded_queries(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        signoz_logs._parse_args(argv)

    assert raised.value.code == 2


def test_main_prints_only_the_signoz_tool_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsysbinary
) -> None:
    inventory = tmp_path / "mcporter.json"
    _write_inventory(inventory)
    monkeypatch.setattr(signoz_logs, "_inventory_path", lambda: inventory)
    requests = _install_transport(monkeypatch, _successful_handler)

    assert (
        signoz_logs.main(
            ["--service", "runner", "--severity", "error", "--limit", "1"]
        )
        == 0
    )

    captured = capsysbinary.readouterr()
    assert json.loads(captured.out) == {
        "content": [{"type": "text", "text": "one matching record"}],
        "structuredContent": {"rows": [{"body": "one matching record"}]},
    }
    assert captured.err == b""
    call = json.loads(requests[-1].data or b"{}")
    assert call["params"]["arguments"] == {
        "service": "runner",
        "severity": "ERROR",
        "timeRange": signoz_logs.DEFAULT_TIME_RANGE,
        "limit": 1,
        "offset": 0,
    }


def test_main_leaves_stdout_empty_when_configuration_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(
        signoz_logs, "_inventory_path", lambda: tmp_path / "missing.json"
    )

    assert signoz_logs.main([]) == signoz_logs.EXIT_CODES["configuration"]

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "signoz-logs-error: configuration:" in captured.err
