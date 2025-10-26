# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock FileSystem for testing.

This module provides a mock implementation of file system operations
for testing without actual file system interactions.
"""

import os
from pathlib import Path
from typing import Dict, List, Set, Union


class MockFileSystem:
    """Mock file system implementation for testing.

    Simulates file system operations in memory without actual disk I/O,
    enabling safe testing of file-related functionality.
    """

    def __init__(self):
        """Initialize the mock file system."""
        self._files: Dict[str, bytes] = {}
        self._directories: Set[str] = set()
        self._metadata: Dict[str, Dict[str, any]] = {}
        self._permissions: Dict[str, int] = {}

        # Add root directory
        self._directories.add("/")

    def exists(self, path: Union[str, Path]) -> bool:
        """Check if a file or directory exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)
        return normalized in self._files or normalized in self._directories

    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if path is a file, False otherwise
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)
        return normalized in self._files

    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path is a directory, False otherwise
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)
        return normalized in self._directories

    def mkdir(self, path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory.

        Args:
            path: Directory path to create
            parents: Create parent directories if they don't exist
            exist_ok: Don't raise error if directory already exists

        Raises:
            FileExistsError: If directory exists and exist_ok is False
            FileNotFoundError: If parent directory doesn't exist and parents is False
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized in self._directories:
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {normalized}")
            return

        if normalized in self._files:
            raise FileExistsError(f"File exists at path: {normalized}")

        parent = os.path.dirname(normalized)
        if parent and parent != normalized:
            if parent not in self._directories:
                if parents:
                    self.mkdir(parent, parents=True, exist_ok=True)
                else:
                    raise FileNotFoundError(f"Parent directory not found: {parent}")

        self._directories.add(normalized)

    def rmdir(self, path: Union[str, Path]) -> None:
        """Remove a directory.

        Args:
            path: Directory path to remove

        Raises:
            FileNotFoundError: If directory doesn't exist
            OSError: If directory is not empty
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._directories:
            raise FileNotFoundError(f"Directory not found: {normalized}")

        # Check if directory is empty
        for file_path in self._files:
            if file_path.startswith(normalized + os.sep):
                raise OSError(f"Directory not empty: {normalized}")

        for dir_path in self._directories:
            if dir_path.startswith(normalized + os.sep) and dir_path != normalized:
                raise OSError(f"Directory not empty: {normalized}")

        self._directories.remove(normalized)
        if normalized in self._metadata:
            del self._metadata[normalized]

    def rmtree(self, path: Union[str, Path]) -> None:
        """Remove a directory tree.

        Args:
            path: Root directory path to remove

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._directories:
            raise FileNotFoundError(f"Directory not found: {normalized}")

        # Remove all files in the directory tree
        files_to_remove = [
            file_path
            for file_path in self._files
            if file_path.startswith(normalized + os.sep) or file_path == normalized
        ]

        for file_path in files_to_remove:
            del self._files[file_path]
            if file_path in self._metadata:
                del self._metadata[file_path]

        # Remove all subdirectories
        dirs_to_remove = [
            dir_path
            for dir_path in self._directories
            if dir_path.startswith(normalized + os.sep) or dir_path == normalized
        ]

        for dir_path in dirs_to_remove:
            self._directories.remove(dir_path)
            if dir_path in self._metadata:
                del self._metadata[dir_path]

    def write_text(self, path: Union[str, Path], content: str) -> None:
        """Write text content to a file.

        Args:
            path: File path
            content: Text content to write
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        # Ensure parent directory exists
        parent = os.path.dirname(normalized)
        if parent and parent not in self._directories:
            raise FileNotFoundError(f"Parent directory not found: {parent}")

        self._files[normalized] = content.encode("utf-8")
        self._metadata[normalized] = {"size": len(content.encode("utf-8")), "type": "text"}

    def write_bytes(self, path: Union[str, Path], content: bytes) -> None:
        """Write binary content to a file.

        Args:
            path: File path
            content: Binary content to write
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        # Ensure parent directory exists
        parent = os.path.dirname(normalized)
        if parent and parent not in self._directories:
            raise FileNotFoundError(f"Parent directory not found: {parent}")

        self._files[normalized] = content
        self._metadata[normalized] = {"size": len(content), "type": "binary"}

    def read_text(self, path: Union[str, Path]) -> str:
        """Read text content from a file.

        Args:
            path: File path

        Returns:
            Text content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {normalized}")

        return self._files[normalized].decode("utf-8")

    def read_bytes(self, path: Union[str, Path]) -> bytes:
        """Read binary content from a file.

        Args:
            path: File path

        Returns:
            Binary content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {normalized}")

        return self._files[normalized]

    def remove(self, path: Union[str, Path]) -> None:
        """Remove a file.

        Args:
            path: File path to remove

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {normalized}")

        del self._files[normalized]
        if normalized in self._metadata:
            del self._metadata[normalized]

    def listdir(self, path: Union[str, Path]) -> List[str]:
        """List directory contents.

        Args:
            path: Directory path

        Returns:
            List of file/directory names

        Raises:
            FileNotFoundError: If directory doesn't exist
            NotADirectoryError: If path is not a directory
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._directories:
            if normalized in self._files:
                raise NotADirectoryError(f"Not a directory: {normalized}")
            raise FileNotFoundError(f"Directory not found: {normalized}")

        contents = []
        prefix = normalized + os.sep if normalized != "/" else "/"

        # Add direct file children
        for file_path in self._files:
            if file_path.startswith(prefix):
                relative = file_path[len(prefix) :]
                if os.sep not in relative:  # Direct child, not nested
                    contents.append(relative)

        # Add direct directory children
        for dir_path in self._directories:
            if dir_path.startswith(prefix) and dir_path != normalized:
                relative = dir_path[len(prefix) :]
                if os.sep not in relative:  # Direct child, not nested
                    contents.append(relative)

        return sorted(contents)

    def get_file_size(self, path: Union[str, Path]) -> int:
        """Get file size.

        Args:
            path: File path

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path_str = str(path)
        normalized = os.path.normpath(path_str)

        if normalized not in self._files:
            raise FileNotFoundError(f"File not found: {normalized}")

        return len(self._files[normalized])

    # Mock-specific testing methods
    def create_test_file(self, path: str, content: str = "test content") -> None:
        """Create a test file for testing purposes.

        Args:
            path: File path
            content: File content
        """
        # Ensure parent directories exist
        parent = os.path.dirname(path)
        if parent:
            parts = parent.split(os.sep)
            current_path = ""
            for part in parts:
                if part:
                    current_path = os.path.join(current_path, part)
                    if current_path not in self._directories:
                        self._directories.add(current_path)

        self.write_text(path, content)

    def create_test_directory(self, path: str) -> None:
        """Create a test directory for testing purposes.

        Args:
            path: Directory path
        """
        self.mkdir(path, parents=True, exist_ok=True)

    def get_all_files(self) -> List[str]:
        """Get all file paths for testing.

        Returns:
            List of all file paths
        """
        return list(self._files.keys())

    def get_all_directories(self) -> List[str]:
        """Get all directory paths for testing.

        Returns:
            List of all directory paths
        """
        return list(self._directories)

    def clear(self):
        """Clear all files and directories."""
        self._files.clear()
        self._directories.clear()
        self._metadata.clear()
        self._permissions.clear()
        # Re-add root directory
        self._directories.add("/")

    def reset(self):
        """Reset the mock file system to initial state."""
        self.clear()
