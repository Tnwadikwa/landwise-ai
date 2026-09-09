from app.main import app
from app.routes import auth
from app.services.auth import create_password_reset_token
from fastapi.testclient import TestClient

client = TestClient(app)


def test_password_reset_reports_email_delivery_failure(monkeypatch) -> None:
    email = "delivery-failure@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "old-password-123"})

    def fail_to_send(recipient: str, reset_url: str) -> None:
        raise RuntimeError("SMTP authentication failed")

    monkeypatch.setattr(auth, "send_password_reset_email", fail_to_send)
    response = client.post("/api/v1/auth/forgot-password", json={"email": email})

    assert response.status_code == 503
    assert response.json()["detail"] == "We could not send the recovery email. Please try again later."


def test_password_reset_token_is_one_time(monkeypatch) -> None:
    email = "reset-test@example.com"
    old_password = "old-password-123"
    new_password = "new-password-456"
    client.post("/api/v1/auth/register", json={"email": email, "password": old_password})

    monkeypatch.setattr(auth, "send_password_reset_email", lambda recipient, reset_url: None)
    request = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert request.status_code == 200
    assert "If an account exists" in request.json()["message"]

    token_data = create_password_reset_token(email)
    assert token_data is not None
    token, _ = token_data
    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "password": new_password})
    assert reset.status_code == 200
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "password": old_password}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": email, "password": new_password}).status_code == 200
