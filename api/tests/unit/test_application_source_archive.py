from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


def _zip(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def test_application_source_archive_rejects_invalid_vite_root(tmp_path: Path) -> None:
    from src.services.application_source_archive import (
        InvalidApplicationSource,
        read_application_source_zip,
    )

    archive = _zip(tmp_path / "source.zip", {"src/main.tsx": b"export {}"})

    with pytest.raises(InvalidApplicationSource) as exc:
        read_application_source_zip(archive)

    assert exc.value.code == "invalid_app_source"
    assert "package.json and index.html" in exc.value.message


def test_solution_source_archive_rejects_too_many_members_before_extract(
    tmp_path: Path,
) -> None:
    from src.services.application_source_archive import (
        InvalidApplicationSource,
        validate_solution_source_archive,
    )

    archive = _zip(
        tmp_path / "solution.zip",
        {
            "bifrost.solution.yaml": b"slug: pack\nname: Pack\n",
            ".bifrost/apps.yaml": b"apps: {}\n",
            "apps/a/package.json": b"{}",
        },
    )

    with pytest.raises(InvalidApplicationSource) as exc:
        validate_solution_source_archive(archive, max_members=2)

    assert exc.value.code == "solution_source_too_many_files"


def test_solution_source_archive_rejects_expanded_size_before_extract(
    tmp_path: Path,
) -> None:
    from src.services.application_source_archive import (
        InvalidApplicationSource,
        validate_solution_source_archive,
    )

    archive = _zip(
        tmp_path / "solution.zip",
        {
            "bifrost.solution.yaml": b"slug: pack\nname: Pack\n",
            ".bifrost/apps.yaml": b"apps: {}\n",
            "apps/a/big.bin": b"x" * 16,
        },
    )

    with pytest.raises(InvalidApplicationSource) as exc:
        validate_solution_source_archive(archive, max_expanded_bytes=15)

    assert exc.value.code == "solution_source_too_large"


def test_solution_source_archive_rejects_encrypted_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.services.application_source_archive import (
        InvalidApplicationSource,
        validate_solution_source_archive,
    )

    class Archive:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def infolist(self):
            info = zipfile.ZipInfo("bifrost.solution.yaml")
            info.flag_bits |= 0x1
            return [info]

    monkeypatch.setattr("src.services.application_source_archive.zipfile.ZipFile", Archive)

    with pytest.raises(InvalidApplicationSource) as exc:
        validate_solution_source_archive(tmp_path / "solution.zip")

    assert exc.value.code == "invalid_solution_source"
    assert "Encrypted" in exc.value.message
