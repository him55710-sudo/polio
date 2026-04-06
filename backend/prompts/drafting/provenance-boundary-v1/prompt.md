# drafting.provenance-boundary

- Version: `1.0.0`
- Category: `drafting`
- Status: `scaffold-only`

## Purpose

Enforce the evidence boundary between student-authored reality and external
research while preparing draft blocks or report artifacts.

## Input Contract

- Evidence snippets labeled with provenance such as `STUDENT_RECORD` or
`EXTERNAL_RESEARCH`
- Drafting intent or target report section
- Optional citations or evidence map slots

## Output Contract

This asset is a reusable instruction fragment. It does not define a standalone
JSON schema.

## Forbidden

- Turning external research into student action or achievement
- Blending provenance types so the final text sounds more personal than the
evidence allows
- Citing decorative or weak evidence as if it materially supports the claim

## Uncertainty Handling

- If a claim lacks `STUDENT_RECORD` support, mark it as unsupported for
student-specific writing
- If external evidence is only contextual, label it as context or rationale
- Drop weak visuals or claims instead of forcing them into the draft

## Evaluation Criteria

- Provenance remains explicit
- Student claims stay tied to student evidence
- External context stays visibly external
- Unsupported blocks are blocked or rewritten safely

## Change Log

- `1.0.0`: Initial provenance boundary fragment for report and block generation.

## Prompt Body

Maintain the provenance boundary at all times.

- `STUDENT_RECORD` may support statements about the student's actions,
experiences, observations, outcomes, and reflections.
- `EXTERNAL_RESEARCH` may support framing, comparison, trend explanation,
selection rationale, or recommendation logic.
- Never rewrite `EXTERNAL_RESEARCH` as if the student personally performed it.
- If a section would require unsupported student evidence, either keep it
tentative, convert it into a question, or leave it out.
- If a visual, equation, or chart is not genuinely supported, drop it instead of
padding the output.
