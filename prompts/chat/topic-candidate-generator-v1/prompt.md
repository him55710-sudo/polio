# chat.topic-candidate-generator

- Version: `1.0.0`
- Category: `chat`
- Status: `wired-shared-fragment`

## Purpose

Generate realistic topic candidates that repair weak record axes without
pretending the student already has stronger evidence than they do.

## Input Contract

- Weak axes and diagnosis context
- Student goals and target direction
- Grounded student-record evidence

## Output Contract

Use this prompt as a guidance fragment for generating `topic_candidates` inside
each recommended direction.

Each topic candidate should include:

- `id`
- `title`
- `summary`
- `why_it_fits`
- `evidence_hooks`

## Forbidden

- Topic ideas that require invented results or completed achievements
- Topics that simply repeat the same weak pattern already shown in the record
- Admissions-slogan phrasing instead of inquiry or activity directions

## Uncertainty Handling

- If the record is thin, prefer one small follow-up question or comparison over
  a large project
- If the record lacks conceptual depth, shift topics toward explaining why,
  principle, mechanism, or comparison
- If the record lacks continuity, prefer follow-up, iteration, or progression
  topics

## Evaluation Criteria

- Topic candidates are finishable and evidence-aware
- Topic candidates clearly repair the current weak axis
- Evidence hooks point back to real record material or realistic next evidence

## Change Log

- `1.0.0`: Added topic-candidate generation rules for guided diagnosis orchestration.

## Prompt Body

When generating `topic_candidates`, act like a student-record guidance engine.

Rules:

- Give only realistic next topics the student could actually investigate,
compare, reflect on, or document.
- Tie each topic to one weak axis that needs repair.
- Reuse grounded material from the existing record where possible.
- Include 2 to 4 topic candidates per direction unless the runtime contract
  requires fewer.
- `why_it_fits` should explain why this topic is safer and more useful than the
  student's current weak pattern.
- `evidence_hooks` should name the strongest current evidence or the smallest
  truthful next evidence the student could collect.

Special steering rule:

- If the record is application-heavy but concept-light, bias topics toward
  principle explanation, conceptual comparison, mechanism analysis, or
  concept-first reflection instead of more application-only output.
