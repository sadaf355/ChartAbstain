"""Generate predictions with a base model, optionally with a LoRA adapter downloaded from the platform.

    python scripts/predict_local.py --inp data/eval.jsonl --out runs/preds/base_qwen3-4b_preds.jsonl \
        --model Qwen/Qwen3-4B-Base
    python scripts/predict_local.py --inp data/eval.jsonl --out runs/preds/A0_preds.jsonl \
        --model Qwen/Qwen3-4B-Base --adapter adapters/A0

The base model is loaded in 4-bit so it fits a free Colab T4. Base and tuned models are always loaded the same
way, so the comparison stays fair. With --adapter, the tokenizer (and chat template) is taken from the adapter
folder, because that is the template the platform trained with. Output is the raw model text; trimming of stray
tokens after the Type label happens in score.py, not here.
"""
import argparse

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from common import SYSTEM, read_jsonl, write_jsonl

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--inp', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--model', required=True, help='Hugging Face id of the base model')
ap.add_argument('--adapter', default=None, help='folder with adapter_config.json and adapter_model.safetensors')
ap.add_argument('--no_system', action='store_true', help='leave the system prompt out (use only if training had none)')
ap.add_argument('--bs', type=int, default=8)
ap.add_argument('--limit', type=int, default=0, help='only predict the first N rows (smoke test)')
a = ap.parse_args()

tok = AutoTokenizer.from_pretrained(a.adapter or a.model)
tok.padding_side = 'left'
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)
model = AutoModelForCausalLM.from_pretrained(a.model, quantization_config=bnb, device_map='auto')
if a.adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, a.adapter)
model.eval()

# Stop at the end-of-turn token as well as the tokenizer's own EOS.
stop_ids = [tok.convert_tokens_to_ids('<|im_end|>'), tok.eos_token_id]


def build(r):
    msgs = [{'role': 'user', 'content': r['input']}]
    if not a.no_system:
        msgs.insert(0, {'role': 'system', 'content': SYSTEM})
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)


rows = read_jsonl(a.inp)
if a.limit:
    rows = rows[:a.limit]
preds = []
for i in range(0, len(rows), a.bs):
    batch = rows[i:i + a.bs]
    enc = tok([build(r) for r in batch], return_tensors='pt', padding=True).to(model.device)
    with torch.no_grad():
        gen = model.generate(**enc, max_new_tokens=200, do_sample=False,
                             eos_token_id=stop_ids, pad_token_id=tok.pad_token_id)
    outs = tok.batch_decode(gen[:, enc['input_ids'].shape[1]:], skip_special_tokens=True)
    preds += [{'id': r['id'], 'output': o.strip()} for r, o in zip(batch, outs)]
    print(i + len(batch), '/', len(rows))
write_jsonl(a.out, preds)
print('wrote', len(preds), 'predictions to', a.out)
