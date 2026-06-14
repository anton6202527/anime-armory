# 拍广告线 · 架构铁律（人读）

## 三条铁律

1. **不拆集**。广告不切「第N集」。一条主片是一个整体（可以很长）。多时长（30/15/6s）、多比例（16:9/9:16/1:1）、A·B 是**交付件 deliverable**，不是集——登记在 `_进度.md` 的「交付版本矩阵」，由 `ad-compose` 从主片重剪/reframe。
2. **自包含**。`ad-*` 不复用 n2d-* / mv-* / novel-* / song-*。借鉴思路可以，import 代码不行。AI 标识/水印不再由本流水线处理，移到工具之外由使用方按平台/地区法规自行处理。
3. **音频先行**。VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本 pass → 配音后分镜 pass），与 n2d「配音先行」同构。广告常是「音乐床 + VO」混合驱动，音乐床作节奏锚一并记录在时间轴。

## 状态机：两个 sibling 文件

- `_进度.md` —— 状态机。先读它判断走到哪。结构=阶段进度表 + 交付版本矩阵 + 维护记录（不是逐集矩阵）。
- `_设置.md` —— 私有选择点（权威）。按 `skills/ad-craft/references/选择点与偏好.md` 解析。

## 阶段图

```
brief(立项) → concept(创意) → script(脚本+VO+时间轴+广告法机检)
   → voice(VO配音·时长清单) → storyboard(分镜·实测时长驱动)
   → image(三层定妆库+出图) → video(图生视频+契约继承)
   → compose(剪辑包装+cutdown+多比例+交付规格) → handoff(AI披露) → review(M0投放前硬项)
```

高风险（花钱/不可逆/合规）阶段 = image / video / compose：正式生产入口须先确认，并跑 `ad-craft/scripts/gate.py <作品根> --stage image|video|compose`。

## 广告专有强化（相对 n2d/mv）

| 维度 | 强化点 | 落在哪 |
|---|---|---|
| 源 | 客户需求 brief（品牌/产品/USP/受众/调性/强制项/claims/交付规格） | `需求/brief.json` |
| 策略 | 创意策划：big idea / 一句话主张 / mood&reference / KV 方向 | `ad-concept` |
| 合规 | 《广告法》违禁词/极限词机检（绝对化用语/虚假/医疗保健）硬闸门 | `ad-script/ad_law_check.py` |
| 一致性 | 产品定妆（hero product 包装/logo/品牌色零漂移）= 三层定妆库第三层 | `ad-image` |
| 包装 | 片尾 end card（logo+slogan+CTA）、角标常驻 | `ad-compose` |
| 交付 | cutdown 多时长、多比例 reframe、响度归一（LUFS）、安全框 | `ad-compose` |

## 跨阶段接力链（治"剪起来跳"）

与 n2d 同构、单一真值源在 `ad-script` 的 `storyboard.json`：每个接缝写 `上一Clip出点=下一Clip入点` + `转场类型` + `需要尾帧?`；`ad-image` 标尾帧的接缝出 `镜头N_end.png`；`ad-video` 读契约不重写 start_state；`ad-compose` 按转场类型接 clip。
