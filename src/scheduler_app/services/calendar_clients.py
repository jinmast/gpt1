"""외부 캘린더 서비스 초기화 스텁."""

from __future__ import annotations

from scheduler_app.config import AppConfig
from scheduler_app.models import ServiceStatus


class GoogleCalendarService:
    """Google Calendar 연동 서비스(초기 스텁)."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def initialize(self) -> ServiceStatus:
        enabled = bool(self._config.google_client_id and self._config.google_client_secret)
        detail = "configured" if enabled else "missing GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET"
        return ServiceStatus(name="google_calendar", initialized=enabled, detail=detail)


class ICloudCalendarService:
    """iCloud Calendar 연동 서비스(초기 스텁)."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def initialize(self) -> ServiceStatus:
        enabled = bool(self._config.icloud_username and self._config.icloud_app_password)
        detail = "configured" if enabled else "missing ICLOUD_USERNAME/ICLOUD_APP_PASSWORD"
        return ServiceStatus(name="icloud_calendar", initialized=enabled, detail=detail)
