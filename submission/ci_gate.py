"""Offline regression gate. No model calls; rubric judge is deterministic v1."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
METRICS = ('answer_accuracy', 'retrieval_recall')


def records(path, key):
    result = {}
    for number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(f'{path}:{number}: invalid {key}')
        if row[key] in result:
            raise ValueError(f'{path}:{number}: duplicate {key}: {row[key]}')
        result[row[key]] = row
    if not result:
        raise ValueError(f'{path}: empty dataset')
    return result


def normalize(text):
    return re.sub(r'\s+', ' ', text.casefold().strip()).rstrip('.')


def load_reference():
    corpus = records(DATA / 'corpus.jsonl', 'doc_id')
    questions = records(DATA / 'questions.jsonl', 'question_id')
    key = records(DATA / 'answer_key.jsonl', 'question_id')
    if set(key) != set(questions):
        raise ValueError('Answer key and questions must have identical IDs')
    for qid, entry in key.items():
        doc = corpus.get(entry['doc_id'])
        if not doc or entry['evidence'] not in doc['text']:
            raise ValueError(f'{qid}: answer-key evidence does not match corpus')
    return corpus, questions, key


def judge(answer, reference, retrieved):
    """Deterministic offline rubric, NOT an LLM. Conservative full-answer grammar.

    Accept only canonical values or bounded declarative paraphrases. Any extra
    text is rejected rather than trusting substring matches or instructions.
    Evidence support means the designated relevant document was retrieved; it
    is not a general semantic entailment assessment.
    """
    answer = normalize(answer)
    accepted = {normalize(x) for x in reference['accepted_answers']}
    correct = answer in accepted
    supported = reference['doc_id'] in retrieved
    reasons = []
    if not correct:
        reasons.append('Answer is outside the documented accepted-answer rubric')
    if not supported:
        reasons.append('Required supporting document was not retrieved')
    return {'correct': correct, 'supported': supported,
            'pass': correct and supported,
            'reason': '; '.join(reasons) or 'Accepted answer with supporting evidence'}


def evaluate(path):
    corpus, questions, key = load_reference()
    predictions = records(path, 'question_id')
    if set(predictions) != set(questions):
        raise ValueError(f'Question coverage mismatch; missing={sorted(set(questions)-set(predictions))}; extra={sorted(set(predictions)-set(questions))}')
    rows = []
    for qid, ref in key.items():
        pred = predictions[qid]
        answer = pred.get('answer')
        docs = pred.get('retrieved_doc_ids')
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f'{qid}: answer must be a nonempty string')
        if not isinstance(docs, list) or any(not isinstance(d, str) for d in docs):
            raise ValueError(f'{qid}: retrieved_doc_ids must be a list of strings')
        if len(set(docs)) != len(docs) or any(d not in corpus for d in docs):
            raise ValueError(f'{qid}: duplicate or unknown document IDs')
        judgment = judge(answer, ref, docs)
        rows.append({'question_id': qid, 'question': questions[qid]['question'],
                     'category': ref['category'], 'answer': answer,
                     'expected': ref['canonical'], 'evidence': ref['evidence'],
                     'expected_doc_id': ref['doc_id'], 'retrieved_doc_ids': docs,
                     'exact_match': normalize(answer) == normalize(ref['canonical']),
                     **judgment})
    count = len(rows)
    metrics = {'answer_accuracy': sum(r['correct'] for r in rows)/count,
               'retrieval_recall': sum(r['supported'] for r in rows)/count,
               'exact_match': sum(r['exact_match'] for r in rows)/count,
               'offline_judge_pass_rate': sum(r['pass'] for r in rows)/count}
    return {'count': count, 'metrics': metrics, 'rows': rows}


def run_gate(path):
    snapshot = json.loads((DATA / 'baseline_metrics.json').read_text(encoding='utf-8-sig'))
    baseline = evaluate(DATA / 'baseline_predictions.jsonl')
    for metric in METRICS:
        value = snapshot.get(metric)
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise ValueError(f'Invalid baseline metric: {metric}')
        if abs(baseline['metrics'][metric] - value) > 0.0005:
            raise ValueError(f'Baseline snapshot does not match recomputed {metric}')
    candidate = evaluate(path)
    thresholds = {m: baseline['metrics'][m] for m in METRICS}
    failures = [m for m in METRICS if candidate['metrics'][m] < thresholds[m]]
    return {**candidate, 'status': 'FAIL' if failures else 'PASS',
            'source': Path(path).name, 'thresholds': thresholds, 'failures': failures,
            'judge_type': 'deterministic_offline_rubric_v1',
            'baseline_rounding': 'Snapshot validated to half of 0.001; exact recomputed baseline used for decisions'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='Optional machine-readable JSON result')
    args = parser.parse_args(argv)
    try:
        result = run_gate(args.predictions)
        code = 1 if result['failures'] else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result = {'status': 'ERROR', 'error': str(exc)}
        code = 2
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
        except OSError as exc:
            print(f'Cannot write report: {exc}', file=sys.stderr)
            return 2
    return code


if __name__ == '__main__':
    sys.exit(main())
