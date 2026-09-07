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
