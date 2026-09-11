import io
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Cookie, File, HTTPException, Response, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from app.schemas import FeasibilityReport, PlotDetails
from app.config import settings
from app.services.auth import get_user, get_user_id
from app.services.projects import (
    create_document, create_project, create_review_request, delete_project, get_project,
    get_review_request, list_documents, list_projects,
)
from app.services.storage import (
    create_private_download_url, delete_private_documents, download_private_document,
    upload_private_document,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    plot: PlotDetails
    report: FeasibilityReport


class ReviewRequestCreate(BaseModel):
    note: str = Field(default="", max_length=2000)


ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _authenticated_user_id(session: str | None) -> int:
    user = get_user(session)
    user_id = get_user_id(user["email"]) if user else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required.")
    return user_id


def _project_summary(project) -> dict:
    plot = json.loads(project.plot_json)
    report = json.loads(project.report_json)
    documents = list_documents(project.id)
    review_request = get_review_request(project.id)
    stage = "Professional review requested" if review_request else (
        "Documents uploaded" if documents else "Analysis complete"
    )
    return {
        "id": project.id,
        "name": project.name,
        "district": plot["district"],
        "asset_type": plot["target_asset_type"],
        "updated_at": project.updated_at.isoformat(),
        "estimated_roi_percentage": report["estimated_roi_percentage"],
        "projected_gross_revenue_ngn": report["projected_gross_revenue_ngn"],
        "confidence_level": report.get("confidence_level", "Unknown"),
        "stage": stage,
        "document_count": len(documents),
        "review_status": review_request.status if review_request else None,
    }


@router.get("")
def projects(landwise_session: str | None = Cookie(default=None)) -> list[dict]:
    user_id = _authenticated_user_id(landwise_session)
    return [_project_summary(project) for project in list_projects(user_id)]


@router.post("", status_code=status.HTTP_201_CREATED)
def save_project(
    request: ProjectCreate,
    landwise_session: str | None = Cookie(default=None),
) -> dict:
    user_id = _authenticated_user_id(landwise_session)
    project = create_project(user_id, request.name.strip(), request.plot.model_dump(), request.report.model_dump())
    return _project_summary(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project(project_id: str, landwise_session: str | None = Cookie(default=None)) -> Response:
    user_id = _authenticated_user_id(landwise_session)
    project = get_project(user_id, project_id)
    if project:
        try:
            delete_private_documents([document.stored_name for document in list_documents(project_id)])
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    if not delete_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/documents")
def project_documents(project_id: str, landwise_session: str | None = Cookie(default=None)) -> list[dict[str, str]]:
    user_id = _authenticated_user_id(landwise_session)
    if not get_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return [
        {"id": document.id, "name": document.original_name, "content_type": document.content_type,
         "created_at": document.created_at.isoformat()}
        for document in list_documents(project_id)
    ]


@router.post("/{project_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_project_document(
    project_id: str,
    file: UploadFile = File(...),
    landwise_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    user_id = _authenticated_user_id(landwise_session)
    if not get_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail="Upload a PDF, JPEG, or PNG document.")
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if not content or len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=422, detail="Documents must be between 1 byte and 10 MB.")
    extension = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}[file.content_type]
    storage_key = f"{project_id}/{uuid.uuid4()}{extension}"
    try:
        upload_private_document(storage_key, content, file.content_type)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    document = create_document(project_id, file.filename or "document", storage_key, file.content_type)
    return {"id": document.id, "name": document.original_name, "content_type": document.content_type}


@router.get("/{project_id}/documents/{document_id}")
def download_project_document(
    project_id: str, document_id: str, landwise_session: str | None = Cookie(default=None),
) -> RedirectResponse:
    user_id = _authenticated_user_id(landwise_session)
    if not get_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    document = next((item for item in list_documents(project_id) if item.id == document_id), None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        return RedirectResponse(create_private_download_url(document.stored_name), status_code=307)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/{project_id}/documents/{document_id}/pdf")
def view_project_document_as_pdf(
    project_id: str, document_id: str, landwise_session: str | None = Cookie(default=None),
) -> Response:
    user_id = _authenticated_user_id(landwise_session)
    if not get_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    document = next((item for item in list_documents(project_id) if item.id == document_id), None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document.content_type == "application/pdf":
        try:
            return RedirectResponse(create_private_download_url(document.stored_name), status_code=307)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        source = download_private_document(document.stored_name)
        image = ImageReader(io.BytesIO(source))
        image_width, image_height = image.getSize()
    except (RuntimeError, OSError) as error:
        raise HTTPException(status_code=503, detail="The image could not be converted to PDF.") from error

    page_width, page_height = A4
    margin = 18 * mm
    scale = min((page_width - 2 * margin) / image_width, (page_height - 2 * margin) / image_height)
    render_width, render_height = image_width * scale, image_height * scale
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.drawImage(image, (page_width - render_width) / 2, (page_height - render_height) / 2, render_width, render_height)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    filename = f"{document.original_name.rsplit('.', 1)[0]}.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{project_id}/professional-review", status_code=status.HTTP_201_CREATED)
def request_professional_review(
    project_id: str, request: ReviewRequestCreate, landwise_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    user_id = _authenticated_user_id(landwise_session)
    if not get_project(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    review_request = create_review_request(project_id, request.note.strip())
    return {"id": review_request.id, "status": review_request.status, "message": "Professional review requested."}


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
    story.extend([Spacer(1, 8 * mm), Paragraph(f"Verification confidence: {report.get('confidence_level', 'Unknown')}", styles["Heading2"])])
    for check in report.get("verification_checks", []):
        story.append(Paragraph(f"{check['label']} ({check['status']}): {check['detail']}", styles["BodyText"]))
    story.extend([Spacer(1, 6 * mm), Paragraph("Assumptions and sources", styles["Heading2"])])
    story.extend(Paragraph(f"• {assumption}", styles["BodyText"]) for assumption in report.get("assumptions", []))
    story.extend([Spacer(1, 6 * mm), Paragraph("AI marketing draft", styles["Heading2"]), Paragraph(report["marketing_copy_global"], styles["BodyText"]), Spacer(1, 8 * mm), Paragraph("This report is an estimate for decision support and is not legal, planning, or financial advice.", styles["Italic"])])
    document.build(story)
    buffer.seek(0)
    filename = f"{project.name.lower().replace(' ', '-')}-landwise-report.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
