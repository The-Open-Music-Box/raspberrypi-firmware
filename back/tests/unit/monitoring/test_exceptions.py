# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for custom exception classes."""

import pytest
from app.src.monitoring.core.exceptions import (
    # Base
    TombError,
    # Audio
    AudioError,
    AudioResourceError,
    AudioResourceBusyError,
    AudioDeviceError,
    AudioFormatError,
    AudioBufferError,
    AudioBackendError,
    # Playlist
    PlaylistError,
    PlaylistNotFoundError,
    TrackNotFoundError,
    PlaylistValidationError,
    # NFC
    NFCError,
    NFCDeviceError,
    NFCTagError,
    # Upload
    UploadError,
    UploadValidationError,
    UploadStorageError,
    # Configuration
    ConfigurationError,
    HardwareConfigurationError,
    # Service
    ServiceError,
    ServiceUnavailableError,
    ServiceInitializationError,
    # Monitoring
    MonitoringError,
    EventMonitoringError,
    LoggingError,
    # Validation
    ValidationError,
    SchemaValidationError,
    # Network
    NetworkError,
    ConnectionError as NetworkConnectionError,
    TimeoutError as NetworkTimeoutError,
    # Database
    DatabaseError,
    DatabaseConnectionError,
    DatabaseMigrationError,
    # FileSystem
    FileSystemError,
    FileNotFoundError as FSFileNotFoundError,
    FilePermissionError,
    DirectoryError,
    # Utility functions
    get_exception_hierarchy,
    is_critical_error,
    get_error_category,
)


class TestBaseExceptions:
    """Test base exception hierarchy."""

    def test_tomb_error_is_exception(self):
        """Test TombError inherits from Exception."""
        error = TombError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_tomb_error_with_no_message(self):
        """Test TombError can be raised without message."""
        error = TombError()
        assert isinstance(error, Exception)


class TestAudioExceptions:
    """Test audio-related exceptions."""

    def test_audio_error_hierarchy(self):
        """Test AudioError inherits from TombError."""
        error = AudioError("audio failed")
        assert isinstance(error, TombError)
        assert isinstance(error, Exception)

    def test_audio_resource_error(self):
        """Test AudioResourceError."""
        error = AudioResourceError("resource unavailable")
        assert isinstance(error, AudioError)
        assert str(error) == "resource unavailable"

    def test_audio_resource_busy_error(self):
        """Test AudioResourceBusyError."""
        error = AudioResourceBusyError("device busy")
        assert isinstance(error, AudioResourceError)
        assert isinstance(error, AudioError)

    def test_audio_device_error(self):
        """Test AudioDeviceError."""
        error = AudioDeviceError("device not found")
        assert isinstance(error, AudioError)

    def test_audio_format_error(self):
        """Test AudioFormatError."""
        error = AudioFormatError("unsupported format")
        assert isinstance(error, AudioError)

    def test_audio_buffer_error(self):
        """Test AudioBufferError."""
        error = AudioBufferError("buffer overflow")
        assert isinstance(error, AudioError)

    def test_audio_backend_error(self):
        """Test AudioBackendError."""
        error = AudioBackendError("backend initialization failed")
        assert isinstance(error, AudioError)


class TestPlaylistExceptions:
    """Test playlist-related exceptions."""

    def test_playlist_error_hierarchy(self):
        """Test PlaylistError inherits from TombError."""
        error = PlaylistError("playlist error")
        assert isinstance(error, TombError)

    def test_playlist_not_found_error(self):
        """Test PlaylistNotFoundError."""
        error = PlaylistNotFoundError("playlist-123")
        assert isinstance(error, PlaylistError)

    def test_track_not_found_error(self):
        """Test TrackNotFoundError."""
        error = TrackNotFoundError("track-456")
        assert isinstance(error, PlaylistError)

    def test_playlist_validation_error(self):
        """Test PlaylistValidationError."""
        error = PlaylistValidationError("invalid playlist data")
        assert isinstance(error, PlaylistError)


class TestNFCExceptions:
    """Test NFC-related exceptions."""

    def test_nfc_error_hierarchy(self):
        """Test NFCError inherits from TombError."""
        error = NFCError("nfc failed")
        assert isinstance(error, TombError)

    def test_nfc_device_error(self):
        """Test NFCDeviceError."""
        error = NFCDeviceError("device not found")
        assert isinstance(error, NFCError)

    def test_nfc_tag_error(self):
        """Test NFCTagError."""
        error = NFCTagError("invalid tag")
        assert isinstance(error, NFCError)


class TestDatabaseExceptions:
    """Test database-related exceptions."""

    def test_database_error_hierarchy(self):
        """Test DatabaseError inherits from TombError."""
        error = DatabaseError("database error")
        assert isinstance(error, TombError)

    def test_database_connection_error(self):
        """Test DatabaseConnectionError."""
        error = DatabaseConnectionError("connection failed")
        assert isinstance(error, DatabaseError)

    def test_database_migration_error(self):
        """Test DatabaseMigrationError."""
        error = DatabaseMigrationError("migration failed")
        assert isinstance(error, DatabaseError)


class TestUploadExceptions:
    """Test upload-related exceptions."""

    def test_upload_error_hierarchy(self):
        """Test UploadError inherits from TombError."""
        error = UploadError("upload failed")
        assert isinstance(error, TombError)

    def test_upload_validation_error(self):
        """Test UploadValidationError."""
        error = UploadValidationError("invalid file type")
        assert isinstance(error, UploadError)

    def test_upload_storage_error(self):
        """Test UploadStorageError."""
        error = UploadStorageError("storage full")
        assert isinstance(error, UploadError)


class TestConfigurationExceptions:
    """Test configuration exceptions."""

    def test_configuration_error_hierarchy(self):
        """Test ConfigurationError inherits from TombError."""
        error = ConfigurationError("configuration error")
        assert isinstance(error, TombError)

    def test_hardware_configuration_error(self):
        """Test HardwareConfigurationError."""
        error = HardwareConfigurationError("invalid hardware config")
        assert isinstance(error, ConfigurationError)


class TestServiceExceptions:
    """Test service exceptions."""

    def test_service_error_hierarchy(self):
        """Test ServiceError inherits from TombError."""
        error = ServiceError("service error")
        assert isinstance(error, TombError)

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        error = ServiceUnavailableError("service down")
        assert isinstance(error, ServiceError)

    def test_service_initialization_error(self):
        """Test ServiceInitializationError."""
        error = ServiceInitializationError("init failed")
        assert isinstance(error, ServiceError)


class TestMonitoringExceptions:
    """Test monitoring exceptions."""

    def test_monitoring_error_hierarchy(self):
        """Test MonitoringError inherits from TombError."""
        error = MonitoringError("monitoring error")
        assert isinstance(error, TombError)

    def test_event_monitoring_error(self):
        """Test EventMonitoringError."""
        error = EventMonitoringError("event monitoring failed")
        assert isinstance(error, MonitoringError)

    def test_logging_error(self):
        """Test LoggingError."""
        error = LoggingError("logging failed")
        assert isinstance(error, MonitoringError)


class TestValidationExceptions:
    """Test validation exceptions."""

    def test_validation_error_hierarchy(self):
        """Test ValidationError inherits from TombError."""
        error = ValidationError("validation error")
        assert isinstance(error, TombError)

    def test_schema_validation_error(self):
        """Test SchemaValidationError."""
        error = SchemaValidationError("schema validation failed")
        assert isinstance(error, ValidationError)


class TestFileSystemExceptions:
    """Test filesystem exceptions."""

    def test_filesystem_error_hierarchy(self):
        """Test FileSystemError inherits from TombError."""
        error = FileSystemError("filesystem error")
        assert isinstance(error, TombError)

    def test_file_not_found_error(self):
        """Test FileNotFoundError."""
        error = FSFileNotFoundError("file not found")
        assert isinstance(error, FileSystemError)

    def test_file_permission_error(self):
        """Test FilePermissionError."""
        error = FilePermissionError("permission denied")
        assert isinstance(error, FileSystemError)

    def test_directory_error(self):
        """Test DirectoryError."""
        error = DirectoryError("directory error")
        assert isinstance(error, FileSystemError)


class TestNetworkExceptions:
    """Test network-related exceptions."""

    def test_network_error_hierarchy(self):
        """Test NetworkError inherits from TombError."""
        error = NetworkError("network error")
        assert isinstance(error, TombError)

    def test_connection_error(self):
        """Test ConnectionError."""
        error = NetworkConnectionError("connection failed")
        assert isinstance(error, NetworkError)

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = NetworkTimeoutError("request timeout")
        assert isinstance(error, NetworkError)


class TestUtilityFunctions:
    """Test utility functions for exceptions."""

    def test_get_exception_hierarchy(self):
        """Test get_exception_hierarchy returns dict."""
        hierarchy = get_exception_hierarchy()
        assert isinstance(hierarchy, dict)
        assert "TombError" in hierarchy
        assert "AudioError" in hierarchy["TombError"]

    def test_is_critical_error_with_critical(self):
        """Test is_critical_error identifies critical exceptions."""
        error = DatabaseConnectionError("connection lost")
        assert is_critical_error(error) is True

    def test_is_critical_error_with_non_critical(self):
        """Test is_critical_error returns False for non-critical."""
        error = PlaylistNotFoundError("playlist not found")
        assert is_critical_error(error) is False

    def test_get_error_category_audio(self):
        """Test get_error_category for audio errors."""
        error = AudioDeviceError("device error")
        assert get_error_category(error) == "audio"

    def test_get_error_category_playlist(self):
        """Test get_error_category for playlist errors."""
        error = PlaylistNotFoundError("not found")
        assert get_error_category(error) == "playlist"

    def test_get_error_category_nfc(self):
        """Test get_error_category for NFC errors."""
        error = NFCDeviceError("device error")
        assert get_error_category(error) == "nfc"

    def test_get_error_category_upload(self):
        """Test get_error_category for upload errors."""
        error = UploadValidationError("validation failed")
        assert get_error_category(error) == "upload"

    def test_get_error_category_configuration(self):
        """Test get_error_category for configuration errors."""
        error = ConfigurationError("config error")
        assert get_error_category(error) == "configuration"

    def test_get_error_category_service(self):
        """Test get_error_category for service errors."""
        error = ServiceUnavailableError("service down")
        assert get_error_category(error) == "service"

    def test_get_error_category_monitoring(self):
        """Test get_error_category for monitoring errors."""
        error = MonitoringError("monitoring failed")
        assert get_error_category(error) == "monitoring"

    def test_get_error_category_validation(self):
        """Test get_error_category for validation errors."""
        error = ValidationError("validation failed")
        assert get_error_category(error) == "validation"

    def test_get_error_category_network(self):
        """Test get_error_category for network errors."""
        error = NetworkError("network error")
        assert get_error_category(error) == "network"

    def test_get_error_category_database(self):
        """Test get_error_category for database errors."""
        error = DatabaseError("database error")
        assert get_error_category(error) == "database"

    def test_get_error_category_filesystem(self):
        """Test get_error_category for filesystem errors."""
        error = FileSystemError("filesystem error")
        assert get_error_category(error) == "filesystem"

    def test_get_error_category_unknown(self):
        """Test get_error_category for unknown errors."""
        error = Exception("generic error")
        assert get_error_category(error) == "unknown"


class TestExceptionRaising:
    """Test exceptions can be raised and caught properly."""

    def test_raise_and_catch_tomb_error(self):
        """Test raising and catching TombError."""
        with pytest.raises(TombError) as exc_info:
            raise TombError("test")
        assert str(exc_info.value) == "test"

    def test_raise_and_catch_audio_error(self):
        """Test raising and catching AudioError."""
        with pytest.raises(AudioError):
            raise AudioError("audio failed")

    def test_catch_base_exception_with_derived(self):
        """Test catching base exception when derived is raised."""
        with pytest.raises(TombError):
            raise AudioDeviceError("device error")

    def test_catch_multiple_levels(self):
        """Test exception hierarchy multiple levels deep."""
        with pytest.raises(AudioError):
            raise AudioResourceBusyError("busy")

        with pytest.raises(AudioResourceError):
            raise AudioResourceBusyError("busy")

    def test_exception_with_complex_message(self):
        """Test exceptions with formatted messages."""
        playlist_id = "playlist-123"
        error = PlaylistNotFoundError(f"Playlist {playlist_id} not found in database")
        assert "playlist-123" in str(error)
        assert isinstance(error, PlaylistError)
