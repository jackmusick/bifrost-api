"""Resolve retained source for rebuilding one standalone App."""

from __future__ import annotations

import asyncio
import base64
import binascii
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from src.jobs.platform.application_deploy import _read_source_zip
from src.jobs.platform.base import PlatformJobFailure
from src.models.orm.applications import Application
from src.services.application_source_artifact import ApplicationSourceArtifactStorage
from src.services.solutions.deploy import solution_entity_id
from src.services.solutions.source_artifact import SolutionSourceArtifactStorage
from src.services.solutions.zip_install import preview_zip_path

SourceKind = Literal["independent", "solution"]


@dataclass(frozen=True)
class ResolvedApplicationSource:
    files: dict[str, bytes]
    dependencies: dict[str, str]
    source_kind: SourceKind


class ApplicationSourceUnavailable(Exception):
    """Retained rebuild source is missing or unusable."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


async def resolve_application_source(application: Application) -> ResolvedApplicationSource:
    if application.solution_id is not None:
        return await _resolve_solution_source(application)
    return await _resolve_independent_source(application)


async def _resolve_independent_source(
    application: Application,
) -> ResolvedApplicationSource:
    if application.active_deployment_id is None:
        raise ApplicationSourceUnavailable(
            "source_unavailable",
            "Independent App has no active retained source deployment.",
        )

    storage = ApplicationSourceArtifactStorage()
    with tempfile.TemporaryDirectory(prefix="bifrost-app-source-") as tmp:
        source_zip = Path(tmp) / "source.zip"
        try:
            await storage.copy_deployment_source_to_path(
                application.id, application.active_deployment_id, source_zip
            )
        except FileNotFoundError as exc:
            raise ApplicationSourceUnavailable(
                "source_unavailable",
                "Retained App source artifact is missing.",
            ) from exc
        except Exception as exc:
            if _looks_like_missing_object(exc):
                raise ApplicationSourceUnavailable(
                    "source_unavailable",
                    "Retained App source artifact is missing.",
                ) from exc
            raise

        try:
            files = await asyncio.to_thread(_read_source_zip, source_zip)
        except PlatformJobFailure as exc:
            raise ApplicationSourceUnavailable("invalid_source", str(exc)) from exc

    return ResolvedApplicationSource(
        files=files,
        dependencies=dict(application.dependencies or {}),
        source_kind="independent",
    )


async def _resolve_solution_source(application: Application) -> ResolvedApplicationSource:
    solution_id = application.solution_id
    if solution_id is None:
        raise ApplicationSourceUnavailable(
            "source_unavailable",
            "Solution-managed App is missing its owning Solution id.",
        )

    storage = SolutionSourceArtifactStorage(solution_id)
    with tempfile.TemporaryDirectory(prefix="bifrost-solution-source-") as tmp:
        source_zip = Path(tmp) / "source.zip"
        try:
            exists = await storage.copy_to_path(source_zip)
        except Exception as exc:
            if _looks_like_missing_object(exc):
                raise ApplicationSourceUnavailable(
                    "source_unavailable",
                    "Retained Solution source artifact is missing.",
                ) from exc
            raise
        if not exists:
            raise ApplicationSourceUnavailable(
                "source_unavailable",
                "Retained Solution source artifact is missing.",
            )

        try:
            preview = await asyncio.to_thread(preview_zip_path, source_zip)
        except (ValueError, zipfile.BadZipFile) as exc:
            raise ApplicationSourceUnavailable(
                "invalid_source",
                f"Retained Solution source artifact is invalid: {exc}",
            ) from exc
        except Exception as exc:
            raise ApplicationSourceUnavailable(
                "invalid_source",
                f"Retained Solution source artifact could not be parsed: {exc}",
            ) from exc

    for manifest_app in preview.apps:
        manifest_id = _parse_manifest_id(manifest_app)
        if manifest_id is None:
            continue
        if solution_entity_id(solution_id, manifest_id) != application.id:
            continue

        files = _solution_app_files(manifest_app)
        if "package.json" not in files or "index.html" not in files:
            raise ApplicationSourceUnavailable(
                "source_unavailable",
                "Solution App source is missing package.json or index.html.",
            )
        return ResolvedApplicationSource(
            files=files,
            dependencies=dict(manifest_app.get("dependencies") or {}),
            source_kind="solution",
        )

    raise ApplicationSourceUnavailable(
        "source_unavailable",
        "No retained Solution manifest entry maps to this App.",
    )


def _parse_manifest_id(manifest_app: dict) -> UUID | None:
    try:
        return UUID(str(manifest_app["id"]))
    except (KeyError, TypeError, ValueError):
        return None


def _solution_app_files(manifest_app: dict) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name, content in (manifest_app.get("src_files") or {}).items():
        files[str(name)] = str(content).encode("utf-8")
    for name, content in (manifest_app.get("bin_files") or {}).items():
        try:
            files[str(name)] = base64.b64decode(str(content), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ApplicationSourceUnavailable(
                "invalid_source",
                f"Solution App binary source file is invalid base64: {name}",
            ) from exc
    return files


def _looks_like_missing_object(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}"
    return "NoSuchKey" in text or "404" in text or "Not Found" in text
