from fastapi import APIRouter, Depends
from unifoli_api.core.config import Settings, get_settings
from unifoli_api.schemas.runtime import RuntimeCapabilities

router = APIRouter()

@router.get("/capabilities", response_model=RuntimeCapabilities)
async def get_runtime_capabilities(settings: Settings = Depends(get_settings)):
    # Logic to decide recommended modes
    # If serverless, recommended is often async if we have a worker, 
    # but if we are in serverless NO worker mode, we must use sync or inline.
    
    # Assumption: if serverless and async_jobs_inline_dispatch is true, 
    # it means we handle jobs during the request or in a background thread.
    
    is_serverless = settings.serverless_runtime
    
    recommended_parse = "async"
    recommended_diagnosis = "async"
    
    if is_serverless:
        # In serverless, we prefer sync for short tasks if no worker exists,
        # but the project seems to prefer async jobs even in serverless if inline dispatch is on.
        # However, for pure serverless (e.g. Vercel), long jobs might timeout.
        pass

    return RuntimeCapabilities(
        allow_inline_job_processing=settings.allow_inline_job_processing,
        async_jobs_inline_dispatch=settings.async_jobs_inline_dispatch,
        serverless_runtime=is_serverless,
        recommended_document_parse_mode="sync" if settings.allow_inline_job_processing and not is_serverless else "async",
        recommended_diagnosis_mode="async",
        requires_explicit_process_kicking=not settings.async_jobs_inline_dispatch
    )
