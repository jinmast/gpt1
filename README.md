# scheduler_app

Google/iCloud 캘린더 연동을 위한 스케줄러 애플리케이션의 최소 부팅 골격입니다.

## 로컬 실행 방법

1. 가상환경 생성 및 활성화

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. editable 설치

   ```bash
   pip install -e .
   ```

3. 환경 변수 파일 준비

   ```bash
   cp .env.example .env
   ```

   `.env` 값을 실제 계정/앱 키로 수정하세요.

4. 실행

   ```bash
   scheduler-app
   ```

   또는

   ```bash
   python -m scheduler_app.main
   ```

## 환경 변수

- `APP_ENV`: 실행 환경 (`development`, `staging`, `production` 등)
- `GOOGLE_CLIENT_ID`: Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth Client Secret
- `ICLOUD_USERNAME`: Apple ID (이메일)
- `ICLOUD_APP_PASSWORD`: iCloud 앱 전용 비밀번호

샘플 값은 `.env.example`에서 확인할 수 있습니다.

## 현재 지원 범위

현재 버전은 아래 기능만 제공합니다.

- 환경 변수 로드 (`scheduler_app.config`)
- 서비스 초기화 스텁 생성 (`scheduler_app.services`)
- 부팅 시 초기화 상태 출력 (`scheduler_app.main`)

아직 실제 API 호출/인증 토큰 저장/일정 동기화 로직은 구현되어 있지 않습니다.
