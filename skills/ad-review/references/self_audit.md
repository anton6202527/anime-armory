# 拍广告 流程自审操作手册（模式②）—— 让广告产线可重复自我优化

把"人工复盘整条 ad 流水线"固化成一条可复跑流程。默认产出 = 一份**建议报告**（report-only，不自动改 skill）。ad 线自包含，本手册只对照 ad-* 自己的 skill + references，不读取其它创作系列的脚本或文档。

## 何时跑
- 用户主动要（"广告流程还能优化啥""过一遍 ad 产线"）。
- 每做完一批广告项目后的阶段复盘。
- **接了新模型/能力时**（新生视频模型/渠道、新生图后端、新配音后端、平台出了新一致性/口型/音画特性）——最高价值触发点。
- **法规/平台审核口径更新时**（广告法新增违禁词案例、抖音/快手/视频号广告审核细则变化）——广告线特有的高频触发点。

## 第0步：本地静态自审（先跑，不联网、不改文件）
联网对标前先确认 ad 产线自身没有治理漂移：

```bash
python3 skills/ad-review/scripts/self_audit.py            # 人读 markdown
python3 skills/ad-review/scripts/self_audit.py --json     # 喂回 LLM 汇总
```

它查 ad 线特有治理项：
- **广告法机检单入口**：`ad_law_check.py` 是唯一机检入口，gate / review 都消费 `广告法机检报告.json`、无旁路（block）。
- **交付规格外置**：cutdown / 多比例 / LUFS 响度集中在 `ad-craft contract`（`DELIVERY_PROFILE`/`CUTDOWN_PLANS`/`MULTI_ASPECT_RATIOS`），ad-compose 未硬编码响度。
- **生图后端白名单文档一致性**：ad-image SKILL + 选择点目录覆盖 `AD_APPROVED_IMAGE_BACKENDS`，且不把即梦/Dreamina 逆向当成可选放行后端。
- **生图模型/渠道分列**：新项目必须写具体模型版本 + 独立访问渠道，init/gate/已落图 manifest 全部消费；旧 `生图AI` 只迁移。
- **AI 使用披露文档一致性**：`ai_usage.py` 存在且与 `AI_VISUAL_USAGE_MODES` 对齐。
- **选择点对齐**：`contract.CHOICE_POINTS` 的每个键都暴露在 `选择点与偏好.md` 目录里。
- **正式 runner 真 gate**：image/video/compose 执行器入口直接调用 gate，不只靠文档提醒。
- **模板去样例化**：非测试生产文件不得泄漏 STARBOX/星盒等 fixture 品牌。
- **发布顺序与证据**：compose → handoff/compliance → review → feedback；claim 分型证据、实际 placement、逐 jurisdiction 复核均机器化并绑定当前内容。
- **逐阶段验收无旁路**：每阶段标准都有 evidence/authority/threshold/on_fail；`progress_set` 与正式 runner 消费；M0 后必须具名 human signoff。
- **最终交付证据链**：迁移器、locale matrix、release variant、最终像素文字、ASR、实际 C2PA/隐式标识、最终媒体 contact sheet、逐资产依赖哈希图均有执行器、消费者和全阶段 golden project 回归，缺任一为 block。

**0 block / 0 warn 才进入下一步联网市场对标。** 该脚本是 ad 线专属产线治理脚本；自审工艺写在本手册内，脚本实现只服务广告系列。

## 第1步：拉广告市场基准（联网，必带年月）
按广告线定制的三轴分轴搜，每轴落到"当前做法 + 证据链接 + 采集日期"：

| 轴 | 搜什么 | 映射到 ad 的 |
|---|---|---|
| **① 钩子/转化效果** | 平台官方目标化创意指南、实验工具与版位建议；公开基准只能作背景，不能把行业平均值伪装成项目阈值 | ad-concept（目标/假设）/ ad-script（0-3s 时间轴）/ ad-compose（cutdown 骨架）/ ad-review 具名钩子判断 / ad-feedback 预注册实验 |
| **② 合规**（广告线特有·高频变动） | 广告法/引证内容/代言、逐辖区发布、AI 显隐式标识、主动声明及元数据 | ad-script + producer_pack + placement/jurisdiction compliance + final review |
| **③ 成本/路由 + 各 stage 模型 SOTA** | 单条广告生成成本/周期、批量自动化、产品 hero 一致性的最省路由；图/视频/配音各 stage 当前最强模型及新语法（主体库/原生音画/多参考/最大时长） | ad-image / ad-video 模型路由 / ad-voice 后端 / 重抽预算策略 |
| **④ 技术交付/无障碍** | 当前版位比例/时长/安全区、色彩/响度、最终像素文字/ASR、字幕/音频描述、闪烁、C2PA/隐式标识 | platform_pack / locale+release variant / ad-compose final-file QC / contact sheet + human signoff |

> 先查法律/监管、平台广告帮助中心、技术标准正文和模型官方 API；二手实战贴只补充案例，不能单独决定硬阈值。每个口径区分 `official / house / heuristic / human`，并记录 URL、发布日期/更新日与本次采集日。
> **合规轴每次必新搜**：广告法案例和平台审核口径是 ad 线变动最快的项，旧结论极易过期。

## 第2步：对照 → 差距清单
逐 stage 把"基准做法"对到 `ad-*/SKILL.md` + `references/*` + `ad-craft/scripts/contract.py`：

- **先查已实现**：很多"新做法"产线早做了（如三层定妆库含产品 hero、voice-first 驱动镜头时长、广告法机检 + 免责联动、cutdown 矩阵、交付响度归一）。**已实现的不重复立项**——报告里标"✅ 已覆盖"一行带过。
- **找真差距**：只记"基准有、ad 没有或更弱"的。每条写成：
  ```
  差距：<一句话>
  证据：<链接>（采集 <年-月>）
  落点：<改哪个 ad skill 哪段 / 或新立项>
  优先级：must（影响成片质量/转化/合规）/ optional（增稳/提效）
  可脚本化：是/否（是→能进 ad_law_check / gate / self_audit / review）
  ```
- **分三类处置**：① 硬约束（铁律 / 词库 / gate 项）② 可选增强（opt-in 段）③ 机检项（脚本）。

## 第3步：起草 + 落地（人确认后）
1. 高价值项直接起草建议（结论 + 决策 + 落点表）。
2. 建议的 skill edit 写成 diff 级描述（改哪段、加什么铁律/词库/段落）。
3. **改任何 skill → 必同步 `skills/README.md` 索引**（仓库硬约定，缺了视为未完成）。本 skill 不自己改 README，由执行落地时统一处理。
4. **默认不自动改产线**：模式②产报告，用户拍板后再由对应 ad skill / 人执行编辑。

## 防过期 / 防噪声铁律
- 每条建议**带来源链接 + 采集日期**；旧报告里的建议可能已被采纳或已过时，落地前重新核对当前 skill 是否已有。
- **每次自审都从头按本流程重跑**（第0步本地自审 → 拉基准 → 对照 → 差距），**绝不读旧报告当捷径**——市场/法规会变，旧结论可能已过时或已落地。
- **报告一次性·不留存**：只讲给用户，**不在 skill 目录存 `_流程自审_*.md`** 这类存档。
- 容错铁律同模式①：只报"真差距"，不把"换种说法会更好"的主观偏好堆进来。
- 模型名/特性会变——写"能力"而非死绑某产品版本号；易变候选清单登记在 `ad/_lib/freshness.py` 并带采集日期戳。

## 一次自审的标准产物
```
# 拍广告 流程自审 <年-月-日>
## 第0步本地自审结果（block/warn/info 摘要）
## 三轴取证摘要（含来源链接 + 采集日期）
## 差距清单（按优先级）
  - [must] …  落点：ad-xxx 某段
  - [optional] …
## 已覆盖（✅ 一行带过，证明查过没重复）
## 建议落地顺序 + 是否需要改 README
```
