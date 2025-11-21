# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for progress_utils utility.
"""

import pytest
from app.src.utils.progress_utils import (
    calculate_progress,
    calculate_progress_safe,
    format_progress,
    calculate_remaining,
    is_complete,
    calculate_progress_ratio,
)


class TestCalculateProgress:
    """Test suite for calculate_progress function."""

    def test_basic_percentage_calculation(self):
        """Test basic percentage calculation."""
        assert calculate_progress(50, 100) == 50.0
        assert calculate_progress(25, 100) == 25.0
        assert calculate_progress(75, 100) == 75.0

    def test_complete_progress(self):
        """Test 100% completion."""
        assert calculate_progress(100, 100) == 100.0

    def test_no_progress(self):
        """Test 0% completion."""
        assert calculate_progress(0, 100) == 0.0

    def test_fractional_percentage(self):
        """Test fractional percentage calculation."""
        assert calculate_progress(1, 3) == 33.33
        assert calculate_progress(2, 3) == 66.67

    def test_precision_control(self):
        """Test precision parameter."""
        assert calculate_progress(1, 3, precision=0) == 33.0
        assert calculate_progress(1, 3, precision=1) == 33.3
        assert calculate_progress(1, 3, precision=2) == 33.33
        assert calculate_progress(1, 3, precision=4) == 33.3333

    def test_zero_total_with_zero_current(self):
        """Test handling of zero total and zero current."""
        assert calculate_progress(0, 0) == 0.0

    def test_zero_total_with_positive_current(self):
        """Test handling of zero total with positive current."""
        assert calculate_progress(5, 0) == 100.0

    def test_negative_total(self):
        """Test handling of negative total."""
        assert calculate_progress(50, -100) == 100.0

    def test_current_exceeds_total(self):
        """Test handling when current exceeds total."""
        assert calculate_progress(150, 100) == 100.0

    def test_negative_current(self):
        """Test handling of negative current."""
        assert calculate_progress(-10, 100) == 0.0

    def test_float_values(self):
        """Test with float values."""
        assert calculate_progress(1.5, 3.0) == 50.0
        assert calculate_progress(2.75, 5.5) == 50.0

    def test_large_numbers(self):
        """Test with large numbers."""
        assert calculate_progress(1000000, 2000000) == 50.0


class TestCalculateProgressSafe:
    """Test suite for calculate_progress_safe function."""

    def test_normal_progress_clamped(self):
        """Test that normal progress is properly clamped."""
        assert calculate_progress_safe(50, 100) == 50.0

    def test_exceeding_progress_clamped_to_100(self):
        """Test that progress exceeding 100% is clamped."""
        assert calculate_progress_safe(150, 100) == 100.0

    def test_negative_progress_clamped_to_0(self):
        """Test that negative progress is clamped to 0."""
        assert calculate_progress_safe(-10, 100) == 0.0

    def test_zero_total_handled_safely(self):
        """Test safe handling of zero total."""
        result = calculate_progress_safe(0, 0)
        assert 0.0 <= result <= 100.0


class TestFormatProgress:
    """Test suite for format_progress function."""

    def test_format_with_percentage_symbol(self):
        """Test that result includes percentage symbol."""
        assert format_progress(50, 100) == "50.0%"

    def test_format_fractional_percentage(self):
        """Test formatting of fractional percentages."""
        assert format_progress(1, 3) == "33.33%"
        assert format_progress(2, 3) == "66.67%"

    def test_format_complete_progress(self):
        """Test formatting of 100% progress."""
        assert format_progress(100, 100) == "100.0%"

    def test_format_zero_progress(self):
        """Test formatting of 0% progress."""
        assert format_progress(0, 100) == "0.0%"

    def test_format_with_custom_precision(self):
        """Test formatting with custom precision."""
        assert format_progress(1, 3, precision=0) == "33.0%"
        assert format_progress(1, 3, precision=1) == "33.3%"
        assert format_progress(1, 3, precision=4) == "33.3333%"


class TestCalculateRemaining:
    """Test suite for calculate_remaining function."""

    def test_calculate_remaining_basic(self):
        """Test basic remaining calculation."""
        assert calculate_remaining(30, 100) == 70
        assert calculate_remaining(25, 100) == 75

    def test_calculate_remaining_complete(self):
        """Test remaining when complete."""
        assert calculate_remaining(100, 100) == 0

    def test_calculate_remaining_exceeds_total(self):
        """Test remaining when current exceeds total."""
        assert calculate_remaining(120, 100) == 0

    def test_calculate_remaining_float_values(self):
        """Test remaining with float values."""
        assert calculate_remaining(2.5, 10.0) == 7.5

    def test_calculate_remaining_no_progress(self):
        """Test remaining with no progress."""
        assert calculate_remaining(0, 100) == 100

    def test_calculate_remaining_preserves_type(self):
        """Test that type is preserved."""
        # Integer inputs
        result_int = calculate_remaining(30, 100)
        assert isinstance(result_int, int)

        # Float inputs
        result_float = calculate_remaining(30.0, 100.0)
        assert isinstance(result_float, float)


class TestIsComplete:
    """Test suite for is_complete function."""

    def test_complete_when_equal(self):
        """Test completion when current equals total."""
        assert is_complete(100, 100) is True

    def test_complete_when_exceeds(self):
        """Test completion when current exceeds total."""
        assert is_complete(101, 100) is True

    def test_not_complete_when_less(self):
        """Test not complete when current is less than total."""
        assert is_complete(99, 100) is False
        assert is_complete(50, 100) is False
        assert is_complete(0, 100) is False

    def test_complete_with_float_values(self):
        """Test completion with float values."""
        assert is_complete(10.0, 10.0) is True
        assert is_complete(10.1, 10.0) is True
        assert is_complete(9.9, 10.0) is False


class TestCalculateProgressRatio:
    """Test suite for calculate_progress_ratio function."""

    def test_ratio_half_complete(self):
        """Test ratio for 50% completion."""
        assert calculate_progress_ratio(50, 100) == 0.5

    def test_ratio_complete(self):
        """Test ratio for 100% completion."""
        assert calculate_progress_ratio(100, 100) == 1.0

    def test_ratio_no_progress(self):
        """Test ratio for 0% completion."""
        assert calculate_progress_ratio(0, 100) == 0.0

    def test_ratio_fractional(self):
        """Test ratio for fractional progress."""
        assert calculate_progress_ratio(1, 3) == 0.3333
        assert calculate_progress_ratio(2, 3) == 0.6667

    def test_ratio_precision_control(self):
        """Test precision control for ratio."""
        assert calculate_progress_ratio(1, 3, precision=1) == 0.3
        assert calculate_progress_ratio(1, 3, precision=2) == 0.33
        assert calculate_progress_ratio(1, 3, precision=4) == 0.3333

    def test_ratio_handles_zero_total(self):
        """Test ratio handling of zero total."""
        result = calculate_progress_ratio(0, 0)
        assert 0.0 <= result <= 1.0

    def test_ratio_handles_exceeding_progress(self):
        """Test ratio when current exceeds total."""
        assert calculate_progress_ratio(150, 100) == 1.0


class TestEdgeCases:
    """Test edge cases across all functions."""

    def test_very_small_numbers(self):
        """Test with very small numbers."""
        assert calculate_progress(0.001, 0.01) == 10.0

    def test_very_large_numbers(self):
        """Test with very large numbers."""
        assert calculate_progress(1000000000, 2000000000) == 50.0

    def test_mixed_integer_and_float(self):
        """Test mixing integers and floats."""
        assert calculate_progress(50, 100.0) == 50.0
        assert calculate_progress(50.0, 100) == 50.0


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_file_upload_progress(self):
        """Test typical file upload progress calculation."""
        # 1MB of 10MB uploaded
        chunks_received = 10
        total_chunks = 100
        progress = calculate_progress(chunks_received, total_chunks)
        assert progress == 10.0

        # Progress as we upload
        assert calculate_progress(25, 100) == 25.0
        assert calculate_progress(50, 100) == 50.0
        assert calculate_progress(75, 100) == 75.0
        assert calculate_progress(100, 100) == 100.0

    def test_batch_processing_progress(self):
        """Test batch processing progress tracking."""
        items_processed = 47
        total_items = 200
        progress = calculate_progress(items_processed, total_items)
        assert progress == 23.5

        remaining = calculate_remaining(items_processed, total_items)
        assert remaining == 153

    def test_download_progress_display(self):
        """Test progress display formatting."""
        # Download started
        assert format_progress(0, 1000) == "0.0%"

        # In progress
        assert format_progress(350, 1000) == "35.0%"

        # Almost done
        assert format_progress(995, 1000) == "99.5%"

        # Complete
        assert format_progress(1000, 1000) == "100.0%"

    def test_progress_bar_ui_integration(self):
        """Test progress ratio for UI progress bars."""
        # Progress bar expects 0-1 range
        ratio = calculate_progress_ratio(350, 1000)
        assert 0.0 <= ratio <= 1.0
        assert ratio == 0.35
