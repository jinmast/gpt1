from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from scheduler_app.models import SourceRecord, SyncDecision, UnifiedItem
from scheduler_app.sync.mapping_store import MappingStore


class SyncSource:
    """Source interface for scheduler data providers."""

    name: str

    def fetch(self) -> list[SourceRecord]:
        raise NotImplementedError


class UnifiedRepository:
    """Persistence interface for unified entities."""

    def get(self, unified_id: str) -> UnifiedItem | None:
        raise NotImplementedError

    def upsert(self, item: UnifiedItem) -> UnifiedItem:
        raise NotImplementedError


@dataclass(slots=True)
class SyncPolicy:
    source_priority: list[str]
    strategy: str = "last_write_wins"
    propagate_deletes: bool = False

    def priority_rank(self, source: str) -> int:
        try:
            return self.source_priority.index(source)
        except ValueError:
            return len(self.source_priority)


class SyncEngine:
    """Fetch -> normalize -> map/upsert -> conflict resolution pipeline."""

    def __init__(
        self,
        sources: list[SyncSource],
        mapping_store: MappingStore,
        repository: UnifiedRepository,
        policy: SyncPolicy,
    ) -> None:
        self.sources = sources
        self.mapping_store = mapping_store
        self.repository = repository
        self.policy = policy

    def run(self) -> list[UnifiedItem]:
        synced: list[UnifiedItem] = []
        for source in self.sources:
            records = source.fetch()
            for record in records:
                synced_item = self._process_record(record)
                if synced_item:
                    synced.append(synced_item)
        return synced

    def _process_record(self, record: SourceRecord) -> UnifiedItem | None:
        unified_id = self.mapping_store.get_unified_id(record.source, record.source_id)
        current = self.repository.get(unified_id) if unified_id else None

        if record.deleted and self.policy.propagate_deletes:
            if unified_id:
                tombstone = self._build_tombstone(record, unified_id)
                saved = self.repository.upsert(tombstone)
                self.mapping_store.delete_by_source(record.source, record.source_id)
                return saved
            return None

        candidate = self._normalize(record, unified_id=unified_id)
        decision = self._resolve_conflict(current=current, incoming=candidate)

        to_save = decision.winner if decision.action == "winner" else decision.merged
        if not to_save:
            return None

        saved = self.repository.upsert(to_save)
        self.mapping_store.upsert(record.source, record.source_id, saved.id)
        return saved

    def _normalize(self, record: SourceRecord, unified_id: str | None = None) -> UnifiedItem:
        payload = record.payload
        return UnifiedItem(
            id=unified_id or str(uuid4()),
            source=record.source,
            source_id=record.source_id,
            title=payload.get("title", ""),
            notes=payload.get("notes"),
            due_at=payload.get("due_at"),
            start_at=payload.get("start_at"),
            end_at=payload.get("end_at"),
            status=payload.get("status", "active"),
            updated_at=record.updated_at,
        )

    def _resolve_conflict(self, current: UnifiedItem | None, incoming: UnifiedItem) -> SyncDecision:
        if current is None:
            return SyncDecision(action="winner", winner=incoming, reason="new_item")

        if self.policy.strategy == "field_merge":
            merged = self._merge_fields(current, incoming)
            return SyncDecision(action="merged", merged=merged, reason="field_merge")

        winner = self._last_write_wins(current, incoming)
        return SyncDecision(action="winner", winner=winner, reason="last_write_wins")

    def _last_write_wins(self, current: UnifiedItem, incoming: UnifiedItem) -> UnifiedItem:
        if incoming.updated_at > current.updated_at:
            return incoming
        if incoming.updated_at < current.updated_at:
            return current

        incoming_rank = self.policy.priority_rank(incoming.source)
        current_rank = self.policy.priority_rank(current.source)
        return incoming if incoming_rank < current_rank else current

    def _merge_fields(self, current: UnifiedItem, incoming: UnifiedItem) -> UnifiedItem:
        def pick_field(current_value: object, incoming_value: object) -> object:
            if incoming.updated_at > current.updated_at:
                return incoming_value if incoming_value is not None else current_value
            if incoming.updated_at < current.updated_at:
                return current_value

            incoming_rank = self.policy.priority_rank(incoming.source)
            current_rank = self.policy.priority_rank(current.source)
            return incoming_value if incoming_rank < current_rank and incoming_value is not None else current_value

        return UnifiedItem(
            id=current.id,
            source=incoming.source,
            source_id=incoming.source_id,
            title=str(pick_field(current.title, incoming.title)),
            notes=pick_field(current.notes, incoming.notes),
            due_at=pick_field(current.due_at, incoming.due_at),
            start_at=pick_field(current.start_at, incoming.start_at),
            end_at=pick_field(current.end_at, incoming.end_at),
            status=str(pick_field(current.status, incoming.status)),
            updated_at=max(current.updated_at, incoming.updated_at, datetime.utcnow()),
        )

    def _build_tombstone(self, record: SourceRecord, unified_id: str) -> UnifiedItem:
        return UnifiedItem(
            id=unified_id,
            source=record.source,
            source_id=record.source_id,
            title="",
            notes="Deleted at source",
            status="deleted",
            updated_at=record.updated_at,
        )
