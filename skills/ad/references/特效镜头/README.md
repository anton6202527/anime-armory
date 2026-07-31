# 特效镜头参考库（signature shots）· ad 线

本目录是 ad 线出视频的**命名特效镜头**索引，与 [`../运镜/`](../运镜/) 平行但互补：

- **运镜** = 相机轨迹原语（推/拉/摇/移/环绕/穿越…），回答"镜头怎么动"。
- **特效镜头** = 命名的**复合镜头模板**（产品扫光 / 液体飞溅 / 悬浮缓入 / 玻璃破碎定格 / 普拉达换装 / 移轴微缩…），把「运镜 + 主体动作 + 特效 + 时基」打包成一条可直接粘贴的核心 prompt。

机器可读真值源是 [`manifest.json`](manifest.json)：48 条特效各带中文名、英文名、别名、category、回链运镜（`camera_move` → 运镜 `lexicon_key`）、主体动作/特效/时基、**中英双语核心 prompt**、negatives 列表、身份风险级、平台命名模板与来源。纯离线 prompt 索引，不含视觉参考媒体。

广告最常用：`product_commercial`（产品扫光/液体飞溅/悬浮缓入/产品分解组装/香水雾化）、`macro_intimate`（微距推镜/化妆品涂抹）、`transformation`（普拉达换装/试装/换脸）、`scale_world`（移轴微缩）、`action_impact`（玻璃破碎定格）。其余仙侠/科幻等类目按需取用（如游戏/影视广告）。

## 与代码的接线（主动接入）

- 检测模块：`skills/ad/_lib/signature_effects.py`——启动时从本 manifest 构建 `SIGNATURE_EFFECT_LEXICON` 与 `HIGH_IDENTITY_RISK_EFFECTS`，提供 `signature_effect_directive(text)`。
- 视频落地：`skills/ad/ad-video/scripts/plan_prompts.py`——每个镜头若在运镜/动作/描述里点名某特效，自动在 prompt 的"运镜与动作"段暴露该核心 prompt，并对 `identity_risk=high` 的特效（换装/换脸/化妆品涂抹等）**自动把该特效 negatives + 身份锁负向词并入 `negative_elements`**（进而进入编译后的 `negative_prompt`）。
- 也可在镜头对象上显式写 `signature_effect` 字段点名。

```bash
python3 skills/ad/scripts/effect_reference.py list
python3 skills/ad/scripts/effect_reference.py list --category product_commercial
python3 skills/ad/scripts/effect_reference.py show 产品扫光 --json
python3 skills/ad/scripts/effect_reference.py self-check
```

## 使用原则

- 特效核心 prompt 已含 `速度/方向/起止/时基`；落地时补**产品/品牌身份锚**与**场景锚**，勿丢结构化字段与安全区/文字规则。
- **身份高风险特效**（换装/换脸/化妆品涂抹近脸/名场面等）：形变必须是**有意声明**、只在指定转场点发生；plan_prompts 命中即拼身份锁负向词。**换装/换脸类不得用于假冒真实人物或明星脸。**
- 平台命名模板（可灵/即梦/Higgsfield/Runway/Pika 等）仅作口径参考；提交仍以本库结构化核心 prompt 为准，并遵守广告合规与 safe-zone。

## 来源

48 条特效基于对 2025–2026 主流 AI 视频平台命名模板与提示实践的实时检索整理；逐条 `platform_refs` 与 `sources` 见 `manifest.json`；部分为社区俗称、无官方同名卡时以电影摄影通行做法为准。
