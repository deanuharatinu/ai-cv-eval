from __future__ import annotations

import json
from typing import Any, Optional, Protocol

from app.core.config import settings

from google import genai
from google.genai import types

from app.domain import schemes
from app.util import constants


class LLMProvider(Protocol):
    async def parse_resume(self, *, resume_text: str) -> dict[str, Any]: ...
    async def parse_project_report(
        self, *, project_report_text: str
    ) -> dict[str, Any]: ...
    async def score_resume(
        self,
        *,
        job_title: str,
        scoring_rule: str,
        job_description: str,
        resume: dict[str, Any],
    ) -> dict[str, Any]: ...
    async def score_project_report(
        self,
        *,
        job_title: str,
        scoring_rule: str,
        case_study_brief: str,
        project_report: dict[str, Any],
    ) -> dict[str, Any]: ...


class CVParserError(RuntimeError):
    """Raised when the CV parser fails to return valid JSON output."""


class GeminiLLMProvider(LLMProvider):
    _DEFAULT_MAX_RESUME_CHARS = 18000
    _DEFAULT_TEMPERATURE = 0.3

    def __init__(
        self,
        *,
        client: Optional[genai.Client] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_resume_chars: int = _DEFAULT_MAX_RESUME_CHARS,
    ) -> None:
        self._model = model or settings.llm_model or constants.GEMINI_2_5_FLASH
        self._max_resume_chars = max_resume_chars
        effective_api_key = api_key or settings.llm_provider_api_key
        if not effective_api_key:
            raise ValueError(
                "Missing Gemini API key. Set settings.llm_provider_api_key or GEMINI_API_KEY."
            )

        self._client = client or genai.Client(api_key=effective_api_key)

    async def parse_resume(self, *, resume_text: str) -> dict[str, Any]:
        truncated_resume = resume_text[: self._max_resume_chars]
        prompt = self._build_resume_parser_prompt(truncated_resume)
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        resume_parser_generate_config = types.GenerateContentConfig(
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            seed=0,
            response_mime_type="application/json",
            response_schema=schemes.CV_RESPONSE_SCHEMA,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=resume_parser_generate_config,
        )

        payload_text = self._extract_text(response)
        if not payload_text:
            raise CVParserError("Gemini response was empty.")

        return self._decode_payload(payload_text)

    async def parse_project_report(self, *, project_report_text):
        prompt = self._build_project_report_parser_prompt(project_report_text)
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        resume_parser_generate_config = types.GenerateContentConfig(
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            seed=0,
            response_mime_type="application/json",
            response_schema=schemes.PROJECT_REPORT_SCHEMA,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=resume_parser_generate_config,
        )

        payload_text = self._extract_text(response)
        if not payload_text:
            raise CVParserError("Gemini response was empty.")

        return self._decode_payload(payload_text)

    async def score_resume(
        self,
        *,
        job_title: str,
        scoring_rule: str,
        job_description: str,
        resume: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = self._build_resume_scoring_prompt(
            job_title=job_title,
            scoring_rule=scoring_rule,
            job_description=job_description,
            resume=resume,
        )
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        resume_scoring_generate_config = types.GenerateContentConfig(
            temperature=0.3,
            top_p=0.5,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            seed=0,
            response_mime_type="application/json",
            response_schema=schemes.CV_MATCH_EVALUATION_SCHEMA,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=resume_scoring_generate_config,
        )

        payload_text = self._extract_text(response)
        if not payload_text:
            raise CVParserError("Gemini response was empty.")

        return self._decode_payload(payload_text)

    async def score_project_report(
        self,
        *,
        job_title: str,
        scoring_rule: str,
        case_study_brief: str,
        project_report: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = self._build_project_report_scoring_prompt(
            job_title=job_title,
            scoring_rule=scoring_rule,
            case_study_brief=case_study_brief,
            project_report=project_report,
        )
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        resume_scoring_generate_config = types.GenerateContentConfig(
            temperature=0.3,
            top_p=0.5,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            seed=0,
            response_mime_type="application/json",
            response_schema=schemes.PROJECT_DELIVERABLE_EVALUATION_SCHEMA,
        )

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=resume_scoring_generate_config,
        )

        payload_text = self._extract_text(response)
        if not payload_text:
            raise CVParserError("Gemini response was empty.")

        return self._decode_payload(payload_text)

    def _build_resume_parser_prompt(self, resume_text: str) -> str:
        return (
            "Extract structured JSON for the candidate using the schema shared earlier.\n"
            "Resume contents:\n"
            "<resume>\n"
            f"{resume_text}\n"
            "</resume>"
        )

    def _build_project_report_parser_prompt(self, project_report_text: str) -> str:
        return (
            "Extract structured JSON for the project report using the schema shared earlier.\n"
            "Project Report contents:\n"
            "<project_report>\n"
            f"{project_report_text}\n"
            "</project_report>"
        )

    def _build_resume_scoring_prompt(
        self,
        *,
        job_title: str,
        scoring_rule: str,
        job_description: str,
        resume: dict[str, Any],
    ) -> str:
        resume_json = json.dumps(resume, indent=2)
        scoring_rule_section = (
            scoring_rule.strip() or "No scoring rule context provided."
        )
        job_description_section = (
            job_description.strip() or "No job description context provided."
        )

        return (
            "You are an experienced technical recruiter assessing how well a candidate aligns with the target role.\n"
            f"Role title: {job_title}\n"
            "\n"
            "Use the supplied materials exactly as written:\n"
            "- Treat <scoring_rule> as the definitive rubric. If it differs from prior knowledge, follow the scoring rule.\n"
            "- Treat <job_description>  as the role requirements the candidate must satisfy.\n"
            "- Treat <resume_json> as the structured resume facts; do not infer beyond it.\n"
            "\n"
            "Scoring procedure:\n"
            "- Assign integer values only, 1-5, for every required dimension (1 = poor fit, 5 = outstanding fit).\n"
            "- Justify scores internally with explicit evidence from the resume that maps to the job requirements and rubric.\n"
            "- When evidence is thin or absent, score conservatively rather than guessing.\n"
            "- For each score, provide concise notes explaining the rationale and citing the supporting resume details.\n"
            "- Compute the overall CV match rate by applying the weights from the scoring rule to each category score, summing the weighted results, and returning the final value as a decimal between 0 and 1."
            "\n"
            "Available references:\n"
            "<scoring_rule>\n"
            f"{scoring_rule_section}\n"
            "</scoring_rule>\n"
            "<job_description>\n"
            f"{job_description_section}\n"
            "</job_description>\n"
            "<resume_json>\n"
            f"{resume_json}\n"
            "</resume_json>\n"
            "\n"
            "Think through the evidence step-by-step, then respond with ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "technical_skills_match": <int>,\n'
            '  "technical_skills_match_notes": <str>,\n'
            '  "experience_level": <int>,\n'
            '  "experience_level_notes": <str>,\n'
            '  "relevant_achievements": <int>,\n'
            '  "relevant_achievements_notes": <str>,\n'
            '  "cultural_collaboration_fit": <int>\n'
            '  "cultural_collaboration_fit_notes": <str>\n'
            '  "cv_match_rate": <float>\n'
            '  "cv_feedback": <str>\n'
            "}\n"
            "Do not include commentary, markdown fences, or extra keys in the final response."
        )

    def _build_project_report_scoring_prompt(
        self,
        *,
        job_title: str,
        scoring_rule: str,
        case_study_brief: str,
        project_report: dict[str, Any],
    ) -> str:
        report_json = json.dumps(project_report, indent=2)
        scoring_rule_section = scoring_rule.strip() or "No scoring rule context provided."
        brief_section = case_study_brief.strip() or "No case study brief provided."
        role_title = job_title or "Unknown role"

        return (
            "You are an experienced technical reviewer scoring a candidate's project deliverable for the specified role.\n"
            f"Role title: {role_title}\n"
            "\n"
            "Use the supplied materials exactly as written:\n"
            "- Treat <scoring_rule> as the definitive rubric. If it conflicts with prior knowledge, follow the scoring rule.\n"
            "- Treat <case_study_brief> as the canonical project requirements and evaluation expectations.\n"
            "- Treat <project_report_json> as the structured facts about the candidate's submission; do not infer beyond it.\n"
            "\n"
            "Scoring procedure:\n"
            "- Assign only integers 1-5 for every required dimension (1 = poor, 5 = outstanding).\n"
            "- Base each score on explicit evidence from the project report that maps to the rubric and case study brief.\n"
            "- When evidence is weak or absent, score conservatively rather than guessing.\n"
            "- For every score, supply concise notes that explain the rationale and cite the supporting details from the project report.\n"
            "- Compute the overall project score by applying the weights from the scoring rule to each category score, summing the weighted results, and returning the final value"
            "\n"
            "Available references:\n"
            "<scoring_rule>\n"
            f"{scoring_rule_section}\n"
            "</scoring_rule>\n"
            "<case_study_brief>\n"
            f"{brief_section}\n"
            "</case_study_brief>\n"
            "<project_report_json>\n"
            f"{report_json}\n"
            "</project_report_json>\n"
            "\n"
            "Think through the evidence step-by-step, then respond with ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "correctness": <int>,\n'
            '  "correctness_notes": <str>,\n'
            '  "code_quality_structure": <int>,\n'
            '  "code_quality_structure_notes": <str>,\n'
            '  "resilience_error_handling": <int>,\n'
            '  "resilience_error_handling_notes": <str>,\n'
            '  "documentation_explanation": <int>,\n'
            '  "documentation_explanation_notes": <str>,\n'
            '  "creativity_bonus": <int>,\n'
            '  "creativity_bonus_notes": <str>\n'
            '  "project_score": <float>\n'
            '  "project_feedback": <str>\n'
            "}\n"
            "Do not include commentary, markdown fences, or extra keys in the final response."
        )

    @staticmethod
    def _extract_text(response: types.GenerateContentResponse) -> str:
        if getattr(response, "output_text", None):
            return response.output_text

        parts: list[str] = []
        for candidate in response.candidates or []:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        parts.append(part.text)
        return "".join(parts)

    def _decode_payload(self, raw_text: str) -> dict[str, Any]:
        cleaned = self._strip_json_fence(raw_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise CVParserError(
                "Gemini response was not valid JSON.: {cleaned}"
            ) from exc

    @staticmethod
    def _strip_json_fence(text_value: str) -> str:
        stripped = text_value.strip()
        if not stripped.startswith("```"):
            return stripped
        stripped = stripped[3:].lstrip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].lstrip()
        if "```" in stripped:
            stripped = stripped.rsplit("```", 1)[0]
        return stripped.strip()
