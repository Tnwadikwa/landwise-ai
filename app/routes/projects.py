import io
import json
from datetime import datetime

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import FeasibilityReport, PlotDetails
from app.services.auth import get_user, get_user_id
from app.services.projects import create_project, delete_project, get_project, list_projects

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    plot: PlotDetails
    report: FeasibilityReport


def _authenticated_user_id(session: str | None) -> int:
    user = get_user(session)
    user_id = get_user_id(user["email"]) if user else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required.")
    return user_id


def _project_summary(project) -> dict[str, str]:
    plot = json.loads(project.plot_json)
    return {
        "id": project.id,
        "name": project.name,
        "district": plot["district"],
        "asset_type": plot["target_asset_type"],
        "updated_at": project.updated_at.isoformat(),
    }


@router.get("")
def projects(landwise_session: str | None = Cookie(default=None)) -> list[dict[str, str]]:
    user_id = _authenticated_user_id(landwise_session)
    return [_project_summary(project) for project in list_projects(user_id)]


@router.post("", status_code=status.HTTP_201_CREATED)
def save_project(
    request: ProjectCreate,
    landwise_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    user_id = _authenticated_user_id(landwise_session)
    project = create_project(user_id, request.name.strip(), request.plot.model_dump(), request.report.model_dump())
    return _project_summary(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(project_id: str, landwise_session: str | None = Cookie(default=None)) -> Response:
    user_id = _authenticated_user_id(landwise_session)
    if not delete_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/report.pdf")
def download_report(project_id: str, landwise_session: str | None = Cookie(default=None)) -> StreamingResponse:
    user_id = _authenticated_user_id(landwise_session)
    project = get_project(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    plot = json.loads(project.plot_json)
    report = json.loads(project.report_json)
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    story = [Paragraph("Landwise AI", styles["Title"]), Paragraph(project.name, styles["Heading1"]), Paragraph(f"Generated {datetime.now().strftime('%d %B %Y')}", styles["Normal"]), Spacer(1, 10 * mm)]
    details = [
        ["District", plot["district"]],
        ["Plot size", f'{plot["plot_size_sqm"]:,.0f} sqm'],
        ["Title type", plot["title_type"]],
        ["Cadastral zone", plot["cadastral_zone"]],
        ["Proposed development", plot["target_asset_type"]],
        ["Acquisition cost", f'NGN {plot["acquisition_cost_ngn"]:,.0f}'],
    ]
    table = Table(details, colWidths=[48 * mm, 120 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf3e8")), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dfd2")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 10 * mm), Paragraph("Decision brief", styles["Heading2"])])
    metrics = [["Estimated units", str(report["estimated_units"]), "Estimated ROI", f'{report["estimated_roi_percentage"]}%'], ["Projected revenue", f'NGN {report["projected_gross_revenue_ngn"]:,.0f}', "Buildable coverage", f'{report["max_allowable_coverage_sqm"]:,.0f} sqm']]
    metrics_table = Table(metrics, colWidths=[42 * mm, 45 * mm, 48 * mm, 33 * mm])
    metrics_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#173f35")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.white), ("PADDING", (0, 0), (-1, -1), 8)]))
    story.extend([metrics_table, Spacer(1, 8 * mm), Paragraph("Planning checklist", styles["Heading2"])])
    story.extend(Paragraph(f"• {note}", styles["BodyText"]) for note in report["fcda_compliance_notes"])
    story.extend([Spacer(1, 6 * mm), Paragraph("AI marketing draft", styles["Heading2"]), Paragraph(report["marketing_copy_global"], styles["BodyText"]), Spacer(1, 8 * mm), Paragraph("This report is an estimate for decision support and is not legal, planning, or financial advice.", styles["Italic"])])
    document.build(story)
    buffer.seek(0)
    filename = f"{project.name.lower().replace(' ', '-')}-landwise-report.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
