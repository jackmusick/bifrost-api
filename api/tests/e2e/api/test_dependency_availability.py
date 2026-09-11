"""E2E coverage for dependency relationship availability."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.e2e.conftest import write_and_register


@pytest.mark.e2e
class TestDependencyAvailability:
    def test_form_workflow_true_and_zero_linked_app_false(
        self, e2e_client, platform_admin
    ) -> None:
        suffix = uuid4().hex[:8]
        workflow_name = f"availability_probe_{suffix}"
        workflow_path = f"workflows/{workflow_name}.py"
        workflow = write_and_register(
            e2e_client,
            platform_admin.headers,
            workflow_path,
            f'''
from bifrost import workflow

@workflow(name="{workflow_name}")
def {workflow_name}() -> str:
    return "ok"
''',
            workflow_name,
        )

        form_response = e2e_client.post(
            "/api/forms",
            headers=platform_admin.headers,
            json={
                "name": f"Availability form {suffix}",
                "workflow_id": workflow["id"],
                "form_schema": {"fields": []},
                "access_level": "authenticated",
            },
        )
        assert form_response.status_code == 201, form_response.text
        form = form_response.json()

        unlinked_form_response = e2e_client.post(
            "/api/forms",
            headers=platform_admin.headers,
            json={
                "name": f"Availability unlinked form {suffix}",
                "form_schema": {"fields": []},
                "access_level": "authenticated",
            },
        )
        assert unlinked_form_response.status_code == 201, unlinked_form_response.text
        unlinked_form = unlinked_form_response.json()

        app_slug = f"availability-empty-{suffix}"
        app_response = e2e_client.post(
            "/api/applications",
            headers=platform_admin.headers,
            json={
                "name": f"Availability empty app {suffix}",
                "slug": app_slug,
                "app_model": "inline_v1",
            },
        )
        assert app_response.status_code == 201, app_response.text
        app = app_response.json()

        try:
            availability_response = e2e_client.post(
                "/api/dependencies/availability",
                headers=platform_admin.headers,
                json={
                    "workflow_ids": [workflow["id"]],
                    "form_ids": [form["id"], unlinked_form["id"]],
                    "app_ids": [app["id"]],
                    "agent_ids": [],
                },
            )
            assert availability_response.status_code == 200, availability_response.text
            availability = availability_response.json()["has_relationships"]
            assert availability[f"workflow:{workflow['id']}"] is True
            assert availability[f"form:{form['id']}"] is True
            assert availability[f"form:{unlinked_form['id']}"] is False
            assert availability[f"app:{app['id']}"] is False
        finally:
            e2e_client.delete(
                f"/api/forms/{form['id']}",
                headers=platform_admin.headers,
            )
            e2e_client.delete(
                f"/api/forms/{unlinked_form['id']}",
                headers=platform_admin.headers,
            )
            e2e_client.delete(
                f"/api/applications/{app['id']}",
                headers=platform_admin.headers,
            )
            e2e_client.delete(
                f"/api/files/editor?path={workflow_path}",
                headers=platform_admin.headers,
            )

    def test_requested_workflow_detects_unrequested_form_reference(
        self, e2e_client, platform_admin
    ) -> None:
        suffix = uuid4().hex[:8]
        workflow_name = f"availability_mixed_{suffix}"
        workflow_path = f"workflows/{workflow_name}.py"
        workflow = write_and_register(
            e2e_client,
            platform_admin.headers,
            workflow_path,
            f'''
from bifrost import workflow

@workflow(name="{workflow_name}")
def {workflow_name}() -> str:
    return "ok"
''',
            workflow_name,
        )

        linked_form_response = e2e_client.post(
            "/api/forms",
            headers=platform_admin.headers,
            json={
                "name": f"Availability hidden linked form {suffix}",
                "workflow_id": workflow["id"],
                "form_schema": {"fields": []},
                "access_level": "authenticated",
            },
        )
        assert linked_form_response.status_code == 201, linked_form_response.text
        linked_form = linked_form_response.json()

        requested_form_response = e2e_client.post(
            "/api/forms",
            headers=platform_admin.headers,
            json={
                "name": f"Availability requested unrelated form {suffix}",
                "form_schema": {"fields": []},
                "access_level": "authenticated",
            },
        )
        assert requested_form_response.status_code == 201, requested_form_response.text
        requested_form = requested_form_response.json()

        try:
            availability_response = e2e_client.post(
                "/api/dependencies/availability",
                headers=platform_admin.headers,
                json={
                    "workflow_ids": [workflow["id"]],
                    "form_ids": [requested_form["id"]],
                    "app_ids": [],
                    "agent_ids": [],
                },
            )
            assert availability_response.status_code == 200, availability_response.text
            availability = availability_response.json()["has_relationships"]
            assert availability[f"workflow:{workflow['id']}"] is True
            assert availability[f"form:{requested_form['id']}"] is False
        finally:
            e2e_client.delete(
                f"/api/forms/{linked_form['id']}",
                headers=platform_admin.headers,
            )
            e2e_client.delete(
                f"/api/forms/{requested_form['id']}",
                headers=platform_admin.headers,
            )
            e2e_client.delete(
                f"/api/files/editor?path={workflow_path}",
                headers=platform_admin.headers,
            )
