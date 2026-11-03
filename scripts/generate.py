"""Generate the synthetic chart Q&A dataset (seed 7). Every answer is computed by code, never by a model."""
import os
import random
from types import SimpleNamespace as NS
from common import NL, ROOT, write_jsonl, to_messages

os.chdir(ROOT)  # write to <repo>/data whatever the launch directory is

random.seed(7)
N_TABLES, Q_PER_TABLE, HARD_CAP = 500, 6, 120
HOLDOUT = {'logistics', 'energy'}   # unseen domains -> hard slice
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
NO_INFO = 'Cannot be determined from this chart.'
METRICS = ['profit margin', 'customer satisfaction score', 'industry-wide market share', 'number of employees']
DOMAINS = [
    NS(key='retail', title='Monthly sales by region', ents=['North', 'South', 'East', 'West', 'Central'], per='months', unit='INR lakh', lo=20, hi=120),
    NS(key='saas', title='Monthly recurring revenue by plan', ents=['Basic', 'Pro', 'Team', 'Enterprise', 'Starter'], per='months', unit='USD thousand', lo=10, hi=90),
    NS(key='expense', title='Quarterly expenses by department', ents=['Marketing', 'Operations', 'HR', 'IT', 'Sales'], per='quarters', unit='INR lakh', lo=5, hi=60),
    NS(key='fund', title='Fund NAV by scheme', ents=['Alpha Equity', 'Bluechip', 'Debt Plus', 'Hybrid', 'Index Fifty'], per='quarters', unit='INR per unit', lo=15, hi=90),
    NS(key='loan', title='Loan default rate by segment', ents=['Personal', 'Home', 'Auto', 'Business', 'Education'], per='quarters', unit='percent', lo=1, hi=12),
    NS(key='hospital', title='Bed occupancy by ward', ents=['ICU', 'General', 'Maternity', 'Pediatrics', 'Surgical'], per='weeks', unit='percent', lo=40, hi=98),
    NS(key='crop', title='Average mandi price by crop', ents=['Wheat', 'Rice', 'Onion', 'Tomato', 'Soybean'], per='months', unit='INR per quintal', lo=800, hi=4500),
    NS(key='school', title='Enrollment by grade band', ents=['Primary', 'Middle', 'Secondary', 'Senior', 'Nursery'], per='years', unit='students', lo=200, hi=1500),
    NS(key='energy', title='Electricity use by plant', ents=['Plant A', 'Plant B', 'Plant C', 'Plant D', 'Plant E'], per='months', unit='MWh', lo=100, hi=900),
    NS(key='logistics', title='Average delivery delay by route', ents=['Mumbai-Pune', 'Delhi-Jaipur', 'Chennai-Hyderabad', 'Kolkata-Patna', 'Surat-Indore'], per='weeks', unit='hours', lo=2, hi=30),
]

def num(x, dec):
    return f'{x:.{dec}f}'

def labels(per, n):
    m = n + 1   # the last label is never shown; used for 'not on the chart' questions
    if per == 'months':
        s = random.randint(0, 12 - m)
        return MONTHS[s:s + m]
    if per == 'quarters':
        return [f'Q{(i % 4) + 1} FY{24 + i // 4}' for i in range(m)]
    if per == 'years':
        s = random.randint(2014, 2018)
        return [str(s + i) for i in range(m)]
    return [f'Week {i + 1}' for i in range(m)]

def make_table(d):
    k, n = random.randint(2, 4), random.randint(4, 7)
    names = random.sample(d.ents, k)
    labs = labels(d.per, n)
    dec = 0 if d.hi >= 800 else 1
    data = {}
    for nm in names:
        v, row = random.uniform(d.lo, d.hi), []
        for _ in range(n):
            row.append(int(round(v)) if dec == 0 else round(v, 1))
            v = max(d.lo * 0.3, v * (1 + random.uniform(-0.13, 0.16)))
        data[nm] = row
    if any(0 in r for r in data.values()):
        return None
    for i in range(n):
        col = [data[nm][i] for nm in names]
        if len(set(col)) < len(col):
            return None   # no ties inside a period
    ctype = random.choice(['bar', 'line', 'stacked bar', 'area'])
    start = 0
    if ctype == 'bar' and random.random() < 0.5:
        start = int(min(x for r in data.values() for x in r) * random.uniform(0.7, 0.92))
    return NS(d=d, unit=d.unit, title=d.title, ents=d.ents, names=names, labs=labs[:-1],
              missing=labs[-1], data=data, dec=dec, ctype=ctype, start=start)

def describe(c):
    rows = [f'Chart: {c.ctype} chart. Title: {c.title} ({c.unit}).',
            f'Y-axis starts at {c.start}.', 'Data:']
    for nm in c.names:
        cells = '; '.join(f'{p}={num(v, c.dec)}' for p, v in zip(c.labs, c.data[nm]))
        rows.append(f'{nm}: {cells}')
    return NL.join(rows)

def pick_period(c):
    i = random.randrange(len(c.labs))
    return i, c.labs[i], {nm: c.data[nm][i] for nm in c.names}

# every q_* returns (question, answer, reason, kind, value, extra) or None
def q_max(c, top=True):
    i, p, col = pick_period(c)
    order = sorted(col, key=col.get, reverse=top)
    w, nx = order[0], order[1]
    word = 'highest' if top else 'lowest'
    q = random.choice([f'Which series has the {word} value in {p}?',
                       f'In {p}, which series is {word}?',
                       f'Name the series with the {word} value in {p}.'])
    why = f'In {p}, {w} is {num(col[w], c.dec)} and the next one, {nx}, is {num(col[nx], c.dec)}.'
    return q, w, why, 'name', w, {}

def q_min(c):
    return q_max(c, False)

def q_pct(c):
    s = random.choice(c.names)
    i, j = sorted(random.sample(range(len(c.labs)), 2))
    a, b = c.data[s][i], c.data[s][j]
    v = round((b - a) / a * 100, 1)
    q = random.choice([f'What is the percent change in {s} from {c.labs[i]} to {c.labs[j]}?',
                       f'By what percent did {s} change between {c.labs[i]} and {c.labs[j]}?'])
    ans = f'{v:+.1f}% (from {num(a, c.dec)} to {num(b, c.dec)}) for {s}'
    return q, ans, 'Percent change = (new - old) / old x 100, using the plotted values.', 'num', v, {}

def q_diff(c):
    i, p, col = pick_period(c)
    s1, s2 = random.sample(c.names, 2)
    dv = round(abs(col[s1] - col[s2]), c.dec)
    q = random.choice([f'What is the difference between {s1} and {s2} in {p}?',
                       f'In {p}, how far apart are {s1} and {s2}?'])
    why = f'In {p}, {s1} is {num(col[s1], c.dec)} and {s2} is {num(col[s2], c.dec)}.'
    return q, f'{num(dv, c.dec)} {c.unit}', why, 'num', dv, {}

def q_rank(c):
    i, p, col = pick_period(c)
    order = sorted(col, key=col.get, reverse=True)
    q = random.choice([f'Rank the series from highest to lowest in {p}.',
                       f'What is the ranking of the series in {p}, highest first?'])
    why = f'Values in {p}: ' + '; '.join(f'{n}={num(col[n], c.dec)}' for n in order) + '.'
    return q, ', then '.join(order), why, 'rank', order, {}

def q_trend(c):
    s = random.choice(c.names)
    first, last = c.data[s][0], c.data[s][-1]
    if first == last:
        return None
    w = 'increased' if last > first else 'decreased'
    a, b = c.labs[0], c.labs[-1]
    q = random.choice([f'Did {s} increase or decrease from {a} to {b}?',
                       f'Overall, did {s} go up or down between {a} and {b}?'])
    why = f'{s} went from {num(first, c.dec)} in {a} to {num(last, c.dec)} in {b}.'
    return q, f'{s} {w}', why, 'trend', w, {}

def q_share(c):
    i, p, col = pick_period(c)
    s = random.choice(c.names)
    tot = sum(col.values())
    v = round(col[s] / tot * 100, 1)
    q = random.choice([f'What share of the total does {s} account for in {p}?',
                       f'In {p}, what percent of the total is {s}?'])
    why = f'{s} is {num(col[s], c.dec)} out of a total of {num(tot, c.dec)} in {p}.'
    return q, f'{v:.1f}% of the total', why, 'num', v, {}

def q_axis(c):   # truncated-axis trap
    if c.start <= 0:
        return None
    i, p, col = pick_period(c)
    s1, s2 = sorted(random.sample(c.names, 2), key=col.get, reverse=True)
    a, b = col[s1], col[s2]
    x = round((a - b) / b * 100, 1)
    q = f'The bar for {s1} in {p} looks much taller than {s2}. By what percent is {s1} actually higher than {s2}?'
    why = f'The y-axis starts at {c.start}, not 0, so the bars exaggerate the gap. Real gap = ({num(a, c.dec)} - {num(b, c.dec)}) / {num(b, c.dec)} x 100.'
    return q, f'{x:.1f}% higher', why, 'num', x, {}

def q_unit(c):   # unit-conversion trap
    if c.unit == 'INR lakh':
        div, new, nd, hint = 100, 'INR crore', 2, '(1 crore = 100 lakh)'
    elif c.unit == 'USD thousand':
        div, new, nd, hint = 1000, 'USD million', 3, '(1 million = 1000 thousand)'
    else:
        return None
    i, p, col = pick_period(c)
    tot = sum(col.values())
    v = round(tot / div, nd)
    q = f'What is the total of all series in {p}, in {new}? {hint}'
    why = f'The total in {p} is {num(tot, c.dec)} {c.unit}. Divide by {div} to convert.'
    return q, f'{v:.{nd}f} {new}', why, 'num', v, {'tol': 1.1 * 10 ** -nd}

def q_abstain(c):
    s, p = random.choice(c.names), random.choice(c.labs)
    first, last = c.labs[0], c.labs[-1]
    kind = random.choice(['future', 'cause', 'period', 'series', 'metric'])
    if kind == 'future':
        q = random.choice([f'What will {s} be in the period after {last}?', f'Predict the value of {s} for the next period.'])
        why = f'The chart only shows {first} to {last}. It has no forecast.'
    elif kind == 'cause':
        q = f'Why did {s} change in {p}?'
        why = 'The chart shows values only. It gives no information about the cause.'
    elif kind == 'period':
        q = f'What was {s} in {c.missing}?'
        why = f'The chart covers {first} to {last} only. {c.missing} is not shown.'
    elif kind == 'series':
        others = [e for e in c.ents if e not in c.names]
        if not others:
            return None
        fake = random.choice(others)
        q = f'What was {fake} in {p}?'
        why = f'{fake} is not on this chart. The series are ' + ', '.join(c.names) + '.'
    else:
        m = random.choice(METRICS)
        q = f'What was the {m} of {s} in {p}?'
        why = f'The chart shows only {c.title.lower()} ({c.unit}). It does not show {m}.'
    return q, NO_INFO, why, 'abstain', None, {}

COMPUTED = [q_max, q_min, q_pct, q_diff, q_rank, q_trend, q_share]

def pick(c):
    r = random.random()
    if r < 0.20:
        return 'abstain', q_abstain(c)
    if r < 0.35:
        fn = random.choice([q_axis, q_unit])
        item = fn(c)
        if item:
            return fn.__name__[2:], item
    fn = random.choice(COMPUTED)
    return fn.__name__[2:], fn(c)

out = {'train': [], 'test': [], 'hard': []}
keys, counter, tables = [], 0, 0
while tables < N_TABLES:
    d = random.choice(DOMAINS)
    c = make_table(d)
    if c is None:
        continue
    tables += 1
    sl = 'hard' if d.key in HOLDOUT else ('test' if random.random() < 0.15 else 'train')
    desc, seen = describe(c), set()
    for _ in range(Q_PER_TABLE):
        qt, item = pick(c)
        if item is None or item[0] in seen:
            continue
        seen.add(item[0])
        counter += 1
        rid = f'A-{counter:04d}'
        q, ans, why, kind, val, extra = item
        atype = 'abstain' if kind == 'abstain' else 'computed'
        out[sl].append({'id': rid, 'input': f'Ref: {rid}{NL}{desc}{NL}Question: {q}',
                        'output': f'Answer: {ans}{NL}Reason: {why}{NL}Type: {atype}'})
        keys.append({'id': rid, 'slice': sl, 'table_id': tables, 'qtype': qt, 'kind': kind,
                     'value': val, 'names': c.names, **extra})

random.shuffle(out['hard'])
out['hard'] = out['hard'][:HARD_CAP]
keep = {r['id'] for rows in out.values() for r in rows}
os.makedirs('data', exist_ok=True)
write_jsonl('data/train.jsonl', out['train'])
write_jsonl('data/train_messages.jsonl', [to_messages(r['input'], r['output']) for r in out['train']])
write_jsonl('data/test.jsonl', out['test'])
write_jsonl('data/hard.jsonl', out['hard'])
write_jsonl('data/eval.jsonl', out['test'] + out['hard'])
write_jsonl('data/answer_key.jsonl', [k for k in keys if k['id'] in keep])
n_ab = sum(1 for r in out['train'] if 'Type: abstain' in r['output'])
print('train', len(out['train']), 'test', len(out['test']), 'hard', len(out['hard']))
print('abstain share in train:', round(n_ab / max(len(out['train']), 1), 3))
