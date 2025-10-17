import uuid
from typing import Protocol

from app.adapters.queue_inproc import InProcessQueue
from app.domain.models import EvaluateRequest, EvaluateResponse, JobStatus, ResultResponse


class EvalServiceProtocol(Protocol):
    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse:
        ...

    async def get_status(self, job_id: str) -> ResultResponse:
        ...


class EvalService(EvalServiceProtocol):
    def __init__(self, queue: InProcessQueue) -> None:
        self._queue = queue
        self._jobs: dict[str, ResultResponse] = {}

    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse:
        job_id = uuid.uuid4().hex
        self._jobs[job_id] = ResultResponse(id=job_id, status=JobStatus.queued)

        async def process() -> None:
            # TODO: wire actual evaluation graph via ADK.
            self._jobs[job_id] = ResultResponse(id=job_id, status=JobStatus.processing, stage="cv_ingest")
            # Placeholder for processing logic.
            self._jobs[job_id] = ResultResponse(id=job_id, status=JobStatus.completed)

        self._queue.submit(process)
        return EvaluateResponse(id=job_id, status=JobStatus.queued)

    async def get_status(self, job_id: str) -> ResultResponse:
        if job_id not in self._jobs:
            return ResultResponse(id=job_id, status=JobStatus.failed, error_message="Unknown job id")
        return self._jobs[job_id]
