# Evaluation Harness v1

The Evaluation Harness is Polio's internal system for measuring the core quality of our AI outputs. It ensures that as we iterate on the `DiagnosisEngine` and `ChatOrchestrator`, we maintain our commitment to groundedness, actionability, safety, and usefulness.

## What it Evaluates

1.  **Groundedness**: Prevents hallucinations. Every claim must be tied to a student's actual record or an official university criterion.
2.  **Actionability**: Ensures the student is never left "stuck." Every response should point to the next concrete action.
3.  **Safety**: Enforces product guardrails. No "admission guarantees," no "fabrication," and no "over-polishing."
4.  **Usefulness**: Measures the overall value and anxiety-reduction impact on the student.

## Why it Matters

High-stakes educational consulting requires trust. If the AI hallucinates success or invents activities, that trust is permanently broken. The harness provides the metrics we need to prevent regression.

## Data Requirements (Human-in-the-loop)

To make this harness effective, we need human-authored **cases** in `eval/cases/`.
Each case should include:
- `case_id`: Unique identifier (e.g., `STU-001-CS-INT-01`)
- `student_profile`: Anonymized student context (Grade, GPA, Achievements).
- `target_plan`: The student's goals (Universities, Majors).
- `uploaded_evidence_summary`: What records are actually available to the AI.
- `expected_good_behavior`: Specific things the AI *should* say or suggest.
- `disallowed_behavior`: Specific guardrails for this case.

## Future Automation Path

1.  **Diagnosis/Chat Integration**: Replace the `runner` placeholder with real calls to the backend APIs.
2.  **LLM-Judge**: Use a stronger model (e.g., Gemini 1.5 Pro) to act as a "judge" using the `rubrics/v1.yaml` criteria.
3.  **CI Registry**: Automatically run evaluations on every PR to `backend/`.
4.  **Dashboard**: Visualize results and score trends over time.

## Running the Harness

To run the current v1 scaffold:

```powershell
python eval/runner/eval_runner.py
```

This will produce a JSON file in `eval/results/` that can be reviewed for quality audits.
