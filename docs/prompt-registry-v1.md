# Prompt Registry V1

This document defines the first managed prompt asset registry for Polio.

## Why This Comes First

Prompt strings are currently scattered across backend runtime files.

That is workable for a single editor, but it creates prompt-shape drift when
multiple parallel changes land at the same time. The v1 registry fixes the
lookup surface first so future prompt edits can converge on stable names,
stable files, and explicit runtime ownership.

## Canonical Registry Surface

The v1 prompt registry is split across two places on purpose:

- Prompt assets live in `prompts/`
- Runtime loading scaffolding lives in `backend/services/api/src/polio_api/services/prompt_registry.py`

The root asset registry is the canonical place to edit prompt content.
Backend remains the canonical place to decide when and how a prompt is used at
runtime.

## Canonicalized Prompt Assets

The following prompt names are now reserved and documented:

| Prompt Name | Category | Intended Function | Current Wiring Status |
| --- | --- | --- | --- |
| `system.guardrails.admissions-authenticity` | `system-guardrails` | Shared authenticity and provenance policy | Wired through prompt dependencies |
| `system.guardrails.render-quality-low` | `system-guardrails` | Low-level render quality guardrail | Wired into workshop render runtime |
| `system.guardrails.render-quality-mid` | `system-guardrails` | Mid-level render quality guardrail | Wired into workshop render runtime |
| `system.guardrails.render-quality-high` | `system-guardrails` | High-level render quality guardrail | Wired into workshop render runtime |
| `system.guardrails.workshop-quality-profiles` | `system-guardrails` | Workshop quality profile data bundle | Wired into `quality_control.py` |
| `diagnosis.grounded-analysis` | `diagnosis` | Diagnosis result generation | Wired into diagnosis runtime |
| `chat.coaching-orchestration` | `chat` | Coaching-first draft chat | Wired into draft chat runtime |
| `chat.workshop-choice-copy` | `chat` | Workshop starter/follow-up/ack copy bundle | Wired into `quality_control.py` |
| `drafting.provenance-boundary` | `drafting` | Provenance separation rules | Wired as render system instruction fragment |
| `drafting.report-render` | `drafting` | Report artifact rendering | Wired into workshop render runtime |
| `inquiry-support.contact-triage` | `inquiry-support` | Inquiry triage and summarization | Wired into deterministic inquiry triage metadata |
| `evaluation.prompt-output-rubric` | `evaluation` | Prompt output review rubric | Wired into `eval/runner/eval_runner.py` |

## Current Backend Touchpoints

The registry is designed around the prompt-heavy backend files that currently
assemble inline strings:

- `backend/services/api/src/polio_api/services/diagnosis_service.py`
- `backend/services/api/src/polio_api/api/routes/drafts.py`
- `backend/services/api/src/polio_api/services/workshop_render_service.py`
- `backend/services/api/src/polio_api/services/quality_control.py`
- `backend/services/api/src/polio_api/services/rag_service.py`
- `backend/services/api/src/polio_api/services/inquiry_service.py`
- `eval/runner/eval_runner.py`

These files are still the active runtime behavior today, but the main inline
system prompts for diagnosis, draft chat, and workshop render now resolve
through the registry first. Inquiry triage now stores registry-aware
deterministic metadata, the eval runner now reads the canonical evaluation
judge asset directly, and workshop quality-level copy now resolves through
registry-owned JSON bundles instead of inline strings.

## Loader Scaffold

The v1 backend loader provides:

- named prompt lookup through `PromptRegistry.get_asset(...)`
- dependency composition through `PromptRegistry.compose_prompt(...)`
- environment-aware override paths through `PROMPT_ASSET_ROOT` and `PROMPT_REGISTRY_PATH`
- graceful missing-prompt errors through `PromptAssetNotFoundError`

This is intentionally minimal. It is safe to adopt incrementally file by file.

## What Is Not Wired Yet

The registry does not replace every prompt-shaped string yet.

The following prompt paths are still inline or partially duplicated:

- legacy prompt package material under `backend/packages/prompts/`
- some render-time JSON contract framing and repair-language overlays

The following are now partially wired but still conservative:

- inquiry triage uses the registry contract shape, but generation is still deterministic rather than LLM-backed
- eval judging reads the registry asset, but scoring is still heuristic rather than model-judged

## Backend Wiring Guidance

When a backend flow is migrated, the preferred pattern is:

1. Load the named asset with `get_prompt_registry()`
2. Compose the prompt with dependencies if needed
3. Keep request-time variables in backend code, not hardcoded into the asset
4. Keep runtime-specific schema classes in backend code
5. Raise or log `PromptAssetNotFoundError` clearly instead of silently falling
back to stale strings

## Next Contracts To Add

The next prompt assets worth formalizing are:

- diagnosis scoring rubric fragments
- workshop render repair and escalation fragments
- export-time provenance stripping instructions
- research-selection and citation-ranking prompts
- inquiry reply drafting prompts, if support automation becomes real

## Rule Of Thumb

If someone asks, "where do I edit the prompt text?" the answer is now
`prompts/`.

If someone asks, "where do I wire that prompt into runtime behavior?" the answer
is `backend/`.
