# n2d-lora lifecycle schema

`n2d-lora` 把 LoRA 从“散落的 `.safetensors` 文件”变成可审计资产。默认目录：

```text
制漫剧/<剧名>/设定库/lora/<CHAR_ID>/<形态>/
├── dataset/
├── dataset_manifest.json
├── train_job.json
├── validation_report.json
├── lora_card.json
├── lora_card.md
└── <CHAR_ID>_<形态>_v1.safetensors
```

## `lora_card.json`

记录角色、形态、触发词、底模、许可和策略：

```json
{
  "kind": "n2d_lora_card",
  "version": 1,
  "character_id": "CHAR_SHEN",
  "character_name": "沈念",
  "form": "常态",
  "trigger": "沈念_常态_v1",
  "base_model": "sdxl",
  "license_mode": "commercial",
  "provider": "manual",
  "status": "candidate"
}
```

## `dataset_manifest.json`

扫描 `dataset/` 后生成。关键字段：

- `summary.images`：图片数量。
- `summary.captions`：caption 数。
- `summary.role_counts`：front/side/back/outfit/fullbody 等粗略角色分布。
- `summary.warnings`：低于 15 张、缺 caption、缺侧脸、图片过小等。
- `summary.ready_for_training`：无 warning 时才为 true。

## `train_job.json`

训练任务输入，不直接隐藏云提交：

- `provider`: `manual | fal | runpod`
- `base_model`
- `license_mode`
- `trigger`
- `dataset_manifest`
- `expected_model_path`
- `hyperparameters`
- `provider_payload`
- `warnings`

这份文件可以交给人或后续云适配器执行。商用项目若使用许可不清的底模，必须留 warning。

## `validation_report.json`

验证通过后才能注册 ready：

- `model_path`
- `model_sha256`
- `base_model`
- `trigger`
- `verdict`: `pass | warn | block`
- `manual_review.approved`
- `manual_review.allow_dataset_warnings`
- `manual_review.notes`：当 `allow_dataset_warnings=true` 时必填非空原因。
- `blocks`
- `warnings`

没有 `pass` verdict 时，`register` 默认拒绝写入 registry ready。若数据集存在 warning，只有报告里显式记录 `manual_review.allow_dataset_warnings=true` 且 `manual_review.notes` 非空才允许注册；否则即便人工 `approved` 也不能进入 ready。`register --force` 不提升 ready，只写 `status=candidate` 并记录 `manual_override.reasons`，供人工审计和后续补验证。

## registry 回写

`register` 会更新：

```json
{
  "identity_adapters": {
    "lora": {
      "status": "ready",
      "base_model": "sdxl",
      "model_path": "设定库/lora/CHAR_SHEN/常态/CHAR_SHEN_normal_v1.safetensors",
      "trigger": "沈念_常态_v1",
      "dataset": "设定库/lora/CHAR_SHEN/常态/dataset_manifest.json",
      "model_hash": "...",
      "validation_report": "设定库/lora/CHAR_SHEN/常态/validation_report.json",
      "train_job": "设定库/lora/CHAR_SHEN/常态/train_job.json"
    }
  }
}
```

如果强制登记但仍有 ready 阻断项，回写示例为：

```json
{
  "identity_adapters": {
    "lora": {
      "status": "candidate",
      "model_path": "设定库/lora/CHAR_SHEN/常态/missing.safetensors",
      "validation_report": "设定库/lora/CHAR_SHEN/常态/validation_report.json",
      "manual_override": {
        "forced": true,
        "reasons": [
          "validation_verdict_not_pass:block",
          "model_path_missing"
        ],
        "registered_at": "2026-06-08T12:00:00+00:00"
      }
    }
  }
}
```

然后必须运行：

```bash
python3 skills/n2d-identity/scripts/identity.py <作品根> --write
```
