"""Pick 6 demo examples (one per question type) and write demo/examples.json.

    python scripts/make_demo_examples.py --tuned A0diff_r16_4ep
    python scripts/make_demo_examples.py --tuned A2_strong --base base_qwen3-4b

Reads runs/preds/<name>_preds.jsonl. For each type it prefers a case the tuned model gets right and the
untuned model gets wrong, so the demo shows a real difference. Types: abstain, axis, unit, pct, max, trend.
"""
import argparse
import json
import os

from common import check, clean_output, read_jsonl, repo_path

ap = argparse.ArgumentParser()
ap.add_argument('--tuned', required=True, help='run name, file runs/preds/<name>_preds.jsonl')
ap.add_argument('--base', default='base_qwen3-4b')
ap.add_argument('--types', default='abstain,axis,unit,pct,max,trend')
a = ap.parse_args()

keys = {k['id']: k for k in read_jsonl(repo_path('data', 'answer_key.jsonl'))}
inputs = {r['id']: r['input'] for r in read_jsonl(repo_path('data', 'eval.jsonl'))}


def load(name):
    return {p['id']: clean_output(p['output']) for p in read_jsonl(repo_path('runs', 'preds', name + '_preds.jsonl'))}


base, tuned = load(a.base), load(a.tuned)

examples = []
for qt in a.types.split(','):
    ids = sorted(i for i, k in keys.items() if k['qtype'] == qt and i in tuned and i in base)
    good = [i for i in ids if check(keys[i], tuned[i])[0]]
    best = [i for i in good if not check(keys[i], base[i])[0]] or good
    if not best:
        print('no good example for', qt)
        continue
    i = best[0]
    head, question = inputs[i].split('\nQuestion: ', 1)
    chart = head.split('\n', 1)[1]  # drop the "Ref:" line
    examples.append({'id': i, 'type': qt, 'chart': chart, 'question': question,
                     'untuned': base[i][:400], 'tuned': tuned[i],
                     'untuned_correct': bool(check(keys[i], base[i])[0])})

out = repo_path('demo', 'examples.json')
with open(out, 'w', encoding='utf-8') as fh:
    json.dump({'untuned_model': a.base, 'tuned_model': a.tuned, 'examples': examples}, fh, indent=1, ensure_ascii=False)
print('wrote', len(examples), 'examples to', out)
