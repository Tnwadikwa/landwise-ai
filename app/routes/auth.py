from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from app.services.auth import create_session, create_user, delete_session, get_user

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials) -> dict[str, str]:
    if not create_user(str(credentials.email).lower(), credentials.password):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return {"message": "Account created. You can now sign in."}


@router.post("/login")
def login(credentials: Credentials, response: Response) -> dict[str, str]:
    token = create_session(str(credentials.email).lower(), credentials.password)
    if not token:
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
