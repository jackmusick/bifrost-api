"""Validation and sanitization for retained App source archives."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# One standalone V2 App build input is intentionally capped at 256 MiB after
# sanitization. This is enforced for independent App uploads and for the one
# selected Solution App that an SDK rebuild will compile.
APP_SOURCE_MAX_EXPANDED_BYTES = 256 * 1024 * 1024

# A retained Solution archive may contain multiple Apps plus workflows and
# manifests, so it needs a larger pre-extract envelope than a single App. These
# limits bound CPU/memory/path traversal work before zip extraction without
# applying the single-App 256 MiB budget to the whole multi-App workspace.
SOLUTION_SOURCE_MAX_MEMBERS = 50_000
SOLUTION_SOURCE_MAX_EXPANDED_BYTES = 2 * 1024 * 1024 * 1024

_SOURCE_SKIP_DIRS = {
    ".cache",
    ".git",
    ".next",
    ".turbo",
    ".vite",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
}


@dataclass(frozen=True)
class InvalidApplicationSource(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def read_application_source_zip(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    seen: set[str] = set()
    expanded = 0
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise InvalidApplicationSource(
            "invalid_app_source", "App source is not a valid zip file."
        ) from exc
    with archive:
        for info in archive.infolist():
            rel = PurePosixPath(info.filename)
            if info.is_dir():
                continue
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise InvalidApplicationSource(
                    "invalid_app_source", f"Unsafe path in App source: {info.filename}"
                )
            normalized = _normalize_source_path(rel)
            normalized_name = normalized.as_posix()
            if normalized_name in seen:
                raise InvalidApplicationSource(
                    "invalid_app_source",
                    f"Duplicate path in App source: {normalized_name}",
                )
            seen.add(normalized_name)
            if _should_skip_source_path(normalized):
                continue
            expanded += info.file_size
            if expanded > APP_SOURCE_MAX_EXPANDED_BYTES:
                raise InvalidApplicationSource(
                    "app_source_too_large",
                    "Expanded App source exceeds the 256 MiB limit.",
                )
            try:
                files[normalized_name] = archive.read(info)
            except (zipfile.BadZipFile, RuntimeError) as exc:
                raise InvalidApplicationSource(
                    "invalid_app_source", "App source is not a valid zip file."
                ) from exc
    require_vite_source_files(files)
    return files


def require_vite_source_files(files: dict[str, bytes]) -> None:
    if "package.json" not in files or "index.html" not in files:
        raise InvalidApplicationSource(
            "invalid_app_source",
            "App source must be a Vite project with package.json and index.html at its root.",
        )


def enforce_application_source_budget(
    files: dict[str, bytes], *, max_expanded_bytes: int = APP_SOURCE_MAX_EXPANDED_BYTES
) -> None:
    expanded = sum(len(content) for content in files.values())
    if expanded > max_expanded_bytes:
        raise InvalidApplicationSource(
            "app_source_too_large",
            "Expanded App source exceeds the 256 MiB limit.",
        )


def validate_solution_source_archive(
    path: Path,
    *,
    max_members: int = SOLUTION_SOURCE_MAX_MEMBERS,
    max_expanded_bytes: int = SOLUTION_SOURCE_MAX_EXPANDED_BYTES,
) -> None:
    member_count = 0
    expanded = 0
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise InvalidApplicationSource(
            "invalid_solution_source", "Solution source is not a valid zip file."
        ) from exc
    with archive:
        for info in archive.infolist():
            member_count += 1
            if member_count > max_members:
                raise InvalidApplicationSource(
                    "solution_source_too_many_files",
                    f"Solution source archive exceeds the {max_members} member limit.",
                )
            if info.flag_bits & 0x1:
                raise InvalidApplicationSource(
                    "invalid_solution_source",
                    f"Encrypted zip members are not supported: {info.filename}",
                )
            rel = PurePosixPath(info.filename)
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                raise InvalidApplicationSource(
                    "invalid_solution_source",
                    f"Unsafe path in Solution source: {info.filename}",
                )
            expanded += info.file_size
            if expanded > max_expanded_bytes:
                raise InvalidApplicationSource(
                    "solution_source_too_large",
                    "Expanded Solution source exceeds the retained source limit.",
                )


def prepare_application_source_archive(
    source_zip: Path, retained_source_zip: Path
) -> dict[str, bytes]:
    source_files = read_application_source_zip(source_zip)
    _write_source_zip(retained_source_zip, source_files)
    return source_files


def _normalize_source_path(rel: PurePosixPath) -> PurePosixPath:
    parts = [part for part in rel.parts if part not in ("", ".")]
    if not parts:
        raise InvalidApplicationSource("invalid_app_source", "Unsafe empty path in App source.")
    return PurePosixPath(*parts)


def _should_skip_source_path(rel: PurePosixPath) -> bool:
    name = rel.name
    return (
        any(part in _SOURCE_SKIP_DIRS for part in rel.parts[:-1])
        or name in _SOURCE_SKIP_DIRS
        or name == ".env"
        or name.startswith(".env.")
    )


def _write_source_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
