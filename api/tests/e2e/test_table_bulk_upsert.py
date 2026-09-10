from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from src.models.orm.solutions import Solution
from src.models.orm.tables import Document, Table

pytestmark = pytest.mark.e2e


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


def _create_table(
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
            "name": f"bulk_{uuid.uuid4().hex[:8]}",
            "organization_id": organization_id,
            "policies": _admin_policy(policy_actions),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _bulk_body(*rows: tuple[str, dict]) -> dict:
    return {"documents": [{"id": doc_id, "data": data} for doc_id, data in rows]}


def test_bulk_upsert_requires_platform_admin(e2e_client, platform_admin, org1_user):
    table_id = _create_table(e2e_client, platform_admin)
    try:
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/bulk-upsert",
            headers=org1_user.headers,
            json=_bulk_body(("a", {"value": 1})),
        )
        assert response.status_code == 403, response.text
    finally:
        e2e_client.delete(f"/api/tables/{table_id}", headers=platform_admin.headers)


def test_bulk_upsert_honors_table_policies_for_platform_admin(
    e2e_client,
    platform_admin,
):
    table_id = _create_table(e2e_client, platform_admin, policy_actions=["read"])
    try:
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/bulk-upsert",
            headers=platform_admin.headers,
            json=_bulk_body(("denied", {"value": 1})),
        )
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == {"denied_row_indices": [0]}

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 0
    finally:
        e2e_client.delete(f"/api/tables/{table_id}", headers=platform_admin.headers)


def test_bulk_upsert_rejects_duplicate_ids_atomically(e2e_client, platform_admin):
    table_id = _create_table(e2e_client, platform_admin)
    try:
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/bulk-upsert",
            headers=platform_admin.headers,
            json=_bulk_body(("dup", {"value": 1}), ("dup", {"value": 2})),
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == {"duplicate_ids": ["dup"]}

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 0
    finally:
        e2e_client.delete(f"/api/tables/{table_id}", headers=platform_admin.headers)


def test_bulk_upsert_idempotent_replay_replaces_data_and_counts(
    e2e_client,
    platform_admin,
):
    table_id = _create_table(e2e_client, platform_admin)
    try:
        first = e2e_client.post(
            f"/api/tables/{table_id}/documents/bulk-upsert",
            headers=platform_admin.headers,
            json=_bulk_body(
                ("alpha", {"keep": "first", "remove": "gone"}),
                ("beta", {"nullable": None}),
            ),
        )
        assert first.status_code == 200, first.text
        assert first.json() == {"count": 2}

        replay = e2e_client.post(
            f"/api/tables/{table_id}/documents/bulk-upsert",
            headers=platform_admin.headers,
            json=_bulk_body(
                ("alpha", {"keep": "second", "nullable": None}),
                ("gamma", {"created": True}),
            ),
        )
        assert replay.status_code == 200, replay.text
        assert replay.json() == {"count": 2}

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
    finally:
        e2e_client.delete(f"/api/tables/{table_id}", headers=platform_admin.headers)


def test_bulk_upsert_rolls_back_when_request_validation_fails(
    e2e_client,
    platform_admin,
):
    table_id = _create_table(e2e_client, platform_admin)
    try:
        response = e2e_client.post(
            f"/api/tables/{table_id}/documents/bulk-upsert",
            headers=platform_admin.headers,
            json={"documents": [{"id": "valid", "data": {"x": 1}}, {"id": "bad", "data": []}]},
        )
        assert response.status_code == 422, response.text

        count = e2e_client.get(
            f"/api/tables/{table_id}/documents/count",
            headers=platform_admin.headers,
        )
        assert count.status_code == 200, count.text
        assert count.json()["count"] == 0
    finally:
        e2e_client.delete(f"/api/tables/{table_id}", headers=platform_admin.headers)


@pytest.mark.asyncio
async def test_bulk_upsert_solution_context_cannot_write_foreign_solution_table(
    db_session,
    e2e_client,
    platform_admin,
):
    owning_solution = Solution(
        id=uuid.uuid4(),
        slug=f"bulk-own-{uuid.uuid4().hex[:8]}",
        name="Bulk Owner",
    )
    foreign_solution = Solution(
        id=uuid.uuid4(),
        slug=f"bulk-foreign-{uuid.uuid4().hex[:8]}",
        name="Bulk Foreign",
    )
    table = Table(
        id=uuid.uuid4(),
        name=f"bulk_solution_{uuid.uuid4().hex[:8]}",
        organization_id=None,
        solution_id=owning_solution.id,
        access=_admin_policy(),
    )
    db_session.add_all([owning_solution, foreign_solution, table])
    await db_session.commit()
    try:
        response = e2e_client.post(
            f"/api/tables/{table.id}/documents/bulk-upsert?solution={foreign_solution.id}",
            headers=platform_admin.headers,
            json=_bulk_body(("blocked", {"value": 1})),
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
