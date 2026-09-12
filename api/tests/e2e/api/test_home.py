from uuid import uuid4

import pytest

from src.core.security import create_embed_access_token


pytestmark = pytest.mark.e2e


def _create_form(e2e_client, headers, name: str, organization_id: str | None = None) -> dict:
    response = e2e_client.post(
        "/api/forms",
        headers=headers,
        json={
            "name": name,
            "description": "Home API test form",
            "workflow_id": None,
            "form_schema": {"fields": []},
            "access_level": "everyone",
            "organization_id": organization_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _collection_names(e2e_client, headers) -> set[str]:
    response = e2e_client.get("/api/home", headers=headers)
    assert response.status_code == 200, response.text
    return {collection["name"] for collection in response.json()["collections"]}


class TestHomeApi:
    def test_private_collection_and_pin_persist_for_owner_only(
        self, e2e_client, platform_admin, org1_user, org2_user, org1
    ):
        form = _create_form(
            e2e_client,
            platform_admin.headers,
            f"Home Private {uuid4().hex[:8]}",
            org1["id"],
        )
        key = f"form:{form['id']}"

        create_response = e2e_client.post(
            "/api/home/collections",
            headers=org1_user.headers,
            json={
                "name": f"Private Home {uuid4().hex[:8]}",
                "description": "",
                "icon": "folder",
                "shared": False,
                "organization_id": None,
                "resource_keys": [key],
            },
        )
        assert create_response.status_code == 201, create_response.text
        collection = create_response.json()
        assert collection["resource_keys"] == [key]
        assert collection["can_edit"] is True

        pref_response = e2e_client.put(
            f"/api/home/preferences/{key}",
            headers=org1_user.headers,
            json={"pinned": True, "opened": True},
        )
        assert pref_response.status_code == 204, pref_response.text

        owner_home = e2e_client.get("/api/home", headers=org1_user.headers)
        assert owner_home.status_code == 200, owner_home.text
        owner_body = owner_home.json()
        assert collection["name"] in {item["name"] for item in owner_body["collections"]}
        resource = next(item for item in owner_body["resources"] if item["key"] == key)
        assert resource["pinned"] is True
        assert resource["last_opened_at"] is not None

        assert collection["name"] not in _collection_names(e2e_client, org2_user.headers)

    def test_shared_collection_scope_and_unavailable_refs_do_not_leak(
        self, e2e_client, platform_admin, org1_user, org2_user, org1, org2
    ):
        org1_form = _create_form(
            e2e_client,
            platform_admin.headers,
            f"Home Shared Org1 {uuid4().hex[:8]}",
            org1["id"],
        )
        org2_form = _create_form(
            e2e_client,
            platform_admin.headers,
            f"Home Shared Org2 {uuid4().hex[:8]}",
            org2["id"],
        )
        create_response = e2e_client.post(
            "/api/home/collections",
            headers=platform_admin.headers,
            json={
                "name": f"Org Shared Home {uuid4().hex[:8]}",
                "description": "",
                "icon": "folder",
                "shared": True,
                "organization_id": org1["id"],
                "resource_keys": [f"form:{org1_form['id']}"],
            },
        )
        assert create_response.status_code == 201, create_response.text
        collection = create_response.json()

        assert collection["name"] in _collection_names(e2e_client, org1_user.headers)
        assert collection["name"] not in _collection_names(e2e_client, org2_user.headers)

        bad_update = e2e_client.put(
            f"/api/home/collections/{collection['id']}",
            headers=platform_admin.headers,
            json={
                "name": collection["name"],
                "description": "",
                "icon": "folder",
                "shared": True,
                "organization_id": org1["id"],
                "resource_keys": [f"form:{org2_form['id']}"],
            },
        )
        assert bad_update.status_code == 422, bad_update.text

        missing_pref = e2e_client.put(
            f"/api/home/preferences/form:{uuid4()}",
            headers=org1_user.headers,
            json={"pinned": True},
        )
        assert missing_pref.status_code == 404

    def test_non_admin_and_embed_boundaries(self, e2e_client, org1_user, org1):
        shared_attempt = e2e_client.post(
            "/api/home/collections",
            headers=org1_user.headers,
            json={
                "name": "User Shared",
                "description": "",
                "icon": "folder",
                "shared": True,
                "organization_id": org1["id"],
                "resource_keys": [],
            },
        )
        assert shared_attempt.status_code == 403

        token = create_embed_access_token(
            embed_kind="app",
            grant="hmac",
            resource_id=str(uuid4()),
            org_id=org1["id"],
        )
        embed_response = e2e_client.get(
            "/api/home",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert embed_response.status_code == 403
