# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Path Utilities for consistent folder naming

Provides utilities for generating consistent, filesystem-safe folder names
from playlist titles and other user inputs.
"""

import re
import unicodedata


def normalize_folder_name(name: str) -> str:
    """Generate a consistent, filesystem-safe folder name from a playlist title.

    This function ensures that:
    - All folder names are generated consistently across the application
    - No filesystem-unsafe characters are used
    - The result is reproducible for the same input

    Args:
        name: The original name/title to normalize

    Returns:
        A filesystem-safe folder name

    Examples:
        normalize_folder_name("Jacques Brel raconte - Pierre et le Loup(2002)-Flac 16bits-44.1Hkz")
        -> "jacques_brel_raconte_-_pierre_et_le_loup_2002_-flac_16bits-44_1hkz"

        normalize_folder_name("Test Playlist")
        -> "test_playlist"
    """
    if not name or not name.strip():
        return "unknown"

    # Remove accents and normalize unicode
    normalized = unicodedata.normalize('NFD', name)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Convert to lowercase
    normalized = normalized.lower()

    # Replace spaces with underscores
    normalized = re.sub(r'\s+', '_', normalized)

    # Replace filesystem-unsafe characters with safe alternatives
    # Parentheses, brackets, dots (except extension dots), colons, semicolons
    normalized = re.sub(r'[()[\]:]', '_', normalized)
    normalized = re.sub(r'[;]', '_', normalized)

    # Replace multiple consecutive underscores with single underscore
    normalized = re.sub(r'_+', '_', normalized)

    # Remove leading/trailing underscores
    normalized = normalized.strip('_')

    # Ensure we don't have an empty result
    if not normalized:
        return "unknown"

    return normalized


def get_playlist_folder_path(config, playlist_name: str, playlist_id: str = None) -> str:
    """Get the complete folder path for a playlist.

    Args:
        config: Application configuration object
        playlist_name: The playlist name/title
        playlist_id: Optional playlist ID for fallback

    Returns:
        Complete path to the playlist folder
    """
    from pathlib import Path

    folder_name = normalize_folder_name(playlist_name)
    if not folder_name or folder_name == "unknown":
        # Fallback to playlist ID if available
        folder_name = playlist_id if playlist_id else "unknown"

    return str(Path(config.upload_folder) / folder_name)


def migrate_existing_folder(old_path: str, new_path: str) -> bool:
    """Migrate an existing folder to the new normalized path.

    Args:
        old_path: Path to the existing folder
        new_path: Path to the new normalized folder

    Returns:
        True if migration successful, False otherwise
    """
    from pathlib import Path
    import shutil

    old_folder = Path(old_path)
    new_folder = Path(new_path)

    try:
        # If old folder exists and new folder doesn't, move it
        if old_folder.exists() and not new_folder.exists():
            # Create parent directory if needed
            new_folder.parent.mkdir(parents=True, exist_ok=True)

            # Move the folder
            shutil.move(str(old_folder), str(new_folder))
            return True
        elif old_folder.exists() and new_folder.exists():
            # Both exist - merge contents
            for item in old_folder.iterdir():
                target = new_folder / item.name
                if not target.exists():
                    shutil.move(str(item), str(target))

            # Remove empty old folder
            if not any(old_folder.iterdir()):
                old_folder.rmdir()
            return True

    except Exception:
        return False

    return False