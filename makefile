.PHONY: run

APP_MODULE ?= app.main:app
UVICORN ?= uvicorn
HOST ?= 0.0.0.0
PORT ?= 8000
UVICORN_ARGS ?= --reload

run:
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) $(UVICORN_ARGS)

install-dependencies:
	pip install -r requirements.txt

ingest-rag-document:
	python -m app.ingestion.seed_docs