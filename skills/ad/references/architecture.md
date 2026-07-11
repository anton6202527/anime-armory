# 拍广告线 · 架构铁律（人读）

## 三条铁律

1. **不拆集**。广告不切「第N集」。一条主片是一个整体（可以很长）。多时长（30/15/6s）、多比例（16:9/9:16/1:1）、A·B 是**交付件 deliverable**，不是集——登记在 `_进度.md` 的「交付版本矩阵」，由 `ad-compose` 从主片重剪/reframe。
2. **自包含 + 发布证据闭环**。`ad-*` 的入口、契约、脚本、文档和机检均在广告系列内维护。平台 UI 声明由发布方执行，但 AI 使用、显式/隐式标识责任、元数据和平台回执必须回写 compliance manifest。
3. **音频先行**。VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本 pass → 配音后分镜 pass）。广告常是「音乐床 + VO」混合驱动，音乐床作节奏锚一并记录在时间轴。

## 状态机：两个 sibling 文件

- `_进度.md` —— 状态机。先读它判断走到哪。结构=阶段进度表 + 交付版本矩阵 + 维护记录（不是逐集矩阵）。
- `_设置.md` —— 私有选择点（权威）。按 `skills/ad-craft/references/选择点与偏好.md` 解析。

## 阶段图

```
brief(目标/KPI立项) → concept(创意) → script(脚本+VO+时间轴+广告法机检)
   → voice(VO配音·时长清单) → storyboard(分镜·实测时长驱动)
   → image(三层定妆库+出图) → video(图生视频+契约继承)
   → compose(剪辑包装+delivery_qc) → handoff(AI/发布合规) → review(M0投放前硬项)
   → feedback(可选：投放数据 Test→Learn→Refresh)
```

高风险（花钱/不可逆/合规）阶段 = image / video / compose：正式生产入口须先确认，并跑 `ad-craft/scripts/gate.py <作品根> --stage image|video|compose`。

## 广告专有强化

| 维度 | 强化点 | 落在哪 |
|---|---|---|
| 源 | brief（品牌/产品/USP/受众/广告目标/漏斗/KPI/转化事件/claims/交付规格） | `需求/brief.json` |
| 策略 | 创意策划：big idea / 一句话主张 / mood&reference / KV 方向 | `ad-concept` |
| 合规 | 广告法硬闸 + claim 结构化证据 + AI/平台发布声明证据 | `ad-script` + `ad-craft` |
| 一致性 | 产品/品牌 + 角色/服装 + 场景/道具 + voice_key + 实际镜头接缝 | `ad-image` + `ad-video` + `ad-review` |
| 包装 | 片尾 end card（logo+slogan+CTA）、角标常驻 | `ad-compose` |
| 交付 | cutdown 多时长、多比例 reframe、响度归一（LUFS）、安全框 | `ad-compose` |

## 跨阶段接力链（治"剪起来跳"）

`storyboard.json` 定义接缝合同；`ad-image` 产需要的尾帧；video runner 记录真实输入和提交 hash；`video_qc` 实抽每个 clip 的 start/mid/end，并比较相邻尾/首帧；`ad-compose` 再按转场合同剪辑。声明与媒体实测缺一不可。
