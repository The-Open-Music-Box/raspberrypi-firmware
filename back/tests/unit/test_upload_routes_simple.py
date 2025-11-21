"""Simple tests for UploadRoutes functionality."""

import pytest
from unittest.mock import Mock, patch

def test_upload_routes_import():
    """Test that UploadRoutes can be imported and initialized."""
    from app.src.routes.factories.upload_routes import UploadRoutes

    mock_app = Mock()
    mock_socketio = Mock()

    routes = UploadRoutes(mock_app, mock_socketio)

    assert routes.app == mock_app
    assert routes.socketio == mock_socketio
    # New architecture: api_routes instead of router
    assert routes.api_routes is None  # Not initialized until register_with_app() is called

def test_upload_routes_registration():
    """Test route registration functionality."""
    from app.src.routes.factories.upload_routes import UploadRoutes

    mock_app = Mock()
    mock_socketio = Mock()

    routes = UploadRoutes(mock_app, mock_socketio)
    routes.register_with_app()

    # Verify registration was called
    mock_app.include_router.assert_called_once()
    # Verify api_routes was initialized
    assert routes.api_routes is not None