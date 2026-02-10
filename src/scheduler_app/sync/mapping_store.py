from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Mapping:
    source: str
    source_id: str
    unified_id: str


class MappingStore:
    """In-memory store for source_id <-> unified_id mappings."""

    def __init__(self) -> None:
        self._by_source: dict[tuple[str, str], str] = {}
        self._by_unified: dict[str, dict[str, str]] = {}

    def get_unified_id(self, source: str, source_id: str) -> str | None:
        return self._by_source.get((source, source_id))

    def get_source_ids(self, unified_id: str) -> dict[str, str]:
        return dict(self._by_unified.get(unified_id, {}))

    def upsert(self, source: str, source_id: str, unified_id: str) -> Mapping:
        previous_unified_id = self._by_source.get((source, source_id))
        if previous_unified_id and previous_unified_id != unified_id:
            previous_source_map = self._by_unified.get(previous_unified_id)
            if previous_source_map:
                previous_source_map.pop(source, None)
                if not previous_source_map:
                    self._by_unified.pop(previous_unified_id, None)

        self._by_source[(source, source_id)] = unified_id
        per_source = self._by_unified.setdefault(unified_id, {})
        per_source[source] = source_id
        return Mapping(source=source, source_id=source_id, unified_id=unified_id)

    def delete_by_source(self, source: str, source_id: str) -> None:
        unified_id = self._by_source.pop((source, source_id), None)
        if not unified_id:
            return

        source_map = self._by_unified.get(unified_id)
        if not source_map:
            return

        source_map.pop(source, None)
        if not source_map:
            self._by_unified.pop(unified_id, None)

    def delete_by_unified(self, unified_id: str) -> None:
        source_map = self._by_unified.pop(unified_id, {})
        for source, source_id in source_map.items():
            self._by_source.pop((source, source_id), None)
