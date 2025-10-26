# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unified Exception Classes for TheOpenMusicBox.

This module consolidates all custom exception classes used throughout 
the application for better error handling and debugging.
"""


# === Base Exceptions ===


class TombError(Exception):
    """Base exception for all TheOpenMusicBox errors."""

    pass


# === Audio System Exceptions ===


class AudioError(TombError):
    """Base exception for audio-related errors."""

    pass


class AudioResourceError(AudioError):
    """Exception raised when audio resource operations fail."""

    pass


class AudioResourceBusyError(AudioResourceError):
    """Exception raised when trying to access a resource that's already in use."""

    pass


class AudioDeviceError(AudioError):
    """Exception raised when audio device operations fail."""

    pass


class AudioFormatError(AudioError):
    """Exception raised when audio format is not supported or invalid."""

    pass


class AudioBufferError(AudioError):
    """Exception raised when audio buffer operations fail."""

    pass


class AudioBackendError(AudioError):
    """Exception raised when audio backend operations fail."""

    pass


# === Playlist Exceptions ===


class PlaylistError(TombError):
    """Base exception for playlist-related errors."""

    pass


class PlaylistNotFoundError(PlaylistError):
    """Exception raised when a playlist is not found."""

    pass


class TrackNotFoundError(PlaylistError):
    """Exception raised when a track is not found."""

    pass


class PlaylistValidationError(PlaylistError):
    """Exception raised when playlist validation fails."""

    pass


# === NFC Exceptions ===


class NFCError(TombError):
    """Base exception for NFC-related errors."""

    pass


class NFCDeviceError(NFCError):
    """Exception raised when NFC device operations fail."""

    pass


class NFCTagError(NFCError):
    """Exception raised when NFC tag operations fail."""

    pass


# === Upload Exceptions ===


class UploadError(TombError):
    """Base exception for upload-related errors."""

    pass


class UploadValidationError(UploadError):
    """Exception raised when upload validation fails."""

    pass


class UploadStorageError(UploadError):
    """Exception raised when upload storage operations fail."""

    pass


# === Configuration Exceptions ===


class ConfigurationError(TombError):
    """Exception raised when configuration is invalid."""

    pass


class HardwareConfigurationError(ConfigurationError):
    """Exception raised when hardware configuration is invalid."""

    pass


# === Service Exceptions ===


class ServiceError(TombError):
    """Base exception for service-related errors."""

    pass


class ServiceUnavailableError(ServiceError):
    """Exception raised when a required service is unavailable."""

    pass


class ServiceInitializationError(ServiceError):
    """Exception raised when service initialization fails."""

    pass


# === Monitoring Exceptions ===


class MonitoringError(TombError):
    """Base exception for monitoring-related errors."""

    pass


class EventMonitoringError(MonitoringError):
    """Exception raised when event monitoring operations fail."""

    pass


class LoggingError(MonitoringError):
    """Exception raised when logging operations fail."""

    pass


# === Validation Exceptions ===


class ValidationError(TombError):
    """Exception raised when data validation fails."""

    pass


class SchemaValidationError(ValidationError):
    """Exception raised when schema validation fails."""

    pass


# === Network Exceptions ===


class NetworkError(TombError):
    """Base exception for network-related errors."""

    pass


class ConnectionError(NetworkError):
    """Exception raised when network connection fails."""

    pass


class TimeoutError(NetworkError):
    """Exception raised when network operation times out."""

    pass


# === Database Exceptions ===


class DatabaseError(TombError):
    """Base exception for database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    pass


class DatabaseMigrationError(DatabaseError):
    """Exception raised when database migration fails."""

    pass


# === File System Exceptions ===


class FileSystemError(TombError):
    """Base exception for file system-related errors."""

    pass


class FileNotFoundError(FileSystemError):
    """Exception raised when a file is not found."""

    pass


class FilePermissionError(FileSystemError):
    """Exception raised when file permission is denied."""

    pass


class DirectoryError(FileSystemError):
    """Exception raised when directory operations fail."""

    pass


# === Utility Functions ===


def get_exception_hierarchy() -> dict:
    """Get the complete exception hierarchy.

    Returns:
        Dictionary representing the exception hierarchy
    """
    return {
        "TombError": {
            "AudioError": [
                "AudioResourceError",
                "AudioResourceBusyError",
                "AudioDeviceError",
                "AudioFormatError",
                "AudioBufferError",
                "AudioBackendError",
            ],
            "PlaylistError": [
                "PlaylistNotFoundError",
                "TrackNotFoundError",
                "PlaylistValidationError",
            ],
            "NFCError": ["NFCDeviceError", "NFCTagError"],
            "UploadError": ["UploadValidationError", "UploadStorageError"],
            "ConfigurationError": ["HardwareConfigurationError"],
            "ServiceError": ["ServiceUnavailableError", "ServiceInitializationError"],
            "MonitoringError": ["EventMonitoringError", "LoggingError"],
            "ValidationError": ["SchemaValidationError"],
            "NetworkError": ["ConnectionError", "TimeoutError"],
            "DatabaseError": ["DatabaseConnectionError", "DatabaseMigrationError"],
            "FileSystemError": ["FileNotFoundError", "FilePermissionError", "DirectoryError"],
        }
    }


def is_critical_error(exception: Exception) -> bool:
    """Check if an exception should be considered critical.

    Args:
        exception: Exception to check

    Returns:
        True if exception is critical, False otherwise
    """
    critical_exceptions = (
        DatabaseConnectionError,
        ServiceInitializationError,
        HardwareConfigurationError,
        AudioDeviceError,
    )

    return isinstance(exception, critical_exceptions)


def get_error_category(exception: Exception) -> str:
    """Get the category of an exception.

    Args:
        exception: Exception to categorize

    Returns:
        String representing the error category
    """
    if isinstance(exception, AudioError):
        return "audio"
    elif isinstance(exception, PlaylistError):
        return "playlist"
    elif isinstance(exception, NFCError):
        return "nfc"
    elif isinstance(exception, UploadError):
        return "upload"
    elif isinstance(exception, ConfigurationError):
        return "configuration"
    elif isinstance(exception, ServiceError):
        return "service"
    elif isinstance(exception, MonitoringError):
        return "monitoring"
    elif isinstance(exception, ValidationError):
        return "validation"
    elif isinstance(exception, NetworkError):
        return "network"
    elif isinstance(exception, DatabaseError):
        return "database"
    elif isinstance(exception, FileSystemError):
        return "filesystem"
    else:
        return "unknown"
