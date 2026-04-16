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

Recommended for shared Vercel serverless runtime:

- `ALLOW_INLINE_JOB_PROCESSING=true`
- `ASYNC_JOBS_INLINE_DISPATCH=true`
- `POSTGRES_ENABLE_PGVECTOR=false` unless your Postgres instance supports `pgvector`

Do not rely on these in production except as a temporary emergency escape hatch:

- `ALLOW_PRODUCTION_SQLITE=true`
- default SQLite `DATABASE_URL`

Using SQLite on Vercel will not preserve diagnosis data reliably and can still fail readiness when schema initialization is missing.

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

Optional PDF analysis Gemini override:

- `PDF_ANALYSIS_LLM_PROVIDER=gemini`
- `PDF_ANALYSIS_GEMINI_API_KEY=<backend-only secret>`

If using Ollama outside local development:

- `OLLAMA_BASE_URL=https://<remote-ollama-endpoint>/v1`
- `PDF_ANALYSIS_OLLAMA_BASE_URL=https://<remote-ollama-endpoint>/v1`

Do not point production Ollama settings to `localhost`.

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

Common failure signals:

- `BACKEND_STARTUP_FAILED`
- `DATABASE_URL_REQUIRED`
- `DB_SCHEMA_MISMATCH`
- `DATABASE_UNAVAILABLE`

## 7. Required manual steps outside the repo

1. Provision a managed Postgres database.
2. Set `DATABASE_URL` in the Vercel project.
3. Run Alembic migrations against that database before routing production traffic.
4. Set backend auth secrets.
5. Add the deployed frontend origin to:
   - backend `CORS_ORIGINS`
   - Firebase Authorized Domains
6. Set Gemini credentials if you want Gemini-backed diagnosis enrichment.

## 8. Symptoms and direct meaning

- Frontend shows `HTML_MISROUTE`
  - `VITE_API_URL` points at the frontend origin or rewrites are bypassed.
- Frontend shows `NETWORK_UNREACHABLE`
  - browser never received a normal HTTP response; inspect DNS, TLS, CORS, or total backend outage.
- Frontend shows `BACKEND_STARTUP_FAILED`
  - Vercel reached the Python function, but the backend failed before serving normal API responses.
- `/api/v1/health` returns `DB_SCHEMA_MISMATCH`
  - the database exists but migrations have not reached Alembic head.
