from __future__ import annotations

import chromadb

from pathlib import Path
from typing import Optional, Protocol, Sequence

from app.core.config import settings
from app.util.gemini_embedding import GeminiEmbeddingFunction


class RetrievedChunk(dict):
    """Simple mapping wrapper for retrieved context."""


class VectorStore(Protocol):
    async def upsert(self, doc_id: str, chunks: Sequence[dict[str, str]]) -> None: ...

    async def query(self, query: str, top_k: int = 5) -> list[RetrievedChunk]: ...


class ChromaDBVectorStore(VectorStore):
    def __init__(self, chroma_path: Optional[Path] = None) -> None:
        storage_root = Path(chroma_path or Path(settings.documents_root) / "chroma")
        storage_root.mkdir(parents=True, exist_ok=True)

        self._chromadb_client = chromadb.PersistentClient(path=str(storage_root))
        self._collection = self._chromadb_client.get_or_create_collection(
            name="ground_truth",
            metadata={"hnsw:space": "cosine"},
            embedding_function=GeminiEmbeddingFunction(),
        )

    async def upsert(self, doc_id: str, chunks: Sequence[dict[str, str]]) -> None:
        ids, texts, metadatas = [], [], []
        for i, c in enumerate(chunks):
            ids.append(f"{doc_id}:{i}")
            texts.append(c["text"])
            metadatas.append({"doc_id": doc_id, "kind": c["kind"], "ord": i})

        self._collection.add(ids=ids, documents=texts, metadatas=metadatas)

    async def query(
        self, query: str, top_k: int = 5, where: chromadb.Where = None
    ) -> list[RetrievedChunk]:
        result = self._collection.query(
            query_texts=[query], n_results=top_k, where=where
        )

        return [
            {
                "chunk_id": result["ids"][0][i],
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "score": 1.0 - result["distances"][0][i],
            }
            for i in range(len(result["ids"][0]))
        ]
