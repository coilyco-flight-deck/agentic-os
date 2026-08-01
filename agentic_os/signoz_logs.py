"""Search bounded SigNoz logs through the converged read-only MCP server."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any


MCP_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_SERVER_NAME = "signoz"
DEFAULT_TIME_RANGE = "1h"
DEFAULT_LIMIT = 100
MAX_LIMIT = 1_000
MAX_OFFSET = 1_000_000
DEFAULT_MAX_BYTES = 4 * 1024 * 1024
HARD_MAX_BYTES = 16 * 1024 * 1024
MAX_WINDOW_MS = 7 * 24 * 60 * 60 * 1000
MAX_QUERY_CHARS = 4_096
MAX_VALUE_CHARS = 256
HTTP_TIMEOUT_SECONDS = 15
RELATIVE_TIME_RE = re.compile(r"^(?P<count>[1-9][0-9]{0,3})(?P<unit>[mhd])$")
SEVERITIES = frozenset({"DEBUG", "INFO", "WARN", "ERROR", "FATAL"})
RESERVED_HEADERS = frozenset(
    {
        "accept",
        "content-length",
        "content-type",
        "mcp-protocol-version",
        "mcp-session-id",
    }
)

EXIT_CODES = {
    "too_large": 65,
    "unavailable": 69,
    "protocol": 70,
    "configuration": 78,
    "tool_error": 69,
}


class SignozLogsError(RuntimeError):
    """A typed failure rendered without writing a partial JSON result."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.exit_code = EXIT_CODES[kind]


@dataclasses.dataclass(frozen=True)
class MCPServer:
    """One HTTP MCP endpoint selected from the converged inventory."""

    url: str
    headers: Mapping[str, str]


def _inventory_path() -> Path:
    return Path.home() / ".mcporter" / "mcporter.json"


def _read_inventory(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SignozLogsError(
            "configuration", f"cannot read converged MCP inventory {path}: {exc}."
        ) from exc
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SignozLogsError(
            "configuration", f"converged MCP inventory {path} is not valid JSON."
        ) from exc


def load_signoz_server(path: Path | None = None) -> MCPServer:
    """Load the fixed SigNoz server entry without accepting an arbitrary endpoint."""

    inventory_path = path or _inventory_path()
    document = _read_inventory(inventory_path)
    if not isinstance(document, dict):
        raise SignozLogsError("configuration", "MCP inventory must be a JSON object.")
    servers = document.get("mcpServers")
    if not isinstance(servers, dict):
        raise SignozLogsError(
            "configuration", "MCP inventory must contain an mcpServers object."
        )
    raw_server = servers.get(DEFAULT_SERVER_NAME)
    if not isinstance(raw_server, dict):
        raise SignozLogsError(
            "configuration",
            "MCP inventory has no configured signoz server. Run AOS convergence and retry.",
        )

    raw_url = raw_server.get("url") or raw_server.get("baseUrl")
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise SignozLogsError(
            "configuration", "the configured signoz MCP server has no HTTP URL."
        )
    url = raw_url.strip()
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SignozLogsError(
            "configuration",
            "the configured signoz MCP server must use an http(s) URL without credentials or a fragment.",
        )

    raw_headers = raw_server.get("headers", {})
    if not isinstance(raw_headers, dict):
        raise SignozLogsError(
            "configuration", "the configured signoz MCP headers must be an object."
        )
    headers: dict[str, str] = {}
    for raw_name, raw_value in raw_headers.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            raise SignozLogsError(
                "configuration", "the configured signoz MCP headers must be strings."
            )
        name = raw_name.strip()
        if not name or name.lower() in RESERVED_HEADERS:
            raise SignozLogsError(
                "configuration",
                f"the configured signoz MCP header {raw_name!r} is reserved or empty.",
            )
        headers[name] = raw_value
    return MCPServer(url=url, headers=headers)


def _read_bounded(response: Any, max_bytes: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            advertised = int(content_length)
        except ValueError:
            advertised = 0
        if advertised > max_bytes:
            raise SignozLogsError(
                "too_large",
                f"SigNoz MCP advertised {advertised} bytes, above the {max_bytes}-byte limit.",
            )

    chunks: list[bytes] = []
    total = 0
    while total <= max_bytes:
        chunk = response.read(min(64 * 1024, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    if total > max_bytes:
        raise SignozLogsError(
            "too_large", f"SigNoz MCP returned more than the {max_bytes}-byte limit."
        )
    return b"".join(chunks)


def _decode_json(raw: bytes, *, context: str) -> Any:
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SignozLogsError("protocol", f"SigNoz MCP returned invalid {context} JSON.") from exc


def _decode_sse(raw: bytes, *, request_id: int) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SignozLogsError("protocol", "SigNoz MCP returned non-UTF-8 SSE.") from exc

    events: list[str] = []
    data_lines: list[str] = []
    for line in text.splitlines():
        if not line:
            if data_lines:
                events.append("\n".join(data_lines))
                data_lines = []
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").lstrip())
    if data_lines:
        events.append("\n".join(data_lines))

    for event in events:
        payload = _decode_json(event.encode("utf-8"), context="SSE event")
        if isinstance(payload, dict) and payload.get("id") == request_id:
            return payload
    raise SignozLogsError(
        "protocol", f"SigNoz MCP SSE contained no response for request {request_id}."
    )


def _decode_response(raw: bytes, content_type: str, *, request_id: int) -> Any:
    media_type = content_type.partition(";")[0].strip().lower()
    if media_type == "text/event-stream":
        return _decode_sse(raw, request_id=request_id)
    if media_type in {"application/json", ""}:
        return _decode_json(raw, context="response")
    raise SignozLogsError(
        "protocol", f"SigNoz MCP returned unsupported content type {media_type!r}."
    )


def _error_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "unknown JSON-RPC error"
    message = payload.get("message")
    return message if isinstance(message, str) and message else "unknown JSON-RPC error"


class MCPHTTPClient:
    """Minimal bounded Streamable HTTP client for one MCP tool call."""

    def __init__(self, server: MCPServer, *, max_bytes: int):
        self.server = server
        self.max_bytes = max_bytes
        self.session_id = ""
        self.initialized = False

    def _headers(self) -> dict[str, str]:
        headers = dict(self.server.headers)
        headers.update(
            {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            }
        )
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        return headers

    def _open(self, request: urllib.request.Request) -> Any:
        try:
            return urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            raise SignozLogsError(
                "unavailable", f"SigNoz MCP returned HTTP {exc.code}."
            ) from exc
        except OSError as exc:
            raise SignozLogsError(
                "unavailable", f"SigNoz MCP request failed: {exc}."
            ) from exc

    def _post(self, payload: Mapping[str, Any], *, request_id: int | None) -> Any:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            self.server.url,
            data=data,
            headers=self._headers(),
            method="POST",
        )
        with self._open(request) as response:
            raw = _read_bounded(response, self.max_bytes)
            if not self.session_id:
                session_id = response.headers.get("MCP-Session-Id", "").strip()
                if session_id:
                    self.session_id = session_id
            if request_id is None:
                return None
            return _decode_response(
                raw,
                response.headers.get("Content-Type", ""),
                request_id=request_id,
            )

    def initialize(self) -> None:
        request_id = 1
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "aosguard-signoz-logs", "version": "1"},
                },
            },
            request_id=request_id,
        )
        if not isinstance(response, dict) or response.get("id") != request_id:
            raise SignozLogsError("protocol", "SigNoz MCP returned an invalid initialize response.")
        if "error" in response:
            raise SignozLogsError(
                "protocol", f"SigNoz MCP initialization failed: {_error_message(response['error'])}."
            )
        result = response.get("result")
        if (
            not isinstance(result, dict)
            or result.get("protocolVersion") != MCP_PROTOCOL_VERSION
        ):
            raise SignozLogsError(
                "protocol", "SigNoz MCP negotiated an unsupported protocol version."
            )
        self._post(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            },
            request_id=None,
        )
        self.initialized = True

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self.initialized:
            raise SignozLogsError("protocol", "SigNoz MCP client was not initialized.")
        request_id = 2
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": dict(arguments)},
            },
            request_id=request_id,
        )
        if not isinstance(response, dict) or response.get("id") != request_id:
            raise SignozLogsError("protocol", "SigNoz MCP returned an invalid tool response.")
        if "error" in response:
            raise SignozLogsError(
                "tool_error", f"SigNoz log search failed: {_error_message(response['error'])}."
            )
        result = response.get("result")
        if not isinstance(result, dict):
            raise SignozLogsError("protocol", "SigNoz MCP tool response omitted its result.")
        if result.get("isError") is True:
            raise SignozLogsError("tool_error", "SigNoz log search returned an MCP tool error.")
        return result


def _bounded_positive(value: str, *, maximum: int, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{label} must be an integer") from exc
    if parsed < 1 or parsed > maximum:
        raise argparse.ArgumentTypeError(f"{label} must be between 1 and {maximum}")
    return parsed


def _limit(value: str) -> int:
    return _bounded_positive(value, maximum=MAX_LIMIT, label="limit")


def _max_bytes(value: str) -> int:
    return _bounded_positive(value, maximum=HARD_MAX_BYTES, label="max-bytes")


def _offset(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("offset must be an integer") from exc
    if parsed < 0 or parsed > MAX_OFFSET:
        raise argparse.ArgumentTypeError(f"offset must be between 0 and {MAX_OFFSET}")
    return parsed


def _bounded_text(value: str, *, maximum: int, label: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError(f"{label} cannot be empty")
    if len(value) > maximum:
        raise argparse.ArgumentTypeError(f"{label} cannot exceed {maximum} characters")
    return value


def _query(value: str) -> str:
    return _bounded_text(value, maximum=MAX_QUERY_CHARS, label="query")


def _search_text(value: str) -> str:
    return _bounded_text(value, maximum=MAX_QUERY_CHARS, label="search-text")


def _short_value(value: str) -> str:
    return _bounded_text(value, maximum=MAX_VALUE_CHARS, label="value")


def _severity(value: str) -> str:
    severity = _bounded_text(value, maximum=MAX_VALUE_CHARS, label="severity").upper()
    if severity not in SEVERITIES:
        allowed = ", ".join(sorted(SEVERITIES))
        raise argparse.ArgumentTypeError(f"severity must be one of {allowed}")
    return severity


def _time_range(value: str) -> str:
    match = RELATIVE_TIME_RE.fullmatch(value)
    if not match:
        raise argparse.ArgumentTypeError("time-range must look like 30m, 6h, or 7d")
    count = int(match.group("count"))
    seconds_per_unit = {"m": 60, "h": 60 * 60, "d": 24 * 60 * 60}
    if count * seconds_per_unit[match.group("unit")] * 1000 > MAX_WINDOW_MS:
        raise argparse.ArgumentTypeError("time-range cannot exceed 7d")
    return value


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="signoz logs",
        description="Search bounded log records through the configured SigNoz MCP reader.",
    )
    parser.add_argument("--query", type=_query, help="SigNoz log filter expression")
    parser.add_argument("--service", type=_short_value, help="service.name shortcut")
    parser.add_argument("--severity", type=_severity, help="exact severity_text shortcut")
    parser.add_argument("--search-text", type=_search_text, help="log body text search")
    parser.add_argument(
        "--time-range",
        type=_time_range,
        help=f"relative range up to 7d (default: {DEFAULT_TIME_RANGE})",
    )
    parser.add_argument("--start", type=int, help="absolute start time in unix milliseconds")
    parser.add_argument("--end", type=int, help="absolute end time in unix milliseconds")
    parser.add_argument("--limit", type=_limit, default=DEFAULT_LIMIT)
    parser.add_argument("--offset", type=_offset, default=0)
    parser.add_argument(
        "--max-bytes",
        type=_max_bytes,
        default=DEFAULT_MAX_BYTES,
        help=f"response and output bound (default: {DEFAULT_MAX_BYTES})",
    )
    args = parser.parse_args(argv)

    has_start = args.start is not None
    has_end = args.end is not None
    if has_start != has_end:
        parser.error("--start and --end must be supplied together")
    if has_start:
        if args.time_range is not None:
            parser.error("--time-range cannot be combined with --start and --end")
        if args.start < 0 or args.end <= args.start:
            parser.error("absolute times must satisfy 0 <= start < end")
        if args.end - args.start > MAX_WINDOW_MS:
            parser.error("absolute time window cannot exceed 7d")
    elif args.time_range is None:
        args.time_range = DEFAULT_TIME_RANGE
    return args


def _tool_arguments(args: argparse.Namespace) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "limit": args.limit,
        "offset": args.offset,
    }
    for argument, tool_key in (
        (args.query, "query"),
        (args.service, "service"),
        (args.severity, "severity"),
        (args.search_text, "searchText"),
        (args.time_range, "timeRange"),
    ):
        if argument is not None:
            arguments[tool_key] = argument
    if args.start is not None:
        arguments["start"] = args.start
        arguments["end"] = args.end
    return arguments


def _render_result(result: Mapping[str, Any], max_bytes: int) -> bytes:
    try:
        payload = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        ) + b"\n"
    except (TypeError, ValueError) as exc:
        raise SignozLogsError("protocol", "SigNoz MCP result is not valid JSON data.") from exc
    if len(payload) > max_bytes:
        raise SignozLogsError(
            "too_large",
            f"rendered SigNoz result is {len(payload)} bytes, above the {max_bytes}-byte limit.",
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        server = load_signoz_server()
        client = MCPHTTPClient(server, max_bytes=args.max_bytes)
        client.initialize()
        result = client.call_tool("signoz_search_logs", _tool_arguments(args))
        output = _render_result(result, args.max_bytes)
    except SignozLogsError as exc:
        print(f"signoz-logs-error: {exc.kind}: {exc}", file=sys.stderr)
        return exc.exit_code
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
