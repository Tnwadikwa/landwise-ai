from fastapi import APIRouter, Cookie, HTTPException

from app.services.auth import get_user

router = APIRouter(prefix="/api/v1/premium", tags=["premium"])


def require_paid_user(session: str | None) -> dict[str, str]:
    user = get_user(session)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required.")
    if user["plan"] != "paid":
        raise HTTPException(status_code=403, detail="This feature is available on a paid plan.")
    return user


@router.get("/team-workspace")
def team_workspace(landwise_session: str | None = Cookie(default=None)) -> dict[str, str]:
    require_paid_user(landwise_session)
    return {"status": "ready", "feature": "team_workspace"}