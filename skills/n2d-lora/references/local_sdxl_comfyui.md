# 本机 SDXL / ComfyUI sidechain

## 定位

本机 SDXL 只用于两件事：

- 运行时路由：检测本机是否具备完整 LoRA 训练/验证环境；完整则优先本机 LoRA 训练，不完整则回到项目主/云端生图后端。
- LoRA 验证：加载 `.safetensors`，用同底模出少量验证图。
- hero 镜补强：核心角色的关键近景 / 爽点 / 封面候选镜，用已验证 LoRA 生成少量图后回流。

它不是项目主生图后端，不允许把整集隐式切到 ComfyUI/SDXL。凡使用本链路的镜头必须写
`生产数据/lora_exception_scope_<集>.json`，并在 `production_events.jsonl` 记录 sidechain 事件。

## 安装

```bash
bash skills/n2d-lora/scripts/install_sdxl_comfy.sh
python3 skills/n2d-lora/scripts/sdxl_local.py doctor
```

默认安装到：

- ComfyUI：`~/ComfyUI`
- conda env：`sdxl-comfy`
- 启动脚本：`~/ComfyUI/launch_n2d_sdxl.sh`

模型权重不自动下载。把 SDXL checkpoint 放到：

```text
~/ComfyUI/models/checkpoints/
```

把 LoRA `.safetensors` 放到：

```text
~/ComfyUI/models/loras/
```

## 写入项目 profile

```bash
python3 skills/n2d-lora/scripts/sdxl_local.py write-profile <作品根>
```

产物：

```text
<作品根>/生产数据/local_sdxl_profile.json
```

该 profile 明确 `not_a_project_model_switch=true`，只声明本机 SDXL 是 LoRA 验证 / hero shot sidechain。

## 运行时自动路由

每次准备 LoRA 训练或验证前先跑：

```bash
python3 skills/n2d-lora/scripts/sdxl_local.py route <作品根> \
  --character-id CHAR_SHEN \
  --form 常态 \
  --write
```

产物：

```text
<作品根>/生产数据/lora_runtime_route.json
```

判定规则：

- `decision.route=local_lora_training`：本机环境完整，优先用本机 LoRA 训练/验证链。
- `decision.route=cloud_image_generation_fallback`：本机不完整，不阻塞产线，继续使用 `_设置.md` 中的 `生图AI` / `生图模型` 作为云端/主生图后端。

“完整”不是只看 ComfyUI 是否能启动，还要求：

- ComfyUI 文件存在。
- `sdxl-comfy` conda env 存在且 MPS 可用。
- `models/checkpoints/` 至少有一个 SDXL checkpoint。
- 有 LoRA 训练入口：通过 `N2D_LORA_TRAIN_CMD` 配置，或本机存在常见 `sdxl_train_network.py` 训练脚本。
- 指定角色时，目标 `dataset_manifest.json` 已 ready for training。

如果训练入口在自定义位置，设置：

```bash
export N2D_LORA_TRAIN_CMD='accelerate launch /path/to/sdxl_train_network.py'
```

## macOS MPS 本机训练启动约束

在 macOS/Apple Silicon 上，MPS 可用不等于所有包装层都能用 MPS。已验证的安全路径是：

```bash
python3 skills/n2d-lora/scripts/local_train.py prepare <作品根> --character-id CHAR_XXX --form 常态
# 然后把 prepare 打印出来的 `conda run -n sdxl-comfy accelerate launch ...` 整行，
# 直接从当前顶层 zsh 执行。
```

不要用 `local_train.py run`、不要执行生成的 `train_command*.sh` 文件、不要用 Python subprocess /
`env ... conda run` / bash/zsh 脚本包一层再启动；这些包装在本机实测会让 PyTorch MPS 退化为 CPU，
1000 step SDXL LoRA 会从小时级变成十几小时级。`local_train.py run` 在 macOS 默认 fail-fast，只保留
`--allow-nested-run` 给 CPU 诊断。

若 `sdxl_local.py route` 因 Python subprocess 探针报 `mps_not_available`，但已经从顶层 zsh 直接跑过
`conda run -n sdxl-comfy python -c 'import torch; x=torch.ones(1, device="mps"); print(x.device)'`
并确认输出 `mps:0`，可用 `--assume-local-accelerator` 重新写 route。该 override 会落进 route JSON 的
`accelerator_override_assumed=true`，只表示外部 MPS 探针已确认，不允许跳过后续训练日志、validate 或 register gate。

若要做速度探针，先跑 1 step，并只把日志里 `accelerator device: mps` 且模型日志显示 `device: mps:0`
视为本机 MPS 训练可用证据。1-step probe 产出的 `.safetensors` 只能作为连通性证据，不能 validate/register
成 ready LoRA。

直接 `torch.ones(..., device="mps")` 只能证明 PyTorch 能创建 MPS tensor，不能证明 sd-scripts 的训练主循环
没有落到 CPU。正式训练开始后仍应检查训练日志或进程抽样：若调用栈长期落在 `libtorch_cpu` /
`slow_conv2d_backward_cpu`，应记录为 CPU fallback 长训；产物仍可验证，但不要把这次运行当作 MPS 性能基线。

启用 `--cache_text_encoder_outputs` 时不能同时使用 caption shuffle。`local_train.py prepare` 会自动把
dataset TOML 的 `shuffle_caption` 置为 `false`，并从命令行移除 `--shuffle_caption`；手写命令也必须遵守，
否则 sd-scripts 会在进入训练前报错退出。

## 生成 hero 镜 workflow

```bash
python3 skills/n2d-lora/scripts/sdxl_local.py workflow <作品根> 第1集 \
  --clip Clip_03 \
  --character-id CHAR_SHEN \
  --form 常态 \
  --checkpoint "sd_xl_base_1.0.safetensors" \
  --lora "CHAR_SHEN_normal_v1.safetensors" \
  --trigger "shen_v1" \
  --prompt "close-up hero shot, same character DNA, series visual style" \
  --negative "wrong identity, deformed face, blurry"
```

产物：

```text
<作品根>/生产数据/comfyui_workflows/第1集_Clip_03_sdxl_lora.json
```

启动 ComfyUI 后可提交：

```bash
~/ComfyUI/launch_n2d_sdxl.sh
python3 skills/n2d-lora/scripts/sdxl_local.py enqueue <workflow.json>
```

## 接入 n2d gate

使用 SDXL/ComfyUI/LoRA 产物前，必须先写例外范围：

```bash
python3 skills/n2d-lora/scripts/lora.py exception-scope <作品根> 第1集 \
  --character-id CHAR_SHEN \
  --form 常态 \
  --clip Clip_03 \
  --reason "核心角色 hero close-up needs approved SDXL LoRA" \
  --project-image-model "GPT Image 2" \
  --lora-base-model "sdxl" \
  --style-bridge "match series lighting/color; run full image_qc and human signoff"
```

ComfyUI 输出图确认后记录事件：

```bash
python3 skills/n2d-lora/scripts/sdxl_local.py record-output <作品根> 第1集 \
  --clip Clip_03 \
  --output "<输出PNG路径>" \
  --character-id CHAR_SHEN \
  --form 常态 \
  --lora-model "CHAR_SHEN_normal_v1.safetensors" \
  --workflow "<workflow.json>"
```

然后必须跑：

```bash
python3 skills/n2d-lora/scripts/lora.py exception-scope <作品根> 第1集 --check
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image
```

## 不做的事

- 不把“能启动 ComfyUI”当成“能训练 LoRA”：训练必须通过 `route` 检测到完整本机训练入口；否则自动回落主/云端生图后端。
- 不自动下载权重：SDXL checkpoint/LoRA 权利和许可证由项目记录。
- 不替代主生图后端：只在 hero shot scope 内有效。
