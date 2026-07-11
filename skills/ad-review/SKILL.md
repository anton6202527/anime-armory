---
name: ad-review
description: 拍广告 质检 + 流程自审（ad 线 QA 环节，不生产内容只审）。双模——模式①「作品质检·M0」：投放前检查广告主片与交付包的硬阻断项（成片存在、广告法机检 0 block、出视频 video_qc 0 block、VO 非占位、AI 使用披露留痕、交付矩阵回写、产品/logo/品牌包装人工复核）。模式②「流程自审」：联网拉广告市场基准（钩子/转化 · 合规 · 成本/路由+模型SOTA 三轴），对照 ad-* 各 skill 找差距，report-only。Use when asked 广告质检, 广告审片, 投放前检查, 品牌一致性审查, 流程自审, 广告流程优化, ad 还能优化啥, ad-review for a 拍广告 project. Triggers 广告质检, 广告审片, 投放前检查, 品牌一致性审查, 流程自审, 流程优化, 自我优化, ad-review, QA.
---

# ad-review — 拍广告 · 质检 + 流程自审

不生产内容，只**审**。是 ad 家族的 QA 环节。两个模式：

- **模式①「作品质检·M0」**——审**某条广告主片与交付包的产物**：先汇总产品/品牌/视频/合规一致性 findings，再做投放前硬阻断项体检。在 `ad-compose` 出主片和交付件后跑。
- **模式②「流程自审」**——审**广告流水线本身**：联网拉广告市场基准（钩子/转化 · 合规 · 成本/路由），对照 ad-* 各 skill + references，产出"差距清单 + 建议改哪个 skill 哪段"。让"整套广告产线不断自我优化"成为一条可复跑命令。

> ad 线**自包含**：本 skill 只查/对照 ad-* 自己的 skill、脚本和 references。

---

# 模式①：作品质检（M0）

在 `ad-compose`、delivery QC 和发布合规 manifest 完成后跑。M0 不把全帧 dHash/NCC 伪装成语义审片：机器负责真实媒体抽帧、并排、结构/时长/响度和证据完整性，产品/logo/人物/场景语义一致性由人对 contact sheet 签收。

## 用法

```bash
python3 skills/ad-review/scripts/consistency_findings.py "<作品根>" --write
python3 skills/ad-craft/scripts/compliance_manifest.py "<作品根>" --declaration-status completed --declaration-evidence "<回执>"
python3 skills/ad-review/scripts/review.py "<作品根>" --json "<作品根>/合规/ad_review_m0.json"
```

产物：`生产数据/consistency_findings.{json,md}` + `合规/ad_review_m0.{json,md}`。有 block 时退出码为 1。

## 检查项

1. 主片 `合成/成片_主片.mp4` 存在。
2. `脚本/广告法机检报告.json` 存在且 `summary.block=0`。
3. `出视频/分镜/video_qc.json` 存在且 `summary.block=0`。
4. `consistency_findings.json` 汇总 product_qc / contract inheritance / video_qc / asset consistency / voice consistency / 广告法 / AI 披露；角色、场景、道具跨镜生成并排表，voice_key 漂移硬挡。
5. **开篇钩子饱和度评分 (Hook Saturation Score)**：评估前 3 秒的视觉张力和音效吸引力。
6. **placement-aware 安全区核查**：按实际版位/交互遮挡模板确认核心产品、USP、CTA；未知平台规格不得用通用中心网格冒充通过。
7. **视觉虚假宣传检测**：核对产品比例与真人比例的逻辑合理性。
8. `配音/时长清单.json.has_placeholder=false`。
9. `ai_usage.json` + `compliance_manifest.json.release_ready=true`；平台声明/显式标识/元数据责任必须有证据。
10. `合成/delivery_qc.json` 0 block：每件实测时长、比例、音轨、LUFS、true peak 通过。
11. `_进度.md` 只允许把 delivery_qc 通过的交付件标 ✅；产品/logo/人物/场景/道具/字幕/音画同步列人工签收。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把 `ai_usage.py` 当质检 | 它只做披露留痕；投放前还要跑本 review |
| 占位 VO 出成片 | M0 block；真 VO 复跑后再合成 |
| 跳过出视频 QC | M0 block；先跑 `ad-video/scripts/video_qc.py` 并修到 0 block |
| 主片存在但交付矩阵没回写 | 跑 `deliver.py --mark-existing`，让进度与文件一致 |
