# 拍广告线 · 架构铁律（人读）

## 八条铁律

1. **不拆集**。广告不切「第N集」。一条主片是一个整体（可以很长）。多时长（30/15/6s）、多比例（16:9/9:16/4:5/1:1）、A·B 是**交付件 deliverable**，不是集——登记在 `_进度.md` 的「交付版本矩阵」，由 `ad-compose` 从主片重剪/reframe。
2. **自包含 + 发布证据闭环**。`ad-*` 的入口、契约、脚本、文档和机检均在广告系列内维护。平台 UI 声明由发布方执行，但 AI 使用、显式/隐式标识责任、元数据和平台回执必须回写 compliance manifest。
3. **音频先行**。VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本 pass → 配音后分镜 pass）。广告常是「音乐床 + VO」混合驱动，音乐床作节奏锚一并记录在时间轴。
4. **模型与渠道分列**。生成者必须是具体模型版本，Codex/厂商/API/网页只写在渠道字段；已落图 job 同时记录 `model/channel`。
5. **claim 与披露不可拆**。producer pack 验依据，storyboard 验呈现，cutdown 按 `claim_id` 原子保留；不能大字讲结果、小字或短版删条件。
6. **平台到版位、地区到辖区**。平台名和“海外”都不是发布规格；release-ready 必须有实际 placement 证据和逐 jurisdiction、绑定当前内容 SHA 的复核。
7. **最终文件才是发布事实**。字幕/CTA/价格/声明在最终像素上抽查，关键口播做批准 VO→实际 VO→字幕→母版音轨四路对账，C2PA/隐式标识直接探测最终文件；计划值或 `preserve` 字符串不能替代。
8. **完成状态内容寻址**。每个阶段、镜头和交付件以输入/输出 SHA 收据验收；旧 ✅ 不继承，变更只失效受影响节点，具名签收绑定最终媒体、逐资产 contact sheet 和人工证据哈希。

## 状态机：两个 sibling 文件

- `_进度.md` —— 状态机。先读它判断走到哪。结构=阶段进度表 + 交付版本矩阵 + 维护记录（不是逐集矩阵）。
- `_设置.md` —— 私有选择点（权威）。按 `skills/ad/ad-craft/references/选择点与偏好.md` 解析。

## 阶段图

```
brief(目标/KPI立项) → concept(创意) → script(脚本+VO+时间轴+广告法机检)
   → voice(VO配音·时长清单) → storyboard(分镜·实测时长驱动)
   → image(三层定妆库+出图) → video(图生视频+契约继承)
   → compose(剪辑包装+技术/色彩/最终文字/ASR/无障碍/provenance QC)
   → handoff(locale/逐变体/版位/辖区发布合规) → review(最终媒体 contact sheet+M0+具名审片)
   → feedback(可选：投放数据 Test→Learn→Refresh)
```

高风险（花钱/不可逆/合规）阶段 = image / video / compose：正式生产入口须先确认，并跑 `ad-craft/scripts/gate.py <作品根> --stage image|video|compose`。

## 广告专有强化

| 维度 | 强化点 | 落在哪 |
|---|---|---|
| 源 | brief（品牌/产品/USP/受众/广告目标/漏斗/KPI/转化事件/claims/交付规格） | `需求/brief.json` |
| 策略 | 创意策划：big idea / 一句话主张 / mood&reference / KV 方向 | `ad-concept` |
| 合规 | 广告法 + 引证呈现 + locale + 逐交付 release variant + 实际 AI provenance + placement/jurisdiction 证据 | `ad-script` + `ad-craft` + `ad-compose` |
| 一致性 | 产品/品牌 + 人物/服装 + 场景/道具 + voice_key + 实际接缝 + 最终媒体逐资产 contact sheet | `ad-image` + `ad-video` + `ad-review` |
| 包装 | 片尾 end card（logo+slogan+CTA）、角标常驻 | `ad-compose` |
| 交付 | claim-safe cutdown、多比例、版位、BT.709/响度、最终像素文字/ASR、WCAG 目标、C2PA/隐式标识 | `ad-compose` |

## 跨阶段接力链（治"剪起来跳"）

`storyboard.json` 定义接缝合同；`ad-image` 产需要的尾帧；video runner 记录真实输入和提交 hash；`video_qc` 实抽每个 clip 的 start/mid/end，并比较相邻尾/首帧；`ad-compose` 再按转场合同剪辑。声明与媒体实测缺一不可。
