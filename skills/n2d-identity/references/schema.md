# n2d identity closure schema

`n2d-identity` 生成两类生产数据。

## identity_adapter_matrix.json

路径：

```text
制漫剧/<剧名>/生产数据/identity_adapter_matrix.json
```

顶层：

```json
{
  "kind": "n2d_identity_adapter_matrix",
  "version": 1,
  "root": "制漫剧/剧名",
  "generated_at": "2026-06-08T00:00:00Z",
  "summary": {},
  "forms": []
}
```

每个 `forms[]`：

```json
{
  "character_id": "CHAR_WANG",
  "character_name": "王敦",
  "form": "常态",
  "asset_key": "王敦",
  "anchor_phrase": "圆脸微胖·短束发·旧青袍·眼神藏锋",
  "reference_group": {
    "front": {"path": "出图/共享/图片/定妆_王敦.png", "exists": true},
    "side": {"path": "出图/共享/图片/定妆_王敦_侧.png", "exists": true},
    "back": {"path": "出图/共享/图片/定妆_王敦_背.png", "exists": true},
    "outfit": {"path": "出图/共享/图片/定妆_王敦_半身.png", "exists": true},
    "turnaround": {"path": "出图/共享/图片/定妆_王敦_三视图.png", "exists": true}
  },
  "image_bindings": {
    "codex": {"mode": "reference_group", "status": "fallback_reference_group", "ready": true, "binding": "reference_group"},
    "seedream": {"mode": "universal_reference", "status": "registered", "ready": true, "binding": "universal_reference", "handle": "sd_ref_wang"},
    "kling": {"mode": "subject_library", "status": "registered", "ready": true, "binding": "subject_library", "handle": "klg_subj_123"},
    "sora": {"mode": "character_cameo", "status": "unregistered", "ready": false, "binding": "fallback_reference_group", "needs_action": "register_character_cameo"}
  },
  "video_bindings": {
    "kling": {"mode": "character_id", "status": "registered", "ready": true, "binding": "character_id", "handle": "klg_char_123"},
    "seedance": {"mode": "face_lock", "status": "unregistered", "ready": false, "binding": "fallback_reference_group", "needs_action": "register_face_lock"},
    "veo": {"mode": "reference_controls", "status": "unregistered", "ready": false, "binding": "fallback_reference_group", "needs_action": "register_reference_controls"}
  },
  "lora_binding": {
    "status": "ready",
    "ready": true,
    "base_model": "flux",
    "model_path": "models/lora/wang.safetensors",
    "trigger": "wangdun_char",
    "model_hash": "sha256...",
    "validation_report": "设定库/lora/CHAR_WANG/常态/validation_report.json",
    "train_job": "设定库/lora/CHAR_WANG/常态/train_job.json"
  },
  "angle_policy": {},
  "drift_forbidden": ["face_shape", "hairstyle", "outfit_palette"],
  "gaps": [],
  "recommendations": []
}
```

`summary` 关键字段：`forms`、`forms_with_reference_group_ready`、`forms_with_native_image_ready`、`forms_with_native_video_ready`、`forms_with_lora_ready`、`forms_with_gaps`。
`forms_with_native_image_ready` 统计有「图后端原生角色ID/主体（非 reference_group 兜底）已 ready」的形态——阶段1 解除 Codex 垄断后，图也能走第②档原生主体（见下）。

允许的 `mode`（错 mode 由 `gate.py` 阻断）：

- **image**：`codex/openai` → `reference_group`；`seedream` → `universal_reference`；`kling` → `character_id / subject_library / custom_model / element_library`；`sora` → `character_cameo`。
- **video**：`dreamina` → `first_last_frame / reference_group`；`kling` → `character_id`；`seedance` → `face_lock`；`veo` → `reference_controls`。

`binding != "reference_group"` 且 `ready=true` 即算「原生身份已生效」；否则一律回退 `reference_group` 兜底，绝不阻塞出图/出视频。

LoRA ready 由 `n2d-lora` 生命周期写回。`model_path/base_model/trigger/model_hash/validation_report` 是 gate 必填字段；`validation_report` 必须是 `n2d_lora_validation_report` 且 `verdict=pass`，`model_hash` 必须与 `validation_report.model_sha256` 一致。若验证报告包含 `dataset_has_warnings`，必须同时写 `manual_review.allow_dataset_warnings=true` 和非空 `manual_review.notes`，说明为什么仍可用于生产；否则 adapter matrix 与生产 gate 都会判为未 ready。

## identity_drift_report.json

路径：

```text
制漫剧/<剧名>/生产数据/identity_drift_report.json
```

顶层：

```json
{
  "kind": "n2d_identity_drift_report",
  "version": 1,
  "root": "制漫剧/剧名",
  "generated_at": "2026-06-08T00:00:00Z",
  "available": true,
  "episodes": ["第1集", "第2集"],
  "characters": {
    "王敦": {
      "episodes": {
        "第1集": {"ok": 8, "warn": 1, "block": 0, "noface": 0},
        "第2集": {"ok": 4, "warn": 2, "block": 1, "noface": 0}
      },
      "first_bad_episode": "第2集",
      "total_warn": 3,
      "total_block": 1
    }
  },
  "notes": []
}
```

`available=false` 表示缺 insightface/cv2，机器脸相似度跳过；报表仍会输出 registry adapter matrix，跨集漂移暂交人判。
