# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Contract tests for Track entity serialization.

These tests ensure that Track entities serialize correctly to match the OpenAPI contract.
After the refactoring (commit refactor(domain)), Track entity now directly uses 'number'
field to align with OpenAPI contract v3.3.2.
"""

import pytest
import yaml
from pathlib import Path
from dataclasses import asdict

from app.src.domain.data.models.track import Track


class TestTrackSerializationContract:
    """Test that Track entity serialization matches OpenAPI contract."""

    @pytest.fixture
    def openapi_schema(self):
        """Load OpenAPI schema for validation."""
        schema_path = Path(__file__).parent / "openapi.yaml"
        with open(schema_path, 'r') as f:
            schema = yaml.safe_load(f)
        return schema['components']['schemas']['Track']

    @pytest.fixture
    def sample_track(self):
        """Create a sample Track entity."""
        return Track(
            id="track-123",
            track_number=1,
            title="Test Track",
            filename="test.mp3",
            file_path="/path/to/test.mp3",
            duration_ms=180000,
            artist="Test Artist",
            album="Test Album"
        )

    def test_track_entity_has_required_fields(self, sample_track, openapi_schema):
        """Test that Track entity has all required fields from OpenAPI contract.

        After the refactoring, Track entity directly uses 'number' field
        which matches the OpenAPI contract.
        """
        # Serialize track using asdict
        serialized = asdict(sample_track)

        # Get required fields from OpenAPI contract
        required_fields = openapi_schema['required']

        # Check that all required contract fields are present
        missing_fields = []
        for field in required_fields:
            if field not in serialized:
                missing_fields.append(field)

        assert not missing_fields, (
            f"Track serialization missing required OpenAPI fields: {missing_fields}. "
            f"Serialized fields: {list(serialized.keys())}"
        )

    def test_track_serialization_field_names_match_contract(self, sample_track, openapi_schema):
        """Test that serialized Track field names exactly match OpenAPI contract.

        After refactoring, Track.number is a direct dataclass field (not a property),
        so asdict() serializes it correctly as 'number'.
        """
        # Serialize track using asdict
        serialized = asdict(sample_track)

        # Get expected fields from OpenAPI contract
        required_contract_fields = set(openapi_schema['required'])
        serialized_fields = set(serialized.keys())

        # Verify 'number' field is present (no mapping needed anymore)
        assert 'track_number' in serialized, (
            "Track should have 'number' field after serialization"
        )

        # Check all required contract fields are present
        missing = required_contract_fields - serialized_fields
        if missing:
            pytest.fail(
                f"Track serialization missing required contract fields: {missing}. "
                f"Serialized: {serialized_fields}, Contract required: {required_contract_fields}"
            )

    def test_track_number_field_is_dataclass_field(self, sample_track):
        """Test that 'number' is a direct dataclass field (not a property).

        After refactoring, Track.number is a direct field, so asdict()
        serializes it correctly without any mapping.
        """
        serialized = asdict(sample_track)

        # Track.number should be a direct field
        assert hasattr(sample_track, 'number'), "Track should have 'number' attribute"

        # asdict() should serialize 'number' directly
        assert 'track_number' in serialized, "asdict() should serialize 'number' field"
        assert serialized['track_number'] == sample_track.number, "Serialized number should match entity"

    def test_repository_serialization_is_contract_compliant(self, sample_track, openapi_schema):
        """Test that Track serialization is contract compliant.

        After refactoring, no field mapping is needed - asdict() returns
        contract-compliant data directly.
        """
        # Serialize the track
        track_dict = asdict(sample_track)

        # Now verify against contract
        required_fields = set(openapi_schema['required'])
        serialized_fields = set(track_dict.keys())

        # Should have 'number' directly from asdict()
        assert 'track_number' in track_dict, "Serialized track should have 'number' field per contract"

        # All required contract fields should be present
        missing = required_fields - serialized_fields
        assert not missing, f"Missing required contract fields: {missing}"

    def test_track_list_serialization_contract(self, openapi_schema):
        """Test that a list of tracks serializes correctly for API responses.

        This simulates what GET /api/playlists/{id} returns.
        """
        tracks = [
            Track(
                id=f"track-{i}",
                track_number=i,
                title=f"Track {i}",
                filename=f"track{i}.mp3",
                file_path=f"/path/track{i}.mp3",
                duration_ms=180000
            )
            for i in range(1, 4)
        ]

        # Serialize tracks (no mapping needed after refactoring)
        serialized_tracks = [asdict(track) for track in tracks]

        # Verify all tracks have correct field names
        for i, track_dict in enumerate(serialized_tracks, 1):
            assert 'track_number' in track_dict, f"Track {i} should have 'number' field"
            assert track_dict['track_number'] == i, f"Track {i} should have number={i}"

    def test_reorder_tracks_response_contract(self):
        """Test that reordered tracks maintain contract compliance.

        This would have caught the bug reported by the user where frontend
        showed "12 tracks have invalid track numbers".
        """
        # Simulate reordering tracks
        original_tracks = [
            Track(id=f"track-{i}", track_number=i, title=f"Track {i}",
                  filename=f"track{i}.mp3", file_path=f"/path/track{i}.mp3")
            for i in [1, 2, 3]
        ]

        # Reorder: 3, 1, 2
        reordered = [original_tracks[2], original_tracks[0], original_tracks[1]]

        # Update track numbers
        for i, track in enumerate(reordered, 1):
            track.number = i

        # Serialize (no mapping needed after refactoring)
        serialized = [asdict(track) for track in reordered]

        # Verify sequential numbering
        for i, track_dict in enumerate(serialized, 1):
            assert track_dict['track_number'] == i, (
                f"Reordered track at position {i} should have number={i}, got {track_dict.get('number')}"
            )
            assert 'track_number' in track_dict, f"Track {i} must have 'number' field"

        # Verify no duplicates
        numbers = [t['track_number'] for t in serialized]
        assert len(numbers) == len(set(numbers)), f"Duplicate track numbers found: {numbers}"

    @pytest.mark.parametrize("field_name,field_type", [
        ("track_number", int),  # OpenAPI v4.1.0
        ("title", str),
        ("filename", str),
    ])
    def test_required_fields_have_correct_types(self, sample_track, openapi_schema, field_name, field_type):
        """Test that required fields have correct types per OpenAPI contract."""
        track_dict = asdict(sample_track)

        assert field_name in track_dict, f"Required field '{field_name}' missing"
        assert isinstance(track_dict[field_name], field_type), (
            f"Field '{field_name}' should be {field_type.__name__}, "
            f"got {type(track_dict[field_name]).__name__}"
        )


class TestRepositorySerializationIntegration:
    """Integration tests for repository serialization.

    These tests verify the actual repository layer does correct serialization.
    """

    @pytest.mark.asyncio
    async def test_pure_sqlite_repository_get_tracks_returns_contract_compliant_data(self):
        """Test that PureSQLitePlaylistRepository serializes tracks correctly.

        After refactoring, Track entity uses 'number' directly, so no mapping needed.
        """
        from unittest.mock import Mock, patch
        from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository

        # Mock database response (DB column is still track_number, but repository maps it)
        mock_db_rows = [
            {
                'id': 'track-1',
                'playlist_id': 'playlist-1',
                'track_number': 1,  # DB column name
                'title': 'Track 1',
                'filename': 'track1.mp3',
                'file_path': '/path/track1.mp3',
                'duration_ms': 180000,
                'artist': 'Artist 1',
                'album': 'Album 1',
                'play_count': 0,
                'server_seq': 1,
                'created_at': '2025-01-01T00:00:00',
                'updated_at': '2025-01-01T00:00:00'
            }
        ]

        with patch('app.src.infrastructure.repositories.pure_sqlite_playlist_repository.get_database_manager') as mock_get_db:
            mock_db_service = Mock()
            mock_db_service.execute_query = Mock(return_value=mock_db_rows)

            mock_db_manager = Mock()
            mock_db_manager.database_service = mock_db_service
            mock_get_db.return_value = mock_db_manager

            repository = PureSQLitePlaylistRepository()

            # Get tracks (this returns Track entities)
            tracks = await repository.get_tracks_by_playlist('playlist-1')

            # Serialize them as the API would
            serialized = [asdict(track) for track in tracks]

            # Verify contract compliance
            assert len(serialized) == 1
            track = serialized[0]

            # After refactoring, 'number' is directly available
            assert 'track_number' in track, (
                "Serialized track should have 'number' field required by OpenAPI contract"
            )
            assert track['track_number'] == 1
            assert track['filename'] == 'track1.mp3'
