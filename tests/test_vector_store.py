import asyncio

from app.adapters.vector_store import ChromaDBVectorStore


def test_vector_store_query_uses_seeded_documents():
    store = ChromaDBVectorStore()

    results = asyncio.run(store.query("rubric scoring for cv", top_k=1))

    assert len(results) == 1
    top = results[0]
    assert top["metadata"]["doc_id"] == "case_study_brief"
    assert top["metadata"]["kind"] == "case_study_brief"
