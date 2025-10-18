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
