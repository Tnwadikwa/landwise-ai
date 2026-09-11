from fastapi import APIRouter, Cookie, HTTPException, status

from app.config import settings
from datetime import datetime, timezone

from app.schemas import FeasibilityReport, PlotDetails, VerificationCheck
from app.services.auth import get_user
from app.services.feasibility import analyze_fcda_zoning, calculate_financials
from app.services.location import verify_location
from app.services.marketing import generate_global_marketing_copy
from app.services.verification import validate_supplied_land_details

router = APIRouter(prefix="/api/v1/feasibility", tags=["feasibility"])


@router.post("/generate", response_model=FeasibilityReport)
async def generate_development_feasibility(
    plot: PlotDetails,
    landwise_session: str | None = Cookie(default=None),
) -> FeasibilityReport:
    if not get_user(landwise_session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to analyze your land.",
        )
    try:
        validate_supplied_land_details(plot)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not settings.location_validation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Real-location verification is required before Landwise AI can calculate projections.",
        )
    try:
        verified_location = await verify_location(plot.district)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not verified_location:
        raise HTTPException(
            status_code=422,
            detail="We could not recognise that district or locality. Check the spelling and try again.",
        )
    zoning = analyze_fcda_zoning(plot.plot_size_sqm, plot.district)
    construction_cost, revenue, roi = calculate_financials(plot, zoning.estimated_units)
    marketing_copy = await generate_global_marketing_copy(
        district=verified_location.display_name if verified_location else plot.district,
        cadastral_zone=plot.cadastral_zone,
        title_type=plot.title_type,
        asset_type=plot.target_asset_type,
        units=zoning.estimated_units,
    )
    checked_at = datetime.now(timezone.utc).isoformat()
    verification_checks = [
        VerificationCheck(
            label="Location",
            status="verified",
            detail=f"Matched {verified_location.display_name}.",
            source="OpenStreetMap Nominatim",
            checked_at=checked_at,
        ),
        VerificationCheck(
            label="Title and ownership",
            status="pending",
            detail="Requires an authorised land-registry check or professional review.",
            checked_at=checked_at,
        ),
        VerificationCheck(
            label="Cadastral and planning data",
            status="pending",
            detail="Requires an authoritative planning or cadastral data source.",
            checked_at=checked_at,
        ),
        VerificationCheck(
            label="Market comparables",
            status="assumption",
            detail="Using current Landwise AI model assumptions until verified comparable data is connected.",
            checked_at=checked_at,
        ),
    ]
    assumptions = [
        f"Maximum ground coverage uses a {settings.max_coverage_ratio:.0%} planning-model assumption.",
        f"Construction cost uses NGN {settings.cost_per_sqm_ngn:,.0f} per sqm.",
        f"Projected sale revenue uses NGN {settings.unit_sale_price_ngn:,.0f} per estimated unit.",
        "Revenue and ROI are indicative until title, planning, and market comparables are verified.",
    ]

    return FeasibilityReport(
        district=plot.district,
        verified_location=verified_location.display_name if verified_location else None,
        max_allowable_coverage_sqm=zoning.max_allowable_coverage_sqm,
        estimated_units=zoning.estimated_units,
        construction_cost_ngn=construction_cost,
        projected_gross_revenue_ngn=revenue,
        estimated_roi_percentage=round(roi, 2),
        fcda_compliance_notes=zoning.compliance_notes,
        marketing_copy_global=marketing_copy,
        verification_checks=verification_checks,
        confidence_level="Low",
        assumptions=assumptions,
    )
