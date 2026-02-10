"""Pluggable token storage backends for OAuth credentials."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Optional


@dataclass
class OAuthToken:
    """Google OAuth token payload."""

    access_token: str
    refresh_token: str
    expires_at: datetime
    token_type: str = "Bearer"
    scope: str = ""

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    def to_dict(self) -> dict:
        data = asdict(self)
        data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthToken":
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope", ""),
        )


class TokenStore(ABC):
    """Storage contract for OAuth tokens."""

    @abstractmethod
    def save_token(self, user_id: str, token: OAuthToken) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_token(self, user_id: str) -> Optional[OAuthToken]:
        raise NotImplementedError

    @abstractmethod
    def delete_token(self, user_id: str) -> None:
        raise NotImplementedError


class FileTokenStore(TokenStore):
    """Simple JSON file-backed token store."""

    def __init__(self, path: str = "tokens/google_tokens.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> dict:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _write_all(self, data: dict) -> None:
        with self.path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)

    def save_token(self, user_id: str, token: OAuthToken) -> None:
        data = self._read_all()
        data[user_id] = token.to_dict()
        self._write_all(data)

    def load_token(self, user_id: str) -> Optional[OAuthToken]:
        data = self._read_all()
        payload = data.get(user_id)
        return OAuthToken.from_dict(payload) if payload else None

    def delete_token(self, user_id: str) -> None:
        data = self._read_all()
        if user_id in data:
            del data[user_id]
            self._write_all(data)


class SQLiteTokenStore(TokenStore):
    """SQLite-backed token store."""

    def __init__(self, db_path: str = "tokens/google_tokens.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    user_id TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    token_type TEXT NOT NULL,
                    scope TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_token(self, user_id: str, token: OAuthToken) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO oauth_tokens (user_id, access_token, refresh_token, expires_at, token_type, scope)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_at = excluded.expires_at,
                    token_type = excluded.token_type,
                    scope = excluded.scope
                """,
                (
                    user_id,
                    token.access_token,
                    token.refresh_token,
                    token.expires_at.isoformat(),
                    token.token_type,
                    token.scope,
                ),
            )
            conn.commit()

    def load_token(self, user_id: str) -> Optional[OAuthToken]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT access_token, refresh_token, expires_at, token_type, scope
                FROM oauth_tokens
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return OAuthToken(
            access_token=row[0],
            refresh_token=row[1],
            expires_at=datetime.fromisoformat(row[2]),
            token_type=row[3],
            scope=row[4],
        )

    def delete_token(self, user_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM oauth_tokens WHERE user_id = ?", (user_id,))
            conn.commit()
