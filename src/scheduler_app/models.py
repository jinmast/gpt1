from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class UnifiedItem:
    """A source-agnostic scheduler entity used by the sync pipeline."""

    id: str
    source: str
    source_id: str
    title: str
    notes: str | None = None
    due_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str = "active"
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class SourceRecord:
    """Raw data fetched from a specific source system."""

    source: str
    source_id: str
    payload: dict[str, Any]
    updated_at: datetime
    deleted: bool = False


@dataclass(slots=True)
class SyncDecision:
    """Conflict handling result for one unified item."""

    action: str
    winner: UnifiedItem | None = None
    merged: UnifiedItem | None = None
    reason: str = ""
