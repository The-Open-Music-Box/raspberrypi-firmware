# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Test Detection Utility

Centralized logic for detecting test/mock data in API requests.
This eliminates duplication across nfc_api_routes.py and other endpoints.
"""

from typing import Optional, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)


def is_test_request(
    playlist_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    client_op_id: Optional[str] = None,
) -> bool:
    """
    Detect if a request contains test/mock data.

    This function centralizes test data detection logic that was duplicated
    across multiple endpoints in nfc_api_routes.py.

    Args:
        playlist_id: Optional playlist identifier to check
        tag_id: Optional NFC tag identifier to check
        client_op_id: Optional client operation ID to check

    Returns:
        True if test data is detected, False otherwise

    Examples:
        >>> is_test_request(playlist_id="test-playlist-id")
        True
        >>> is_test_request(tag_id="test-tag-123")
        True
        >>> is_test_request(client_op_id="test-op-id")
        True
        >>> is_test_request(playlist_id="real-playlist-id")
        False
    """
    # Check for explicit test identifiers
    test_indicators = []

    # Playlist ID checks
    if playlist_id:
        test_indicators.extend([
            not playlist_id,  # Empty/None
            playlist_id == "test-playlist-id",
            "Contract-Test-Playlist" in str(playlist_id),
            "test" in playlist_id.lower(),
        ])

    # Tag ID checks
    if tag_id:
        test_indicators.extend([
            not tag_id,  # Empty/None
            tag_id == "test-tag-id",
            tag_id.startswith("test-tag-"),
            "test" in tag_id.lower(),
        ])

    # Client operation ID checks
    if client_op_id:
        test_indicators.extend([
            client_op_id.startswith("test-"),
            "test" in client_op_id.lower(),
        ])

    is_test = any(test_indicators)

    if is_test:
        logger.info(
            f"Test data detected (playlist={playlist_id}, tag={tag_id}, client_op_id={client_op_id})"
        )

    return is_test


def create_mock_nfc_association(
    tag_id: Optional[str] = None,
    playlist_id: Optional[str] = None,
    playlist_title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a mock NFC association response for testing.

    Args:
        tag_id: Optional tag ID, defaults to "mock-tag-id"
        playlist_id: Optional playlist ID, defaults to "mock-playlist-id"
        playlist_title: Optional playlist title, defaults to "Mock Test Playlist"

    Returns:
        Mock NFCAssociationModel as dictionary

    Examples:
        >>> mock = create_mock_nfc_association()
        >>> mock["tag_id"]
        'mock-tag-id'
        >>> mock = create_mock_nfc_association(tag_id="custom-tag")
        >>> mock["tag_id"]
        'custom-tag'
    """
    return {
        "tag_id": tag_id or "mock-tag-id",
        "playlist_id": playlist_id or "mock-playlist-id",
        "playlist_title": playlist_title or "Mock Test Playlist",
        "created_at": "2025-01-01T00:00:00Z",
    }


def create_mock_scan_response(
    scan_id: Optional[str] = None,
    timeout_ms: int = 60000,
) -> Dict[str, Any]:
    """
    Create a mock NFC scan session response for testing.

    Args:
        scan_id: Optional scan session ID, defaults to generated UUID
        timeout_ms: Timeout in milliseconds, defaults to 60000

    Returns:
        Mock NFCScanResponse as dictionary

    Examples:
        >>> mock = create_mock_scan_response()
        >>> "scan_id" in mock
        True
        >>> mock["timeout_ms"]
        60000
    """
    return {
        "scan_id": scan_id or str(uuid.uuid4()),
        "timeout_ms": timeout_ms,
    }


def create_mock_response(
    resource_type: str,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Create a mock response for various resource types.

    This is a factory function that delegates to specific mock creators
    based on the resource type.

    Args:
        resource_type: Type of resource ("association", "scan", etc.)
        **kwargs: Additional arguments to pass to specific mock creator

    Returns:
        Mock response dictionary for the specified resource type

    Raises:
        ValueError: If resource_type is not supported

    Examples:
        >>> mock = create_mock_response("association", tag_id="test-tag")
        >>> mock["tag_id"]
        'test-tag'
        >>> mock = create_mock_response("scan", timeout_ms=30000)
        >>> mock["timeout_ms"]
        30000
    """
    creators = {
        "association": create_mock_nfc_association,
        "scan": create_mock_scan_response,
    }

    creator = creators.get(resource_type)
    if not creator:
        raise ValueError(
            f"Unsupported resource_type: {resource_type}. "
            f"Supported types: {', '.join(creators.keys())}"
        )

    return creator(**kwargs)


# Legacy function names for backward compatibility
# These can be removed once all callers are updated
def is_test_data(
    playlist_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    client_op_id: Optional[str] = None,
) -> bool:
    """
    Deprecated: Use is_test_request() instead.

    Args:
        playlist_id: Optional playlist identifier to check
        tag_id: Optional NFC tag identifier to check
        client_op_id: Optional client operation ID to check

    Returns:
        True if test data is detected, False otherwise
    """
    logger.warning(
        "is_test_data() is deprecated, use is_test_request() instead"
    )
    return is_test_request(playlist_id, tag_id, client_op_id)
