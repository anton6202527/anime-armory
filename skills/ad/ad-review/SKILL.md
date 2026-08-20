---
name: ad-review
description: 拍广告 质检 + 流程自审。模式①在最终编码媒体上生成逐资产首/中/尾帧 contact sheet，检查发布变体、最终文字、ASR、无障碍、C2PA/隐式标识，再由具名审片人逐项留证并以 SHA-256 绑定全部交付件和 contact sheet；机器不伪装语义审片。模式②以实时一手来源审查 ad-* 流程与标准。Use when asked 广告质检, 广告审片, 投放前检查, 品牌一致性审查, 流程自审, 广告流程优化, ad 还能优化啥, ad-review for a 拍广告 project. Triggers 广告质检, 广告审片, 投放前检查, 品牌一致性审查, contact sheet, C2PA, 流程自审, 流程优化, 自我优化, ad-review, QA.
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
python3 skills/ad/ad-review/scripts/consistency_findings.py "<作品根>" --write  # 内含最终 clip/交付件首中尾帧+逐资产 contact sheet
python3 skills/ad/ad-craft/scripts/compliance_manifest.py "<作品根>" --declaration-status completed --declaration-evidence "<回执>"
python3 skills/ad/ad-review/scripts/review.py "<作品根>" --json "<作品根>/合规/ad_review_m0.json"
# 审片人在真实主片、全部交付件和 contact sheet 上逐项审完后，
# 为 human_signoff.py --help 列出的每个 CHECK 各重复一对参数：
python3 skills/ad/ad-review/scripts/human_signoff.py "<作品根>" --reviewer "<姓名>" \
  --approve <CHECK_1> --evidence <CHECK_1>="<该项证据文件或记录>" \
  --approve <CHECK_2> --evidence <CHECK_2>="<该项证据文件或记录>" \
  ...
python3 skills/ad/ad-craft/scripts/stage_acceptance.py "<作品根>" --stage review
```

产物：`生产数据/final_media_consistency.json` + `final_media_frames/` + 按 product/character/scene/prop 分类的 `final_media_contact_sheets/`，以及 `consistency_findings.{json,md}`、`asset_drift_report.{json,md}`、`合规/ad_review_m0.{json,md}`、`human_signoff.json`。签收 SHA-256 绑定全部未取消交付件、逐资产 contact sheet、delivery/color/accessibility/rendered-text/ASR/provenance/locale/release-variant QC 与当前 M0。每个检查都必须有本地证据哈希；URL/record 证据另传 `--evidence-sha CHECK=64HEX`。脚本刻意没有 `--approve-all`。

## 跨镜资产漂移报表（事后聚合）

```bash
python3 skills/ad/ad-review/scripts/asset_drift_report.py "<作品根>" --write
```

补的空档：`asset_consistency.py` 现已把 `PROD_`/`BRAND_` 纳入跨镜 dHash（阈值比常规资产更紧 26bit、
命中标 `priority=high` 置顶），而 `product_qc` 覆盖产品的**单批次内**比对——本报表再把已有各份机检汇总成
**逐资产 × 逐镜**的 ok/warn/block/noevidence 时间线，标出 `first_bad_shot`、连崩镜数，并给修复建议
（单镜孤立崩 → 只重抽该镜；同一资产多镜连崩 → 回定妆库/registry，别只重抽单图；产品/品牌资产崩 → P0）。
`consistency_findings.py --write` 已自动带上它，无需单独记得跑。

**诚实边界**：① 它**零像素、只聚合上游报告**，不会发现上游没发现的漂移——产品跨镜像素统计来自
`asset_consistency`（全帧启发式）与 `product_qc`（ROI 口径），本报表只汇总；② `noevidence ≠ ok`，上游对完全干净的
镜头不留痕，故干净项目也会出 info，**缺证据不算通过**是刻意的；③ 它是"审"不是"门"——**恒不产 block**
（`finding()` 在构造层强制降档），紧迫度读 `detail.priority` 而非 severity。硬闸仍是 `product_qc` 的
prompt-lint 与 provenance。

## 一致性覆盖账本（fail-closed）

```bash
python3 skills/ad/ad-review/scripts/verifier_coverage.py "<作品根>" --write
```

防的不是"机检报了问题"而是**机检空转**：报告存在但 0 个真实对象被检、registry 登记了产品而
`product_qc` 没检到任何产品图、advisory 侧车 available=false 却被当干净。逐机检算
**适用 × 真跑 × 新鲜 × 检了真实对象** 四元组，规则"**适用 × 休眠 → 交付前阻断**"：硬机检
（product_qc/asset_consistency/video_qc/contract_inheritance）空转/过期在适用时 block，
`final_media_consistency` 与 advisory 编剧轴只 warn（`advisory_degraded` 空转告警）。落
`生产数据/ad_verifier_coverage.{json,md}`；gate 在 video 阶段 warn 提醒、**compose（交付点）
缺账本或账本有 block 一律硬挡**。降档唯一出口：`合规/degraded_qc_waiver.json`
（approved+scope+reason+signed_by 齐全才有效）签核留痕降为 warn。**本检可产 block**——它是
确定性覆盖闸，不适用"创意启发式只提示"的规矩（防降级宪章 `ad-craft/scripts/consistency_charter.py`
已锁定）。

## 检查项

1. 主片 `合成/成片_主片.mp4` 存在。
2. `脚本/广告法机检报告.json` 存在且 `summary.block=0`。
3. `出视频/分镜/video_qc.json` 存在且 `summary.block=0`。
4. `final_media_consistency.json` 从最终 clip 与每个最终编码交付件按镜抽首/中/尾帧，按产品/人物/场景/道具生成 contact sheet；视觉 hash 仅定位，具名人逐资产签收。
5. **开篇钩子人工判断**：审片人按广告目标判断前 3 秒的产品/品牌、信息密度、画面张力和声音；机器只确认时间段/媒体存在，不产“必有效”分数。
6. **placement-aware 人工安全区核查**：对每个实际版位、比例、caption 与 anchor/add-on 使用当前官方/客户模板；通用中心网格不能充当发布证据。
7. **视觉真实性人工判断**：产品尺度、演示、前后对比、效果画面是否误导必须由具名审片人结合实物/claim 依据判断，dHash/NCC 只做定位快筛。
8. `配音/时长清单.json.has_placeholder=false`。
9. `locale_matrix_validation`、`release_variant_manifest`、`provenance_qc` 与 `compliance_manifest.release_ready=true`；每件绑定 placement/locale/jurisdiction/claims/disclosures/rights，并分别具备绑定当前媒体 SHA 的 AI label receipt 与 commercial/paid-partnership disclosure receipt，实际文件 provenance 已探测。
10. `campaign_readiness.summary.release_ready=true`：formal 投放的落地页/最终 URL 与跳转证据、offer/claim/CTA/价格对账、行业×平台×辖区准入、转化事件与 tag/pixel/SDK/CAPI diagnostics、归因、UTM/deep-link、consent/privacy 全部闭合；sample/demo 永远不能当正式投放通过。
11. `delivery_qc` 0 block：每件实测时长、比例、版位约束、音轨、LUFS/true peak、BT.709 通过；`color_preflight` 0 block。
12. `rendered_text_qc`、`asr_consistency`、`accessibility_qc` 0 block；最终文字、关键口播、完整非语言字幕、条件化音频描述/媒体替代均闭合，启发式 WARN 在具名审片处理。
13. 依赖图所有上游节点 current；`_进度.md` 只允许把全部最终媒体 QC 通过的交付件标 ✅，review 要求 M0、人工证据与 contact sheet 哈希均当前。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把 `ai_usage.py` 当质检 | 它只做披露留痕；投放前还要跑本 review |
| 占位 VO 出成片 | M0 block；真 VO 复跑后再合成 |
| 跳过出视频 QC | M0 block；先跑 `ad-video/scripts/video_qc.py` 并修到 0 block |
| 主片存在但交付矩阵没回写 | 跑 `deliver.py --mark-existing`，让进度与文件一致 |
| 把 Hook/视觉真实性当成可自动裁决 | 机器只给证据和快筛；用 `human_signoff.py` 逐项具名签收 |
| 平台名/“海外”写了就算发布合规 | 必须实际 placement + 逐 jurisdiction 复核，并绑定当前脚本/主片/delivery plan SHA |
| AI 标签回执存在就以为商业披露完成 | AI 来源标识与商业/付费合作披露是两条独立义务；逐 placement 各自留当前 SHA 回执 |
| 样片 readiness 只有 WARN 就拿去投 | sample 永远 `release_ready=false`；正式投放须切 formal 并补齐项目内证据 |
| 闪烁快筛没报警就声称 WCAG 通过 | 快筛只 WARN；按 WCAG 三闪阈值做具名或专业工具复核 |
