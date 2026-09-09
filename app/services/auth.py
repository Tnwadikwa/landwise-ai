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
        return settings.database_url.replace("postgres://", "postgresql+psycopg://", 1).replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
        database.add(
            User(
                email=email,
                password_hash=_hash_password(password),
                created_at=datetime.now(timezone.utc),
            )
        )
        try:
            database.commit()
            return True
        except IntegrityError:
            database.rollback()
            return False


def create_session(email: str, password: str) -> str | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if not user or not _verify_password(password, user.password_hash):
            return None
        token = secrets.token_urlsafe(32)
        database.add(
            UserSession(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        database.commit()
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
    with SessionLocal() as database:
        session = database.get(UserSession, token_hash)
        if not session or _as_utc(session.expires_at) <= datetime.now(timezone.utc):
            return None
        user = database.get(User, session.user_id)
        if not user:
            return None
        return {"email": user.email, "created_at": user.created_at.isoformat()}


def get_user_id(email: str) -> int | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        return user.id if user else None


def delete_session(token: str | None) -> None:
    if token:
        with SessionLocal() as database:
            database.execute(
                delete(UserSession).where(
                    UserSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            )
            database.commit()


def create_password_reset_token(email: str) -> tuple[str, str] | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        database.add(
            PasswordResetToken(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        database.commit()
        return token, user.email


def reset_password(token: str, new_password: str) -> bool:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with SessionLocal() as database:
        record = database.get(PasswordResetToken, token_hash)
        if not record or record.used_at or _as_utc(record.expires_at) <= datetime.now(timezone.utc):
            return False
        user = database.get(User, record.user_id)
        if not user:
            return False
        user.password_hash = _hash_password(new_password)
        record.used_at = datetime.now(timezone.utc)
        database.execute(delete(UserSession).where(UserSession.user_id == record.user_id))
        database.commit()
        return True
