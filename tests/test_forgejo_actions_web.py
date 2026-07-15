from __future__ import annotations

import base64

from agentic_os import forgejo_actions_web as web


def test_request_uses_basic_auth(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(req):
        captured["authorization"] = req.headers["Authorization"]
        captured["method"] = req.method
        captured["content_type"] = req.headers.get("Content-Type")
        return Response()

    monkeypatch.setattr(web.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("FORGEJO_USERNAME", "coilyco-ops")

    assert web.request("https://forgejo.example/x", "secret") == b"ok"

    scheme, encoded = captured["authorization"].split(" ", 1)
    assert scheme == "Basic"
    assert base64.b64decode(encoded).decode("utf-8") == "coilyco-ops:secret"
    assert captured["method"] == "GET"
    assert captured["content_type"] is None
