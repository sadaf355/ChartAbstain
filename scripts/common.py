"""Shared helpers: data I/O, the system prompt, answer parsing and the answer checker."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NL = chr(10)
NUM = re.compile(r'-?[0-9]+(?:,[0-9]{3})*(?:[.][0-9]+)?')
TYPE_END = re.compile(r'Type:\s*(computed|abstain)')

SYSTEM = ('You answer questions about business charts using only the data given. '
          'Reply in three lines: Answer, Reason, Type. If the chart does not contain '
          'the information, the Answer is: Cannot be determined from this chart. and Type is abstain.')


def repo_path(*parts):
    """Path inside the repository, independent of the current working directory."""
    return os.path.join(ROOT, *parts)


def read_jsonl(path):
    with open(path, encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path, rows):
    with open(path, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + NL)


def to_messages(inp, out):
    return {'messages': [{'role': 'system', 'content': SYSTEM},
                         {'role': 'user', 'content': inp},
                         {'role': 'assistant', 'content': out}]}


def parse(output):
    """Split a three-line reply into its Answer / Reason / Type values."""
    d = {'answer': '', 'reason': '', 'type': ''}
    for line in output.splitlines():
        for k in d:
            if line.lower().startswith(k + ':') and not d[k]:
                d[k] = line.split(':', 1)[1].strip()
    return d


def is_abstain(text):
    t = text.lower()
    return 'cannot be determined' in t or 'not enough information' in t


def has_name(name, text):
    return re.search('(?<![A-Za-z0-9])' + re.escape(name) + '(?![A-Za-z0-9])', text, re.I)


def check(key, output):
    """Return (correct, abstained, format_ok) for one reply, using the code-computed answer key."""
    p = parse(output)
    fmt = bool(p['answer'] and p['reason'] and p['type'])
    ab = is_abstain(p['answer'])
    kind, line = key['kind'], p['answer']
    if kind == 'abstain':
        return ab, ab, fmt
    if ab or not line:
        return False, ab, fmt
    if kind == 'num':
        nums = [float(x.replace(',', '')) for x in NUM.findall(line)]
        t = key['value']
        tol = key.get('tol') or max(0.11, 0.003 * abs(t))
        return bool(nums) and abs(nums[0] - t) <= tol, ab, fmt
    if kind == 'name':
        found = [n for n in key['names'] if has_name(n, line)]
        return found == [key['value']], ab, fmt
    if kind == 'rank':
        pos = []
        for n in key['value']:
            m = has_name(n, line)
            pos.append(m.start() if m else -1)
        return min(pos) >= 0 and pos == sorted(pos), ab, fmt
    if kind == 'trend':
        w = key['value']
        other = 'decreased' if w == 'increased' else 'increased'
        low = line.lower()
        return (w in low) and (other not in low), ab, fmt
    return False, ab, fmt


def clean_output(text):
    """Cut stray tokens that some tuned adapters emit after the Type label (they never stop cleanly)."""
    m = TYPE_END.search(text)
    return (text[:m.end()] if m else text).strip()


def lenient_output(text):
    """Content-only view: start at the first 'Answer:' (add the label if the model left it out)."""
    m = re.search(r'answer:', text, re.I)
    return text[m.start():] if m else 'Answer: ' + text


def type_ok(key, output):
    """True if the Type label is the one the task requires (abstain for abstentions, else computed)."""
    want = 'abstain' if key['kind'] == 'abstain' else 'computed'
    return parse(output)['type'].strip().lower() == want
