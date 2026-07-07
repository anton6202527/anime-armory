# 角色身份 Adapter Matrix

- root: 创作区/制漫剧/那妖魔是姜大人
- generated_at: 2026-07-07T11:35:19+00:00
- anchor_fingerprint: `6f05ff9c0259449c…`（锚点版本快照·6 form 已钉死；指纹变=锚点被改，跨集继承换脸风险）

| 角色 | 形态 | reference_group | image native ready | video native ready | LoRA | gaps |
|---|---|---|---|---|---|---|
| 姜月初 | 囚犯初醒态 | ready | codex:image2image_reference_chain, dreamina:image2image_reference_chain, kling:fallback_reference_group, openai:image2image_reference_chain, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | abandoned | - |
| 姜月初 | 镇魔司伪装态 | ready | codex:image2image_reference_chain, dreamina:image2image_reference_chain, kling:fallback_reference_group, openai:image2image_reference_chain, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | abandoned | - |
| 陈青源 | 常态 | ready | kling:fallback_reference_group, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | not_needed | - |
| GROUP_飞鹰门众人 | 常态 | ready | kling:fallback_reference_group, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | not_needed | - |
| GROUP_狼妖群 | 常态 | ready | kling:fallback_reference_group, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | not_needed | - |
| 青面郎君 | 常态 | ready | kling:fallback_reference_group, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | not_needed | - |
| 虎山神 / 虎妖 | 诈死复苏态 | ready | kling:fallback_reference_group, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | not_needed | - |
| 裴长青 | 濒死战损态 | ready | kling:fallback_reference_group, seedream:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, sora:fallback_reference_group, veo:fallback_reference_group | not_needed | - |

## Recommendations

### 姜月初 / 囚犯初醒态
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 姜月初 / 镇魔司伪装态
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 陈青源 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### GROUP_飞鹰门众人 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### GROUP_狼妖群 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 青面郎君 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 虎山神 / 虎妖 / 诈死复苏态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 裴长青 / 濒死战损态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

