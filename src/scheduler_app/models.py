"""공통 데이터 모델 정의."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceStatus:
    """서비스 초기화 상태를 나타낸다."""

    name: str
    initialized: bool
    detail: str
