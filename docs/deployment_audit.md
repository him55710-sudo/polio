# Uni Foli Deployment Configuration Audit

This document provides a comprehensive mapping of environment variables and configuration settings required for different runtime postures of the Uni Foli platform.

## 1. Deployment Matrix

| Component | Local Dev (Mock) | Local with Ollama | Serverless (Vercel) | Serverful (Worker) |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Auth** | Firebase Emulator | Firebase Production | Firebase Production | Firebase Production |
| **Async Jobs** | Inline (Sync) | Inline (Sync) | Qstash / Edge Queue | Redis + Celery/Worker |
| **PDF Analysis** | Heuristic Mock | Ollama (Llama3) | Google Gemini API | GPT-4o / Claude 3.5 |
| **Frontend** | localhost:5173 | localhost:5173 | Vercel URL | Custom Domain |

## 2. Environment Variables Configuration

### Frontend (`frontend/.env`)

| Variable | Local / Default | Production / Serverless | Purpose |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | `http://127.0.0.1:8000` | `https://api.unifoli.com` | Backend API endpoint |
| `VITE_SYNC_API_JOBS` | `true` | `false` | If true, frontend waits for task completion in one request |
| `VITE_ALLOW_GUEST_MODE`| `true` | `true` | Enable/Disable guest login; set `false` to disable |

### Backend (`backend/.env`)

| Variable | Recommended Value | Purpose |
| :--- | :--- | :--- |
| `APP_ENV` | `development` / `production` | Switches log levels and security strictness |
| `ALLOW_INLINE_JOB_PROCESSING` | `true` (Serverless) / `false` (Worker) | Forces parser/diagnosis to run in the API request thread |
| `ASYNC_JOBS_INLINE_DISPATCH` | `true` | Frontend requests immediate background start via `/process` |
| `LLM_PROVIDER` | `google` / `openai` / `ollama` | Selects the PDF analysis engine |

## 3. Common Failure Signatures & Recovery

### "Guest appears logged in but upload fails"
- **Cause**: Frontend has a local guest session, but backend has `ALLOW_GUEST_MODE=false`.
- **Fix**: Align `ALLOW_GUEST_MODE` in backend with `VITE_ALLOW_GUEST_MODE` in frontend.

### "Diagnosis stalls at 8-15%"
- **Cause**: Sync timeout or LLM connection failure during Stage 2-5 of parsing.
- **Improved Behavior**: System now falls back to "Partially Completed" status, preserving Stage 1 (Extract) results.

### "Frontend calls 127.0.0.1 instead of deployed API"
- **Cause**: `VITE_API_URL` missing or hardcoded to localhost in `api.ts`.
- **Fix**: Check `frontend/src/lib/api.ts` handles dynamic environment detection.

## 4. Maintenance Notes
- **Diagnosis vs Report**: The transition to `RESULT` step now only depends on `diagnosis_run.status`. The PDF report generation is a background task marked by `report_status`. A failure in report generation does NOT hide the diagnosis findings.
- **Stage Progress**: Observability is provided via `parse_metadata.stages`. Monitor this field in logs to identify brittle PDF parsing steps.
