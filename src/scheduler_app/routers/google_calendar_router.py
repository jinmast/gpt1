"""Router for Google Calendar OAuth + sync flows."""

from fastapi import APIRouter, HTTPException, Query

from scheduler_app.services.google_calendar_service import GoogleCalendarService
from scheduler_app.services.token_store import FileTokenStore

router = APIRouter(prefix="/google", tags=["google-calendar"])
service = GoogleCalendarService(token_store=FileTokenStore())


@router.get("/connect")
def connect_google(user_id: str = Query(..., description="Internal user id")) -> dict[str, str]:
    """Return OAuth consent URL for the given user."""
    return {"auth_url": service.generate_auth_url(user_id=user_id)}


@router.get("/callback")
def oauth_callback(code: str, state: str) -> dict[str, str]:
    """Exchange authorization code and persist tokens."""
    try:
        service.exchange_code_for_token(user_id=state, code=code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}") from exc
    return {"status": "connected", "user_id": state}


@router.get("/sync/events")
def sync_events(user_id: str = Query(...), max_results: int = 20) -> dict:
    """Pull latest events from Google calendar."""
    try:
        events = service.list_events(user_id=user_id, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Sync failed: {exc}") from exc
    return {"count": len(events), "events": events}
