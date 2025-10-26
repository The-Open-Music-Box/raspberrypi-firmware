# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
SQLite Database Service Implementation

Pure infrastructure implementation of PersistenceServiceProtocol.
Handles all SQLite-specific connection management, transactions, and operations.
"""

import sqlite3
import time
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
from pathlib import Path

import logging
from app.src.domain.protocols.persistence_service_protocol import PersistenceServiceProtocol
from app.src.data.connection_pool import ConnectionPool
from app.src.services.error.unified_error_decorator import handle_infrastructure_errors

def _handle_infrastructure_errors(component_name: str = "infrastructure"):
    return handle_infrastructure_errors(component_name)

logger = logging.getLogger(__name__)


class SQLiteDatabaseService(PersistenceServiceProtocol):
    """SQLite implementation of database service following DDD principles.

    This is a pure infrastructure service that implements the domain's
    PersistenceServiceProtocol using SQLite and connection pooling.
    """

    def __init__(self, database_path: str, pool_size: int = 5):
        """Initialize SQLite database service.

        Args:
            database_path: Path to SQLite database file
            pool_size: Number of connections to maintain in pool
        """
        self.database_path = database_path
        self.pool_size = pool_size
        self._connection_pool = None
        self._setup_database()

    def _setup_database(self):
        """Setup database file and connection pool."""
        # Ensure database directory exists
        db_file = Path(self.database_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Test basic connectivity
        try:
            with sqlite3.connect(self.database_path) as test_conn:
                test_conn.execute("SELECT 1")
            logger.info(f"✅ SQLite database accessible: {self.database_path}")
        except Exception as e:
            logger.error(f"❌ SQLite database setup failed: {e}")
            raise

        # Initialize connection pool
        self._connection_pool = ConnectionPool(
            db_path=self.database_path,
            pool_size=self.pool_size
        )

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper lifecycle management."""
        connection = None
        try:
            connection = self._connection_pool.get_connection()
            # Configure SQLite for optimal performance
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.execute("PRAGMA cache_size = 10000")

            yield connection
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
        finally:
            if connection:
                self._connection_pool.return_connection(connection)

    @contextmanager
    def get_transaction(self):
        """Get a database transaction with automatic commit/rollback."""
        with self.get_connection() as connection:
            try:
                connection.execute("BEGIN")
                yield connection
                connection.commit()
            except Exception as e:
                try:
                    connection.rollback()
                except:
                    pass
                raise

    @_handle_infrastructure_errors("database_service")
    def execute_query(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "query"
    ) -> List[Any]:
        """Execute a SELECT query and return results."""
        start_time = time.time()

        with self.get_connection() as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            results = cursor.fetchall()

            execution_time = (time.time() - start_time) * 1000
            if execution_time > 100:
                logger.warning(
                    f"⚠️ Slow query: {operation_name} took {execution_time:.2f}ms"
                )

            return results

    @_handle_infrastructure_errors("database_service")
    def execute_single(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "query_single"
    ) -> Optional[Any]:
        """Execute a SELECT query and return single result."""
        start_time = time.time()

        with self.get_connection() as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            result = cursor.fetchone()

            execution_time = (time.time() - start_time) * 1000
            if execution_time > 100:
                logger.warning(
                    f"⚠️ Slow query: {operation_name} took {execution_time:.2f}ms"
                )

            return result

    @_handle_infrastructure_errors("database_service")
    def execute_command(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "command"
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE command."""
        start_time = time.time()

        with self.get_transaction() as connection:
            cursor = connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            rowcount = cursor.rowcount

            execution_time = (time.time() - start_time) * 1000
            if execution_time > 100:
                logger.warning(
                    f"⚠️ Slow command: {operation_name} took {execution_time:.2f}ms"
                )

            return rowcount

    @_handle_infrastructure_errors("database_service")
    def execute_insert(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "insert"
    ) -> str:
        """Execute an INSERT command and return the new row ID."""
        start_time = time.time()

        with self.get_transaction() as connection:
            cursor = connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            lastrowid = str(cursor.lastrowid)

            execution_time = (time.time() - start_time) * 1000
            if execution_time > 100:
                logger.warning(
                    f"⚠️ Slow insert: {operation_name} took {execution_time:.2f}ms"
                )

            return lastrowid

    @_handle_infrastructure_errors("database_service")
    def execute_batch(
        self,
        operations: List[Dict[str, Any]],
        operation_name: str = "batch"
    ) -> List[Any]:
        """Execute multiple operations in a single transaction."""
        start_time = time.time()

        with self.get_transaction() as connection:
            cursor = connection.cursor()
            results = []

            for op in operations:
                query = op["query"]
                params = op.get("params")
                op_type = op.get("type", "command")

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if op_type == "insert":
                    results.append(str(cursor.lastrowid))
                elif op_type == "select":
                    results.append(cursor.fetchall())
                elif op_type == "select_one":
                    results.append(cursor.fetchone())
                else:
                    results.append(cursor.rowcount)

            execution_time = (time.time() - start_time) * 1000
            if execution_time > 200:
                logger.warning(
                    f"⚠️ Slow batch: {operation_name} took {execution_time:.2f}ms"
                )

            return results

    def get_health_info(self) -> Dict[str, Any]:
        """Get database health information."""
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()

                # Get database info
                cursor.execute("PRAGMA database_list")
                db_info = cursor.fetchall()

                cursor.execute("PRAGMA table_list")
                tables = cursor.fetchall()

                return {
                    "status": "healthy",
                    "database_path": self.database_path,
                    "database_info": [dict(row) for row in db_info],
                    "tables_count": len(tables),
                    "connection_pool_size": self.pool_size,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_path": self.database_path
            }

    def cleanup(self):
        """Clean up database service resources."""
        if self._connection_pool:
            self._connection_pool.close_all()
            logger.info("✅ SQLite database service cleaned up")
