# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Base Session Entity

Provides common session management patterns to eliminate duplication.
Single Responsibility: Reusable session state management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import uuid4


class SessionStateType(Enum):
    """Base interface for session state enums.

    Subclasses should define their own specific states.
    """
    pass


@dataclass
class BaseSessionEntity(ABC):
    """
    Base class for domain session entities.

    Provides common patterns for:
    - Session ID generation
    - Timeout management
    - Expiration checking
    - Time remaining calculation

    Eliminates duplication between AssociationSession and UploadSession.
    """

    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_seconds: int = 300  # 5 minutes default

    @property
    def timeout_at(self) -> datetime:
        """
        Calculate when this session expires.

        Common pattern appearing in:
        - AssociationSession (lines 52-56)
        - UploadSession (lines 62-66)
        """
        return datetime.fromtimestamp(
            self.created_at.timestamp() + self.timeout_seconds, tz=timezone.utc
        )

    def is_expired(self) -> bool:
        """
        Check if this session has expired.

        Common pattern appearing in:
        - AssociationSession (lines 58-60)
        - UploadSession (lines 82-84)
        """
        return datetime.now(timezone.utc) > self.timeout_at

    def get_remaining_seconds(self) -> int:
        """
        Get remaining seconds before timeout.

        Common pattern appearing in:
        - AssociationSession (lines 131-137)
        - UploadSession (lines 168-174)
        """
        if self.is_expired():
            return 0

        remaining = self.timeout_at - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds()))

    @abstractmethod
    def is_active(self) -> bool:
        """
        Check if session is active.

        Implementation is domain-specific (depends on state enum).
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary for serialization.

        Subclasses should implement their specific serialization.
        """
        pass

    def _base_dict_fields(self) -> Dict[str, Any]:
        """
        Get common dictionary fields for serialization.

        Subclasses can use this to include common fields in to_dict().
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "timeout_at": self.timeout_at.isoformat(),
            "remaining_seconds": self.get_remaining_seconds(),
        }
