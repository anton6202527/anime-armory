# n2d 本机 VLM 后端接入（mlx-vlm）

本机默认使用 `n2dvlm` conda 环境里的 MLX-VLM，面向 Apple Silicon。两条接口不要混用：

## 1. 单图设定核对：`N2D_VLM_CMD`

消费方：`skills/n2d-image/scripts/vlm_verify.py`、`image_qc.py --prop-shape-vlm-confirm` 等。

契约：命令模板必须包含 `{image}`，建议包含 `{prompt}`；stdout 返回：

```json
{"match": true, "confidence": 0.9, "mismatches": [], "reason": "符合设定"}
```

可用模板：

```bash
export N2D_VLM_CMD='conda run -n n2dvlm python skills/n2d-review/scripts/backends/vlm_cmd_mlxvlm.py --image {image} --prompt {prompt}'
```

当前仓库已内置默认自动接入：未显式设置 `N2D_VLM_CMD` 时，若检测到 `n2dvlm` 环境且 `vlm_cmd_mlxvlm.py` 存在，`vlm_verify.py` 会自动使用上述后端。需要临时关闭时：

```bash
export N2D_VLM_CMD=off
```

## 2. 两图外观比对：`N2D_APPEARANCE_BATCH_CMD`

消费方：`skills/n2d-review/scripts/appearance_judge_runner.py`。

契约：batch 命令接收 `<manifest.json>`，读取其中 `pairs:[{character,shot,reference,shot_image}]`，就地写回 `findings`。这是 `appearance_mlxvlm.py` 的接口，不是 `N2D_VLM_CMD` 的单图接口。

可用模板：

```bash
export N2D_APPEARANCE_BATCH_CMD='conda run -n n2dvlm python skills/n2d-review/scripts/backends/appearance_mlxvlm.py'
```

当前仓库也已内置默认自动接入：未显式设置 `N2D_APPEARANCE_BATCH_CMD` 时，若检测到 `n2dvlm` 环境且 `appearance_mlxvlm.py` 存在，`appearance_judge_runner.py --write` 会自动使用该 batch 后端。需要只写 manifest、不跑重模型时：

```bash
export N2D_APPEARANCE_BATCH_CMD=off
```

## 模型与阈值

- `N2D_VLM_MODEL`：默认 `mlx-community/Qwen2.5-VL-3B-Instruct-4bit`。内存富裕时可换 `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`。
- `N2D_VLM_MAX_TOKENS`：单图判官输出上限，默认 `512`。
- `N2D_VLM_BLOCK_FLOOR`：`vlm_verify.py` block 置信阈值，默认 `0.6`。
- `N2D_APPEARANCE_WARN_FLOOR` / `N2D_APPEARANCE_BLOCK_FLOOR`：外观相似度阈值，默认 `0.7` / `0.5`。

## Smoke Test

用任意本地图验证单图后端能读图并输出 JSON：

```bash
conda run -n n2dvlm python skills/n2d-review/scripts/backends/vlm_cmd_mlxvlm.py \
  --image <image.png> \
  --prompt '请判断图片中是否有清晰可见的人物。只输出 JSON：{"match": true/false, "confidence": 0-1, "mismatches": [], "reason": "一句话"}'
```

预期 stdout 可被 `vlm_verify.parse_verdict()` 解析。stderr/非 0 退出码表示后端不可用，n2d 会跳过或按对应 gate 规则提示补环境，不会臆造判定。
