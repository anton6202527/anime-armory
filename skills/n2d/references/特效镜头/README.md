# 特效镜头参考库（signature shots）

本目录是 n2d 线出视频的**命名特效镜头**索引，与 [`../运镜/`](../运镜/README.md) 平行但互补：

- **运镜** = 相机轨迹原语（推/拉/摇/移/环绕/穿越…），回答"镜头怎么动"。
- **特效镜头** = 命名的**复合镜头模板**（穿云而入 / 子弹时间 / 产品扫光 / 普拉达换装 / 深海巨兽…），把「运镜 + 主体动作 + 特效 + 时基」打包成一条可直接粘贴的核心 prompt，回答"这个招牌镜头整套怎么拍"。

机器可读真值源是 [`manifest.json`](manifest.json)：25 条特效各带中文名、英文名、别名、category、回链运镜（`camera_move` → 运镜 `lexicon_key`）、主体动作/特效/时基、**中英双语核心 prompt**、negatives 列表、身份风险级、平台命名模板与来源。与运镜库不同，特效库是**纯离线 prompt 索引，不含视觉参考媒体**。

## 与代码的接线（主动接入，非死文件）

- 活词典：`skills/n2d/_lib/n2d_const.py::SIGNATURE_EFFECT_LEXICON`，启动时从本 manifest 构建；`HIGH_IDENTITY_RISK_EFFECTS` 汇总高身份风险特效。
- 归一化：`skills/n2d/_lib/n2d_logic.py::normalize_signature_effect()`——把分镜/运镜自由文本里出现的特效名归一到本库。
- 视频落地：`skills/n2d/n2d-video/scripts/prompt_pack.py::signature_effect_directive()`——每个 Clip 若在运镜/描述里点名某特效，自动在 Clip 块暴露该特效的可粘贴核心 prompt，并对 `identity_risk=high` 的特效（换装/换脸/名场面/近脸升格/对打/化鸟）**自动把该特效 negatives + 身份锁负向词并入本镜提交负向 prompt**。

```bash
python3 skills/n2d/scripts/effect_reference.py list
python3 skills/n2d/scripts/effect_reference.py list --category action_impact
python3 skills/n2d/scripts/effect_reference.py show 子弹时间 --json
python3 skills/n2d/scripts/effect_reference.py self-check
```

## 使用原则

- 特效核心 prompt 已含 `速度/方向/起止/时基`；落地到具体镜时补**主体身份锚**与**场景锚**，勿丢结构化字段。
- 一个 Clip 一般只用一种主特效；特效服务本镜功能，不与运镜结构化字段冲突（`camera_move` 已回链）。
- **身份高风险特效**（换装/换脸/名场面/近脸升格KO/双人对打/飞鸟解体/地球缩放落地锁脸）：形变必须是**有意声明**的，只在指定转场点发生；prompt_pack 命中即拼身份锁负向词。**换装/换脸类不得用于假冒真实人物。**
- 平台命名模板（可灵/即梦/Higgsfield/PixVerse/Runway/Pika 等）仅作口径参考；真正提交仍以本库结构化核心 prompt 为准。

## 特效索引（48 条，按 category）

**第一批 25（飞行/宇宙/引力/商业/变身/微距/动作/时间/生物/载具/光彩/水下）**

| 中文名 | 英文名 | category | 回链运镜 | 身份风险 |
|---|---|---|---|---|
| 穿云而入 | cloud-break reveal | flight_aerial | 穿越运镜 | medium |
| 飞跃地平线 | horizon soar | flight_aerial | 无人机航拍 | low |
| 俯冲地球 | orbital dive | flight_aerial | 穿越运镜 | low |
| 地球缩放 | earth zoom in | cosmic_scale | 推镜头 | high |
| 环球缩放 | earth zoom out | cosmic_scale | 拉镜头 | medium |
| 逆转引力 | reverse gravity | gravity_surreal | 升降 | medium |
| 产品扫光 | product light-sweep | product_commercial | 推镜头 | low |
| 试装特写 | outfit try-on closeup | product_commercial | 移镜头 | medium |
| 悬浮缓入 | levitation push-in | product_commercial | 推镜头 | low |
| 普拉达换装 | outfit-change walk | transformation | 跟拍 | high |
| 面部换拍 | face morph | transformation | 固定机位 | high |
| 微距推镜 | macro push-in | macro_intimate | 推镜头 | low |
| 瞳孔推镜 | pupil push-through | macro_intimate | 推镜头 | medium |
| 升格KO | overcranked KO | action_impact | 推镜头 | high |
| 升格爆炸 | overcranked explosion | action_impact | 移镜头 | low |
| 双人对打 | two-person fight | action_impact | 跟拍 | high |
| 小蜜蜂运镜 | bee / hype cam | action_impact | 环绕 | medium |
| 子弹时间 | bullet time | time_manip | 环绕 | medium |
| 深海巨兽 | deep-sea leviathan | creature_reveal | 升降 | low |
| 飞鸟解体 | flock dissolve | creature_reveal | 推镜头 | high |
| 山路追击 | mountain-road chase | vehicle_scene | 载具跟拍 | low |
| 雪地赛车 | snow rally | vehicle_scene | 载具跟拍 | low |
| city drive | night-city neon drive | vehicle_scene | 载具跟拍 | low |
| 巨星名场面 | superstar walkout | hero_glamour | 环绕 | high |
| 水下慢镜头 | underwater slow-motion | aquatic | 跟拍 | medium |

**第二批 23（仙侠武侠/科幻变身/商业产品/环境时间/尺度规模）**

| 中文名 | 英文名 | category | 回链运镜 | 身份风险 |
|---|---|---|---|---|
| 御剑飞行 | flying-sword flight | wuxia_xianxia | 跟拍 | medium |
| 剑气斩 | sword-qi slash | wuxia_xianxia | 甩镜 | medium |
| 破碎虚空 | void shatter | scifi_transform | 推镜头 | high |
| 气场爆发 | aura burst | scifi_transform | 环绕 | high |
| 巨龙盘旋 | dragon reveal | creature_reveal | 环绕 | low |
| 凤凰浴火 | phoenix rebirth | creature_reveal | 升降 | high |
| 纳米装甲合体 | nano armor assembly | scifi_transform | 仰角英雄推 | medium |
| 机甲变形 | mecha transform | transformation | 环绕 | low |
| 化尘消散 | dust disintegration | transformation | 推镜头 | medium |
| 液态金属 | liquid-metal morph | transformation | 环绕 | high |
| 超空间跳跃 | hyperspace jump | scifi_transform | 穿越运镜 | low |
| 时间静止走过 | time-freeze walkthrough | time_manip | 跟拍 | medium |
| 液体飞溅 | liquid splash | product_commercial | 推镜头 | medium |
| 化妆品涂抹 | cosmetic application | macro_intimate | 移镜头 | high |
| 产品分解组装 | exploded assembly | product_commercial | 环绕 | medium |
| 香水雾化 | perfume mist | product_commercial | 推镜头 | medium |
| 玻璃破碎定格 | glass shatter freeze | action_impact | 环绕 | medium |
| 昼夜流逝 | day-to-night timelapse | environment_time | 固定机位 | low |
| 生长延时 | growth timelapse | environment_time | 推镜头 | low |
| 移轴微缩 | tilt-shift miniature | scale_world | 顶视俯拍 | low |
| 星空银河延时 | astro timelapse | environment_time | 固定机位 | low |
| 末日城市毁灭 | city destruction | scale_world | 无人机航拍 | medium |
| 千军万马 | army charge | crowd_scale | 无人机航拍 | medium |

## 来源

48 条特效基于对 2025–2026 主流 AI 视频平台命名模板与提示实践的实时检索整理：可灵(Kling)、即梦/Dreamina、Runway、Pika、Vidu、海螺(Hailuo)、Higgsfield、PixVerse、Sora、Veo。逐条 `platform_refs` 与 `sources` 见 `manifest.json`；部分为社区俗称、无官方同名卡时以电影摄影通行做法为准。
