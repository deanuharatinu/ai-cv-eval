import uuid
import chromadb

from pathlib import Path
from typing import List
from pypdf import PdfReader

from app.core.config import settings
from app.util.gemini_embedding import GeminiEmbeddingFunction

DEFAULT_DOC_ID = "case_study_brief"


def load_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> List[str]:
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks: List[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if not window:
            continue
        chunks.append(" ".join(window))
        if start + chunk_size >= len(words):
            break
    return chunks


def seed_internal_documents(
    brief_pdf: Path,
    chroma_path: Path | None = None,
    doc_id: str = DEFAULT_DOC_ID,
) -> None:
    """
    Ingest the provided PDF into the ground_truth collection.
    Stores the document as sequential chunks tagged by doc_id for retrieval.
    """
    pdf_path = brief_pdf
    if not pdf_path.exists():
        raise FileNotFoundError(f"Could not locate brief PDF at {pdf_path}")

    raw_text = load_pdf_text(pdf_path)
    chunks = chunk_text(raw_text)
    if not chunks:
        raise ValueError("No textual content extracted from PDF")

    docs_root = Path(settings.documents_root)
    docs_root.mkdir(parents=True, exist_ok=True)

    chroma_root = chroma_path or docs_root / "chroma"
    chroma_root.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_root))
    embedding_function = GeminiEmbeddingFunction()

    collection = client.get_or_create_collection(
        name="ground_truth",
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function,
    )

    metadatas = [
        {"doc_id": doc_id, "kind": doc_id, "ordinal": idx} for idx in range(len(chunks))
    ]
    ids = [f"{doc_id}-{uuid.uuid4().hex[:8]}-{idx}" for idx in range(len(chunks))]

    existing = collection.get(where={"doc_id": doc_id})
    existing_ids = existing.get("ids") or []
    if existing_ids:
        collection.delete(ids=existing_ids)

    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

    result = collection.query(
        query_texts="case study brief backend developer objectives"
    )
    print(f"result: {result}")


if __name__ == "__main__":
    seed_internal_documents(brief_pdf=Path("data_sample/ground-truth-doc.pdf"))
