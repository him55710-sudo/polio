# chat.template-recommender

- Version: `1.0.0`
- Category: `chat`
- Status: `wired-shared-fragment`

## Purpose

Recommend document templates that match the selected direction, supported
formats, and authenticity needs without assuming major-specific export packs.

## Input Contract

- Allowed template ids and metadata from runtime
- Format recommendations for the current direction
- Diagnosis context and weak axes

## Output Contract

Use this prompt as a guidance fragment for generating:

- `template_candidates`
- `recommended_default_action.template_id`

Template recommendations must point only to runtime-provided template ids.

## Forbidden

- Inventing template ids
- Assuming major-specific export packs
- Recommending visually flashy output when the record should stay conservative
  and submission-friendly

## Uncertainty Handling

- Prefer conservative HWPX-friendly templates for submission-style outputs
- Prefer presentation templates only when progression, visual comparison, or
  concise storytelling is genuinely useful
- Prefer provenance-capable templates when the direction depends heavily on
  evidence review or comparison

## Evaluation Criteria

- Template choices match the format and document goal
- HWPX recommendations stay conservative and school-friendly
- The chosen default template clearly fits the diagnosis-driven direction

## Change Log

- `1.0.0`: Added template recommendation rules for guided diagnosis orchestration.

## Prompt Body

When generating `template_candidates`:

- Recommend only from the allowed template ids provided by runtime.
- Reuse the same logical template across PDF, PPTX, and HWPX where possible.
- Treat HWPX as a conservative, submission-friendly format.
- Match template style to the real document goal:
  - evidence-heavy report work should favor report or comparison templates
  - activity summaries should stay school-friendly and restrained
  - presentation templates should be used when the direction benefits from
    progression, visual emphasis, or concise structure
- `why_it_fits` should explain why the template helps the student express the
  next step truthfully.

For `recommended_default_action`:

- Choose one template id that already appears in the selected direction's
  `template_candidates`.
- Make sure the template id is compatible with the selected default format.
