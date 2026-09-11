from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PROFILE = {"first_name": "Ada", "surname": "Okafor", "date_of_birth": "1992-04-20", "gender": "Woman"}


def test_register_login_me_and_logout() -> None:
    email = f"auth-test-{uuid4()}@example.com"
    password = "secure-password-1234!"

    register = client.post("/api/v1/auth/register", json={**PROFILE, "email": email, "password": password, "confirm_password": password})
    assert register.status_code in (201, 409)

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    account = client.get("/api/v1/auth/me").json()
    assert account["email"] == email
    assert account["first_name"] == "Ada"
    assert account["surname"] == "Okafor"
    assert account["gender"] == "Woman"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_wrong_password_is_rejected() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_account_security_controls() -> None:
    client.cookies.clear()
    email = f"security-features-{uuid4()}@example.com"
    old_password = "old-secure-password1!"
    new_password = "new-secure-password2!"
    assert client.post("/api/v1/auth/register", json={**PROFILE, "email": email, "password": old_password, "confirm_password": old_password}).status_code == 201

    changed = client.post("/api/v1/auth/change-password", json={"current_password": old_password, "new_password": new_password})
    assert changed.status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": email, "password": new_password}).status_code == 200
    assert client.post("/api/v1/auth/logout-all").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_paid_feature_is_locked_for_free_accounts() -> None:
    client.cookies.clear()
    email = f"free-plan-{uuid4()}@example.com"
    password = "free-plan-password1!"
    assert client.post("/api/v1/auth/register", json={**PROFILE, "email": email, "password": password, "confirm_password": password}).status_code == 201
    response = client.get("/api/v1/premium/team-workspace")
    assert response.status_code == 403


def test_registration_requires_matching_strong_password_and_profile() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={**PROFILE, "email": "profile-test@example.com", "password": "password123!", "confirm_password": "different123!"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Passwords do not match."


def test_only_gender_can_be_updated_in_profile() -> None:
    client.cookies.clear()
    email = f"gender-update-{uuid4()}@example.com"
    password = "profile-password1!"
    assert client.post(
        "/api/v1/auth/register",
        json={**PROFILE, "email": email, "password": password, "confirm_password": password},
    ).status_code == 201

    updated = client.patch("/api/v1/auth/profile/gender", json={"gender": "Non-binary"})
    assert updated.status_code == 200
    account = client.get("/api/v1/auth/me").json()
    assert account["gender"] == "Non-binary"
    assert account["first_name"] == "Ada"
    assert account["surname"] == "Okafor"
