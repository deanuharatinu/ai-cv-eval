from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models import JobStatus
from app.infra.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    job_title: Mapped[str] = mapped_column(String(128))
    cv_file_id: Mapped[str] = mapped_column(String(64))
    report_file_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.queued
    )
    stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    result: Mapped[Optional["EvalResultModel"]] = relationship(
        "EvalResultModel",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EvalResultModel(Base):
    __tablename__ = "evaluation_results"

    job_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cv_match_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cv_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    project_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overall_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_cv_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_project_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_resume_score_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_project_score_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    job: Mapped[JobModel] = relationship("JobModel", back_populates="result")
