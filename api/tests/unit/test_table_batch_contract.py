from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.contracts.tables import DocumentBatchCreate


def test_batch_create_defaults_to_insert_and_returns_documents():
    payload = DocumentBatchCreate(documents=[])

    assert payload.documents == []
    assert payload.upsert is False
    assert payload.write_mode is None
    assert payload.effective_write_mode == "insert"
    assert payload.return_documents is True


def test_legacy_upsert_flag_maps_to_merge_upsert():
    payload = DocumentBatchCreate(
        documents=[{"id": "row-1", "data": {"value": 1}}],
        upsert=True,
    )

    assert payload.effective_write_mode == "merge_upsert"


def test_legacy_upsert_flag_allows_rows_without_ids():
    payload = DocumentBatchCreate(
        documents=[
            {"id": "row-1", "data": {"value": 1}},
            {"data": {"value": 2}},
        ],
        upsert=True,
    )

    assert payload.effective_write_mode == "merge_upsert"
    assert payload.documents[1].id is None


@pytest.mark.parametrize("write_mode", ["insert", "merge_upsert", "replace_upsert"])
def test_explicit_write_mode_controls_effective_write_mode(write_mode: str):
    payload = DocumentBatchCreate(
        documents=[{"id": "row-1", "data": {"value": 1}}],
        write_mode=write_mode,
        return_documents=False,
    )

    assert payload.effective_write_mode == write_mode
    assert payload.return_documents is False


@pytest.mark.parametrize("write_mode", ["insert", "replace_upsert"])
def test_upsert_flag_rejects_explicit_non_merge_write_modes(write_mode: str):
    with pytest.raises(ValidationError):
        DocumentBatchCreate(
            documents=[{"id": "row-1", "data": {"value": 1}}],
            upsert=True,
            write_mode=write_mode,
        )


@pytest.mark.parametrize(
    ("kwargs", "documents"),
    [
        ({"write_mode": "merge_upsert"}, [{"data": {"value": 1}}]),
        ({"write_mode": "replace_upsert"}, [{"data": {"value": 1}}]),
        ({"write_mode": "merge_upsert"}, [{"id": "", "data": {"value": 1}}]),
        ({"write_mode": "replace_upsert"}, [{"id": "", "data": {"value": 1}}]),
    ],
)
def test_upsert_modes_require_explicit_nonempty_document_ids(kwargs, documents):
    with pytest.raises(ValidationError):
        DocumentBatchCreate(documents=documents, **kwargs)


def test_batch_create_allows_at_most_1000_documents():
    DocumentBatchCreate(
        documents=[{"data": {"index": index}} for index in range(1000)]
    )

    with pytest.raises(ValidationError):
        DocumentBatchCreate(
            documents=[{"data": {"index": index}} for index in range(1001)]
        )
