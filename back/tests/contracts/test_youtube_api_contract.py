"""Contract tests for YouTube API endpoints.

Validates that YouTube API endpoints conform to the expected API contract.

Progress: 3/3 endpoints tested ✅
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app_with_youtube_routes():
    """Create FastAPI app with YouTube routes configured."""
    from app.src.api.endpoints.youtube_api_routes import YouTubeAPIRoutes

    app = FastAPI()

    # Add mock container to app
    app.container = Mock()

    # Mock YouTube service factory
    def mock_youtube_service_factory(request):
        service = Mock()
        service.process_download = AsyncMock(return_value={
            "status": "success",
            "title": "Test Video",
            "id": "test-video-id"
        })
        service.search_videos = AsyncMock(return_value={
            "results": [
                {"title": "Video 1", "url": "https://youtube.com/watch?v=1"},
                {"title": "Video 2", "url": "https://youtube.com/watch?v=2"}
            ]
        })
        service.get_task_status = AsyncMock(return_value={
            "status": "completed",
            "progress": 100
        })
        return service

    routes = YouTubeAPIRoutes(mock_youtube_service_factory)
    app.include_router(routes.get_router())

    return app, routes


@pytest.mark.asyncio
class TestYoutubeAPIContract:
    """Contract tests for YouTube API endpoints."""

    async def test_download_contract(self, app_with_youtube_routes):
        """Test POST /api/youtube/download - Download YouTube video.

        Contract:
        - Request body: {url: str (required)}
        - Success response (200): {status: "success", data: {status, title, id, ...}}
        - Error response (400): when URL is invalid
        """
        app, routes = app_with_youtube_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful download (using test URL to trigger mock)
            response = await client.post(
                "/api/youtube/download",
                json={"url": "test-value"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

            # Test error when URL missing
            response = await client.post(
                "/api/youtube/download",
                json={}
            )

            assert response.status_code == 422  # FastAPI validation error

    async def test_get_download_status_contract(self, app_with_youtube_routes):
        """Test GET /api/youtube/status/{task_id} - Get download status.

        Contract:
        - Path param: task_id (string)
        - Success response (200): {status: "success", data: {status, progress, ...}}
        - Error response (404): when task not found
        """
        app, routes = app_with_youtube_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful status retrieval
            response = await client.get("/api/youtube/status/test-task-123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "status" in data["data"]

    async def test_search_contract(self, app_with_youtube_routes):
        """Test GET /api/youtube/search - Search YouTube videos.

        Contract:
        - Query params: query (str, required)
        - Success response (200): {status: "success", data: {results: []}}
        - Error response (400): when query missing
        """
        app, routes = app_with_youtube_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful search (empty query triggers mock response)
            response = await client.get("/api/youtube/search?query=")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "results" in data["data"]
            assert isinstance(data["data"]["results"], list)
