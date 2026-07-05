# Local SDXL LoRA Train Command

- character_id: `CHAR_HE_PINGSHENG`
- form: `常态`
- trigger: `he_pingsheng_normal_v1`
- base checkpoint: `/Users/lalala/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`
- trainer: `/Users/lalala/sd-scripts/sdxl_train_network.py`
- conda env: `sdxl-comfy`
- optimizer: `AdamW`
- LoRA rank/alpha: `16/16`
- resolution: `512` with aspect buckets for first local MPS v1 (`768` smoke worked but estimated ~16-17h for 1000 steps)
- output model: `设定库/lora/CHAR_HE_PINGSHENG/常态/CHAR_HE_PINGSHENG_常态_v1.safetensors`

Smoke test uses `--max_train_steps 2`.
Formal run uses `--max_train_steps 1000`.

## Smoke Results

- `mixed_precision=fp16`: failed; Accelerate rejects fp16 on MPS.
- `mixed_precision=bf16`: failed; Accelerate rejects bf16 on MPS.
- `resolution=768`, `mixed_precision=no`: succeeded; about 60 seconds/step.
- `resolution=512`, `mixed_precision=no`: succeeded; about 20 seconds/step after cache.

## Formal Command Shape

The formal run writes:

- log: `training/local_sdxl_v1/train_1000.log`
- pid: `training/local_sdxl_v1/train_1000.pid`
- output: `CHAR_HE_PINGSHENG_常态_v1.safetensors`
