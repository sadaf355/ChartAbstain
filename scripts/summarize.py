"""Score every runs/preds/*_preds.jsonl and write the comparison table to runs/results.md and runs/results.csv.

    python scripts/summarize.py

Name each predictions file <run>_preds.jsonl (for example A0_preds.jsonl, base_qwen3-4b_preds.jsonl).
"strict" needs the Answer/Reason/Type lines; "content only" forgives a missing label (see score.py).
"""
import csv
import glob
import os

from common import NL, repo_path
from score import acc, evaluate

COLUMNS = ['run', 'strict_all', 'strict_test', 'strict_hard', 'abstain_recall', 'over_abstain',
           'format_valid', 'type_label', 'content_only_all', 'content_only_abstain_recall', 'rows']


def main():
    files = glob.glob(repo_path('runs', 'preds', '*_preds.jsonl'))
    files.sort(key=lambda f: (not os.path.basename(f).startswith('base'), os.path.basename(f)))
    rows = []
    for f in files:
        s, len_ = evaluate(f), evaluate(f, lenient=True)
        rows.append({'run': os.path.basename(f)[:-len('_preds.jsonl')],
                     'strict_all': acc(s), 'strict_test': acc(s, 'slice=test'), 'strict_hard': acc(s, 'slice=hard'),
                     'abstain_recall': s['abstain_recall'], 'over_abstain': s['over_abstain'],
                     'format_valid': s['format_valid'], 'type_label': s['type_label'],
                     'content_only_all': acc(len_), 'content_only_abstain_recall': len_['abstain_recall'],
                     'rows': s['n']})
    with open(repo_path('runs', 'results.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    head = ['run', 'strict all', 'strict test', 'strict hard', 'abstain recall', 'over-abstain',
            'format valid', 'type label', 'content-only all', 'content-only abstain recall']
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    for r in rows:
        lines.append('| ' + r['run'] + ' | ' + ' | '.join(f'{r[k]:.1%}' for k in COLUMNS[1:-1]) + ' |')
    table = NL.join(lines)
    with open(repo_path('runs', 'results.md'), 'w', encoding='utf-8') as fh:
        fh.write(table + NL)
    print(table)


if __name__ == '__main__':
    main()
