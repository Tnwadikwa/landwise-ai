import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, select
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
        database.delete(project)
        database.commit()
        return True
