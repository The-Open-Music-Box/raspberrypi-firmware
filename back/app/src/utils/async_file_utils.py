# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Asynchronous file utilities for non-blocking I/O operations.

This module provides async wrappers around common file operations to prevent
blocking the main thread during file system operations. It uses thread pools
to execute synchronous operations in a non-blocking manner.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Optional, Union, List
from concurrent.futures import ThreadPoolExecutor
import functools

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)

# Thread pool for file operations - managed lifecycle
_file_executor: Optional[ThreadPoolExecutor] = None


def get_file_executor() -> ThreadPoolExecutor:
    """Get or create the file executor thread pool.

    Returns:
        ThreadPoolExecutor for async file operations
    """
    global _file_executor
    if _file_executor is None:
        _file_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="async_file")
        logger.info("✅ File executor thread pool initialized")
    return _file_executor


def cleanup_file_executor():
    """Cleanup the file executor thread pool.

    Should be called during application shutdown.
    """
    global _file_executor
    if _file_executor is not None:
        _file_executor.shutdown(wait=True)
        _file_executor = None
        logger.info("✅ File executor thread pool cleaned up")


def _sync_to_async(func):
    """Decorator to convert synchronous functions to async using thread pool."""

    @functools.wraps(func)
    @handle_errors("async_wrapper")
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        executor = get_file_executor()
        result = await loop.run_in_executor(executor, func, *args, **kwargs)
        return result

    return async_wrapper


class AsyncFileUtils:
    """Async file utilities for non-blocking file operations."""

    @staticmethod
    async def exists(path: Union[str, Path]) -> bool:
        """Check if a file or directory exists asynchronously.

        Args:
            path: Path to check

        Returns:
            True if the path exists, False otherwise
        """

        @_sync_to_async
        def _exists(p):
            return Path(p).exists()

        return await _exists(path)

    @staticmethod
    async def is_file(path: Union[str, Path]) -> bool:
        """Check if a path is a file asynchronously.

        Args:
            path: Path to check

        Returns:
            True if the path is a file, False otherwise
        """

        @_sync_to_async
        def _is_file(p):
            return Path(p).is_file()

        return await _is_file(path)

    @staticmethod
    async def is_dir(path: Union[str, Path]) -> bool:
        """Check if a path is a directory asynchronously.

        Args:
            path: Path to check

        Returns:
            True if the path is a directory, False otherwise
        """

        @_sync_to_async
        def _is_dir(p):
            return Path(p).is_dir()

        return await _is_dir(path)

    @staticmethod
    async def mkdir(path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory asynchronously.

        Args:
            path: Path to create
            parents: Create parent directories if needed
            exist_ok: Don't raise error if directory exists
        """

        @_sync_to_async
        def _mkdir(p, parents, exist_ok):
            Path(p).mkdir(parents=parents, exist_ok=exist_ok)

        await _mkdir(path, parents, exist_ok)

    @staticmethod
    async def unlink(path: Union[str, Path], missing_ok: bool = False) -> None:
        """Remove a file asynchronously.

        Args:
            path: Path to remove
            missing_ok: Don't raise error if file doesn't exist
        """

        @_sync_to_async
        def _unlink(p, missing_ok):
            try:
                Path(p).unlink()
            except FileNotFoundError:
                if not missing_ok:
                    raise

        await _unlink(path, missing_ok)

    @staticmethod
    async def read_text(path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Read text from a file asynchronously.

        Args:
            path: Path to read from
            encoding: Text encoding

        Returns:
            File contents as string
        """

        @_sync_to_async
        def _read_text(p, encoding):
            return Path(p).read_text(encoding=encoding)

        return await _read_text(path, encoding)

    @staticmethod
    async def write_text(path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
        """Write text to a file asynchronously.

        Args:
            path: Path to write to
            content: Text content to write
            encoding: Text encoding
        """

        @_sync_to_async
        def _write_text(p, content, encoding):
            Path(p).write_text(content, encoding=encoding)

        await _write_text(path, content, encoding)

    @staticmethod
    async def read_bytes(path: Union[str, Path]) -> bytes:
        """Read bytes from a file asynchronously.

        Args:
            path: Path to read from

        Returns:
            File contents as bytes
        """

        @_sync_to_async
        def _read_bytes(p):
            return Path(p).read_bytes()

        return await _read_bytes(path)

    @staticmethod
    async def write_bytes(path: Union[str, Path], content: bytes) -> None:
        """Write bytes to a file asynchronously.

        Args:
            path: Path to write to
            content: Bytes content to write
        """

        @_sync_to_async
        def _write_bytes(p, content):
            Path(p).write_bytes(content)

        await _write_bytes(path, content)

    @staticmethod
    async def stat(path: Union[str, Path]) -> os.stat_result:
        """Get file statistics asynchronously.

        Args:
            path: Path to get stats for

        Returns:
            File statistics
        """

        @_sync_to_async
        def _stat(p):
            return Path(p).stat()

        return await _stat(path)

    @staticmethod
    async def listdir(path: Union[str, Path]) -> List[str]:
        """List directory contents asynchronously.

        Args:
            path: Directory path to list

        Returns:
            List of filenames in the directory
        """

        @_sync_to_async
        def _listdir(p):
            return [item.name for item in Path(p).iterdir()]

        return await _listdir(path)

    @staticmethod
    async def glob(path: Union[str, Path], pattern: str) -> List[Path]:
        """Glob pattern matching asynchronously.

        Args:
            path: Base path to search from
            pattern: Glob pattern

        Returns:
            List of matching paths
        """

        @_sync_to_async
        def _glob(p, pattern):
            return list(Path(p).glob(pattern))

        return await _glob(path, pattern)

    @staticmethod
    async def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Copy a file asynchronously.

        Args:
            src: Source file path
            dst: Destination file path
        """

        @_sync_to_async
        def _copy_file(src, dst):
            import shutil

            shutil.copy2(src, dst)

        await _copy_file(src, dst)

    @staticmethod
    async def move_file(src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move/rename a file asynchronously.

        Args:
            src: Source file path
            dst: Destination file path
        """

        @_sync_to_async
        def _move_file(src, dst):
            import shutil

            shutil.move(src, dst)

        await _move_file(src, dst)

    @staticmethod
    async def get_file_size(path: Union[str, Path]) -> int:
        """Get file size asynchronously.

        Args:
            path: Path to get size for

        Returns:
            File size in bytes
        """

        @_sync_to_async
        def _get_size(p):
            return Path(p).stat().st_size

        return await _get_size(path)

    @staticmethod
    @handle_errors("safe_delete")
    async def safe_delete(path: Union[str, Path]) -> bool:
        """Safely delete a file with error handling.

        Args:
            path: Path to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        await AsyncFileUtils.unlink(path, missing_ok=True)
        logger.debug(f"Successfully deleted file: {path}")
        return True

    @staticmethod
    @handle_errors("ensure_directory")
    async def ensure_directory(path: Union[str, Path]) -> bool:
        """Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure

        Returns:
            True if directory exists or was created successfully
        """
        await AsyncFileUtils.mkdir(path, parents=True, exist_ok=True)
        logger.debug(f"Directory ensured: {path}")
        return True


# Convenience functions for common operations
async def aexists(path: Union[str, Path]) -> bool:
    """Async version of Path.exists()"""
    return await AsyncFileUtils.exists(path)


async def ais_file(path: Union[str, Path]) -> bool:
    """Async version of Path.is_file()"""
    return await AsyncFileUtils.is_file(path)


async def ais_dir(path: Union[str, Path]) -> bool:
    """Async version of Path.is_dir()"""
    return await AsyncFileUtils.is_dir(path)


async def amkdir(path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
    """Async version of Path.mkdir()"""
    await AsyncFileUtils.mkdir(path, parents, exist_ok)


async def aunlink(path: Union[str, Path], missing_ok: bool = False) -> None:
    """Async version of Path.unlink()"""
    await AsyncFileUtils.unlink(path, missing_ok)


def cleanup_file_executor():
    """Clean up the file executor thread pool."""
    _file_executor.shutdown(wait=True)
    logger.info("File executor thread pool cleaned up")
