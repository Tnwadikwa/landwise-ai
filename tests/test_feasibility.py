import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.feasibility import analyze_fcda_zoning

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


def test_zoning_calculation() -> None:
    result = analyze_fcda_zoning(1200, "Katampe Extension")
    assert result.max_allowable_coverage_sqm == 600
    assert result.estimated_units == 4
    assert result.compliance_notes


def test_feasibility_endpoint_without_api_key() -> None:
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
