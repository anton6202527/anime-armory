#!/usr/bin/env bash
set -euo pipefail
# Audit command file. On macOS, executing conda from bash/zsh/Python wrappers can disable PyTorch MPS.
if [[ "$(uname -s)" == "Darwin" ]]; then
  echo '[error] macOS MPS-safe launch requires running the printed conda command directly from top-level zsh, not this script file.' >&2
  exit 64
fi
cd /Users/lalala/sd-scripts
conda run -n sdxl-comfy accelerate launch --num_processes 1 --num_machines 1 --mixed_precision no --num_cpu_threads_per_process 1 /Users/lalala/sd-scripts/sdxl_train_network.py --pretrained_model_name_or_path /Users/lalala/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors --dataset_config '/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/设定库/lora/CHAR_01/镇魔司伪装态/sdxl_dataset_config.toml' --output_dir '/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/设定库/lora/CHAR_01/镇魔司伪装态' --output_name 'CHAR_01_镇魔司伪装态_v1' --save_model_as safetensors --save_precision fp16 --network_module networks.lora --network_dim 8 --network_alpha 8 --learning_rate 5e-4 --unet_lr 5e-4 --text_encoder_lr 5e-5 5e-5 --max_train_steps 1000 --train_batch_size 1 --mixed_precision no --optimizer_type AdamW --lr_scheduler constant --gradient_checkpointing --cache_latents --cache_latents_to_disk --max_data_loader_n_workers 0 --seed 4242 --caption_extension .txt --keep_tokens 1 --tokenizer_cache_dir '/Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/local_sdxl_cache/tokenizers' --metadata_trigger_phrase char01_jiang_yuechu_zhenmosi_v1 --training_comment 'n2d local SDXL LoRA training; trigger=char01_jiang_yuechu_zhenmosi_v1' --lowram --network_train_unet_only --cache_text_encoder_outputs --cache_text_encoder_outputs_to_disk
