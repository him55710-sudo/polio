# Prompts Package

This backend package is now a compatibility surface, not the primary prompt
registry.

## Canonical Rule

- Edit prompt assets in the root `prompts/` directory
- Load them at runtime from `backend/services/api/src/unifoli_api/services/prompt_registry.py`
- Keep backend-only glue code, adapters, or legacy migration notes here when needed

Prompts should still be versioned and reviewed like code, but new canonical
prompt content should not be added here first.
