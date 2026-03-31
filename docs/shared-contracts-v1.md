# Shared Contracts v1

This document fixes the first contract surface that both the frontend and backend must treat as canonical.

## Why This Was Fixed First

The current repo already had real API usage spread across:

- dashboard and onboarding profile flows
- diagnosis payload persistence
- current blueprint and quest start flows
- public inquiry submission

Those shapes were duplicated in several frontend files and one important backend endpoint still returned loose `dict[str, object]` payloads. In parallel AI work, that is where shape drift starts first.

This v1 pass keeps the scope intentionally small and only locks the APIs already in active use.

## Canonical Contract Surface

The canonical shared DTOs now live under `packages/shared-contracts/src/`.

### User and onboarding

- `UserProfile`
- `UserTargetsUpdateRequest`
- `UserTargetsUpdateResponse`
- `UserStats`
- `OnboardingProfileUpdateRequest`
- `OnboardingGoalsUpdateRequest`

Mapped endpoints:

- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me/targets`
- `POST /api/v1/users/onboarding/profile`
- `POST /api/v1/users/onboarding/goals`
- `GET /api/v1/projects/user/stats`

### Diagnosis and grounded progress state

- `DiagnosisResultPayload`
- `StoredDiagnosis`
- `DiagnosisRunRequest`
- `DiagnosisRunResponse`

Mapped endpoints:

- `POST /api/v1/diagnosis/run`
- `POST /api/v1/diagnosis/runs`
- `GET /api/v1/diagnosis/{diagnosis_id}`
- `GET /api/v1/diagnosis/project/{project_id}/latest`

### Blueprint and quest flow

- `BlueprintQuest`
- `CurrentBlueprintResponse`
- `QuestStartPayload`

Mapped endpoints:

- `GET /api/v1/blueprints/current`
- `POST /api/v1/quests/{quest_id}/start`

### Inquiry intake

- `InquiryPayload`
- `InquiryResponse`
- inquiry enum-like validation values:
  - `INQUIRY_TYPE_VALUES`
  - `INQUIRY_CATEGORY_VALUES`
  - `ONE_TO_ONE_INQUIRY_CATEGORY_VALUES`
  - `PARTNERSHIP_INQUIRY_CATEGORY_VALUES`
  - `BUG_REPORT_INQUIRY_CATEGORY_VALUES`
  - `INSTITUTION_TYPE_VALUES`

Mapped endpoint:

- `POST /api/v1/inquiries`

### Auth basics

- `SocialProviderPrepareRequest`
- `SocialProviderPrepareResponse`
- `SocialLoginRequest`
- `SocialLoginResponse`
- `FirebaseExchangeResponse`

Mapped endpoints:

- `POST /api/v1/auth/social/prepare`
- `POST /api/v1/auth/social`
- `POST /api/v1/auth/firebase/exchange`

## Source Of Truth Rule

When frontend and backend need the same request or response shape:

1. Start in `packages/shared-contracts/src/`.
2. Mirror the backend response model in `backend/services/api/src/polio_api/schemas/`.
3. Update frontend consumers to import from the shared contract package instead of redefining local interfaces.

Do not create new DTO copies inside feature pages unless the type is purely view-local and never crosses the API boundary.

## Backend Mirror Rule

Python cannot import the TypeScript contract files directly in the current repo setup, so the backend mirror schemas are the runtime enforcement layer. They must stay structurally aligned with `packages/shared-contracts/src/`.

For v1, the key backend mirrors are:

- `backend/services/api/src/polio_api/schemas/user.py`
- `backend/services/api/src/polio_api/schemas/blueprint.py`
- `backend/services/api/src/polio_api/schemas/inquiry.py`
- `backend/services/api/src/polio_api/schemas/diagnosis.py`

## Guardrail Note

These contracts exist to stabilize grounded product flows, not to widen claims. They should continue to support:

- evidence-backed diagnosis
- explicit uncertainty
- real student record grounding
- no fabricated activity
- no guaranteed outcome framing

## Next Contracts To Expand

After this v1 surface is stable, the next highest-value shared contracts are:

- project create/read and upload responses
- parsed document summaries and chunks
- workshop state and message/tool responses
- render job DTOs
- export and provenance block shapes
