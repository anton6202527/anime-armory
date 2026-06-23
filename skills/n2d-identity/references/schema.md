# n2d identity closure schema

`n2d-identity` 生成三类生产数据：adapter matrix、跨集脸漂报表（含 LoRA 升档建议）、音色跨集漂移报表。

## identity_adapter_matrix.json

路径：

```text
创作区/制漫剧/<剧名>/生产数据/identity_adapter_matrix.json
```

顶层：

```json
{
  "kind": "n2d_identity_adapter_matrix",
  "version": 1,
  "root": "创作区/制漫剧/剧名",
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
  "physical_scale": {
    "height_cm": 178,
    "body_type": "微胖",
    "relative_scale": "比沈念高半个头"
  },
  "expression_dna": {
    "joy": "眼角微弯，唇角上扬，眼神柔和",
    "anger": "眉心微蹙，下颌收紧，眼神藏锋冷峻",
    "sorrow": "低头垂眸，眼眶微红，神情落寞",
    "fear": "瞳孔微缩，呼吸略促，面部肌肉僵硬"
  },
  "performance_signature": {
    "micro_expressions": "先压住嘴角再抬眼，情绪外露前有半拍停顿",
    "habitual_gestures": ["说谎时拇指摩挲袖口", "压迫对手时微微侧身"],
    "posture": "肩背挺直，重心偏后，不抢步",
    "eye_behavior": "先扫对方手部再对视",
    "speech_rhythm": "短句、低音量、尾音收住"
  },
  "signature_equipment": ["WEAPON_01", "PROP_07"],
  "identity_marks": [
    {
      "mark_id": "MARK_左腕旧疤",
      "type": "疤痕",
      "region": "左腕",
      "side": "left",
      "color": "淡",
      "persistence": "permanent",
      "plot_load": true,
      "keywords": ["左腕旧疤", "左腕淡疤", "旧疤"]
    },
    {
      "mark_id": "MARK_觉醒金瞳",
      "type": "瞳色",
      "region": "双眼",
      "color": "金",
      "persistence": {"acquired_at": "第3集"},
      "plot_load": true,
      "keywords": ["金瞳", "金色瞳孔"]
    }
  ],
  "weathering_profile": {
    "base_state": "new",
    "evolution": [
      {"episode": "第10集", "state": "worn", "tags": "clothes slightly faded, fine dust on boots"}
    ]
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

`performance_signature` 是角色表演一致性层，记录微表情、惯用动作、站姿、眼神反应和说话节奏。production profile 下，核心/常驻角色缺该字段会被 `n2d-review` gate 阻断；临时配角可不填。

`identity_marks` 是辨识标记层，登记疤痕/胎记/纹身/瞳色/痣/义体等**载剧情**辨识标记（认亲胎记、战损疤、血统异瞳、禁术印记），由 `n2d-review` 的 `辨识标记(MK1)` 机检（`marks_consistency.py`，归入 `character_consistency` 评分维度）。每条字段：`type`（类型）、`region`（部位）、`side`（left/right/center，可选）、`color`（可选）、`persistence`（`"permanent"` 永久标记，或 `{"acquired_at":"第N集"}` 获得型标记）、`plot_load`（是否载剧情）、`keywords`（机检在 storyboard/出图 prompt 里搜的词；不填则从 type+region 等派生）。机检语义：永久/已获得标记未在某镜文本出现 → 🟡warn（疑似漂移/丢失，或合理遮挡，人核对）；未获得标记在获得集之前出现 → 🔴block（时间线穿帮）。这是**文本/结构**机检（查标记有没有写进分镜/出图 prompt），像素/VLM 在场核验（OWLv2/外观判官）是后续增强档。无 `identity_marks` 登记则该机检优雅跳过，不假报。

`signature_equipment` 是主角/核心动作角色的专属装备绑定层，引用 `asset_registry.json` 里的 `WEAPON_xx/PROP_xx/VFX_xx/OUTFIT_xx`。production profile 下，核心动作角色或显式 `combat_role/action_role/signature_equipment_expected=true` 的 form 缺该字段会被 `n2d-review` gate 阻断；`WEAPON_xx` 还必须在 `asset_registry` 中有 `weapon_profile`，用于锁武器审美、剪影尺度、材质色卡、携带方式、战斗用法和禁漂项。

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
创作区/制漫剧/<剧名>/生产数据/identity_drift_report.json
```

顶层：

```json
{
  "kind": "n2d_identity_drift_report",
  "version": 1,
  "root": "创作区/制漫剧/剧名",
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
      "total_block": 1,
      "recurrence": {
        "max_gap": 0,
        "long_gap_reentries": [],
        "high_risk": false
      }
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
      "next_command": "python3 skills/n2d-lora/scripts/lora.py init '创作区/制漫剧/剧名' --character-id CHAR_WANG --form '常态'"
    }
  ],
  "notes": []
}
```

`available=false` 表示缺 insightface/cv2，机器脸相似度跳过；报表仍会输出 registry adapter matrix，跨集漂移暂交人判。

每个角色还带 `recurrence`（跨集复现间隔）：`max_gap`=相邻两次出场之间缺席的最大集数，`long_gap_reentries[]`=缺席 ≥ `RECURRENCE_GAP_THRESHOLD`（默认 2）集后再登场的 `{at, prev, gap}` 列表，`high_risk`=是否存在长间隔再登场。依据 EntityBench(2026) 实证「跨镜一致性随复现间隔急剧衰退」——长间隔再登场是跨镜崩脸主因。`recurrence` 是**出场排期**事实而非像素度量，`available=false`（无 insightface）时仍计算。`n2d-image/scripts/face_drift_risk.py` 在出图前据此对「本集长间隔再登场」的角色加风险分并置顶重锚建议（喂质心定妆图/最强参考，核心角考虑升原生主体或 LoRA）。

`recommendations[]`（LoRA 升档自动建议）的产出条件——三条全满足才输出，否则空列表：

1. `available=true` 且该角色跨集漂移显著：warn/block 出现的集数 ≥2，或存在 `first_bad_episode`；
2. 角色能对回 registry（form.asset_key 精确命中 > character.name 精确命中）；
3. 该角色（命中 form）的 `identity_adapters.lora.status` 不是 `ready` / `training`。

消费方：`n2d-lora suggest` 直接打印；adapter matrix `summary.characters_needing_lora_upgrade` 取其 character_id 集合。

## identity_voice_drift_report.json

路径：

```text
创作区/制漫剧/<剧名>/生产数据/identity_voice_drift_report.json
```

由 `voice_consistency.py` 产出（`identity.py --write` 在存在配音时长清单时顺带跑）。输入：各集
`合成/第N集/配音/时长清单.json`（n2d-voice 逐句条目，音色键字段认契约 `voice_key`，兼容现行中文字段
`音色键`）与 `设定库/voicemap.json`（角色→音色注册表，路径取 `n2d_contract.voicemap_path`）。

顶层：

```json
{
  "kind": "n2d_identity_voice_drift_report",
  "version": 1,
  "root": "创作区/制漫剧/剧名",
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
创作区/制漫剧/<剧名>/生产数据/identity_voice_print_第N集.json
创作区/制漫剧/<剧名>/生产数据/consistency_findings_voice_print_第N集.json
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
