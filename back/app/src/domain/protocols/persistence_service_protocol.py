# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Persistence Service Protocol for Domain Layer

Pure domain interface for data persistence operations following DDD principles.
This abstraction ensures Domain remains persistence-ignorant while still being
able to define contracts for data storage. Infrastructure implementations
must implement this protocol.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager


class PersistenceServiceProtocol(ABC):
    """Protocol for database operations in the domain layer.

    This is a pure domain interface that defines what database operations
    the domain needs without coupling to any specific database implementation.
    """

    @abstractmethod
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper lifecycle management.

        Yields:
            Database connection ready for operations
        """
        pass

    @abstractmethod
    @contextmanager
    def get_transaction(self):
        """Get a database transaction with automatic commit/rollback.

        Yields:
            Database connection within a transaction context
        """
        pass

    @abstractmethod
    def execute_query(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "query"
    ) -> List[Any]:
        """Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Query parameters
            operation_name: Operation name for logging/monitoring

        Returns:
            List of result rows
        """
        pass

    @abstractmethod
    def execute_single(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "query_single"
    ) -> Optional[Any]:
        """Execute a SELECT query and return single result.

        Args:
            query: SQL query string
            params: Query parameters
            operation_name: Operation name for logging/monitoring

        Returns:
            Single row or None
        """
        pass

    @abstractmethod
    def execute_command(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "command"
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE command.

        Args:
            query: SQL command string
            params: Command parameters
            operation_name: Operation name for logging/monitoring

        Returns:
            Number of affected rows
        """
        pass

    @abstractmethod
    def execute_insert(
        self,
        query: str,
        params: Union[tuple, dict] = None,
        operation_name: str = "insert"
    ) -> str:
        """Execute an INSERT command and return the new row ID.

        Args:
            query: SQL INSERT string
            params: Insert parameters
            operation_name: Operation name for logging/monitoring

        Returns:
            Last inserted row ID
        """
        pass

    @abstractmethod
    def execute_batch(
        self,
        operations: List[Dict[str, Any]],
        operation_name: str = "batch"
    ) -> List[Any]:
        """Execute multiple operations in a single transaction.

        Args:
            operations: List of operations with 'query', 'params', 'type'
            operation_name: Operation name for logging/monitoring

        Returns:
            List of results from each operation
        """
        pass

    @abstractmethod
    def get_health_info(self) -> Dict[str, Any]:
        """Get database health information.

        Returns:
            Dictionary with health status and metadata
        """
        pass