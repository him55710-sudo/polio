from pydantic import BaseModel

class RuntimeCapabilities(BaseModel):
    allow_inline_job_processing: bool
    async_jobs_inline_dispatch: bool
    serverless_runtime: bool
    recommended_document_parse_mode: str  # "sync" or "async"
    recommended_diagnosis_mode: str      # "sync" or "async"
    requires_explicit_process_kicking: bool
