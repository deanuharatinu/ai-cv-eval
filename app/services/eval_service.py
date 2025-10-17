import uuid
from datetime import datetime, timezone
from typing import Mapping, Optional, Protocol, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.queue_inproc import InProcessQueue
from app.domain.models import EvaluateRequest, EvaluateResponse, JobStatus, ResultPayload, ResultResponse

_UNSET = object()


class EvalServiceProtocol(Protocol):
    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse:
        ...

    async def get_status(self, job_id: str) -> ResultResponse:
        ...


class EvalService(EvalServiceProtocol):
    def __init__(
        self,
        queue: InProcessQueue,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._queue = queue
        self._session_factory = session_factory

    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse:
        job_id = uuid.uuid4().hex

        async with self._session_factory() as session:
            await self._create_job(session, job_id, payload)

        async def process() -> None:
            try:
                # TODO: wire actual evaluation graph via ADK.
                await self._update_job(
                    job_id,
                    status=JobStatus.processing,
                    stage="cv_ingest",
                    error_message=None,
                )
                # Placeholder for processing logic.
                await self._update_job(
                    job_id,
                    status=JobStatus.completed,
                    stage=None,
                    error_message=None,
                )
            except Exception as exc:  # pragma: no cover - defensive
                await self._update_job(
                    job_id,
                    status=JobStatus.failed,
                    stage=None,
                    error_message=str(exc),
                )

        self._queue.submit(process)

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
                return ResultResponse(id=job_id, status=JobStatus.failed, error_message="Unknown job id")

            payload = self._row_to_payload(row)

            return ResultResponse(
                id=row["id"],
                status=JobStatus(row["status"]),
                stage=row["stage"],
                result=payload,
                error_message=row["error_message"],
            )

    async def _create_job(self, session: AsyncSession, job_id: str, payload: EvaluateRequest) -> None:
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
