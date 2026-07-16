# 角色身份 Adapter Matrix

- root: 创作区/制漫剧/仙界闭关小能手
- generated_at: 2026-07-15T17:00:17+00:00
- anchor_fingerprint: `562dc15d314a3d72…`（锚点版本快照·4 form 已钉死；指纹变=锚点被改，跨集继承换脸风险）

| 角色 | 形态 | reference_group | image native ready | video native ready | LoRA | gaps |
|---|---|---|---|---|---|---|
| 贺平生 | 本集为14岁杂役常态 | ready | codex:image2image_reference_chain, seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |
| 张老大 | 常态 | ready | seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |
| 杂役背景组 | 常态 | ready | seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |
| 韩老三 | 常态 | ready | seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |

## Recommendations

### 贺平生 / 本集为14岁杂役常态
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 张老大 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 杂役背景组 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 韩老三 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

