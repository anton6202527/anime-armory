# n2d identity closure schema

`n2d-identity` 生成三类生产数据：adapter matrix、跨集脸漂报表（含 LoRA 升档建议）、音色跨集漂移报表。

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

`summary` 关键字段：`forms`、`forms_with_reference_group_ready`、`forms_with_native_image_ready`、`forms_with_native_video_ready`、`forms_with_lora_ready`、`forms_with_gaps`、`characters_needing_lora_upgrade`。
`characters_needing_lora_upgrade` 是该升档 LoRA 的 character_id 列表，与 drift report 的 `recommendations` **同一判定**（漂移显著 + lora status 不是 ready/training）；构建 matrix 时没有 drift 数据（如 `--skip-face` 或机检不可用）则为空列表。
`forms_with_native_image_ready` 统计有「图后端原生角色ID/主体（非 reference_group 兜底）已 ready」的形态——阶段1 解除 Codex 垄断后，图也能走第②档原生主体（见下）。

允许的 `mode`（错 mode 由 `gate.py` 阻断）：

- **image**：`codex/openai` → `reference_group`；`dreamina/即梦` → `reference_group`；`seedream` → `universal_reference`；`kling` → `character_id / subject_library / custom_model / element_library`；`sora` → `character_cameo`。
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
  "recommendations": [
    {
      "type": "lora_upgrade",
      "character": "王敦",
      "character_id": "CHAR_WANG",
      "character_name": "王敦",
      "form": "常态",
      "lora_status": "candidate",
      "bad_episodes": ["第1集", "第2集"],
      "first_bad_episode": "第2集",
      "reason": "2 集脸部相似度低于阈值（第1集,第2集）；first_bad_episode=第2集（出现过 block 级漂移）；LoRA status=candidate，reference_group/原生主体未压住跨集漂移",
      "next_command": "python3 skills/n2d-lora/scripts/lora.py init '制漫剧/剧名' --character-id CHAR_WANG --form '常态'"
    }
  ],
  "notes": []
}
```

`available=false` 表示缺 insightface/cv2，机器脸相似度跳过；报表仍会输出 registry adapter matrix，跨集漂移暂交人判。

`recommendations[]`（LoRA 升档自动建议）的产出条件——三条全满足才输出，否则空列表：

1. `available=true` 且该角色跨集漂移显著：warn/block 出现的集数 ≥2，或存在 `first_bad_episode`；
2. 角色能对回 registry（form.asset_key 精确命中 > character.name 精确命中）；
3. 该角色（命中 form）的 `identity_adapters.lora.status` 不是 `ready` / `training`。

消费方：`n2d-lora suggest` 直接打印；adapter matrix `summary.characters_needing_lora_upgrade` 取其 character_id 集合。

## identity_voice_drift_report.json

路径：

```text
制漫剧/<剧名>/生产数据/identity_voice_drift_report.json
```

由 `voice_consistency.py` 产出（`identity.py --write` 在存在配音时长清单时顺带跑）。输入：各集
`合成/第N集/配音/时长清单.json`（n2d-voice 逐句条目，音色键字段认契约 `voice_key`，兼容现行中文字段
`音色键`）与 `设定库/voicemap.json`（角色→音色注册表，路径取 `n2d_contract.voicemap_path`）。

顶层：

```json
{
  "kind": "n2d_identity_voice_drift_report",
  "version": 1,
  "root": "制漫剧/剧名",
  "generated_at": "2026-06-10T00:00:00Z",
  "episodes": [
    {"episode": "第1集", "manifest": "合成/第1集/配音/时长清单.json", "status": "ok", "lines": 16,
     "characters": {"沈念": ["SHEN"], "旁白": ["NARR"]}}
  ],
  "drifts": [
    {
      "character": "沈念",
      "episode_from": "第1集",
      "episode_to": "第2集",
      "voice_from": "SHEN",
      "voice_to": "SHEN_NEW",
      "first_affected_line_idx": 1,
      "return_to_stage": "voice",
      "affected_shots": ["镜头2", "镜头3"],
      "scope": "第2集 角色「沈念」音色由 SHEN 漂为 SHEN_NEW：该集此角色共 2 句需按注册音色重配（n2d-voice），重配后时长清单变化需复核分镜时长（n2d-script 阶段2）"
    }
  ],
  "voicemap_mismatches": [
    {
      "character": "沈念",
      "episode": "第1集",
      "voice_key_used": "SHEN_X",
      "voice_key_registered": "SHEN",
      "first_affected_line_idx": 0,
      "return_to_stage": "voice",
      "affected_shots": ["镜头1"],
      "scope": "第1集 角色「沈念」实际使用音色 SHEN_X 与 voicemap 注册的 SHEN 不符：共 1 句需按注册音色重配（n2d-voice）"
    }
  ],
  "summary": {"episodes_total": 2, "episodes_checked": 2, "episodes_insufficient": 0, "drifts": 1, "voicemap_mismatches": 1},
  "notes": []
}
```

约定：

- 集状态 `ok / insufficient_data / invalid`：任何带角色的逐句条目缺音色键字段 → 整集 `insufficient_data`，
  跳过比对（**不报假漂移**）；`invalid` 表示清单不是 JSON 数组。
- `drifts` 覆盖两种情况：跨集换键（`episode_from != episode_to`，与上一可检集比）和同集内换键
  （`episode_from == episode_to`）。
- `voicemap.json` 缺失/不可解析 → 写入 `notes` 并跳过对账；角色未登记 → `notes` 里
  `voicemap_unregistered:<角色>`，不算 mismatch。
- 每条 drift/mismatch 的 `return_to_stage/affected_shots/scope` 是给 n2d-batch 的回流建议：回 `voice`
  阶段只重配受影响角色/集，重配后需复核分镜时长（时长清单驱动镜头时长）。

## identity_voice_print_第N集.json

路径：

```text
制漫剧/<剧名>/生产数据/identity_voice_print_第N集.json
制漫剧/<剧名>/生产数据/consistency_findings_voice_print_第N集.json
```

由 `voice_print_consistency.py` 产出（`identity.py --write` 在存在配音时长清单时逐集顺带跑）。
前者是声纹原始报告，后者是统一回流报告，`kind=n2d_consistency_findings`，维度键 `voice_consistency`。

原始报告顶层：

```json
{
  "kind": "n2d_identity_voice_print_report",
  "episode": "第1集",
  "manifest": "合成/第1集/配音/时长清单.json",
  "available": true,
  "mode": "resemblyzer",
  "precision": "ok",
  "groups": {
    "沈念|SHEN": {
      "floor": 0.72,
      "floor_calibrated": true,
      "lines": [{"idx": 0, "score": 0.91, "band": "ok"}],
      "drift_count": 0
    }
  },
  "total_drift": 0
}
```

约定：

- 缺 resemblyzer/speechbrain 或无可用逐句 wav 时写 `available=false`、`precision=insufficient_precision`，
  交还人判，不输出假相似度。
- `consistency_findings_voice_print_第N集.json` 只把 `band=bad/warn` 的组外发为 finding，
  `return_to_stage=voice`，供 `n2d-score`、`n2d-feedback`、`n2d-batch --from-consistency-findings` 统一消费。
