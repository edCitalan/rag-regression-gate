"""Generate a portable dashboard; optionally create genuine Evidently reports."""
import os
os.environ['DO_NOT_TRACK'] = '1'
import argparse
import html
import json
from pathlib import Path
from ci_gate import DATA, ROOT, run_gate

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidently', action='store_true')
    parser.add_argument('--predictions', type=Path, help='Add a candidate run')
    args = parser.parse_args()
    paths = [DATA/f'{name}_predictions.jsonl' for name in ('baseline','regressed','improved')]
    if args.predictions:
        paths.append(args.predictions)
    runs = [run_gate(p) for p in paths]
    out = ROOT/'reports'; out.mkdir(exist_ok=True)
    (ROOT/'dashboard.json').write_text(json.dumps(runs,indent=2),encoding='utf-8')
    links = {}
    if args.evidently:
        import pandas as pd
        from evidently import Report
        from evidently.metrics import MeanValue
        from evidently.tests import gte
        def frame(run):
            return pd.DataFrame([{'answer_accuracy':int(r['correct']),
                                  'retrieval_recall':int(r['supported']),
                                  'offline_judge_pass_rate':int(r['pass'])} for r in run['rows']])
        for i, run in enumerate(runs):
            report = Report([MeanValue(column=m, tests=[gte(v)]) for m,v in run['thresholds'].items()]
                            + [MeanValue(column='offline_judge_pass_rate')])
            snapshot = report.run(frame(run),frame(runs[0]))
            name = f'evidently-{i}.html'
            snapshot.save_html(str(out/name))
            (out/f'evidently-{i}.json').write_text(snapshot.json(),encoding='utf-8')
            links[i] = f'<p><a href="reports/{name}">Open Evidently report</a></p>'
    esc = html.escape
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RAG quality regression dashboard</title><style>body{font:16px system-ui;margin:40px auto;max-width:1100px;padding:0 20px;color:#172637;background:#f6f8fb}h1{font-size:32px}section{background:white;padding:24px;margin:24px 0;border:1px solid #ccd6e0;border-radius:10px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #dae1e8}th{background:#eef3f8}.PASS{color:#126432}.FAIL{color:#b12525}small{color:#46566a}code{overflow-wrap:anywhere}</style><h1>RAG quality regression dashboard</h1><p>Fixture comparison — these are supplied scenarios, not chronological production runs.</p><p>Blocking thresholds: answer accuracy and retrieval recall ≥ 15/18 (83.33%). Judge: deterministic offline rubric v1; no AI model or API calls. Exact match and judge pass rate are diagnostic.</p>']
    for i, run in enumerate(runs):
        parts.append(f'<section><h2>{esc(run["source"])} · <span class="{run["status"]}">{run["status"]}</span></h2>')
        parts.append('<table><tr><th>Metric</th><th>Result</th><th>Baseline</th><th>Change</th></tr>')
        for metric, score in run['metrics'].items():
            base = runs[0]['metrics'][metric]
            parts.append(f'<tr><td>{metric}</td><td>{round(score*run["count"])}/{run["count"]} ({score:.2%})</td><td>{base:.2%}</td><td>{(score-base)*100:+.2f} pp</td></tr>')
        parts.append('</table>'+links.get(i,''))
        parts.append('<h3>Category accuracy</h3><p>'+ ' · '.join(f'{cat}: {sum(r["correct"] for r in run["rows"] if r["category"]==cat)}/{sum(r["category"]==cat for r in run["rows"])}' for cat in ('price','refund','latency','feature'))+'</p>')
        parts.append('<h3>Remaining failures</h3><table><tr><th>Question</th><th>Answer → expected</th><th>Reason</th></tr>')
        for row in run['rows']:
            if not row['pass']:
                parts.append(f'<tr><td>{esc(row["question"])}</td><td>{esc(row["answer"])} → {esc(row["expected"])}</td><td>{esc(row["reason"])}</td></tr>')
        parts.append('</table><h3>Changes from baseline</h3><p>')
        changes = [f'{r["question_id"]}: {"fixed" if r["pass"] else "regressed"}' for r,b in zip(run['rows'],runs[0]['rows']) if r['pass'] != b['pass']]
        parts.append(esc('; '.join(changes) or 'No pass/fail changes')+'</p></section>')
    parts.append('<small>18 questions: one answer changes accuracy by 5.56 percentage points. Passing the baseline does not mean all answers are correct. Rubric accepts a finite set of documented forms; it is not a semantic LLM judge.</small></html>')
    (ROOT/'dashboard.html').write_text(''.join(parts),encoding='utf-8')
    print('Wrote',ROOT/'dashboard.html')

if __name__ == '__main__':
    main()


