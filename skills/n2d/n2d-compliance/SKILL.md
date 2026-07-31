---
name: n2d-compliance
description: P0 compliance and rights preflight for n2d. Create and validate 合规/compliance_manifest.json before paid image/video/compose/review gates, covering source/adaptation copyright, character likeness authorization, voice cloning authorization, target-platform review, NRTA 广电备案/分级/播前审核 (regulatory_filing), overseas localization, and AI 生成合成内容标识待办 (ai_labeling — 显式标签/元数据/水印只做 INFO 和 best-effort 后处理，不阻断主流程). Use when asked for 合规前置, 版权前置, 角色授权, 声音克隆授权, 平台审核, 广电备案, 网络微短剧备案, 播前审核, 分级, 出海本地化, AI标识, AI生成标识, compliance gate, copyright gate.
---

# n2d-compliance — 合规与版权前置

`n2d-compliance` 是 n2d 的 P0 合规包入口。它不做法律判断，也不替代律师或平台最终审核；它把“必须先确认的权利与监管事项”变成机器可读文件，让 `n2d-review/scripts/gate.py` 在出图、出视频、合成、审查前阻断。AI 标识/披露/水印例外：只做 INFO 待办和 best-effort 后处理，不阻断主流程。

核心文件：

```text
创作区/制漫剧/<剧名>/合规/compliance_manifest.json
创作区/制漫剧/<剧名>/合规/release_manifest_第N集.json
```

## 输入 / 输出 / 读写边界

- **输入**：源文本/改编权信息、identity registry 角色、声音克隆/素材授权、平台审核策略、目标地区。
- **输出**：`合规/compliance_manifest.json` 和 `--check` 结果；发布前由 `n2d-compose/release_manifest.py` 汇总 `release_manifest_第N集.json/md`；dashboard gate 会把阻断写入生产数据。
- **读写边界**：只建立/校验合规包；不替代法律意见、不生成媒体、不改生产阶段。
- **契约关系**：internal_only 免检范围、必填域和 gate 阶段阻断口径与 `skills/n2d/_lib/n2d_contract.py` 保持同源。

## 标准命令

初始化模板：

```bash
python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> --init
```

初始化会先读 `<作品根>/_设置.md` 的 `合规用途`（缺省来自默认设置 `internal_only`）。自己做 demo / 学习 / 内部预览时保持 `合规用途=internal_only`；只有准备公开发布候选或付费投放时，才改为 `publish_candidate` / `paid_distribution` 并补平台审核、备案、本地化和发布标识证据。

检查合规包：

```bash
python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> 第1集 --check
python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> 第1集 --check --stage review --json
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image_preflight
```

`dashboard.py gate` 是生产硬闸门入口（内部调用 `gate.py --json` 并把 QA 入账）；`compliance.py --check` 用于提前看缺口。`--json` 输出字段级 `n2d_compliance_field_verdict`，状态为 `pass / blocked / demo-only / internal-only`，供 `release_verdict.py` 直接聚合，不再只读 manifest 顶层粗状态。

发布前归档：

```bash
python3 skills/n2d/n2d-dashboard/scripts/event_ledger.py doctor <作品根>
python3 skills/n2d/n2d-compose/release_manifest.py build <作品根> 第1集 --stage review --write
python3 skills/n2d/n2d-compose/release_manifest.py check <作品根> 第1集
```

`release_manifest` 汇总母带 SHA256、合规 issue、gate findings、机器分、人审签收、AI 标识/水印/C2PA 待办和事件账本审计路径。它不是新的合规判定引擎，只是发布边界的证据包；`readiness.status=blocked` 时不能进入投放交付。

## 必填面

- **版权/改编权**：源文本、改编权、BGM、音效、字体。按设计宪法 D4，用户提供或同一作品根内的源文本默认用户为原著作者，源文本与同源漫剧改编权默认 `original`，不因缺外部证明阻断；明确第三方/转载/授权/公版时才转入对应状态。`licensed/user_declared/stock_licensed` 仍必须写 evidence/ref。
- **角色授权**：`identity_registry.json` 里的每个角色都要在 `character_likeness.characters[]` 留记录。原创合成角色写 `synthetic_character`；真人/演员/授权形象必须写授权 evidence。
- **声音克隆**：未克隆写 `synthetic_voice/no_clone`；一旦使用真人参考音或零样本克隆，必须 `status=authorized_clone`、`authorization_status=approved`、`evidence` 非空。
- **平台审核**：发布候选必须写 `platform_review.targets[]`，含平台、地区、规则 profile、检查日期、版权审核、内容分级审核。`publish_candidate` 在 image/video 阶段只报 INFO 待办，compose/review/release 前转 BLOCK；`paid_distribution` 从任何阶段开始都按发布严格口径 BLOCK。
- **生成后端使用限制（G-V3·2026-06-24·非阻断提醒）**：选生图/出视频后端时注意平台条款——**即梦/Dreamina 2026-02-15 起**限制上传真人脸/已知 IP/动漫角色形象并加隐形水印（真人/授权形象镜须在 `character_likeness` 留授权 evidence；隐形水印归 `ai_labeling` 非阻断待办）；**Sora 已 EOL**（Web/App 2026-04-26 停、API 2026-09-24 日落），仅旧项目 manual。条款会变，详见 `n2d/references/模型矩阵.md`「后端平台使用限制」，付费批量前复核。
- **广电备案/分级/播前审核（2026 新规·境内投放）**：`regulatory_filing` 段——`regime=NRTA_网络微短剧`、`tier`（分级：重点/普通/其他）、`planning_filing_no`（规划备案号）、`release_filing_no`（上线备案号）、`pre_broadcast_review`（pending/ready/done/not_applicable）、`filed_at`。**2026.3 起广电总局把全部 AIGC 作品纳入分级 + 播前审核**（已下架 25000+ 集），网络微短剧"先备案后上线"。检查：`pre_broadcast_review` 不能停 `pending`、review 前须 `done`；`paid_distribution`/review 前 `release_filing_no` 必填不留 TODO。`publish_candidate` 的 image/video 阶段只报 INFO 待办，compose/review/release 前转 BLOCK；`paid_distribution` 从任何阶段开始都按发布严格口径 BLOCK。纯海外/内部预览可 `applicable=false` 并在 `notes` 写理由——与 `platform_review` 同列内部 demo 免检域（`internal_only` 时 BLOCK 降 INFO）。**平台自审 ≠ 监管备案**，两者都要过。**2026 监管硬化（P3·2026-06-26 补登）**：广电 2026-04 起未备案动画微短剧强制下架、备案过审率<30%、约 65% 收整改单；红果 2026-05 下架约 2.1 万剧（~95% 漫剧）并**明令禁止「全自动零审核」、强制每集 AI 成片人工终审**。新增 `regulatory_filing.platform_human_review`（红果每集人审 attest·未 done 出 INFO 提醒·**批量产线尤须逐集人审**，不阻断主流程=尊重「人审在工具外做」的设计）。
- **出海本地化**：海外平台或非 CN 地区必须 `localization.status=ready/done`，且字幕语言覆盖目标语言。它和 `platform_review` / `regulatory_filing` 同属发布边界域：`publish_candidate` 在 image/video 阶段只报 INFO，compose/review/release 或 `paid_distribution` 时 BLOCK。
- **AI 生成合成内容标识（非阻断发布待办）**：`ai_labeling` 段——`applicable`、`explicit_label`（显式可见标签·`text`/`position`/`status`）、`implicit_metadata`（元数据隐式标识·`service_provider_code`/`content_id`/`applied`）、`digital_watermark`（鼓励项·可外置）、`explicit_label.prominent_label_spec`（**2026 广电显著标识规格自查·P3**：成片前 5s 内出现、持续≥3s、显著位、经切条/二创/出海裁剪后仍存活，否则整片可能被下架·未确认出 INFO·非阻断）。`n2d-compose/ai_label.py` 可在导出后 best-effort 落显式角标 + 写元数据并回写 `status=done`/`applied=true`；失败、缺配置、未落标、未做数字水印或平台侧披露都只能出 INFO 待办，**不得阻断 compose/review、进度回写、dashboard 记账或后续集推进**。发布前按目标地区/平台补齐；严格 GB 45438 字节级扩展盒格式属工具外/后续专用编码器工作。

## 前置原则

- 任何 `unknown/pending/unlicensed` 都不得进入付费 image/video/compose；但仓库创作源文本 / 同源改编不得默认为 `unknown`，应按设计宪法 D4 自动登记 `original`。
- **发布边界口径（已工程化）**：`distribution_intent=internal_only` 时，`compliance.py --check` 与 review gate 把 `platform_review` / `localization`（出海本地化）/ `regulatory_filing`（广电备案）域的 BLOCK 降为 INFO 并加注「内部 demo 免检，转投放前需补」；`publish_candidate` 在 image/video 阶段把这些发布域列为 INFO，compose/review/release 前转 BLOCK；`paid_distribution` 从 image/video 开始就严格 BLOCK。`compliance_verdict` 会把字段级结果归并成 `blocked / internal-only / demo-only / pass`，`release_verdict` 直接消费这个结构化口径。**角色/声音授权检查照常 BLOCK**——授权问题不因内部使用或早期阶段而豁免，且为日后转投放留底。判定同源于契约 `COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS` / `COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS`。
- 平台规则会变：`policy_profile` 必须带检查日期，例如 `youtube_policy_2026-06-08`，不要把平台条款写死在脚本里。
- **AI 标识非阻断铁律**：显式可见标签、元数据隐式标识、数字水印、平台侧 AIGC 披露和 C2PA Content Credentials 全部不得成为 n2d 主流程 blocker。`n2d-compose/ai_label.py` 只做 best-effort；`compliance.py --check` 与 review gate 只出 INFO。发布前若目标地区/平台要求标识，由使用方在发布工序或工具外补齐。
- **做完 ≠ 可发布**：`release_verdict.py` 的 `delivery_states` 把技术交付和发行 profile 分开。AI 标识、备案、本地化、平台审核只影响 `publish_ready_cn / publish_ready_overseas / publish_ready_commercial`；不会把已存在且通过技术 QA 的 `clip_delivery_complete / master_delivery_complete` 改回未完成。版权、角色肖像、真人声音克隆等授权不是“发布装饰”，仍按相应生产/发布边界 fail-closed。

## 参考基准

- 广电总局 2026 专项治理：自 2026.3 起把全部 AIGC 作品纳入分级 + 播前审核，网络微短剧需规划/上线备案号、先备案后上线（已下架 25000+ 违规集）。`regulatory_filing` 段对应此。
- **中国《人工智能生成合成内容标识办法》2025-09-01 生效 + 强制国标 GB 45438-2025**：显式标签、元数据隐式标识、数字水印和平台侧 AIGC 披露在本线统一视为发布前待办。`ai_labeling` 段 + `n2d-compose/ai_label.py` 只提供自动化辅助，不构成主流程放行条件。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 在成片后才想起来做合规检查 | 必须在付费出图/出视频前跑 `--init` 并补齐策略，gate 会在生产入口前置阻断 |
| 反复要求用户证明本仓源文本/同源改编权 | 按设计宪法 D4 默认用户为原著作者，`rights.source_text` / `rights.adaptation` 写 `original` 留痕；只有明确第三方来源才要求 evidence/ref |
| 把 internal_only 当作完全免检 | `internal_only` 只免检平台审核/出海本地化/广电备案；角色/声音授权检查照常 BLOCK |
| 把 publish_candidate 的发布待办提前硬拦出图/出视频 | `publish_candidate` 的平台/本地化/备案缺口在 image/video 只报 INFO；compose/review/release 前必须补齐，否则 BLOCK |
| 平台过审就以为能投 | 平台自审 ≠ 广电备案；2026 起境内网络微短剧须先过广电分级+播前审核（`regulatory_filing.release_filing_no` + `pre_broadcast_review=done`）才能投放 |
| 声音克隆只声明未提供证据 | 必须提供 `evidence` 字段说明授权来源，否则 gate 阻断 |
| 随意更改 policy_profile 为不带日期的泛称 | `policy_profile` 必须带检查日期（如 `youtube_policy_2026-06-08`），防平台规则过期 |
| 跨项目直接复制 compliance_manifest.json | 每个项目的源文本、素材和授权情况不同，必须针对本项目单独 `--init` 并确认 |
