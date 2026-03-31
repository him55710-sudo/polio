# Polio Evaluation Harness v1

The Evaluation Harness is a structured framework for measuring the quality of Polio's AI outputs.

## Core Evaluation Axes

- **Groundedness**: Is the response anchored in student records and official evidence?
- **Actionability**: Does the response provide a clear, concrete next step?
- **Safety**: Does the response follow product guardrails (no exaggeration, no admission promises)?
- **Usefulness**: Does the response actually help the student move forward?

## Directory Structure

- `cases/`: YAML files containing student scenarios and expected behaviors.
- `rubrics/`: Scoring definitions and criteria.
- `fixtures/`: Mock data or static resources used during evaluation.
- `runner/`: Scripts to execute the evaluation flow.
- `results/`: Output of evaluation runs (JSON/HTML).

## Getting Started

1. Add cases to `eval/cases/`.
2. Ensure `eval/rubrics/v1.yaml` matches your requirements.
3. The runner now reads the canonical judge asset from `prompts/registry.v1.json`
   using `evaluation.prompt-output-rubric`.
4. Run the mock runner:
   ```powershell
   python eval/runner/eval_runner.py
   ```

## Notes

- `POLIO_EVAL_MOCK_MODE=good` keeps the mock generator grounded by default.
- `POLIO_EVAL_MOCK_MODE=bad` intentionally emits a failing sample so the judge
  path can be inspected.
