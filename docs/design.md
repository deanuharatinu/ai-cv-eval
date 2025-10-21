# AI CV Evaluation Service – Design Overview

## Context & Guiding Principles
- Provide a lightweight service that scores CVs and project reports using LLM and RAG context.
- Keep every infrastructure choice simple for local development, yet isolate it behind interfaces so a production-grade replacement is straightforward.
- Favor clear, synchronous-style code paths on the API boundary while delegating slower work (PDF parsing, LLM calls) to background execution.

## High-Level Architecture
1. **FastAPI HTTP layer** (`app/main.py`, `app/api/`): receives uploads, enqueues evaluation jobs, and exposes result polling endpoints.
2. **Service layer** (`app/services/`): orchestrates business logic. `EvalService` coordinates storage, vector retrieval, LLM scoring, and persistence; `UploadService` saves files.
3. **Adapters** (`app/adapters/`): thin wrappers implementing `Protocol` interfaces for storage, queue, repositories, vector store, and LLM provider. Each default adapter is minimal but intentionally swappable.
4. **Infrastructure** (`app/infra/`): database engine setup and SQLAlchemy models. Uses SQLite by default for zero-config persistence.
5. **Utility helpers** (`app/util/`): shared code such as retry helpers and Gemini embedding integration.

The dependency graph is assembled in `app/dependencies.py`, letting FastAPI dependency injection provide shared singletons without global state.

## Request Lifecycle
1. **Upload** (`POST /upload`):
   - `UploadService` persists two PDFs through the `Storage` interface.
   - Returns deterministic file IDs for later use.
2. **Evaluate** (`POST /evaluate`):
   - `EvalService.enqueue` derives a stable job ID (SHA256 of payload) to deduplicate retries.
   - Validates file existence via `Storage.exists`.
   - Persists a new job row via `Repository.create_job` and schedules asynchronous processing on `InProcessQueue`.
3. **Background processing** (`EvalService._process_job`):
   - Extracts text from PDFs using `pypdf` (run in threads to avoid blocking event loop).
   - Parses structured resume/project report JSON via `LLMProvider`.
   - Retrieves scoring rubrics and briefs from the `VectorStore` (Chroma + Gemini embeddings).
   - Scores resume/report with the LLM, computes aggregate metrics, and stores snapshots through `Repository.update_eval_result`.
   - Updates job status and stage after each milestone for transparent progress reporting.
4. **Result polling** (`GET /result/{job_id}`):
   - Reads job status and aggregated results. Unknown IDs map to HTTP 404.

## Simple Defaults, Swappable Abstractions

| Concern | Default Choice | Swap Strategy |
|---------|----------------|---------------|
| Storage | `LocalStorage` writes to `./data/files` using `pathlib`. | Implement `Storage` Protocol via Amazon S3, GCS, etc.; update provider in `get_storage`. |
| Queue | `InProcessQueue` uses `asyncio` + `ThreadPoolExecutor`. | Replace with Celery, Redis Queue, or Pub/Sub worker by conforming to the `submit(callable)` signature. |
| Database | SQLite file via SQLAlchemy async engine. | Point `settings.database_url` at Postgres/MySQL; models and repository queries already use SQLAlchemy Core. |
| Repository | `SQLiteRepository` with raw SQL text statements. | Implement `Repository` backed by an ORM session, external API, or message bus while keeping service contract intact. |
| LLM Provider | `GeminiLLMProvider` encapsulates prompts, retry, response parsing. | Provide another `LLMProvider` (OpenAI, Anthropic, offline model) by implementing the protocol functions. |
| Vector Store | Chroma persistent client with Gemini embeddings. | Swap in Pinecone, Weaviate, or managed RAG service by offering the `VectorStore` API (`upsert`, `query`). |

Because services depend on Protocols rather than concrete classes, replacements require only updating dependency wiring in `app/dependencies.py` or injecting mocks during testing.

## Data & Schema Highlights
- **Jobs** table (`app/infra/models.py`): tracks job lifecycle, status, stage, error message, and original file IDs.
- **Evaluation Results** table: stores aggregate scores plus raw LLM JSON blobs for auditing.
- **EvaluateRequest** (`app/domain/models.py`): minimal payload (job title + file IDs) keeps API surface simple.
- Score normalization (`EvalService._calculate_cv_match_rate/_calculate_project_score`) converts LLM output into deterministic floats before persistence.

## Resilience & Observability
- Retry wrappers (`app/util/retry.py`) handle transient Gemini faults with exponential backoff.
- Logging config (`app/core/logging.py`) sets a single console handler; production upgrades could add structured logging or centralized sinks without touching service code.
- Job stages (`cv_ingest`, `cv_extract`, `cv_scoring`, etc.) surface meaningful progress for clients polling results.

## LLM & RAG Choices
- Prompts live inside `GeminiLLMProvider`, keeping orchestration logic agnostic to prompt revisions.
- `GeminiEmbeddingFunction` wraps content embedding with shared retry behavior. Failing fast on missing API keys avoids misconfigured deployments.
- RAG ingestion (`app/ingestion/seed_docs.py`) chunkifies PDFs and seeds the `ground_truth` collection; using simple word-window chunking ensures predictable behavior, yet the pipeline can adopt more advanced segmentation later.

## Configuration & Environment
- `app/core/config.py` uses Pydantic settings bound to `.env`, aligning with 12-factor configuration.
- Make targets (`makefile`) bootstrap dependencies, run the FastAPI app, and ingest RAG documents. They provide a simple local workflow that can evolve into CI/CD scripts.

## Future Hardening Paths
1. Introduce a durable task queue (e.g., Celery + Redis) for horizontal scaling and failure recovery.
2. Externalize storage (S3/GCS) with signed URLs to avoid uploading large files through the API gateway.
3. Expand observability: structured logs, metrics, and tracing around LLM latency.
4. Implement auth/tenant isolation on API endpoints when moving beyond trusted environments.
5. Add evaluation history pagination and filters via the repository interface.

This design keeps the foundational pieces intentionally lightweight while isolating integration points so each component can be swapped for a production-grade alternative with minimal upheaval.
