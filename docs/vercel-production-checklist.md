# Uni Foli Vercel Production Checklist

This checklist is the source of truth for production deployments that need the diagnosis upload flow to work.

## 1. Choose the right deployment shape

### Shared frontend + backend in one Vercel project

- Set the Vercel Root Directory to the repo root.
- Keep the root [`vercel.json`](../vercel.json) active.
- The Python API entrypoint must stay at [`api/index.py`](../api/index.py).
- Do not set `VITE_API_URL` when frontend and backend share the same Vercel origin.
- Frontend requests such as `/api/v1/documents/upload` will then resolve to the same origin and be rewritten to the Python function.

### Separate frontend and backend projects

- Frontend project Root Directory may be `frontend/`.
- Backend project Root Directory must still expose the Python API entrypoint and `/api/v1/*` routes.
- Set `VITE_API_URL` to the backend origin.
- Add the frontend origin to backend `CORS_ORIGINS`.

## 2. Minimum backend env vars for diagnosis upload

These values are required before upload, parse, and diagnosis can work in production.

- `APP_ENV=production`
- `APP_DEBUG=false`
- `DATABASE_URL=<managed postgres connection string>`
- `CORS_ORIGINS=https://<your-frontend-origin>`
- `AUTH_ALLOW_LOCAL_DEV_BYPASS=false`

If the database provider gives a provider-specific environment variable instead
of `DATABASE_URL`, the backend also accepts these aliases:

- `SUPABASE_DATABASE_URL`
- `POSTGRES_URL`
- `POSTGRES_URL_NON_POOLING`
- `POSTGRES_PRISMA_URL`

`DATABASE_URL` has priority when more than one of these values is set. When
moving to Supabase, replace or remove the old provider `DATABASE_URL` instead
of leaving it alongside a new alias.

Recommended for shared Vercel serverless runtime:

- `ALLOW_INLINE_JOB_PROCESSING=true`
- `ASYNC_JOBS_INLINE_DISPATCH=true`
- `POSTGRES_ENABLE_PGVECTOR=false` unless your Postgres instance supports `pgvector`

Do not rely on these in production except as a temporary emergency escape hatch:

- `ALLOW_PRODUCTION_SQLITE=true` (이 설정은 운영 환경에서 **매우 위험**하며, readiness 체크를 통과하지 못하게 만듭니다)
- default SQLite `DATABASE_URL`

SQLite는 Vercel/serverless 환경에서 데이터가 영구 저장되지 않으며, 동시 요청 시 `database is locked` 오류가 발생합니다. 운영 환경에서는 반드시 Managed PostgreSQL을 사용해야 합니다.

## 3. Backend auth/env checklist

At least one backend auth verification path must be configured:

- JWT mode:
  - `AUTH_JWT_SECRET` or `AUTH_JWT_PUBLIC_KEY`
- Firebase mode:
  - `FIREBASE_PROJECT_ID`
  - `FIREBASE_SERVICE_ACCOUNT_JSON` or `FIREBASE_SERVICE_ACCOUNT_JSON_BASE64`
  - or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a deployed credentials file

If social login is enabled:

- `AUTH_SOCIAL_LOGIN_ENABLED=true`
- `AUTH_SOCIAL_STATE_SECRET=<random secret>`
- provider-specific redirect URIs must target the deployed frontend origin, not localhost

## 4. LLM env checklist

Diagnosis upload itself should not fail because of LLM credentials, but production diagnosis quality depends on them.

Gemini path:

- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=<backend-only secret>`
- Accepted aliases: `GOOGLE_API_KEY` or `GENAI_API_KEY`

Optional PDF analysis Gemini override:

- `PDF_ANALYSIS_LLM_PROVIDER=gemini`
- `PDF_ANALYSIS_GEMINI_API_KEY=<backend-only secret>`

If using Ollama outside local development:

- `OLLAMA_BASE_URL=https://<remote-ollama-endpoint>/v1`
- `PDF_ANALYSIS_OLLAMA_BASE_URL=https://<remote-ollama-endpoint>/v1`

Do not point production Ollama settings to `localhost`.

### 4.1 LLM Input Budgeting (Safety)

Large student documents can exceed Gemini's context window or cost too much. Use these to safely truncate input:

- `DIAGNOSIS_LLM_MAX_INPUT_CHARS=120000` (Default)
- `PDF_ANALYSIS_MAX_INPUT_CHARS=60000`
- `SEMANTIC_EXTRACTION_MAX_INPUT_CHARS=80000`
- `GEMINI_MAX_OUTPUT_TOKENS=4096`

## 5. Frontend env checklist

Shared monorepo deployment:

- `VITE_API_URL` should be unset
- `VITE_SYNC_API_JOBS=true` only if you intentionally want the browser to wait for inline API work

Separate frontend deployment:

- `VITE_API_URL=https://<backend-origin>`
- `VITE_SYNC_API_JOBS=true` only when the backend has no worker and is expected to process jobs inline

Never expose backend secrets such as `GEMINI_API_KEY` in frontend env files.

## 6. Health/readiness checks after deploy

Run these immediately after each deploy:

```bash
curl -i https://<your-origin>/api/v1/health
curl -i https://<your-origin>/api/v1/readiness
```

Expected success signals:

- `200 OK`
- `"status":"ok"`
- `"boot_ok":true`
- `database.connected=true` on `/api/v1/readiness`
- `llm.gemini_api_key_configured=true` on `/api/v1/readiness?check_llm=true`

Common failure signals:

- `BACKEND_STARTUP_FAILED`
- `PRODUCTION_SQLITE_UNSAFE`: Production 환경에서 SQLite를 사용 중임 (DATABASE_URL을 Postgres로 변경 필요)
- `DATABASE_URL_REQUIRED`
- `DB_SCHEMA_MISMATCH`: DB 스키마가 최신이 아님 (Alembic migration 실행 필요)
- `DATABASE_UNAVAILABLE`

## 7. Required manual steps outside the repo

1. Provision a managed Postgres database (recommended: Supabase Postgres; AWS RDS is also compatible).
2. Set `DATABASE_URL` in the Vercel project settings, or set one of the supported aliases such as `SUPABASE_DATABASE_URL`.
3. Run Alembic migrations against that database:
   - 로컬에서 운영 DB URL을 임시로 `DATABASE_URL`로 설정한 후 `alembic upgrade head` 실행
   - 또는 CI/CD 파이프라인에서 실행
4. /api/v1/readiness를 호출하여 `database.connected=true` 및 `database.scheme=postgresql` 확인.
5. `DB_SCHEMA_MISMATCH` 발생 시 migration이 누락되었음을 의미하므로 다시 upgrade를 시도하세요.
6. Set backend auth secrets.
7. Add the deployed frontend origin to:
   - backend `CORS_ORIGINS`
   - Firebase Authorized Domains
8. Set Gemini credentials if you want Gemini-backed diagnosis enrichment.

### 7.1 Moving to Supabase without rewriting the app

The backend data model is SQLAlchemy plus Alembic. Use another managed
Postgres service when the current database quota is exhausted. Supabase
Postgres is the lowest-risk replacement because it preserves SQL migrations,
relationships, and the existing query code. Firebase Auth and Firebase Storage
can still be used alongside Postgres.

Recommended Supabase path:

1. Create a Supabase project.
2. Copy the Supabase pooled Postgres connection string for app runtime.
3. Set it as `SUPABASE_DATABASE_URL` or `DATABASE_URL` in Vercel.
4. Remove or replace any old provider `DATABASE_URL` so it does not take priority.
5. Keep `POSTGRES_ENABLE_PGVECTOR=false` unless the target database has the
   vector extension enabled.
6. Run migrations once against the same database.
7. Deploy and verify `/api/v1/readiness?check_db=true`.

Avoid moving the primary relational data to Cloud Firestore unless you are
planning a larger persistence rewrite. Firestore is a document database, so it
does not run the current Alembic migrations, joins, SQL queries, or pgvector
path.

## 8. Symptoms and direct meaning

- **`HTML_MISROUTE`**
  - **증상**: 프론트엔드가 API 응답(JSON) 대신 HTML을 받음.
  - **원인 1 (분리 배포)**: `VITE_API_URL`이 백엔드 주소가 아닌 프론트엔드 주소로 설정되어, 백엔드로 가야 할 요청을 프론트엔드 라우터(React Router)가 낚아채서 index.html을 반환함.
  - **원인 2 (통합 배포)**: `vercel.json`의 rewrites 설정이 누락되거나 작동하지 않아 `/api/*` 요청이 Python 서버로 전달되지 않고 프론트엔드 정적 파일로 연결됨.
  - **조치**: `VITE_API_URL`을 확인하고, 통합 배포라면 해당 변수를 비우고 rewrite 설정을 점검하세요.

- **`NETWORK_UNREACHABLE`**
  - **증상**: 브라우저가 서버로부터 어떤 응답도 받지 못함.
  - **원인**: 백엔드 서버 다운, 잘못된 도메인/IP, 혹은 CORS 정책 위반으로 브라우저가 요청을 차단함.
  - **조치**: 백엔드 로그를 확인하고, `CORS_ORIGINS`에 현재 프론트엔드 도메인이 포함되어 있는지 확인하세요.

- **`BACKEND_STARTUP_FAILED` (500/502/503)**
  - **증상**: 서버가 살아있으나 내부 오류로 응답을 못 함.
  - **원인**: `DATABASE_URL` 누락, 라이브러리 설치 오류, 혹은 런타임 크래시.
  - **조치**: Vercel Function Logs를 확인하여 traceback을 추적하세요.

- **`DATABASE_UNAVAILABLE`**
  - **증상**: 서버는 작동하나 데이터베이스 연결 실패.
  - **조치**: DB 암호, 호스트 설정, 화이트리스트 IP 설정을 확인하세요.

---

## 9. Deployment Mode Quick Summary

| 항목 | 통합 배포 (Monolith) | 분리 배포 (Decoupled) |
| :--- | :--- | :--- |
| **VITE_API_URL** | **비워둠 (Empty)** | **백엔드 Origin URL** (e.g., `https://api.unifoli.com`) |
| **vercel.json** | 필수 (rewrites 설정) | 선택 사항 |
| **CORS_ORIGINS** | 필요 없음 (Same-Origin) | 필수 (프론트엔드 Origin 주소) |
| **Firebase Domain** | 자동 추가됨 | 수동으로 백엔드/프론트엔드 도메인 추가 필요 |
