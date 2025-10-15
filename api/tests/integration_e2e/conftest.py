"""
Pytest fixtures for end-to-end integration tests
"""

import pytest
import requests
import base64
import json
import time


# Base URL for Azure Functions
BASE_URL = "http://localhost:7071/api"


@pytest.fixture(scope="session")
def ensure_services_running():
    """
    Ensure docker-compose services are running
    Waits for health check to pass
    """
    max_retries = 30
    retry_delay = 1

    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print(f"\n✓ Azure Functions is ready at {BASE_URL}")
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            if i == 0:
                print(f"\n⏳ Waiting for Azure Functions to start...")
            time.sleep(retry_delay)

    raise RuntimeError(
        f"Azure Functions did not start after {max_retries * retry_delay} seconds. "
        f"Please run: docker-compose up -d"
    )


@pytest.fixture
def platform_admin_headers():
    """
    Headers for platform admin user (jack@gocovi.com)
    Uses X-MS-Client-Principal header like Azure Static Web Apps
    """
    client_principal = {
        "identityProvider": "aad",
        "userId": "jack@gocovi.com",
        "userDetails": "jack@gocovi.com",
        "userRoles": ["authenticated", "PlatformAdmin"]
    }

    encoded = base64.b64encode(json.dumps(client_principal).encode()).decode()

    return {
        "X-MS-Client-Principal": encoded,
        "Content-Type": "application/json"
    }


@pytest.fixture
def org_user_headers():
    """
    Headers for org user (jack@gocovi.dev)
    Uses X-MS-Client-Principal header like Azure Static Web Apps
    """
    client_principal = {
        "identityProvider": "aad",
        "userId": "jack@gocovi.dev",
        "userDetails": "jack@gocovi.dev",
        "userRoles": ["authenticated"]
    }

    encoded = base64.b64encode(json.dumps(client_principal).encode()).decode()

    return {
        "X-MS-Client-Principal": encoded,
        "Content-Type": "application/json"
    }


@pytest.fixture
def anonymous_headers():
    """
    Headers for anonymous requests (no authentication)
    """
    return {
        "Content-Type": "application/json"
    }


@pytest.fixture
def base_url():
    """Base URL for API requests"""
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(ensure_services_running):
    """
    Automatically runs before all tests to ensure services are ready
    """
    # Load seed data for E2E tests
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    try:
        from seed_data import seed_all_data
        seed_all_data("UseDevelopmentStorage=true")
        print("✓ Seed data loaded successfully")
    except Exception as e:
        print(f"Warning: Failed to load seed data: {e}")
        # Continue without seed data - some tests may fail
        pass
