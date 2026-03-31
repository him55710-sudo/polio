# system.guardrails.render-quality-low

- Version: `1.0.0`
- Category: `system-guardrails`
- Status: `wired`

## Purpose

Constrain low-level workshop rendering so the output stays finishable,
evidence-first, and realistic for the student's current context.

## Input Contract

- Current quality level is `low`
- Selected workshop turns
- Optional supporting references

## Output Contract

Reusable render instruction fragment.

## Forbidden

- Expanding beyond directly supportable student evidence
- Polishing weak context into a confident conclusion

## Uncertainty Handling

- Convert weak support into a verification note or next action
- Prefer narrow, finishable wording over ambitious framing

## Evaluation Criteria

- The result stays concrete, safe, and class-level realistic

## Change Log

- `1.0.0`: Initial low render guardrail fragment.

## Prompt Body

[Render Quality Guardrail: Low]
- Stay tightly anchored to the student's actual record and directly supportable actions.
- Do not introduce experiments, measurements, interviews, or outcomes that are not already evidenced.
- Prefer short, finishable, classroom-realistic wording over polished ambition.
- If support is thin, say additional verification is needed instead of smoothing the gap away.
