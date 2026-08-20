# 出图后端矩阵（ad-image · 本线自持）

新项目分列 `生图模型` 与 `生图渠道`：默认 `GPT Image 2` via `Codex CLI`（或官方 OpenAI Images API）。非默认具体模型只作为用户明确签核的单项目例外；签核文件为 `<作品根>/合规/image_backend_override.json`。旧 `生图AI` 仅供迁移，不得进入正式付费 job。

| 后端 | 多参考 | 原生主体ID | 广告适配 |
|---|---|---|---|
| Codex / OpenAI gpt-image | ✗ | ✗ | 默认；单参考，产品锚定靠强 prompt + 参考图 |
| Nano Banana / Gemini | ✓ | ✗ | 多参考锁角色/产品，原生 SynthID 标识 |
| Seedream Universal Reference | ✓ | ✓ | 免 LoRA 跨图锁主体（≤14 图），**产品/代言人一致性最稳** |
| 可灵 Kling 主体库 / Element Library | ✓ | ✓ | 注册产品/代言人为主体，按 ID 复用 |
| Sora Character Cameo | ✓ | ✓ | 可复用主体 ID |
| Dreamina/即梦官方 CLI/API | ✗ | ✗ | 不作默认/自动选择；仅签核例外。视频阶段走 Dreamina 不代表图片也用 Dreamina |

## 两条硬闸门

1. **Codex image2 优先**——无签核时只走 Codex/OpenAI 生图；非 Codex/OpenAI 必须有 `<作品根>/合规/image_backend_override.json`。
2. **项目内不混用后端**——一个 `创作区/拍广告/<项目>/` 锁一个生图后端；切换记录到 `_设置.md` 并重出受影响图。
3. **禁第三方逆向/未授权出图**——即梦/Dreamina 逆向路径 `forbidden`；官方 Dreamina 图片路径也只作签核例外。

## 广告一致性建议

- **产品/logo/代言人** = 最严，优先用**多参考 + 原生主体库**（Seedream/可灵）或多参考后端，单参考后端（Codex）靠强锚点 + 身份锁定句。
- **品牌色**：逐镜 prompt 带主色 HEX，避免环境光染偏。
- **关键 logo/包装文字镜**：AI 文字不稳 → 出图占位，`ad-compose` 用真 logo/包装贴图合成最稳。
- **多版位**：主比例出图后由 `ad-craft/scripts/placement_adaptation.py` 逐交付件选择原生构图、原生重剪/重做或经签核的机械裁切；不能把统一 reframe 当默认。前期仍留 title-safe / action-safe 余量，但中心网格不替代具体版位模板。
