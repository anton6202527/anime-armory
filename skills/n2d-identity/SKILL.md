---
name: n2d-identity
description: 横切角色身份闭环层：把 n2d 的 identity_registry.json 和 reference group、Face Lock、Character ID、reference controls、LoRA 真正打通，生成后端 adapter matrix，并输出跨集角色漂移报表。Use when asked about 角色身份闭环, identity_registry, Face Lock, Character ID, LoRA, reference group, 跨集漂移报表, 角色一致性报表.
---

# n2d-identity — 角色身份闭环

你是 **n2d 角色身份资产管理员**。你的目标是把“定妆图 + 锚点句”升级为可调度、可审查、可回流的身份闭环：

1. `identity_registry.json` 是角色/形态机器真值。
2. reference group 是所有后端的兜底身份资产。
3. Face Lock / Character ID / reference controls 是后端原生身份适配。
4. LoRA 是重资产增强层，只给核心长线角色。
5. 跨集漂移必须有报表，不靠人脑记“第几集开始不像”。

## 触发

- 用户说：角色身份闭环、identity_registry、Face Lock、Character ID、LoRA、reference group、跨集漂移报表。
- 出图前/出视频前需要确认角色身份资产是否齐。
- 审片发现跨集脸漂、服装漂、后端身份未生效、LoRA 假 ready。
- 批量跑多集前需要生成身份 adapter matrix。

## 核心规则

- **一份 registry，多端消费**：n2d-image 取 `reference_group` / 图后端角色 ID；n2d-video 取 `Character ID / Face Lock / reference controls`；n2d-review 取 `drift_forbidden` 和跨集漂移报表。不要在 prompt 现场手写临时 ID。
- **reference group 永远是兜底**：任何后端未注册、无权限、生成失败时，都退回 front/side/back/outfit/turnaround + 锚点句 + 首尾帧。
- **ready 不能空登记**：`registered/ready` 必须写真实 `id/handle/reference/model_path`；LoRA `ready` 必须写 `base_model/model_path/trigger/model_hash/validation_report`，且验证报告必须 `verdict=pass`。若报告含 `dataset_has_warnings`，只能在 `manual_review.allow_dataset_warnings=true` 且 `manual_review.notes` 写明原因时放行。
- **后端 mode 要匹配能力**：Kling video 用 `character_id`，Seedance 用 `face_lock`，Veo 用 `reference_controls`，Dreamina 用 `first_last_frame` 或 `reference_group`；错 mode 由 gate 阻断。
- **跨集漂移要回源头**：报表发现某角色从第 N 集开始大量 🔴/🟡，先查该集是否换定妆、混后端、缺 adapter、用了高危角度或 reference group 缺图，再只重跑受影响镜头。

## 工作流

### 1. 生成身份闭环报表

```bash
python3 skills/n2d-identity/scripts/identity.py <作品根> --write
```

输出：

- `生产数据/identity_adapter_matrix.json`
- `生产数据/identity_adapter_matrix.md`
- `生产数据/identity_drift_report.json`
- `生产数据/identity_drift_report.md`

字段见 `references/schema.md`。

### 2. 出图阶段怎么用

- 生成/补共享定妆时，同步更新 `出图/共享/identity_registry.json`。
- 分镜 prompt 只从 registry 取 reference group 和 drift_forbidden，不临场猜参考图。
- **图后端原生主体（阶段1 起一等公民）**：`生图AI` 解除 Codex 垄断后，图侧也能走第②档——`identity_adapters.image` 支持 `seedream→universal_reference`、`kling→subject_library/character_id`、`sora→character_cameo`。注册一次按 ID 引用，`identity_adapter_matrix` 的 `image native ready` 列与 `summary.forms_with_native_image_ready` 会统计它。Codex/OpenAI 无持久主体，自动回退 reference_group 兜底。
- 若多角色同框或核心角色跨集漂，优先补图/视频后端原生角色 ID / 主体库；仍不稳才提 LoRA。注意：图后端整集统一一个，混用会被 image gate 拦。

### 3. 出视频阶段怎么用

- 先跑 `n2d-identity`，再跑 `n2d-model-router` / `n2d-video`。
- 每个含角色 Clip 的 `角色身份注册层` 字段必须引用 adapter matrix：
  - Kling ready：写 Character ID / handle。
  - Seedance ready：写 Face Lock reference / id。
  - Veo ready：写 reference controls。
  - Dreamina / 未注册：写 first/last frame + reference_group fallback。
- 高危镜头（极暗、人物太小、极端角度、多人接触）若 primary 后端未 ready，优先登记为注册候选或拆镜。

### 4. 审片阶段怎么用

- 跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --episodes 1-10 --write`。
- `--episodes` 复用公共集数解析，支持 `1-10`、`一-三`、`第２集,第三集` 等中文/全角写法。
- `--write` 写出的 JSON/Markdown 使用同盘 temp + `os.replace` 原子落盘，gate/progress 同时读取时不会看到半截文件。
- `identity_drift_report.md` 会按角色/集统计 `ok/warn/block/noface`，列出 `first_bad_episode`。
- 有 🔴：回 `n2d-image` 重出受影响镜头；若同一角色多集反复 🔴，回共享定妆/registry/adapter 注册层，不要只重抽单图。

## 和其它 skill 的关系

- `n2d-image`：生产 reference group 和 registry。
- `n2d-asset-market`：跨项目导入/导出 registry 片段和定妆组；导入角色后本 skill 必须重建 adapter matrix，且默认不要沿用旧项目的 Character ID / Face Lock / LoRA ready 状态。
- `n2d-lora`：管理 LoRA 数据集、训练任务、验证报告和 registry ready 回写；本 skill 只消费其写好的 lora binding 并检查 fake ready。
- `n2d-video`：消费 adapter matrix 写平台参数。
- `n2d-review`：gate registry，审跨集漂移。
- `n2d-batch`：用 drift report 只重排受影响角色/集/镜头。
- `n2d-dashboard`：记录身份注册、漂移、重抽原因。
