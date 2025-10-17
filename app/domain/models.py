from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UploadResponse(BaseModel):
    cv_id: str
    report_id: str


class EvaluateRequest(BaseModel):
    job_title: str = Field(..., min_length=1, max_length=128)
    cv_id: str
    report_id: str


class EvaluateResponse(BaseModel):
    id: str
    status: JobStatus


class ResultPayload(BaseModel):
    cv_match_rate: Optional[float] = None
    cv_feedback: Optional[str] = None
    project_score: Optional[float] = None
    project_feedback: Optional[str] = None
    overall_summary: Optional[str] = None


class ResultResponse(BaseModel):
    id: str
    status: JobStatus
    stage: Optional[str] = None
    result: Optional[ResultPayload] = None
    error_message: Optional[str] = None
