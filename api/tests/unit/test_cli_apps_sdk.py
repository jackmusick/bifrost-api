from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from click.testing import CliRunner
from unittest.mock import AsyncMock

from bifrost import client as bifrost_client_module
from bifrost.commands.apps import apps_group


class _Response:
    def __init__(
        self,
        method: str,
        api_url: str,
        path: str,
        *,
        status_code: int = 200,
        json_body: Any | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json_body = json_body
        self.content = content if content is not None else b""
        self.headers = headers or {}
        self.text = (
            ("" if json_body is None else str(json_body))
            if content is None
            else content.decode(errors="replace")
        )
        self.request = httpx.Request(method, f"{api_url}{path}")

    def json(self) -> Any:
        return self._json_body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code} error",
                request=self.request,
                response=httpx.Response(
                    self.status_code,
                    json=self._json_body,
                    request=self.request,
                ),
            )


class _FakeClient:
    def __init__(self, *, app: dict[str, Any]) -> None:
        self.api_url = "http://test.local"
        self._access_token = "token"
        self.app = app
        self.jobs: list[dict[str, Any]] = []
        self.batch_response: dict[str, Any] | None = None
        self.source_content = b"PK\x03\x04source"
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    async def get(self, path: str):
        self.calls.append(("GET", path, None))
        if path == f"/api/applications/{self.app['slug']}":
            return _Response("GET", self.api_url, path, json_body=self.app)
        if path == "/api/applications":
            return _Response(
                "GET",
                self.api_url,
                path,
                json_body={"applications": [self.app], "total": 1},
            )
        if path == f"/api/applications/{self.app['id']}/source":
            return _Response(
                "GET",
                self.api_url,
                path,
                content=self.source_content,
                headers={
                    "content-disposition": 'attachment; filename="portal-source.zip"'
                },
            )
        if path.startswith("/api/platform-jobs/"):
            return _Response("GET", self.api_url, path, json_body=self.jobs.pop(0))
        return _Response("GET", self.api_url, path, status_code=404, json_body={})

    async def post(self, path: str, *, json: dict[str, Any] | None = None):
        self.calls.append(("POST", path, json))
        if path == f"/api/applications/{self.app['id']}/sdk/update":
            return _Response(
                "POST",
                self.api_url,
                path,
                status_code=202,
                json_body={"job_id": "job-single", "status": "queued", "reused": False},
            )
        if path == "/api/applications/sdk/update":
            assert self.batch_response is not None
            return _Response(
                "POST",
                self.api_url,
                path,
                json_body=self.batch_response,
            )
        return _Response("POST", self.api_url, path, status_code=404, json_body={})


def _app(app_id: str | None = None) -> dict[str, Any]:
    return {
        "id": app_id or str(uuid4()),
        "slug": "portal",
        "name": "Portal",
        "app_model": "standalone_v2",
        "sdk_package_version": "1.0.0",
        "sdk_fingerprint": "old-fp",
        "sdk_contract_version": 1,
        "sdk_built_at": "2026-09-12T00:00:00+00:00",
        "sdk_status": "update_available",
        "sdk_source_available": True,
    }


def _install_client(monkeypatch, fake: _FakeClient) -> None:
    monkeypatch.setattr(
        bifrost_client_module.BifrostClient,
        "get_instance",
        classmethod(lambda cls, require_auth=False: fake),
    )


def test_apps_sdk_status_shows_deployed_provenance(monkeypatch) -> None:
    fake = _FakeClient(app=_app())
    _install_client(monkeypatch, fake)

    result = CliRunner().invoke(apps_group, ["sdk", "status", "portal"])

    assert result.exit_code == 0, result.output
    assert "update_available" in result.output
    assert "sdk_package_version" in result.output
    assert ("GET", "/api/applications/portal", None) in fake.calls


def test_apps_sdk_update_single_polls_platform_job(monkeypatch) -> None:
    app = _app()
    fake = _FakeClient(app=app)
    fake.jobs = [
        {"status": "running", "progress": {"phase": "Building", "current": 1}},
        {
            "status": "succeeded",
            "progress": {"phase": "Done"},
            "result": {"deployment_id": "dep"},
        },
    ]
    _install_client(monkeypatch, fake)
    sleep = AsyncMock()
    monkeypatch.setattr("bifrost.platform_jobs.asyncio.sleep", sleep)

    result = CliRunner().invoke(apps_group, ["sdk", "update", "portal"])

    assert result.exit_code == 0, result.output
    assert ("POST", f"/api/applications/{app['id']}/sdk/update", None) in fake.calls
    assert [
        call
        for call in fake.calls
        if call[0] == "GET" and call[1].startswith("/api/platform-jobs/")
    ]
    assert sleep.await_count == 1


def test_apps_sdk_update_all_reports_skips_without_failing(monkeypatch) -> None:
    app = _app()
    skipped_id = str(uuid4())
    fake = _FakeClient(app=app)
    fake.batch_response = {
        "accepted": [
            {
                "application_id": app["id"],
                "job_id": "job-batch",
                "status": "queued",
                "reused": False,
            }
        ],
        "skipped": [
            {"application_id": skipped_id, "reason": "current"},
        ],
    }
    fake.jobs = [{"status": "succeeded", "progress": {"phase": "Done"}, "result": {}}]
    _install_client(monkeypatch, fake)
    monkeypatch.setattr("bifrost.platform_jobs.asyncio.sleep", AsyncMock())

    result = CliRunner().invoke(apps_group, ["sdk", "update", "--all"])

    assert result.exit_code == 0, result.output
    assert (
        "POST",
        "/api/applications/sdk/update",
        {"application_ids": None},
    ) in fake.calls
    assert skipped_id in result.output
    assert "current" in result.output


def test_apps_source_export_writes_retained_zip_without_overwriting(
    monkeypatch, tmp_path: Path
) -> None:
    app = _app()
    fake = _FakeClient(app=app)
    _install_client(monkeypatch, fake)
    destination = tmp_path / "portal-source.zip"

    result = CliRunner().invoke(
        apps_group, ["source", "export", "portal", str(destination)]
    )

    assert result.exit_code == 0, result.output
    assert destination.read_bytes() == fake.source_content

    result = CliRunner().invoke(
        apps_group, ["source", "export", "portal", str(destination)]
    )

    assert result.exit_code == 1
    assert "Refusing to overwrite" in result.output
