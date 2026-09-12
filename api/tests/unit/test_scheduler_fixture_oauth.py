from __future__ import annotations

import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


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
    body = urlencode(data).encode()
    request = Request(
        f"{base_url}/oauth/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def test_authorize_redirect_requires_fixture_client_and_pkce():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        redirect_uri = "http://client:80/api/mcp/oauth/callback"
        authorize_url = (
            f"{base_url}/oauth/authorize?"
            + urlencode(
                {
                    "client_id": "scheduler-fixture-client",
                    "response_type": "code",
                    "state": "opaque-state",
                    "redirect_uri": redirect_uri,
                    "code_challenge": "challenge",
                    "code_challenge_method": "S256",
                }
            )
        )
        opener = build_opener(NoRedirect)
        try:
            opener.open(authorize_url, timeout=5)
        except HTTPError as exc:
            assert exc.code == 302
            final_url = exc.headers["Location"]
        else:  # pragma: no cover - failure branch
            raise AssertionError("fixture authorize endpoint did not redirect")
        parsed = urlparse(final_url)
        query = parse_qs(parsed.query)
        assert final_url.startswith(redirect_uri)
        assert query["code"] == ["scheduler-fixture-code"]
        assert query["state"] == ["opaque-state"]


def test_authorize_rejects_wrong_client():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            urlopen(
                f"{base_url}/oauth/authorize?client_id=wrong&response_type=code&state=s&"
                "redirect_uri=http://client:80/api/mcp/oauth/callback&"
                "code_challenge=challenge&code_challenge_method=S256",
                timeout=5,
            )
        except HTTPError as exc:
            assert exc.code == 400
            assert json.loads(exc.read()) == {"error": "invalid_request"}
        else:  # pragma: no cover - failure branch
            raise AssertionError("fixture accepted wrong OAuth client")


def test_authorization_code_exchange_requires_exact_code_client_secret_and_pkce():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        status, payload = post_form(
            base_url,
            {
                "grant_type": "authorization_code",
                "code": "scheduler-fixture-code",
                "client_id": "scheduler-fixture-client",
                "client_secret": "scheduler-fixture-secret",
                "redirect_uri": "http://client:80/api/mcp/oauth/callback",
                "code_verifier": "x" * 32,
            },
        )
        assert status == 200
        assert payload["access_token"] == "scheduler-fixture-access-authorized"
        assert payload["refresh_token"] == "scheduler-fixture-refresh"
        assert payload["scope"] == "fixture.read"


def test_authorization_code_exchange_rejects_wrong_code():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            post_form(
                base_url,
                {
                    "grant_type": "authorization_code",
                    "code": "wrong",
                    "client_id": "scheduler-fixture-client",
                    "client_secret": "scheduler-fixture-secret",
                    "redirect_uri": "http://client:80/api/mcp/oauth/callback",
                    "code_verifier": "x" * 32,
                },
            )
        except HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read())
            assert payload["error"] == "invalid_grant"
        else:  # pragma: no cover - failure branch
            raise AssertionError("fixture accepted wrong authorization code")


def test_refresh_token_exchange_still_uses_existing_contract():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        status, payload = post_form(
            base_url,
            {
                "grant_type": "refresh_token",
                "refresh_token": "scheduler-fixture-refresh",
                "client_id": "scheduler-fixture-client",
                "client_secret": "scheduler-fixture-secret",
            },
        )
        assert status == 200
        assert payload["access_token"] == "scheduler-fixture-access-refreshed"
        assert payload["refresh_token"] == "scheduler-fixture-refresh"
        assert payload["scope"] == "fixture.read"


def test_authorize_rejects_redirect_header_line_breaks():
    for server in serve_fixture():
        base_url = f"http://127.0.0.1:{server.server_port}"
        for line_break in ("\r", "\n", "\r\n"):
            query = urlencode({
                "client_id": "scheduler-fixture-client",
                "response_type": "code",
                "state": "opaque-state",
                "redirect_uri": f"http://client/{line_break}X-Injected: value/api/mcp/oauth/callback",
                "code_challenge": "challenge",
                "code_challenge_method": "S256",
            })
            try:
                build_opener(NoRedirect).open(f"{base_url}/oauth/authorize?{query}", timeout=5)
            except HTTPError as exc:
                assert exc.code == 400
                assert exc.headers.get("X-Injected") is None
                assert exc.headers.get("Location") is None
                assert json.loads(exc.read()) == {"error": "invalid_request"}
            else:
                raise AssertionError("fixture accepted a redirect with a header line break")
