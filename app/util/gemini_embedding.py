import chromadb

from typing import List, Optional, Sequence

from google import genai
from google.genai import types

from app.core.config import settings
from app.util import constants


class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(
        self,
        *,
        genai_client: Optional[genai.Client] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        api_key = settings.llm_provider_api_key
        if not api_key:
            raise ValueError(
                "Missing Gemini API key. Set settings.llm_provider_api_key or GEMINI_API_KEY."
            )

        self._genai_client = genai_client or genai.Client(api_key=api_key)
        self._embedding_model = embedding_model or constants.GEMINI_EMBEDDING_001
        super().__init__()

    def __call__(self, documents: Sequence[str]) -> chromadb.Embeddings:
        embeddings: List[List[float]] = []
        for doc in documents:
            response = self._genai_client.models.embed_content(
                model=self._embedding_model,
                contents=doc,
                config=types.EmbedContentConfig(
                    task_type="retrieval_document",
                    title="ground_truth_chunk",
                ),
            )

            if hasattr(response, "embedding"):
                embeddings.append(list(response.embedding.values))
            elif hasattr(response, "embeddings"):
                embeddings.append(list(response.embeddings[0].values))
            else:
                raise RuntimeError(
                    "Unexpected response format from Gemini embeddings API."
                )

        return embeddings
