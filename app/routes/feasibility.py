from fastapi import APIRouter, Cookie, HTTPException, status

from app.config import settings
from app.schemas import FeasibilityReport, PlotDetails
from app.services.auth import get_user
from app.services.feasibility import analyze_fcda_zoning, calculate_financials
from app.services.location import verify_location
from app.services.marketing import generate_global_marketing_copy

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
        verified_location = await verify_location(plot.district)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if settings.location_validation_enabled and not verified_location:
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
    )
