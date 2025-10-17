"""
Integration tests for Forms API
Tests Forms CRUD operations by calling Azure Functions directly (no HTTP)
"""

import pytest

from functions.forms import (
    create_form,
    delete_form,
    get_form,
    list_forms,
    update_form,
)
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestFormsIntegration:
    """Test Forms API endpoints"""

    @pytest.mark.asyncio
    async def test_list_forms_as_org_user(self, test_form, test_global_form, test_org_with_user):
        """
        CRITICAL TEST: Org user should see BOTH global forms AND their org's forms.

        This is the core authorization logic for regular users:
        1. All active GLOBAL forms (regardless of isPublic)
        2. All active forms in THEIR org

        This test would have caught the frontend filtering bug where org forms were hidden.
        """
        req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
        )

        response = await list_forms(req)
        status, body = parse_response(response)

        assert status == 200
        forms = body
        assert isinstance(forms, list)
        assert len(forms) >= 2, "Should have at least 2 forms (1 global + 1 org)"

        # Extract form names and partition keys for analysis
        form_names = [form["name"] for form in forms]
        form_org_ids = [form["orgId"] for form in forms]

        # CRITICAL: Must include global form
        assert test_global_form["name"] in form_names, \
            f"Org users MUST see global forms. Found: {form_names}"

        # CRITICAL: Must include org-specific form
        assert test_form["name"] in form_names, \
            f"Org users MUST see their org's forms. Found: {form_names}"

        # Verify we have forms from BOTH GLOBAL and the org
        assert "GLOBAL" in form_org_ids, "Should have at least one global form"
        assert test_form["org_id"] in form_org_ids, "Should have at least one org form"

        # Log for debugging
        print(f"\n✓ Org user correctly sees {len(forms)} forms:")
        for form in forms:
            print(f"  - {form['name']} (orgId: {form['orgId']}, isGlobal: {form.get('isGlobal')})")

    @pytest.mark.asyncio
    async def test_list_forms_as_platform_admin(self, test_platform_admin_user, test_global_form):
        """
        Platform admin in GLOBAL scope sees global forms.

        Note: Platform admins without X-Organization-Id header operate in GLOBAL scope,
        so they only see global forms. To see org-scoped forms, they must set X-Organization-Id.
        """
        req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
        )

        response = await list_forms(req)
        status, body = parse_response(response)

        assert status == 200
        forms = body
        assert isinstance(forms, list)
        assert len(forms) >= 1  # At least one global form

        form_names = [form["name"] for form in forms]
        assert test_global_form["name"] in form_names, f"Expected {test_global_form['name']}, found {form_names}"

        # All forms should be global since we're in GLOBAL scope
        for form in forms:
            assert form.get("isGlobal") is True or form.get("orgId") == "GLOBAL"

    @pytest.mark.asyncio
    async def test_create_form_as_platform_admin(self, test_platform_admin_user):
        """Platform admin can create forms"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Test Form Integration",
                "description": "A test form for integration testing",
                "linkedWorkflow": "test_workflow",
                "formSchema": {
                    "fields": [
                        {
                            "name": "test_field",
                            "label": "Test Field",
                            "type": "text",
                            "required": True
                        }
                    ]
                },
                "isGlobal": False,
                "isPublic": False
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["name"] == "Test Form Integration"
        assert form["description"] == "A test form for integration testing"
        # Platform admin without X-Organization-Id creates forms in GLOBAL scope
        assert form["isGlobal"] is True
        assert form["orgId"] == "GLOBAL"
        assert form["isPublic"] is False
        assert len(form["formSchema"]["fields"]) == 1
        assert "id" in form

        # Verify we can retrieve it
        form_id = form["id"]
        get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(),
            route_params={"formId": form_id},
        )

        get_response = await get_form(get_req)
        get_status, retrieved_form = parse_response(get_response)

        assert get_status == 200
        assert retrieved_form["id"] == form_id
        assert retrieved_form["name"] == "Test Form Integration"

    @pytest.mark.asyncio
    async def test_create_global_form_as_platform_admin(self, test_platform_admin_user):
        """Platform admin can create global forms"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Global Test Form Integration",
                "linkedWorkflow": "global_test_workflow",
                "formSchema": {"fields": []},
                "isGlobal": True,
                "isPublic": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["isGlobal"] is True
        assert form["orgId"] == "GLOBAL"

    @pytest.mark.asyncio
    async def test_get_form_by_id(self, test_org_with_user, test_global_form):
        """User can get a form by ID if they have access"""
        # Use the global form created by the fixture
        form_id = test_global_form["form_id"]

        get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
            route_params={"formId": form_id},
        )

        response = await get_form(get_req)
        status, body = parse_response(response)

        assert status == 200
        form = body
        assert form["id"] == form_id
        assert "formSchema" in form
        assert "fields" in form["formSchema"]

    @pytest.mark.asyncio
    async def test_get_form_not_found(self, test_platform_admin_user):
        """Getting non-existent form returns 404"""
        req = create_mock_request(
            method="GET",
            url="/api/forms/non-existent-form-id",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": "non-existent-form-id"},
        )

        response = await get_form(req)
        status, body = parse_response(response)

        assert status == 404
        assert body["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_update_form_as_platform_admin(self, test_platform_admin_user):
        """Platform admin can update forms"""
        # First create a form
        create_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form to Update Integration",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False
            }
        )

        create_response = await create_form(create_req)
        create_status, create_body = parse_response(create_response)

        assert create_status == 201
        form_id = create_body["id"]

        # Update it
        update_req = create_mock_request(
            method="PUT",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": form_id},
            body={
                "name": "Updated Form Name Integration"
            }
        )

        update_response = await update_form(update_req)
        status, body = parse_response(update_response)

        assert status == 200
        updated_form = body
        assert updated_form["name"] == "Updated Form Name Integration"
        assert updated_form["id"] == form_id

    @pytest.mark.asyncio
    async def test_delete_form_as_platform_admin(self, test_platform_admin_user):
        """Platform admin can soft-delete forms"""
        # First create a form
        create_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form to Delete Integration",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False
            }
        )

        create_response = await create_form(create_req)
        create_status, create_body = parse_response(create_response)

        assert create_status == 201
        form_id = create_body["id"]

        # Delete it
        delete_req = create_mock_request(
            method="DELETE",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": form_id},
        )

        delete_response = await delete_form(delete_req)
        status, _ = parse_response(delete_response)

        assert status == 204

        # Verify it's soft-deleted (should return 404 or isActive=false)
        get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(),
            route_params={"formId": form_id},
        )

        get_response = await get_form(get_req)
        get_status, get_body = parse_response(get_response)

        # Either 404 (filtered out) or 200 with isActive=false
        if get_status == 200:
            form = get_body
            assert form["isActive"] is False
        else:
            assert get_status == 404

    @pytest.mark.asyncio
    async def test_create_form_as_org_user_forbidden(self, test_org_with_user):
        """Org users cannot create forms (platform admin only)"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
            body={
                "name": "Should Fail",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False
            }
        )

        response = await create_form(req)
        status, _ = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_create_form_validation_error(self, test_platform_admin_user):
        """Creating form without required fields returns 400"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Incomplete Form"
                # Missing: linkedWorkflow, formSchema
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 400
        assert body["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_inactive_forms_visibility(self, test_platform_admin_user, test_org_with_user):
        """Inactive forms are visible to admins for management but hidden from regular users"""
        # Step 1: Create a form as platform admin
        create_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form to Deactivate Integration",
                "linkedWorkflow": "test_workflow",
                "formSchema": {"fields": []},
                "isGlobal": True,
                "isPublic": True
            }
        )

        create_response = await create_form(create_req)
        create_status, create_body = parse_response(create_response)

        assert create_status == 201
        form_id = create_body["id"]

        # Step 2: Verify form appears in list for both admin and org user
        admin_list_req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
        )

        admin_list_response = await list_forms(admin_list_req)
        admin_list_status, admin_forms = parse_response(admin_list_response)

        assert admin_list_status == 200
        admin_form_ids = [f["id"] for f in admin_forms]
        assert form_id in admin_form_ids, "Form should be visible to admin before deactivation"

        org_list_req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
        )

        org_list_response = await list_forms(org_list_req)
        org_list_status, org_forms = parse_response(org_list_response)

        assert org_list_status == 200
        org_form_ids = [f["id"] for f in org_forms]
        assert form_id in org_form_ids, "Form should be visible to org user before deactivation"

        # Step 3: Deactivate the form using update endpoint
        update_req = create_mock_request(
            method="PUT",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": form_id},
            body={"isActive": False}
        )

        update_response = await update_form(update_req)
        update_status, updated_form = parse_response(update_response)

        assert update_status == 200
        assert updated_form["isActive"] is False

        # Step 4: Verify form STILL appears in list for admin (admins can see inactive forms to manage them)
        admin_list_req2 = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
        )

        admin_list_response2 = await list_forms(admin_list_req2)
        admin_list_status2, admin_forms2 = parse_response(admin_list_response2)

        assert admin_list_status2 == 200
        admin_form_ids2 = [f["id"] for f in admin_forms2]
        assert form_id in admin_form_ids2, "Inactive form SHOULD be visible to admin for management"

        # Step 5: Verify form no longer appears in list for org user
        org_list_req2 = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
        )

        org_list_response2 = await list_forms(org_list_req2)
        org_list_status2, org_forms2 = parse_response(org_list_response2)

        assert org_list_status2 == 200
        org_form_ids2 = [f["id"] for f in org_forms2]
        assert form_id not in org_form_ids2, "Inactive form should NOT be visible to org user"

        # Step 6: Verify platform admin can still GET inactive form by ID (for management)
        admin_get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": form_id},
        )

        admin_get_response = await get_form(admin_get_req)
        admin_get_status, admin_get_body = parse_response(admin_get_response)

        assert admin_get_status == 200, "Platform admin should be able to GET inactive form by ID"
        assert admin_get_body["isActive"] is False

        # Step 6b: Verify org user CANNOT GET inactive form by ID
        org_get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
            route_params={"formId": form_id},
        )

        org_get_response = await get_form(org_get_req)
        org_get_status, _ = parse_response(org_get_response)

        assert org_get_status == 403, "Org user should get 403 Forbidden for inactive form"

        # Step 7: Verify admin can reactivate the form
        reactivate_req = create_mock_request(
            method="PUT",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            route_params={"formId": form_id},
            body={"isActive": True}
        )

        reactivate_response = await update_form(reactivate_req)
        reactivate_status, reactivate_body = parse_response(reactivate_response)

        assert reactivate_status == 200, "Admin should be able to reactivate inactive form"
        assert reactivate_body["isActive"] is True
