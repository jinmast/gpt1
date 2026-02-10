"""scheduler_app 실행 진입점."""

from __future__ import annotations

from scheduler_app.config import load_config
from scheduler_app.services import GoogleCalendarService, ICloudCalendarService



def main() -> None:
    """설정 로드, 서비스 초기화, 상태 출력."""

    config = load_config()

    google_service = GoogleCalendarService(config)
    icloud_service = ICloudCalendarService(config)

    statuses = [google_service.initialize(), icloud_service.initialize()]

    print(f"[scheduler_app] environment={config.app_env}")
    for status in statuses:
        mark = "OK" if status.initialized else "WARN"
        print(f"[{mark}] {status.name}: {status.detail}")


if __name__ == "__main__":
    main()
