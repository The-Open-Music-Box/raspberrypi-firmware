# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Thread-safe SQLite connection pool for efficient database connection management.

Provides connection pooling with overflow handling and optimized SQLite settings.
"""

import sqlite3
from typing import Optional
import threading
import queue

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)


class ConnectionPool:
    """Thread-safe SQLite connection pool with optimized settings."""

    def __init__(
        self, db_path: str, pool_size: int = 5, max_overflow: int = 10, timeout: float = 30.0
    ):
        """Initialize the connection pool.

        Args:
            db_path: Path to the SQLite database file
            pool_size: Base number of connections to maintain in the pool
            max_overflow: Maximum number of overflow connections allowed
            timeout: Connection timeout in seconds
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self._pool = queue.Queue(maxsize=pool_size + max_overflow)
        self._current_size = 0
        self._lock = threading.Lock()
        self._created_connections = 0

        # Pre-populate the pool
        self._init_pool()

    def _init_pool(self):
        """Initialize the connection pool with base connections."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)

    @handle_errors("_create_connection")
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection with optimal settings."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        # Optimize SQLite settings
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=2000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=134217728")
        conn.execute("PRAGMA foreign_keys=ON")
        # Set row factory for dict-like access
        conn.row_factory = sqlite3.Row
        with self._lock:
            self._created_connections += 1
            self._current_size += 1
        logger.debug(f"Created DB connection (total: {self._created_connections})")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool.

        Returns:
            A database connection from the pool

        Raises:
            sqlite3.OperationalError: If the connection pool is exhausted
        """
        try:
            return self._pool.get(timeout=1.0)
        except queue.Empty:
            with self._lock:
                if self._current_size < self.pool_size + self.max_overflow:
                    conn = self._create_connection()
                    if conn:
                        return conn

            try:
                return self._pool.get(timeout=self.timeout)
            except queue.Empty as exc:
                raise sqlite3.OperationalError("Connection pool exhausted") from exc

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool.

        Args:
            conn: The database connection to return to the pool
        """
        if conn:
            try:
                conn.execute("SELECT 1").fetchone()
                conn.rollback()
                self._pool.put(conn, timeout=1.0)
            except (queue.Full, sqlite3.Error):
                self._close_connection(conn)

    def _close_connection(self, conn: sqlite3.Connection):
        """Close a connection and update counters.

        Args:
            conn: The database connection to close
        """
        try:
            conn.close()
        except sqlite3.Error:
            pass
        with self._lock:
            self._current_size -= 1

    def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
            except queue.Empty:
                break

    def get_statistics(self) -> dict:
        """Get connection pool statistics.

        Returns:
            Dictionary containing pool statistics
        """
        with self._lock:
            return {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "current_size": self._current_size,
                "created_connections": self._created_connections,
                "queue_size": self._pool.qsize(),
            }
