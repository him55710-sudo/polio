from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
import uvicorn

from unifoli_api.core.config import get_settings
from unifoli_api.core.errors import UniFoliErrorCode
from unifoli_api.core.runtime_diagnostics import (
    build_health_payload,
    classify_startup_failure,
    snapshot_settings_from_env,
)
from unifoli_shared.paths import ensure_app_directories

logger = logging.getLogger("unifoli.api")

def _set_runtime_boot_state(
    app: FastAPI,
    *,
    ready: bool,
    stage: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    app.state.runtime_boot_ready = ready
    app.state.runtime_boot_stage = stage
    app.state.runtime_boot_error_code = error_code
    app.state.runtime_boot_error_message = error_message


def _bootstrap_health_payload(
    *,
    app: FastAPI,
    stage: str,
    error: Exception | str,
    settings=None,
) -> dict[str, object]:
    effective_settings = settings or snapshot_settings_from_env()
    _set_runtime_boot_state(
        app,
        ready=False,
        stage=stage,
        error_code=classify_startup_failure(error),
        error_message=str(error).strip() or "Backend startup failed.",
    )
    return build_health_payload(effective_settings, app_state=app.state, check_db=False, check_llm=False)


def _create_boot_failure_app(*, stage: str, error: Exception | str, settings=None) -> FastAPI:
    effective_settings = settings or snapshot_settings_from_env()
    api_prefix = str(getattr(effective_settings, "api_prefix", None) or os.getenv("API_PREFIX") or "/api/v1").strip() or "/api/v1"
    app = FastAPI(
        title="Uni Foli Backend",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    payload = _bootstrap_health_payload(app=app, stage=stage, error=error, settings=effective_settings)

    @app.get(f"{api_prefix}/health", include_in_schema=False)
    @app.get(f"{api_prefix}/readiness", include_in_schema=False)
    async def boot_failure_health() -> JSONResponse:
        return JSONResponse(status_code=503, content=payload)

    @app.get(f"{api_prefix}/runtime/capabilities", include_in_schema=False)
    async def boot_failure_capabilities() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": UniFoliErrorCode.BACKEND_STARTUP_FAILED.value,
                    "message": "Backend startup failed before runtime capabilities became available.",
                    "debug_detail": payload["startup"]["message"],
                    "stage": payload["startup"]["stage"],
                }
            },
        )

    @app.get("/", include_in_schema=False)
    async def boot_failure_home() -> HTMLResponse:
        return HTMLResponse(
            """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Uni Foli Backend Boot Failure</title>
  </head>
  <body>
    <main style="max-width:760px;margin:48px auto;font-family:Segoe UI,Noto Sans KR,sans-serif;line-height:1.6;padding:0 20px;">
      <h1>Uni Foli backend is not ready.</h1>
      <p>The Python API booted into a diagnostic mode so the deployment can report why requests are blocked.</p>
      <p>Check <code>/api/v1/health</code> or <code>/api/v1/readiness</code> for the structured startup error.</p>
    </main>
  </body>
</html>
            """.strip(),
            status_code=503,
        )

    return app


def _is_readiness_exempt_path(path: str, api_prefix: str) -> bool:
    if path in {"/", "/favicon.ico"}:
        return True
    exempt_suffixes = {
        f"{api_prefix}/health",
        f"{api_prefix}/readiness",
        f"{api_prefix}/runtime/capabilities",
    }
    return path in exempt_suffixes


def create_app() -> FastAPI:
    try:
        settings = get_settings()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Backend settings bootstrap failed.")
        return _create_boot_failure_app(stage="settings", error=exc)

    allow_origin_regex = settings.cors_origin_regex
    if settings.app_env == "local" and not allow_origin_regex:
        allow_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    docs_enabled = settings.api_docs_enabled or settings.app_env == "local"

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        _set_runtime_boot_state(app_instance, ready=True, stage="initializing")
        ensure_app_directories()
        try:
            from unifoli_api.core.database import initialize_database

            initialize_database()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Backend startup readiness failed.")
            _set_runtime_boot_state(
                app_instance,
                ready=False,
                stage="database_initialization",
                error_code=classify_startup_failure(exc),
                error_message=str(exc).strip() or "Database initialization failed.",
            )
        else:
            _set_runtime_boot_state(app_instance, ready=True, stage="ready")
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        description=(
            "Beginner-friendly backend skeleton for Uni Foli. "
            "Create projects, upload files, write drafts, and queue render jobs."
        ),
    )
    app.state.runtime_settings = settings
    _set_runtime_boot_state(app, ready=True, stage="bootstrapping")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import time
        start_time = time.monotonic()
        try:
            if not getattr(request.app.state, "runtime_boot_ready", True) and not _is_readiness_exempt_path(request.url.path, settings.api_prefix):
                payload = build_health_payload(settings, app_state=request.app.state, check_db=False, check_llm=False)
                response = JSONResponse(status_code=503, content=payload)
                duration = time.monotonic() - start_time
                logger.error(
                    "Request blocked while backend is unready: %s",
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "duration_ms": int(duration * 1000),
                        "client": request.client.host if request.client else "unknown",
                        "boot_stage": payload["startup"]["stage"],
                        "error_code": payload["startup"]["error_code"],
                    },
                )
                response.headers.setdefault("X-Content-Type-Options", "nosniff")
                response.headers.setdefault("X-Frame-Options", "DENY")
                response.headers.setdefault("Referrer-Policy", "no-referrer")
                return response

            response = await call_next(request)
            duration = time.monotonic() - start_time
            
            # Simple structured log
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": int(duration * 1000),
                "client": request.client.host if request.client else "unknown",
            }
            if response.status_code >= 400:
                logger.warning("Request completed: %s", log_data)
            else:
                logger.info("Request completed: %s", log_data)

            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            return response
        except Exception as exc:
            duration = time.monotonic() - start_time
            logger.error(
                "Request failed: %s %s | duration: %dms",
                request.method, request.url.path, int(duration * 1000),
                exc_info=True
            )
            raise

    try:
        from unifoli_api.api.router import api_router
    except Exception as exc:  # noqa: BLE001
        logger.exception("Backend router import failed.")
        return _create_boot_failure_app(stage="router_import", error=exc, settings=settings)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    def home_page() -> Response:
        if settings.app_env != "local" and settings.api_root_redirect_enabled:
            target = (settings.public_app_base_url or "").strip()
            if target:
                return RedirectResponse(url=target, status_code=307)

        docs_card = (
            """
          <a class="card" href="/docs">
            <strong>Open API Docs</strong>
            Browse and execute every route from Swagger UI.
            <code>/docs</code>
          </a>
            """.strip()
            if docs_enabled
            else """
          <div class="info">
            <strong>API Docs Hidden</strong>
            Interactive API docs are disabled by default outside local development.
          </div>
            """.strip()
        )
        return HTMLResponse(
            """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Uni Foli Backend</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f3f7fb;
        --card: #ffffff;
        --ink: #0f172a;
        --muted: #475569;
        --line: #dbe4ee;
        --accent: #0f766e;
        --accent-strong: #115e59;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Segoe UI", "Noto Sans KR", sans-serif;
        background:
          radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 28%),
          linear-gradient(180deg, #f8fbfd 0%, var(--bg) 100%);
        color: var(--ink);
      }
      main {
        max-width: 920px;
        margin: 0 auto;
        padding: 60px 40px;
      }
      .hero {
        margin-bottom: 80px;
        text-align: center;
      }
      .eyebrow {
        display: inline-block;
        margin-bottom: 16px;
        padding: 6px 14px;
        border-radius: 99px;
        background: #e0f2f1;
        color: #0d9488;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }
      h1 {
        margin: 0 0 24px 0;
        color: var(--ink);
        font-size: 48px;
        font-weight: 800;
        line-height: 1.1;
        letter-spacing: -0.02em;
      }
      p {
        max-width: 600px;
        margin: 0 auto 40px auto;
        color: var(--muted);
        font-size: 18px;
        line-height: 1.6;
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        justify-content: center;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 24px;
      }
      .info {
        padding: 32px;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--card);
      }
      .card {
        display: block;
        width: 280px;
        padding: 32px;
        text-decoration: none;
        text-align: left;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: var(--card);
        color: var(--muted);
        font-size: 15px;
        line-height: 1.5;
        transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
      }
      a.card:hover, a.card:focus-visible {
        transform: translateY(-2px);
        border-color: rgba(15, 118, 110, 0.4);
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
      }
      strong {
        display: block;
        margin-bottom: 8px;
        color: var(--ink);
        font-size: 18px;
      }
      code {
        display: inline-block;
        margin-top: 8px;
        padding: 4px 8px;
        border-radius: 8px;
        background: #e2f3f1;
        color: #134e4a;
        font-size: 13px;
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <span class="eyebrow">Uni Foli backend</span>
        <h1>Upload, parse, draft, and render from one backend.</h1>
        <p>
          This local service powers the beginner-friendly backend blueprint for Uni Foli.
          Confirm health, inspect available render formats, and use interactive docs only when
          they are explicitly enabled for the current environment.
        </p>
        <div class="actions">
          __DOCS_CARD__
          <a class="card" href="/api/v1/health">
            <strong>Check Server Health</strong>
            Confirm the backend is responding correctly.
            <code>/api/v1/health</code>
          </a>
          <a class="card" href="/api/v1/render-jobs/formats">
            <strong>See Render Formats</strong>
            Verify which export formats are available now.
            <code>/api/v1/render-jobs/formats</code>
          </a>
        </div>
      </section>
      <section class="grid" aria-label="backend highlights">
        <div class="info">
          <strong>Automatic Ingest</strong>
          PDF, TXT, and MD uploads can be parsed into documents and chunks immediately.
        </div>
        <div class="info">
          <strong>Selected Rendering</strong>
          Users choose one output format per job: PDF, PPTX, or HWPX.
        </div>
        <div class="info">
          <strong>Safe Local Setup</strong>
          SQLite works out of the box, and PostgreSQL plus pgvector is ready when needed.
        </div>
      </section>
    </main>
  </body>
</html>
            """.replace("__DOCS_CARD__", docs_card).strip()
        )

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    return app


print("INIT: Creating FastAPI app...")
app = create_app()
if getattr(app.state, "runtime_boot_ready", True):
    print("INIT: FastAPI app created successfully.")
else:
    print(
        "INIT: FastAPI app created in degraded boot mode. "
        f"stage={getattr(app.state, 'runtime_boot_stage', 'unknown')} "
        f"code={getattr(app.state, 'runtime_boot_error_code', 'unknown')}"
    )


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "unifoli_api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )


if __name__ == "__main__":
    run()
