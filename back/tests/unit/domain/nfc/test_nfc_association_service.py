# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for NFC Association Service."""

import pytest
from unittest.mock import AsyncMock

from app.src.domain.nfc.services.nfc_association_service import NfcAssociationService
from app.src.domain.nfc.entities.nfc_tag import NfcTag
from app.src.domain.nfc.entities.association_session import SessionState
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.infrastructure.nfc.repositories.nfc_memory_repository import NfcMemoryRepository


@pytest.fixture
def nfc_repository():
    """Fixture for NFC repository."""
    return NfcMemoryRepository()


@pytest.fixture
def association_service(nfc_repository):
    """Fixture for NFC association service."""
    return NfcAssociationService(nfc_repository)


class TestNfcAssociationService:
    """Test cases for NFC Association Service."""
    
    @pytest.mark.asyncio
    async def test_start_association_session(self, association_service):
        """Test starting an association session."""
        playlist_id = "playlist123"
        
        session = await association_service.start_association_session(playlist_id)
        
        assert session.playlist_id == playlist_id
        assert session.state == SessionState.LISTENING
        assert session.is_active()
        
        # Session should be tracked
        active_sessions = association_service.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == session.session_id
    
    @pytest.mark.asyncio
    async def test_start_duplicate_session_fails(self, association_service):
        """Test that starting duplicate session for same playlist fails."""
        playlist_id = "playlist123"
        
        # Start first session
        await association_service.start_association_session(playlist_id)
        
        # Try to start another session for same playlist
        with pytest.raises(ValueError, match="Association session already active"):
            await association_service.start_association_session(playlist_id)
    
    @pytest.mark.asyncio
    async def test_start_session_invalid_playlist(self, association_service):
        """Test starting session with invalid playlist ID."""
        with pytest.raises(ValueError, match="Playlist ID is required"):
            await association_service.start_association_session("")
    
    @pytest.mark.asyncio
    async def test_process_tag_detection_success(self, association_service, nfc_repository):
        """Test successful tag detection and association."""
        playlist_id = "playlist123"
        tag_id = TagIdentifier(uid="abcd1234")
        
        # Start session
        session = await association_service.start_association_session(playlist_id)
        
        # Process tag detection
        result = await association_service.process_tag_detection(tag_id)
        
        assert result["action"] == "association_success"
        assert result["playlist_id"] == playlist_id
        assert result["tag_id"] == str(tag_id)
        assert result["session_state"] == SessionState.SUCCESS.value
        
        # Verify tag is saved and associated
        saved_tag = await nfc_repository.find_by_identifier(tag_id)
        assert saved_tag is not None
        assert saved_tag.is_associated()
        assert saved_tag.get_associated_playlist_id() == playlist_id
    
    @pytest.mark.asyncio
    async def test_process_tag_detection_duplicate(self, association_service, nfc_repository):
        """Test tag detection with duplicate association."""
        playlist1 = "playlist123"
        playlist2 = "playlist456"
        tag_id = TagIdentifier(uid="abcd1234")

        # Create tag already associated with playlist1
        existing_tag = NfcTag(identifier=tag_id)
        existing_tag.associate_with_playlist(playlist1)
        await nfc_repository.save_tag(existing_tag)

        # Start session for playlist2
        session = await association_service.start_association_session(playlist2)

        # Process tag detection
        result = await association_service.process_tag_detection(tag_id)

        assert result["action"] == "duplicate_association"
        assert result["playlist_id"] == playlist2
        assert result["existing_playlist_id"] == playlist1
        assert result["session_state"] == SessionState.DUPLICATE.value
        assert result["is_same_playlist"] == False

        # Verify session is still active (DUPLICATE state should keep it active)
        active_sessions = association_service.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].state == SessionState.DUPLICATE

    @pytest.mark.asyncio
    async def test_process_tag_detection_duplicate_same_playlist(self, association_service, nfc_repository):
        """Test tag detection when trying to re-associate with the same playlist."""
        playlist_id = "playlist123"
        tag_id = TagIdentifier(uid="abcd1234")

        # Create tag already associated with the playlist
        existing_tag = NfcTag(identifier=tag_id)
        existing_tag.associate_with_playlist(playlist_id)
        await nfc_repository.save_tag(existing_tag)

        # Start session for the SAME playlist
        session = await association_service.start_association_session(playlist_id)

        # Process tag detection
        result = await association_service.process_tag_detection(tag_id)

        assert result["action"] == "duplicate_association"
        assert result["playlist_id"] == playlist_id
        assert result["existing_playlist_id"] == playlist_id
        assert result["is_same_playlist"] == True
        assert result["session_state"] == SessionState.DUPLICATE.value

        # Verify session is still active to prevent playback
        active_sessions = association_service.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].state == SessionState.DUPLICATE
    
    @pytest.mark.asyncio
    async def test_process_tag_no_active_sessions(self, association_service):
        """Test tag detection with no active sessions."""
        tag_id = TagIdentifier(uid="abcd1234")
        
        result = await association_service.process_tag_detection(tag_id)
        
        assert result["action"] == "tag_detected"
        assert result["tag_id"] == str(tag_id)
        assert result["no_active_sessions"] is True
    
    @pytest.mark.asyncio
    async def test_stop_association_session(self, association_service):
        """Test stopping an association session."""
        playlist_id = "playlist123"

        session = await association_service.start_association_session(playlist_id)
        session_id = session.session_id

        # Stop session
        success = await association_service.stop_association_session(session_id)
        assert success is True

        # Session should be cancelled (updated behavior)
        retrieved_session = await association_service.get_association_session(session_id)
        assert retrieved_session.state == SessionState.CANCELLED

        # No active sessions
        active_sessions = association_service.get_active_sessions()
        assert len(active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_stop_nonexistent_session(self, association_service):
        """Test stopping a non-existent session."""
        success = await association_service.stop_association_session("nonexistent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, association_service):
        """Test cleaning up expired sessions."""
        playlist_id = "playlist123"
        
        # Create session with very short timeout
        session = await association_service.start_association_session(playlist_id, timeout_seconds=0)
        
        # Cleanup should mark it as timed out
        cleaned_count = await association_service.cleanup_expired_sessions()
        assert cleaned_count == 1
        
        # Session should be timed out
        retrieved_session = await association_service.get_association_session(session.session_id)
        assert retrieved_session.state == SessionState.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_dissociate_tag(self, association_service, nfc_repository):
        """Test dissociating a tag."""
        tag_id = TagIdentifier(uid="abcd1234")
        playlist_id = "playlist123"
        
        # Create associated tag
        tag = NfcTag(identifier=tag_id)
        tag.associate_with_playlist(playlist_id)
        await nfc_repository.save_tag(tag)
        
        # Dissociate
        success = await association_service.dissociate_tag(tag_id)
        assert success is True
        
        # Verify dissociation
        retrieved_tag = await nfc_repository.find_by_identifier(tag_id)
        assert retrieved_tag is not None
        assert not retrieved_tag.is_associated()
    
    @pytest.mark.asyncio
    async def test_dissociate_nonexistent_tag(self, association_service):
        """Test dissociating a non-existent tag."""
        tag_id = TagIdentifier(uid="beef1234")
        
        success = await association_service.dissociate_tag(tag_id)
        assert success is False