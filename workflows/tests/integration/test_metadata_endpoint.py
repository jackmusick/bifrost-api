"""
Integration tests for /admin/metadata endpoint
Tests that the metadata endpoint returns correct workflow and data provider information
"""

import pytest
import json
from unittest.mock import Mock

# Import to trigger auto-discovery
import workflows  # noqa: F401

from admin.metadata import get_metadata
import azure.functions as func


class TestMetadataEndpoint:
    """Test /admin/metadata endpoint"""

    def test_metadata_endpoint_returns_200(self):
        """Test that metadata endpoint returns 200 status"""
        # Create mock request
        req = Mock(spec=func.HttpRequest)

        # Call endpoint
        response = get_metadata(req)

        assert response.status_code == 200
        assert response.mimetype == "application/json"

    def test_metadata_endpoint_returns_workflows(self):
        """Test that metadata endpoint returns workflows array"""
        req = Mock(spec=func.HttpRequest)
        response = get_metadata(req)

        # Parse JSON response
        data = json.loads(response.get_body().decode())

        assert "workflows" in data
        assert isinstance(data["workflows"], list)
        assert len(data["workflows"]) >= 1  # At least user_onboarding

    def test_metadata_endpoint_returns_data_providers(self):
        """Test that metadata endpoint returns dataProviders array"""
        req = Mock(spec=func.HttpRequest)
        response = get_metadata(req)

        # Parse JSON response
        data = json.loads(response.get_body().decode())

        assert "dataProviders" in data
        assert isinstance(data["dataProviders"], list)

    def test_user_onboarding_workflow_in_response(self):
        """Test that user_onboarding workflow is included in response"""
        req = Mock(spec=func.HttpRequest)
        response = get_metadata(req)

        data = json.loads(response.get_body().decode())
        workflows = data["workflows"]

        # Find user_onboarding workflow
        user_onboarding = next(
            (w for w in workflows if w["name"] == "user_onboarding"),
            None
        )

        assert user_onboarding is not None
        assert user_onboarding["description"] == "Onboard new Microsoft 365 user with license assignment"
        assert user_onboarding["category"] == "user_management"
        assert "m365" in user_onboarding["tags"]
        assert user_onboarding["requiresOrg"] is True

    def test_workflow_parameters_formatted_correctly(self):
        """Test that workflow parameters are formatted correctly"""
        req = Mock(spec=func.HttpRequest)
        response = get_metadata(req)

        data = json.loads(response.get_body().decode())
        workflows = data["workflows"]

        # Get user_onboarding workflow
        user_onboarding = next(
            (w for w in workflows if w["name"] == "user_onboarding"),
            None
        )

        assert "parameters" in user_onboarding
        parameters = user_onboarding["parameters"]

        assert len(parameters) == 5

        # Check first_name parameter
        first_name = parameters[0]
        assert first_name["name"] == "first_name"
        assert first_name["type"] == "string"
        assert first_name["label"] == "First Name"
        assert first_name["required"] is True

        # Check email parameter with validation
        email = parameters[2]
        assert email["name"] == "email"
        assert email["type"] == "email"
        assert email["required"] is True
        assert "validation" in email
        assert "pattern" in email["validation"]

        # Check license parameter with data provider
        license_param = parameters[3]
        assert license_param["name"] == "license"
        assert license_param["dataProvider"] == "get_available_licenses"
        assert license_param["required"] is True

        # Check department parameter with default value
        department = parameters[4]
        assert department["name"] == "department"
        assert department["required"] is False
        assert "defaultValue" in department
        assert department["defaultValue"] == ""

    def test_parameter_optional_fields_excluded_when_not_present(self):
        """Test that optional parameter fields are excluded when not present"""
        req = Mock(spec=func.HttpRequest)
        response = get_metadata(req)

        data = json.loads(response.get_body().decode())
        workflows = data["workflows"]

        user_onboarding = next(
            (w for w in workflows if w["name"] == "user_onboarding"),
            None
        )

        # first_name parameter should not have validation, dataProvider, or defaultValue
        first_name = user_onboarding["parameters"][0]
        assert "validation" not in first_name
        assert "dataProvider" not in first_name
        assert "defaultValue" not in first_name

    def test_no_authentication_required(self):
        """Test that endpoint works without authentication"""
        # This endpoint should work without any auth headers
        req = Mock(spec=func.HttpRequest)
        req.headers = {}

        response = get_metadata(req)

        # Should still return 200
        assert response.status_code == 200
