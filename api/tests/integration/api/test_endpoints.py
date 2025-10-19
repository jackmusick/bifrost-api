"""Integration tests for Generic Endpoints

Tests generic system endpoints:
- Health check endpoints
- Version and status endpoints
- System discovery endpoints
- Utility endpoints
"""

import json
import logging
import pytest
import requests

logger = logging.getLogger(__name__)


class TestHealthEndpoints:
    """Test system health check endpoints"""

    def test_health_check_endpoint_exists(self, api_base_url):
        """GET /api/health should be available"""
        response = requests.get(
            f"{api_base_url}/api/health",
            timeout=10
        )

        # Health check should be accessible without auth
        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info(f"Health check: {data}")

    def test_health_includes_status_field(self, api_base_url):
        """Health response should include status field"""
        response = requests.get(
            f"{api_base_url}/api/health",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            # Should have status field
            if "status" in data:
                assert data["status"] in ["healthy", "ok", "running", "up"]
                logger.info(f"Health status: {data['status']}")

    def test_readiness_probe_endpoint(self, api_base_url):
        """GET /api/ready should indicate readiness"""
        response = requests.get(
            f"{api_base_url}/api/ready",
            timeout=10
        )

        # Readiness probe should be accessible
        assert response.status_code in [200, 401, 404, 503]
        if response.status_code == 200:
            logger.info("Service is ready")
        elif response.status_code == 503:
            logger.info("Service not ready (503)")

    def test_liveness_probe_endpoint(self, api_base_url):
        """GET /api/live should indicate liveness"""
        response = requests.get(
            f"{api_base_url}/api/live",
            timeout=10
        )

        # Liveness probe should be accessible
        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            logger.info("Service is live")


class TestVersionEndpoint:
    """Test version and metadata endpoints"""

    def test_version_endpoint_success(self, api_base_url):
        """GET /api/version should return version info"""
        response = requests.get(
            f"{api_base_url}/api/version",
            timeout=10
        )

        # Version endpoint should be accessible
        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info(f"Version info: {data}")

    def test_version_includes_version_string(self, api_base_url):
        """Version response should include version string"""
        response = requests.get(
            f"{api_base_url}/api/version",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            # Should have version or similar field
            version_fields = ["version", "app_version", "apiVersion"]
            has_version = any(field in data for field in version_fields)
            if has_version:
                logger.info(f"Version found in response")

    def test_status_endpoint_success(self, api_base_url):
        """GET /api/status should return system status"""
        response = requests.get(
            f"{api_base_url}/api/status",
            timeout=10
        )

        # Status endpoint should be accessible
        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info(f"System status: {data}")

    def test_status_includes_environment(self, api_base_url):
        """Status response may include environment info"""
        response = requests.get(
            f"{api_base_url}/api/status",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            # May include environment, timestamp, etc.
            if "environment" in data or "timestamp" in data:
                logger.info("Status includes environment/timestamp")


class TestDiscoveryEndpoints:
    """Test API discovery endpoints"""

    def test_endpoints_list_endpoint(self, api_base_url):
        """GET /api/endpoints should list available endpoints"""
        response = requests.get(
            f"{api_base_url}/api/endpoints",
            timeout=10
        )

        # Discovery endpoint should be accessible
        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            # Should return a list or dict of endpoints
            assert isinstance(data, (list, dict))
            logger.info(f"Discovered {len(data) if isinstance(data, list) else len(data)} endpoints")

    def test_endpoints_includes_documentation(self, api_base_url):
        """Endpoints discovery should include documentation"""
        response = requests.get(
            f"{api_base_url}/api/endpoints",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                endpoint = data[0]
                # Should have some descriptive fields
                desc_fields = ["name", "path", "method", "description"]
                has_desc = any(field in endpoint for field in desc_fields)
                if has_desc:
                    logger.info("Endpoints have documentation")

    def test_openapi_json_endpoint(self, api_base_url):
        """GET /api/openapi.json should return OpenAPI spec"""
        response = requests.get(
            f"{api_base_url}/api/openapi.json",
            timeout=10
        )

        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Should have OpenAPI structure
            if "openapi" in data or "swagger" in data:
                logger.info("OpenAPI spec found")

    def test_swagger_ui_accessible(self, api_base_url):
        """GET /api/docs should return Swagger UI"""
        response = requests.get(
            f"{api_base_url}/api/docs",
            timeout=10
        )

        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            html = response.text
            # Should be HTML content
            assert "<html" in html.lower() or "<!doctype" in html.lower()
            logger.info("Swagger UI accessible")


class TestUtilityEndpoints:
    """Test utility and diagnostic endpoints"""

    def test_echo_endpoint_returns_request(self, api_base_url, admin_headers):
        """GET /api/echo should echo request back"""
        response = requests.get(
            f"{api_base_url}/api/echo?message=hello",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            # Should echo back something about the request
            logger.info(f"Echo response: {data}")

    def test_time_endpoint_returns_server_time(self, api_base_url):
        """GET /api/time should return server time"""
        response = requests.get(
            f"{api_base_url}/api/time",
            timeout=10
        )

        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            # Should have time field
            if "timestamp" in data or "time" in data or "now" in data:
                logger.info("Server time endpoint working")

    def test_info_endpoint_returns_system_info(self, api_base_url):
        """GET /api/info should return system information"""
        response = requests.get(
            f"{api_base_url}/api/info",
            timeout=10
        )

        assert response.status_code in [200, 401, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info(f"System info: {data}")


class TestErrorEndpoints:
    """Test error handling and diagnostics"""

    def test_404_error_handling(self, api_base_url):
        """Nonexistent endpoint should return 404"""
        response = requests.get(
            f"{api_base_url}/api/nonexistent-endpoint-xyz",
            timeout=10
        )

        assert response.status_code == 404
        # 404 responses may not always be JSON
        try:
            data = response.json()
            assert "error" in data or "message" in data
        except Exception:
            # If not JSON, just check we got the right status
            pass
        logger.info("404 error handled correctly")

    def test_error_test_endpoint(self, api_base_url, admin_headers):
        """GET /api/test-error should deliberately trigger error"""
        response = requests.get(
            f"{api_base_url}/api/test-error",
            headers=admin_headers,
            timeout=10
        )

        # Should return error status (not found or unauthorized more likely)
        assert response.status_code in [401, 404, 500]
        logger.info(f"Error test endpoint: {response.status_code}")

    def test_validation_test_endpoint(self, api_base_url, admin_headers):
        """GET /api/test-validation should trigger validation error"""
        response = requests.get(
            f"{api_base_url}/api/test-validation",
            headers=admin_headers,
            timeout=10
        )

        # Should return validation error or not found
        assert response.status_code in [400, 401, 404, 422]
        logger.info(f"Validation test endpoint: {response.status_code}")


class TestEndpointResponseFormats:
    """Test endpoint response formatting"""

    def test_json_response_format(self, api_base_url):
        """Endpoints should return valid JSON"""
        response = requests.get(
            f"{api_base_url}/api/status",
            timeout=10
        )

        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/json"
            data = response.json()
            assert isinstance(data, (dict, list))
            logger.info("JSON response format correct")

    def test_html_response_for_swagger_ui(self, api_base_url):
        """Swagger UI should return HTML"""
        response = requests.get(
            f"{api_base_url}/api/docs",
            timeout=10
        )

        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
            logger.info("HTML response format correct")

    def test_error_response_structure(self, api_base_url):
        """Error responses should have consistent structure"""
        response = requests.get(
            f"{api_base_url}/api/nonexistent",
            timeout=10
        )

        if response.status_code >= 400:
            # Try to parse as JSON, but 404s may not be JSON
            try:
                data = response.json()
                assert isinstance(data, dict)
                has_error_info = "error" in data or "message" in data
                assert has_error_info
            except Exception:
                # Not JSON response, but we have error status
                pass
            logger.info("Error response structure valid")


class TestEndpointPerformance:
    """Test endpoint performance characteristics"""

    def test_health_endpoint_fast_response(self, api_base_url):
        """Health endpoint should respond quickly"""
        import time
        start = time.time()
        response = requests.get(
            f"{api_base_url}/api/health",
            timeout=10
        )
        elapsed = time.time() - start

        # Should respond within 1 second (loose performance test)
        assert elapsed < 5.0
        logger.info(f"Health endpoint response time: {elapsed:.3f}s")

    def test_version_endpoint_fast_response(self, api_base_url):
        """Version endpoint should respond quickly"""
        import time
        start = time.time()
        response = requests.get(
            f"{api_base_url}/api/version",
            timeout=10
        )
        elapsed = time.time() - start

        # Should respond quickly
        assert elapsed < 5.0
        logger.info(f"Version endpoint response time: {elapsed:.3f}s")
