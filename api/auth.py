"""
user register and login 具体功能代码
"""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from utils.config import sign_conf
from api.db import get_db_connection

bearer_scheme = HTTPBearer(auto_error=False)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        # 兼容历史无时区数据，按UTC解释
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${pwd_hash.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, saved_hash = password_hash.split("$", 1)
    except ValueError:
        return False
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return secrets.compare_digest(pwd_hash.hex(), saved_hash)

def create_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    created_at = _utc_now()
    expires_at = created_at + timedelta(hours=sign_conf["token_expire_hours"])
    with get_db_connection() as conn:
        # 清理过期令牌
        conn.execute("DELETE FROM tokens WHERE expires_at < ?", (_to_utc_iso(created_at),))
        conn.execute(
            "INSERT INTO tokens (user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, token, _to_utc_iso(created_at), _to_utc_iso(expires_at))
        )
        conn.commit()
    return token

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> sqlite3.Row:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")
    
    token = credentials.credentials
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.username, t.expires_at
            FROM tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token = ?
            """,
            (token,)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    expires_at = _parse_utc(row["expires_at"])
    if expires_at <= _utc_now():
        raise HTTPException(status_code=401, detail="Authentication token has expired")
    
    return row