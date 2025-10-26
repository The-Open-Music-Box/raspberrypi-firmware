# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for NFC Tag Domain Entity."""

import pytest
from datetime import datetime, timezone

from app.src.domain.nfc.entities.nfc_tag import NfcTag
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier


class TestNfcTag:
    """Test cases for NFC Tag entity."""
    
    def test_create_nfc_tag(self):
        """Test creating an NFC tag."""
        tag_id = TagIdentifier(uid="abcd1234")
        tag = NfcTag(identifier=tag_id)
        
        assert tag.identifier == tag_id
        assert tag.associated_playlist_id is None
        assert tag.last_detected_at is None
        assert tag.detection_count == 0
        assert not tag.is_associated()
    
    def test_associate_with_playlist(self):
        """Test associating tag with playlist."""
        tag_id = TagIdentifier(uid="abcd1234")
        tag = NfcTag(identifier=tag_id)
        playlist_id = "playlist123"
        
        tag.associate_with_playlist(playlist_id)
        
        assert tag.associated_playlist_id == playlist_id
        assert tag.is_associated()
        assert tag.get_associated_playlist_id() == playlist_id
    
    def test_associate_with_invalid_playlist_id(self):
        """Test associating with invalid playlist ID."""
        tag_id = TagIdentifier(uid="abcd1234")
        tag = NfcTag(identifier=tag_id)
        
        with pytest.raises(ValueError, match="Playlist ID cannot be empty"):
            tag.associate_with_playlist("")
        
        with pytest.raises(ValueError, match="Playlist ID cannot be empty"):
            tag.associate_with_playlist("   ")
    
    def test_dissociate_from_playlist(self):
        """Test dissociating tag from playlist."""
        tag_id = TagIdentifier(uid="abcd1234")
        tag = NfcTag(identifier=tag_id)
        
        # Associate first
        tag.associate_with_playlist("playlist123")
        assert tag.is_associated()
        
        # Then dissociate
        tag.dissociate_from_playlist()
        assert not tag.is_associated()
        assert tag.associated_playlist_id is None
    
    def test_mark_detected(self):
        """Test marking tag as detected."""
        tag_id = TagIdentifier(uid="abcd1234")
        tag = NfcTag(identifier=tag_id)
        
        before_time = datetime.now(timezone.utc)
        tag.mark_detected()
        after_time = datetime.now(timezone.utc)
        
        assert tag.detection_count == 1
        assert tag.last_detected_at is not None
        assert before_time <= tag.last_detected_at <= after_time
        
        # Mark detected again
        tag.mark_detected()
        assert tag.detection_count == 2
    
    def test_is_recently_detected(self):
        """Test checking if tag was recently detected."""
        tag_id = TagIdentifier(uid="abcd1234")
        tag = NfcTag(identifier=tag_id)
        
        # Not detected yet
        assert not tag.is_recently_detected()
        
        # Mark as detected
        tag.mark_detected()
        assert tag.is_recently_detected(seconds=30)
        assert tag.is_recently_detected(seconds=1)
    
    def test_tag_equality(self):
        """Test tag equality based on identifier."""
        tag_id1 = TagIdentifier(uid="abcd1234")
        tag_id2 = TagIdentifier(uid="abcd1234")
        tag_id3 = TagIdentifier(uid="efab5678")
        
        tag1 = NfcTag(identifier=tag_id1)
        tag2 = NfcTag(identifier=tag_id2)
        tag3 = NfcTag(identifier=tag_id3)
        
        assert tag1 == tag2  # Same identifier
        assert tag1 != tag3  # Different identifier
        assert tag1 != "not a tag"  # Different type
    
    def test_tag_hash(self):
        """Test tag hashing for use in sets/dicts."""
        tag_id1 = TagIdentifier(uid="abcd1234")
        tag_id2 = TagIdentifier(uid="abcd1234")
        tag_id3 = TagIdentifier(uid="efab5678")
        
        tag1 = NfcTag(identifier=tag_id1)
        tag2 = NfcTag(identifier=tag_id2)
        tag3 = NfcTag(identifier=tag_id3)
        
        # Same identifier should have same hash
        assert hash(tag1) == hash(tag2)
        
        # Can be used in sets
        tag_set = {tag1, tag2, tag3}
        assert len(tag_set) == 2  # tag1 and tag2 are duplicates