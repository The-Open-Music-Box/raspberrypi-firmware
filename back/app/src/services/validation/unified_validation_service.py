# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified Validation Service

This service centralizes all validation logic to eliminate the 45+ duplicated
validation patterns across routes, services, and domain layers.
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import os
import re
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field = field


class UnifiedValidationService:
    """
    Service centralisé pour toutes les validations.

    Élimine les duplications dans:
    - Validation des playlists (4 niveaux différents)
    - Validation des tracks (3+ services)
    - Validation des fichiers audio répétée
    - Patterns de validation inconsistants
    """

    # Validation constants
    MAX_PLAYLIST_TITLE_LENGTH = 255
    MAX_PLAYLIST_DESCRIPTION_LENGTH = 1000
    MAX_TRACK_TITLE_LENGTH = 255
    MAX_FILENAME_LENGTH = 255
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

    SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}
    SUPPORTED_MIME_TYPES = {
        "audio/mpeg",
        "audio/wav",
        "audio/flac",
        "audio/mp4",
        "audio/ogg",
        "audio/aac",
        "audio/x-ms-wma",
    }

    @staticmethod
    def validate_playlist_data(
        data: Dict[str, Any], context: str = "api", required_fields: Optional[List[str]] = None
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Valide les données d'une playlist de manière contextuelle.

        Remplace les validations dupliquées dans:
        - Routes API (validation Pydantic)
        - Application Services (validation métier)
        - Domain Models (validation entité)
        - Repository (validation persistance)

        Args:
            data: Données de playlist à valider
            context: Contexte de validation ('api', 'domain', 'repository', 'update')
            required_fields: Champs requis spécifiques

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Default required fields by context
        if required_fields is None:
            if context == "api":
                required_fields = ["title"]
            elif context == "domain":
                required_fields = ["title"]
            elif context == "repository":
                required_fields = ["title", "id"]
            elif context == "update":
                required_fields = []  # Updates can be partial
            else:
                required_fields = ["title"]

        # Check required fields
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append({"field": field, "message": f"{field} is required"})

        # Validate title
        title = data.get("title", "").strip()
        if title:  # Only validate if present
            if len(title) == 0:
                errors.append({"field": "title", "message": "Title cannot be empty"})
            elif len(title) > UnifiedValidationService.MAX_PLAYLIST_TITLE_LENGTH:
                errors.append(
                    {
                        "field": "title",
                        "message": f"Title too long (max {UnifiedValidationService.MAX_PLAYLIST_TITLE_LENGTH} chars)",
                    }
                )
            elif not UnifiedValidationService._is_valid_string(title):
                errors.append({"field": "title", "message": "Title contains invalid characters"})

        # Validate description
        description = data.get("description", "")
        if description:
            if len(description) > UnifiedValidationService.MAX_PLAYLIST_DESCRIPTION_LENGTH:
                errors.append(
                    {
                        "field": "description",
                        "message": f"Description too long (max {UnifiedValidationService.MAX_PLAYLIST_DESCRIPTION_LENGTH} chars)",
                    }
                )

        # Validate ID format if provided
        playlist_id = data.get("id")
        if playlist_id and context in ["repository", "update"]:
            if not UnifiedValidationService._is_valid_id(playlist_id):
                errors.append({"field": "id", "message": "Invalid ID format"})

        # Context-specific validations
        if context == "api":
            # API-specific validations
            pass
        elif context == "domain":
            # Domain-specific validations
            tracks = data.get("tracks", [])
            if isinstance(tracks, list):
                for i, track in enumerate(tracks):
                    track_valid, track_errors = UnifiedValidationService.validate_track_data(
                        track, context="domain"
                    )
                    if not track_valid:
                        for error in track_errors:
                            errors.append(
                                {
                                    "field": f"tracks[{i}].{error.get('field', 'unknown')}",
                                    "message": error.get("message", "Invalid track"),
                                }
                            )

        return len(errors) == 0, errors

    @staticmethod
    @handle_service_errors("unified_validation")
    def validate_track_data(
        data: Dict[str, Any], context: str = "upload", validate_file_exists: bool = True
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Valide les données d'une track.

        Remplace les validations dupliquées dans:
        - Upload service (validation fichier)
        - Application service (validation métier)
        - Domain layer (validation entité)

        Args:
            data: Données de track à valider
            context: Contexte ('upload', 'domain', 'api', 'database')
            validate_file_exists: Vérifier l'existence du fichier

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Validate title
        title = data.get("title", "").strip()
        if not title:
            errors.append({"field": "title", "message": "Track title is required"})
        elif len(title) > UnifiedValidationService.MAX_TRACK_TITLE_LENGTH:
            errors.append(
                {
                    "field": "title",
                    "message": f"Track title too long (max {UnifiedValidationService.MAX_TRACK_TITLE_LENGTH} chars)",
                }
            )

        # Validate track number
        track_number = data.get("track_number", 0)
        if not isinstance(track_number, int) or track_number < 0:
            errors.append(
                {"field": "track_number", "message": "Track number must be a non-negative integer"}
            )
        elif track_number > 9999:
            errors.append({"field": "track_number", "message": "Track number too high (max 9999)"})

        # Validate filename
        filename = data.get("filename", "").strip()
        if context in ["upload", "database"] and not filename:
            errors.append({"field": "filename", "message": "Filename is required"})
        elif filename:
            if len(filename) > UnifiedValidationService.MAX_FILENAME_LENGTH:
                errors.append(
                    {
                        "field": "filename",
                        "message": f"Filename too long (max {UnifiedValidationService.MAX_FILENAME_LENGTH} chars)",
                    }
                )
            elif not UnifiedValidationService._is_valid_filename(filename):
                errors.append({"field": "filename", "message": "Invalid filename format"})

        # Validate file_path and existence
        file_path = data.get("file_path", "").strip()
        if context in ["upload", "domain"] and file_path:
            # Validate file extension
            path_obj = Path(file_path)
            extension = path_obj.suffix.lower()

            if extension not in UnifiedValidationService.SUPPORTED_AUDIO_EXTENSIONS:
                errors.append(
                    {
                        "field": "file_path",
                        "message": f"Unsupported audio format: {extension}. Supported: {', '.join(UnifiedValidationService.SUPPORTED_AUDIO_EXTENSIONS)}",
                    }
                )

            # Validate file existence if requested
            if validate_file_exists and not os.path.exists(file_path):
                errors.append(
                    {"field": "file_path", "message": f"Audio file not found: {file_path}"}
                )

            # Validate file size if file exists
            elif validate_file_exists and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size > UnifiedValidationService.MAX_FILE_SIZE:
                    errors.append(
                        {
                            "field": "file_path",
                            "message": f"File too large: {file_size} bytes (max {UnifiedValidationService.MAX_FILE_SIZE})",
                        }
                    )
                elif file_size == 0:
                    errors.append({"field": "file_path", "message": "Audio file is empty"})
        # Validate duration
        duration_ms = data.get("duration_ms", data.get("duration", 0))
        if duration_ms is not None:
            if not isinstance(duration_ms, (int, float)) or duration_ms < 0:
                errors.append(
                    {"field": "duration_ms", "message": "Duration must be a non-negative number"}
                )
            elif duration_ms > 24 * 60 * 60 * 1000:  # 24 hours max
                errors.append(
                    {"field": "duration_ms", "message": "Duration too long (max 24 hours)"}
                )

        # Validate optional metadata
        for field in ["artist", "album"]:
            value = data.get(field)
            if value and len(str(value)) > 255:
                errors.append({"field": field, "message": f"{field} too long (max 255 chars)"})

        return len(errors) == 0, errors

    @staticmethod
    @handle_service_errors("unified_validation")
    def validate_audio_file(file_path: str, check_content: bool = False) -> Tuple[bool, str]:
        """
        Valide un fichier audio physique.

        Args:
            file_path: Chemin vers le fichier
            check_content: Vérifier le contenu du fichier (plus lent)

        Returns:
            (is_valid, error_message)
        """
        # Check file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        # Check if it's a file (not directory)
        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"
        # Check file extension
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        if extension not in UnifiedValidationService.SUPPORTED_AUDIO_EXTENSIONS:
            return False, f"Unsupported audio format: {extension}"
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "Audio file is empty"
        if file_size > UnifiedValidationService.MAX_FILE_SIZE:
            return False, f"File too large: {file_size} bytes"
        # Basic content validation if requested
        if check_content:
            with open(file_path, "rb") as f:
                # Read first few bytes to check for audio signatures
                header = f.read(16)
                if not UnifiedValidationService._has_audio_signature(header, extension):
                    return False, f"File does not appear to be valid audio: {extension}"

    @staticmethod
    def validate_upload_session_data(data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Valide les données d'une session d'upload.

        Args:
            data: Données de session d'upload

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Validate filename
        filename = data.get("filename", "").strip()
        if not filename:
            errors.append(
                {"field": "filename", "message": "Filename is required for upload session"}
            )
        else:
            # Check extension
            extension = Path(filename).suffix.lower()
            if extension not in UnifiedValidationService.SUPPORTED_AUDIO_EXTENSIONS:
                errors.append(
                    {"field": "filename", "message": f"Unsupported file type: {extension}"}
                )

        # Validate file size
        file_size = data.get("file_size")
        if file_size is None:
            errors.append({"field": "file_size", "message": "File size is required"})
        elif not isinstance(file_size, int) or file_size <= 0:
            errors.append({"field": "file_size", "message": "File size must be a positive integer"})
        elif file_size > UnifiedValidationService.MAX_FILE_SIZE:
            errors.append(
                {
                    "field": "file_size",
                    "message": f"File too large: {file_size} bytes (max {UnifiedValidationService.MAX_FILE_SIZE})",
                }
            )

        # Validate chunk size
        chunk_size = data.get("chunk_size", 1024 * 1024)  # Default 1MB
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            errors.append(
                {"field": "chunk_size", "message": "Chunk size must be a positive integer"}
            )
        elif chunk_size > 10 * 1024 * 1024:  # Max 10MB chunks
            errors.append({"field": "chunk_size", "message": "Chunk size too large (max 10MB)"})

        return len(errors) == 0, errors

    @staticmethod
    def validate_nfc_association_data(data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Valide les données d'association NFC.

        Args:
            data: Données d'association NFC

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Validate tag_id
        tag_id = data.get("tag_id", "").strip()
        if not tag_id:
            errors.append({"field": "tag_id", "message": "NFC tag ID is required"})
        elif not re.match(r"^[A-Fa-f0-9]{8,32}$", tag_id):
            errors.append(
                {"field": "tag_id", "message": "Invalid NFC tag ID format (expected hex string)"}
            )

        # Validate playlist_id
        playlist_id = data.get("playlist_id", "").strip()
        if not playlist_id:
            errors.append({"field": "playlist_id", "message": "Playlist ID is required"})
        elif not UnifiedValidationService._is_valid_id(playlist_id):
            errors.append({"field": "playlist_id", "message": "Invalid playlist ID format"})

        return len(errors) == 0, errors

    @staticmethod
    def _is_valid_string(value: str) -> bool:
        """Vérifie si une chaîne est valide (pas de caractères de contrôle)."""
        if not value:
            return False
        # Check for control characters (except tabs and newlines in descriptions)
        return all(ord(char) >= 32 or char in "\t\n" for char in value)

    @staticmethod
    def _is_valid_filename(filename: str) -> bool:
        """Vérifie si un nom de fichier est valide."""
        if not filename:
            return False

        # Check for invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in invalid_chars for char in filename):
            return False

        # Check for reserved names on Windows
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False

        return True

    @staticmethod
    def _is_valid_id(id_value: str) -> bool:
        """Vérifie si un ID est valide (UUID ou format similaire)."""
        if not id_value:
            return False

        # Accept UUID format or alphanumeric with dashes/underscores
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", id_value))

    @staticmethod
    def _has_audio_signature(header: bytes, extension: str) -> bool:
        """
        Vérifie si l'en-tête du fichier correspond à un format audio.

        Args:
            header: Premiers bytes du fichier
            extension: Extension du fichier

        Returns:
            True si l'en-tête semble valide
        """
        if not header:
            return False

        # MP3 signatures
        if extension == ".mp3":
            # ID3v2 or MP3 sync
            return header[:3] == b"ID3" or header[:2] == b"\xff\xfb" or header[:2] == b"\xff\xf3"

        # WAV signature
        elif extension == ".wav":
            return header[:4] == b"RIFF"

        # FLAC signature
        elif extension == ".flac":
            return header[:4] == b"fLaC"

        # OGG signature
        elif extension == ".ogg":
            return header[:4] == b"OggS"

        # M4A/MP4 signatures
        elif extension in [".m4a", ".mp4"]:
            return b"ftyp" in header[:16]

        # For unknown formats, assume valid
        return True
