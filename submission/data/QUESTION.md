# The task

Build a **CI regression gate** for a RAG system (the one from task 6.1, or any
RAG over the bundled `corpus.jsonl` / `questions.jsonl`). Everything needed is
provided — no external data.

You are given three sets of results over the same questions (whose answers are known), plus a baseline:

- `baseline_predictions.jsonl` — last known-good (~0.83 accuracy)
- `regressed_predictions.jsonl` — a real regression (~0.56)
- `improved_predictions.jsonl` — a real improvement (~0.94)
- `baseline_metrics.json` — the baseline snapshot to compare against

## Build

1. `submission/ci_gate.py` — invoked as `python ci_gate.py --predictions <file>`.
   It must **exit nonzero when quality has regressed** vs the baseline, and **exit
   zero otherwise**. (The grader runs it on the regressed and improved fixtures.)
2. A regression **test suite** with all three categories: at least one
   **deterministic** check, at least one **LLM-as-judge** check, and at least one
   **adversarial** case.
3. A **dashboard** (`submission/dashboard.{md,html,png,json}`) showing quality over runs.
4. Wire the gate into CI (a GitHub Actions workflow or equivalent) that fails the build on regression.

## Grading (deterministic)

An automated grader runs your `ci_gate.py` on the regressed fixture (expects CI fail)
and the improved fixture (expects CI pass), and scans the suite for the three
required categories.
