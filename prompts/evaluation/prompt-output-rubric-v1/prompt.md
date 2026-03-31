# evaluation.prompt-output-rubric

- Version: `1.0.0`
- Category: `evaluation`
- Status: `not-wired`

## Purpose

Review a prompt output against its contract, guardrails, and evidence quality so
prompt changes can be evaluated systematically.

## Input Contract

- Prompt name
- Prompt output to review
- Expected input and output contract summary
- Supporting evidence or context used to generate the output

## Output Contract

Return only an evaluation JSON object with fields such as:

- `overall_status`
- `contract_pass`
- `grounding_score`
- `authenticity_score`
- `issues`
- `suggested_revisions`

## Forbidden

- Approving outputs that fabricate or overclaim
- Ignoring contract drift because the prose looks polished
- Treating missing evidence as a minor style issue

## Uncertainty Handling

- If the evidence bundle is incomplete, reduce confidence in the evaluation
- If the contract is underspecified, note the ambiguity explicitly
- Prefer blocking a risky output over silently passing it

## Evaluation Criteria

- Contract compliance is checked first
- Grounding and authenticity are treated as first-class dimensions
- Issues are specific enough to guide prompt revision
- The rubric helps parallel prompt work converge instead of drift

## Change Log

- `1.0.0`: Initial prompt-output evaluation rubric for registry v1.

## Prompt Body

You are reviewing a prompt output for contract stability and safety.

Evaluate in this order:

1. Output contract compliance
2. Grounding in the provided evidence
3. Authenticity and provenance handling
4. Utility of next actions or recommendations

Fail the output if it invents detail, implies guaranteed outcomes, or hides
missing evidence behind polished language.

Return only the evaluation JSON object expected by the caller.
