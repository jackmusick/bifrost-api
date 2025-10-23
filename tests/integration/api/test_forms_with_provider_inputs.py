"""
Integration tests for forms with static dataProviderInputs (T022)
Tests that forms can be saved and validated with data provider inputs
"""

import pytest
import requests


class TestFormsWithDataProviderInputs:
    """T022: Integration test for form save with static dataProviderInputs"""

    def test_create_form_with_valid_static_inputs(
        self,
        api_base_url,
        platform_admin_headers
    ):
        """
        Test creating a form with valid static data provider inputs.

        Expected behavior:
        - Form creation succeeds with 201
        - Form saves with dataProviderInputs intact
        - Retrieved form includes dataProviderInputs
        """
        form_data = {
            "name": "Test Form with Data Provider Inputs",
            "description": "Integration test form",
            "linkedWorkflow": "test_workflow",
            "formSchema": {
                "fields": [
                    {
                        "name": "repo_selector",
                        "label": "Select Repository",
                        "type": "select",
                        "required": True,
                        "dataProvider": "get_github_repos",
                        "dataProviderInputs": {
                            "token": {
                                "mode": "static",
                                "value": "ghp_static_token_123"
                            },
                            "org": {
                                "mode": "static",
                                "value": "test-org"
                            }
                        }
                    }
                ]
            },
            "isPublic": True
        }

        # Create form
        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=platform_admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 201
        created_form = response.json()

        assert "id" in created_form
        form_id = created_form["id"]

        # Retrieve form and verify dataProviderInputs are preserved
        get_response = requests.get(
            f"{api_base_url}/api/forms/{form_id}",
            headers=platform_admin_headers,
            timeout=10
        )

        assert get_response.status_code == 200
        retrieved_form = get_response.json()

        # Verify dataProviderInputs are intact
        field = retrieved_form["formSchema"]["fields"][0]
        assert field["dataProvider"] == "get_github_repos"
        assert "dataProviderInputs" in field
        assert field["dataProviderInputs"]["token"]["mode"] == "static"
        assert field["dataProviderInputs"]["token"]["value"] == "ghp_static_token_123"
        assert field["dataProviderInputs"]["org"]["value"] == "test-org"

        # Cleanup
        requests.delete(
            f"{api_base_url}/api/forms/{form_id}",
            headers=platform_admin_headers,
            timeout=10
        )

    def test_create_form_missing_required_data_provider_params(
        self,
        api_base_url,
        platform_admin_headers
    ):
        """
        Test creating a form with data provider that has missing required parameters.

        Expected behavior:
        - Form creation fails with 400
        - Error message indicates missing required parameter
        """
        form_data = {
            "name": "Test Form Missing Params",
            "description": "Should fail validation",
            "linkedWorkflow": "test_workflow",
            "formSchema": {
                "fields": [
                    {
                        "name": "repo_selector",
                        "label": "Select Repository",
                        "type": "select",
                        "required": True,
                        "dataProvider": "get_github_repos",
                        "dataProviderInputs": {
                            # Missing required 'token' parameter
                            "org": {
                                "mode": "static",
                                "value": "test-org"
                            }
                        }
                    }
                ]
            },
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=platform_admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 400
        error_data = response.json()

        assert "error" in error_data
        assert "details" in error_data
        errors = error_data["details"].get("errors", [])
        assert any("token" in str(err) and "required" in str(err).lower() for err in errors)

    def test_create_form_with_invalid_data_provider(
        self,
        api_base_url,
        platform_admin_headers
    ):
        """
        Test creating a form with non-existent data provider.

        Expected behavior:
        - Form creation fails with 400
        - Error message indicates unknown data provider
        """
        form_data = {
            "name": "Test Form Invalid Provider",
            "description": "Should fail validation",
            "linkedWorkflow": "test_workflow",
            "formSchema": {
                "fields": [
                    {
                        "name": "selector",
                        "label": "Select Something",
                        "type": "select",
                        "required": True,
                        "dataProvider": "nonexistent_provider",
                        "dataProviderInputs": {
                            "param": {
                                "mode": "static",
                                "value": "value"
                            }
                        }
                    }
                ]
            },
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=platform_admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 400
        error_data = response.json()

        assert "error" in error_data
        assert "details" in error_data
        errors = error_data["details"].get("errors", [])
        assert any("nonexistent_provider" in str(err) for err in errors)

    def test_create_form_with_invalid_input_mode(
        self,
        api_base_url,
        platform_admin_headers
    ):
        """
        Test creating a form with invalid input configuration.

        Expected behavior:
        - Pydantic validation fails with 400
        - Error indicates validation problem with dataProviderInputs
        """
        form_data = {
            "name": "Test Form Invalid Mode",
            "description": "Should fail validation",
            "linkedWorkflow": "test_workflow",
            "formSchema": {
                "fields": [
                    {
                        "name": "selector",
                        "label": "Select Something",
                        "type": "select",
                        "required": True,
                        "dataProvider": "get_github_repos",
                        "dataProviderInputs": {
                            "token": {
                                "mode": "static"
                                # Missing 'value' for static mode!
                            }
                        }
                    }
                ]
            },
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=platform_admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 400
        error_data = response.json()

        # Pydantic validation should catch this
        assert "error" in error_data
        assert "ValidationError" in error_data["error"]

    def test_update_form_add_data_provider_inputs(
        self,
        api_base_url,
        platform_admin_headers,
        platform_test_form
    ):
        """
        Test updating an existing form to add data provider inputs.

        Expected behavior:
        - Update succeeds
        - New dataProviderInputs are added
        - Validation runs on updated schema
        """
        # Update form to add data provider with inputs
        update_data = {
            "formSchema": {
                "fields": [
                    {
                        "name": "email",
                        "label": "Email Address",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "license",
                        "label": "License Type",
                        "type": "select",
                        "required": True,
                        "dataProvider": "get_filtered_licenses",
                        "dataProviderInputs": {
                            "filter": {
                                "mode": "static",
                                "value": "available"
                            }
                        }
                    }
                ]
            }
        }

        response = requests.put(
            f"{api_base_url}/api/forms/{platform_test_form}",
            headers=platform_admin_headers,
            json=update_data,
            timeout=10
        )

        assert response.status_code == 200
        updated_form = response.json()

        # Verify update was applied
        fields = updated_form["formSchema"]["fields"]
        license_field = next(f for f in fields if f["name"] == "license")

        assert license_field["dataProvider"] == "get_filtered_licenses"
        assert license_field["dataProviderInputs"]["filter"]["mode"] == "static"
        assert license_field["dataProviderInputs"]["filter"]["value"] == "available"

    def test_form_with_multiple_fields_using_data_providers(
        self,
        api_base_url,
        platform_admin_headers
    ):
        """
        Test form with multiple fields each using different data providers.

        Expected behavior:
        - Form creation succeeds
        - Each field maintains its own dataProviderInputs
        - Validation works for all fields
        """
        form_data = {
            "name": "Multi-Provider Form",
            "description": "Form with multiple data provider fields",
            "linkedWorkflow": "test_workflow",
            "formSchema": {
                "fields": [
                    {
                        "name": "repository",
                        "label": "Repository",
                        "type": "select",
                        "required": True,
                        "dataProvider": "get_github_repos",
                        "dataProviderInputs": {
                            "token": {
                                "mode": "static",
                                "value": "ghp_token_1"
                            },
                            "org": {
                                "mode": "static",
                                "value": "org1"
                            }
                        }
                    },
                    {
                        "name": "branch",
                        "label": "Branch",
                        "type": "select",
                        "required": True,
                        "dataProvider": "get_github_branches",
                        "dataProviderInputs": {
                            "token": {
                                "mode": "static",
                                "value": "ghp_token_1"
                            },
                            "repo": {
                                "mode": "static",
                                "value": "org1/repo1"
                            }
                        }
                    },
                    {
                        "name": "license",
                        "label": "License",
                        "type": "select",
                        "required": False,
                        "dataProvider": "get_filtered_licenses",
                        "dataProviderInputs": {
                            "filter": {
                                "mode": "static",
                                "value": "available"
                            }
                        }
                    }
                ]
            },
            "isPublic": True
        }

        response = requests.post(
            f"{api_base_url}/api/forms",
            headers=platform_admin_headers,
            json=form_data,
            timeout=10
        )

        assert response.status_code == 201
        created_form = response.json()

        # Verify all three fields have their dataProviderInputs
        fields = created_form["formSchema"]["fields"]
        assert len(fields) == 3

        repo_field = next(f for f in fields if f["name"] == "repository")
        branch_field = next(f for f in fields if f["name"] == "branch")
        license_field = next(f for f in fields if f["name"] == "license")

        assert repo_field["dataProviderInputs"]["org"]["value"] == "org1"
        assert branch_field["dataProviderInputs"]["repo"]["value"] == "org1/repo1"
        assert license_field["dataProviderInputs"]["filter"]["value"] == "available"

        # Cleanup
        requests.delete(
            f"{api_base_url}/api/forms/{created_form['id']}",
            headers=platform_admin_headers,
            timeout=10
        )
