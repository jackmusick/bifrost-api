from __future__ import annotations

import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "scheduler_fixture_server.py"
spec = importlib.util.spec_from_file_location("scheduler_fixture_server", MODULE_PATH)
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def serve_fixture():
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def post_form(base_url: str, data: dict[str, str]):
    request = Request(
        f"{base_url}/oauth/token",
        data=urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def post_mcp(base_url: str, payload: dict[str, object], token: str):
    request = Request(
        f"{base_url}/mcp",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def test_client_credentials_exchange_requires_exact_fixture_credentials():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        status, payload = post_form(
            base_url,
            {
                "grant_type": "client_credentials",
                "client_id": "scheduler-fixture-client",
                "client_secret": "scheduler-fixture-secret",
                "scope": "fixture.read",
            },
        )

        assert status == 200
        assert payload == {
            "access_token": "scheduler-fixture-access-service",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "fixture.read",
        }


def test_client_credentials_exchange_rejects_wrong_secret():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            post_form(
                base_url,
                {
                    "grant_type": "client_credentials",
                    "client_id": "scheduler-fixture-client",
                    "client_secret": "wrong",
                    "scope": "fixture.read",
                },
            )
        except HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read())
            assert payload["error"] == "invalid_client"
        else:  # pragma: no cover - failure branch
            raise AssertionError("fixture accepted wrong client credentials")


def test_mcp_initialize_and_tools_list_require_bearer_token():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            post_mcp(
                base_url,
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                "wrong",
            )
        except HTTPError as exc:
            assert exc.code == 401
            assert json.loads(exc.read()) == {"error": "unauthorized"}
        else:  # pragma: no cover - failure branch
            raise AssertionError("fixture accepted wrong MCP bearer token")

        status, initialized = post_mcp(
            base_url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
            "scheduler-fixture-access-service",
        )
        assert status == 200
        assert initialized == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "scheduler-fixture-mcp",
                    "version": "1.0.0",
                },
            },
        }

        status, tools = post_mcp(
            base_url,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            "scheduler-fixture-access-service",
        )
        assert status == 200
        assert tools == {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "scheduler_fixture_echo",
                        "description": "Echoes deterministic scheduler fixture input.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                            "required": ["message"],
                        },
                    }
                ]
            },
        }


def test_mcp_initialized_notification_returns_empty_accepted_response():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        request = Request(
            f"{base_url}/mcp",
            data=json.dumps(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            ).encode(),
            headers={
                "Authorization": "Bearer scheduler-fixture-access-service",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            assert response.status == 202
            assert response.read() == b""
