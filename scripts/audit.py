"""Audit Adaption's data-adaptation output against the private answer key, then build the repaired dataset.

    python scripts/audit.py                                 # reads data/adapted_raw.jsonl
    python scripts/audit.py --src path/to/adapted.jsonl

Every adapted row is matched to the answer key through its "Ref: A-xxxx" tag, and its enhanced completion
is checked with the same checker that scores the models. Output:
    runs/audit_report.md              counts, per-type error rates, damage categories, examples
    data/repaired.jsonl               input/output rows        (platform upload: repaired_messages.jsonl)
    data/repaired_messages.jsonl      chat-format rows, the dataset used for run A2

Repair rule: a row whose answer is wrong is replaced by the original row. A correct answer with a wrong Type
label keeps its text and only the Type line is rewritten (disable with --keep-bad-type-rows to restore the
original instead). Rows the platform dropped are restored from the original unless --no-restore-dropped.
"""
import argparse
import collections
import json
import os
import re

from common import NL, check, is_abstain, parse, read_jsonl, repo_path, to_messages, write_jsonl

REF = re.compile(r'A-[0-9]{4}')
UP = re.compile(r'\b(increase[ds]?|up|rise[ns]?|rose|grew|grow[ns]?|higher|gain(?:ed)?)\b', re.I)
DOWN = re.compile(r'\b(decrease[ds]?|down|fell|fall(?:s|en)?|declin\w*|drop\w*|lower|reduc\w*)\b', re.I)

FORMAT_DRIFT = ('format: abstention kept, labels stripped', 'format: trend reworded (right direction)')


def user_text(cell):
    """The user message of an adapted row (the platform stores the prompt as a JSON string of messages)."""
    try:
        msgs = json.loads(cell) if isinstance(cell, str) else cell
        return [m['content'] for m in msgs if m['role'] == 'user'][-1]
    except Exception:
        return str(cell)


def set_type(text, label):
    lines = text.split(NL)
    for i, ln in enumerate(lines):
        if ln.lower().startswith('type:'):
            lines[i] = 'Type: ' + label
            return NL.join(lines)
    return text.rstrip() + NL + 'Type: ' + label


def classify(key, out):
    """Name the kind of damage in an answer that failed the check."""
    answer = parse(out)['answer'] or out.split(NL)[0]
    if key['qtype'] == 'abstain':
        return FORMAT_DRIFT[0] if is_abstain(out) else 'content: abstain row really wrong'
    if key['qtype'] == 'trend':
        if is_abstain(answer):
            return 'content: answerable question flipped to abstain'
        up, down = bool(UP.search(answer)), bool(DOWN.search(answer))
        if up != down and up == (key['value'] == 'increased'):
            return FORMAT_DRIFT[1]
        return 'content: trend wrong direction or unclear'
    if is_abstain(answer):
        return 'content: answerable question flipped to abstain'
    return 'content: wrong number or name'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', default=repo_path('data', 'adapted_raw.jsonl'))
    ap.add_argument('--keep-bad-type-rows', action='store_true')
    ap.add_argument('--no-restore-dropped', action='store_true')
    a = ap.parse_args()

    train = {r['id']: r for r in read_jsonl(repo_path('data', 'train.jsonl'))}
    keys = {k['id']: k for k in read_jsonl(repo_path('data', 'answer_key.jsonl'))}
    c = collections.Counter()
    damage, per_type, per_type_bad, labels = (collections.Counter() for _ in range(4))
    fixed, seen, examples, type_examples = [], set(), [], []

    for r in read_jsonl(a.src):
        c['rows'] += 1
        m = REF.search(user_text(r.get('original_prompt', '')))
        rid = m.group(0) if m else None
        if rid not in train:
            c['unmatched'] += 1
            continue
        if rid in seen:
            c['duplicate_ids'] += 1
            continue
        seen.add(rid)
        c['matched'] += 1
        k, base = keys[rid], train[rid]
        out = str(r.get('enhanced_completion') or '').strip()
        ok, ab, fmt = check(k, out)
        per_type[k['qtype']] += 1
        labels[parse(out)['type'].lower()] += 1
        if not ok:
            c['wrong'] += 1
            per_type_bad[k['qtype']] += 1
            damage[classify(k, out)] += 1
            if len(examples) < 5:
                examples.append((rid, base['output'], out))
            fixed.append(base)
            continue
        if not fmt:
            c['line_missing'] += 1
            fixed.append(base)
            continue
        want = 'abstain' if k['kind'] == 'abstain' else 'computed'
        if parse(out)['type'].lower() != want:
            c['bad_type'] += 1
            if len(type_examples) < 3:
                type_examples.append((rid, out))
            if a.keep_bad_type_rows:
                fixed.append(base)
                continue
            out = set_type(out, want)
        c['kept'] += 1
        fixed.append({'id': rid, 'input': base['input'], 'output': out})

    if not a.no_restore_dropped:
        for rid, base in train.items():
            if rid not in seen:
                c['restored_dropped'] += 1
                fixed.append(base)

    n = max(c['matched'], 1)
    content = sum(v for k, v in damage.items() if k.startswith('content'))
    drift = sum(v for k, v in damage.items() if k.startswith('format'))
    flips = damage['content: answerable question flipped to abstain']
    n_abstain = sum(1 for k in keys.values() if k['kind'] == 'abstain' and k['id'] in train)
    correct = c['matched'] - c['wrong'] - c['line_missing']  # answers that passed the checker with all 3 lines
    lines = [
        f"rows in adapted file: {c['rows']} (original {len(train)})",
        f"matched to answer key: {c['matched']} ({c['matched'] / max(c['rows'], 1):.1%}); "
        f"unmatched {c['unmatched']}; duplicate ids {c['duplicate_ids']}",
        f"answers that fail the checker: {c['wrong']} ({c['wrong'] / n:.1%} of matched)",
        f"  wrong content: {content} ({content / n:.1%}); of which answerable questions flipped to abstain: {flips}",
        f"  right meaning, broken wording or format: {drift} ({drift / n:.1%})",
        f"abstention rows that fail the checker: {damage[FORMAT_DRIFT[0]] + damage['content: abstain row really wrong']}"
        f" of {n_abstain} (labels stripped: {damage[FORMAT_DRIFT[0]]})",
        f"correct answers carrying a wrong Type label: {c['bad_type']} of {correct}",
        f"enhanced rows kept after repair: {c['kept']}",
        f"rows the platform dropped, restored from original: {c['restored_dropped']}",
        f"rows in repaired dataset: {len(fixed)}",
    ]

    os.makedirs(repo_path('runs'), exist_ok=True)
    with open(repo_path('runs', 'audit_report.md'), 'w', encoding='utf-8') as fh:
        w = lambda s='': fh.write(s + NL)
        w('# Audit report')
        w()
        for x in lines:
            w('- ' + x)
        w()
        w('## Damage categories (answers that fail the checker)')
        w()
        w('| category | rows | share of matched |')
        w('|---|---|---|')
        for name, v in damage.most_common():
            w(f'| {name} | {v} | {v / n:.1%} |')
        w()
        w('## Failure rate by question type')
        w()
        w('| type | failing | total | rate |')
        w('|---|---|---|---|')
        for q in sorted(per_type):
            w(f'| {q} | {per_type_bad[q]} | {per_type[q]} | {per_type_bad[q] / per_type[q]:.0%} |')
        w()
        w('## Type labels found in the adapted answers (required: computed, abstain)')
        w()
        w(', '.join(f'`{k or "(none)"}` {v}' for k, v in labels.most_common(10)))
        w()
        w('## Wrong answers (original vs adapted)')
        for rid, o, x in examples:
            w()
            w(f'**{rid}**')
            w('Original: ' + o.replace(NL, ' | '))
            w('Adapted: ' + x.replace(NL, ' | '))
        w()
        w('## Bad Type labels (adapted)')
        for rid, x in type_examples:
            w()
            w(f'**{rid}**')
            w(x.replace(NL, ' | '))

    print(NL.join(lines))
    write_jsonl(repo_path('data', 'repaired.jsonl'), fixed)
    write_jsonl(repo_path('data', 'repaired_messages.jsonl'), [to_messages(r['input'], r['output']) for r in fixed])


if __name__ == '__main__':
    main()
