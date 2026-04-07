$env:PYTHONPATH = "services/api/src;services/worker/src;services/render/src;services/ingest/src;packages/domain/src;packages/shared/src;packages/parsers/src;packages/prompts/src"
.\.venv\Scripts\python.exe -m uvicorn polio_api.main:app --host 127.0.0.1 --port 8000
