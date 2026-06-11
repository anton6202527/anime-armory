---
name: n2d-identity
description: 横切角色身份闭环层：把 n2d 的 identity_registry.json 和 reference group、Face Lock、Character ID、reference controls、LoRA 真正打通，生成后端 adapter matrix，输出跨集角色漂移报表（含 LoRA 升档自动建议），并对账配音时长清单×voicemap 产出音色跨集漂移报表。Use when asked about 角色身份闭环, identity_registry, Face Lock, Character ID, LoRA, reference group, 跨集漂移报表, 角色一致性报表, 音色漂移, 音色一致性, LoRA 升档建议.
---

# n2d-identity — 角色身份闭环

你是 **n2d 角色身份资产管理员**。你的目标是把“定妆图 + 锚点句”升级为可调度、可审查、可回流的身份闭环：

1. `identity_registry.json` 是角色/形态机器真值。
2. reference group 是所有后端的兜底身份资产。
3. Face Lock / Character ID / reference controls 是后端原生身份适配。
4. LoRA 是重资产增强层，只给核心长线角色；何时升档由漂移报表的 `recommendations` 工程化判定，不靠拍脑袋。
5. 跨集漂移必须有报表，不靠人脑记“第几集开始不像”。
6. 音色也是身份：一角一色、跨集持久。配音 manifest 的 voice_key × voicemap 注册表对账出 `voice_drift_report`。

## 触发

- 用户说：角色身份闭环、identity_registry、Face Lock、Character ID、LoRA、reference group、跨集漂移报表。
- 出图前/出视频前需要确认角色身份资产是否齐。
- 审片发现跨集脸漂、服装漂、后端身份未生效、LoRA 假 ready。
- 批量跑多集前需要生成身份 adapter matrix。

## 输入 / 输出 / 读写边界

- **输入**：`identity_registry.json`、reference group、后端 adapter 状态、LoRA 绑定、配音时长清单、voicemap、声纹机检依赖。
- **输出**：`identity_adapter_matrix.json/md`、`identity_drift_report.json/md`、音色/声纹 drift 报表和 batch 可消费 findings。
- **读写边界**：只读 registry 并写报表；不写 registry 本体、不训练 LoRA、不重配音、不重出图。
- **契约关系**：registry owner/path、adapter status、LoRA ready 阻断、voice finding kind 都来自 `skills/common/n2d_contract.py`。

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

- `生产数据/identity_adapter_matrix.json`（`summary.characters_needing_lora_upgrade` 列出该升档 LoRA 的角色 id）
- `生产数据/identity_adapter_matrix.md`
- `生产数据/identity_drift_report.json`（`recommendations[]` 为 LoRA 升档自动建议，带 character_id/理由/下一步命令）
- `生产数据/identity_drift_report.md`
- 若存在配音时长清单（`合成/第N集/配音/时长清单.json`），`--write` 还会顺带跑音色对账，输出
  `生产数据/identity_voice_drift_report.json` + `.md`（也可单独跑：
  `python3 skills/n2d-identity/scripts/voice_consistency.py <作品根> --write`）。
- 同时逐集跑声纹机检 `voice_print_consistency.py`，输出
  `生产数据/identity_voice_print_第N集.json`，并外发
  `生产数据/consistency_findings_voice_print_第N集.json`
  （kind=`n2d_consistency_findings`，维度 `voice_consistency`，可直接交给 `n2d-batch --from-consistency-findings`）。

字段见 `references/schema.md`。

### 1b. LoRA 升档自动建议（工程化触发）

「要不要上 LoRA」不再靠人判：drift report 里某角色 **跨集漂移显著**（warn/block 出现的集数 ≥2，或存在
`first_bad_episode`）且其 `identity_adapters.lora.status` 不是 `ready/training` 时，
`recommendations[]` 自动产出一条 `type=lora_upgrade` 建议（character_id、理由、
`next_command` 直接给出 `python3 skills/n2d-lora/scripts/lora.py init ...`）。同一判定同步进
adapter matrix 的 `summary.characters_needing_lora_upgrade`。机检不可用（`available=false`）或
角色对不上 registry 时给空列表，不瞎编。`n2d-lora` 的 `suggest` 子命令消费这份建议。

### 1c. 音色跨集漂移对账（voice_consistency）

「一角一色、跨集持久」：逐句配音条目的 voice_key（契约 `voice_key`，兼容 n2d-voice 现行中文字段
`音色键`）做两类对账——① 同一角色跨集（含同集内）voice_key 变化 → drift；② 实际使用键与
`设定库/voicemap.json` 注册键不符 → voicemap_mismatch。逐句条目缺音色键字段的集标
`insufficient_data` 并跳过比对（宁缺勿假）。每条 drift/mismatch 带 batch 回流建议
（`return_to_stage="voice"`、`affected_shots`、`scope`），供 n2d-batch 只重配受影响角色/集；
重配后时长清单变化，需复核 n2d-script 阶段2 的分镜时长。

### 1d. 声纹实际漂移（voice_print_consistency）

`voice_consistency.py` 只对账 `voice_key` 字符串；`voice_print_consistency.py` 量逐句 wav 的 speaker embedding，
补“键写对但后端实际克隆音色漂了”的盲区。缺 resemblyzer/speechbrain 时只写
`available=false / insufficient_precision`，交还人判，不输出假相似度。发现漂移时外发
`consistency_findings_voice_print_第N集.json`，统一进入 score/batch/feedback 的一致性通道。

### 2. 出图阶段怎么用

- 生成/补共享定妆时，由 **n2d-image（唯一写方）** 同步更新 `出图/共享/identity_registry.json`；n2d-identity 只读校验、写报表，不写 registry 本体（owner 见 `n2d_contract.PRODUCT_KINDS`：n2d-image 写 / n2d-identity·n2d-review 读校）。
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
- `identity_drift_report.md` 会按角色/集统计 `ok/warn/block/noface`，列出 `first_bad_episode`，末尾附「LoRA 升档建议」。
- 有 🔴：回 `n2d-image` 重出受影响镜头；若同一角色多集反复 🔴，回共享定妆/registry/adapter 注册层，不要只重抽单图；`recommendations` 已给出是否该升档 LoRA 及下一步命令。
- `identity_voice_drift_report.md` 列出音色漂移/对账不符及回流范围；有 drift 回 `n2d-voice` 按注册音色重配。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 跨项目直接拷贝旧 Face Lock | 导入角色后本 skill 必须重建 adapter matrix，且默认不应沿用旧项目的已废弃/无关 ID |
| 未跑 `identity.py --write` 就出视频 | adapter matrix 不会自己刷新，会导致 n2d-model-router 或出图 prompt 使用过期的配置 |
| 把 prompt 里的外貌描写当成身份基准 | 必须从 registry 获取 reference group，避免每次用 LLM 自由发挥外貌 |
| 对跨集漂移不做记录，靠人脑记 | 必须通过本 skill 生成 drift report，让机器统计从哪一集开始崩 |

## 和其它 skill 的关系

- `n2d-image`：生产 reference group 和 registry。
- `n2d-asset-market`：跨项目导入/导出 registry 片段和定妆组；导入角色后本 skill 必须重建 adapter matrix，且默认不要沿用旧项目的 Character ID / Face Lock / LoRA ready 状态。
- `n2d-lora`：管理 LoRA 数据集、训练任务、验证报告和 registry ready 回写；本 skill 只消费其写好的 lora binding 并检查 fake ready，同时通过 drift report `recommendations` 工程化触发其 `suggest`/`init` 升档入口。
- `n2d-voice`：写 voicemap.json 和逐句时长清单（含音色键）；本 skill 对账产出 voice_drift_report，drift 回流 n2d-voice 重配。
- `n2d-video`：消费 adapter matrix 写平台参数。
- `n2d-review`：gate registry，审跨集漂移。
- `n2d-batch`：用 drift report 只重排受影响角色/集/镜头。
- `n2d-dashboard`：记录身份注册、漂移、重抽原因。
