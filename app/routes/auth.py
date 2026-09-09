import logging

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.services.auth import (
    create_password_reset_token,
    create_session,
    create_user,
    change_password,
    delete_all_sessions,
    delete_user_account,
    delete_session,
    get_user_id,
    get_user,
    login_failure_reason,
    reset_password,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str = Field(..., min_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class AccountDelete(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, response: Response) -> dict[str, str]:
    email = str(credentials.email).strip().lower()
    if not create_user(email, credentials.password):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    token = create_session(email, credentials.password)
    response.set_cookie("landwise_session", token, httponly=True, samesite="lax", max_age=604800)
    return {"message": "Account created. You are now signed in."}


@router.post("/login")
def login(credentials: Credentials, response: Response) -> dict[str, str]:
    token = create_session(str(credentials.email).strip().lower(), credentials.password)
    if not token:
        logger.warning("Login rejected for %s: %s", str(credentials.email).lower(), login_failure_reason(str(credentials.email).strip().lower(), credentials.password))
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    response.set_cookie("landwise_session", token, httponly=True, samesite="lax", max_age=604800)
    return {"message": "Signed in successfully."}


@router.get("/me")
def me(landwise_session: str | None = Cookie(default=None)) -> dict[str, str]:
    user = get_user(landwise_session)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user


@router.post("/logout")
def logout(response: Response, landwise_session: str | None = Cookie(default=None)) -> dict[str, str]:
    delete_session(landwise_session)
    response.delete_cookie("landwise_session")
    return {"message": "Signed out."}


def _require_user_id(session: str | None) -> int:
    user = get_user(session)
    user_id = get_user_id(user["email"]) if user else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user_id


@router.post("/change-password")
def change_password_endpoint(
    request: PasswordChange,
    response: Response,
    landwise_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    user_id = _require_user_id(landwise_session)
    if not change_password(user_id, request.current_password, request.new_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    response.delete_cookie("landwise_session")
    return {"message": "Password changed. Please sign in again."}


@router.post("/logout-all")
def logout_all(response: Response, landwise_session: str | None = Cookie(default=None)) -> dict[str, str]:
    user_id = _require_user_id(landwise_session)
    delete_all_sessions(user_id)
    response.delete_cookie("landwise_session")
    return {"message": "All sessions have been signed out."}


@router.delete("/account")
def delete_account(
    request: AccountDelete,
    response: Response,
    landwise_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    user_id = _require_user_id(landwise_session)
    if not change_password(user_id, request.password, request.password):
        raise HTTPException(status_code=400, detail="Password is incorrect.")
    delete_user_account(user_id)
    response.delete_cookie("landwise_session")
    return {"message": "Your account and saved projects have been deleted."}


@router.post("/forgot-password")
def forgot_password(request: PasswordResetRequest) -> dict[str, str]:
    result = create_password_reset_token(str(request.email).lower())
    if result:
        token, email = result
        reset_url = f"{settings.site_url}/reset-password.html?token={token}"
        try:
            send_password_reset_email(email, reset_url)
        except Exception as error:
            logger.exception("Password recovery email delivery failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="We could not send the recovery email. Please try again later.",
            ) from error
    return {"message": "If an account exists for that email, a password reset link is on its way."}


@router.post("/reset-password")
def reset_password_endpoint(request: PasswordReset) -> dict[str, str]:
    if not reset_password(request.token, request.password):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    return {"message": "Password reset successfully. You can now sign in."}
