# Prompt Registry

This directory is the managed prompt asset registry for UniFoli v1.

It is intentionally organized by product purpose instead of by model provider or
ad hoc experiment name.

## Categories

- `diagnosis/`: prompts for fit analysis, evidence gaps, and next actions
- `chat/`: prompts for coaching-first conversation orchestration
- `drafting/`: prompts for grounded report generation and provenance handling
- `inquiry-support/`: prompts for safe inquiry triage and support workflows
- `evaluation/`: prompts and rubrics for prompt-output review
- `system-guardrails/`: reusable policy and authenticity constraints

## Asset Format

Each prompt asset is a `prompt.md` file with the same visible sections:

- `Purpose`
- `Input Contract`
- `Output Contract`
- `Forbidden`
- `Uncertainty Handling`
- `Evaluation Criteria`
- `Change Log`
- `Prompt Body`

The canonical machine-readable lookup lives in `registry.v1.json`.

The `Prompt Body` may be either:

- reusable instruction text
- a machine-readable JSON bundle consumed by backend runtime code

## Naming Rule

Prompt names use stable dotted identifiers, for example:

- `diagnosis.grounded-analysis`
- `chat.coaching-orchestration`
- `drafting.report-render`

## Runtime Rule

Runtime prompt loading belongs under `backend/`.

The current backend scaffold reads this directory through
`backend/services/api/src/unifoli_api/services/prompt_registry.py`.
This keeps prompt assets centralized while leaving runtime integration inside the
backend source of truth.
