#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手"
LORA_ROOT="${PROJECT_ROOT}/设定库/lora/CHAR_HE_PINGSHENG/常态"
TRAIN_ROOT="${LORA_ROOT}/training/local_sdxl_v1"
LOG_PATH="${TRAIN_ROOT}/train_1000.log"
PID_PATH="${TRAIN_ROOT}/train_1000.pid"
EXIT_PATH="${TRAIN_ROOT}/train_1000.exit"

mkdir -p "${TRAIN_ROOT}/logs_formal"
echo "$$" > "${PID_PATH}"
rm -f "${EXIT_PATH}"

{
  echo "[start] $(date '+%Y-%m-%d %H:%M:%S %z') local SDXL LoRA training"
  echo "[output] ${LORA_ROOT}/CHAR_HE_PINGSHENG_常态_v1.safetensors"
  cd /Users/lalala/sd-scripts
  PYTORCH_ENABLE_MPS_FALLBACK=1 \
  N2D_ASSUME_LOCAL_ACCELERATOR=1 \
  conda run -n sdxl-comfy accelerate launch --num_cpu_threads_per_process 1 \
    /Users/lalala/sd-scripts/sdxl_train_network.py \
    --pretrained_model_name_or_path /Users/lalala/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors \
    --dataset_config "${TRAIN_ROOT}/dataset_config_512.toml" \
    --output_dir "${LORA_ROOT}" \
    --output_name CHAR_HE_PINGSHENG_常态_v1 \
    --save_model_as safetensors \
    --network_module networks.lora \
    --network_dim 16 \
    --network_alpha 16 \
    --learning_rate 1e-4 \
    --unet_lr 1e-4 \
    --optimizer_type AdamW \
    --lr_scheduler constant \
    --max_train_steps 1000 \
    --train_batch_size 1 \
    --mixed_precision no \
    --save_precision float \
    --gradient_checkpointing \
    --cache_latents \
    --cache_latents_to_disk \
    --cache_text_encoder_outputs \
    --cache_text_encoder_outputs_to_disk \
    --network_train_unet_only \
    --max_data_loader_n_workers 0 \
    --lowram \
    --seed 4242 \
    --save_every_n_steps 250 \
    --save_last_n_steps 3 \
    --logging_dir "${TRAIN_ROOT}/logs_formal" \
    --metadata_title CHAR_HE_PINGSHENG_常态_v1 \
    --metadata_trigger_phrase he_pingsheng_normal_v1 \
    --training_comment local_sdxl_mps_512_1000steps
  status=$?
  echo "[exit] $(date '+%Y-%m-%d %H:%M:%S %z') status=${status}"
  echo "${status}" > "${EXIT_PATH}"
  exit "${status}"
} >> "${LOG_PATH}" 2>&1
