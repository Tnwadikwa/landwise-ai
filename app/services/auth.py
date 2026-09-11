import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, create_engine, delete, inspect, select, text
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
    first_name: Mapped[str | None] = mapped_column(String(80))
    surname: Mapped[str | None] = mapped_column(String(80))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(30))
    email_verified: Mapped[bool] = mapped_column(default=False)
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


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    surname: Mapped[str] = mapped_column(String(80), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(30), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    for name, definition in {
        "first_name": "VARCHAR(80)", "surname": "VARCHAR(80)", "date_of_birth": "DATE", "gender": "VARCHAR(30)",
        "email_verified": "BOOLEAN NOT NULL DEFAULT TRUE",
    }.items():
        if name not in columns:
            with engine.begin() as database:
                database.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))


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


def create_user(email: str, password: str, first_name: str, surname: str, date_of_birth: date, gender: str) -> bool:
    with SessionLocal() as database:
        database.add(
            User(
                email=email,
                password_hash=_hash_password(password),
                first_name=first_name,
                surname=surname,
                date_of_birth=date_of_birth,
                gender=gender,
                email_verified=True,
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
        if settings.email_verification_required and not user.email_verified:
            raise ValueError("email_not_verified")
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
        plan = "paid" if user.email in settings.paid_account_emails else "free"
        return {
            "id": str(user.id), "email": user.email, "first_name": user.first_name or "",
            "surname": user.surname or "", "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else "",
            "gender": user.gender or "", "created_at": user.created_at.isoformat(), "plan": plan,
            "email_verified": user.email_verified,
        }


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


def delete_all_sessions(user_id: int) -> None:
    with SessionLocal() as database:
        database.execute(delete(UserSession).where(UserSession.user_id == user_id))
        database.commit()


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    with SessionLocal() as database:
        user = database.get(User, user_id)
        if not user or not _verify_password(current_password, user.password_hash):
            return False
        user.password_hash = _hash_password(new_password)
        database.execute(delete(UserSession).where(UserSession.user_id == user_id))
        database.commit()
        return True


def update_gender(user_id: int, gender: str) -> bool:
    with SessionLocal() as database:
        user = database.get(User, user_id)
        if not user:
            return False
        user.gender = gender
        database.commit()
        return True


def delete_user_account(user_id: int) -> bool:
    with SessionLocal() as database:
        user = database.get(User, user_id)
        if not user:
            return False
        database.execute(text("DELETE FROM projects WHERE user_id = :user_id"), {"user_id": user_id})
        database.execute(delete(UserSession).where(UserSession.user_id == user_id))
        database.delete(user)
        database.commit()
        return True


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


def create_pending_registration(email: str, password: str, first_name: str, surname: str, date_of_birth: date, gender: str) -> str | None:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.email == email))
        if user:
            return None
        code = f"{secrets.randbelow(1_000_000):06d}"
        database.merge(
            PendingRegistration(
                email=email,
                code_hash=hashlib.sha256(code.encode()).hexdigest(),
                password_hash=_hash_password(password),
                first_name=first_name,
                surname=surname,
                date_of_birth=date_of_birth,
                gender=gender,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            )
        )
        database.commit()
        return code


def verify_pending_registration(email: str, code: str) -> bool:
    with SessionLocal() as database:
        record = database.get(PendingRegistration, email)
        if not record or not secrets.compare_digest(record.code_hash, hashlib.sha256(code.encode()).hexdigest()):
            return False
        if _as_utc(record.expires_at) <= datetime.now(timezone.utc):
            return False
        if database.scalar(select(User).where(User.email == record.email)):
            database.delete(record)
            database.commit()
            return False
        database.add(User(email=record.email, password_hash=record.password_hash, first_name=record.first_name, surname=record.surname, date_of_birth=record.date_of_birth, gender=record.gender, email_verified=True, created_at=datetime.now(timezone.utc)))
        database.delete(record)
        database.commit()
        return True


def resend_pending_registration(email: str) -> str | None:
    with SessionLocal() as database:
        record = database.get(PendingRegistration, email)
        if not record:
            return None
        code = f"{secrets.randbelow(1_000_000):06d}"
        record.code_hash = hashlib.sha256(code.encode()).hexdigest()
        record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        database.commit()
        return code


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
