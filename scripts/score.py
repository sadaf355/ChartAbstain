"""Score a predictions file against the private answer key.

    python scripts/score.py runs/preds/A0_preds.jsonl                        # strict scoring
    python scripts/score.py runs/preds/base_qwen3-4b_preds.jsonl --lenient   # content only, label not required
    python scripts/score.py preds.jsonl --raw                                # do not trim junk after the Type label

Strict: the answer must sit on an "Answer:" line, as the system prompt demands.
Lenient: the first "Answer:" in the text is used and a missing label is forgiven, so it measures what the
model knows rather than whether it follows the format.
"""
import argparse
import collections

from common import NL, check, clean_output, lenient_output, read_jsonl, repo_path, type_ok


def evaluate(pred_path, key_path=None, lenient=False, raw=False):
    keys = {k['id']: k for k in read_jsonl(key_path or repo_path('data', 'answer_key.jsonl'))}
    groups = collections.defaultdict(lambda: [0, 0])
    ab_hit = ab_n = over = non_ab = fmt_ok = type_hit = n = 0
    fails = []
    for p in read_jsonl(pred_path):
        k = keys[p['id']]
        out = p['output']
        if not raw:
            out = clean_output(out)
        if lenient:
            out = lenient_output(out)
        ok, ab, fmt = check(k, out)
        n += 1
        fmt_ok += fmt
        type_hit += type_ok(k, out)
        for g in ('ALL', 'slice=' + k['slice'], 'type=' + k['qtype']):
            groups[g][0] += ok
            groups[g][1] += 1
        if k['kind'] == 'abstain':
            ab_n += 1
            ab_hit += ab
        else:
            non_ab += 1
            over += ab
        if not ok:
            fails.append((p['id'], k['qtype'], out.replace(NL, ' | ')[:110]))
    return {'n': n, 'groups': {g: tuple(v) for g, v in groups.items()},
            'abstain_recall': ab_hit / max(ab_n, 1), 'over_abstain': over / max(non_ab, 1),
            'format_valid': fmt_ok / max(n, 1), 'type_label': type_hit / max(n, 1), 'fails': fails}


def acc(res, group='ALL'):
    c, t = res['groups'].get(group, (0, 0))
    return c / t if t else float('nan')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('preds')
    ap.add_argument('--lenient', action='store_true')
    ap.add_argument('--raw', action='store_true')
    ap.add_argument('--show', type=int, default=15, help='number of failures to print')
    a = ap.parse_args()
    res = evaluate(a.preds, lenient=a.lenient, raw=a.raw)
    for g in sorted(res['groups']):
        c, t = res['groups'][g]
        print(f'{g:<16} {c / t:6.1%}  ({c}/{t})')
    print(f"abstention recall    {res['abstain_recall']:.1%}")
    print(f"over-abstention rate {res['over_abstain']:.1%}")
    print(f"format valid         {res['format_valid']:.1%}")
    print(f"type label correct   {res['type_label']:.1%}")
    for item in res['fails'][:a.show]:
        print('FAIL', *item)


if __name__ == '__main__':
    main()
