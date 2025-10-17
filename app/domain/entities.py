from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.domain.models import JobStatus


@dataclass
class FileRecord:
    id: str
    filename: str
    mime: str
    path: str
    sha256: str
    created_at: datetime


@dataclass
class JobRecord:
    id: str
    job_title: str
    cv_file_id: str
    report_file_id: str
    status: JobStatus
    stage: Optional[str]
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


@dataclass
class EvalResultRecord:
    job_id: str
    cv_match_rate: Optional[float]
    cv_feedback: Optional[str]
    project_score: Optional[float]
    project_feedback: Optional[str]
    overall_summary: Optional[str]
    raw_cv_json: Optional[dict]
    raw_project_json: Optional[dict]
