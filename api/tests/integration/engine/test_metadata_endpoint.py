"""
Integration tests for /admin/metadata endpoint
Tests that the metadata endpoint returns correct workflow and data provider information
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import azure.functions as func
import pytest

from functions.discovery import get_discovery_metadata


@pytest.fixture(scope="class", autouse=True)
def discover_workspace_workflows():
    """Discover and register workspace workflows before tests"""
    workspace_path = Path(__file__).parent.parent.parent.parent / "workspace"

    if workspace_path.exists():
        for py_file in workspace_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            relative_path = py_file.relative_to(workspace_path)
            module_parts = list(relative_path.parts[:-1]) + [py_file.stem]
            module_name = f"workspace.{'.'.join(module_parts)}"

            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    # Always create a new module instance to re-run decorators
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
            except Exception:
                pass

    yield


class TestMetadataEndpoint:
    """Test /admin/metadata endpoint"""

    def test_metadata_endpoint_returns_200(self):
        """Test that metadata endpoint returns 200 status"""
        # Create mock request
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        req.headers = {}

        # Call endpoint
        response = asyncio.run(get_discovery_metadata(req))

        assert response.status_code == 200
        assert response.mimetype == "application/json"

    def test_metadata_endpoint_returns_workflows(self):
        """Test that metadata endpoint returns workflows array"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        req.headers = {}
        response = asyncio.run(get_discovery_metadata(req))

        # Parse JSON response
        data = json.loads(response.get_body().decode())

        assert "workflows" in data
        assert isinstance(data["workflows"], list)
        assert len(data["workflows"]) >= 1  # At least user_onboarding

    def test_metadata_endpoint_returns_data_providers(self):
        """Test that metadata endpoint returns dataProviders array"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        response = asyncio.run(get_discovery_metadata(req))

        # Parse JSON response
        data = json.loads(response.get_body().decode())

        assert "dataProviders" in data
        assert isinstance(data["dataProviders"], list)

    def test_test_workflow_in_response(self):
        """Test that test_workflow is included in response"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        response = asyncio.run(get_discovery_metadata(req))

        data = json.loads(response.get_body().decode())
        workflows = data["workflows"]

        # Find test_workflow
        test_workflow = next(
            (w for w in workflows if w["name"] == "test_workflow"),
            None
        )

        assert test_workflow is not None
        assert test_workflow["description"] == "Simple test workflow for validation"
        assert test_workflow["category"] == "testing"
        assert "test" in test_workflow["tags"]
        assert test_workflow["executionMode"] == "sync"

    def test_workflow_parameters_formatted_correctly(self):
        """Test that workflow parameters are formatted correctly"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        response = asyncio.run(get_discovery_metadata(req))

        data = json.loads(response.get_body().decode())
        workflows = data["workflows"]

        # Get test_workflow
        test_workflow = next(
            (w for w in workflows if w["name"] == "test_workflow"),
            None
        )

        assert "parameters" in test_workflow
        parameters = test_workflow["parameters"]

        assert len(parameters) == 2

        # Check name parameter
        name_param = parameters[0]
        assert name_param["name"] == "name"
        assert name_param["type"] == "string"
        assert name_param["label"] == "Name"
        assert name_param["required"] is True
        assert "helpText" in name_param
        assert name_param["helpText"] == "Name to greet"

        # Check count parameter with default value
        count_param = parameters[1]
        assert count_param["name"] == "count"
        assert count_param["type"] == "int"
        assert count_param["label"] == "Count"
        assert count_param["required"] is False
        assert "defaultValue" in count_param
        assert count_param["defaultValue"] == 1
        assert "helpText" in count_param
        assert count_param["helpText"] == "Number of times to greet"

    def test_parameter_optional_fields_excluded_when_not_present(self):
        """Test that optional parameter fields are excluded when not present"""
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        response = asyncio.run(get_discovery_metadata(req))

        data = json.loads(response.get_body().decode())
        workflows = data["workflows"]

        test_workflow = next(
            (w for w in workflows if w["name"] == "test_workflow"),
            None
        )

        # name parameter should not have validation, dataProvider, or defaultValue
        name_param = test_workflow["parameters"][0]
        assert "validation" not in name_param
        assert "dataProvider" not in name_param
        assert "defaultValue" not in name_param

    def test_no_authentication_required(self):
        """Test that endpoint works without authentication"""
        # This endpoint should work without any auth headers
        req = Mock(spec=func.HttpRequest)
        req.headers = {}
        req.headers = {}

        response = asyncio.run(get_discovery_metadata(req))

        # Should still return 200
        assert response.status_code == 200
