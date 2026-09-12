import logging
import re
from datetime import date

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.services.auth import (
    create_pending_registration,
    resend_pending_registration,
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
    update_gender,
    verify_pending_registration,
)
from app.services.email import send_email_verification_email, send_password_reset_email

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class Registration(Credentials):
    first_name: str = Field(..., min_length=1, max_length=80)
    surname: str = Field(..., min_length=1, max_length=80)
    date_of_birth: date
    gender: str = Field(..., pattern="^(Woman|Man|Non-binary|Prefer not to say)$")
    confirm_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str = Field(..., min_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, min_length=8, max_length=128)


class EmailVerification(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class GenderUpdate(BaseModel):
    gender: str = Field(..., pattern="^(Woman|Man|Non-binary|Prefer not to say)$")


class AccountDelete(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)


def _validate_strong_password(password: str) -> None:
    if not (len(password) >= 8 and re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password)):
        raise HTTPException(
            status_code=422,
            detail="Password must contain at least 8 characters, one number, and one special character.",
        )


def _validate_profile(credentials: Registration) -> None:
    fields = {"First name": credentials.first_name, "Surname": credentials.surname}
    placeholders = {"na", "n/a", "none", "test", "testing", "unknown", "-"}
    for label, value in fields.items():
        normalized = value.strip().lower()
        if normalized in placeholders or not re.fullmatch(r"[A-Za-z][A-Za-z '-]*", value.strip()):
            raise HTTPException(status_code=422, detail=f"Enter a valid {label.lower()}.")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: Registration, response: Response) -> dict[str, str]:
    email = str(credentials.email).strip().lower()
    if credentials.date_of_birth >= date.today():
        raise HTTPException(status_code=422, detail="Enter a valid date of birth.")
    _validate_profile(credentials)
    _validate_strong_password(credentials.password)
    if credentials.password != credentials.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match.")
    if not settings.email_verification_required:
        if not create_user(
            email, credentials.password, credentials.first_name.strip(), credentials.surname.strip(),
            credentials.date_of_birth, credentials.gender,
        ):
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        token = create_session(email, credentials.password)
        response.set_cookie("landwise_session", token, httponly=True, samesite="lax", max_age=604800)
        return {"message": "Account created. You are now signed in.", "verification_required": "false"}
    code = create_pending_registration(email, credentials.password, credentials.first_name.strip(), credentials.surname.strip(), credentials.date_of_birth, credentials.gender)
    if code is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    verification_url = f"{settings.site_url}/verify-email.html?email={email}"
    try:
        send_email_verification_email(email, verification_url, code)
    except Exception as error:
        logger.exception("Verification email delivery failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="We could not send the verification email. Please try again later.") from error
    return {"message": "Check your email for a six-digit verification code.", "verification_required": "true"}


@router.post("/login")
def login(credentials: Credentials, response: Response) -> dict[str, str]:
    try:
        token = create_session(str(credentials.email).strip().lower(), credentials.password)
    except ValueError as error:
        if str(error) == "email_not_verified":
            raise HTTPException(status_code=403, detail="Please verify your email before signing in.") from error
        raise
    if not token:
        logger.warning("Login rejected for %s: %s", str(credentials.email).lower(), login_failure_reason(str(credentials.email).strip().lower(), credentials.password))
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    response.set_cookie("landwise_session", token, httponly=True, samesite="lax", max_age=604800)
    return {"message": "Signed in successfully."}


@router.get("/me")
def me(landwise_session: str | None = Cookie(default=None)) -> dict[str, object]:
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
    _validate_strong_password(request.new_password)
    if not change_password(user_id, request.current_password, request.new_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    response.delete_cookie("landwise_session")
    return {"message": "Password changed. Please sign in again."}


@router.patch("/profile/gender")
def update_profile_gender(
    request: GenderUpdate,
    landwise_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    user_id = _require_user_id(landwise_session)
    if not update_gender(user_id, request.gender):
        raise HTTPException(status_code=404, detail="Account not found.")
    return {"gender": request.gender, "message": "Gender updated."}


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


@router.post("/resend-verification")
def resend_verification(request: PasswordResetRequest) -> dict[str, str]:
    email = str(request.email).strip().lower()
    code = resend_pending_registration(email)
    if code:
        verification_url = f"{settings.site_url}/verify-email.html?email={email}"
        try:
            send_email_verification_email(email, verification_url, code)
        except Exception as error:
            logger.exception("Verification email delivery failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="We could not send the verification email. Please try again later.",
            ) from error
    return {"message": "If an unverified account exists for that email, a verification link is on its way."}


@router.post("/verify-email")
def verify_email(request: EmailVerification) -> dict[str, str]:
    if not verify_pending_registration(str(request.email).strip().lower(), request.code):
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired.")
    return {"message": "Email verified successfully. You can now sign in."}


@router.post("/reset-password")
def reset_password_endpoint(request: PasswordReset) -> dict[str, str]:
    _validate_strong_password(request.password)
    if request.confirm_password is not None and request.password != request.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match.")
    if not reset_password(request.token, request.password):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    return {"message": "Password reset successfully. You can now sign in."}
