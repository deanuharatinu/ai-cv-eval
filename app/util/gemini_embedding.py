import chromadb
import logging

from functools import partial
from typing import List, Optional, Sequence

from google import genai
from google.genai import types

from app.core.config import settings
from app.util import constants
from app.util.retry import is_retryable_gemini_error, sync_retry


class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(
        self,
        *,
        genai_client: Optional[genai.Client] = None,
        embedding_model: Optional[str] = None,
        retry_attempts: int = 4,
        retry_base_delay: float = 0.6,
        retry_max_delay: float = 6.0,
        retry_jitter: float = 0.4,
    ) -> None:
        api_key = settings.llm_provider_api_key
        if not api_key:
            raise ValueError(
                "Missing Gemini API key. Set settings.llm_provider_api_key or GEMINI_API_KEY."
            )

        self._genai_client = genai_client or genai.Client(api_key=api_key)
        self._embedding_model = embedding_model or constants.GEMINI_EMBEDDING_001
        self._logger = logging.getLogger(self.__class__.__name__)
        self._retry_attempts = retry_attempts
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay
        self._retry_jitter = retry_jitter
        super().__init__()

    def __call__(self, documents: Sequence[str]) -> chromadb.Embeddings:
        embeddings: List[List[float]] = []
        for doc in documents:
            operation = partial(self._embed_single_document, doc)
            vector = sync_retry(
                operation,
                attempts=self._retry_attempts,
                base_delay=self._retry_base_delay,
                max_delay=self._retry_max_delay,
                jitter=self._retry_jitter,
                should_retry=is_retryable_gemini_error,
                logger=self._logger,
                context="gemini.embed_content",
            )
            embeddings.append(vector)

        return embeddings

    def _embed_single_document(self, document: str) -> List[float]:
        response = self._genai_client.models.embed_content(
            model=self._embedding_model,
            contents=document,
            config=types.EmbedContentConfig(
                task_type="retrieval_document",
                title="ground_truth_chunk",
            ),
        )

        if hasattr(response, "embedding"):
            return list(response.embedding.values)
        if hasattr(response, "embeddings"):
            return list(response.embeddings[0].values)
        raise RuntimeError("Unexpected response format from Gemini embeddings API.")
