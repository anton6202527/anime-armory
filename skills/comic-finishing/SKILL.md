---
name: comic-finishing
description: 漫画传统原稿收尾计划阶段。Use when planning manga lineart, ink, blacks, screentone, grayscale/value hierarchy, action/focus/speed lines, manga symbols, drawn SFX treatment, finish layers, or traditional manuscript aesthetics before comic-image. Triggers 原稿收尾, 传统收尾, 墨线, 黑场, 网点, 效果线, 集中线, 速度线, 漫符, drawn SFX, screentone, comic-finishing.
---

# comic-finishing — 原稿收尾计划

把传统漫画的完成稿手法结构化：草稿 → 铅笔 → 清线 → 墨线/黑场 → 网点/灰阶 → 效果线/漫符 → 拟声词融入画面 → 最终检查。它发生在 `comic-layout` 之后、`comic-image` 出图包之前，让逐格 prompt 能继承传统原稿审美，而不是只写“漫画风”。

## 输入

- `_设置.md`：基础视觉风格、出图稿层、网点策略、效果线策略。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`。
- 可选 `排版/第N话/name_board.json`。

## 输出

- `出图/第N话/finishing/finishing_plan.json`：schema 见 `references/finishing_schema.md`。
- `出图/第N话/finishing/finishing_plan.md`：人工可读收尾计划。
- `_进度.md`：完成后把 `原稿收尾` 标为 `✅`。

## 怎么跑

```bash
python3 skills/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话
```

## 工作流

1. 读取分格、layout 和 name board，确定每格的稿层、黑白灰价值、网点密度、效果线类型和拟声词处理。
2. 动作/冲击/揭示格加 `effects_plan`，但必须保留脸、手、道具和接触点可读。
3. 黑白/页漫优先显式 `tone_plan`；彩色条漫也要有 `value_plan`，避免只靠色相堆信息。
4. 拟声词只在需要时作为画面节奏元素处理；正文对白仍后期嵌字。
5. 输出 plan 后，`comic-image` 会把计划注入逐格 prompt/job 包。

## 原则

- “墨线/黑场/网点/效果线”是叙事工具，不是装饰滤镜。
- 黑场先决定视觉重心，网点再服务材质、空间深度和情绪。
- 速度线、集中线、冲击闪、漫符必须指向动作路径、视线焦点或情绪读点。
- 传统手法不能破坏一致性底线：脸、眼神目标、身体完整性、场景轴线和关键道具仍是硬约束。

## 不做什么

- 不直接改最终面板图。
- 不替代 `comic-image` 的真实出图。
- 不把对白正文烘焙进画面。
