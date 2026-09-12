from datetime import datetime, timezone
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.jobs.platform.base import PlatformJobFailure


def test_sdk_update_definition_is_registered_with_expected_policy() -> None:
    from src.jobs.platform.application_sdk_update import (
        APPLICATION_SDK_UPDATE_DEFINITION,
        ApplicationSdkUpdatePayload,
    )
    from src.jobs.platform.registry import get_platform_job_definition

    definition = get_platform_job_definition("application.sdk_update")

    assert definition is APPLICATION_SDK_UPDATE_DEFINITION
    assert definition.job_type == "application.sdk_update"
    assert definition.payload_version == 1
    assert definition.payload_model is ApplicationSdkUpdatePayload
    assert definition.policy.timeout_seconds == 20 * 60
    assert definition.policy.max_attempts == 1
    assert definition.policy.min_memory_headroom_mb == 512


@pytest.mark.asyncio
async def test_sdk_update_resolves_source_and_uses_shared_build_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.jobs.platform import application_sdk_update as job
    from src.services.application_source_resolver import ResolvedApplicationSource

    app_id, old_id, new_id = uuid4(), uuid4(), uuid4()
    built_at = datetime(2026, 9, 12, tzinfo=timezone.utc)
    app = SimpleNamespace(
        id=app_id,
        name="My App",
        app_model="standalone_v2",
        solution_id=None,
        active_deployment_id=old_id,
        sdk_package_version="1.0.0",
        sdk_fingerprint="old-fp",
        sdk_contract_version=1,
        sdk_built_at=built_at,
    )
    events: list[tuple[str, object]] = []

    class DB:
        async def get(self, _model, requested_id):
            assert requested_id == app_id
            return app

    class Context:
        job_id = uuid4()

        async def report(self, message: str, *, percent: int):
            events.append(("report", (message, percent)))

    @asynccontextmanager
    async def db_context():
        yield DB()

    async def resolve_source(application):
        events.append(("resolve", application.id))
        assert application is app
        return ResolvedApplicationSource(
            files={"package.json": b"{}", "index.html": b"<div id='root'></div>"},
            dependencies={"react": "^18.3.1"},
            source_kind="independent",
        )

    async def rebuild_application(**kwargs):
        events.append(("build", kwargs))
        assert kwargs["application"] is app
        assert kwargs["deployment_id"] == new_id
        assert kwargs["enforce_expected_state"] is True
        assert kwargs["expected_active_deployment_id"] == old_id
        assert kwargs["expected_sdk_fingerprint"] == "old-fp"
        assert kwargs["source"].source_kind == "independent"
        return {"application_id": str(app_id), "deployment_id": str(new_id)}

    monkeypatch.setattr(job, "get_db_context", lambda: db_context())
    monkeypatch.setattr(job, "resolve_application_source", resolve_source)
    monkeypatch.setattr(job, "rebuild_application_from_source", rebuild_application)

    result = await job.run_application_sdk_update(
        Context(),
        job.ApplicationSdkUpdatePayload(
            application_id=app_id,
            deployment_id=new_id,
            expected_active_deployment_id=old_id,
            expected_sdk_package_version="1.0.0",
            expected_sdk_fingerprint="old-fp",
            expected_sdk_contract_version=1,
            expected_sdk_built_at=built_at,
        ),
    )

    assert result == {"application_id": str(app_id), "deployment_id": str(new_id)}
    assert [name for name, _ in events] == [
        "report",
        "report",
        "resolve",
        "report",
        "build",
        "report",
    ]


@pytest.mark.asyncio
async def test_sdk_update_source_unavailable_is_platform_job_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.jobs.platform import application_sdk_update as job
    from src.services.application_source_resolver import ApplicationSourceUnavailable

    app_id, deployment_id = uuid4(), uuid4()
    app = SimpleNamespace(id=app_id, app_model="standalone_v2", solution_id=None)

    class DB:
        async def get(self, *_args):
            return app

    class Context:
        job_id = uuid4()

        async def report(self, *_args, **_kwargs):
            pass

    @asynccontextmanager
    async def db_context():
        yield DB()

    async def resolve_source(_application):
        raise ApplicationSourceUnavailable("source_unavailable", "Retained source missing.")

    monkeypatch.setattr(job, "get_db_context", lambda: db_context())
    monkeypatch.setattr(job, "resolve_application_source", resolve_source)

    with pytest.raises(PlatformJobFailure) as exc:
        await job.run_application_sdk_update(
            Context(),
            job.ApplicationSdkUpdatePayload(
                application_id=app_id,
                deployment_id=deployment_id,
            ),
        )

    assert exc.value.code == "source_unavailable"
    assert "Retained source missing" in exc.value.message


@pytest.mark.asyncio
async def test_shared_rebuild_preserves_active_on_failure_and_cleans_new_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.services import application_build
    from src.services.application_source_resolver import ResolvedApplicationSource

    app_id, old_id, new_id = uuid4(), uuid4(), uuid4()
    app = SimpleNamespace(
        id=app_id,
        solution_id=None,
        app_model="standalone_v2",
        active_deployment_id=old_id,
        deployed_at=None,
        sdk_package_version="old",
        sdk_fingerprint="old-fp",
        sdk_contract_version=1,
        sdk_built_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    events: list[tuple[str, object]] = []

    class Builder:
        def compile_dist(self, *_args):
            return {"index.html": b"built"}

        async def upload_deployment(self, *_args):
            events.append(("upload", None))
            raise RuntimeError("upload failed")

        async def delete_deployment(self, application_id, deployment_id):
            events.append(("delete_dist", (application_id, deployment_id)))

    class SourceArtifacts:
        async def delete_deployment_source(self, application_id, deployment_id):
            events.append(("delete_source", (application_id, deployment_id)))

    monkeypatch.setattr(application_build, "SolutionAppBuilder", Builder)
    monkeypatch.setattr(
        application_build, "ApplicationSourceArtifactStorage", SourceArtifacts
    )
    monkeypatch.setattr(
        application_build,
        "current_sdk_metadata",
        lambda: SimpleNamespace(
            package_version="1.2.3",
            fingerprint="new-fp",
            contract_version=7,
        ),
    )

    with pytest.raises(RuntimeError, match="upload failed"):
        await application_build.rebuild_application_from_source(
            application=app,
            deployment_id=new_id,
            source=ResolvedApplicationSource(
                files={"package.json": b"{}", "index.html": b"<div id='root'></div>"},
                dependencies={},
                source_kind="independent",
            ),
        )

    assert app.active_deployment_id == old_id
    assert app.sdk_fingerprint == "old-fp"
    assert events == [
        ("upload", None),
        ("delete_source", (app_id, new_id)),
        ("delete_dist", (app_id, new_id)),
    ]


@pytest.mark.asyncio
async def test_shared_rebuild_does_not_persist_solution_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.services import application_build
    from src.services.application_source_resolver import ResolvedApplicationSource

    app_id, old_id, new_id = uuid4(), uuid4(), uuid4()
    solution_id = uuid4()
    app = SimpleNamespace(
        id=app_id,
        solution_id=solution_id,
        app_model="standalone_v2",
        active_deployment_id=old_id,
        deployed_at=None,
        sdk_package_version=None,
        sdk_fingerprint=None,
        sdk_contract_version=None,
        sdk_built_at=None,
    )
    events: list[tuple[str, object]] = []

    class Builder:
        def compile_dist(self, *_args):
            return {"index.html": b"built"}

        async def upload_deployment(self, application_id, deployment_id, dist):
            events.append(("upload", (application_id, deployment_id, dist)))

        async def delete_deployment(self, application_id, deployment_id):
            events.append(("delete_dist", (application_id, deployment_id)))

    class SourceArtifacts:
        async def write_deployment_source(self, *_args):
            raise AssertionError("Solution source must stay in the Solution archive")

        async def delete_deployment_source(self, application_id, deployment_id):
            events.append(("delete_source", (application_id, deployment_id)))

    class DB:
        async def flush(self):
            events.append(("flush", app.active_deployment_id))

    @asynccontextmanager
    async def db_context():
        yield DB()

    monkeypatch.setattr(application_build, "SolutionAppBuilder", Builder)
    monkeypatch.setattr(
        application_build, "ApplicationSourceArtifactStorage", SourceArtifacts
    )
    monkeypatch.setattr(application_build, "get_db_context", lambda: db_context())
    monkeypatch.setattr(
        application_build,
        "current_sdk_metadata",
        lambda: SimpleNamespace(
            package_version="1.2.3",
            fingerprint="new-fp",
            contract_version=7,
        ),
    )

    result = await application_build.rebuild_application_from_source(
        application=app,
        deployment_id=new_id,
        source=ResolvedApplicationSource(
            files={"package.json": b"{}", "index.html": b"<div id='root'></div>"},
            dependencies={},
            source_kind="solution",
        ),
    )

    assert result["deployment_id"] == str(new_id)
    assert app.active_deployment_id == new_id
    assert app.sdk_fingerprint == "new-fp"
    assert ("delete_dist", (app_id, old_id)) in events
    assert ("delete_source", (app_id, old_id)) not in events
