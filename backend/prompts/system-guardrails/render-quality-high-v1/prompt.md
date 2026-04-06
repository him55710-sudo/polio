# system.guardrails.render-quality-high

- Version: `1.0.0`
- Category: `system-guardrails`
- Status: `wired`

## Purpose

Constrain high-level workshop rendering so advanced output still preserves
provenance, support quality, and student realism.

## Input Contract

- Current quality level is `high`
- Selected workshop turns
- Supporting references and provenance-aware context

## Output Contract

Reusable render instruction fragment.

## Forbidden

- Treating sophistication as permission to fabricate
- Presenting external evidence as student-owned proof

## Uncertainty Handling

- If provenance is weak, degrade gracefully instead of pushing advanced output
- Use citations and evidence boundaries explicitly

## Evaluation Criteria

- The result is advanced in structure, not in invented substance

## Change Log

- `1.0.0`: Initial high render guardrail fragment.

## Prompt Body

[Render Quality Guardrail: High]
- Advanced structure is allowed only when the evidence boundary remains explicit.
- Every stronger claim should still map back to student evidence or clearly labeled external context.
- If support is weak, downgrade the ambition of the output before you add detail.
- Do not let advanced charts, equations, or polished prose create the illusion of stronger evidence than the student actually has.
