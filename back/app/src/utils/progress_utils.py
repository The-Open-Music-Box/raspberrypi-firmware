# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Progress Calculation Utilities

Centralized logic for calculating progress percentages.
This eliminates duplication of progress calculation formulas across the application.
"""

from typing import Union


def calculate_progress(
    current: Union[int, float],
    total: Union[int, float],
    precision: int = 2,
) -> float:
    """
    Calculate progress percentage with safe division.

    This function centralizes the progress calculation formula that was duplicated
    across upload handling and other progress tracking code:

    ```python
    progress_percent = round(
        (chunks_received / max(1, total_chunks)) * 100, 2
    )
    ```

    Args:
        current: Current progress value (e.g., chunks received, bytes processed)
        total: Total value (e.g., total chunks, total bytes)
        precision: Number of decimal places to round to (default: 2)

    Returns:
        Progress percentage as a float, rounded to specified precision

    Examples:
        >>> calculate_progress(50, 100)
        50.0
        >>> calculate_progress(1, 3)
        33.33
        >>> calculate_progress(0, 0)  # Safe handling of zero total
        0.0
        >>> calculate_progress(5, 0)  # Safe handling of zero total
        100.0
        >>> calculate_progress(100, 100)
        100.0
        >>> calculate_progress(75, 100, precision=0)
        75.0
        >>> calculate_progress(1, 3, precision=4)
        33.3333
    """
    # Handle edge case: zero or negative total
    if total <= 0:
        # If total is 0 and current is also 0, consider it 0% complete
        # If total is 0 but current is positive, consider it 100% complete
        return 0.0 if current <= 0 else 100.0

    # Handle edge case: current exceeds total
    if current > total:
        return 100.0

    # Handle edge case: negative current
    if current < 0:
        return 0.0

    # Calculate percentage
    percentage = (current / total) * 100

    # Round to specified precision
    return round(percentage, precision)


def calculate_progress_safe(
    current: Union[int, float],
    total: Union[int, float],
    precision: int = 2,
) -> float:
    """
    Calculate progress with additional safety checks and clamping.

    This version ensures the result is always between 0 and 100.

    Args:
        current: Current progress value
        total: Total value
        precision: Number of decimal places to round to

    Returns:
        Progress percentage clamped between 0.0 and 100.0

    Examples:
        >>> calculate_progress_safe(50, 100)
        50.0
        >>> calculate_progress_safe(-10, 100)
        0.0
        >>> calculate_progress_safe(150, 100)
        100.0
    """
    progress = calculate_progress(current, total, precision)
    return max(0.0, min(100.0, progress))


def format_progress(
    current: Union[int, float],
    total: Union[int, float],
    precision: int = 2,
) -> str:
    """
    Calculate and format progress as a string with percentage symbol.

    Args:
        current: Current progress value
        total: Total value
        precision: Number of decimal places to round to

    Returns:
        Formatted progress string (e.g., "75.50%")

    Examples:
        >>> format_progress(50, 100)
        '50.0%'
        >>> format_progress(1, 3)
        '33.33%'
        >>> format_progress(100, 100)
        '100.0%'
    """
    progress = calculate_progress(current, total, precision)
    return f"{progress}%"


def calculate_remaining(
    current: Union[int, float],
    total: Union[int, float],
) -> Union[int, float]:
    """
    Calculate remaining value (total - current).

    Args:
        current: Current progress value
        total: Total value

    Returns:
        Remaining value (same type as inputs)

    Examples:
        >>> calculate_remaining(30, 100)
        70
        >>> calculate_remaining(2.5, 10.0)
        7.5
        >>> calculate_remaining(100, 100)
        0
        >>> calculate_remaining(120, 100)
        0
    """
    remaining = total - current
    return max(0, remaining)


def is_complete(
    current: Union[int, float],
    total: Union[int, float],
) -> bool:
    """
    Check if progress is complete.

    Args:
        current: Current progress value
        total: Total value

    Returns:
        True if current >= total, False otherwise

    Examples:
        >>> is_complete(100, 100)
        True
        >>> is_complete(99, 100)
        False
        >>> is_complete(101, 100)
        True
    """
    return current >= total


def calculate_progress_ratio(
    current: Union[int, float],
    total: Union[int, float],
    precision: int = 4,
) -> float:
    """
    Calculate progress as a ratio between 0 and 1.

    Useful for progress bars and other UI components that expect
    a 0-1 range instead of 0-100.

    Args:
        current: Current progress value
        total: Total value
        precision: Number of decimal places to round to

    Returns:
        Progress ratio between 0.0 and 1.0

    Examples:
        >>> calculate_progress_ratio(50, 100)
        0.5
        >>> calculate_progress_ratio(1, 3)
        0.3333
        >>> calculate_progress_ratio(100, 100)
        1.0
        >>> calculate_progress_ratio(0, 100)
        0.0
    """
    percentage = calculate_progress(current, total, precision + 2)
    ratio = percentage / 100
    return round(ratio, precision)
