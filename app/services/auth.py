import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class UserSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

def _database_url() -> str:
    if settings.database_url:
        return settings.database_url.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"

engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_database() -> None:
    Base.metadata.create_all(engine)


def database_diagnostics() -> dict[str, str]:
    with engine.connect() as database:
        if settings.database_url:
            row = database.execute(text("SELECT current_database() AS name, current_user AS username")).one()
            return {"backend": "postgresql", "database": row.name, "user": row.username}
        return {"backend": "sqlite", "database": str(Path(settings.database_path))}

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"

def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", 1)
    candidate = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
    return secrets.compare_digest(candidate, digest_hex)

def create_user(email: str, password: str) -> bool:
    with SessionLocal() as database:
        database.add(User(email=email, password_hash=_hash_password(password), created_at=datetime.now(timezone.utc)))
        try:
            database.commit()
            return True
        except IntegrityError:
            database.rollback()

def create_session(email: str, password: str) -> str | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if not user or not _verify_password(password, user.password_hash):
            return None
        token = secrets.token_urlsafe(32)
    database.add(UserSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    database.commit()
    return token

def get_user(token: str | None) -> dict[str, str] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with SessionLocal() as database:
        session = database.get(UserSession, token_hash)
        if not session or session.expires_at <= datetime.now(timezone.utc):
            return None
        user = database.get(User, session.user_id)
    return {"email": user.email, "created_at": user.created_at.isoformat()} if user else None

def delete_session(token: str | None) -> None:
    if token:
        with SessionLocal() as database:
            database.execute(delete(UserSession).where(UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
            database.commit()

def create_password_reset_token(email: str) -> tuple[str, str] | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if not user:
            return None
    token = secrets.token_urlsafe(32)
    database.add(PasswordResetToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
    database.commit()
    return token, user.email

def reset_password(token: str, new_password: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with SessionLocal() as database:
        record = database.get(PasswordResetToken, token_hash)
        if not record or record.used_at or record.expires_at <= datetime.now(timezone.utc):
            return False
        user = database.get(User, record.user_id)
        if not user:
            return False
        user.password_hash = _hash_password(new_password)
        record.used_at = datetime.now(timezone.utc)
    database.execute(delete(UserSession).where(UserSession.user_id == record.user_id))
    database.commit()
    return True
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
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
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


def login_failure_reason(email: str, password: str) -> str | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if not user:
            return "user_missing"
        if not _verify_password(password, user.password_hash):
            return "password_mismatch"
        return None


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


def create_password_reset_token(email: str) -> tuple[str, str] | None:
    with _connection() as connection:
        user = connection.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        connection.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user["id"], expires_at.isoformat()),
        )
        return token, user["email"]


def reset_password(token: str, new_password: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with _connection() as connection:
        record = connection.execute(
            "SELECT user_id, expires_at, used_at FROM password_reset_tokens WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if (
            not record
            or record["used_at"]
            or datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc)
        ):
            return False
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), record["user_id"]),
        )
        connection.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?",
            (datetime.now(timezone.utc).isoformat(), token_hash),
        )
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (record["user_id"],))
        return True
