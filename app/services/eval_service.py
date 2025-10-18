import asyncio
import io
import json
from functools import partial
import uuid
from datetime import datetime, timezone
from typing import Mapping, Optional, Protocol, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.llm_provider import LLMProvider
from app.adapters.queue_inproc import InProcessQueue
from app.adapters.storage import LocalStorage, Storage
from app.domain.models import (
    EvaluateRequest,
    EvaluateResponse,
    JobStatus,
    ResultPayload,
    ResultResponse,
)
from pypdf import PdfReader

_UNSET = object()


class EvalServiceProtocol(Protocol):
    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse: ...

    async def get_status(self, job_id: str) -> ResultResponse: ...


class EvalService(EvalServiceProtocol):
    def __init__(
        self,
        queue: InProcessQueue,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        storage: Optional[Storage] = None,
        llm_provider: Optional[LLMProvider] = None,
    ) -> None:
        self._queue = queue
        self._session_factory = session_factory
        self._storage = storage or LocalStorage()
        self._llm_provider = llm_provider or LLMProvider()

    async def _process_job(self, job_id: str, payload: EvaluateRequest) -> None:
        try:
            await self._update_job(
                job_id,
                status=JobStatus.processing,
                stage="cv_ingest",
                error_message=None,
            )

            await self._process_cv(job_id, payload)
            await self._process_project_report(job_id, payload)

            await self._update_job(
                job_id,
                status=JobStatus.completed,
                stage=None,
                error_message=None,
            )
        except Exception as exc:
            await self._update_job(
                job_id,
                status=JobStatus.failed,
                stage=None,
                error_message=str(exc),
            )

    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse:
        job_id = uuid.uuid4().hex

        async with self._session_factory() as session:
            await self._create_job(session, job_id, payload)

        self._queue.submit(partial(self._process_job, job_id, payload))

        return EvaluateResponse(id=job_id, status=JobStatus.queued)

    async def get_status(self, job_id: str) -> ResultResponse:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT
                        j.id,
                        j.status,
                        j.stage,
                        j.error_message,
                        r.cv_match_rate,
                        r.cv_feedback,
                        r.project_score,
                        r.project_feedback,
                        r.overall_summary
                    FROM jobs AS j
                    LEFT JOIN evaluation_results AS r ON r.job_id = j.id
                    WHERE j.id = :job_id
                    """
                ),
                {"job_id": job_id},
            )
            row = result.mappings().one_or_none()

            if row is None:
                return ResultResponse(
                    id=job_id, status=JobStatus.failed, error_message="Unknown job id"
                )

            payload = self._row_to_payload(row)

            return ResultResponse(
                id=row["id"],
                status=JobStatus(row["status"]),
                stage=row["stage"],
                result=payload,
                error_message=row["error_message"],
            )

    async def _create_job(
        self, session: AsyncSession, job_id: str, payload: EvaluateRequest
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        await session.execute(
            text(
                """
                INSERT INTO jobs (
                    id,
                    job_title,
                    cv_file_id,
                    report_file_id,
                    status,
                    stage,
                    error_message,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :job_title,
                    :cv_file_id,
                    :report_file_id,
                    :status,
                    :stage,
                    :error_message,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "id": job_id,
                "job_title": payload.job_title,
                "cv_file_id": payload.cv_id,
                "report_file_id": payload.report_id,
                "status": JobStatus.queued.value,
                "stage": None,
                "error_message": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        await session.commit()

    async def _update_job(
        self,
        job_id: str,
        *,
        status: Optional[JobStatus] = None,
        stage: Union[Optional[str], object] = _UNSET,
        error_message: Union[Optional[str], object] = _UNSET,
    ) -> None:
        assignments = ["updated_at = :updated_at"]
        params: dict[str, object] = {
            "job_id": job_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if status is not None:
            assignments.append("status = :status")
            params["status"] = status.value

        if stage is not _UNSET:
            assignments.append("stage = :stage")
            params["stage"] = stage

        if error_message is not _UNSET:
            assignments.append("error_message = :error_message")
            params["error_message"] = error_message

        query = text(
            f"""
            UPDATE jobs
            SET {', '.join(assignments)}
            WHERE id = :job_id
            """
        )
        async with self._session_factory() as session:
            await session.execute(query, params)
            await session.commit()

    def _row_to_payload(self, row: Mapping[str, object]) -> Optional[ResultPayload]:
        fields = (
            "cv_match_rate",
            "cv_feedback",
            "project_score",
            "project_feedback",
            "overall_summary",
        )

        if all(row.get(field) is None for field in fields):
            return None

        return ResultPayload(
            cv_match_rate=row.get("cv_match_rate"),
            cv_feedback=row.get("cv_feedback"),
            project_score=row.get("project_score"),
            project_feedback=row.get("project_feedback"),
            overall_summary=row.get("overall_summary"),
        )

    async def _process_cv(self, job_id: str, payload: EvaluateRequest) -> None:
        cv_text = await self._extract_pdf_text(payload.cv_id)
        if not cv_text.strip():
            raise ValueError("Unable to extract text from CV PDF.")

        await self._update_job(job_id, stage="cv_extract")
        structured_cv = await self._llm_provider.parse_resume(resume_text=cv_text)
        await self._persist_cv_snapshot(job_id, structured_cv)

    async def _process_project_report(
        self, job_id: str, payload: EvaluateRequest
    ) -> None:
        report_text = await self._extract_pdf_text(payload.report_id)
        if not report_text.strip():
            raise ValueError("Unable to extract text from Report Project PDF.")

        await self._update_job(job_id, stage="report_extract")
        structured_report = await self._llm_provider.parse_project_report(
            project_report_text=report_text
        )
        await self._persist_project_report_snapshot(job_id, structured_report)

    async def _extract_pdf_text(self, file_id: str) -> str:
        pdf_bytes = await self._storage.open(file_id)
        return await asyncio.to_thread(self._pdf_bytes_to_text, pdf_bytes)

    @staticmethod
    def _pdf_bytes_to_text(data: bytes) -> str:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(
            filter(None, (page.extract_text() or "" for page in reader.pages))
        )

    async def _persist_cv_snapshot(
        self, job_id: str, cv_snapshot: dict[str, object]
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO evaluation_results (job_id, raw_cv_json)
                    VALUES (:job_id, :raw_cv_json)
                    ON CONFLICT(job_id) DO UPDATE SET raw_cv_json = :raw_cv_json
                    """
                ),
                {"job_id": job_id, "raw_cv_json": json.dumps(cv_snapshot)},
            )
            await session.commit()

    async def _persist_project_report_snapshot(
        self, job_id: str, project_report_snapshot: dict[str, object]
    ) -> None:
        assignments = ["raw_project_json = :raw_project_json"]
        params: dict[str, object] = {
            "job_id": job_id,
            "raw_project_json": json.dumps(project_report_snapshot),
        }

        query = text(
            f"""
                UPDATE evaluation_results
                SET {', '.join(assignments)}
                WHERE job_id = :job_id
            """
        )

        async with self._session_factory() as session:
            await session.execute(query, params)
            await session.commit()
