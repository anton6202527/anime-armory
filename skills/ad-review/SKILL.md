---
name: ad-review
description: 拍广告 M0 质检/自审 — 投放前检查广告主片与交付包的硬阻断项：成片存在、广告法机检 0 block、VO 非占位、AI 使用披露与水印状态、交付矩阵回写、产品/logo/品牌包装人工复核提示。Use when asked 广告质检, 广告审片, 投放前检查, 品牌一致性审查, ad-review for a 拍广告 project.
---

# ad-review — 拍广告 · M0 质检/自审

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
4. `合规/ai_usage.json` 存在，且水印/AI 标识不是“未记录”。
5. `_进度.md` 的交付矩阵至少有主片路径；缺回写则先跑 `ad-compose/deliver.py --mark-existing`。
6. 产品/logo/品牌色/字幕/音画同步列为人工复核清单。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把 `ai_usage.py` 当质检 | 它只做披露留痕；投放前还要跑本 review |
| 占位 VO 出成片 | M0 block；真 VO 复跑后再合成 |
| 主片存在但交付矩阵没回写 | 跑 `deliver.py --mark-existing`，让进度与文件一致 |
