---
name: ad-review
description: 拍广告 质检 + 流程自审（ad 线 QA 环节，不生产内容只审）。双模——模式①「作品质检·M0」：投放前检查广告主片与交付包的硬阻断项（成片存在、广告法机检 0 block、VO 非占位、AI 使用披露留痕、交付矩阵回写、产品/logo/品牌包装人工复核）。模式②「流程自审」：联网拉广告市场基准（钩子/转化 · 合规 · 成本/路由+模型SOTA 三轴），对照 ad-* 各 skill 找差距，report-only。Use when asked 广告质检, 广告审片, 投放前检查, 品牌一致性审查, 流程自审, 广告流程优化, ad 还能优化啥, ad-review for a 拍广告 project. Triggers 广告质检, 广告审片, 投放前检查, 品牌一致性审查, 流程自审, 流程优化, 自我优化, ad-review, QA.
---

# ad-review — 拍广告 · 质检 + 流程自审

不生产内容，只**审**。是 ad 家族的 QA 环节。两个模式：

- **模式①「作品质检·M0」**——审**某条广告主片与交付包的产物**：投放前硬阻断项体检。在 `ad-compose` 出主片和交付件后跑。
- **模式②「流程自审」**——审**广告流水线本身**：联网拉广告市场基准（钩子/转化 · 合规 · 成本/路由），对照 ad-* 各 skill + references，产出"差距清单 + 建议改哪个 skill 哪段"。让"整套广告产线不断自我优化"成为一条可复跑命令。

> ad 线**自包含**：本 skill 只查/对照 ad-* 自己的 skill、脚本和 references。

---

# 模式①：作品质检（M0）

在 `ad-compose` 出主片和交付件后跑。M0 先做**投放前硬项**，不伪装成视觉模型审片：产品/logo/品牌色像素级判断仍要人审，但脚本会把必须看的位置列出来。

## 用法

```bash
python3 skills/ad-review/scripts/review.py "<作品根>" --json "<作品根>/合规ad_review_m0.json"
```

产物：`合规ad_review_m0.json` + `合规ad_review_m0.md`。有 block 时退出码为 1。

## 检查项

1. 主片 `合成/成片_主片.mp4` 存在。
2. `脚本/广告法机检报告.json` 存在且 `summary.block=0`。
3. **开篇钩子饱和度评分 (Hook Saturation Score)**：评估前 3 秒的视觉张力和音效吸引力。
4. **万能安全区核查**：确认核心产品和 USP 落在 8x8 网格中心，无遮挡且适配裁切。
5. **视觉虚假宣传检测**：核对产品比例与真人比例的逻辑合理性。
6. `配音/时长清单.json.has_placeholder=false`。
4. `合规/ai_usage.json` AI 使用披露留痕存在。（AI 标识/水印不再由本流水线把关，移到工具之外由使用方按平台/地区法规自行处理。）
5. `_进度.md` 的交付矩阵至少有主片路径；缺回写则先跑 `ad-compose/deliver.py --mark-existing`。
6. 产品/logo/品牌色/字幕/音画同步列为人工复核清单。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把 `ai_usage.py` 当质检 | 它只做披露留痕；投放前还要跑本 review |
| 占位 VO 出成片 | M0 block；真 VO 复跑后再合成 |
| 主片存在但交付矩阵没回写 | 跑 `deliver.py --mark-existing`，让进度与文件一致 |
