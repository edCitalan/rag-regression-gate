"""Generate the explicit, corpus-backed reference artifact. Review changes to it."""
import json
from ci_gate import DATA, records

corpus = records(DATA / 'corpus.jsonl', 'doc_id')
rows = []
def add(qid, category, doc, value, variants):
    rows.append(dict(question_id=qid, category=category, doc_id=doc,
                     canonical=value, accepted_answers=[value, *variants],
                     evidence=corpus[doc]['text']))

for i, (plan, price, days) in enumerate([('Starter',19,7),('Team',49,14),('Business',99,30),('Enterprise',299,60)]):
    doc = 'plan-' + plan.lower()
    add(f'q-price-{i}', 'price', doc, f'${price} per month',
        [f'The {plan} plan costs ${price} per month', f'${price}/month', f'{price} USD per month'])
    add(f'q-refund-{i}', 'refund', doc, f'{days} days',
        [f'Within {days} days of purchase', f'The refund window is {days} days',
         f'Refunds are available within {days} days of purchase'])
for i, (region, ms) in enumerate([('us-east',20),('us-west',28),('eu-central',36),('ap-southeast',44)]):
    add(f'q-latency-{i}', 'latency', 'region-' + region, f'about {ms} ms',
        [f'{ms} ms', f'Approximately {ms} milliseconds', f'Typical API latency is about {ms} ms'])
for i, (feature, plan) in enumerate([('SSO','Team'),('audit-logs','Team'),('custom-roles','Business'),('API','Business'),('webhooks','Enterprise'),('data-export','Enterprise')]):
    add(f'q-feature-{i}', 'feature', 'feature-' + feature, f'the {plan} plan',
        [plan, f'{plan} plan', f'{plan} and above', f'The {plan} plan and above', f'Available starting on the {plan} plan'])
(DATA / 'answer_key.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
