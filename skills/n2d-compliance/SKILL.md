---
name: n2d-compliance
description: P0 compliance and rights preflight for novel2drama/n2d. Create and validate 合规/compliance_manifest.json before paid image/video/compose/review gates, covering source/adaptation copyright, character likeness authorization, voice cloning authorization, AI disclosure, visible/metadata/C2PA or platform watermark strategy, target-platform review, and overseas localization. Use when asked for 合规前置, 版权前置, 角色授权, 声音克隆授权, AI标识, 水印合规, 平台审核, 出海本地化, compliance gate, copyright gate.
---

# n2d-compliance — 合规与版权前置

`n2d-compliance` 是 n2d 的 P0 合规包入口。它不做法律判断，也不替代律师或平台最终审核；它把“必须先确认的权利与披露事项”变成机器可读文件，让 `n2d-review/scripts/gate.py` 在出图、出视频、合成、审查前阻断。

核心文件：

```text
制漫剧/<剧名>/合规/compliance_manifest.json
```

## 输入 / 输出 / 读写边界

- **输入**：源文本/改编权信息、identity registry 角色、声音克隆/素材授权、AI 标识/水印/平台审核策略、目标地区。
- **输出**：`合规/compliance_manifest.json` 和 `--check` 结果；dashboard gate 会把阻断写入生产数据。
- **读写边界**：只建立/校验合规包；不替代法律意见、不生成媒体、不改生产阶段。
- **契约关系**：internal_only 免检范围、必填域和 gate 阶段阻断口径与 `skills/common/n2d_contract.py` 保持同源。

## 标准命令

初始化模板：

```bash
python3 skills/n2d-compliance/scripts/compliance.py <作品根> --init
```

检查合规包：

```bash
python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第1集 --check
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image
```

`dashboard.py gate` 是生产硬闸门入口（内部调用 `gate.py --json` 并把 QA 入账）；`compliance.py --check` 用于提前看缺口。

## 必填面

- **版权/改编权**：源文本、改编权、BGM、音效、字体。`licensed/user_declared/stock_licensed` 必须写 evidence/ref。
- **角色授权**：`identity_registry.json` 里的每个角色都要在 `character_likeness.characters[]` 留记录。原创合成角色写 `synthetic_character`；真人/演员/授权形象必须写授权 evidence。
- **声音克隆**：未克隆写 `synthetic_voice/no_clone`；一旦使用真人参考音或零样本克隆，必须 `status=authorized_clone`、`authorization_status=approved`、`evidence` 非空。
- **AI 标识**：`ai_disclosure.required=true`，并声明可见标识、元数据标识、C2PA/Content Credentials 或平台隐式标识策略。
- **水印**：合成前至少 `planned/ready`；review 前 `watermark.ai_visible.status=done` 且登记本集最终水印资产。
- **平台审核**：发布候选必须写 `platform_review.targets[]`，含平台、地区、规则 profile、检查日期、版权审核、AI 披露上传、内容分级审核。
- **出海本地化**：海外平台或非 CN 地区必须 `localization.status=ready/done`，且字幕语言覆盖目标语言。

## 前置原则

- 任何 `unknown/pending/unlicensed` 都不得进入付费 image/video/compose。
- **internal_only 免检范围（已工程化）**：`distribution_intent=internal_only` 时，`compliance.py --check` 与 review gate 把 `platform_review` / `localization`（出海本地化）域的 BLOCK 降为 INFO 并加注「内部 demo 免检，转投放前需补」；**角色/声音授权、AI 标识、水印检查照常 BLOCK**——授权问题不因内部使用而豁免，且为日后转投放留底。判定同源于契约 `COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS` / `COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS`。
- 平台规则会变：`policy_profile` 必须带检查日期，例如 `youtube_ai_disclosure_2026-06-08`，不要把平台条款写死在脚本里。
- 中国投放默认需要显式 AI 标识 + 元数据/隐式标识策略；海外平台按目标平台上传流程做 AI disclosure。

## 参考基准

- YouTube 要求对真实感 AI 生成或显著 AI 修改内容做上传披露。
- TikTok 要求真实感 AIGC 标注，并会利用 C2PA Content Credentials 自动标记。
- 中国《人工智能生成合成内容标识办法》把 AI 标识分为显式和隐式。
- C2PA/Content Credentials 是跨平台 provenance 元数据方向；本地无法签发时，也要在 manifest 里写 `not_supported` 和平台侧替代方案。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 在成片后才想起来做合规检查 | 必须在付费出图/出视频前跑 `--init` 并补齐策略，gate 会在生产入口前置阻断 |
| 把 internal_only 当作完全免检 | `internal_only` 只免检平台审核和出海本地化；角色/声音授权、AI 标识、水印检查照常 BLOCK |
| 声音克隆只声明未提供证据 | 必须提供 `evidence` 字段说明授权来源，否则 gate 阻断 |
| 随意更改 policy_profile 为不带日期的泛称 | `policy_profile` 必须带检查日期（如 `youtube_ai_disclosure_2026-06-08`），防平台规则过期 |
| 跨项目直接复制 compliance_manifest.json | 每个项目的源文本、素材和授权情况不同，必须针对本项目单独 `--init` 并确认 |
