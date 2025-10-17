from typing import Protocol, Sequence


class RetrievedChunk(dict):
    """Simple mapping wrapper for retrieved context."""


class VectorStore(Protocol):
    async def upsert(self, doc_id: str, chunks: Sequence[str]) -> None:
        ...

    async def query(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        ...


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._store: dict[str, list[str]] = {}

    async def upsert(self, doc_id: str, chunks: Sequence[str]) -> None:
        self._store.setdefault(doc_id, []).extend(chunks)

    async def query(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        # TODO: swap with Chroma or FAISS implementation.
        return [RetrievedChunk({"doc_id": doc_id, "text": chunk}) for doc_id, chunks in self._store.items() for chunk in chunks][:top_k]
