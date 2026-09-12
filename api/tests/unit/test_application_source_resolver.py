from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.models.orm.applications import Application
from src.services.solutions.deploy import solution_entity_id


def _zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def _workspace_zip(path: Path, *, app_ids: list[UUID]) -> bytes:
    files: dict[str, bytes] = {
        "bifrost.solution.yaml": b"slug: sdk-pack\nname: SDK Pack\nversion: 1.0.0\n",
        ".bifrost/apps.yaml": (
            "apps:\n"
            f"  {app_ids[0]}:\n"
            f"    id: {app_ids[0]}\n"
            "    slug: target\n"
            "    name: Target\n"
            "    path: apps/target\n"
            "    app_model: standalone_v2\n"
            "    dependencies: {react: ^18.3.1}\n"
            f"  {app_ids[1]}:\n"
            f"    id: {app_ids[1]}\n"
            "    slug: other\n"
            "    name: Other\n"
            "    path: apps/other\n"
            "    app_model: standalone_v2\n"
            "    dependencies: {lodash: ^4.17.21}\n"
        ).encode(),
        "apps/target/package.json": b'{"name":"target"}',
        "apps/target/index.html": b"<div id='root'></div>",
        "apps/target/src/main.tsx": b"export const target = true;\n",
        "apps/target/logo.png": b"\x89PNG\r\n\x1a\nTARGET",
        "apps/other/package.json": b'{"name":"other"}',
        "apps/other/index.html": b"<div id='other'></div>",
        "apps/other/src/main.tsx": b"export const other = true;\n",
    }
    archive = _zip(path, files)
    return archive.read_bytes()


def _app(
    *,
    app_id: UUID | None = None,
    solution_id: UUID | None = None,
    active_deployment_id: UUID | None = None,
    dependencies: dict[str, str] | None = None,
) -> Application:
    return Application(
        id=app_id or uuid4(),
        slug=f"app-{uuid4().hex[:8]}",
        name="App",
        app_model="standalone_v2",
        solution_id=solution_id,
        active_deployment_id=active_deployment_id,
        dependencies=dependencies,
    )


def _assert_unavailable(exc: BaseException, code: str) -> None:
    assert getattr(exc, "code") == code
    assert str(exc)


@pytest.mark.asyncio
async def test_independent_success_reads_active_artifact_and_returns_exact_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver

    app = _app(
        active_deployment_id=uuid4(),
        dependencies={"react": "^18.3.1"},
    )
    archive = _zip(
        tmp_path / "source.zip",
        {
            "package.json": b'{"scripts":{"build":"vite build"}}',
            "index.html": b"<div id='root'></div>",
            "src/main.tsx": b"export {}",
        },
    )

    copied: list[tuple[UUID, UUID]] = []

    class Storage:
        async def copy_deployment_source_to_path(self, app_id, deployment_id, path):
            copied.append((app_id, deployment_id))
            path.write_bytes(archive.read_bytes())
            return archive.stat().st_size

    monkeypatch.setattr(resolver, "ApplicationSourceArtifactStorage", lambda: Storage())

    source = await resolver.resolve_application_source(app)

    assert source.source_kind == "independent"
    assert copied == [(app.id, app.active_deployment_id)]
    assert source.dependencies == {"react": "^18.3.1"}
    assert source.files == {
        "package.json": b'{"scripts":{"build":"vite build"}}',
        "index.html": b"<div id='root'></div>",
        "src/main.tsx": b"export {}",
    }


@pytest.mark.asyncio
async def test_independent_missing_active_deployment_is_typed() -> None:
    from src.services.application_source_resolver import (
        ApplicationSourceUnavailable,
        resolve_application_source,
    )

    with pytest.raises(ApplicationSourceUnavailable) as exc:
        await resolve_application_source(_app())
    _assert_unavailable(exc.value, "source_unavailable")


@pytest.mark.asyncio
async def test_independent_missing_object_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services import application_source_resolver as resolver

    class Storage:
        async def copy_deployment_source_to_path(self, *_args):
            raise FileNotFoundError("missing")

    monkeypatch.setattr(resolver, "ApplicationSourceArtifactStorage", lambda: Storage())

    with pytest.raises(resolver.ApplicationSourceUnavailable) as exc:
        await resolver.resolve_application_source(_app(active_deployment_id=uuid4()))
    _assert_unavailable(exc.value, "source_unavailable")


@pytest.mark.asyncio
async def test_independent_malformed_archive_is_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.services import application_source_resolver as resolver

    class Storage:
        async def copy_deployment_source_to_path(self, _app_id, _deployment_id, path):
            path.write_bytes(b"not a zip")
            return 9

    monkeypatch.setattr(resolver, "ApplicationSourceArtifactStorage", lambda: Storage())

    with pytest.raises(resolver.ApplicationSourceUnavailable) as exc:
        await resolver.resolve_application_source(_app(active_deployment_id=uuid4()))
    _assert_unavailable(exc.value, "invalid_source")


@pytest.mark.asyncio
async def test_solution_success_maps_remapped_id_and_returns_only_target_app(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver

    solution_id = uuid4()
    target_manifest_id = uuid4()
    other_manifest_id = uuid4()
    app = _app(
        app_id=solution_entity_id(solution_id, target_manifest_id),
        solution_id=solution_id,
    )
    archive_data = _workspace_zip(
        tmp_path / "solution.zip",
        app_ids=[target_manifest_id, other_manifest_id],
    )

    class Storage:
        async def copy_to_path(self, path):
            path.write_bytes(archive_data)
            return True

    monkeypatch.setattr(resolver, "SolutionSourceArtifactStorage", lambda _sid: Storage())

    source = await resolver.resolve_application_source(app)

    assert source.source_kind == "solution"
    assert source.dependencies == {"react": "^18.3.1"}
    assert source.files == {
        "package.json": b'{"name":"target"}',
        "index.html": b"<div id='root'></div>",
        "src/main.tsx": b"export const target = true;\n",
        "logo.png": b"\x89PNG\r\n\x1a\nTARGET",
    }


@pytest.mark.asyncio
async def test_solution_missing_mapping_is_typed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver

    solution_id = uuid4()
    archive_data = _workspace_zip(tmp_path / "solution.zip", app_ids=[uuid4(), uuid4()])

    class Storage:
        async def copy_to_path(self, path):
            path.write_bytes(archive_data)
            return True

    monkeypatch.setattr(resolver, "SolutionSourceArtifactStorage", lambda _sid: Storage())

    with pytest.raises(resolver.ApplicationSourceUnavailable) as exc:
        await resolver.resolve_application_source(_app(solution_id=solution_id))
    _assert_unavailable(exc.value, "source_unavailable")


@pytest.mark.asyncio
async def test_solution_missing_source_artifact_is_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.services import application_source_resolver as resolver

    class Storage:
        async def copy_to_path(self, _path):
            return False

    monkeypatch.setattr(resolver, "SolutionSourceArtifactStorage", lambda _sid: Storage())

    with pytest.raises(resolver.ApplicationSourceUnavailable) as exc:
        await resolver.resolve_application_source(_app(solution_id=uuid4()))
    _assert_unavailable(exc.value, "source_unavailable")


@pytest.mark.asyncio
async def test_solution_missing_required_source_files_is_typed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver

    solution_id = uuid4()
    manifest_id = uuid4()
    data = _zip(
        tmp_path / "solution.zip",
        {
            "bifrost.solution.yaml": b"slug: sdk-pack\nname: SDK Pack\n",
            ".bifrost/apps.yaml": (
                "apps:\n"
                f"  {manifest_id}:\n"
                f"    id: {manifest_id}\n"
                "    slug: target\n"
                "    name: Target\n"
                "    path: apps/target\n"
                "    app_model: standalone_v2\n"
            ).encode(),
            "apps/target/src/main.tsx": b"export {}",
        },
    ).read_bytes()

    class Storage:
        async def copy_to_path(self, path):
            path.write_bytes(data)
            return True

    monkeypatch.setattr(resolver, "SolutionSourceArtifactStorage", lambda _sid: Storage())

    with pytest.raises(resolver.ApplicationSourceUnavailable) as exc:
        await resolver.resolve_application_source(
            _app(app_id=solution_entity_id(solution_id, manifest_id), solution_id=solution_id)
        )
    _assert_unavailable(exc.value, "source_unavailable")


@pytest.mark.asyncio
async def test_solution_traversal_path_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver

    data = _zip(
        tmp_path / "bad.zip",
        {
            "bifrost.solution.yaml": b"slug: sdk-pack\nname: SDK Pack\n",
            "../evil.txt": b"nope",
        },
    ).read_bytes()

    class Storage:
        async def copy_to_path(self, path):
            path.write_bytes(data)
            return True

    monkeypatch.setattr(resolver, "SolutionSourceArtifactStorage", lambda _sid: Storage())

    with pytest.raises(resolver.ApplicationSourceUnavailable) as exc:
        await resolver.resolve_application_source(_app(solution_id=uuid4()))
    _assert_unavailable(exc.value, "invalid_source")


@pytest.mark.asyncio
async def test_resolver_does_not_call_solution_deploy_install_or_write_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver
    from src.services.solutions import zip_install
    from src.services.solutions.deploy import SolutionDeployer

    solution_id = uuid4()
    manifest_id = uuid4()
    app = _app(app_id=solution_entity_id(solution_id, manifest_id), solution_id=solution_id)
    data = _workspace_zip(tmp_path / "solution.zip", app_ids=[manifest_id, uuid4()])

    class Storage:
        async def copy_to_path(self, path):
            path.write_bytes(data)
            return True

        write = AsyncMock(side_effect=AssertionError("write must not be called"))
        write_from_path = AsyncMock(side_effect=AssertionError("write must not be called"))
        delete = AsyncMock(side_effect=AssertionError("delete must not be called"))

    def explode(*_args, **_kwargs):
        raise AssertionError("deploy/install entrypoint must not be called")

    monkeypatch.setattr(resolver, "SolutionSourceArtifactStorage", lambda _sid: Storage())
    monkeypatch.setattr(SolutionDeployer, "deploy", explode)
    monkeypatch.setattr(zip_install, "install_zip", explode)
    monkeypatch.setattr(zip_install, "install_zip_path", explode)

    await resolver.resolve_application_source(app)

    assert Storage.write.await_count == 0
    assert Storage.write_from_path.await_count == 0
    assert Storage.delete.await_count == 0


@pytest.mark.asyncio
async def test_blocking_resolution_runs_through_to_thread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.services import application_source_resolver as resolver

    app = _app(active_deployment_id=uuid4())
    archive = _zip(
        tmp_path / "source.zip",
        {
            "package.json": b"{}",
            "index.html": b"<div id='root'></div>",
            "src/main.tsx": b"export {}",
        },
    )

    class Storage:
        async def copy_deployment_source_to_path(self, _app_id, _deployment_id, path):
            path.write_bytes(archive.read_bytes())
            return archive.stat().st_size

    calls: list[str] = []

    async def fake_to_thread(func, *args, **kwargs):
        calls.append(getattr(func, "__name__", repr(func)))
        return func(*args, **kwargs)

    monkeypatch.setattr(resolver, "ApplicationSourceArtifactStorage", lambda: Storage())
    monkeypatch.setattr(resolver.asyncio, "to_thread", fake_to_thread)

    source = await resolver.resolve_application_source(app)

    assert source.files["src/main.tsx"] == b"export {}"
    assert calls
