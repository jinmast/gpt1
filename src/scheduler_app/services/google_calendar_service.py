"""Google Calendar integration service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from scheduler_app.config import settings
from scheduler_app.services.token_store import OAuthToken, TokenStore


class GoogleCalendarService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

    def __init__(
        self,
        token_store: TokenStore,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        self.token_store = token_store
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    def generate_auth_url(self, user_id: str, state: Optional[str] = None) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state or user_id,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, user_id: str, code: str) -> OAuthToken:
        response = requests.post(
            self.TOKEN_URL,
            data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        token = OAuthToken(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token", ""),
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=int(payload.get("expires_in", 3600))),
            token_type=payload.get("token_type", "Bearer"),
            scope=payload.get("scope", ""),
        )
        self.token_store.save_token(user_id, token)
        return token

    def refresh_access_token(self, user_id: str) -> OAuthToken:
        token = self.token_store.load_token(user_id)
        if not token or not token.refresh_token:
            raise ValueError(f"No refresh token found for user '{user_id}'.")

        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": token.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()

        refreshed = OAuthToken(
            access_token=payload["access_token"],
            refresh_token=token.refresh_token,
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=int(payload.get("expires_in", 3600))),
            token_type=payload.get("token_type", token.token_type),
            scope=payload.get("scope", token.scope),
        )
        self.token_store.save_token(user_id, refreshed)
        return refreshed

    def _authorized_headers(self, user_id: str) -> dict[str, str]:
        token = self.token_store.load_token(user_id)
        if not token:
            raise ValueError(f"No token available for user '{user_id}'.")

        if token.is_expired:
            token = self.refresh_access_token(user_id)

        return {"Authorization": f"{token.token_type} {token.access_token}"}

    def list_events(
        self,
        user_id: str,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        params = {
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": max_results,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        response = requests.get(
            f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            headers=self._authorized_headers(user_id),
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("items", [])

    def create_event(self, user_id: str, event: dict[str, Any], calendar_id: str = "primary") -> dict[str, Any]:
        response = requests.post(
            f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            headers={**self._authorized_headers(user_id), "Content-Type": "application/json"},
            json=event,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def update_event(
        self,
        user_id: str,
        event_id: str,
        event: dict[str, Any],
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        response = requests.put(
            f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers={**self._authorized_headers(user_id), "Content-Type": "application/json"},
            json=event,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def delete_event(self, user_id: str, event_id: str, calendar_id: str = "primary") -> None:
        response = requests.delete(
            f"{self.CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers=self._authorized_headers(user_id),
            timeout=15,
        )
        response.raise_for_status()
