# 出图后端矩阵（ad-image · 本线自持）

`生图AI` 默认 Codex；放行官方多参考一致性后端。判定逻辑 `ad-craft/scripts/contract.py` `classify_image_backend`。

| 后端 | 多参考 | 原生主体ID | 广告适配 |
|---|---|---|---|
| Codex / OpenAI gpt-image | ✗ | ✗ | 默认；单参考，产品锚定靠强 prompt + 参考图 |
| Nano Banana / Gemini | ✓ | ✗ | 多参考锁角色/产品，原生 SynthID 标识 |
| Seedream Universal Reference | ✓ | ✓ | 免 LoRA 跨图锁主体（≤14 图），**产品/代言人一致性最稳** |
| 可灵 Kling 主体库 / Element Library | ✓ | ✓ | 注册产品/代言人为主体，按 ID 复用 |
| Sora Character Cameo | ✓ | ✓ | 可复用主体 ID |

## 两条硬闸门

1. **项目内不混用后端**——一个 `拍广告/<项目>/` 锁一个生图后端；切换记录到 `_设置.md` 并重出受影响图。
2. **禁第三方逆向/未授权出图**——即梦/Dreamina 逆向路径 `forbidden`（官方 API 不在此列）。

## 广告一致性建议

- **产品/logo/代言人** = 最严，优先用**多参考 + 原生主体库**（Seedream/可灵）或多参考后端，单参考后端（Codex）靠强锚点 + 身份锁定句。
- **品牌色**：逐镜 prompt 带主色 HEX，避免环境光染偏。
- **关键 logo/包装文字镜**：AI 文字不稳 → 出图占位，`ad-compose` 用真 logo/包装贴图合成最稳。
- **多比例**：按 `交付比例` 主比例出图，其它比例 `ad-compose` reframe；构图留 title-safe / action-safe 余量，别贴边。
