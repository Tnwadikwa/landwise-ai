from app.main import app
from app.services.auth import create_password_reset_token
from fastapi.testclient import TestClient

client = TestClient(app)


def test_password_reset_token_is_one_time() -> None:
    email = "reset-test@example.com"
    old_password = "old-password-123"
    new_password = "new-password-456"
    client.post("/api/v1/auth/register", json={"email": email, "password": old_password})

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
