"""
E2E tests for batch table-document operations against REST endpoints.

Document ``id`` is a globally-unique primary key, so all IDs must be
unique across all tables. Tests use UUID-suffixed IDs.

Auto-create-on-insert lives in the SDK (``bifrost.tables`` runs a
404 → POST /api/tables → retry on the first write); the REST handlers
themselves return 404 when the table is missing. This file exercises
the REST handlers directly, so each test creates its table first.
"""

import logging
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from src.models.orm.solutions import Solution
from src.models.orm.tables import Document, Table

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.e2e


def _uid(prefix: str = "") -> str:
    """Generate a globally unique ID with optional prefix."""
    return f"{prefix}{uuid4().hex[:12]}"


def _create_table(e2e_client, headers, name: str) -> str:
    resp = e2e_client.post(
        "/api/tables",
        headers=headers,
        json={"name": name},
    )
    assert resp.status_code == 201, f"Create table failed: {resp.text}"
    return resp.json()["id"]


def _admin_policy(actions: list[str] | None = None) -> dict:
    return {
        "policies": [
            {
                "name": "admin_bypass",
                "actions": actions or ["read", "create", "update", "delete"],
                "when": {"user": "is_platform_admin"},
            }
        ]
    }


def _create_policy_table(
    e2e_client,
    platform_admin,
    *,
    organization_id=None,
    policy_actions: list[str] | None = None,
) -> str:
    response = e2e_client.post(
        "/api/tables",
        headers=platform_admin.headers,
        json={
            "name": f"batch_policy_{uuid4().hex[:8]}",
            "organization_id": organization_id,
            "policies": _admin_policy(policy_actions),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _replace_body(*rows: tuple[str, dict], return_documents: bool = False) -> dict:
    return {
        "write_mode": "replace_upsert",
        "return_documents": return_documents,
        "documents": [{"id": doc_id, "data": data} for doc_id, data in rows],
    }


class TestInsertBatch:
    """Batch insert via POST /api/tables/{id}/documents/batch."""

    def test_insert_batch(self, e2e_client, platform_admin):
        """Insert multiple documents in a single batch."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_batch_{uuid4().hex[:8]}"
        )
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "documents": [
                    {"data": {"name": "Acme Corp", "status": "active"}},
                    {"data": {"name": "Beta Inc", "status": "pending"}},
                    {"data": {"name": "Gamma LLC", "status": "active"}},
                ],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["inserted"] == 3
        assert len(data["documents"]) == 3
        for doc in data["documents"]:
            assert doc["id"] is not None
            assert doc["table_id"] is not None
            assert "name" in doc["data"]

    def test_insert_batch_with_custom_ids(self, e2e_client, platform_admin):
        """Insert batch with caller-provided IDs."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_batch_{uuid4().hex[:8]}"
        )
        id1, id2 = _uid("acme-"), _uid("beta-")
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "documents": [
                    {"id": id1, "data": {"name": "Acme Corp"}},
                    {"id": id2, "data": {"name": "Beta Inc"}},
                ],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["inserted"] == 2
        ids = {doc["id"] for doc in data["documents"]}
        assert ids == {id1, id2}

class TestUpsertBatch:
    """Batch upsert via POST /api/tables/{id}/documents/batch with upsert=true."""

    def test_upsert_batch_creates_new(self, e2e_client, platform_admin):
        """Upsert batch creates all new documents."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_upsert_{uuid4().hex[:8]}"
        )
        id1, id2 = _uid("emp-"), _uid("emp-")
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "upsert": True,
                "documents": [
                    {"id": id1, "data": {"name": "John", "dept": "Eng"}},
                    {"id": id2, "data": {"name": "Jane", "dept": "Sales"}},
                ],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["inserted"] == 2
        ids = {doc["id"] for doc in data["documents"]}
        assert ids == {id1, id2}

    def test_upsert_batch_updates_existing(self, e2e_client, platform_admin):
        """Upsert batch updates existing documents (merge semantics)."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_upsert_{uuid4().hex[:8]}"
        )
        id1, id2 = _uid("emp-"), _uid("emp-")

        first = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "upsert": True,
                "documents": [
                    {"id": id1, "data": {"name": "John", "dept": "Eng"}},
                    {"id": id2, "data": {"name": "Jane", "dept": "Sales"}},
                ],
            },
        )
        assert first.status_code == 200, first.text

        update = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "upsert": True,
                "documents": [
                    {"id": id1, "data": {"dept": "Management"}},
                    {"id": id2, "data": {"dept": "Marketing"}},
                ],
            },
        )
        assert update.status_code == 200, update.text
        data = update.json()
        assert data["inserted"] == 2
        for doc in data["documents"]:
            if doc["id"] == id1:
                assert doc["data"]["dept"] == "Management"
                assert doc["data"]["name"] == "John"  # merge preserves prior fields
            elif doc["id"] == id2:
                assert doc["data"]["dept"] == "Marketing"
                assert doc["data"]["name"] == "Jane"

    def test_upsert_batch_mixed(self, e2e_client, platform_admin):
        """Upsert batch handles a mix of new and existing documents."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_upsert_{uuid4().hex[:8]}"
        )
        existing_id, new_id = _uid("existing-"), _uid("new-")

        seed = e2e_client.post(
            f"/api/tables/{table_id}/documents",
            headers=platform_admin.headers,
            json={"id": existing_id, "data": {"name": "Old"}},
        )
        assert seed.status_code == 201, seed.text

        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "upsert": True,
                "documents": [
                    {"id": existing_id, "data": {"name": "Updated"}},
                    {"id": new_id, "data": {"name": "Brand New"}},
                ],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["inserted"] == 2

        cnt = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert cnt.json()["count"] == 2


class TestReplaceUpsertBatch:
    """Replacement upsert via POST /api/tables/{id}/documents/batch."""

    def test_openapi_does_not_expose_bulk_upsert_route(self, e2e_client):
        response = e2e_client.get("/openapi.json")
        assert response.status_code == 200, response.text
        assert not any(
            path.endswith("/documents/bulk-upsert")
            for path in response.json()["paths"]
        )

    def test_replace_upsert_count_only_response(self, e2e_client, platform_admin):
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_replace_{uuid4().hex[:8]}"
        )
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json=_replace_body(
                ("alpha", {"replacement": True}),
                ("beta", {"nullable": None}),
            ),
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"inserted": 2, "errors": [], "documents": []}

    def test_replace_upsert_replaces_existing_data_and_counts(
        self,
        e2e_client,
        platform_admin,
    ):
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_replace_{uuid4().hex[:8]}"
        )
        first = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json=_replace_body(
                ("alpha", {"keep": "first", "remove": "gone"}),
                ("beta", {"nullable": None}),
            ),
        )
        assert first.status_code == 200, first.text
        assert first.json()["inserted"] == 2

        replay = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json=_replace_body(
                ("alpha", {"keep": "second", "nullable": None}),
                ("gamma", {"created": True}),
            ),
        )
        assert replay.status_code == 200, replay.text
        assert replay.json() == {"inserted": 2, "errors": [], "documents": []}

        alpha = e2e_client.get(
            f"/api/tables/{table_id}/documents/alpha",
            headers=platform_admin.headers,
        )
        assert alpha.status_code == 200, alpha.text
        assert alpha.json()["data"] == {"keep": "second", "nullable": None}

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 3

    def test_replace_upsert_rejects_duplicate_ids_atomically(
        self,
        e2e_client,
        platform_admin,
    ):
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_replace_{uuid4().hex[:8]}"
        )
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json=_replace_body(("dup", {"value": 1}), ("dup", {"value": 2})),
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == {"duplicate_ids": ["dup"]}

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 0

    def test_replace_upsert_honors_table_policies_atomically(
        self,
        e2e_client,
        platform_admin,
    ):
        table_id = _create_policy_table(
            e2e_client, platform_admin, policy_actions=["read"]
        )
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json=_replace_body(("denied", {"value": 1})),
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == {"denied_row_indices": [0]}

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 0

    def test_replace_upsert_rolls_back_when_request_validation_fails(
        self,
        e2e_client,
        platform_admin,
    ):
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_replace_{uuid4().hex[:8]}"
        )
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "write_mode": "replace_upsert",
                "documents": [
                    {"id": "valid", "data": {"x": 1}},
                    {"id": "bad", "data": []},
                ],
            },
        )
        assert response.status_code == 422, response.text

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_replace_upsert_solution_context_cannot_write_foreign_solution_table(
        self,
        db_session,
        e2e_client,
        platform_admin,
    ):
        owning_solution = Solution(
            id=uuid4(),
            slug=f"batch-own-{uuid4().hex[:8]}",
            name="Batch Owner",
        )
        foreign_solution = Solution(
            id=uuid4(),
            slug=f"batch-foreign-{uuid4().hex[:8]}",
            name="Batch Foreign",
        )
        table = Table(
            id=uuid4(),
            name=f"batch_solution_{uuid4().hex[:8]}",
            organization_id=None,
            solution_id=owning_solution.id,
            access=_admin_policy(),
        )
        db_session.add_all([owning_solution, foreign_solution, table])
        await db_session.commit()
        try:
            response = e2e_client.post(
                f"/api/tables/{table.id}/documents/batch?solution={foreign_solution.id}",
                headers=platform_admin.headers,
                json=_replace_body(("blocked", {"value": 1})),
            )
            assert response.status_code == 404, response.text

            rows = (
                await db_session.execute(
                    select(Document).where(Document.table_id == table.id)
                )
            ).scalars().all()
            assert rows == []
        finally:
            await db_session.execute(delete(Table).where(Table.id == table.id))
            await db_session.execute(
                delete(Solution).where(Solution.id.in_([owning_solution.id, foreign_solution.id]))
            )
            await db_session.commit()


class TestDeleteBatch:
    """Batch delete via POST /api/tables/{id}/documents/batch-delete."""

    def test_delete_batch(self, e2e_client, platform_admin):
        """Delete multiple existing documents in one round trip."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_delete_{uuid4().hex[:8]}"
        )
        id1, id2, id3 = _uid("del-"), _uid("del-"), _uid("del-")

        seed = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch",
            headers=platform_admin.headers,
            json={
                "documents": [
                    {"id": id1, "data": {"name": "A"}},
                    {"id": id2, "data": {"name": "B"}},
                    {"id": id3, "data": {"name": "C"}},
                ],
            },
        )
        assert seed.status_code == 200, seed.text

        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch-delete",
            headers=platform_admin.headers,
            json={"ids": [id1, id3]},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["deleted"] == 2
        assert set(data["deleted_ids"]) == {id1, id3}

        cnt = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert cnt.json()["count"] == 1

    def test_delete_batch_skips_nonexistent(self, e2e_client, platform_admin):
        """IDs that don't exist in the table are silently skipped."""
        table_id = _create_table(
            e2e_client, platform_admin.headers, f"test_delete_{uuid4().hex[:8]}"
        )
        real_id = _uid("real-")
        seed = e2e_client.post(
            f"/api/tables/{table_id}/documents",
            headers=platform_admin.headers,
            json={"id": real_id, "data": {"name": "Real"}},
        )
        assert seed.status_code == 201, seed.text

        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/batch-delete",
            headers=platform_admin.headers,
            json={"ids": [real_id, _uid("fake-"), _uid("fake-")]},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["deleted"] == 1
        assert data["deleted_ids"] == [real_id]

    def test_delete_batch_nonexistent_table(self, e2e_client, platform_admin):
        """Delete on a missing table returns 404 (REST surface)."""
        response = e2e_client.post(
            f"/api/tables/nonexistent_{uuid4().hex[:8]}/documents/batch-delete",
            headers=platform_admin.headers,
            json={"ids": [_uid(), _uid()]},
        )
        assert response.status_code == 404
