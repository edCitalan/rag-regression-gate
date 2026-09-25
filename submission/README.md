# Offline RAG regression gate

Python 3.10+; tested with Python 3.13.5. Required gate, tests, CI entry point, and summary dashboard use the standard library only. No API keys, model downloads, network requests, or package installation are required for these commands.

From `submission/`:

```sh
python -S ci_gate.py --predictions data/regressed_predictions.jsonl --output reports/regressed.json
# exit 1: regression
python -S ci_gate.py --predictions data/improved_predictions.jsonl --output reports/improved.json
# exit 0: pass
python -S ci_gate.py --predictions data/baseline_predictions.jsonl
# exit 0: baseline equality passes
python -S -m unittest discover -v
python -S ci.py --predictions data/candidate_predictions.jsonl
```

Exit codes: 0 passes both blocking metrics, 1 quality regression, 2 invalid input/configuration or report write error. Paths to supplied predictions resolve from the caller's working directory; bundled reference paths resolve from the script directory.

## What is judged, and by whom?

No AI model is used. The system that produced the supplied predictions is unidentified. The explicitly labeled `deterministic_offline_rubric_v1` is the assignment-permitted **AI-as-judge substitute**, not a live LLM or semantic evaluator. Evidently is a reporting and metric-testing library, not the judge model.

`data/answer_key.jsonl` contains canonical answers, a finite list of accepted variants, relevant document IDs, and verbatim corpus evidence. The rubric uses case/whitespace normalization and removes trailing periods, then requires a full-answer match against those variants. It accepts the documented paraphrases and rejects all other forms, including extra instructions, contradictions, and wrong units. This conservative design may reject a valid but unlisted paraphrase. It does not claim general natural-language understanding or comprehensive prompt-injection detection.

`build_answer_key.py` records the manually selected facts and builds the reference artifact. Do not regenerate or update the key automatically from candidate predictions. Changes to ground truth, accepted forms, or thresholds require review. Evidence text is checked against the corpus on each evaluation; that check does not replace human review of the fact mapping.

## Metrics and gate policy

- `answer_accuracy`: share of all 18 answers accepted by the offline correctness rubric.
- `retrieval_recall`: share retrieving the one designated relevant document. Equivalent to mean recall with one gold document per question. Irrelevant additional documents are not penalized; this is not precision or ranking quality.
- `exact_match`: normalized match against canonical wording; diagnostic.
- `offline_judge_pass_rate`: accepted answer AND relevant evidence retrieved; diagnostic. Evidence presence is not a general entailment test.

Either blocking metric below baseline fails the gate. The supplied snapshot (0.833 each) is validated against the recomputed baseline within 0.0005, its rounding precision. Actual decisions use exact recomputed 15/18 thresholds. No regression tolerance is applied. An unchanged baseline passes.

All required question IDs must occur exactly once. Missing/extra/duplicate IDs, unknown or duplicate document references, empty data, malformed JSON, and invalid field types fail closed. Empty retrieval lists are valid but score zero. All questions remain in the denominator.

Expected fixtures: baseline 15/18 (83.33%), regressed 10/18 (55.56%), improved 17/18 (94.44%), for both blocking metrics. Improved still misses Enterprise pricing. These fixtures couple retrieval and answer failures; synthetic tests exercise independent failures. Eighteen questions are insufficient to establish broad production quality or statistical confidence. Category scores are diagnostic only.

## CI

`.github/workflows/quality.yml` runs the suite and gates `data/candidate_predictions.jsonl`. The initial candidate is an explicitly copied improved fixture for the demo. Replace that file with actual system outputs in your prediction-generation step; evaluating a permanently frozen example would not monitor your application.

`ci.py` is also a standalone offline CI equivalent. It propagates gate failures, runs tests, and writes a candidate JSON artifact even for invalid input. For valid inputs, it builds the summary dashboard even when the gate fails. The suite expects the regressed fixture to fail; that successful negative test does not itself fail CI. The separate candidate gate controls build status.

GitHub checkout and artifact transfer require GitHub connectivity. Evaluation commands themselves run offline with Python already installed and do not install dependencies. The workflow is supplied but has not been executed on GitHub. To enforce merge blocking, configure the `quality` job as a required status check in the target repository.

## Dashboard and Evidently

Open `dashboard.html` for all three fixture comparisons, counts, thresholds, metric changes, categories, failures, and changes from baseline. `dashboard.json` contains the underlying results. The runs are scenarios, not a fabricated production time series.

Genuine Evidently 0.7.23 HTML/JSON reports are included under `reports/evidently-*`. To regenerate them in a pre-provisioned environment:

```sh
python build_dashboard.py --evidently
```

For initial connected setup only, install `requirements-report.txt`. A resolved package inventory is provided in `requirements-report-lock.txt`; offline installations require packages/wheels provisioned ahead of time. Report dependencies are never required by the build gate. Telemetry is disabled before importing Evidently. No LLM descriptors, remote datasets, or cloud services are used. Evidently reports include mean scores and explicit baseline tests for the two blocking metrics.

Without Evidently, `python -S build_dashboard.py` regenerates the portable summary. Existing Evidently reports remain fixture snapshots and are not automatically updated by CI. The summary links to them only when generated with `--evidently`, avoiding stale candidate-report links.

Documentation consulted: https://docs.evidentlyai.com/introduction and https://evidentlyai.github.io/evidently/api-reference/main/evidently/core/report.html.

## Optional real AI judge

A separate API-based judge is now implemented. See [AI_JUDGE.md](AI_JUDGE.md) for the local .env setup, exact rubric, API contract, run commands, audit trail, and live-validation status. The required offline gate still uses no AI model.
