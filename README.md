# AI CV Evaluation Backend

## Getting started

### Installation

- Install venv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- Install dependencies

```bash
make install-dependencies
```

### Environment Variables

- Create `.env` using `.env.example` as guidance for the variables
- Gemini is used for the LLM model and Embedding models

### Document Ingestion as Ground Truth

- Add the document to be ingested inside `data_sample/`
- Run document ingestion script

```shell
make ingest-rag-document
```

### Running the App

```bash
make run
```
