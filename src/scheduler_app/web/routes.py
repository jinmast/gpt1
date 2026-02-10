"""Web entry routes for calendar synchronization."""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from scheduler_app.jobs.sync_job import SyncJob

router = APIRouter(prefix="/sync", tags=["sync"])
job = SyncJob()

_CONNECTIONS: dict[str, bool] = {
    "google": True,
    "apple": False,
}

_CALENDARS: dict[str, list[dict[str, Any]]] = {
    "google": [
        {"id": "g-1", "name": "Work"},
        {"id": "g-2", "name": "Personal"},
    ],
    "apple": [
        {"id": "a-1", "name": "Family"},
    ],
}


@router.get("/status")
def get_connection_status() -> dict[str, dict[str, bool]]:
    """Return provider connection states."""
    return {"connections": _CONNECTIONS}


@router.get("/calendars")
def list_calendars(source: str = "google") -> dict[str, Any]:
    """List calendars from a connected source."""
    if source not in _CONNECTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source}'")
    if not _CONNECTIONS[source]:
        raise HTTPException(status_code=400, detail=f"Source '{source}' is not connected")

    return {
        "source": source,
        "count": len(_CALENDARS[source]),
        "items": _CALENDARS[source],
    }


@router.post("/manual")
def trigger_manual_sync(source: str = "google") -> dict[str, Any]:
    """Trigger manual synchronization."""
    if source not in _CONNECTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown source '{source}'")
    if not _CONNECTIONS[source]:
        raise HTTPException(status_code=400, detail=f"Source '{source}' is not connected")

    def fetch_events() -> list[dict[str, Any]]:
        return _CALENDARS[source]

    return job.run_once(source=source, fetch_events=fetch_events)


@router.get("", response_class=HTMLResponse)
def sync_dashboard() -> str:
    """Simple dashboard with connection status, list query and manual sync button."""
    rows = "".join(
        f"<li>{escape(source)}: {'connected' if connected else 'disconnected'}</li>"
        for source, connected in _CONNECTIONS.items()
    )

    return f"""
    <html>
      <body>
        <h1>Calendar Sync</h1>
        <h2>Connection status</h2>
        <ul>{rows}</ul>

        <h2>Actions</h2>
        <form method=\"get\" action=\"/sync/calendars\">
          <input type=\"text\" name=\"source\" value=\"google\" />
          <button type=\"submit\">목록 조회</button>
        </form>
        <form method=\"post\" action=\"/sync/manual\">
          <input type=\"text\" name=\"source\" value=\"google\" />
          <button type=\"submit\">수동 동기화</button>
        </form>
      </body>
    </html>
    """
