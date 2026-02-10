"""Scheduled sync job runner."""

from __future__ import annotations

import logging
from typing import Any, Callable

from scheduler_app.sync_engine import CalendarSyncEngine, SyncError

logger = logging.getLogger(__name__)


class SyncJob:
    """Periodic synchronization job wrapper."""

    def __init__(self, engine: CalendarSyncEngine | None = None) -> None:
        self.engine = engine or CalendarSyncEngine()

    def run_once(
        self,
        source: str,
        fetch_events: Callable[[], list[dict[str, Any]]],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Run one sync cycle and return job result."""
        try:
            result = self.engine.sync(source=source, fetch_events=fetch_events, request_id=request_id)
            logger.info("sync_job_completed source=%s request_id=%s", source, result["request_id"])
            return result
        except SyncError as exc:
            logger.error("sync_job_failed source=%s error=%s", source, exc)
            raise
