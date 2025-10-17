from typing import Protocol


class RAGService(Protocol):
    async def retrieve_cv_context(self, job_title: str, cv_snapshot: dict) -> list[str]:
        ...

    async def retrieve_project_context(self, sections: dict) -> list[str]:
        ...


class SimpleRAGService:
    async def retrieve_cv_context(self, job_title: str, cv_snapshot: dict) -> list[str]:
        # TODO: integrate vector store retrieval.
        return []

    async def retrieve_project_context(self, sections: dict) -> list[str]:
        return []
