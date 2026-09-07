import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings

DATABASE_PATH = Path(settings.database_path)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", 1)
    candidate = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
    return secrets.compare_digest(candidate, digest_hex)


def create_user(email: str, password: str) -> bool:
    try:
        with _connection() as connection:
            connection.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, _hash_password(password), datetime.now(timezone.utc).isoformat()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def create_session(email: str, password: str) -> str | None:
    with _connection() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not _verify_password(password, user["password_hash"]):
            return None
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user["id"], expires_at.isoformat()),
        )
        return token


def get_user(token: str | None) -> dict[str, str] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _connection() as connection:
        user = connection.execute(
            """SELECT users.email, users.created_at, sessions.expires_at
               FROM sessions JOIN users ON users.id = sessions.user_id
               WHERE sessions.token_hash = ?""",
            (token_hash,),
        ).fetchone()
    if not user or datetime.fromisoformat(user["expires_at"]) <= datetime.now(timezone.utc):
        return None
    return {"email": user["email"], "created_at": user["created_at"]}


def delete_session(token: str | None) -> None:
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with _connection() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
