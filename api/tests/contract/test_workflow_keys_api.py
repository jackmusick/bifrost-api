"""
Contract tests for Workflow Keys API (User Story 3)
Tests Pydantic validation for workflow API key generation, validation, and management
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from shared.models import (
    WorkflowKey,
    WorkflowKeyCreateRequest,
    WorkflowKeyResponse,
)


# ==================== WORKFLOW KEY MODEL TESTS ====================

class TestWorkflowKeyModel:
    """Test WorkflowKey model validation"""

    def test_workflow_key_with_all_fields(self):
        """Test WorkflowKey creation with all fields"""
        key = WorkflowKey(
            id="key-123",
            hashedKey="abc123def456",
            workflowId="workflow-1",
            createdBy="user@example.com",
            createdAt=datetime.utcnow(),
            lastUsedAt=datetime.utcnow(),
            revoked=False,
            revokedAt=None,
            revokedBy=None,
            expiresAt=datetime.utcnow() + timedelta(days=90),
            description="Test API Key"
        )
        assert key.hashedKey == "abc123def456"
        assert key.workflowId == "workflow-1"
        assert key.createdBy == "user@example.com"
        assert key.revoked is False
        assert key.description == "Test API Key"

    def test_workflow_key_minimal_fields(self):
        """Test WorkflowKey with only required fields"""
        key = WorkflowKey(
            hashedKey="abc123def456",
            createdBy="user@example.com"
        )
        assert key.hashedKey == "abc123def456"
        assert key.createdBy == "user@example.com"
        assert key.workflowId is None  # Optional
        assert key.revoked is False  # Default
        assert key.lastUsedAt is None  # Optional
        assert key.description is None  # Optional

    def test_workflow_key_global_scope(self):
        """Test global workflow key (workflowId is None)"""
        key = WorkflowKey(
            hashedKey="global123",
            createdBy="admin@example.com",
            workflowId=None
        )
        assert key.workflowId is None
        assert key.hashedKey == "global123"

    def test_workflow_key_workflow_specific(self):
        """Test workflow-specific key"""
        key = WorkflowKey(
            hashedKey="specific123",
            createdBy="user@example.com",
            workflowId="workflows.specific_workflow"
        )
        assert key.workflowId == "workflows.specific_workflow"
        assert key.hashedKey == "specific123"

    def test_workflow_key_revoked_state(self):
        """Test revoked workflow key"""
        revoked_time = datetime.utcnow()
        key = WorkflowKey(
            hashedKey="revoked123",
            createdBy="user@example.com",
            revoked=True,
            revokedAt=revoked_time,
            revokedBy="admin@example.com"
        )
        assert key.revoked is True
        assert key.revokedAt == revoked_time
        assert key.revokedBy == "admin@example.com"

    def test_workflow_key_with_expiration(self):
        """Test workflow key with expiration date"""
        expires_at = datetime.utcnow() + timedelta(days=30)
        key = WorkflowKey(
            hashedKey="expiring123",
            createdBy="user@example.com",
            expiresAt=expires_at
        )
        assert key.expiresAt == expires_at


# ==================== WORKFLOW KEY CREATE REQUEST TESTS ====================

class TestWorkflowKeyCreateRequest:
    """Test WorkflowKeyCreateRequest validation"""

    def test_create_global_key(self):
        """Test creating a global workflow key"""
        request = WorkflowKeyCreateRequest(
            workflowId=None,
            expiresInDays=None,
            description="Global API Key"
        )
        assert request.workflowId is None
        assert request.expiresInDays is None
        assert request.description == "Global API Key"

    def test_create_workflow_specific_key(self):
        """Test creating a workflow-specific key"""
        request = WorkflowKeyCreateRequest(
            workflowId="workflows.process_data",
            expiresInDays=90,
            description="Data Processing Key"
        )
        assert request.workflowId == "workflows.process_data"
        assert request.expiresInDays == 90
        assert request.description == "Data Processing Key"

    def test_create_key_minimal_request(self):
        """Test creating key with minimal request"""
        request = WorkflowKeyCreateRequest()
        assert request.workflowId is None
        assert request.expiresInDays is None
        assert request.description is None

    def test_create_key_with_expiration_only(self):
        """Test creating key with only expiration"""
        request = WorkflowKeyCreateRequest(
            expiresInDays=365
        )
        assert request.expiresInDays == 365
        assert request.workflowId is None

    def test_create_key_with_description_only(self):
        """Test creating key with only description"""
        request = WorkflowKeyCreateRequest(
            description="Production API Key"
        )
        assert request.description == "Production API Key"
        assert request.workflowId is None
        assert request.expiresInDays is None


# ==================== WORKFLOW KEY RESPONSE TESTS ====================

class TestWorkflowKeyResponse:
    """Test WorkflowKeyResponse validation"""

    def test_response_with_raw_key_on_creation(self):
        """Test response with raw key (only shown on creation)"""
        response = WorkflowKeyResponse(
            id="key-123",
            rawKey="wk_abcdef123456789",
            maskedKey=None,
            workflowId="workflows.test",
            createdBy="user@example.com",
            createdAt=datetime.utcnow(),
            lastUsedAt=None,
            revoked=False,
            expiresAt=None,
            description="Test Key"
        )
        assert response.rawKey == "wk_abcdef123456789"
        assert response.maskedKey is None  # Not shown with raw key

    def test_response_with_masked_key_on_list(self):
        """Test response with masked key (shown on list/get operations)"""
        response = WorkflowKeyResponse(
            id="key-123",
            rawKey=None,
            maskedKey="****6789",
            workflowId=None,
            createdBy="user@example.com",
            createdAt=datetime.utcnow(),
            lastUsedAt=datetime.utcnow(),
            revoked=False,
            expiresAt=None,
            description="Global Key"
        )
        assert response.rawKey is None  # Never shown after creation
        assert response.maskedKey == "****6789"

    def test_response_for_global_key(self):
        """Test response for global workflow key"""
        response = WorkflowKeyResponse(
            id="global-key-1",
            rawKey=None,
            maskedKey="****5678",
            workflowId=None,  # Global key
            createdBy="admin@example.com",
            createdAt=datetime.utcnow(),
            lastUsedAt=None,
            revoked=False
        )
        assert response.workflowId is None
        assert response.maskedKey == "****5678"

    def test_response_for_revoked_key(self):
        """Test response for revoked key"""
        response = WorkflowKeyResponse(
            id="revoked-key",
            rawKey=None,
            maskedKey="****1234",
            workflowId="workflows.test",
            createdBy="user@example.com",
            createdAt=datetime.utcnow(),
            lastUsedAt=datetime.utcnow() - timedelta(days=5),
            revoked=True,  # Revoked
            expiresAt=None,
            description="Revoked Test Key"
        )
        assert response.revoked is True
        assert response.maskedKey == "****1234"

    def test_response_with_all_optional_fields(self):
        """Test response with all optional fields populated"""
        created_at = datetime.utcnow()
        last_used = datetime.utcnow() - timedelta(hours=1)
        expires_at = datetime.utcnow() + timedelta(days=30)

        response = WorkflowKeyResponse(
            id="full-key",
            rawKey="wk_full123456",
            maskedKey=None,
            workflowId="workflows.full_test",
            createdBy="user@example.com",
            createdAt=created_at,
            lastUsedAt=last_used,
            revoked=False,
            expiresAt=expires_at,
            description="Full Test Key"
        )
        assert response.rawKey == "wk_full123456"
        assert response.workflowId == "workflows.full_test"
        assert response.lastUsedAt == last_used
        assert response.expiresAt == expires_at
        assert response.description == "Full Test Key"


# ==================== KEY SCOPE VALIDATION TESTS ====================

class TestWorkflowKeyScopeValidation:
    """Test workflow key scope validation logic"""

    def test_global_key_accepts_any_workflow(self):
        """Global key (workflowId=None) should work with any workflow"""
        key = WorkflowKey(
            hashedKey="global-key-hash",
            createdBy="admin@example.com",
            workflowId=None  # Global scope
        )
        # Global key should not have workflow restriction
        assert key.workflowId is None

    def test_workflow_specific_key_has_restriction(self):
        """Workflow-specific key should only work with specified workflow"""
        key = WorkflowKey(
            hashedKey="specific-key-hash",
            createdBy="user@example.com",
            workflowId="workflows.restricted"  # Workflow-specific
        )
        # Key should have workflow restriction
        assert key.workflowId == "workflows.restricted"


# ==================== KEY EXPIRATION TESTS ====================

class TestWorkflowKeyExpiration:
    """Test workflow key expiration validation"""

    def test_non_expiring_key(self):
        """Test key with no expiration (expiresAt=None)"""
        key = WorkflowKey(
            hashedKey="never-expires",
            createdBy="user@example.com",
            expiresAt=None
        )
        assert key.expiresAt is None

    def test_expiring_key_in_future(self):
        """Test key with future expiration"""
        future_expiration = datetime.utcnow() + timedelta(days=90)
        key = WorkflowKey(
            hashedKey="future-expires",
            createdBy="user@example.com",
            expiresAt=future_expiration
        )
        assert key.expiresAt == future_expiration
        # Key should be considered valid (not expired yet)
        assert key.expiresAt > datetime.utcnow()

    def test_expired_key(self):
        """Test key with past expiration"""
        past_expiration = datetime.utcnow() - timedelta(days=1)
        key = WorkflowKey(
            hashedKey="expired",
            createdBy="user@example.com",
            expiresAt=past_expiration
        )
        assert key.expiresAt == past_expiration
        # Key should be considered expired
        assert key.expiresAt < datetime.utcnow()


# ==================== KEY REGENERATION TESTS ====================

class TestWorkflowKeyRegeneration:
    """Test workflow key revocation and regeneration scenarios"""

    def test_revoke_and_create_new_key(self):
        """Test revoking old key and creating new one"""
        # Old key (revoked)
        old_key = WorkflowKey(
            hashedKey="old-key-hash",
            createdBy="user@example.com",
            workflowId="workflows.test",
            revoked=True,
            revokedAt=datetime.utcnow(),
            revokedBy="user@example.com"
        )

        # New key (active)
        new_key = WorkflowKey(
            hashedKey="new-key-hash",
            createdBy="user@example.com",
            workflowId="workflows.test",
            revoked=False
        )

        assert old_key.revoked is True
        assert new_key.revoked is False
        assert old_key.hashedKey != new_key.hashedKey
