# Dashboard Q&A with abstention: fine-tuning Qwen3-4B-Base with Adaption AutoScientist

A model that answers questions about business charts from the plotted data, gives a one-line reason, and says
**"Cannot be determined from this chart."** when the chart does not contain the answer.

Built for the AutoScientist Challenge (Entry A). The pipeline is: synthetic data with code-computed answers,
Adaption data adaptation, an **audit of the adapted data against the answer key**, a repaired dataset, and
LoRA fine-tuning of `Qwen/Qwen3-4B-Base` with AutoScientist.

- Live demo (pre-computed outputs): `<[HF Space link](https://huggingface.co/spaces/Sakshikale235/chartqa-abstain-demo)>`
  
## The task

Charts are given as text (type, title, unit, y-axis start, one row of values per series). Every reply has three lines:

```
Answer: ...
Reason: ...
Type: computed | abstain
```

Question types: highest/lowest, percent change, difference, ranking, trend, share of total, and two trap types,
**truncated y-axis** (the bar gap looks bigger than the real gap) and **unit conversion** (INR lakh to crore,
USD thousand to million). About 20% of questions are unanswerable (future values, causes, periods or series not
on the chart, metrics not shown) and must be answered with the abstention sentence.

## Data

`python scripts/generate.py` (seed 7) rebuilds everything in `data/`. All answers are computed by code.

| file | rows | purpose |
|---|---|---|
| `train.jsonl`, `train_messages.jsonl` | 1,970 | original training set (input/output and chat format) |
| `adapted_raw.jsonl` | 1,966 | Adaption's adapted version of the training set |
| `repaired.jsonl`, `repaired_messages.jsonl` | 1,970 | adapted data after the audit and repair |
| `test.jsonl` | 419 | new tables from domains seen in training |
| `hard.jsonl` | 120 | two unseen domains (logistics, energy) |
| `eval.jsonl` | 539 | test + hard, used for every score below |
| `answer_key.jsonl` | 2,509 | code-computed key used for scoring and the audit |

Split is by table, so no table appears in both train and test. The data is fully synthetic.

## Audit of Adaption's data adaptation

Adaptation settings: Prompt Deduplication and House Special on; rephrase, metadata injection, reasoning traces,
hallucination mitigation and checklist verification off. The platform quality score rose from 9.0 to 9.1.
`python scripts/audit.py` checks every adapted row against the answer key (full report: `runs/audit_report.md`):

| finding | result |
|---|---|
| rows matched to the key | 1,966 of 1,966 |
| answers failing the checker | **482 (24.5%)** |
| wrong content (wrong number or name, wrong trend direction, answerable question flipped to abstain) | 223 (11.3%), of which 83 flipped to "cannot be determined" |
| right meaning, broken wording or format | 259 (13.2%), mostly trend answers reworded and abstentions with labels stripped |
| correct answers with a wrong `Type` label | 1,146 of 1,484 (computed became "bar chart", "ranking", ...) |

Repair: wrong rows are restored from the original, the 4 dropped rows are restored, and the Type label is
corrected on rows whose answer was right. Result: `data/repaired.jsonl`.

## Training runs

Same base model (`Qwen/Qwen3-4B-Base`), same objective text, LoRA via AutoScientist. The platform chose the recipe
for each run, so recipes differ between runs. Real settings come from each adapter's `adapter_config.json` and
`trainer_state.json` (`python scripts/adapter_info.py`).

| run | data | recipe | platform win rate |
|---|---|---|---|
| A0 (strong recipe) | original | r=16, alpha=32, dropout 0.05, 4 epochs (100 steps), lr 1e-4, all attention + MLP modules | 86 vs 14 |
| A2 (light recipe) | repaired | r=8, alpha=16, dropout 0, 2 epochs (50 steps), lr 5e-5 | 77 vs 23 |
| A1 (light recipe) | adapted, unaudited | r=8, alpha=16, 2 epochs, lr 5e-5 | not recorded |

## Results

Greedy decoding on `data/eval.jsonl` (539 rows), 4-bit base model on a Colab T4. "Strict" needs the three-line
format; "content only" forgives a missing Type label and measures what the model knows. One seed per setup, so no
mean or standard deviation is reported.

| run | strict all | strict test | strict hard | abstain recall | over-abstain | format valid | content-only all |
|---|---|---|---|---|---|---|---|
| Qwen3-4B-Base, untuned | 4.1% | 4.3% | 3.3% | 0.0% | 0.0% | 8.0% | 20.4% |
| Qwen3.5-9B, untuned (extra baseline) | 5.4% | 5.0% | 6.7% | 0.0% | 0.0% | 5.6% | 52.5% |
| **A0, strong recipe, original data** | **63.3%** | **64.7%** | **58.3%** | **99.1%** | 0.0% | 94.4% | 63.3% |

Light-recipe runs (numbers from Colab, test slice; prediction files not yet in `runs/preds/`):
A1 adapted 26.7%, A2 repaired 24.3%. These scored far below the strong recipe, with abstention recall under 10%,
so the light recipe was under-trained. A1 gets the Type label right on 5.9% of rows, A2 on 76.1%, which shows the
effect of the repair on the label.

Reading the table: the untuned base model mostly fails the format (strict 4.1%), but even on content only it
reaches 20.4%, so the tuned model's gain is real: +42.9 points on content only, +59.2 strict, and abstention
recall goes from 16.5% (content only) to 99.1%. Accuracy is lower on the unseen-domain hard slice (58.3%).

## Reproduce

```bash
pip install -r requirements.txt            # GPU only needed for predict_local.py
python scripts/generate.py                 # rebuild data/
python scripts/audit.py                    # audit adapted_raw.jsonl, write repaired data
# download adapters into adapters/<run>/ (see adapters/README.md), then:
python scripts/adapter_info.py
python scripts/predict_local.py --inp data/eval.jsonl --out runs/preds/A0_preds.jsonl \
    --model Qwen/Qwen3-4B-Base --adapter adapters/A0
python scripts/summarize.py                # writes runs/results.md and runs/results.csv
python scripts/make_demo_examples.py --tuned A0   # refresh demo/examples.json
```

`notebooks/colab_eval.ipynb` runs the same steps on a free Colab T4 (Runtime, Change runtime type, T4 GPU).

## Repository layout

```
scripts/    generate, audit, predict_local, score, summarize, adapter_info, make_demo_examples, common
data/       synthetic dataset, adapted and repaired versions, eval sets, answer key
runs/       run_log.csv, results table, audit_report.md, saved predictions
demo/       Gradio app for the Hugging Face Space (pre-computed outputs)
notebooks/  Colab evaluation notebook
docs/       platform notes taken during the run
adapters/   LoRA weights go here locally; not stored in git
```

## Limits

Text-only charts (no images), synthetic English data, a single seed per setup, and an evaluation run in 4-bit.
Runs used different platform-chosen recipes, so the data comparison (A0 vs A1 vs A2) is confounded by recipe;
the audit numbers do not depend on training.
