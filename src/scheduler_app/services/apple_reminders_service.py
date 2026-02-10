"""Apple Reminders service abstraction.

This module defines a shared task management interface and a concrete iCloud
CalDAV strategy intended for server-side or cross-platform deployments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class AppleRemindersError(Exception):
    """Base exception for all Apple Reminders service failures."""


class AppleRemindersPermissionError(AppleRemindersError):
    """Raised when access to reminders is denied or not granted."""


class AppleRemindersNetworkError(AppleRemindersError):
    """Raised when network-level issues occur while calling a provider."""


class AppleRemindersOperationError(AppleRemindersError):
    """Raised for provider failures that do not fit more specific categories."""


@dataclass(slots=True)
class ReminderTask:
    """Normalized reminder payload used across provider implementations."""

    task_id: str
    title: str
    notes: str | None = None
    due_at: datetime | None = None
    completed: bool = False


@dataclass(slots=True)
class ReminderTaskCreate:
    """Input model used when creating a reminder."""

    title: str
    notes: str | None = None
    due_at: datetime | None = None


@dataclass(slots=True)
class ReminderTaskUpdate:
    """Input model used when updating a reminder."""

    title: str | None = None
    notes: str | None = None
    due_at: datetime | None = None


@runtime_checkable
class AppleRemindersService(Protocol):
    """Common interface for Apple Reminders providers."""

    def list_tasks(self) -> list[ReminderTask]:
        """Return all tasks from the configured source."""

    def create_task(self, payload: ReminderTaskCreate) -> ReminderTask:
        """Create a task and return the normalized representation."""

    def update_task(self, task_id: str, payload: ReminderTaskUpdate) -> ReminderTask:
        """Update a task by id and return the normalized representation."""

    def complete_task(self, task_id: str) -> ReminderTask:
        """Mark the given task as completed and return the updated task."""


class ICloudCalDAVRemindersService:
    """iCloud CalDAV (VTODO) implementation for server/cross-platform use.

    Expected adapters can call `_wrap_provider_error` to normalize provider
    exceptions into app-level errors.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def list_tasks(self) -> list[ReminderTask]:
        try:
            raw_tasks = self._client.list_vtodo()
            return [self._to_task(raw_task) for raw_task in raw_tasks]
        except Exception as exc:  # provider-specific exceptions are normalized
            raise self._wrap_provider_error(exc) from exc

    def create_task(self, payload: ReminderTaskCreate) -> ReminderTask:
        try:
            raw_task = self._client.create_vtodo(
                title=payload.title,
                notes=payload.notes,
                due_at=payload.due_at,
            )
            return self._to_task(raw_task)
        except Exception as exc:
            raise self._wrap_provider_error(exc) from exc

    def update_task(self, task_id: str, payload: ReminderTaskUpdate) -> ReminderTask:
        try:
            raw_task = self._client.update_vtodo(
                task_id=task_id,
                title=payload.title,
                notes=payload.notes,
                due_at=payload.due_at,
            )
            return self._to_task(raw_task)
        except Exception as exc:
            raise self._wrap_provider_error(exc) from exc

    def complete_task(self, task_id: str) -> ReminderTask:
        try:
            raw_task = self._client.complete_vtodo(task_id)
            return self._to_task(raw_task)
        except Exception as exc:
            raise self._wrap_provider_error(exc) from exc

    @staticmethod
    def _to_task(raw_task: Any) -> ReminderTask:
        """Convert provider output into the app's shared task model."""

        return ReminderTask(
            task_id=str(raw_task["id"]),
            title=raw_task["title"],
            notes=raw_task.get("notes"),
            due_at=raw_task.get("due_at"),
            completed=bool(raw_task.get("completed", False)),
        )

    @staticmethod
    def _wrap_provider_error(exc: Exception) -> AppleRemindersError:
        """Map provider exceptions to shared application-level exception types."""

        name = exc.__class__.__name__.lower()
        message = str(exc)

        if "permission" in name or "unauthorized" in name or "forbidden" in name:
            return AppleRemindersPermissionError(message)

        if "timeout" in name or "connection" in name or "network" in name:
            return AppleRemindersNetworkError(message)

        return AppleRemindersOperationError(message)
