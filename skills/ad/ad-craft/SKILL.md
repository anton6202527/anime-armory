---
name: ad-craft
description: Shared machine contracts and deterministic helpers for the ad-* (拍广告/广告片) skill family — ad project _meta/_设置/_进度 fields, stage contracts, render profile, placement adaptation, campaign readiness, the cutdown/多比例 deliverable axis, and separate AI/commercial disclosure evidence. Other ad-* skills reference these by file path; users can also invoke directly for 拍广告 pipeline contract, manifest, cutdown, 版位适配, 投放就绪, 交付规格, or disclosure questions. Triggers ad contract, ad-craft, 广告合约, 广告契约, 交付版本, cutdown, 多比例交付, 版位适配, 投放就绪, 交付规格, AI使用披露, 商业内容披露, 广告合规留痕.
---

# ad-craft — 拍广告线共享契约

`ad-craft` 是 `ad-*`（拍广告）家族的机器单一真值源，不写文案、不出图、不剪辑。它只沉淀字段、选择点、阶段表、交付件（cutdown/多比例）约定和合规留痕脚本，避免 `ad-script` / `ad-image` / `ad-video` / `ad-compose` 各自解释同一件事。

**自包含铁律**：`ad-*` 的工艺、脚本、契约和文档都在广告系列内独立维护；任何通用能力都必须先落成本系列自己的适配层和测试。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/ad/ad-craft/references/选择点与偏好.md` 读用户私有选择：项目值优先，其次全局默认；仍缺失的普通、可逆项采用推荐值写回并继续。`广告法地区`、`音乐来源` 等合规/权利口径在使用时确认；付费动作绑定一次阶段预算包，包内不逐调用重复问。

本 skill 涉及的选择点：`广告类型`、`创意路线`、`基础视觉风格`、`主片时长`、`交付比例`、`cutdown版本`、`生图模型`、`生图渠道`、`一致性增强`、`生视频模型`、`生视频渠道`、`出视频规格`、`视频分辨率`、`配音后端`、`音乐来源`、`品牌包装模板`、`字幕语言`、`广告法地区`、`交付规格` 等。旧 `生图AI` 只作迁移输入，正式花钱前必须拆成具体模型+访问渠道。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `references/production-standards.md` + `scripts/contract.py` | 初始化项目、交付件和 11 阶段入场/通过线/依据/失败回退；标准均带 evidence/authority/threshold/on_fail |
| 制片前控包 | `scripts/producer_pack.py` | 传统广告 PPM 机器版；claim 按 brand fact/检测/统计/文献/比较/代言分型，条件化要求来源、资质、方法、样本、范围、有效期和披露文案 |
| 平台交付包 | `scripts/platform_pack.py` | 把平台 + 实际 placement + deliverables 落成 pack；安全区证据按 `平台:placement`，未知版位缺规格即 block |
| 统一渲染规格 | `scripts/render_profile.py` | 把源生成请求与母版容器的比例/分辨率/FPS 分开落档；阻断后端不支持参数、profile 漂移和“放大容器冒充原生细节” |
| 版位原生适配 | `scripts/placement_adaptation.py` | 每个交付件显式选择 native master/recrop/reedit/variant 或受控 mechanical reframe；native reedit/variant 的 shot plan 逐镜绑定 source_path(s)，结构风险、焦点/安全区证据与具名批准 fail-closed；完成后签 actual-mode + 输入/输出/profile/plan SHA execution receipt |
| 投放就绪 | `scripts/campaign_readiness.py` | formal/sample 分流；核落地页、素材↔落地页、行业×平台×辖区准入、转化与 diagnostics、归因/UTM/deep-link、consent/privacy；只认项目内证据，不伪装联网/平台操作 |
| 只读进度 | `scripts/progress.py` | 查项目当前前沿 + 下一步该跑哪个 ad-* skill（公共 `progress` 分发路由到此，保持本线 craft 自包含） |
| 状态回写 | `scripts/progress_set.py` | 阶段完成后回写 `_进度.md` 阶段进度；交付件存在后回写交付版本矩阵状态/路径 |
| 逐阶段验收 | `scripts/stage_acceptance.py` + `contract.STAGE_CRITERIA` | 对 11 个阶段统一产出可审计验收报告；区分机器事实、官方口径、内部标准、人工判断和启发式；阻断假 ✅ |
| 旧项目迁移 | `scripts/migrate_project.py` | 默认 dry-run；备份后升级 brief/设置/locale/阶段表，旧 ✅ 按当前验收和依赖收据重算，未知授权/法务事实保持 pending |
| 逐资产依赖图 | `scripts/dependency_graph.py` | 为阶段、逐镜 image/video、逐交付件 compose 建输入/输出 SHA 收据；brief/包装/claim/字幕变化只标记受影响节点 stale |
| 花钱 gate | `scripts/gate.py` | image/video/compose 正式生产入口统一阻断：brief 合规项、广告法报告、分镜时长、占位 VO、上游产物；video/compose 另读 `ad-review/verifier_coverage` 覆盖账本（video warn、compose fail-closed 硬挡——交付前必须证明机检没空转） |
| 防降级宪章 | `scripts/consistency_charter.py` + `test_consistency_charter.py` | 每条承重硬闸（block code）在宪章占一行（带日期理由），守卫测试内省 gate.py 源码 + 功能验证 advisory 降档/新鲜度/占位 VO 纪律；静默降档立即红灯，降档必须先改宪章行=显式审计决策 |
| locale + 发布变体 | `scripts/locale_matrix.py` + `scripts/release_variant_manifest.py` | 逐交付件绑定语言、币种、单位、CTA、法律声明、配音/字幕/排版，以及 deliverable SHA→placement→jurisdiction→claims/disclosures→rights→独立 AI label receipt + commercial/paid-partnership receipt |
| AI 使用 + 发布合规 | `scripts/ai_usage.py` + `scripts/compliance_manifest.py` | 记录 AI/授权；消费最终文件实际 provenance 探测、平台主动声明、placement 证据和逐发行辖区法律复核，复核须绑定当前 release content SHA。显式标识责任=self_rendered/burned_in 等自行烧录取值时，必须在 `合规/rendered_text_plan.json` 有 AI 标识文字条目（缺=block `explicit_label_plan_missing`）且落在起始段 ≤3s（否则 warn）——《标识办法》要求视频**起始画面**显著提示，标识经 `rendered_text_qc` OCR 像素验证，不能只在台账记一笔 |
| 生成止损审计 | `scripts/stop_loss.py` | 读 `生产数据/production_events.jsonl` 生成账本：重抽率>35%、单资产>4 次、credit 超预算线、QC block 未清仍在续抽 → warn。**审不是门**（block 恒 0，止损归人）；gate video/compose 以 advisory 侧车并入，空账显式 `no_evidence` |
| 生成次数预算 | `scripts/generation_budget.py` | **事前**结构性预算（与 stop_loss 事后止损互补）：逐镜生成账（首帧+尾帧+视频）+ 相邻同场景合并候选链（≤10s，endcard/时长缺失断链）+ `AD_BUDGET_MAX_GENERATIONS` 预算线。advisory·block 恒 0；gate image 侧车 |
| 补拍任务包 | `scripts/pickup_plan.py` | 传统 pickup list 纪律：把 product_qc/video_qc 的 block/warn 逐条变成带确定性处置建议的补拍任务（dHash→补参考重出、clip 未回收→先回收、后端冲突→重出或签核 override 二选一）；联动生成账本，单资产 >4 次仍 fail → 升级"改分镜/换处方"。生产实锤教训（星盒：22 block 悬置至项目死亡）的闭环件。advisory；gate video/compose 侧车 |

## 共享脚本

```bash
# 初始化项目 _设置.md / _进度.md（一般由 ad 调度自动调用 contract.py 的函数生成）
cd skills/ad/ad-craft/scripts && python3 -c "import contract; print(contract.progress_markdown('某品牌618'))"

# 只读进度：当前前沿 + 下一步建议（公共 progress 分发也走这里）
python3 skills/ad/ad-craft/scripts/progress.py "<拍广告作品根>"

# 制片前控包：出图前/客户审片前建议跑，先把审批与资产缺口摊开
python3 skills/ad/ad-craft/scripts/producer_pack.py "<拍广告作品根>"

# 平台交付包：出视频/合成前把平台安全区和 cutdown 矩阵落档
python3 skills/ad/ad-craft/scripts/platform_pack.py "<拍广告作品根>"

# 单一渲染规格 + 每个交付件的版位原生适配计划
python3 skills/ad/ad-craft/scripts/render_profile.py "<拍广告作品根>"
python3 skills/ad/ad-craft/scripts/placement_adaptation.py "<拍广告作品根>"
# 跨比例成片完成后按实际模式签收（--input 可重复；native 模式须覆盖 shot plan 的全部 source_path(s)）
python3 skills/ad/ad-craft/scripts/placement_adaptation.py "<拍广告作品根>" --record-execution reframe_9x16 --actual-mode native_reedit --input "出视频/分镜/视频/竖版镜头01.mp4" --output "合成/多比例/成片_9x16.mp4" --executed-by "剪辑甲"

# 花钱/不可逆阶段 gate（每次运行自动落档 生产数据/gate_reports/<stage>.json，--no-record 可关）
python3 skills/ad/ad-craft/scripts/gate.py "<拍广告作品根>" --stage image
python3 skills/ad/ad-craft/scripts/gate.py "<拍广告作品根>" --stage video
python3 skills/ad/ad-craft/scripts/gate.py "<拍广告作品根>" --stage compose

# 任一阶段完成前的统一验收；报告写 生产数据/stage_acceptance/<stage>.json
# （voice 会核 voicemap 未失效、script 会核时间轴结构自洽、image 会核 registry 母本↔快照未陈旧、
#   compose 会逐条复查交付文件真实存在；image/video/compose 还会 advisory 提示花钱 gate 未跑/已过期——
#   验收管「完成」、gate 管「花钱」，两链各自成立但互相可见）
python3 skills/ad/ad-craft/scripts/stage_acceptance.py "<拍广告作品根>" --stage voice
python3 skills/ad/ad-craft/scripts/stage_acceptance.py "<拍广告作品根>" --stage review

# 旧项目先 dry-run，再带备份写入；不会把未知审批迁成“通过”
python3 skills/ad/ad-craft/scripts/migrate_project.py "<拍广告作品根>"
python3 skills/ad/ad-craft/scripts/migrate_project.py "<拍广告作品根>" --write

# locale/逐交付发布变体/依赖图
python3 skills/ad/ad-craft/scripts/locale_matrix.py "<拍广告作品根>" --init
python3 skills/ad/ad-craft/scripts/release_variant_manifest.py "<拍广告作品根>"
python3 skills/ad/ad-craft/scripts/dependency_graph.py "<拍广告作品根>"

# 投放就绪（auto 读取 brief.campaign_mode；formal 缺证据 fail-closed，sample 永不 release-ready）
python3 skills/ad/ad-craft/scripts/campaign_readiness.py "<拍广告作品根>" --mode auto

# 阶段/交付回写
python3 skills/ad/ad-craft/scripts/progress_set.py set-stage "<拍广告作品根>" image --status ✅ --artifact 出图/分镜
python3 skills/ad/ad-craft/scripts/progress_set.py set-deliverable "<拍广告作品根>" master --status ✅ --path 合成/成片_主片.mp4

# 投放前 AI 使用 + 授权披露
python3 skills/ad/ad-craft/scripts/ai_usage.py "<拍广告作品根>" \
  --visual-mode AI-generated --video-mode AI-generated \
  --music-status 授权曲库:已购 --talent-status 未使用真人 --publish-target 抖音

python3 skills/ad/ad-craft/scripts/compliance_manifest.py "<拍广告作品根>" \
  --declaration-status completed --declaration-evidence "合规/平台声明回执.png" \
  --explicit-label-status platform_managed --implicit-label-status platform_managed \
  --metadata-status preserve
```

输出还包括 `合规/locale_matrix{,_validation}.json`、`release_variant_manifest.json`、`provenance_qc.json`，以及 `生产数据/artifact_dependency_graph.json` / `dependency_receipts.json`。

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、脚本不伪装云端自动化 B4、阶段回写 B5、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../docs/skill-design-principles.md)，此处只列 ad 线特有原则。ad 的选择点目录：`skills/ad/ad-craft/references/选择点与偏好.md`。

- **不拆集 + cutdown 轴**：一条主片是整体；多时长/多比例/A·B 是「交付件 deliverable」，登记在 `_进度.md` 交付版本矩阵，由 `default_deliverables()` 按 `主片时长`/`交付比例`/`cutdown版本` 派生。
- **音频先行**：VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本 → 配音后分镜），确保广告主片总时长、强制露出和节奏锚点可对账。
- **标准有类型且有回退**：`deterministic/official/house/human/heuristic` 五类证据不能混用；每条还必须写 authority/threshold/on_fail。内部 `-16 LUFS`、字幕阅读速度等不冒充平台或法律统一标准。
- **claim 三段闭环**：producer pack 验依据，storyboard 按 `claim_id` 验来源/条件/范围的呈现，cutdown 保持 claim+披露原子性；禁止“大字吸睛、小字免责”和先做数据文案后补依据。
- **平台≠版位、海外≠辖区**：发布前必须落到实际 placement 和具体 jurisdiction；通用中心网格、平台级截图或泛称“海外”都不能给 release-ready。

## 测试

```bash
cd skills/ad/ad-craft/scripts && python -m pytest test_contract.py test_progress_set_gate.py test_stage_acceptance.py test_producer_pack.py test_platform_pack.py test_render_profile.py test_placement_adaptation.py test_campaign_readiness.py test_compliance_manifest.py test_locale_matrix.py test_release_variant_manifest.py test_dependency_graph.py test_migrate_project.py test_golden_project.py test_consistency_charter.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把广告拆成「集」 | 拍广告不拆集；多时长/多比例走 cutdown 交付件矩阵，不是 `第N集` |
| 手工改 manifest/交付矩阵字段 | 经对应阶段脚本重新生成，别手改机器契约字段规范 |
| 直接把阶段状态填成 ✅ | `progress_set.py` 会先跑 `stage_acceptance.py`；修复 block 后才能完成 |
| 偏好硬编码（写死即梦/720p/30s） | 一律读 `_设置.md`；新增选择点先进 `skills/ad/ad-craft/references/选择点与偏好.md` 目录 |
| 只写“生图AI=Codex/某厂商” | 分列 `生图模型=具体版本` + `生图渠道=CLI/API/网页入口`；manifest 也分别落档 |
| 只填平台/海外就发布 | 补实际 placement 安全区证据和逐辖区、绑定当前成片哈希的法务复核 |
| 投放前漏 AI/授权留痕 | 脱离管线投放前必须在 `合规/` 调用 `ai_usage.py` 并填具体授权模式 |
| 把 AI 标识当商业合作披露 | 两套收据用途不同；每个最终 placement 都须独立绑定当前交付 SHA 与本地/平台证据 |
| 成片完成就等于可投 | 再跑 `campaign_readiness.py`；formal 的落地页、准入、measurement、routing、privacy 任一缺证都不能 release-ready |
