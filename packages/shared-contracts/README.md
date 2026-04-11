# Shared Contracts

This package is the canonical v1 contract surface for shapes that must stay aligned
between `frontend/` and `backend/`.

## Structure

- `src/user.ts`: user profile, target updates, onboarding payloads, stats
- `src/auth.ts`: social auth request/response basics
- `src/diagnosis.ts`: diagnosis payloads persisted in UI and returned by API
- `src/blueprint.ts`: action blueprint and quest payloads
- `src/inquiry.ts`: inquiry request/response types plus enum-like validation values
- `src/index.ts`: consolidated exports

## Scope

Put here only DTOs that are part of the shared API contract.

Do not put here:

- backend-only ORM models
- frontend-only presentational view models
- prompt text
- business logic

## Current v1 rule

When frontend and backend disagree, fix the implementation to match this package and
the mirrored backend schemas under `backend/services/api/src/unifoli_api/schemas/`.
