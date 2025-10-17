import asyncio
from pathlib import Path

from app.adapters.vector_store import InMemoryVectorStore
from app.core.config import settings


async def seed_internal_documents() -> None:
    """Load static documents (brief, rubrics) and push to vector store."""
    store = InMemoryVectorStore()
    docs_path = Path(settings.documents_root)
    docs_path.mkdir(parents=True, exist_ok=True)

    # TODO: parse the PDF brief into chunks before pushing to the vector store.
    brief_path = docs_path / "case_study_brief.txt"
    if brief_path.exists():
        chunks = [brief_path.read_text()]
        await store.upsert("case_study_brief", chunks)


if __name__ == "__main__":
    asyncio.run(seed_internal_documents())
