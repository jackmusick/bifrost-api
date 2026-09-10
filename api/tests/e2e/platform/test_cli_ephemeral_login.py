"""End-to-end coverage for CLI password-grant boundaries on the real test API.

The default shared e2e stack has MFA enabled. This file therefore enforces the
live password-grant refusal path: a real ``bifrost login --email --password``
subprocess calls ``/auth/login`` and must exit before emitting credentials.

The successful password-grant mechanics are covered at lower layers by
``tests/unit/test_cli_login_ephemeral.py``: form login request shape, token
response handling, global credential storage, URL-only ``.env`` writing, and MFA
refusal branches. Real token issuance and MFA verification are covered by
``tests/e2e/api/test_auth.py``. The second test here preserves the remaining
live subprocess transport link by injecting real post-MFA fixture tokens through
``BIFROST_*`` env vars and calling ``bifrost api`` against the stack.
"""

from __future__ import annotations

import os
import subprocess
import sys

import httpx


def _mfa_required_for_password(api_url: str) -> bool:
    """Probe the test stack to see if global MFA is enabled."""
    with httpx.Client(base_url=api_url, timeout=10.0) as client:
        resp = client.get("/auth/status")
        resp.raise_for_status()
        return bool(resp.json().get("mfa_required_for_password", False))


def _bifrost_cli() -> list[str]:
    """Command vector for invoking the bifrost CLI via the same Python."""
    return [sys.executable, "-m", "bifrost"]


def test_ephemeral_login_refuses_mfa_required(e2e_api_url, platform_admin):
    """Default stack requires MFA, so password-grant login must refuse."""
    assert _mfa_required_for_password(e2e_api_url), (
        "default e2e stack must keep password-grant MFA enforcement enabled"
    )

    result = subprocess.run(
        _bifrost_cli()
        + [
            "login",
            "--email",
            platform_admin.email,
            "--password",
            platform_admin.password,
            "--url",
            e2e_api_url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2, "password-grant login should refuse when MFA is required"
    assert "MFA" in result.stderr, "refusal should explain that MFA is required"


def test_ephemeral_env_vars_authenticate_bifrost_api_subprocess(
    e2e_api_url, platform_admin
):
    """Real fixture tokens injected through BIFROST_* authenticate ``bifrost api``."""
    child_env = os.environ.copy()
    child_env["BIFROST_API_URL"] = e2e_api_url
    child_env["BIFROST_ACCESS_TOKEN"] = platform_admin.access_token
    child_env["BIFROST_REFRESH_TOKEN"] = platform_admin.refresh_token

    result = subprocess.run(
        _bifrost_cli() + ["api", "GET", "/api/integrations"],
        env=child_env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, "env-token subprocess API request should succeed"
