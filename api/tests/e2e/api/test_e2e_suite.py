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
                "displayName": State.org1_user.name,
                "orgId": State.org1["id"],
                "isPlatformAdmin": False,
            },
        )
        assert response.status_code == 201, f"Create user failed: {response.text}"
        data = response.json()
        State.org1_user.user_id = UUID(data["id"])

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
                "displayName": State.org2_user.name,
                "orgId": State.org2["id"],
                "isPlatformAdmin": False,
            },
        )
        assert response.status_code == 201, f"Create user failed: {response.text}"
        data = response.json()
        State.org2_user.user_id = UUID(data["id"])

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

    def test_99_cleanup_role(self):
        """Clean up test role."""
        if State.test_role_id:
            response = State.client.delete(
                f"/api/roles/{State.test_role_id}",
                headers=State.platform_admin.headers,
            )
            assert response.status_code in [200, 204, 404]
