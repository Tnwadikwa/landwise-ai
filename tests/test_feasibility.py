import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.routes import feasibility as feasibility_route
from app.schemas import PlotDetails
from app.services.feasibility import analyze_fcda_zoning
from app.services.location import VerifiedLocation
from app.services.marketing import fallback_marketing_copy
from app.services.verification import validate_supplied_land_details

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


def test_verified_location_model_preserves_geocoder_data() -> None:
    location = VerifiedLocation(
        display_name="East Legon, Accra, Ghana",
        latitude=5.6037,
        longitude=-0.1870,
    )

    assert location.display_name == "East Legon, Accra, Ghana"
    assert location.latitude == pytest.approx(5.6037)
    assert location.longitude == pytest.approx(-0.1870)


def test_land_details_reject_placeholders_and_unknown_title_types() -> None:
    with pytest.raises(ValueError, match="placeholder"):
        validate_supplied_land_details(PlotDetails(**{**VALID_PLOT, "cadastral_zone": "unknown"}))

    with pytest.raises(ValueError, match="title type could not be recognised"):
        validate_supplied_land_details(PlotDetails(**{**VALID_PLOT, "title_type": "Official document"}))


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
    assert body["confidence_level"] == "Low"
    assert body["verification_checks"][0]["status"] == "verified"
    assert body["assumptions"]


def test_unrecognised_location_does_not_generate_projections(monkeypatch: pytest.MonkeyPatch) -> None:
    client.cookies.clear()
    email = f"unverified-{uuid4()}@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123"},
    ).status_code == 201

    async def no_verified_location(_: str) -> None:
        return None

    monkeypatch.setattr(feasibility_route, "verify_location", no_verified_location)
    response = client.post("/api/v1/feasibility/generate", json=VALID_PLOT)

    assert response.status_code == 422
    assert "recognise" in response.json()["detail"]


def test_negative_plot_size_is_rejected() -> None:
    invalid_plot = {**VALID_PLOT, "plot_size_sqm": -1}
    response = client.post("/api/v1/feasibility/generate", json=invalid_plot)
    assert response.status_code == 422


def test_missing_required_field_is_rejected() -> None:
    invalid_plot = {key: value for key, value in VALID_PLOT.items() if key != "district"}
    response = client.post("/api/v1/feasibility/generate", json=invalid_plot)
    assert response.status_code == 422


def test_signed_in_user_can_save_list_download_and_delete_project(monkeypatch: pytest.MonkeyPatch) -> None:
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
    stored_keys: list[str] = []

    def upload_document(storage_key: str, content: bytes, content_type: str) -> None:
        assert content.startswith(b"%PDF")
        assert content_type == "application/pdf"
        stored_keys.append(storage_key)

    monkeypatch.setattr("app.routes.projects.upload_private_document", upload_document)
    monkeypatch.setattr(
        "app.routes.projects.create_private_download_url",
        lambda storage_key: f"https://storage.example.test/{storage_key}",
    )
    monkeypatch.setattr("app.routes.projects.delete_private_documents", lambda storage_keys: None)
    uploaded = client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("survey-plan.pdf", b"%PDF-1.4 land survey", "application/pdf")},
    )
    assert uploaded.status_code == 201
    assert stored_keys and stored_keys[0].startswith(f"{project_id}/")
    document_id = uploaded.json()["id"]
    assert client.get(f"/api/v1/projects/{project_id}/documents").json()[0]["name"] == "survey-plan.pdf"
    downloaded_document = client.get(
        f"/api/v1/projects/{project_id}/documents/{document_id}", follow_redirects=False,
    )
    assert downloaded_document.status_code == 307
    assert downloaded_document.headers["location"].startswith("https://storage.example.test/")
    pdf_document = client.get(
        f"/api/v1/projects/{project_id}/documents/{document_id}/pdf", follow_redirects=False,
    )
    assert pdf_document.status_code == 307
    assert pdf_document.headers["location"].startswith("https://storage.example.test/")
    review = client.post(
        f"/api/v1/projects/{project_id}/professional-review",
        json={"note": "Please review the title and survey plan."},
    )
    assert review.status_code == 201
    assert review.json()["status"] == "requested"
    pdf = client.get(f"/api/v1/projects/{project_id}/report.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 204
    assert client.get("/api/v1/projects").json() == []
