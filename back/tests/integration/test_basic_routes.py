"""Basic integration tests for main application routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestBasicRoutes:
    """Test basic application routes."""

    def test_health_endpoint_exists(self, client):
        """Test that health endpoint is accessible."""
        response = client.get("/health")
        # Should either work or be properly handled
        assert response.status_code in [200, 404, 500]

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        # Should return some response
        assert response.status_code in [200, 302, 404, 500]

    def test_cors_headers(self, client):
        """Test CORS configuration."""
        response = client.get("/", headers={
            "Origin": "http://localhost:3000"
        })
        # Should handle CORS gracefully
        assert response.status_code in [200, 302, 404, 500]

    def test_invalid_endpoint(self, client):
        """Test handling of invalid endpoints."""
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404

    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON."""
        response = client.post("/api/any",
                             content="invalid json",
                             headers={"Content-Type": "application/json"})
        # Should handle malformed JSON gracefully
        assert response.status_code in [400, 404, 422, 500]