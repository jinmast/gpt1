"""Router for Google Calendar OAuth + sync flows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from threading import Lock

from fastapi import APIRouter, HTTPException, Query

from scheduler_app.services.google_calendar_service import GoogleCalendarService
from scheduler_app.services.token_store import FileTokenStore

router = APIRouter(prefix="/google", tags=["google-calendar"])
service = GoogleCalendarService(token_store=FileTokenStore())

_STATE_TTL = timedelta(minutes=10)
_oauth_state_lock = Lock()
_oauth_state_by_nonce: dict[str, tuple[str, datetime]] = {}


def _issue_oauth_state(user_id: str) -> str:
    """Generate and remember short-lived OAuth state nonce for a user."""
    now = datetime.now(timezone.utc)
    nonce = token_urlsafe(32)
    with _oauth_state_lock:
        expired = [
            state_nonce
            for state_nonce, (_, expires_at) in _oauth_state_by_nonce.items()
            if expires_at <= now
        ]
        for state_nonce in expired:
            _oauth_state_by_nonce.pop(state_nonce, None)

        _oauth_state_by_nonce[nonce] = (user_id, now + _STATE_TTL)

    return nonce


def _consume_oauth_state(state: str) -> str:
    """Consume and validate OAuth state nonce, returning the mapped user id."""
    now = datetime.now(timezone.utc)
    with _oauth_state_lock:
        state_record = _oauth_state_by_nonce.pop(state, None)

    if not state_record:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    user_id, expires_at = state_record
    if expires_at <= now:
        raise HTTPException(status_code=400, detail="Expired OAuth state.")

    return user_id


@router.get("/connect")
def connect_google(user_id: str = Query(..., description="Internal user id")) -> dict[str, str]:
    """Return OAuth consent URL for the given user."""
    state = _issue_oauth_state(user_id)
    return {"auth_url": service.generate_auth_url(user_id=user_id, state=state)}


@router.get("/callback")
def oauth_callback(code: str, state: str) -> dict[str, str]:
    """Exchange authorization code and persist tokens."""
    user_id = _consume_oauth_state(state)
    try:
        service.exchange_code_for_token(user_id=user_id, code=code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}") from exc
    return {"status": "connected", "user_id": user_id}


@router.get("/sync/events")
def sync_events(user_id: str = Query(...), max_results: int = 20) -> dict:
    """Pull latest events from Google calendar."""
    try:
        events = service.list_events(user_id=user_id, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Sync failed: {exc}") from exc
    return {"count": len(events), "events": events}
