# AI CV Evaluation Backend

## Getting started

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

- Gemini is used for the LLM model and Embedding models

### Running the App

```bash
uvicorn app.main:app --reload
```

### Document Ingestion as Ground Truth

- Add the document to be ingested on `data/documents/`
- Run document ingestion script

```shell
python -m app.ingestion.seed_docs
```