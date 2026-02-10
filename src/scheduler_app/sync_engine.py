"""Calendar synchronization engine with retry and structured logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import random
import time
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryPolicy:
    """Retry policy configuration for sync operations."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    jitter_seconds: float = 0.2

    def backoff_for_attempt(self, attempt: int) -> float:
        """Return delay for `attempt` (1-indexed)."""
        exponential = self.base_delay_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0, self.jitter_seconds)
        return min(exponential + jitter, self.max_delay_seconds)


class SyncError(RuntimeError):
    """Raised when synchronization fails."""


class CalendarSyncEngine:
    """Engine that synchronizes events from providers with retries."""

    def __init__(self, retry_policy: RetryPolicy | None = None) -> None:
        self.retry_policy = retry_policy or RetryPolicy()

    def sync(
        self,
        source: str,
        fetch_events: Callable[[], list[dict[str, Any]]],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Sync events from a source and return summary."""
        request_id = request_id or str(uuid4())

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            started_at = datetime.now(timezone.utc)
            self._log(
                level=logging.INFO,
                event="sync_started",
                request_id=request_id,
                source=source,
                attempt=attempt,
            )
            try:
                events = fetch_events()
                processed = len(events)
                summary = {
                    "request_id": request_id,
                    "source": source,
                    "processed_count": processed,
                    "synced_at": started_at.isoformat(),
                }
                self._log(
                    level=logging.INFO,
                    event="sync_succeeded",
                    request_id=request_id,
                    source=source,
                    processed_count=processed,
                    attempt=attempt,
                )
                return summary
            except Exception as exc:  # noqa: BLE001
                failure_reason = str(exc)
                self._log(
                    level=logging.WARNING,
                    event="sync_failed",
                    request_id=request_id,
                    source=source,
                    attempt=attempt,
                    failure_reason=failure_reason,
                )

                if attempt >= self.retry_policy.max_attempts:
                    self._log(
                        level=logging.ERROR,
                        event="sync_exhausted",
                        request_id=request_id,
                        source=source,
                        processed_count=0,
                        failure_reason=failure_reason,
                    )
                    raise SyncError(
                        f"Sync failed for source '{source}' after {attempt} attempts: {failure_reason}"
                    ) from exc

                backoff = self.retry_policy.backoff_for_attempt(attempt)
                self._log(
                    level=logging.INFO,
                    event="sync_retry_scheduled",
                    request_id=request_id,
                    source=source,
                    attempt=attempt,
                    backoff_seconds=backoff,
                    failure_reason=failure_reason,
                )
                time.sleep(backoff)

        raise SyncError(f"Unexpected retry state for source '{source}'")

    def _log(self, level: int, event: str, **fields: Any) -> None:
        """Emit JSON structured logs."""
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        logger.log(level, json.dumps(payload, ensure_ascii=False, sort_keys=True))
