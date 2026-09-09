import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.services.feasibility import analyze_fcda_zoning
from app.services.marketing import fallback_marketing_copy

client = TestClient(app)


VALID_PLOT = {
    "district": "Katampe Extension",
    "plot_size_sqm": 1200,
    "title_type": "Right of Occupancy (R of O)",
    "cadastral_zone": "Zone B07",
    "target_asset_type": "4-Bedroom Terrace Duplexes",
    "acquisition_cost_ngn": 150000000,
}


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["backend"] in {"sqlite", "postgresql"}
    assert response.json()["smtp"] in {"configured", "incomplete"}


def test_zoning_calculation() -> None:
    result = analyze_fcda_zoning(1200, "Katampe Extension")
    assert result.max_allowable_coverage_sqm == 600
    assert result.estimated_units == 4
    assert result.compliance_notes


def test_marketing_fallback_uses_entered_location_and_title() -> None:
    copy = fallback_marketing_copy(
        district="East Legon",
        cadastral_zone="LG-04",
        title_type="Leasehold",
        asset_type="Townhouses",
        units=3,
    )

    assert "East Legon" in copy
    assert "LG-04" in copy
    assert "Leasehold" in copy
    assert "Townhouses" in copy
    assert "Abuja" not in copy


def test_feasibility_endpoint_requires_account() -> None:
    client.cookies.clear()
    response = client.post("/api/v1/feasibility/generate", json=VALID_PLOT)
    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to analyze your land."


def test_feasibility_endpoint_for_signed_in_user() -> None:
    client.cookies.clear()
    email = f"feasibility-{uuid4()}@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123"},
    )
    assert registered.status_code == 201

    response = client.post("/api/v1/feasibility/generate", json=VALID_PLOT)
    assert response.status_code == 200
    body = response.json()
    assert body["district"] == "Katampe Extension"
    assert body["estimated_units"] == 4
    assert body["estimated_roi_percentage"] == pytest.approx(44.00, abs=0.01)
    assert body["marketing_copy_global"]


def test_negative_plot_size_is_rejected() -> None:
    invalid_plot = {**VALID_PLOT, "plot_size_sqm": -1}
    response = client.post("/api/v1/feasibility/generate", json=invalid_plot)
    assert response.status_code == 422


def test_missing_required_field_is_rejected() -> None:
    invalid_plot = {key: value for key, value in VALID_PLOT.items() if key != "district"}
    response = client.post("/api/v1/feasibility/generate", json=invalid_plot)
    assert response.status_code == 422


def test_signed_in_user_can_save_list_download_and_delete_project() -> None:
    client.cookies.clear()
    email = f"project-{uuid4()}@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123"},
    ).status_code == 201
    report = client.post("/api/v1/feasibility/generate", json=VALID_PLOT).json()

    saved = client.post(
        "/api/v1/projects",
        json={"name": "Katampe Opportunity", "plot": VALID_PLOT, "report": report},
    )
    assert saved.status_code == 201
    project_id = saved.json()["id"]
    assert client.get("/api/v1/projects").json()[0]["name"] == "Katampe Opportunity"
    pdf = client.get(f"/api/v1/projects/{project_id}/report.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 204
    assert client.get("/api/v1/projects").json() == []
