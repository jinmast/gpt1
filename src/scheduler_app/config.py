"""애플리케이션 설정 로더."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """환경 변수 기반 설정."""

    app_env: str
    google_client_id: str
    google_client_secret: str
    icloud_username: str
    icloud_app_password: str



def load_config() -> AppConfig:
    """환경 변수를 읽어 설정 객체를 반환한다."""

    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        icloud_username=os.getenv("ICLOUD_USERNAME", ""),
        icloud_app_password=os.getenv("ICLOUD_APP_PASSWORD", ""),
    )
