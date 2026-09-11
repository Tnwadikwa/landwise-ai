import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.services.auth import Base, SessionLocal


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    plot_json: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProfessionalReviewRequest(Base):
    __tablename__ = "professional_review_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def create_project(user_id: int, name: str, plot: dict, report: dict) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        plot_json=json.dumps(plot),
        report_json=json.dumps(report),
        created_at=now,
        updated_at=now,
    )
    with SessionLocal() as database:
        database.add(project)
        database.commit()
        database.refresh(project)
    return project


def list_projects(user_id: int) -> list[Project]:
    with SessionLocal() as database:
        return list(
            database.scalars(
                select(Project)
                .where(Project.user_id == user_id)
                .order_by(Project.updated_at.desc())
            )
        )


def get_project(user_id: int, project_id: str) -> Project | None:
    with SessionLocal() as database:
        return database.scalar(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )


def delete_project(user_id: int, project_id: str) -> bool:
    with SessionLocal() as database:
        project = database.scalar(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        if not project:
            return False
        database.execute(delete(ProjectDocument).where(ProjectDocument.project_id == project_id))
        database.execute(delete(ProfessionalReviewRequest).where(ProfessionalReviewRequest.project_id == project_id))
        database.delete(project)
        database.commit()
        return True


def create_document(project_id: str, original_name: str, stored_name: str, content_type: str) -> ProjectDocument:
    document = ProjectDocument(
        id=str(uuid.uuid4()), project_id=project_id, original_name=original_name,
        stored_name=stored_name, content_type=content_type, created_at=datetime.now(timezone.utc),
    )
    with SessionLocal() as database:
        database.add(document)
        database.commit()
        database.refresh(document)
    return document


def list_documents(project_id: str) -> list[ProjectDocument]:
    with SessionLocal() as database:
        return list(database.scalars(select(ProjectDocument).where(ProjectDocument.project_id == project_id)))


def create_review_request(project_id: str, note: str) -> ProfessionalReviewRequest:
    request = ProfessionalReviewRequest(
        id=str(uuid.uuid4()), project_id=project_id, note=note,
        status="requested", created_at=datetime.now(timezone.utc),
    )
    with SessionLocal() as database:
        database.add(request)
        database.commit()
        database.refresh(request)
    return request


def get_review_request(project_id: str) -> ProfessionalReviewRequest | None:
    with SessionLocal() as database:
        return database.scalar(
            select(ProfessionalReviewRequest)
            .where(ProfessionalReviewRequest.project_id == project_id)
            .order_by(ProfessionalReviewRequest.created_at.desc())
        )
