# Real AI judge: implementation and operation log

## Status

Implemented optional live OpenAI API integration. No real model judgment has been executed yet. Tests use mocked API responses and validate the client, not the model's judgment quality. Required GitHub CI stays offline and never calls this API automatically.

## Put your key here

Local file: `C:\Users\edwar\rag-regression-gate\.env`.

```dotenv
OPENAI_API_KEY=your-key-goes-here
OPENAI_JUDGE_MODEL=gpt-4.1-mini-2025-04-14
```

The blank local file has been created. `.env.example` is the public template. `.env` and `live-runs/` are excluded from Git. Both are outside `submission/`, the folder served by the dashboard preview. Do not move the key into HTML, source files, a public GitHub secret substitute, or chat. Environment variables take precedence over the file. This is a small parser, not a shell: no substitution, export commands, or inline comments. No dotenv dependency is required.

## Try one answer

Run from the repository root:

```powershell
# Free preview: prepares the exact request but never contacts OpenAI.
.\.venv\Scripts\python.exe submission\ai_judge.py

# One paid API request after saving the key:
.\.venv\Scripts\python.exe submission\ai_judge.py --live

# Judge the improved fixture's known incorrect Enterprise-price answer:
.\.venv\Scripts\python.exe submission\ai_judge.py --live --question-id q-price-3

# Explicitly judge all 18 answers:
.\.venv\Scripts\python.exe submission\ai_judge.py --live --limit 18
```

A normal Python 3.10+ installation also works; substitute `python` for the venv executable. No additional packages are needed. Default predictions are the improved fixture, first question `q-price-0`. `--predictions path` accepts another complete fixture. `--question-id` chooses a particular row; full input validation still applies. Each selected row is one request; no automatic retries. The default limit is one, maximum 18.

## API implementation

This is an API client, not a newly hosted API server. `submission/ai_judge.py` sends HTTPS POST requests using Python `urllib` to the fixed endpoint `https://api.openai.com/v1/responses`. Authorization is `Bearer OPENAI_API_KEY`; the key is never included in the request body or audit output. Redirects are refused. Timeout is 60 seconds per request.

Default model: `gpt-4.1-mini-2025-04-14`, a pinned snapshot selected for this bounded demonstration, not a claim of best available judge quality. Change `OPENAI_JUDGE_MODEL` to use another compatible model. This implementation sends temperature=0, max_output_tokens=600, store=false, and a strict Structured Outputs JSON schema. A replacement model must support these parameters; there is no silent fallback. Temperature zero and a pinned snapshot do not guarantee identical judgments across runs.

`make_payload()` builds the request. `post()` sends it. `parse_response()` validates the result. `main()` controls previews/live calls, selection, and audit persistence. `RUBRIC` and `SCHEMA` are visible constants in the source. Rubric version is `semantic-judge-v1`.

## What data leaves your computer

For each selected row: the question, candidate answer, expected answer, full gold evidence document, retrieved documents (IDs, titles, text), and evaluation rubric are sent to OpenAI. No complete repository upload occurs. `store=false` is requested; it is not a claim of zero retention under all provider policies. Run only on data you intend to send to that provider.

The candidate and documents are serialized into the user input as data. The rubric is sent separately as instructions. The rubric tells the model to ignore instructions embedded in answers/documents. This is a mitigation, not proof of immunity to prompt injection. No tools or browsing are provided to the judge.

## Judgment rubric and schema

The model determines semantic correctness against the gold evidence, allowing paraphrases; it rejects wrong values, units, scope, contradictions, unsupported additional facts, and abstention on answerable questions. Feature questions require the minimum eligible plan.

Separately, it checks whether the retrieved text supports the answer's substantive claims. This semantic `grounded` check differs from the offline evaluator's document-presence check.

Required model output:

```json
{
  "question_id": "q-price-0",
  "correct": true,
  "grounded": true,
  "reason": "The answer states $19 per month, supported by the Starter plan document."
}
```

This JSON is an illustrative schema example, not a recorded live result. The client derives `pass = correct AND grounded`; it does not ask the model to determine the build outcome. Explanations are concise justifications, not hidden chain-of-thought.

Incomplete responses, refusals, malformed JSON, incorrect field types, wrong question IDs, extra fields, and missing explanations are errors. HTTP failure bodies are not printed. No fallback to deterministic grading is presented as a model result. A successfully completed diagnostic run returns exit 0 even if answers are judged incorrect; operational/validation errors return 2. The offline `ci_gate.py` remains responsible for build pass/fail.

## Tracking each run

`live-runs/<unique-run-id>/audit.json` records UTC start time, mode, model requested, endpoint, rubric version, input-file SHA-256, exact request body including rubric/schema, full API response, provider request ID, usage, model judgment, and offline judgment for comparison. `summary.md` gives a readable result. Dry runs explicitly contain no completed model judgment. On failure, completed earlier rows and the error are saved; the run is not reported as successful. Keys/authorization headers are not saved. Requests and responses contain evaluated content, so these logs stay local by default.

Use `usage.input_tokens`, `usage.input_tokens_details.cached_tokens`, and `usage.output_tokens` from the returned response to track consumption. Look up rates for the actual returned model before calculating cost; this implementation does not invent a cost estimate or enforce a dollar budget. A timeout may still be billed, which is why it does not automatically retry.

## Tests and limits

`test_ai_judge.py` covers request separation, strict format, response validation, refusals/incomplete responses, env precedence, no-network preview, missing-key failure, and a mocked live round trip with audit redaction. These tests run in the existing offline CI alongside deterministic and adversarial checks. They do not validate real model accuracy; after the key is configured, inspect actual results and compare with reviewed examples before promoting this judge to a blocking metric.

The existing dashboard still presents offline fixture evaluations. Live outputs are in the per-run Markdown/JSON files; they are not represented as offline dashboard scores or fed into Evidently automatically.

## Official references

- Structured Outputs and Responses request shape: https://developers.openai.com/api/docs/guides/structured-outputs
- Default model and snapshot: https://developers.openai.com/api/docs/models/gpt-4.1-mini

## Change record

- Added real, optional Responses API judge and explicit paid-call switch.
- Added blank local environment file, public template, and ignore rules.
- Added audit logs, semantic rubric/schema, and client contract tests.
- No API key supplied, no live model results claimed, and no automatic paid CI job enabled.
