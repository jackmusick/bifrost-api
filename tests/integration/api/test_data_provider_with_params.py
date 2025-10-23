"""
Integration tests for data providers with @param decorators (T021)
Tests that data providers with parameters execute correctly with inputs
"""

import pytest
import requests


class TestDataProviderWithParameters:
    """T021: Integration test for data provider with @param decorators"""

    def test_data_provider_without_inputs_returns_empty_or_default(
        self,
        api_base_url,
        auth_headers,
        test_org_id
    ):
        """
        Test calling a parameterized data provider without inputs.

        Expected behavior:
        - If provider has required parameters, should return 400
        - If provider has only optional parameters, should return 200 with defaults
        """
        # Call get_github_repos without required token parameter
        response = requests.post(
            f"{api_base_url}/api/data-providers/get_github_repos",
            headers=auth_headers,
            json={},
            timeout=10
        )

        # Should fail with 400 because 'token' parameter is required
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Required parameter 'token' is missing" in data.get("details", {}).get("errors", [""])[0]

    def test_data_provider_with_valid_inputs_executes_successfully(
        self,
        api_base_url,
        auth_headers,
        test_org_id
    ):
        """
        Test calling a data provider with valid input parameters.

        Expected behavior:
        - Provider executes successfully
        - Returns options list
        - Cache key includes input hash
        """
        # Call get_github_repos with required parameters
        response = requests.post(
            f"{api_base_url}/api/data-providers/get_github_repos",
            headers=auth_headers,
            json={
                "inputs": {
                    "token": "ghp_test_token_12345",
                    "org": "gocovi"
                }
            },
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["provider"] == "get_github_repos"
        assert "options" in data
        assert isinstance(data["options"], list)
        assert len(data["options"]) > 0

        # Verify options include repos for the specified org
        first_option = data["options"][0]
        assert "label" in first_option
        assert "value" in first_option
        assert "gocovi" in first_option["label"]  # Mock data includes org name

        # Verify cache metadata
        assert "cached" in data
        assert "cache_expires_at" in data
        assert data["cached"] is False  # First call

    def test_data_provider_with_different_inputs_returns_different_results(
        self,
        api_base_url,
        auth_headers,
        test_org_id
    ):
        """
        Test that different input values produce different results.

        Expected behavior:
        - Same provider with different inputs returns different options
        - Cache keys are different (no cache hit)
        """
        # Call 1: with org="gocovi"
        response1 = requests.post(
            f"{api_base_url}/api/data-providers/get_github_repos",
            headers=auth_headers,
            json={
                "inputs": {
                    "token": "ghp_test",
                    "org": "gocovi"
                }
            },
            timeout=10
        )

        # Call 2: with org="" (personal repos)
        response2 = requests.post(
            f"{api_base_url}/api/data-providers/get_github_repos",
            headers=auth_headers,
            json={
                "inputs": {
                    "token": "ghp_test",
                    "org": ""
                }
            },
            timeout=10
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Both should return options
        assert len(data1["options"]) > 0
        assert len(data2["options"]) > 0

        # Options should be different (org repos vs personal repos)
        assert data1["options"] != data2["options"]

        # Neither should be cached (different cache keys)
        assert data1["cached"] is False
        assert data2["cached"] is False

    def test_data_provider_cache_hit_with_same_inputs(
        self,
        api_base_url,
        auth_headers,
        test_org_id
    ):
        """
        Test that calling with same inputs hits cache.

        Expected behavior:
        - First call: cached=false
        - Second call with same inputs: cached=true
        """
        inputs = {
            "inputs": {
                "token": "ghp_cache_test",
                "org": "test-org"
            }
        }

        # Call 1: Fresh execution
        response1 = requests.post(
            f"{api_base_url}/api/data-providers/get_github_repos",
            headers=auth_headers,
            json=inputs,
            timeout=10
        )

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False

        # Call 2: Should hit cache
        response2 = requests.post(
            f"{api_base_url}/api/data-providers/get_github_repos",
            headers=auth_headers,
            json=inputs,
            timeout=10
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True

        # Results should be identical
        assert data1["options"] == data2["options"]
        assert data1["cache_expires_at"] == data2["cache_expires_at"]

    def test_data_provider_with_optional_parameter_uses_default(
        self,
        api_base_url,
        auth_headers,
        test_org_id
    ):
        """
        Test data provider with optional parameter.

        Expected behavior:
        - Optional parameter can be omitted
        - Default value is used when parameter not provided
        """
        # Call get_filtered_licenses without filter parameter (optional with default='all')
        response = requests.post(
            f"{api_base_url}/api/data-providers/get_filtered_licenses",
            headers=auth_headers,
            json={
                "inputs": {}  # No filter provided
            },
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        assert data["provider"] == "get_filtered_licenses"
        assert len(data["options"]) > 0  # Should return all licenses (default)

    def test_data_provider_with_multiple_required_params(
        self,
        api_base_url,
        auth_headers,
        test_org_id
    ):
        """
        Test data provider requiring multiple parameters.

        Expected behavior:
        - All required parameters must be provided
        - Missing any required parameter returns 400
        """
        # Call get_github_branches (requires both token and repo)

        # Missing 'repo' parameter
        response1 = requests.post(
            f"{api_base_url}/api/data-providers/get_github_branches",
            headers=auth_headers,
            json={
                "inputs": {
                    "token": "ghp_test"
                    # Missing 'repo'
                }
            },
            timeout=10
        )

        assert response1.status_code == 400
        data1 = response1.json()
        assert "Required parameter 'repo' is missing" in str(data1.get("details", {}).get("errors", []))

        # All required parameters provided
        response2 = requests.post(
            f"{api_base_url}/api/data-providers/get_github_branches",
            headers=auth_headers,
            json={
                "inputs": {
                    "token": "ghp_test",
                    "repo": "gocovi/bifrost-api"
                }
            },
            timeout=10
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["options"]) > 0
        assert any("main" in opt["label"] for opt in data2["options"])
