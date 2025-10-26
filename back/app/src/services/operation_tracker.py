# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Operation Tracker for Deduplication

Tracks client operations to prevent duplicate processing and caches results.
Extracted from StateManager for better separation of concerns.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from app.src.monitoring import get_logger
from app.src.config.socket_config import socket_config

logger = get_logger(__name__)


class OperationTracker:
    """
    Tracks client operations to prevent duplicate processing.

    Maintains a time-based cache of processed operations and their results
    to handle client retries and network issues gracefully.
    """

    def __init__(self):
        self._processed_operations: Dict[str, float] = {}  # client_op_id -> timestamp
        self._operation_results: Dict[str, Any] = {}  # client_op_id -> result for deduplication
        self._operations_lock = asyncio.Lock()

        # Configuration from SocketConfig
        self._dedup_window = socket_config.OPERATION_DEDUP_WINDOW_SEC
        self._result_ttl = socket_config.OPERATION_RESULT_TTL_SEC

        logger.info("OperationTracker initialized")

    async def is_operation_processed(self, client_op_id: str) -> bool:
        """Check if a client operation has already been processed with thread safety."""
        async with self._operations_lock:
            if client_op_id in self._processed_operations:
                # Clean up old operations outside the deduplication window
                current_time = time.time()
                if current_time - self._processed_operations[client_op_id] > self._dedup_window:
                    del self._processed_operations[client_op_id]
                    # Also clean up operation result if expired
                    if client_op_id in self._operation_results:
                        del self._operation_results[client_op_id]
                    return False
                return True
            return False

    async def mark_operation_processed(self, client_op_id: str, result: Any = None) -> None:
        """Mark a client operation as processed with thread safety and optional result caching."""
        async with self._operations_lock:
            current_time = time.time()
            self._processed_operations[client_op_id] = current_time

            # Cache result for duplicate requests
            if result is not None:
                self._operation_results[client_op_id] = {
                    "result": result,
                    "timestamp": current_time,
                }

            logger.debug(f"Operation {client_op_id} marked as processed")

    async def get_operation_result(self, client_op_id: str) -> Optional[Any]:
        """Get cached result for a processed operation."""
        async with self._operations_lock:
            if client_op_id in self._operation_results:
                result_data = self._operation_results[client_op_id]
                current_time = time.time()

                # Check if result is still valid
                if current_time - result_data["timestamp"] <= self._result_ttl:
                    return result_data["result"]
                else:
                    # Clean up expired result
                    del self._operation_results[client_op_id]
            return None

    async def cleanup_expired_operations(self) -> int:
        """Clean up expired operations and return count of cleaned items."""
        async with self._operations_lock:
            current_time = time.time()
            cleaned_ops = 0
            cleaned_results = 0

            # Clean up expired operations
            expired_ops = [
                op_id
                for op_id, timestamp in self._processed_operations.items()
                if current_time - timestamp > self._dedup_window
            ]

            for op_id in expired_ops:
                del self._processed_operations[op_id]
                cleaned_ops += 1

            # Clean up expired results
            expired_results = [
                op_id
                for op_id, result_data in self._operation_results.items()
                if current_time - result_data["timestamp"] > self._result_ttl
            ]

            for op_id in expired_results:
                del self._operation_results[op_id]
                cleaned_results += 1

            total_cleaned = cleaned_ops + cleaned_results
            if total_cleaned > 0:
                logger.debug(f"Cleaned up {cleaned_ops} operations and {cleaned_results} results",
                )

            return total_cleaned

    def get_stats(self) -> dict:
        """Get operation tracking statistics for monitoring."""
        current_time = time.time()

        # Count operations by age
        recent_ops = sum(
            1 for timestamp in self._processed_operations.values() if current_time - timestamp < 300
        )  # last 5 minutes

        old_ops = len(self._processed_operations) - recent_ops

        # Count results by age
        recent_results = sum(
            1
            for result_data in self._operation_results.values()
            if current_time - result_data["timestamp"] < 300
        )

        return {
            "total_tracked_operations": len(self._processed_operations),
            "recent_operations": recent_ops,
            "old_operations": old_ops,
            "cached_results": len(self._operation_results),
            "recent_cached_results": recent_results,
            "dedup_window_sec": self._dedup_window,
            "result_ttl_sec": self._result_ttl,
        }

    def get_processed_operations(self) -> Dict[str, float]:
        """Get all processed operations (for testing/debugging)."""
        return self._processed_operations.copy()

    async def clear_all(self) -> None:
        """Clear all tracked operations and results."""
        async with self._operations_lock:
            op_count = len(self._processed_operations)
            result_count = len(self._operation_results)

            self._processed_operations.clear()
            self._operation_results.clear()

            logger.info(f"Cleared {op_count} operations and {result_count} results")
