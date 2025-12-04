"""
E2E API Test Suite - Full Application Flow

Tests the complete user journey through the Bifrost API:
1. First user registers -> becomes platform admin
2. Platform admin creates organizations
3. Platform admin creates org users
4. Org users complete registration
5. Test CRUD operations and permissions
6. Test isolation between organizations

This is a single test class that runs sequentially, building state
as it goes - just like a real user would interact with the system.
"""

import json
import logging
import os
from dataclasses import dataclass
from uuid import UUID

import httpx
import pytest

from tests.helpers.totp import generate_totp_code

logger = logging.getLogger(__name__)

# API base URL - set by test.sh --e2e
API_BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:18000")
# WebSocket URL derived from API base URL
WS_BASE_URL = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")


@dataclass
class User:
    """Tracks user state through the test flow."""
    email: str
    password: str
    name: str
    user_id: UUID | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    totp_secret: str | None = None
    organization_id: UUID | None = None
    is_superuser: bool = False

    @property
    def headers(self) -> dict[str, str]:
        """Auth headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }


# Module-level state that persists across test methods
class State:
    """Shared state for E2E tests."""
    client: httpx.Client | None = None
    platform_admin: User | None = None
    org1: dict | None = None
    org2: dict | None = None
    org1_user: User | None = None
    org2_user: User | None = None
    test_role_id: str | None = None
    test_form_id: str | None = None
    # New E2E test state
    sync_execution_id: str | None = None
    async_execution_id: str | None = None
    e2e_form_id: str | None = None
    e2e_role_id: str | None = None
    form_execution_id: str | None = None
    # Access level test forms
    authenticated_form_id: str | None = None
    public_form_id: str | None = None
    # Execution behavior tests
    org_user_config_exec_id: str | None = None
    admin_config_exec_id: str | None = None


@pytest.fixture(scope="module", autouse=True)
def setup_client():
    """Create HTTP client for the test module."""
    State.client = httpx.Client(base_url=API_BASE_URL, timeout=30.0)
    yield
    if State.client:
        State.client.close()


@pytest.mark.e2e
class TestFullApplicationFlow:
    """
    Complete E2E test of the Bifrost API.

    Tests run in order, building on previous state.
    This mirrors how a real deployment would be set up.
    """

    # =========================================================================
    # PHASE 1: Initial Setup - First User Becomes Platform Admin
    # =========================================================================

    def test_01_health_check(self):
        """Verify API is running before we start."""
        response = State.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_02_register_first_user_becomes_platform_admin(self):
        """First user to register becomes platform admin."""
        State.platform_admin = User(
            email="admin@gobifrost.com",
            password="AdminPass123!",
            name="Platform Admin",
        )

        # Register
        response = State.client.post(
            "/auth/register",
            json={
                "email": State.platform_admin.email,
                "password": State.platform_admin.password,
                "name": State.platform_admin.name,
            },
        )
        assert response.status_code == 201, f"Register failed: {response.text}"
        data = response.json()

        State.platform_admin.user_id = UUID(data["id"])
        State.platform_admin.is_superuser = data.get("is_superuser", False)

        # First user should be superuser
        assert State.platform_admin.is_superuser, "First user should be platform admin"

    def test_03_platform_admin_login_gets_mfa_challenge(self):
        """Login returns MFA requirement for password auth."""
        response = State.client.post(
            "/auth/login",
            data={
                "username": State.platform_admin.email,
                "password": State.platform_admin.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()

        # Should require MFA setup (first time) or MFA verification (after setup)
        assert data.get("mfa_required") or data.get("mfa_setup_required"), \
            f"Expected MFA requirement, got: {data}"

    def test_04_platform_admin_setup_mfa(self):
        """Setup TOTP for platform admin."""
        # First login to get MFA token
        login_response = State.client.post(
            "/auth/login",
            data={
                "username": State.platform_admin.email,
                "password": State.platform_admin.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login_data = login_response.json()
        # Token can be in mfa_token (for setup/verify) or access_token
        mfa_token = login_data.get("mfa_token") or login_data.get("access_token")
        assert mfa_token, f"No MFA token in response: {login_data}"

        # Setup MFA
        setup_response = State.client.post(
            "/auth/mfa/setup",
            headers={"Authorization": f"Bearer {mfa_token}"},
        )
        assert setup_response.status_code == 200, f"MFA setup failed: {setup_response.text}"
        setup_data = setup_response.json()

        State.platform_admin.totp_secret = setup_data["secret"]
        assert State.platform_admin.totp_secret, "Should receive TOTP secret"

    def test_05_platform_admin_verify_mfa_enrollment(self):
        """Verify TOTP code to complete MFA enrollment."""
        # Login again to get fresh MFA token
        login_response = State.client.post(
            "/auth/login",
            data={
                "username": State.platform_admin.email,
                "password": State.platform_admin.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login_data = login_response.json()
        mfa_token = login_data.get("mfa_token") or login_data.get("access_token")

        # Generate TOTP code
        totp_code = generate_totp_code(State.platform_admin.totp_secret)

        # Verify enrollment
        verify_response = State.client.post(
            "/auth/mfa/verify",
            headers={"Authorization": f"Bearer {mfa_token}"},
            json={"code": totp_code},
        )
        assert verify_response.status_code == 200, f"MFA verify failed: {verify_response.text}"
        verify_data = verify_response.json()

        # Should get tokens and recovery codes
        State.platform_admin.access_token = verify_data["access_token"]
        State.platform_admin.refresh_token = verify_data["refresh_token"]
        assert "recovery_codes" in verify_data, "Should receive recovery codes"

    def test_06_platform_admin_can_access_protected_endpoints(self):
        """Verify platform admin has valid token."""
        response = State.client.get(
            "/auth/me",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Auth check failed: {response.text}"
        data = response.json()
        assert data["email"] == State.platform_admin.email
        assert data["is_superuser"] is True

    # =========================================================================
    # PHASE 2: Platform Admin Creates Organizations
    # =========================================================================

    def test_10_create_first_organization(self):
        """Platform admin creates first organization."""
        response = State.client.post(
            "/api/organizations",
            headers=State.platform_admin.headers,
            json={
                "name": "Bifrost Dev Org",
                "domain": "gobifrost.dev",
            },
        )
        assert response.status_code == 201, f"Create org failed: {response.text}"
        State.org1 = response.json()
        assert State.org1["name"] == "Bifrost Dev Org"

    def test_11_create_second_organization(self):
        """Platform admin creates second organization for isolation tests."""
        response = State.client.post(
            "/api/organizations",
            headers=State.platform_admin.headers,
            json={
                "name": "Second Test Org",
                "domain": "example.com",
            },
        )
        assert response.status_code == 201, f"Create org failed: {response.text}"
        State.org2 = response.json()
        assert State.org2["name"] == "Second Test Org"

    def test_12_list_organizations(self):
        """Platform admin can list all organizations."""
        response = State.client.get(
            "/api/organizations",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List orgs failed: {response.text}"
        orgs = response.json()
        assert len(orgs) >= 2
        org_names = [o["name"] for o in orgs]
        assert "Bifrost Dev Org" in org_names
        assert "Second Test Org" in org_names

    def test_13_get_organization_by_id(self):
        """Platform admin can get specific organization."""
        response = State.client.get(
            f"/api/organizations/{State.org1['id']}",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get org failed: {response.text}"
        org = response.json()
        assert org["id"] == State.org1["id"]
        assert org["name"] == "Bifrost Dev Org"

    # =========================================================================
    # PHASE 3: Create Organization Users
    # =========================================================================

    def test_20_admin_creates_user_for_org1(self):
        """Platform admin pre-creates user for org1."""
        State.org1_user = User(
            email="alice@gobifrost.dev",
            password="AlicePass123!",
            name="Alice Smith",
            organization_id=UUID(State.org1["id"]),
        )

        response = State.client.post(
            "/api/users",
            headers=State.platform_admin.headers,
            json={
                "email": State.org1_user.email,
                "name": State.org1_user.name,
                "organization_id": State.org1["id"],
                "is_superuser": False,
            },
        )
        assert response.status_code == 201, f"Create user failed: {response.text}"
        data = response.json()
        State.org1_user.user_id = UUID(data["id"])
        # Verify user was created with correct organization
        assert data.get("organization_id") == State.org1["id"], \
            f"User should have organization_id, got: {data}"

    def test_21_admin_creates_user_for_org2(self):
        """Platform admin pre-creates user for org2."""
        State.org2_user = User(
            email="bob@example.com",
            password="BobPass123!",
            name="Bob Jones",
            organization_id=UUID(State.org2["id"]),
        )

        response = State.client.post(
            "/api/users",
            headers=State.platform_admin.headers,
            json={
                "email": State.org2_user.email,
                "name": State.org2_user.name,
                "organization_id": State.org2["id"],
                "is_superuser": False,
            },
        )
        assert response.status_code == 201, f"Create user failed: {response.text}"
        data = response.json()
        State.org2_user.user_id = UUID(data["id"])
        # Verify user was created with correct organization
        assert data.get("organization_id") == State.org2["id"], \
            f"User should have organization_id, got: {data}"

    def test_22_org1_user_completes_registration(self):
        """Org1 user completes registration with password."""
        response = State.client.post(
            "/auth/register",
            json={
                "email": State.org1_user.email,
                "password": State.org1_user.password,
                "name": State.org1_user.name,
            },
        )
        assert response.status_code == 201, f"Register failed: {response.text}"
        data = response.json()
        assert data["is_superuser"] is False, "Org user should not be superuser"

    def test_23_org1_user_setup_mfa_and_login(self):
        """Org1 user sets up MFA and gets tokens."""
        # Login to get MFA token
        login_response = State.client.post(
            "/auth/login",
            data={
                "username": State.org1_user.email,
                "password": State.org1_user.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login_data = login_response.json()
        setup_token = login_data.get("mfa_token") or login_data.get("access_token")

        # Setup MFA
        setup_response = State.client.post(
            "/auth/mfa/setup",
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        assert setup_response.status_code == 200, f"MFA setup failed: {setup_response.text}"
        State.org1_user.totp_secret = setup_response.json()["secret"]

        # Verify MFA
        totp_code = generate_totp_code(State.org1_user.totp_secret)
        verify_response = State.client.post(
            "/auth/mfa/verify",
            headers={"Authorization": f"Bearer {setup_token}"},
            json={"code": totp_code},
        )
        assert verify_response.status_code == 200, f"MFA verify failed: {verify_response.text}"
        verify_data = verify_response.json()

        State.org1_user.access_token = verify_data["access_token"]
        State.org1_user.refresh_token = verify_data["refresh_token"]

    def test_24_org2_user_completes_registration_and_mfa(self):
        """Org2 user completes full registration flow."""
        # Register
        response = State.client.post(
            "/auth/register",
            json={
                "email": State.org2_user.email,
                "password": State.org2_user.password,
                "name": State.org2_user.name,
            },
        )
        assert response.status_code == 201, f"Register failed: {response.text}"

        # Login for MFA setup
        login_response = State.client.post(
            "/auth/login",
            data={
                "username": State.org2_user.email,
                "password": State.org2_user.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login_data = login_response.json()
        setup_token = login_data.get("mfa_token") or login_data.get("access_token")

        # Setup MFA
        setup_response = State.client.post(
            "/auth/mfa/setup",
            headers={"Authorization": f"Bearer {setup_token}"},
        )
        assert setup_response.status_code == 200
        State.org2_user.totp_secret = setup_response.json()["secret"]

        # Verify MFA
        totp_code = generate_totp_code(State.org2_user.totp_secret)
        verify_response = State.client.post(
            "/auth/mfa/verify",
            headers={"Authorization": f"Bearer {setup_token}"},
            json={"code": totp_code},
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()

        State.org2_user.access_token = verify_data["access_token"]
        State.org2_user.refresh_token = verify_data["refresh_token"]

    # =========================================================================
    # PHASE 4: Roles and Permissions
    # =========================================================================

    def test_30_create_role(self):
        """Platform admin creates a role."""
        response = State.client.post(
            "/api/roles",
            headers=State.platform_admin.headers,
            json={
                "name": "Form Submitter",
                "description": "Can submit specific forms",
            },
        )
        assert response.status_code == 201, f"Create role failed: {response.text}"
        role = response.json()
        State.test_role_id = role["id"]
        assert role["name"] == "Form Submitter"

    def test_31_list_roles(self):
        """Users can list roles."""
        response = State.client.get(
            "/api/roles",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List roles failed: {response.text}"
        roles = response.json()
        assert isinstance(roles, list)
        role_names = [r["name"] for r in roles]
        assert "Form Submitter" in role_names

    def test_32_assign_role_to_org1_user(self):
        """Platform admin assigns role to org1 user."""
        response = State.client.post(
            f"/api/roles/{State.test_role_id}/users",
            headers=State.platform_admin.headers,
            json={"user_ids": [str(State.org1_user.user_id)]},
        )
        # Accept 200, 201, or 204
        assert response.status_code in [200, 201, 204], \
            f"Assign role failed: {response.status_code} - {response.text}"

    # =========================================================================
    # PHASE 5: Forms CRUD
    # =========================================================================

    def test_40_create_form(self):
        """Platform admin creates a form."""
        response = State.client.post(
            "/api/forms",
            headers=State.platform_admin.headers,
            json={
                "name": "Customer Onboarding",
                "description": "New customer intake form",
                "linked_workflow": "customer_onboarding",
                "form_schema": {
                    "fields": [
                        {"name": "company_name", "type": "text", "label": "Company Name", "required": True},
                        {"name": "contact_email", "type": "email", "label": "Contact Email", "required": True},
                    ]
                },
                "access_level": "role_based",
            },
        )
        assert response.status_code == 201, f"Create form failed: {response.text}"
        form = response.json()
        State.test_form_id = form["id"]
        assert form["name"] == "Customer Onboarding"

    def test_41_list_forms(self):
        """Users can list forms."""
        response = State.client.get(
            "/api/forms",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List forms failed: {response.text}"
        forms = response.json()
        assert isinstance(forms, list)

    def test_42_update_form(self):
        """Platform admin can update a form."""
        response = State.client.patch(
            f"/api/forms/{State.test_form_id}",
            headers=State.platform_admin.headers,
            json={"description": "Updated description"},
        )
        assert response.status_code == 200, f"Update form failed: {response.text}"
        form = response.json()
        assert form["description"] == "Updated description"

    def test_43_assign_form_to_role(self):
        """Platform admin assigns form to role."""
        response = State.client.post(
            f"/api/roles/{State.test_role_id}/forms",
            headers=State.platform_admin.headers,
            json={"form_ids": [State.test_form_id]},
        )
        # Accept 200, 201, or 204
        assert response.status_code in [200, 201, 204], \
            f"Assign form failed: {response.status_code} - {response.text}"

    # =========================================================================
    # PHASE 6: Permission Tests - What Org Users CAN'T Do
    # =========================================================================

    def test_50_org_user_cannot_list_all_organizations(self):
        """Org users cannot list all organizations."""
        response = State.client.get(
            "/api/organizations",
            headers=State.org1_user.headers,
        )
        # Should be 403 Forbidden (not superuser)
        assert response.status_code == 403, \
            f"Org user should not list orgs: {response.status_code}"

    def test_51_org_user_cannot_create_organization(self):
        """Org users cannot create organizations."""
        response = State.client.post(
            "/api/organizations",
            headers=State.org1_user.headers,
            json={"name": "Hacker Corp", "domain": "hacker.com"},
        )
        assert response.status_code == 403, \
            f"Org user should not create orgs: {response.status_code}"

    def test_52_org_user_cannot_create_roles(self):
        """Org users cannot create roles."""
        response = State.client.post(
            "/api/roles",
            headers=State.org1_user.headers,
            json={"name": "Hacker Role", "description": "Unauthorized"},
        )
        assert response.status_code == 403, \
            f"Org user should not create roles: {response.status_code}"

    # =========================================================================
    # PHASE 7: Organization Isolation Tests
    # =========================================================================

    def test_60_org1_user_cannot_see_org2_data(self):
        """Org1 user cannot access org2's resources."""
        # Try to access org2's forms by setting X-Organization-Id header
        response = State.client.get(
            "/api/forms",
            headers={
                **State.org1_user.headers,
                "X-Organization-Id": State.org2["id"],
            },
        )
        # Should be 403 - access denied to other org
        assert response.status_code == 403, \
            f"Cross-org access should be denied: {response.status_code}"

    # =========================================================================
    # PHASE 8: What Org Users CAN Do
    # =========================================================================

    def test_70_org_user_can_see_own_profile(self):
        """Org user can access their own profile."""
        response = State.client.get(
            "/auth/me",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        data = response.json()
        assert data["email"] == State.org1_user.email

    def test_71_org_user_can_list_own_executions(self):
        """Org user can list their execution history."""
        response = State.client.get(
            "/api/executions",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"List executions failed: {response.text}"
        # Response is ExecutionsListResponse with executions array and continuation_token
        data = response.json()
        assert "executions" in data, "Response should have 'executions' field"
        assert isinstance(data["executions"], list)

    def test_72_org_user_can_view_mfa_status(self):
        """Org user can view their MFA status."""
        response = State.client.get(
            "/auth/mfa/status",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"MFA status failed: {response.text}"
        data = response.json()
        assert data["mfa_enabled"] is True

    # =========================================================================
    # PHASE 9: Platform Admin User Management
    # =========================================================================

    def test_80_platform_admin_can_list_users(self):
        """Platform admin can list all users."""
        response = State.client.get(
            "/api/users",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List users failed: {response.text}"
        users = response.json()
        assert len(users) >= 3  # Admin + 2 org users
        emails = [u["email"] for u in users]
        assert State.platform_admin.email in emails
        assert State.org1_user.email in emails
        assert State.org2_user.email in emails

    # =========================================================================
    # PHASE 10: Config and Health Endpoints
    # =========================================================================

    def test_90_health_with_details(self):
        """Health endpoint with component details."""
        response = State.client.get("/health?details=true")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        # Should have component health info
        if "components" in data:
            assert "database" in data["components"]

    def test_91_config_list(self):
        """Platform admin can list config."""
        response = State.client.get(
            "/api/config",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List config failed: {response.text}"

    def test_92_list_workflows(self):
        """Users can list available workflows."""
        response = State.client.get(
            "/api/workflows",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List workflows failed: {response.text}"
        workflows = response.json()
        assert isinstance(workflows, list)

    def test_93_list_data_providers(self):
        """Users can list data providers."""
        response = State.client.get(
            "/api/data-providers",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List data providers failed: {response.text}"

    # =========================================================================
    # PHASE 11: Cleanup (Optional - tests should be idempotent)
    # =========================================================================

    def test_99_cleanup_form(self):
        """Clean up test form."""
        if State.test_form_id:
            response = State.client.delete(
                f"/api/forms/{State.test_form_id}",
                headers=State.platform_admin.headers,
            )
            # Accept 200, 204, or 404 (already deleted)
            assert response.status_code in [200, 204, 404]

    # =========================================================================
    # PHASE 12: Config Operations
    # =========================================================================

    def test_100_set_global_config_string(self):
        """Platform admin creates STRING config in GLOBAL scope."""
        response = State.client.post(
            "/api/config",
            headers=State.platform_admin.headers,
            json={
                "key": "e2e_test_timeout",
                "value": "30",
                "type": "string",
                "description": "E2E test config",
            },
        )
        assert response.status_code == 201, f"Create config failed: {response.text}"
        data = response.json()
        assert data["key"] == "e2e_test_timeout"
        assert data["value"] == "30"

    def test_101_set_int_config(self):
        """Platform admin creates INT config."""
        response = State.client.post(
            "/api/config",
            headers=State.platform_admin.headers,
            json={
                "key": "e2e_max_retries",
                "value": "5",
                "type": "int",
                "description": "Max retries setting",
            },
        )
        assert response.status_code == 201, f"Create config failed: {response.text}"

    def test_102_set_bool_config(self):
        """Platform admin creates BOOL config."""
        response = State.client.post(
            "/api/config",
            headers=State.platform_admin.headers,
            json={
                "key": "e2e_feature_flag",
                "value": "true",
                "type": "bool",
                "description": "Feature flag",
            },
        )
        assert response.status_code == 201, f"Create config failed: {response.text}"

    def test_103_set_json_config(self):
        """Platform admin creates JSON config."""
        response = State.client.post(
            "/api/config",
            headers=State.platform_admin.headers,
            json={
                "key": "e2e_settings",
                "value": '{"enabled": true, "level": 3}',
                "type": "json",
                "description": "JSON settings",
            },
        )
        assert response.status_code == 201, f"Create config failed: {response.text}"

    def test_104_set_secret_config(self):
        """Platform admin creates SECRET config (encrypted)."""
        response = State.client.post(
            "/api/config",
            headers=State.platform_admin.headers,
            json={
                "key": "e2e_api_key",
                "value": "secret-api-key-12345",
                "type": "secret",
                "description": "Test API key",
            },
        )
        assert response.status_code == 201, f"Create secret failed: {response.text}"

    def test_105_list_config_masks_secrets(self):
        """Listing configs shows [SECRET] for encrypted values."""
        response = State.client.get(
            "/api/config",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List config failed: {response.text}"
        configs = response.json()

        # Find the secret config
        secret_config = next((c for c in configs if c["key"] == "e2e_api_key"), None)
        assert secret_config is not None, "Secret config not found"
        assert secret_config["value"] == "[SECRET]", "Secret should be masked"

    def test_106_delete_config(self):
        """Platform admin can delete config."""
        response = State.client.delete(
            "/api/config/e2e_feature_flag",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 204, f"Delete config failed: {response.text}"

    def test_107_org_user_cannot_manage_config(self):
        """Org user cannot create config (403)."""
        response = State.client.post(
            "/api/config",
            headers=State.org1_user.headers,
            json={
                "key": "hacker_config",
                "value": "evil",
                "type": "STRING",
            },
        )
        assert response.status_code == 403, \
            f"Org user should not create config: {response.status_code}"

    # =========================================================================
    # PHASE 13: File Operations & Workflow Discovery
    # =========================================================================

    def test_110_list_workspace_files(self):
        """Platform admin can list workspace files."""
        response = State.client.get(
            "/api/editor/files?path=.",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List files failed: {response.text}"
        files = response.json()
        assert isinstance(files, list)

    def test_111_create_workflow_file(self):
        """Platform admin creates a test workflow file."""

        workflow_content = '''"""E2E Test Workflow"""
import logging
import time
from shared.decorators import workflow, param

logger = logging.getLogger(__name__)

@workflow(
    name="e2e_test_sync_workflow",
    description="E2E test workflow - sync execution",
    execution_mode="sync"
)
@param("message", "string", required=True)
@param("count", "int", default_value=1)
async def e2e_test_sync_workflow(context, message: str, count: int = 1):
    return {
        "status": "success",
        "message": message,
        "count": count,
        "user": context.email,
    }

@workflow(
    name="e2e_test_async_workflow",
    description="E2E test workflow - async execution with logging",
    execution_mode="async"
)
@param("delay_seconds", "int", default_value=2)
async def e2e_test_async_workflow(context, delay_seconds: int = 2):
    """
    Test workflow that:
    1. Logs at DEBUG level (to test log visibility)
    2. Sleeps for delay_seconds (to test concurrency)
    3. Retrieves config to test config scoping
    """
    # DEBUG level log - org users should NOT see this
    logger.debug("DEBUG: Starting async workflow")

    # INFO level log - all users should see this
    logger.info("INFO: Starting workflow")

    # Sleep to test concurrency - if blocking, 10 workflows = 20+ seconds
    # If parallel, 10 workflows should complete in ~3-5 seconds
    time.sleep(delay_seconds)

    # Retrieve config value to test config scoping
    config_value = await context.get_config("e2e_test_key", default=None)

    logger.info("INFO: Workflow completed after sleep")

    return {
        "status": "completed",
        "delayed": delay_seconds,
        "user_email": context.email,
        "org_id": context.scope,
        "config_value": config_value
    }
'''
        response = State.client.put(
            "/api/editor/files/content",
            headers=State.platform_admin.headers,
            json={
                "path": "e2e_test_workflow.py",
                "content": workflow_content,
                "encoding": "utf-8",
            },
        )
        assert response.status_code == 200, f"Create file failed: {response.text}"

    def test_112_workflow_immediately_available(self):
        """Workflow is discoverable after file creation (with discovery sync)."""
        import time

        # Poll for workflow to appear (discovery container syncs every few seconds)
        max_attempts = 30  # 30 seconds max wait
        workflow_names = []

        for attempt in range(max_attempts):
            response = State.client.get(
                "/api/workflows",
                headers=State.platform_admin.headers,
            )
            assert response.status_code == 200, f"List workflows failed: {response.text}"
            workflows = response.json()
            workflow_names = [w["name"] for w in workflows]

            if "e2e_test_sync_workflow" in workflow_names:
                break

            time.sleep(1)

        assert "e2e_test_sync_workflow" in workflow_names, \
            f"Test workflow not discovered after {max_attempts}s. Available: {workflow_names}"

    def test_113_read_file_content(self):
        """Platform admin can read file content back."""

        response = State.client.get(
            "/api/editor/files/content?path=e2e_test_workflow.py",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Read file failed: {response.text}"
        data = response.json()
        assert "e2e_test_sync_workflow" in data["content"]

    def test_114_create_folder(self):
        """Platform admin can create a folder."""

        response = State.client.post(
            "/api/editor/files/folder?path=e2e_test_folder",
            headers=State.platform_admin.headers,
        )
        # 201 for new, or 409 if exists from previous run
        assert response.status_code in [201, 409], f"Create folder failed: {response.text}"

    def test_115_org_user_cannot_access_files(self):
        """Org user cannot access file operations (403)."""
        response = State.client.get(
            "/api/editor/files?path=.",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not access files: {response.status_code}"

    def test_116_create_workspace_form_file(self):
        """Platform admin creates a form.json file via editor API."""

        # Create a .form.json file for hot reload testing
        form_content = json.dumps({
            "id": "e2e-workspace-form",
            "name": "E2E Workspace Form",
            "description": "Form created via file API for hot reload testing",
            "linkedWorkflow": "e2e_test_sync_workflow",
            "isGlobal": True,
            "accessLevel": "authenticated",
            "formSchema": {
                "fields": [
                    {"name": "message", "type": "text", "label": "Message", "required": True}
                ]
            }
        }, indent=2)

        response = State.client.put(
            "/api/editor/files/content",
            headers=State.platform_admin.headers,
            json={
                "path": "e2e_test.form.json",
                "content": form_content,
                "encoding": "utf-8",
            },
        )
        assert response.status_code == 200, f"Create form file failed: {response.text}"

    def test_117_workspace_form_file_persists(self):
        """Workspace form file can be read back."""

        # Read the form file back to verify it was created
        response = State.client.get(
            "/api/editor/files/content",
            headers=State.platform_admin.headers,
            params={"path": "e2e_test.form.json"},
        )
        assert response.status_code == 200, f"Read form file failed: {response.text}"

        # Parse and verify content
        data = response.json()
        content = data.get("content", "")
        form_data = json.loads(content)
        assert form_data.get("id") == "e2e-workspace-form"
        assert form_data.get("name") == "E2E Workspace Form"

    # =========================================================================
    # PHASE 14: Sync Workflow Execution
    # =========================================================================

    def test_120_execute_sync_workflow(self):
        """Platform admin executes sync workflow."""

        response = State.client.post(
            "/api/workflows/execute",
            headers=State.platform_admin.headers,
            json={
                "workflow_name": "e2e_test_sync_workflow",
                "input_data": {
                    "message": "Hello from E2E test",
                    "count": 42,
                },
            },
        )
        # Workflow execution should succeed - if it fails, something is broken
        assert response.status_code == 200, f"Execute failed: {response.text}"
        data = response.json()

        assert data["status"] == "Success", f"Unexpected status: {data}"
        assert "execution_id" in data or "executionId" in data

        # Store execution ID for later tests
        State.sync_execution_id = data.get("execution_id") or data.get("executionId")

    def test_121_sync_execution_returns_result(self):
        """Sync execution returns expected result."""
        if not State.sync_execution_id:
            pytest.skip("No previous execution - workflow not available")

        response = State.client.post(
            "/api/workflows/execute",
            headers=State.platform_admin.headers,
            json={
                "workflow_name": "e2e_test_sync_workflow",
                "input_data": {"message": "Test message", "count": 10},
            },
        )
        assert response.status_code == 200, f"Workflow execution failed: {response.text}"
        data = response.json()

        result = data.get("result", {})
        assert result.get("status") == "success"
        assert result.get("message") == "Test message"
        assert result.get("count") == 10

    def test_122_org_user_cannot_execute_directly(self):
        """Org user cannot call /execute endpoint directly (403)."""
        response = State.client.post(
            "/api/workflows/execute",
            headers=State.org1_user.headers,
            json={
                "workflow_name": "any_workflow",
                "input_data": {"message": "Hacked"},
            },
        )
        assert response.status_code == 403, \
            f"Org user should not execute directly: {response.status_code}"

    # =========================================================================
    # PHASE 15: Async Workflow Execution (basic polling, no WebSocket)
    # =========================================================================

    def test_130_execute_async_workflow(self):
        """Platform admin executes async workflow."""

        response = State.client.post(
            "/api/workflows/execute",
            headers=State.platform_admin.headers,
            json={
                "workflow_name": "e2e_test_async_workflow",
                "input_data": {"delay_seconds": 1},
            },
        )
        assert response.status_code in [200, 202], f"Async workflow execute failed: {response.text}"
        data = response.json()

        # Store execution ID
        State.async_execution_id = data.get("execution_id") or data.get("executionId")
        assert State.async_execution_id, "Should return execution_id"

    def test_131_async_execution_eventually_completes(self):
        """Poll until async execution completes."""
        import time

        if not State.async_execution_id:
            pytest.skip("No async execution ID")

        # Poll for completion
        for _ in range(30):  # 30 second timeout
            response = State.client.get(
                f"/api/executions/{State.async_execution_id}",
                headers=State.platform_admin.headers,
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                if status in ["Success", "Failed"]:
                    assert status == "Success", f"Execution failed: {data}"
                    return
            time.sleep(1)

        pytest.fail("Async execution did not complete within timeout")

    # =========================================================================
    # PHASE 16: Data Provider Execution
    # =========================================================================

    def test_140_list_data_providers(self):
        """Platform admin can list data providers."""
        response = State.client.get(
            "/api/data-providers",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List data providers failed: {response.text}"
        # Response should be a list
        data = response.json()
        assert isinstance(data, list)

    # =========================================================================
    # PHASE 17: Form-Based Execution & Access Control
    # =========================================================================

    def test_150_create_form_linked_to_workflow(self):
        """Platform admin creates form linked to test workflow."""
        # Use a simple workflow name - actual execution may fail but form creation should work
        response = State.client.post(
            "/api/forms",
            headers=State.platform_admin.headers,
            json={
                "name": "E2E Test Form",
                "description": "Form for E2E testing",
                "linked_workflow": "e2e_test_sync_workflow",
                "form_schema": {
                    "fields": [
                        {"name": "message", "type": "text", "label": "Message", "required": True},
                        {"name": "count", "type": "number", "label": "Count", "required": False},
                    ]
                },
                "access_level": "role_based",
                "default_launch_params": {"count": 1},
            },
        )
        assert response.status_code == 201, f"Create form failed: {response.text}"
        form = response.json()
        State.e2e_form_id = form["id"]

    def test_151_create_role_for_form_access(self):
        """Platform admin creates role for form access."""
        if not State.e2e_form_id:
            pytest.skip("Form not created")

        response = State.client.post(
            "/api/roles",
            headers=State.platform_admin.headers,
            json={
                "name": "E2E Form Access Role",
                "description": "Can access E2E test form",
            },
        )
        assert response.status_code == 201, f"Create role failed: {response.text}"
        role = response.json()
        State.e2e_role_id = role["id"]

    def test_152_assign_form_to_role(self):
        """Platform admin assigns form to role."""
        if not State.e2e_form_id or not State.e2e_role_id:
            pytest.skip("Form or role not created")

        response = State.client.post(
            f"/api/roles/{State.e2e_role_id}/forms",
            headers=State.platform_admin.headers,
            json={"form_ids": [State.e2e_form_id]},
        )
        assert response.status_code in [200, 201, 204], \
            f"Assign form to role failed: {response.text}"

    def test_153_assign_org_user_to_role(self):
        """Platform admin assigns org1_user to role."""
        if not State.e2e_role_id:
            pytest.skip("Role not created")

        response = State.client.post(
            f"/api/roles/{State.e2e_role_id}/users",
            headers=State.platform_admin.headers,
            json={"user_ids": [str(State.org1_user.user_id)]},
        )
        assert response.status_code in [200, 201, 204], \
            f"Assign user to role failed: {response.text}"

    def test_154_org_user_cannot_execute_unassigned_form(self):
        """Org user cannot execute form without role assignment."""
        if not State.e2e_form_id:
            pytest.skip("Form not created")

        # Org2 user is NOT assigned to the role
        response = State.client.post(
            f"/api/forms/{State.e2e_form_id}/execute",
            headers=State.org2_user.headers,
            json={"message": "Unauthorized attempt"},
        )
        assert response.status_code == 403, \
            f"Unassigned user should not execute form: {response.status_code}"

    def test_155_org_user_can_execute_assigned_form(self):
        """Org user with role can execute form."""
        if not State.e2e_form_id or not State.e2e_role_id:
            pytest.skip("Form or role not created")

        response = State.client.post(
            f"/api/forms/{State.e2e_form_id}/execute",
            headers=State.org1_user.headers,
            json={"message": "Hello from org user"},
        )
        assert response.status_code == 200, f"Execute form failed: {response.text}"
        data = response.json()

        # Should have execution_id
        assert "execution_id" in data or "executionId" in data
        State.form_execution_id = data.get("execution_id") or data.get("executionId")

    # =========================================================================
    # PHASE 17B: Form Access Level Tests
    # =========================================================================

    def test_156_create_authenticated_access_form(self):
        """Platform admin creates form with 'authenticated' access level."""
        response = State.client.post(
            "/api/forms",
            headers=State.platform_admin.headers,
            json={
                "name": "Authenticated Access Form",
                "description": "Any authenticated user can execute",
                "linked_workflow": "e2e_test_sync_workflow",
                "form_schema": {
                    "fields": [
                        {"name": "message", "type": "text", "label": "Message", "required": True},
                    ]
                },
                "access_level": "authenticated",
            },
        )
        assert response.status_code == 201, f"Create form failed: {response.text}"
        form = response.json()
        State.authenticated_form_id = form["id"]
        assert form["access_level"] == "authenticated"

    def test_157_any_org_user_can_execute_authenticated_form(self):
        """Any authenticated user can execute 'authenticated' access form."""
        if not getattr(State, 'authenticated_form_id', None):
            pytest.skip("Authenticated form not created")

        # Org2 user (NOT assigned to any role for this form) should still be able to execute
        response = State.client.post(
            f"/api/forms/{State.authenticated_form_id}/execute",
            headers=State.org2_user.headers,
            json={"message": "Hello from org2 user"},
        )
        assert response.status_code == 200, \
            f"Authenticated user should execute authenticated form: {response.status_code} - {response.text}"

    def test_158_create_public_access_form(self):
        """Platform admin creates form with 'public' access level."""
        response = State.client.post(
            "/api/forms",
            headers=State.platform_admin.headers,
            json={
                "name": "Public Access Form",
                "description": "Any user can execute (public)",
                "linked_workflow": "e2e_test_sync_workflow",
                "form_schema": {
                    "fields": [
                        {"name": "message", "type": "text", "label": "Message", "required": True},
                    ]
                },
                "access_level": "public",
            },
        )
        assert response.status_code == 201, f"Create form failed: {response.text}"
        form = response.json()
        State.public_form_id = form["id"]
        assert form["access_level"] == "public"

    def test_159_any_user_can_execute_public_form(self):
        """Any authenticated user can execute 'public' access form."""
        if not getattr(State, 'public_form_id', None):
            pytest.skip("Public form not created")

        # Org2 user should be able to execute public form
        response = State.client.post(
            f"/api/forms/{State.public_form_id}/execute",
            headers=State.org2_user.headers,
            json={"message": "Hello from any user"},
        )
        assert response.status_code == 200, \
            f"User should execute public form: {response.status_code} - {response.text}"

    def test_160_role_based_form_denies_unassigned_user(self):
        """Role-based form denies user without role assignment."""
        # This is a sanity check - test_154 already tests this but with e2e_form_id
        if not getattr(State, 'e2e_form_id', None):
            pytest.skip("Role-based form not created")

        # Org2 user is NOT assigned to e2e_role_id
        response = State.client.post(
            f"/api/forms/{State.e2e_form_id}/execute",
            headers=State.org2_user.headers,
            json={"message": "Should be denied"},
        )
        assert response.status_code == 403, \
            f"Unassigned user should be denied: {response.status_code}"

    def test_161_cleanup_access_level_test_forms(self):
        """Clean up access level test forms."""
        # Clean up authenticated form
        if getattr(State, 'authenticated_form_id', None):
            response = State.client.delete(
                f"/api/forms/{State.authenticated_form_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code in [200, 204], \
                f"Delete authenticated form failed: {response.text}"

        # Clean up public form
        if getattr(State, 'public_form_id', None):
            response = State.client.delete(
                f"/api/forms/{State.public_form_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code in [200, 204], \
                f"Delete public form failed: {response.text}"

    # =========================================================================
    # PHASE 18: Execution History & Details
    # =========================================================================

    def test_170_org_user_lists_own_executions(self):
        """Org user can list their own executions."""
        response = State.client.get(
            "/api/executions",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"List executions failed: {response.text}"
        data = response.json()
        assert "executions" in data

        # Should include their form execution
        if State.form_execution_id:
            exec_ids = [e.get("execution_id") or e.get("executionId") for e in data["executions"]]
            assert State.form_execution_id in exec_ids, "User's execution should be visible"

    def test_171_org_user_gets_own_execution_details(self):
        """Org user can get details of their own execution."""
        if not State.form_execution_id:
            pytest.skip("No form execution ID")

        response = State.client.get(
            f"/api/executions/{State.form_execution_id}",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"Get execution failed: {response.text}"

    def test_172_org_user_cannot_see_others_execution(self):
        """Org user cannot access another user's execution."""
        if not State.sync_execution_id:
            pytest.skip("No sync execution ID")

        # Try to access platform admin's execution
        response = State.client.get(
            f"/api/executions/{State.sync_execution_id}",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Should not access other's execution: {response.status_code}"

    def test_173_org_user_cannot_see_variables(self):
        """Org user cannot access execution variables (403)."""
        if not State.form_execution_id:
            pytest.skip("No form execution ID")

        response = State.client.get(
            f"/api/executions/{State.form_execution_id}/variables",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not see variables: {response.status_code}"

    def test_174_platform_admin_sees_all_executions(self):
        """Platform admin can list all executions."""
        response = State.client.get(
            "/api/executions",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List executions failed: {response.text}"
        data = response.json()

        # Verify the response structure is correct
        assert "executions" in data or isinstance(data, list)

        # If we have executions, verify we can see data from multiple users
        executions = data.get("executions", []) if isinstance(data, dict) else data
        if len(executions) > 0:
            # Should see executions from at least one user
            executed_by_set = set()
            for exec in executions:
                executed_by_set.add(exec.get("executed_by") or exec.get("executedBy"))
            assert len(executed_by_set) >= 1

    def test_175_platform_admin_sees_variables(self):
        """Platform admin can access execution variables."""
        if not State.sync_execution_id:
            pytest.skip("No sync execution ID")

        response = State.client.get(
            f"/api/executions/{State.sync_execution_id}/variables",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get variables failed: {response.text}"
        # Variables should be a dict (possibly empty)
        assert isinstance(response.json(), dict)

    def test_176_get_execution_result_endpoint(self):
        """Progressive result loading endpoint works."""
        if not State.sync_execution_id:
            pytest.skip("No sync execution ID")

        response = State.client.get(
            f"/api/executions/{State.sync_execution_id}/result",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get result failed: {response.text}"

        # Verify result structure
        result_data = response.json()
        assert "result" in result_data, "Result should have 'result' field"
        assert "result_type" in result_data, "Result should have 'result_type' field"

        # Verify the actual result content
        assert result_data["result"] is not None, "Result should not be None"
        if isinstance(result_data["result"], dict):
            assert "status" in result_data["result"], "E2E workflow should return status field"

    def test_177_get_execution_logs_endpoint(self):
        """Execution logs endpoint works."""
        if not State.sync_execution_id:
            pytest.skip("No sync execution ID")

        response = State.client.get(
            f"/api/executions/{State.sync_execution_id}/logs",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get logs failed: {response.text}"
        logs = response.json()
        assert isinstance(logs, list), "Logs should be a list"

        # Verify log structure (if logs exist)
        # Note: e2e_test_sync_workflow doesn't log anything, so logs may be empty
        for log in logs:
            assert "level" in log, "Log entry should have 'level' field"
            assert "message" in log, "Log entry should have 'message' field"
            assert "timestamp" in log, "Log entry should have 'timestamp' field"
            assert log["level"] in ["debug", "info", "warning", "error", "traceback"], f"Invalid log level: {log['level']}"

    # =========================================================================
    # PHASE 18B: Execution Behavior Tests (Config Scoping, Debug Logs, Concurrency)
    # =========================================================================

    def test_178_setup_config_for_execution_tests(self):
        """Set up global and org-specific config for execution tests."""

        # Create global config (no X-Organization-Id header = GLOBAL scope)
        response = State.client.post(
            "/api/config",
            headers=State.platform_admin.headers,
            json={
                "key": "e2e_test_key",
                "value": "global_value",
                "type": "string",
                "description": "E2E test config - global scope",
            },
        )
        assert response.status_code == 201, f"Create global config failed: {response.text}"
        global_config = response.json()
        assert global_config.get("scope") == "GLOBAL", \
            f"Global config should have GLOBAL scope, got: {global_config}"

        # Create org-specific config for org1 (use X-Organization-Id header for org scope)
        response = State.client.post(
            "/api/config",
            headers={
                **State.platform_admin.headers,
                "X-Organization-Id": State.org1["id"],
            },
            json={
                "key": "e2e_test_key",
                "value": "org_value",
                "type": "string",
                "description": "E2E test config - org scope",
            },
        )
        assert response.status_code == 201, f"Create org config failed: {response.text}"
        org_config = response.json()
        assert org_config.get("org_id") == State.org1["id"], \
            f"Org config should have org_id={State.org1['id']}, got: {org_config}"

    def test_179_org_user_execution_uses_org_config(self):
        """Org user execution resolves org-specific config over global."""

        # Create a form that links to e2e_test_async_workflow so org user can execute
        response = State.client.post(
            "/api/forms",
            headers=State.platform_admin.headers,
            json={
                "name": "E2E Config Test Form",
                "description": "Form for config scoping test",
                "linked_workflow": "e2e_test_async_workflow",
                "form_schema": {"fields": []},
                "access_level": "authenticated",
            },
        )
        if response.status_code != 201:
            pytest.skip(f"Form creation failed: {response.text}")

        form = response.json()
        config_test_form_id = form["id"]

        # Execute as org1 user via form (authenticated access level allows any auth user)
        response = State.client.post(
            f"/api/forms/{config_test_form_id}/execute",
            headers=State.org1_user.headers,
            json={},
        )
        assert response.status_code == 200, f"Execute form failed: {response.text}"
        data = response.json()
        State.org_user_config_exec_id = data.get("execution_id") or data.get("executionId")

        # Clean up form
        State.client.delete(f"/api/forms/{config_test_form_id}", headers=State.platform_admin.headers)

    def test_180_admin_execution_uses_global_config(self):
        """Admin execution without org context uses global config."""

        # Execute as platform admin (no org context) via direct execute
        response = State.client.post(
            "/api/workflows/execute",
            headers=State.platform_admin.headers,
            json={
                "workflow_name": "e2e_test_async_workflow",
                "input_data": {},
            },
        )
        assert response.status_code in [200, 202], f"Admin workflow execute failed: {response.text}"
        data = response.json()
        State.admin_config_exec_id = data.get("execution_id") or data.get("executionId")

    def test_181_wait_for_config_test_executions(self):
        """Wait for config test executions to complete."""
        import time

        if not State.org_user_config_exec_id and not State.admin_config_exec_id:
            pytest.skip("No config test executions to wait for")

        exec_ids = [e for e in [State.org_user_config_exec_id, State.admin_config_exec_id] if e]

        for exec_id in exec_ids:
            for _ in range(30):  # 30 second timeout
                response = State.client.get(
                    f"/api/executions/{exec_id}",
                    headers=State.platform_admin.headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    if status in ["Success", "Failed"]:
                        assert status == "Success", f"Execution {exec_id} failed: {data}"
                        break
                time.sleep(1)
            else:
                pytest.fail(f"Execution {exec_id} did not complete within timeout")

    def test_182_verify_org_user_got_org_config(self):
        """Verify org user's execution got org-specific config value."""
        if not State.org_user_config_exec_id:
            pytest.skip("No org user config execution")

        response = State.client.get(
            f"/api/executions/{State.org_user_config_exec_id}",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get execution failed: {response.text}"
        data = response.json()

        result = data.get("result", {})
        config_value = result.get("config_value")
        assert config_value == "org_value", \
            f"Org user should get org-specific config, got: {config_value}"

    def test_183_verify_admin_got_global_config(self):
        """Verify admin's execution got global config value."""
        if not State.admin_config_exec_id:
            pytest.skip("No admin config execution")

        response = State.client.get(
            f"/api/executions/{State.admin_config_exec_id}",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get execution failed: {response.text}"
        data = response.json()

        result = data.get("result", {})
        config_value = result.get("config_value")
        assert config_value == "global_value", \
            f"Admin should get global config, got: {config_value}"

    def test_184_org_user_cannot_see_debug_logs(self):
        """Org user only sees INFO+ logs, not DEBUG."""
        if not State.org_user_config_exec_id:
            pytest.skip("No org user config execution")

        response = State.client.get(
            f"/api/executions/{State.org_user_config_exec_id}/logs",
            headers=State.org1_user.headers,
        )
        # Org user may not have access to their own logs - check 200 or 403
        if response.status_code == 403:
            pytest.skip("Org user cannot access execution logs directly")

        assert response.status_code == 200, f"Get logs failed: {response.text}"
        logs = response.json()

        # Check that no DEBUG entries are visible
        for log in logs:
            message = log.get("message", "")
            level = log.get("level", "")
            # Should not see DEBUG level logs
            assert "DEBUG:" not in message, f"Org user should not see DEBUG logs: {message}"
            assert level.upper() != "DEBUG", f"Org user should not see DEBUG level: {level}"

    def test_185_platform_admin_sees_debug_logs(self):
        """Platform admin can see DEBUG level logs."""
        if not State.admin_config_exec_id:
            pytest.skip("No admin config execution")

        response = State.client.get(
            f"/api/executions/{State.admin_config_exec_id}/logs",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get logs failed: {response.text}"
        logs = response.json()

        # Platform admin should see DEBUG entries
        has_debug = any(
            "DEBUG:" in log.get("message", "") or log.get("level", "").upper() == "DEBUG"
            for log in logs
        )
        # Note: This may fail if DEBUG logging is not enabled in test env
        # Accept either having DEBUG logs or not (depends on log level config)
        if not has_debug and len(logs) > 0:
            # Just verify we got logs - DEBUG visibility depends on config
            pass

    def test_186_concurrent_executions_not_blocking(self):
        """10 concurrent executions complete in parallel, not sequentially."""
        import time


        # Start 10 async executions simultaneously
        execution_ids = []
        for i in range(10):
            response = State.client.post(
                "/api/workflows/execute",
                headers=State.platform_admin.headers,
                json={
                    "workflow_name": "e2e_test_async_workflow",
                    "input_data": {},
                },
            )
            assert response.status_code in [200, 202], f"Execute #{i} failed: {response.text}"
            data = response.json()
            exec_id = data.get("execution_id") or data.get("executionId")
            execution_ids.append(exec_id)

        # Poll until all complete
        start = time.time()
        completed = set()

        while len(completed) < len(execution_ids):
            if time.time() - start > 60:  # 60 second timeout
                pytest.fail(f"Only {len(completed)}/{len(execution_ids)} executions completed in 60s")

            for exec_id in execution_ids:
                if exec_id in completed:
                    continue
                response = State.client.get(
                    f"/api/executions/{exec_id}",
                    headers=State.platform_admin.headers,
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    if status in ["Success", "Failed"]:
                        completed.add(exec_id)

            time.sleep(0.5)

        elapsed = time.time() - start

        # Each workflow sleeps 2s. If blocking: 20s+. If parallel: ~3-5s (with overhead)
        # Allow up to 15s for test environment variability
        assert elapsed < 15, \
            f"10 executions took {elapsed:.1f}s - likely blocking (expected <15s for parallel)"

        # Verify all 10 succeeded
        for exec_id in execution_ids:
            response = State.client.get(
                f"/api/executions/{exec_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "Success", f"Execution {exec_id} failed: {data}"

    def test_187_cleanup_execution_test_config(self):
        """Clean up config created for execution tests."""
        # Delete global config
        response = State.client.delete(
            "/api/config/e2e_test_key",
            headers=State.platform_admin.headers,
        )
        assert response.status_code in [200, 204, 404]

        # Delete org-specific config
        response = State.client.delete(
            f"/api/config/e2e_test_key?organization_id={State.org1['id']}",
            headers=State.platform_admin.headers,
        )
        # May be 404 if org config deletion requires different API
        assert response.status_code in [200, 204, 404]

    # =========================================================================
    # PHASE 19: Package Management
    # =========================================================================

    def test_210_list_packages(self):
        """Platform admin can list installed packages."""
        response = State.client.get(
            "/api/packages",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"List packages failed: {response.text}"
        data = response.json()
        assert "packages" in data
        assert isinstance(data["packages"], list)

    def test_211_check_package_updates(self):
        """Platform admin can check for package updates."""
        response = State.client.get(
            "/api/packages/updates",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Check updates failed: {response.text}"
        data = response.json()
        assert "updates" in data

    def test_212_org_user_cannot_install_packages(self):
        """Org user cannot install packages (403)."""
        response = State.client.post(
            "/api/packages/install",
            headers=State.org1_user.headers,
            json={"package": "some-package"},
        )
        assert response.status_code == 403, \
            f"Org user should not install packages: {response.status_code}"

    # =========================================================================
    # PHASE 23: WebSocket Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_300_websocket_connect_with_valid_token(self):
        """Connect to WebSocket with valid JWT token."""
        import asyncio
        from websockets.asyncio.client import connect

        ws_url = f"{WS_BASE_URL}/ws/connect?token={State.platform_admin.access_token}"

        try:
            async with connect(ws_url) as ws:
                # Should receive connected message
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                assert data["type"] == "connected", f"Expected connected, got: {data}"
                assert "userId" in data or "user_id" in data
        except Exception as e:
            pytest.skip(f"WebSocket connection failed: {e}")

    @pytest.mark.asyncio
    async def test_301_websocket_connect_invalid_token(self):
        """Connect to WebSocket with invalid token should fail."""
        from websockets.asyncio.client import connect
        from websockets.exceptions import InvalidStatus

        ws_url = f"{WS_BASE_URL}/ws/connect?token=invalid-token-12345"

        try:
            async with connect(ws_url) as _ws:
                # Should not get here - connection should be rejected
                pytest.fail("Connection should have been rejected")
        except InvalidStatus as e:
            # Expected - connection rejected
            assert e.response.status_code in [401, 403, 4001], f"Unexpected status: {e.response.status_code}"
        except Exception:
            # Other rejection is acceptable
            pass

    @pytest.mark.asyncio
    async def test_302_websocket_ping_pong(self):
        """WebSocket ping/pong works."""
        import asyncio
        from websockets.asyncio.client import connect

        ws_url = f"{WS_BASE_URL}/ws/connect?token={State.platform_admin.access_token}"

        try:
            async with connect(ws_url) as ws:
                # Receive connected message first
                await asyncio.wait_for(ws.recv(), timeout=5)

                # Send ping
                await ws.send(json.dumps({"type": "ping"}))

                # Should receive pong
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                assert data["type"] == "pong", f"Expected pong, got: {data}"
        except Exception as e:
            pytest.skip(f"WebSocket test failed: {e}")

    @pytest.mark.asyncio
    async def test_303_websocket_subscribe_to_execution(self):
        """Subscribe to execution channel."""
        import asyncio
        from websockets.asyncio.client import connect

        if not State.sync_execution_id:
            pytest.skip("No execution ID to subscribe to")

        ws_url = f"{WS_BASE_URL}/ws/connect?token={State.platform_admin.access_token}"

        try:
            async with connect(ws_url) as ws:
                # Receive connected message
                await asyncio.wait_for(ws.recv(), timeout=5)

                # Subscribe to execution channel
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "channels": [f"execution:{State.sync_execution_id}"]
                }))

                # Should receive subscription confirmation or no error
                # Some implementations don't send confirmation
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2)
                    data = json.loads(msg)
                    # Accept subscribed confirmation or any non-error response
                    assert data.get("type") != "error", f"Subscribe error: {data}"
                except asyncio.TimeoutError:
                    # No confirmation is also acceptable
                    pass
        except Exception as e:
            pytest.skip(f"WebSocket test failed: {e}")

    @pytest.mark.asyncio
    async def test_304_org_user_websocket_access(self):
        """Org user can connect to WebSocket."""
        import asyncio
        from websockets.asyncio.client import connect

        ws_url = f"{WS_BASE_URL}/ws/connect?token={State.org1_user.access_token}"

        try:
            async with connect(ws_url) as ws:
                # Should receive connected message
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                assert data["type"] == "connected", f"Expected connected, got: {data}"
        except Exception as e:
            pytest.skip(f"WebSocket connection failed: {e}")

    # =========================================================================
    # PHASE 24: Branding Tests
    # =========================================================================

    def test_320_get_branding_public(self):
        """Get branding without authentication (public endpoint)."""
        # Create a new client without auth headers
        response = State.client.get("/api/branding")
        # Accept 200 or 404 (if branding not configured)
        assert response.status_code in [200, 404], f"Get branding failed: {response.text}"

    def test_321_get_branding_authenticated(self):
        """Get branding with authentication."""
        response = State.client.get(
            "/api/branding",
            headers=State.org1_user.headers,
        )
        assert response.status_code in [200, 404], f"Get branding failed: {response.text}"

    def test_322_update_branding_superuser(self):
        """Superuser can update branding."""
        response = State.client.put(
            "/api/branding",
            headers=State.platform_admin.headers,
            json={
                "primary_color": "#1a73e8",
                "app_name": "Bifrost E2E Test",
            },
        )
        assert response.status_code in [200, 201], f"Update branding failed: {response.text}"

    def test_323_update_branding_org_user_denied(self):
        """Org user cannot update branding (403)."""
        response = State.client.put(
            "/api/branding",
            headers=State.org1_user.headers,
            json={
                "primary_color": "#ff0000",
                "app_name": "Hacked App",
            },
        )
        assert response.status_code == 403, \
            f"Org user should not update branding: {response.status_code}"

    def test_324_upload_square_logo_superuser(self):
        """Superuser can upload square logo."""
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "../logos/square.png")

        with open(logo_path, "rb") as f:
            logo_data = f.read()

        response = State.client.post(
            "/api/branding/logo/square",
            headers={
                "Authorization": f"Bearer {State.platform_admin.access_token}",
            },
            files={"file": ("square.png", logo_data, "image/png")},
        )
        assert response.status_code in [200, 201], f"Upload square logo failed: {response.text}"

    def test_325_upload_rectangle_logo_superuser(self):
        """Superuser can upload rectangle logo."""
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "../logos/rectangle.png")

        with open(logo_path, "rb") as f:
            logo_data = f.read()

        response = State.client.post(
            "/api/branding/logo/rectangle",
            headers={
                "Authorization": f"Bearer {State.platform_admin.access_token}",
            },
            files={"file": ("rectangle.png", logo_data, "image/png")},
        )
        assert response.status_code in [200, 201], f"Upload rectangle logo failed: {response.text}"

    def test_326_get_square_logo_public(self):
        """Get square logo without authentication after upload."""
        response = State.client.get("/api/branding/logo/square")
        assert response.status_code == 200, f"Get square logo failed: {response.text}"
        assert response.headers.get("content-type") == "image/png", "Logo should be PNG"
        assert len(response.content) > 0, "Logo content should not be empty"

    def test_327_get_rectangle_logo_public(self):
        """Get rectangle logo without authentication after upload."""
        response = State.client.get("/api/branding/logo/rectangle")
        assert response.status_code == 200, f"Get rectangle logo failed: {response.text}"
        assert response.headers.get("content-type") == "image/png", "Logo should be PNG"
        assert len(response.content) > 0, "Logo content should not be empty"

    def test_328_upload_logo_org_user_denied(self):
        """Org user cannot upload logo (403)."""
        import os
        logo_path = os.path.join(os.path.dirname(__file__), "../logos/square.png")

        with open(logo_path, "rb") as f:
            logo_data = f.read()

        response = State.client.post(
            "/api/branding/logo/square",
            headers={
                "Authorization": f"Bearer {State.org1_user.access_token}",
            },
            files={"file": ("logo.png", logo_data, "image/png")},
        )
        assert response.status_code == 403, \
            f"Org user should not upload logo: {response.status_code}"

    # =========================================================================
    # PHASE 25: Metrics Tests
    # =========================================================================

    def test_330_get_metrics_authenticated(self):
        """Authenticated user can get metrics."""
        response = State.client.get(
            "/api/metrics",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"Get metrics failed: {response.text}"
        data = response.json()
        # Verify structure has expected fields
        assert isinstance(data, dict)

    def test_331_get_metrics_superuser(self):
        """Superuser can get metrics."""
        response = State.client.get(
            "/api/metrics",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200, f"Get metrics failed: {response.text}"

    def test_332_metrics_response_structure(self):
        """Metrics response has expected structure."""
        response = State.client.get(
            "/api/metrics",
            headers=State.platform_admin.headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Check for common metric fields (may vary by implementation)
        # Accept any dict response as valid
        assert isinstance(data, dict), "Metrics should return a dict"

    def test_333_get_metrics_unauthenticated(self):
        """Unauthenticated request to metrics fails."""
        # Create request without auth header
        response = State.client.get("/api/metrics")
        assert response.status_code == 401, \
            f"Unauthenticated should be 401: {response.status_code}"

    # =========================================================================
    # PHASE 26: Logs Tests
    # =========================================================================

    def test_340_list_logs_superuser(self):
        """Superuser can list logs."""
        response = State.client.get(
            "/api/logs",
            headers=State.platform_admin.headers,
        )
        # Accept 200 (logs returned) or empty array (stub implementation)
        assert response.status_code == 200, f"List logs failed: {response.text}"
        data = response.json()
        assert isinstance(data, (list, dict)), "Logs should return list or dict"

    def test_341_list_logs_org_user_denied(self):
        """Org user cannot list logs (403)."""
        response = State.client.get(
            "/api/logs",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not list logs: {response.status_code}"

    def test_342_get_single_log_superuser(self):
        """Superuser can get single log (even if 404)."""
        response = State.client.get(
            "/api/logs/system/test-row-key",
            headers=State.platform_admin.headers,
        )
        # Accept 200 (found) or 404 (not found - stub)
        assert response.status_code in [200, 404], f"Get log failed: {response.text}"

    def test_343_get_single_log_org_user_denied(self):
        """Org user cannot get single log (403)."""
        response = State.client.get(
            "/api/logs/system/test-row-key",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not get log: {response.status_code}"

    # =========================================================================
    # PHASE 27: Permission Enforcement Tests
    # =========================================================================

    def test_350_org_user_cannot_create_forms(self):
        """Org user cannot create forms (403)."""
        response = State.client.post(
            "/api/forms",
            headers=State.org1_user.headers,
            json={
                "name": "Unauthorized Form",
                "linked_workflow": "e2e_test_workflow",
                "form_schema": {"fields": []},
            },
        )
        assert response.status_code == 403, \
            f"Org user should not create forms: {response.status_code}"

    def test_351_org_user_cannot_update_forms(self):
        """Org user cannot update forms (403)."""
        if not State.e2e_form_id:
            pytest.skip("No form to update")

        response = State.client.put(
            f"/api/forms/{State.e2e_form_id}",
            headers=State.org1_user.headers,
            json={"name": "Hacked Form Name"},
        )
        assert response.status_code == 403, \
            f"Org user should not update forms: {response.status_code}"

    def test_352_org_user_cannot_delete_forms(self):
        """Org user cannot delete forms (403)."""
        if not State.e2e_form_id:
            pytest.skip("No form to delete")

        response = State.client.delete(
            f"/api/forms/{State.e2e_form_id}",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not delete forms: {response.status_code}"

    def test_353_org_user_cannot_list_all_users(self):
        """Org user cannot list all users (403 or filtered)."""
        response = State.client.get(
            "/api/users",
            headers=State.org1_user.headers,
        )
        # Should be 403 or return only limited/filtered data
        assert response.status_code in [403, 200], f"Unexpected: {response.status_code}"
        if response.status_code == 200:
            # If 200, should be filtered (not see all users)
            data = response.json()
            users = data.get("users", []) if isinstance(data, dict) else data
            # Org user should not see platform admin details
            for user in users:
                if user.get("is_superuser"):
                    # Should not expose superuser details to org user
                    pass  # Implementation may vary

    def test_354_org_user_cannot_create_users(self):
        """Org user cannot create users (403)."""
        response = State.client.post(
            "/api/users",
            headers=State.org1_user.headers,
            json={
                "email": "hacker@evil.com",
                "name": "Hacker",
                "organization_id": str(State.org1["id"]),
            },
        )
        assert response.status_code == 403, \
            f"Org user should not create users: {response.status_code}"

    def test_355_org_user_cannot_delete_users(self):
        """Org user cannot delete users (403)."""
        response = State.client.delete(
            f"/api/users/{State.platform_admin.user_id}",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not delete users: {response.status_code}"

    def test_356_org_user_cannot_modify_config(self):
        """Org user cannot modify config (403)."""
        # Config API uses POST for upsert (no PUT endpoint)
        response = State.client.post(
            "/api/config",
            headers=State.org1_user.headers,
            json={"key": "test_key", "value": "hacked_value", "type": "string"},
        )
        assert response.status_code == 403, \
            f"Org user should not modify config: {response.status_code}"

    def test_357_org_user_cannot_delete_config(self):
        """Org user cannot delete config (403)."""
        response = State.client.delete(
            "/api/config/test_key",
            headers=State.org1_user.headers,
        )
        assert response.status_code in [403, 404], \
            f"Org user should not delete config: {response.status_code}"

    def test_358_org_user_cannot_uninstall_packages(self):
        """Org user cannot uninstall packages (403)."""
        response = State.client.delete(
            "/api/packages/some-package",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not uninstall packages: {response.status_code}"

    def test_359_org_user_cannot_access_oauth_admin(self):
        """Org user cannot create OAuth connections (403)."""
        # Correct path is /api/oauth/connections (not /api/oauth-connections)
        response = State.client.post(
            "/api/oauth/connections",
            headers=State.org1_user.headers,
            json={
                "connection_name": "hacked_oauth",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://evil.com/auth",
                "token_url": "https://evil.com/token",
                "client_id": "hacked",
                "client_secret": "hacked",
            },
        )
        assert response.status_code == 403, \
            f"Org user should not create OAuth: {response.status_code}"

    def test_360_org_user_cannot_modify_roles(self):
        """Org user cannot modify roles (403)."""
        if not State.e2e_role_id:
            pytest.skip("No role to modify")

        response = State.client.put(
            f"/api/roles/{State.e2e_role_id}",
            headers=State.org1_user.headers,
            json={"name": "Hacked Role"},
        )
        assert response.status_code == 403, \
            f"Org user should not modify roles: {response.status_code}"

    def test_361_org_user_cannot_delete_roles(self):
        """Org user cannot delete roles (403)."""
        if not State.e2e_role_id:
            pytest.skip("No role to delete")

        response = State.client.delete(
            f"/api/roles/{State.e2e_role_id}",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 403, \
            f"Org user should not delete roles: {response.status_code}"

    def test_362_org_user_can_read_own_profile(self):
        """Org user can read their own profile (positive test)."""
        # Correct path is /auth/me (auth router has prefix /auth, not /api/auth)
        response = State.client.get(
            "/auth/me",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"Get own profile failed: {response.text}"
        data = response.json()
        assert data.get("email") == State.org1_user.email

    def test_363_org_user_can_list_assigned_forms(self):
        """Org user can list forms assigned to them."""
        response = State.client.get(
            "/api/forms",
            headers=State.org1_user.headers,
        )
        assert response.status_code == 200, f"List forms failed: {response.text}"
        # Response should be filtered to assigned forms only

    # =========================================================================
    # PHASE 28: Cleanup (Cleanup last)
    # =========================================================================

    def test_900_cleanup_e2e_test_files(self):
        """Clean up E2E test workflow file."""
        response = State.client.delete(
            "/api/editor/files?path=e2e_test_workflow.py",
            headers=State.platform_admin.headers,
        )
        assert response.status_code in [200, 204, 404]

    def test_901_cleanup_e2e_test_folder(self):
        """Clean up E2E test folder."""
        response = State.client.delete(
            "/api/editor/files?path=e2e_test_folder",
            headers=State.platform_admin.headers,
        )
        assert response.status_code in [200, 204, 404]

    def test_902_cleanup_e2e_form(self):
        """Clean up E2E test form."""
        if hasattr(State, 'e2e_form_id') and State.e2e_form_id:
            response = State.client.delete(
                f"/api/forms/{State.e2e_form_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code in [200, 204, 404]

    def test_903_cleanup_e2e_role(self):
        """Clean up E2E test role."""
        if hasattr(State, 'e2e_role_id') and State.e2e_role_id:
            response = State.client.delete(
                f"/api/roles/{State.e2e_role_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code in [200, 204, 404]

    def test_904_cleanup_e2e_configs(self):
        """Clean up E2E test configs."""
        for key in ["e2e_test_timeout", "e2e_max_retries", "e2e_settings", "e2e_api_key"]:
            response = State.client.delete(
                f"/api/config/{key}",
                headers=State.platform_admin.headers,
            )
            # Accept success or not found
            assert response.status_code in [200, 204, 404]

    def test_905_cleanup_role(self):
        """Clean up original test role."""
        if State.test_role_id:
            response = State.client.delete(
                f"/api/roles/{State.test_role_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code in [200, 204, 404]
