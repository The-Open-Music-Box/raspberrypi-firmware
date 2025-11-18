# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Minimal EventMonitor stub to avoid cross-layer imports.

This stub maintains API shape but does not subscribe to domain events.
"""

import importlib as _il
_logging = _il.import_module('logging')
from typing import Optional


class EventMonitor:
    """Minimal stub for event monitoring (no cross-layer imports)."""

    def __init__(self, max_trace_history: int = 1000, enable_file_logging: bool = False):
        self._is_active = False
        _logging.getLogger(__name__).info("📊 EventMonitor initialized (stub)")

    async def handle_event(self, event) -> None:  # pragma: no cover - stub
        return

    def shutdown(self) -> None:
        self._is_active = False
        _logging.getLogger(__name__).info("📊 EventMonitor shutdown")

    def get_monitoring_statistics(self) -> dict:
        return {"active": self._is_active, "stub": True}
