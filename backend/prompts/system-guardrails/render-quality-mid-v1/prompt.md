# system.guardrails.render-quality-mid

- Version: `1.0.0`
- Category: `system-guardrails`
- Status: `wired`

## Purpose

Constrain mid-level workshop rendering so the output can extend the student's
context a little while remaining grounded and safe.

## Input Contract

- Current quality level is `mid`
- Selected workshop turns
- Optional supporting references

## Output Contract

Reusable render instruction fragment.

## Forbidden

- Turning light extension into unsupported certainty
- Merging student actions with external context

## Uncertainty Handling

- Keep conjecture labeled as a next step, not an accomplished fact
- Use references only as supporting context

## Evaluation Criteria

- The result extends the student's evidence without overclaiming

## Change Log

- `1.0.0`: Initial mid render guardrail fragment.

## Prompt Body

[Render Quality Guardrail: Mid]
- You may extend the framing slightly, but only within what a high school student could plausibly explain and support.
- Keep conclusions specific, evidence-aware, and reversible if more context arrives.
- Separate student actions from interpretation and external context.
- If evidence is partial, keep the output in a grounded draft state rather than presenting it as settled.
