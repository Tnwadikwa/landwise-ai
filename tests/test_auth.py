from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_login_me_and_logout() -> None:
    email = "auth-test@example.com"
    password = "secure-password-123"

    register = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert register.status_code in (201, 409)

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    assert client.get("/api/v1/auth/me").json()["email"] == email

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
    email = "security-features@example.com"
    old_password = "old-secure-password"
    new_password = "new-secure-password"
    assert client.post("/api/v1/auth/register", json={"email": email, "password": old_password}).status_code == 201

    changed = client.post("/api/v1/auth/change-password", json={"current_password": old_password, "new_password": new_password})
    assert changed.status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": email, "password": new_password}).status_code == 200
    assert client.post("/api/v1/auth/logout-all").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_paid_feature_is_locked_for_free_accounts() -> None:
    client.cookies.clear()
    email = "free-plan@example.com"
    assert client.post("/api/v1/auth/register", json={"email": email, "password": "free-plan-password"}).status_code == 201
    response = client.get("/api/v1/premium/team-workspace")
    assert response.status_code == 403
