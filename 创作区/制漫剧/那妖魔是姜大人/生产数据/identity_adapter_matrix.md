# 角色身份 Adapter Matrix

- root: 创作区/制漫剧/那妖魔是姜大人
- generated_at: 2026-07-02T12:19:11+00:00
- anchor_fingerprint: `172d2414f27bbdb6…`（锚点版本快照·0 form 已钉死；指纹变=锚点被改，跨集继承换脸风险）

| 角色 | 形态 | reference_group | image native ready | video native ready | LoRA | gaps |
|---|---|---|---|---|---|---|
| 姜月初 | 囚犯初醒态 | ready | seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |
| 裴长青 | 濒死战损态 | ready | seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |
| 虎山神 / 虎妖 | 诈死复苏态 | ready | seedream:fallback_reference_group, kling:fallback_reference_group, sora:fallback_reference_group | kling:fallback_reference_group, seedance:fallback_reference_group, veo:fallback_reference_group, sora:fallback_reference_group | not_needed | - |

## Recommendations

### 姜月初 / 囚犯初醒态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 裴长青 / 濒死战损态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 虎山神 / 虎妖 / 诈死复苏态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

