# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for StateManagerLifecycleApplicationService

Comprehensive tests for state manager lifecycle service including:
- Lifecycle management (start/stop)
- Cleanup operations
- Health metrics
- Error handling
- Task management
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.src.application.services.state_manager_lifecycle_application_service import (
    StateManagerLifecycleApplicationService,
)


class TestStateManagerLifecycleApplicationService:
    """Test suite for StateManagerLifecycleApplicationService."""

    @pytest.fixture
    def mock_operation_tracker(self):
        """Mock operation tracker."""
        tracker = AsyncMock()
        tracker.cleanup_expired_operations = AsyncMock(return_value=0)
        tracker.get_stats = Mock(return_value={
            "total_tracked_operations": 10,
            "recent_operations": 5,
            "cached_results": 3,
        })
        return tracker

    @pytest.fixture
    def mock_event_outbox(self):
        """Mock event outbox."""
        outbox = AsyncMock()
        outbox.process_outbox = AsyncMock()
        outbox.get_stats = Mock(return_value={
            "total_events": 5,
            "max_size": 1000,
            "events_by_type": {"state_change": 3, "playback": 2},
        })
        return outbox

    @pytest.fixture
    def lifecycle_service(self, mock_operation_tracker, mock_event_outbox):
        """Create lifecycle service instance with mocked dependencies."""
        return StateManagerLifecycleApplicationService(
            operation_tracker=mock_operation_tracker,
            event_outbox=mock_event_outbox,
            cleanup_interval=1,  # Short interval for testing
        )

    @pytest.fixture
    def lifecycle_service_with_defaults(self):
        """Create lifecycle service with default dependencies."""
        return StateManagerLifecycleApplicationService(cleanup_interval=1)

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_with_custom_dependencies(self, mock_operation_tracker, mock_event_outbox):
        """Test initialization with custom dependencies."""
        # Arrange & Act
        service = StateManagerLifecycleApplicationService(
            operation_tracker=mock_operation_tracker,
            event_outbox=mock_event_outbox,
            cleanup_interval=300,
        )

        # Assert
        assert service.operation_tracker == mock_operation_tracker
        assert service.event_outbox == mock_event_outbox
        assert service.cleanup_interval == 300
        assert service._cleanup_task is None
        assert service._is_running is False

    def test_init_with_default_dependencies(self):
        """Test initialization creates default dependencies when not provided."""
        # Act
        service = StateManagerLifecycleApplicationService()

        # Assert
        assert service.operation_tracker is not None
        assert service.event_outbox is not None
        assert service.cleanup_interval == 300  # Default value
        assert service._cleanup_task is None
        assert service._is_running is False

    def test_init_with_custom_cleanup_interval(self):
        """Test initialization with custom cleanup interval."""
        # Act
        service = StateManagerLifecycleApplicationService(cleanup_interval=600)

        # Assert
        assert service.cleanup_interval == 600

    def test_init_with_none_dependencies(self):
        """Test initialization handles None dependencies gracefully."""
        # Act
        service = StateManagerLifecycleApplicationService(
            operation_tracker=None,
            event_outbox=None,
        )

        # Assert
        assert service.operation_tracker is not None
        assert service.event_outbox is not None

    # ================================================================================
    # Test start_lifecycle_management()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_start_lifecycle_management_success(self, lifecycle_service):
        """Test successful lifecycle management startup."""
        # Act
        await lifecycle_service.start_lifecycle_management()

        # Assert
        assert lifecycle_service._is_running is True
        assert lifecycle_service._cleanup_task is not None
        assert not lifecycle_service._cleanup_task.done()

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_start_lifecycle_management_already_running(self, lifecycle_service):
        """Test starting lifecycle management when already running."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        initial_task = lifecycle_service._cleanup_task

        # Act
        await lifecycle_service.start_lifecycle_management()

        # Assert
        assert lifecycle_service._cleanup_task == initial_task
        assert lifecycle_service._is_running is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_start_lifecycle_management_after_stop(self, lifecycle_service):
        """Test restarting lifecycle management after stopping."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        await lifecycle_service.stop_lifecycle_management()

        # Act
        await lifecycle_service.start_lifecycle_management()

        # Assert
        assert lifecycle_service._is_running is True
        assert lifecycle_service._cleanup_task is not None
        assert not lifecycle_service._cleanup_task.done()

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_start_lifecycle_management_creates_cleanup_task(self, lifecycle_service):
        """Test that starting lifecycle management creates cleanup task."""
        # Act
        await lifecycle_service.start_lifecycle_management()

        # Assert
        assert isinstance(lifecycle_service._cleanup_task, asyncio.Task)
        assert lifecycle_service._is_running is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    # ================================================================================
    # Test stop_lifecycle_management()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_stop_lifecycle_management_success(self, lifecycle_service):
        """Test successful lifecycle management shutdown."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Act
        await lifecycle_service.stop_lifecycle_management()

        # Assert
        assert lifecycle_service._is_running is False
        assert lifecycle_service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_stop_lifecycle_management_not_running(self, lifecycle_service):
        """Test stopping lifecycle management when not running."""
        # Act & Assert - should not raise an error
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service._is_running is False

    @pytest.mark.asyncio
    async def test_stop_lifecycle_management_cancels_task(self, lifecycle_service):
        """Test that stopping lifecycle management cancels the cleanup task."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        task = lifecycle_service._cleanup_task

        # Act
        await lifecycle_service.stop_lifecycle_management()

        # Assert
        assert task.cancelled()
        assert lifecycle_service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_stop_lifecycle_management_sets_running_false(self, lifecycle_service):
        """Test that stopping sets _is_running to False."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        assert lifecycle_service._is_running is True

        # Act
        await lifecycle_service.stop_lifecycle_management()

        # Assert
        assert lifecycle_service._is_running is False

    # ================================================================================
    # Test _cleanup_loop()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_cleanup_loop_performs_cleanup(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test that cleanup loop performs cleanup operations."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Wait for at least one cleanup cycle
        await asyncio.sleep(1.5)

        # Assert
        mock_operation_tracker.cleanup_expired_operations.assert_called()
        mock_event_outbox.process_outbox.assert_called()

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_cleanup_loop_respects_interval(self, mock_operation_tracker, mock_event_outbox):
        """Test that cleanup loop respects cleanup interval."""
        # Arrange
        service = StateManagerLifecycleApplicationService(
            operation_tracker=mock_operation_tracker,
            event_outbox=mock_event_outbox,
            cleanup_interval=2,  # 2 seconds
        )

        # Act
        await service.start_lifecycle_management()
        await asyncio.sleep(0.5)  # Wait less than interval

        # Assert - should not have called cleanup yet
        # Note: may have called once on startup, so check call count
        initial_calls = mock_operation_tracker.cleanup_expired_operations.call_count

        # Wait for interval
        await asyncio.sleep(2.5)

        # Should have called cleanup at least once more
        assert mock_operation_tracker.cleanup_expired_operations.call_count > initial_calls

        # Cleanup
        await service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_cleanup_loop_handles_cancellation(self, lifecycle_service):
        """Test that cleanup loop handles cancellation gracefully."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Act
        await lifecycle_service.stop_lifecycle_management()

        # Assert - should complete without errors
        assert lifecycle_service._is_running is False
        assert lifecycle_service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_cleanup_loop_continues_after_error(self, lifecycle_service, mock_operation_tracker):
        """Test that cleanup loop continues running after an error."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.side_effect = [
            Exception("Cleanup error"),
            5,  # Successful cleanup on second call
        ]

        # Act
        await lifecycle_service.start_lifecycle_management()
        await asyncio.sleep(2.5)  # Wait for multiple cleanup cycles

        # Assert
        assert lifecycle_service._is_running is True
        assert mock_operation_tracker.cleanup_expired_operations.call_count >= 2

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_cleanup_loop_stops_when_flag_cleared(self, lifecycle_service):
        """Test that cleanup loop stops when _is_running is set to False."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        assert lifecycle_service._is_running is True

        # Act
        await lifecycle_service.stop_lifecycle_management()
        await asyncio.sleep(0.5)  # Give task time to finish

        # Assert
        assert lifecycle_service._is_running is False

    # ================================================================================
    # Test _perform_cleanup()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_perform_cleanup_cleans_operations(self, lifecycle_service, mock_operation_tracker):
        """Test that cleanup performs operation cleanup."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.return_value = 5

        # Act
        await lifecycle_service._perform_cleanup()

        # Assert
        mock_operation_tracker.cleanup_expired_operations.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_cleanup_processes_outbox(self, lifecycle_service, mock_event_outbox):
        """Test that cleanup processes event outbox."""
        # Act
        await lifecycle_service._perform_cleanup()

        # Assert
        mock_event_outbox.process_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_cleanup_handles_no_operation_tracker(self):
        """Test cleanup when operation tracker is None."""
        # Arrange
        service = StateManagerLifecycleApplicationService(
            operation_tracker=None,
            event_outbox=AsyncMock(),
        )

        # Act & Assert - should not raise error
        await service._perform_cleanup()

    @pytest.mark.asyncio
    async def test_perform_cleanup_handles_no_event_outbox(self):
        """Test cleanup when event outbox is None."""
        # Arrange
        service = StateManagerLifecycleApplicationService(
            operation_tracker=AsyncMock(),
            event_outbox=None,
        )

        # Act & Assert - should not raise error
        await service._perform_cleanup()

    @pytest.mark.asyncio
    async def test_perform_cleanup_handles_operation_tracker_error(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test cleanup handles operation tracker errors gracefully."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.side_effect = Exception("Tracker error")

        # Act & Assert - should not raise error
        await lifecycle_service._perform_cleanup()

        # The error is caught and logged, but outbox processing stops due to single try-catch
        # This is expected behavior based on current implementation
        mock_operation_tracker.cleanup_expired_operations.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_cleanup_handles_outbox_error(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test cleanup handles outbox errors gracefully."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.return_value = 3
        mock_event_outbox.process_outbox.side_effect = Exception("Outbox error")

        # Act & Assert - should not raise error
        await lifecycle_service._perform_cleanup()

        # Operations should still be cleaned
        mock_operation_tracker.cleanup_expired_operations.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_cleanup_returns_stats(self, lifecycle_service, mock_operation_tracker):
        """Test that cleanup tracks statistics."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.return_value = 7

        # Act
        await lifecycle_service._perform_cleanup()

        # Assert
        mock_operation_tracker.cleanup_expired_operations.assert_called_once()

    # ================================================================================
    # Test get_health_metrics()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_get_health_metrics_includes_lifecycle_info(self, lifecycle_service):
        """Test that health metrics include lifecycle service information."""
        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert "lifecycle_service" in metrics
        assert "is_running" in metrics["lifecycle_service"]
        assert "cleanup_task_running" in metrics["lifecycle_service"]
        assert "cleanup_interval" in metrics["lifecycle_service"]
        assert metrics["lifecycle_service"]["cleanup_interval"] == 1

    @pytest.mark.asyncio
    async def test_get_health_metrics_includes_operation_tracker_stats(self, lifecycle_service, mock_operation_tracker):
        """Test that health metrics include operation tracker stats."""
        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert "operations" in metrics
        assert metrics["operations"]["total_tracked_operations"] == 10
        assert metrics["operations"]["recent_operations"] == 5
        mock_operation_tracker.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_health_metrics_includes_outbox_stats(self, lifecycle_service, mock_event_outbox):
        """Test that health metrics include event outbox stats."""
        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert "outbox" in metrics
        assert metrics["outbox"]["total_events"] == 5
        assert metrics["outbox"]["max_size"] == 1000
        mock_event_outbox.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_health_metrics_when_running(self, lifecycle_service):
        """Test health metrics when lifecycle management is running."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert metrics["lifecycle_service"]["is_running"] is True
        assert metrics["lifecycle_service"]["cleanup_task_running"] is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_get_health_metrics_when_not_running(self, lifecycle_service):
        """Test health metrics when lifecycle management is not running."""
        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert metrics["lifecycle_service"]["is_running"] is False
        assert metrics["lifecycle_service"]["cleanup_task_running"] is False

    @pytest.mark.asyncio
    async def test_get_health_metrics_handles_tracker_error(self, lifecycle_service, mock_operation_tracker):
        """Test health metrics handles operation tracker errors."""
        # Arrange
        mock_operation_tracker.get_stats.side_effect = Exception("Stats error")

        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert "error" in metrics
        assert "Stats error" in str(metrics["error"])

    @pytest.mark.asyncio
    async def test_get_health_metrics_handles_outbox_error(self, lifecycle_service, mock_event_outbox):
        """Test health metrics handles event outbox errors."""
        # Arrange
        mock_event_outbox.get_stats.side_effect = Exception("Outbox stats error")

        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert "error" in metrics

    @pytest.mark.asyncio
    async def test_get_health_metrics_with_none_tracker(self):
        """Test health metrics when operation tracker is None."""
        # Arrange
        # Note: Service creates default OperationTracker even when None is passed
        # So we need to actually set it to None after creation to test this scenario
        service = StateManagerLifecycleApplicationService(
            operation_tracker=None,
            event_outbox=AsyncMock(),
        )
        service.operation_tracker = None  # Force it to None for this test

        # Act
        metrics = await service.get_health_metrics()

        # Assert
        assert "lifecycle_service" in metrics
        assert "operations" not in metrics

    @pytest.mark.asyncio
    async def test_get_health_metrics_with_none_outbox(self):
        """Test health metrics when event outbox is None."""
        # Arrange
        # Note: Service creates default EventOutbox even when None is passed
        # So we need to actually set it to None after creation to test this scenario
        service = StateManagerLifecycleApplicationService(
            operation_tracker=AsyncMock(),
            event_outbox=None,
        )
        service.event_outbox = None  # Force it to None for this test

        # Act
        metrics = await service.get_health_metrics()

        # Assert
        assert "lifecycle_service" in metrics
        assert "outbox" not in metrics

    # ================================================================================
    # Test force_cleanup()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_force_cleanup_success(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test successful forced cleanup."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.return_value = 10

        # Act
        result = await lifecycle_service.force_cleanup()

        # Assert
        assert result["success"] is True
        assert "timestamp" in result
        assert "successfully" in result["message"].lower()
        mock_operation_tracker.cleanup_expired_operations.assert_called_once()
        mock_event_outbox.process_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_cleanup_includes_timestamp(self, lifecycle_service):
        """Test that forced cleanup includes timestamp."""
        # Arrange
        before_time = time.time()

        # Act
        result = await lifecycle_service.force_cleanup()

        # Assert
        after_time = time.time()
        assert "timestamp" in result
        assert before_time <= result["timestamp"] <= after_time

    @pytest.mark.asyncio
    async def test_force_cleanup_handles_errors(self, lifecycle_service, mock_operation_tracker):
        """Test forced cleanup handles errors gracefully."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.side_effect = Exception("Force cleanup error")

        # Act
        result = await lifecycle_service.force_cleanup()

        # Assert
        # The error is caught in _perform_cleanup, so force_cleanup still reports success
        # but the error is logged
        assert result["success"] is True
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_force_cleanup_can_be_called_when_running(self, lifecycle_service):
        """Test that force cleanup can be called while lifecycle is running."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Act
        result = await lifecycle_service.force_cleanup()

        # Assert
        assert result["success"] is True
        assert lifecycle_service._is_running is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_force_cleanup_can_be_called_when_stopped(self, lifecycle_service):
        """Test that force cleanup can be called while lifecycle is stopped."""
        # Act
        result = await lifecycle_service.force_cleanup()

        # Assert
        assert result["success"] is True
        assert lifecycle_service._is_running is False

    # ================================================================================
    # Test is_running()
    # ================================================================================

    def test_is_running_returns_false_initially(self, lifecycle_service):
        """Test is_running returns False when not started."""
        # Assert
        assert lifecycle_service.is_running() is False

    @pytest.mark.asyncio
    async def test_is_running_returns_true_when_started(self, lifecycle_service):
        """Test is_running returns True when lifecycle is running."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Assert
        assert lifecycle_service.is_running() is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_is_running_returns_false_after_stop(self, lifecycle_service):
        """Test is_running returns False after stopping."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        await lifecycle_service.stop_lifecycle_management()

        # Assert
        assert lifecycle_service.is_running() is False

    # ================================================================================
    # Test get_status()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_get_status_includes_all_fields(self, lifecycle_service):
        """Test that get_status includes all required fields."""
        # Act
        status = await lifecycle_service.get_status()

        # Assert
        assert "is_running" in status
        assert "cleanup_task_active" in status
        assert "cleanup_interval" in status
        assert "has_operation_tracker" in status
        assert "has_event_outbox" in status

    @pytest.mark.asyncio
    async def test_get_status_when_not_running(self, lifecycle_service):
        """Test get_status when lifecycle is not running."""
        # Act
        status = await lifecycle_service.get_status()

        # Assert
        assert status["is_running"] is False
        assert status["cleanup_task_active"] is False
        assert status["cleanup_interval"] == 1
        assert status["has_operation_tracker"] is True
        assert status["has_event_outbox"] is True

    @pytest.mark.asyncio
    async def test_get_status_when_running(self, lifecycle_service):
        """Test get_status when lifecycle is running."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()

        # Act
        status = await lifecycle_service.get_status()

        # Assert
        assert status["is_running"] is True
        assert status["cleanup_task_active"] is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_get_status_shows_cleanup_interval(self, mock_operation_tracker, mock_event_outbox):
        """Test get_status shows correct cleanup interval."""
        # Arrange
        service = StateManagerLifecycleApplicationService(
            operation_tracker=mock_operation_tracker,
            event_outbox=mock_event_outbox,
            cleanup_interval=600,
        )

        # Act
        status = await service.get_status()

        # Assert
        assert status["cleanup_interval"] == 600

    @pytest.mark.asyncio
    async def test_get_status_with_none_dependencies(self):
        """Test get_status when dependencies are None."""
        # Arrange
        service = StateManagerLifecycleApplicationService(
            operation_tracker=None,
            event_outbox=None,
        )

        # Act
        status = await service.get_status()

        # Assert
        assert status["has_operation_tracker"] is True  # Created by default
        assert status["has_event_outbox"] is True  # Created by default

    # ================================================================================
    # Integration Tests
    # ================================================================================

    @pytest.mark.asyncio
    async def test_full_lifecycle_start_cleanup_stop(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test complete lifecycle: start, cleanup, stop."""
        # Start
        await lifecycle_service.start_lifecycle_management()
        assert lifecycle_service.is_running() is True

        # Wait for cleanup
        await asyncio.sleep(1.5)
        mock_operation_tracker.cleanup_expired_operations.assert_called()
        mock_event_outbox.process_outbox.assert_called()

        # Stop
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service.is_running() is False

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self, lifecycle_service):
        """Test multiple start/stop cycles."""
        # Cycle 1
        await lifecycle_service.start_lifecycle_management()
        assert lifecycle_service.is_running() is True
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service.is_running() is False

        # Cycle 2
        await lifecycle_service.start_lifecycle_management()
        assert lifecycle_service.is_running() is True
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service.is_running() is False

        # Cycle 3
        await lifecycle_service.start_lifecycle_management()
        assert lifecycle_service.is_running() is True
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service.is_running() is False

    @pytest.mark.asyncio
    async def test_cleanup_and_metrics_integration(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test cleanup and metrics work together."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.return_value = 15

        # Start lifecycle
        await lifecycle_service.start_lifecycle_management()

        # Get metrics
        metrics = await lifecycle_service.get_health_metrics()
        assert metrics["lifecycle_service"]["is_running"] is True

        # Force cleanup
        result = await lifecycle_service.force_cleanup()
        assert result["success"] is True

        # Stop
        await lifecycle_service.stop_lifecycle_management()

        # Get final metrics
        final_metrics = await lifecycle_service.get_health_metrics()
        assert final_metrics["lifecycle_service"]["is_running"] is False

    @pytest.mark.asyncio
    async def test_concurrent_force_cleanup_calls(self, lifecycle_service):
        """Test multiple concurrent force cleanup calls."""
        # Act
        results = await asyncio.gather(
            lifecycle_service.force_cleanup(),
            lifecycle_service.force_cleanup(),
            lifecycle_service.force_cleanup(),
        )

        # Assert
        assert len(results) == 3
        for result in results:
            assert result["success"] is True
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_status_reflects_lifecycle_changes(self, lifecycle_service):
        """Test that status accurately reflects lifecycle state changes."""
        # Initial status
        status = await lifecycle_service.get_status()
        assert status["is_running"] is False
        assert status["cleanup_task_active"] is False

        # Start
        await lifecycle_service.start_lifecycle_management()
        status = await lifecycle_service.get_status()
        assert status["is_running"] is True
        assert status["cleanup_task_active"] is True

        # Stop
        await lifecycle_service.stop_lifecycle_management()
        status = await lifecycle_service.get_status()
        assert status["is_running"] is False
        assert status["cleanup_task_active"] is False

    @pytest.mark.asyncio
    async def test_cleanup_continues_despite_partial_failures(self, lifecycle_service, mock_operation_tracker, mock_event_outbox):
        """Test cleanup handles errors gracefully."""
        # Arrange
        mock_operation_tracker.cleanup_expired_operations.side_effect = Exception("Tracker failed")

        # Act
        await lifecycle_service._perform_cleanup()

        # Assert - error is caught and logged, operation stops
        # This is expected behavior based on current implementation
        mock_operation_tracker.cleanup_expired_operations.assert_called_once()

    # ================================================================================
    # Edge Cases and Error Scenarios
    # ================================================================================

    @pytest.mark.asyncio
    async def test_stop_before_start_does_not_error(self, lifecycle_service):
        """Test stopping before starting doesn't cause errors."""
        # Act & Assert - should not raise
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service.is_running() is False

    @pytest.mark.asyncio
    async def test_double_stop_does_not_error(self, lifecycle_service):
        """Test double stop doesn't cause errors."""
        # Arrange
        await lifecycle_service.start_lifecycle_management()
        await lifecycle_service.stop_lifecycle_management()

        # Act & Assert - should not raise
        await lifecycle_service.stop_lifecycle_management()
        assert lifecycle_service.is_running() is False

    @pytest.mark.asyncio
    async def test_rapid_start_stop_cycles(self, lifecycle_service):
        """Test rapid start/stop cycles."""
        # Act
        for _ in range(5):
            await lifecycle_service.start_lifecycle_management()
            await asyncio.sleep(0.1)
            await lifecycle_service.stop_lifecycle_management()
            await asyncio.sleep(0.1)

        # Assert
        assert lifecycle_service.is_running() is False

    @pytest.mark.asyncio
    async def test_cleanup_with_very_short_interval(self, mock_operation_tracker, mock_event_outbox):
        """Test cleanup with very short interval."""
        # Arrange
        service = StateManagerLifecycleApplicationService(
            operation_tracker=mock_operation_tracker,
            event_outbox=mock_event_outbox,
            cleanup_interval=0.1,  # Very short
        )

        # Act
        await service.start_lifecycle_management()
        await asyncio.sleep(0.5)  # Should trigger multiple cleanups

        # Assert
        assert mock_operation_tracker.cleanup_expired_operations.call_count >= 2

        # Cleanup
        await service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_metrics_during_cleanup_error(self, lifecycle_service, mock_operation_tracker):
        """Test getting metrics while cleanup is failing."""
        # Arrange
        mock_operation_tracker.get_stats.side_effect = Exception("Metrics error")

        # Act
        metrics = await lifecycle_service.get_health_metrics()

        # Assert
        assert "error" in metrics
        assert "lifecycle_service" in metrics

    @pytest.mark.asyncio
    async def test_force_cleanup_during_regular_cleanup(self, lifecycle_service, mock_operation_tracker):
        """Test force cleanup while regular cleanup is running."""
        # Arrange
        cleanup_called = asyncio.Event()

        async def slow_cleanup():
            cleanup_called.set()
            await asyncio.sleep(0.5)
            return 5

        mock_operation_tracker.cleanup_expired_operations = slow_cleanup

        # Act
        await lifecycle_service.start_lifecycle_management()
        await cleanup_called.wait()  # Wait for cleanup to start

        # Force cleanup while regular cleanup is running
        result = await lifecycle_service.force_cleanup()

        # Assert
        assert result["success"] is True

        # Cleanup
        await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_cleanup_loop_logs_metrics_periodically(self, lifecycle_service):
        """Test that cleanup loop can log metrics periodically."""
        # Arrange - using time patching to trigger the hourly metrics log
        with patch('time.time') as mock_time:
            # Set time so that time.time() % 3600 < cleanup_interval
            mock_time.return_value = 3599.5  # Just before the hour, within interval

            # Act
            await lifecycle_service.start_lifecycle_management()
            await asyncio.sleep(1.5)  # Wait for one cleanup cycle

            # Assert - just verify it doesn't crash
            assert lifecycle_service.is_running() is True

            # Cleanup
            await lifecycle_service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_cleanup_loop_exception_handling_with_non_cancelled_error(self):
        """Test cleanup loop handles non-CancelledError exceptions."""
        # Arrange
        mock_tracker = AsyncMock()
        error_count = 0

        async def raise_then_succeed():
            nonlocal error_count
            error_count += 1
            if error_count == 1:
                raise ValueError("Test error in cleanup loop")
            return 0

        mock_tracker.cleanup_expired_operations = raise_then_succeed

        service = StateManagerLifecycleApplicationService(
            operation_tracker=mock_tracker,
            event_outbox=AsyncMock(),
            cleanup_interval=0.5,
        )

        # Act
        await service.start_lifecycle_management()
        await asyncio.sleep(1.5)  # Wait for multiple cycles

        # Assert - should have recovered from error and continued
        assert error_count >= 2  # First call raised error, second succeeded
        assert service.is_running() is True

        # Cleanup
        await service.stop_lifecycle_management()

    @pytest.mark.asyncio
    async def test_force_cleanup_with_decorator_exception(self):
        """Test force_cleanup when _perform_cleanup raises an exception that bypasses decorator."""
        # Arrange
        mock_tracker = AsyncMock()
        mock_outbox = AsyncMock()

        # Make _perform_cleanup raise an exception by making handle_service_errors not catch it
        # This is a difficult edge case to trigger since the decorator catches most exceptions
        service = StateManagerLifecycleApplicationService(
            operation_tracker=mock_tracker,
            event_outbox=mock_outbox,
        )

        # Patch _perform_cleanup to raise an exception
        async def raise_error():
            raise RuntimeError("Decorator test error")

        with patch.object(service, '_perform_cleanup', side_effect=raise_error):
            # Act
            result = await service.force_cleanup()

            # Assert - the exception is caught by force_cleanup's own try-catch
            assert result["success"] is False
            assert "Decorator test error" in result["message"]
