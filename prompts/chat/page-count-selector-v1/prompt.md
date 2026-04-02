# chat.page-count-selector

- Version: `1.0.0`
- Category: `chat`
- Status: `wired-shared-fragment`

## Purpose

Choose page-count options that match the real amount of evidence, the output
format, and the complexity of the recommended direction.

## Input Contract

- Direction complexity
- Evidence density and diagnosis context
- Output format options

## Output Contract

Use this prompt as a guidance fragment for generating `page_count_options`.

Each option should include:

- `id`
- `label`
- `page_count`
- `rationale`

## Forbidden

- Inflating length to hide weak evidence
- Long page counts for thin records with little grounded support
- One-size-fits-all page recommendations

## Uncertainty Handling

- If evidence is thin, recommend shorter outputs first
- If the direction is deeper and evidence is stronger, allow longer options
- Keep options narrow and finishable

## Evaluation Criteria

- Page-count options feel realistic for the student's current evidence
- Rationales explain why the length fits the task
- The range supports structured choice rather than open-ended guessing

## Change Log

- `1.0.0`: Added page-count selection rules for guided diagnosis orchestration.

## Prompt Body

When generating `page_count_options`:

- Adapt the number and size of options to the actual diagnosis complexity.
- Prefer shorter outputs when the record is still weak or the next step is about
  clarifying one narrow point.
- Allow longer outputs only when the direction needs a fuller evidence,
  method, comparison, or reflection arc.
- Do not use page count as fake sophistication.
- Each rationale should explain what that length makes possible and why going
  longer would be unnecessary or risky if the evidence is still thin.

Your page-count recommendations should help the student choose a truthful,
finishable output, not a more impressive-looking one.
