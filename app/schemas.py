from pydantic import BaseModel, Field


class PlotDetails(BaseModel):
    district: str = Field(..., min_length=2, json_schema_extra={"example": "Katampe Extension"})
    plot_size_sqm: float = Field(..., gt=0, json_schema_extra={"example": 1200.0})
    title_type: str = Field(..., min_length=2, json_schema_extra={"example": "Right of Occupancy (R of O)"})
    cadastral_zone: str = Field(..., min_length=2, json_schema_extra={"example": "Zone B07"})
    target_asset_type: str = Field(..., min_length=2, json_schema_extra={"example": "4-Bedroom Terrace Duplexes"})
    acquisition_cost_ngn: float = Field(..., ge=0, json_schema_extra={"example": 150000000.0})


class FeasibilityReport(BaseModel):
    district: str
    max_allowable_coverage_sqm: float
    estimated_units: int
    construction_cost_ngn: float
    projected_gross_revenue_ngn: float
    estimated_roi_percentage: float
    fcda_compliance_notes: list[str]
    marketing_copy_global: str
