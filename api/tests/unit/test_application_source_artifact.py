from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


class MemoryBody:
    def __init__(self, data: bytes):
        self._data = data
        self._offset = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._data) - self._offset
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class MemoryS3:
    exceptions = SimpleNamespace(NoSuchKey=KeyError)

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def put_object(self, *, Bucket, Key, Body, ContentType=None):
        self.objects[Key] = Body

    async def get_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return {"Body": MemoryBody(self.objects[Key])}

    async def delete_object(self, *, Bucket, Key):
        self.deleted.append(Key)
        self.objects.pop(Key, None)

    async def list_objects_v2(self, **kwargs):
        prefix = kwargs["Prefix"]
        keys = sorted(key for key in self.objects if key.startswith(prefix))
        return {"Contents": [{"Key": key} for key in keys], "IsTruncated": False}


@pytest.fixture
def source_storage(monkeypatch: pytest.MonkeyPatch):
    from src.services import application_source_artifact

    memory = MemoryS3()

    class StorageClient:
        def __init__(self, _settings):
            pass

        @asynccontextmanager
        async def get_client(self):
            yield memory

        async def put_object_from_chunks(
            self,
            path: str,
            chunks: AsyncIterator[bytes],
            *,
            content_type: str | None = None,
            part_size: int = 8 * 1024 * 1024,
        ) -> tuple[str, int]:
            data = b""
            async for chunk in chunks:
                data += chunk
            memory.objects[path] = data
            return ("hash", len(data))

        async def iter_object_chunks(self, path: str, *, chunk_size: int):
            data = memory.objects[path]
            for offset in range(0, len(data), chunk_size):
                yield data[offset : offset + chunk_size]

    monkeypatch.setattr(application_source_artifact, "S3StorageClient", StorageClient)
    return application_source_artifact.ApplicationSourceArtifactStorage(), memory


@pytest.mark.asyncio
async def test_source_artifact_writes_reads_and_deletes_exact_deployment_key(
    tmp_path: Path, source_storage
) -> None:
    storage, memory = source_storage
    app_id = uuid4()
    deployment_id = uuid4()
    source = tmp_path / "source.zip"
    source.write_bytes(b"zip-bytes")

    digest, size = await storage.write_deployment_source(app_id, deployment_id, source)

    key = f"_application_artifacts/{app_id}/deployments/{deployment_id}/source.zip"
    assert memory.objects == {key: b"zip-bytes"}
    assert digest == "hash"
    assert size == len(b"zip-bytes")

    copied = tmp_path / "copied.zip"
    assert await storage.copy_deployment_source_to_path(app_id, deployment_id, copied) == len(
        b"zip-bytes"
    )
    assert copied.read_bytes() == b"zip-bytes"

    assert await storage.read_deployment_source(app_id, deployment_id) == b"zip-bytes"

    await storage.delete_deployment_source(app_id, deployment_id)
    assert memory.deleted == [key]
    assert memory.objects == {}


@pytest.mark.asyncio
async def test_source_artifact_deletes_all_artifacts_for_app_prefix(source_storage) -> None:
    storage, memory = source_storage
    app_id = uuid4()
    other_app_id = uuid4()
    first = uuid4()
    second = uuid4()
    memory.objects = {
        f"_application_artifacts/{app_id}/deployments/{first}/source.zip": b"1",
        f"_application_artifacts/{app_id}/deployments/{second}/source.zip": b"2",
        f"_application_artifacts/{other_app_id}/deployments/{uuid4()}/source.zip": b"3",
    }

    await storage.delete_application_artifacts(app_id)

    assert sorted(memory.objects) == [
        next(key for key in memory.objects if key.startswith(f"_application_artifacts/{other_app_id}/"))
    ]
    assert sorted(memory.deleted) == sorted(
        [
        f"_application_artifacts/{app_id}/deployments/{first}/source.zip",
        f"_application_artifacts/{app_id}/deployments/{second}/source.zip",
        ]
    )
