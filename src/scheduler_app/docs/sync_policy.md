# Sync Policy

## 1) Source priority

If two sources update the same logical item at the same timestamp, the higher-priority source wins. Configure priority as an ordered list (left = high priority):

```python
SyncPolicy(source_priority=["google_calendar", "notion", "todoist"])
```

Unknown sources are treated as the lowest priority.

## 2) Conflict resolution strategy

The sync engine supports two strategies:

- `last_write_wins` (default): choose the item with the most recent `updated_at`. On ties, use source priority.
- `field_merge`: resolve each field individually. Prefer values from the most recent update; on ties, prefer higher-priority sources.

## 3) Delete propagation

- If `propagate_deletes=False`, deleted source records are ignored.
- If `propagate_deletes=True`, the engine writes a tombstone (`status="deleted"`) and removes the source mapping.
- Mapping cleanup only removes the deleted source relation, so other source links to the same unified item can remain.

## 4) Mapping-table upsert behavior

For every successful sync write:

1. Resolve `source_id -> unified_id` using `MappingStore`.
2. Reuse existing `unified_id` when available; otherwise create a new one.
3. Upsert the unified entity in repository storage.
4. Upsert mapping (`source_id ↔ unified_id`) for traceability and idempotency.
