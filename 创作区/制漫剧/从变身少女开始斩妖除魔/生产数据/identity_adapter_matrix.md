# 角色身份 Adapter Matrix

- root: 创作区/制漫剧/从变身少女开始斩妖除魔
- generated_at: 2026-06-29T06:03:07+00:00
- anchor_fingerprint: `f89db7978efed21e…`（锚点版本快照·0 form 已钉死；指纹变=锚点被改，跨集继承换脸风险）

| 角色 | 形态 | reference_group | image native ready | video native ready | LoRA | gaps |
|---|---|---|---|---|---|---|
| 姜月初 | 战场形态 | ready | - | - | not_needed | - |
| 姜月初 | 觉醒蓝调母本 | ready | - | - | not_needed | - |
| 年轻校尉 | 断臂校尉 | ready | - | - | not_needed | - |
| 大唐皇帝 | 朝堂常态 | ready | - | - | not_needed | - |
| 程老 | 朝堂常态 | ready | - | - | not_needed | - |
| 朝堂群臣 | 群臣剪影 | missing | - | - | not_needed | image.codex:unknown_status:restricted_partial, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, video.dreamina:unknown_status:restricted_partial |
| 巴西郡残兵 | 残兵剪影 | missing | - | - | not_needed | image.codex:unknown_status:restricted_partial, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, video.dreamina:unknown_status:restricted_partial |

## Recommendations

### 姜月初 / 战场形态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- lora: core long-running character; consider LoRA only if reference_group/native adapters still drift
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 姜月初 / 觉醒蓝调母本
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- lora: core long-running character; consider LoRA only if reference_group/native adapters still drift
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 年轻校尉 / 断臂校尉
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 大唐皇帝 / 朝堂常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 程老 / 朝堂常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 朝堂群臣 / 群臣剪影
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 巴西郡残兵 / 残兵剪影
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

