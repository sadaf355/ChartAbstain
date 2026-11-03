"""List the training settings of every adapter in adapters/ and flag identical weight files.

    python scripts/adapter_info.py

Run it after downloading adapters from the platform. It catches two easy mistakes: evaluating the wrong
folder (two adapters with the same md5 are the same weights) and comparing runs that were trained with
different recipes (rank, alpha, epochs, steps differ).
"""
import glob
import hashlib
import json
import os

from common import repo_path


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    seen = {}
    for d in sorted(glob.glob(repo_path('adapters', '*'))):
        cfg_path, w_path = os.path.join(d, 'adapter_config.json'), os.path.join(d, 'adapter_model.safetensors')
        if not (os.path.isfile(cfg_path) and os.path.isfile(w_path)):
            print(f'{os.path.basename(d):<10} missing adapter_config.json or adapter_model.safetensors')
            continue
        cfg = json.load(open(cfg_path))
        ts_path = os.path.join(d, 'trainer_state.json')
        ts = json.load(open(ts_path)) if os.path.isfile(ts_path) else {}
        evals = [x['eval_loss'] for x in ts.get('log_history', []) if 'eval_loss' in x]
        mods = cfg.get('target_modules')
        digest = md5(w_path)
        name = os.path.basename(d)
        print(f"{name:<10} r={cfg.get('r')} alpha={cfg.get('lora_alpha')} dropout={cfg.get('lora_dropout')} "
              f"modules={len(mods) if isinstance(mods, (list, set)) else mods} "
              f"epochs={ts.get('num_train_epochs')} steps={ts.get('global_step')} "
              f"final_eval_loss={evals[-1] if evals else None} md5={digest[:12]}")
        if digest in seen:
            print(f'  WARNING: same weights as {seen[digest]}')
        seen.setdefault(digest, name)


if __name__ == '__main__':
    main()
