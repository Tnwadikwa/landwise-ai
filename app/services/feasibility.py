from dataclasses import dataclass

from app.config import settings
from app.schemas import PlotDetails


@dataclass(frozen=True)
class ZoningResult:
    max_allowable_coverage_sqm: float
    estimated_units: int
    compliance_notes: list[str]


def analyze_fcda_zoning(plot_size_sqm: float, district: str) -> ZoningResult:
    coverage = plot_size_sqm * settings.max_coverage_ratio
    estimated_units = max(1, int(coverage // 150))

    return ZoningResult(
        max_allowable_coverage_sqm=coverage,
        estimated_units=estimated_units,
        compliance_notes=[
            f"Maximum ground coverage allowed ({settings.max_coverage_ratio:.0%}): {coverage:g} sqm.",
            "Minimum 6-meter setback required from front boundary.",
            "Minimum 3-meter setback required from side and rear boundaries.",
            "Soil test report mandatory for multi-storey development.",
            f"Confirm current FCDA requirements for {district} before construction.",
        ],
    )


def calculate_financials(plot: PlotDetails, estimated_units: int) -> tuple[float, float, float]:
    construction_cost = estimated_units * settings.unit_built_area_sqm * settings.cost_per_sqm_ngn
    revenue = estimated_units * settings.unit_sale_price_ngn
    total_investment = construction_cost + plot.acquisition_cost_ngn
    roi = ((revenue - total_investment) / total_investment) * 100 if total_investment else 0.0
    return construction_cost, revenue, roi
