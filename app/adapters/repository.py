from typing import List, Mapping, Optional, Protocol, Union
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import (
    EvaluateRequest,
    JobStatus,
    ResultPayload,
    ResultResponse,
)

_UNSET = object()


class Repository(Protocol):
    async def create_job(self, job_id: str, payload: EvaluateRequest) -> None: ...

    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        stage: Union[Optional[str], object] = _UNSET,
        error_message: Union[Optional[str], object] = _UNSET,
    ) -> None: ...

    async def create_eval_result(self, job_id: str) -> None: ...

    async def update_eval_result(
        self, job_id: str, assignments: List[str], params: dict[str, object]
    ) -> None: ...

    async def get_status(self, job_id: str) -> ResultResponse: ...


class SQLiteRepository(Repository):

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._session_factory = session_factory

    async def create_job(self, job_id: str, payload: EvaluateRequest) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()

        async with self._session_factory() as session:
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

    async def update_job(
        self,
        job_id: str,
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

    async def create_eval_result(self, job_id: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO evaluation_results (job_id)
                    VALUES (:job_id)
                    """
                ),
                {"job_id": job_id},
            )
            await session.commit()

    async def update_eval_result(
        self,
        job_id: str,
        assignments: List[str],
        params: dict[str, object],
    ) -> None:
        params["job_id"] = job_id

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

    async def get_status(self, job_id: str) -> ResultResponse:
        async with self._session_factory() as session:
            query = text(
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
            )
            result = await session.execute(query, {"job_id": job_id})
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
