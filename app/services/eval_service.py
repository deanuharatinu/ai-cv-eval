import asyncio
import hashlib
import io
import json

from functools import partial
from typing import Any, Optional, Protocol

from app.adapters import repository
from app.adapters.llm_provider import GeminiLLMProvider, LLMProvider
from app.adapters.queue_inproc import InProcessQueue
from app.adapters.storage import LocalStorage, Storage
from app.adapters.vector_store import ChromaDBVectorStore, VectorStore
from app.domain.models import (
    EvaluateRequest,
    EvaluateResponse,
    JobStatus,
    ResultResponse,
)
from sqlalchemy.exc import IntegrityError
from pypdf import PdfReader


class EvalServiceProtocol(Protocol):
    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse: ...

    async def get_status(self, job_id: str) -> ResultResponse: ...


class EvalService(EvalServiceProtocol):
    def __init__(
        self,
        queue: InProcessQueue,
        *,
        repository: repository.Repository,
        storage: Optional[Storage] = None,
        llm_provider: Optional[LLMProvider] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        self._queue = queue
        self._repository = repository
        self._storage = storage or LocalStorage()
        self._llm_provider = llm_provider or GeminiLLMProvider()
        self._vector_store = vector_store or ChromaDBVectorStore()

    async def enqueue(self, payload: EvaluateRequest) -> EvaluateResponse:
        job_id = self._derive_job_id(payload)

        existing = await self._repository.get_status(job_id)
        if not self._is_unknown_job(existing):
            return EvaluateResponse(id=job_id, status=existing.status)

        is_cv_exist = await self._storage.exists(payload.cv_id)
        is_report_exist = await self._storage.exists(payload.report_id)
        if not is_cv_exist or not is_report_exist:
            return EvaluateResponse(id="CV ID org Report ID not valid", status=JobStatus.failed)

        try:
            await self._repository.create_job(job_id, payload)
        except IntegrityError:
            existing = await self._repository.get_status(job_id)
            if self._is_unknown_job(existing):
                raise
            return EvaluateResponse(id=job_id, status=existing.status)

        self._queue.submit(partial(self._process_job, job_id, payload))

        return EvaluateResponse(id=job_id, status=JobStatus.queued)

    async def get_status(self, job_id: str) -> ResultResponse:
        return await self._repository.get_status(job_id)

    async def _process_job(self, job_id: str, payload: EvaluateRequest) -> None:
        try:
            await self._repository.update_job(
                job_id,
                status=JobStatus.processing,
                stage="cv_ingest",
                error_message=None,
            )

            await self._repository.create_eval_result(job_id)
            scored_resume = await self._process_cv(job_id, payload)
            scored_project_report = await self._process_project_report(job_id, payload)

            overall_summary = await self._llm_provider.get_candidate_overall_summary(
                scored_resume, scored_project_report
            )

            candidate_score = {
                "cv_match_rate": scored_resume.get("cv_match_rate", 0.0),
                "cv_feedback": scored_resume.get("cv_feedback", ""),
                "project_score": scored_project_report.get("project_score", 0.0),
                "project_feedback": scored_project_report.get("project_feedback", ""),
                "overall_summary": overall_summary,
            }
            await self._persist_candidate_overall_summary(job_id, candidate_score)

            await self._repository.update_job(
                job_id,
                status=JobStatus.completed,
                stage=None,
                error_message=None,
            )
        except Exception as exc:
            await self._repository.update_job(
                job_id,
                status=JobStatus.failed,
                stage=None,
                error_message=str(exc),
            )

    async def _process_cv(
        self, job_id: str, payload: EvaluateRequest
    ) -> dict[str, Any]:
        cv_text = await self._extract_pdf_text(payload.cv_id)
        if not cv_text.strip():
            raise ValueError("Unable to extract text from CV PDF.")

        await self._repository.update_job(job_id, stage="cv_extract")
        structured_cv = await self._llm_provider.parse_resume(resume_text=cv_text)

        await self._persist_cv_snapshot(job_id, structured_cv)

        await self._repository.update_job(job_id, stage="cv_scoring")
        scoring_rule_results = await self._vector_store.query(
            query="Scoring rubric for CV Match Evaluation", top_k=2
        )
        scoring_rule = "\n".join(
            [result.get("text", "") for result in scoring_rule_results]
        )

        job_description_results = await self._vector_store.query(
            query=f"Job description for role: {payload.job_title}", top_k=2
        )
        job_description = "\n".join(
            [result.get("text", "") for result in job_description_results]
        )

        scored_resume = await self._llm_provider.score_resume(
            job_title=payload.job_title,
            scoring_rule=scoring_rule,
            job_description=job_description,
            resume=structured_cv,
        )

        scored_resume["cv_match_rate"] = self._calculate_cv_match_rate(scored_resume)

        await self._persist_resume_score_snapshot(job_id, scored_resume)

        return scored_resume

    async def _process_project_report(
        self, job_id: str, payload: EvaluateRequest
    ) -> dict[str, Any]:
        report_text = await self._extract_pdf_text(payload.report_id)
        if not report_text.strip():
            raise ValueError("Unable to extract text from Report Project PDF.")

        await self._repository.update_job(job_id, stage="report_extract")
        structured_report = await self._llm_provider.parse_project_report(
            project_report_text=report_text
        )

        await self._persist_project_report_snapshot(job_id, structured_report)

        await self._repository.update_job(job_id, stage="report_scoring")
        scoring_rule_results = await self._vector_store.query(
            query="Scoring rubric for Project Deliverable Evaluation", top_k=2
        )
        scoring_rule = "\n".join(
            [result.get("text", "") for result in scoring_rule_results]
        )

        case_study_results = await self._vector_store.query(
            query=f"Case study brief for role: {payload.job_title}", top_k=2
        )
        case_study = "\n".join(
            [result.get("text", "") for result in case_study_results]
        )

        scored_project_report = await self._llm_provider.score_project_report(
            job_title=payload.job_title,
            scoring_rule=scoring_rule,
            case_study_brief=case_study,
            project_report=structured_report,
        )

        scored_project_report["project_score"] = self._calculate_project_score(
            scored_project_report
        )

        await self._persist_report_score_snapshot(job_id, scored_project_report)

        return scored_project_report

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
        assignments = ["raw_cv_json = :raw_cv_json"]
        params: dict[str, object] = {"raw_cv_json": json.dumps(cv_snapshot)}
        await self._repository.update_eval_result(job_id, assignments, params)

    async def _persist_project_report_snapshot(
        self, job_id: str, project_report_snapshot: dict[str, object]
    ) -> None:
        assignments = ["raw_project_json = :raw_project_json"]
        params: dict[str, object] = {
            "raw_project_json": json.dumps(project_report_snapshot)
        }
        await self._repository.update_eval_result(job_id, assignments, params)

    async def _persist_resume_score_snapshot(
        self, job_id: str, resume_score_snapshot: dict[str, object]
    ) -> None:
        assignments = ["raw_resume_score_json = :raw_resume_score_json"]
        params: dict[str, object] = {
            "raw_resume_score_json": json.dumps(resume_score_snapshot),
        }
        await self._repository.update_eval_result(job_id, assignments, params)

    async def _persist_report_score_snapshot(
        self, job_id: str, report_score_snapshot: dict[str, object]
    ) -> None:
        assignments = ["raw_project_score_json = :raw_project_score_json"]
        params: dict[str, object] = {
            "raw_project_score_json": json.dumps(report_score_snapshot),
        }
        await self._repository.update_eval_result(job_id, assignments, params)

    async def _persist_candidate_overall_summary(
        self, job_id: str, candidate_score: dict[str, Any]
    ) -> None:
        assignments = [
            "cv_match_rate = :cv_match_rate",
            "cv_feedback = :cv_feedback",
            "project_score = :project_score",
            "project_feedback = :project_feedback",
            "overall_summary = :overall_summary",
        ]
        params: dict[str, object] = candidate_score
        await self._repository.update_eval_result(job_id, assignments, params)

    @staticmethod
    def _derive_job_id(payload: EvaluateRequest) -> str:
        canonical_payload = json.dumps(
            {
                "job_title": payload.job_title.strip(),
                "cv_id": payload.cv_id,
                "report_id": payload.report_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        return digest[:32]

    @staticmethod
    def _is_unknown_job(result: ResultResponse) -> bool:
        return (
            result.status == JobStatus.failed
            and result.error_message == "Unknown job id"
        )

    @staticmethod
    def _calculate_cv_match_rate(scored_resume: dict[str, Any]) -> float:
        components = [
            ("technical_skills_match", ("technical_skills_weight",)),
            ("experience_level", ("experience_level_weight",)),
            ("relevant_achievements", ("relevant_achievements_weight",)),
            ("cultural_collaboration_fit", ("cultural_collaboration_fit_weight",)),
        ]

        weighted_sum = 0.0
        total_weight = 0.0

        for score_key, weight_keys in components:
            raw_score = scored_resume.get(score_key)
            score = EvalService._safe_number(raw_score)
            weight = 0.0

            for weight_key in weight_keys:
                raw_weight = scored_resume.get(weight_key)
                weight = EvalService._safe_number(raw_weight)
                if weight:
                    break

            weight_fraction = weight / 100.0 if weight > 1 else weight

            if weight_fraction <= 0:
                continue

            weighted_sum += score * weight_fraction
            total_weight += weight_fraction

        if total_weight <= 0:
            return 0.0

        return round(weighted_sum / total_weight, 2) * 0.2

    @staticmethod
    def _calculate_project_score(scored_project_report: dict[str, Any]) -> float:
        components = [
            ("correctness", ("correctness_weight",)),
            (
                "code_quality_structure",
                ("code_quality_structure_weight",),
            ),
            ("resilience_error_handling", ("resilience_error_handling_weight",)),
            ("documentation_explanation", ("documentation_explanation_weight",)),
            ("creativity_bonus", ("creativity_bonus_weight",)),
        ]

        weighted_sum = 0.0
        total_weight = 0.0

        for score_key, weight_keys in components:
            raw_score = scored_project_report.get(score_key)
            score = EvalService._safe_number(raw_score)
            weight = 0.0

            for weight_key in weight_keys:
                raw_weight = scored_project_report.get(weight_key)
                weight = EvalService._safe_number(raw_weight)
                if weight:
                    break

            weight_fraction = weight / 100.0 if weight > 1 else weight

            if weight_fraction <= 0:
                continue

            weighted_sum += score * weight_fraction
            total_weight += weight_fraction

        if total_weight <= 0:
            return 0.0

        return round(weighted_sum / total_weight, 2)

    @staticmethod
    def _safe_number(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
