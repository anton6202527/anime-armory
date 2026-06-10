# 角色身份 Adapter Matrix

- root: 制漫剧/本宫才是这皇宫最大的妖
- generated_at: 2026-06-09T10:28:20+00:00

| 角色 | 形态 | reference_group | image native ready | video native ready | LoRA | gaps |
|---|---|---|---|---|---|---|
| 沈念 / 林婉儿 | 常态 | missing | - | - | not_needed | image.codex:reference_group_assets_missing, image.dreamina:reference_group_assets_missing, image.openai:reference_group_assets_missing, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, missing_reference:turnaround, video.dreamina:reference_group_assets_missing |
| 沈念 / 林婉儿 | 觉醒态 | missing | - | - | not_needed | image.codex:reference_group_assets_missing, image.dreamina:reference_group_assets_missing, image.openai:reference_group_assets_missing, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, missing_reference:turnaround, video.dreamina:reference_group_assets_missing |
| 小禾 | 惊慌护主 | missing | - | - | not_needed | image.codex:reference_group_assets_missing, image.dreamina:reference_group_assets_missing, image.openai:reference_group_assets_missing, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, missing_reference:turnaround, video.dreamina:reference_group_assets_missing |
| 柳娘子 | 人皮态 | missing | - | - | not_needed | image.codex:reference_group_assets_missing, image.dreamina:reference_group_assets_missing, image.openai:reference_group_assets_missing, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, missing_reference:turnaround, video.dreamina:reference_group_assets_missing |
| 柳娘子 | 破皮惊恐态 | missing | - | - | not_needed | image.codex:reference_group_assets_missing, image.dreamina:reference_group_assets_missing, image.openai:reference_group_assets_missing, missing_reference:back, missing_reference:front, missing_reference:outfit, missing_reference:side, missing_reference:turnaround, video.dreamina:reference_group_assets_missing |

## Recommendations

### 沈念 / 林婉儿 / 常态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- kling: register character_id for high-risk/core shots
- lora: core long-running character; consider LoRA only if reference_group/native adapters still drift
- seedance: register face_lock for high-risk/core shots
- seedream: register universal_reference for high-risk/core shots
- sora: register character_cameo for high-risk/core shots
- veo: register reference_controls for high-risk/core shots
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 沈念 / 林婉儿 / 觉醒态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- kling: register character_id for high-risk/core shots
- lora: core long-running character; consider LoRA only if reference_group/native adapters still drift
- seedance: register face_lock for high-risk/core shots
- seedream: register universal_reference for high-risk/core shots
- sora: register character_cameo for high-risk/core shots
- veo: register reference_controls for high-risk/core shots
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 小禾 / 惊慌护主
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- kling: register character_id for high-risk/core shots
- seedance: register face_lock for high-risk/core shots
- seedream: register universal_reference for high-risk/core shots
- sora: register character_cameo for high-risk/core shots
- veo: register reference_controls for high-risk/core shots
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 柳娘子 / 人皮态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- kling: register character_id for high-risk/core shots
- seedance: register face_lock for high-risk/core shots
- seedream: register universal_reference for high-risk/core shots
- sora: register character_cameo for high-risk/core shots
- veo: register reference_controls for high-risk/core shots
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

### 柳娘子 / 破皮惊恐态
- image: no ready native image subject; for multi-character/cross-episode drift register a subject library / Character Cameo (Seedream Universal Reference / Kling 主体库 / Sora Cameo) — otherwise reference_group fallback stays in effect
- kling: register character_id for high-risk/core shots
- seedance: register face_lock for high-risk/core shots
- seedream: register universal_reference for high-risk/core shots
- sora: register character_cameo for high-risk/core shots
- veo: register reference_controls for high-risk/core shots
- video: no ready native identity adapter; high-risk clips should use reference_group fallback or register Character ID/Face Lock/reference controls

