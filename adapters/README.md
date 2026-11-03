# Adapters (not stored in git)

LoRA weights are large and live on Hugging Face instead: `https://huggingface.co/<HF_USERNAME>/<MODEL_REPO>`.
To re-run evaluation, download each adapter from the AutoScientist run page into this folder, one sub-folder
per run, each holding `adapter_config.json`, `adapter_model.safetensors`, `tokenizer.json` and
`trainer_state.json`. Then run `python scripts/adapter_info.py` to list the real settings of every folder.

| folder | data | recipe (from adapter_config.json / trainer_state.json) |
|---|---|---|
| FILL: A0 | original | |
| FILL: A1 | adapted, unaudited | |
| FILL: A2 | adapted + repaired | |
