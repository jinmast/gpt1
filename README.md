# Scheduler App

## Apple Reminders integration decision

지원 플랫폼은 **서버/크로스플랫폼**으로 결정했고, 이에 따라 Apple Reminders 연동 방식은 **iCloud CalDAV(VTODO)** 를 사용합니다.

- EventKit은 macOS/iOS 네이티브 앱 권한 모델에 최적화되어 있어 서버 환경에는 부적합합니다.
- CalDAV는 서버에서 동작 가능한 표준 프로토콜이므로 백엔드/멀티플랫폼 구조에 맞습니다.

구현은 `src/scheduler_app/services/apple_reminders_service.py`의 `ICloudCalDAVRemindersService`를 기준으로 구성했습니다.

## 인증/권한 흐름 (iCloud CalDAV)

1. **앱 전용 비밀번호 생성**
   - Apple ID 계정에서 App-Specific Password를 생성합니다.
2. **서버 비밀값 설정**
   - Apple ID, App-Specific Password를 시크릿 저장소(예: Vault, 환경변수)에 저장합니다.
3. **CalDAV 클라이언트 인증**
   - 서버 부팅 시 CalDAV 클라이언트를 Apple iCloud CalDAV endpoint에 Basic/Auth 기반으로 인증합니다.
4. **권한 실패 처리**
   - 인증 실패/권한 거부(401/403 등)는 `AppleRemindersPermissionError`로 래핑합니다.
5. **네트워크 실패 처리**
   - 타임아웃/연결 문제는 `AppleRemindersNetworkError`로 래핑합니다.
6. **기타 연산 실패 처리**
   - 스키마 오류/미지원 응답 등은 `AppleRemindersOperationError`로 래핑합니다.

## 공통 인터페이스

`AppleRemindersService` 프로토콜은 아래 메서드를 공통 계약으로 제공합니다.

- `list_tasks`
- `create_task`
- `update_task`
- `complete_task`

상위 계층은 구현체에 관계없이 동일한 메서드/예외 계층을 사용하여 일관 처리할 수 있습니다.
