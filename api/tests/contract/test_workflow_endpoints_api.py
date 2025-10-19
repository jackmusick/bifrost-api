"""
Contract tests for Workflow Endpoints API
Tests workflow endpoint configuration, HTTP method validation, and API key validation
"""

import hashlib
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from shared.models import (
    WorkflowMetadata,
    WorkflowParameter,
    WorkflowKey,
    WorkflowKeyCreateRequest,
)


# ==================== WORKFLOW METADATA ENDPOINT CONFIG TESTS ====================

class TestWorkflowMetadataEndpointConfig:
    """Test WorkflowMetadata endpoint configuration fields"""

    def test_metadata_endpoint_enabled(self):
        """Test workflow metadata with endpoint enabled"""
        metadata = WorkflowMetadata(
            name="test_workflow",
            description="Test workflow",
            endpointEnabled=True,
            allowedMethods=["POST", "GET"]
        )
        assert metadata.endpointEnabled is True
        assert metadata.allowedMethods == ["POST", "GET"]
        assert metadata.disableGlobalKey is False

    def test_metadata_endpoint_disabled_by_default(self):
        """Test that endpointEnabled defaults to False"""
        metadata = WorkflowMetadata(
            name="test_workflow",
            description="Test workflow"
        )
        assert metadata.endpointEnabled is False
        assert metadata.allowedMethods == ["POST"]  # Default
        assert metadata.disableGlobalKey is False

    def test_metadata_multiple_allowed_methods(self):
        """Test workflow with multiple HTTP methods"""
        metadata = WorkflowMetadata(
            name="crud_workflow",
            description="CRUD operations",
            endpointEnabled=True,
            allowedMethods=["GET", "POST", "PUT", "DELETE"]
        )
        assert len(metadata.allowedMethods) == 4
        assert set(metadata.allowedMethods) == {"GET", "POST", "PUT", "DELETE"}

    def test_metadata_disable_global_key(self):
        """Test disableGlobalKey flag in metadata"""
        metadata = WorkflowMetadata(
            name="secure_workflow",
            description="Secure workflow",
            endpointEnabled=True,
            allowedMethods=["POST"],
            disableGlobalKey=True
        )
        assert metadata.disableGlobalKey is True

    def test_metadata_public_endpoint(self):
        """Test publicEndpoint flag for unauthenticated webhooks"""
        metadata = WorkflowMetadata(
            name="webhook_receiver",
            description="Public webhook",
            endpointEnabled=True,
            allowedMethods=["POST"],
            publicEndpoint=True
        )
        assert metadata.publicEndpoint is True
        assert metadata.endpointEnabled is True

    def test_metadata_serialization(self):
        """Test that metadata can be serialized to JSON"""
        metadata = WorkflowMetadata(
            name="my_workflow",
            description="My workflow",
            endpointEnabled=True,
            allowedMethods=["POST"],
            disableGlobalKey=True
        )
        data = metadata.model_dump()
        assert data["name"] == "my_workflow"
        assert data["endpointEnabled"] is True
        assert data["allowedMethods"] == ["POST"]
        assert data["disableGlobalKey"] is True


# ==================== WORKFLOW KEY DISABLE GLOBAL KEY TESTS ====================

class TestWorkflowKeyDisableGlobalKey:
    """Test disableGlobalKey field on WorkflowKey models"""

    def test_workflow_key_disable_global_key_default_false(self):
        """Test that disableGlobalKey defaults to False"""
        key = WorkflowKey(
            hashedKey="test123",
            createdBy="user@example.com"
        )
        assert key.disableGlobalKey is False

    def test_workflow_key_disable_global_key_true(self):
        """Test disableGlobalKey can be set to True"""
        key = WorkflowKey(
            hashedKey="test123",
            createdBy="user@example.com",
            disableGlobalKey=True
        )
        assert key.disableGlobalKey is True

    def test_workflow_key_create_request_disable_global_key(self):
        """Test disableGlobalKey in WorkflowKeyCreateRequest"""
        request = WorkflowKeyCreateRequest(
            workflowId="workflow-1",
            disableGlobalKey=True
        )
        assert request.disableGlobalKey is True

    def test_workflow_key_create_request_workflow_specific_with_disable_global_key(self):
        """Test workflow-specific key with disable global key flag"""
        request = WorkflowKeyCreateRequest(
            workflowId="workflows.test_workflow",
            expiresInDays=90,
            disableGlobalKey=True
        )
        assert request.workflowId == "workflows.test_workflow"
        assert request.disableGlobalKey is True

    def test_workflow_key_create_request_global_key_ignore_disable_flag(self):
        """Test that disableGlobalKey is irrelevant for global keys"""
        # Global keys (workflowId=None) don't use disableGlobalKey, but it can be set
        request = WorkflowKeyCreateRequest(
            workflowId=None,  # Global key
            disableGlobalKey=True  # This has no effect for global keys
        )
        assert request.workflowId is None
        assert request.disableGlobalKey is True  # Field exists but is meaningless


# ==================== API KEY VALIDATION SCENARIOS ====================

class TestWorkflowKeyAuthenticationScenarios:
    """Test authentication scenarios with workflow-specific keys and global keys"""

    def test_workflow_key_hashing_consistency(self):
        """Test that API key hashing is consistent"""
        raw_key = "wk_test_key_12345"
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

        key = WorkflowKey(
            hashedKey=hashed_key,
            createdBy="user@example.com"
        )

        # Verify that hashing is deterministic
        assert key.hashedKey == hashed_key
        assert key.hashedKey == hashlib.sha256(raw_key.encode()).hexdigest()

    def test_workflow_key_workflow_specific_scoping(self):
        """Test workflow-specific key scoping"""
        key = WorkflowKey(
            hashedKey="specific_key_hash",
            createdBy="user@example.com",
            workflowId="workflows.important_workflow",
            disableGlobalKey=True
        )

        # This key should only work for this specific workflow
        assert key.workflowId == "workflows.important_workflow"
        assert key.disableGlobalKey is True

    def test_global_key_no_workflow_scope(self):
        """Test global key has no workflow scope"""
        key = WorkflowKey(
            hashedKey="global_key_hash",
            createdBy="admin@example.com",
            workflowId=None  # No specific workflow
        )

        # Global key can be used for any workflow
        assert key.workflowId is None
        assert key.disableGlobalKey is False  # Global key always allows global keys

    def test_workflow_key_revocation(self):
        """Test revoked key state"""
        revoked_time = datetime.utcnow()
        key = WorkflowKey(
            hashedKey="revoked_key_hash",
            createdBy="user@example.com",
            revoked=True,
            revokedAt=revoked_time,
            revokedBy="admin@example.com"
        )

        assert key.revoked is True
        assert key.revokedAt == revoked_time
        assert key.revokedBy == "admin@example.com"

    def test_workflow_key_expiration(self):
        """Test key expiration date"""
        expires_at = datetime.utcnow() + timedelta(days=90)
        key = WorkflowKey(
            hashedKey="expiring_key_hash",
            createdBy="user@example.com",
            expiresAt=expires_at
        )

        assert key.expiresAt == expires_at

    def test_workflow_key_last_used_tracking(self):
        """Test last used timestamp tracking"""
        now = datetime.utcnow()
        key = WorkflowKey(
            hashedKey="used_key_hash",
            createdBy="user@example.com",
            lastUsedAt=now
        )

        assert key.lastUsedAt == now


# ==================== HTTP METHOD VALIDATION ====================

class TestHttpMethodValidation:
    """Test HTTP method validation for workflow endpoints"""

    def test_single_method_allowed(self):
        """Test endpoint with single HTTP method allowed"""
        metadata = WorkflowMetadata(
            name="test",
            description="Test",
            endpointEnabled=True,
            allowedMethods=["POST"]
        )
        assert len(metadata.allowedMethods) == 1
        assert "POST" in metadata.allowedMethods

    def test_multiple_methods_allowed(self):
        """Test endpoint with multiple HTTP methods allowed"""
        metadata = WorkflowMetadata(
            name="test",
            description="Test",
            endpointEnabled=True,
            allowedMethods=["GET", "POST", "PUT"]
        )
        assert len(metadata.allowedMethods) == 3
        assert all(m in metadata.allowedMethods for m in ["GET", "POST", "PUT"])

    def test_all_methods_allowed(self):
        """Test endpoint with all HTTP methods allowed"""
        metadata = WorkflowMetadata(
            name="test",
            description="Test",
            endpointEnabled=True,
            allowedMethods=["GET", "POST", "PUT", "DELETE"]
        )
        assert len(metadata.allowedMethods) == 4
        assert metadata.allowedMethods == ["GET", "POST", "PUT", "DELETE"]

    def test_duplicate_methods_allowed(self):
        """Test that duplicate methods are accepted"""
        # Pydantic doesn't auto-deduplicate lists
        metadata = WorkflowMetadata(
            name="test",
            description="Test",
            endpointEnabled=True,
            allowedMethods=["POST", "POST", "GET"]
        )
        assert "POST" in metadata.allowedMethods
        assert "GET" in metadata.allowedMethods


# ==================== ENDPOINT CONFIGURATION SCENARIOS ====================

class TestEndpointConfigurationScenarios:
    """Test realistic endpoint configuration scenarios"""

    def test_read_only_endpoint(self):
        """Test configuration for read-only endpoint"""
        metadata = WorkflowMetadata(
            name="read_workflow",
            description="Read-only",
            endpointEnabled=True,
            allowedMethods=["GET"]
        )
        assert metadata.allowedMethods == ["GET"]
        assert len(metadata.allowedMethods) == 1

    def test_write_only_endpoint(self):
        """Test configuration for write-only endpoint"""
        metadata = WorkflowMetadata(
            name="write_workflow",
            description="Write-only",
            endpointEnabled=True,
            allowedMethods=["POST"]
        )
        assert metadata.allowedMethods == ["POST"]

    def test_crud_endpoint(self):
        """Test configuration for CRUD endpoint"""
        metadata = WorkflowMetadata(
            name="crud_workflow",
            description="CRUD operations",
            endpointEnabled=True,
            allowedMethods=["GET", "POST", "PUT", "DELETE"]
        )
        assert len(metadata.allowedMethods) == 4

    def test_update_methods_endpoint(self):
        """Test configuration for endpoint supporting updates"""
        metadata = WorkflowMetadata(
            name="update_workflow",
            description="Update operations",
            endpointEnabled=True,
            allowedMethods=["POST", "PUT"]
        )
        assert set(metadata.allowedMethods) == {"POST", "PUT"}

    def test_disabled_endpoint_still_valid(self):
        """Test that disabled endpoint is still valid"""
        metadata = WorkflowMetadata(
            name="disabled_workflow",
            description="Disabled endpoint",
            endpointEnabled=False,
            allowedMethods=["POST", "GET"]
        )
        assert metadata.endpointEnabled is False
        assert metadata.allowedMethods == ["POST", "GET"]

    def test_endpoint_with_global_key_disabled(self):
        """Test endpoint with global key disabled"""
        metadata = WorkflowMetadata(
            name="secure_workflow",
            description="Secure workflow",
            endpointEnabled=True,
            allowedMethods=["POST"],
            disableGlobalKey=True
        )
        assert metadata.disableGlobalKey is True

    def test_endpoint_with_global_key_enabled(self):
        """Test endpoint with global key enabled"""
        metadata = WorkflowMetadata(
            name="public_workflow",
            description="Public workflow",
            endpointEnabled=True,
            allowedMethods=["POST"],
            disableGlobalKey=False
        )
        assert metadata.disableGlobalKey is False
