# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Common exceptions for TheOpenMusicBox application."""


class BusinessLogicError(Exception):
    """Exception raised when business logic rules are violated."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ValidationError(Exception):
    """Exception raised when data validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(Exception):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)