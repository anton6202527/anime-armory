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

## 标准命令

初始化模板：

```bash
python3 skills/n2d-compliance/scripts/compliance.py <作品根> --init
```

检查合规包：

```bash
python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第1集 --check
python3 skills/n2d-review/scripts/gate.py <作品根> 第1集 --stage image
```

`gate.py` 才是硬闸门；`compliance.py --check` 用于提前看缺口。

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
- 内部测试可设置 `distribution_intent=internal_only`，gate 会跳过平台投放审核但提醒不得直接发布。
- 平台规则会变：`policy_profile` 必须带检查日期，例如 `youtube_ai_disclosure_2026-06-08`，不要把平台条款写死在脚本里。
- 中国投放默认需要显式 AI 标识 + 元数据/隐式标识策略；海外平台按目标平台上传流程做 AI disclosure。

## 参考基准

- YouTube 要求对真实感 AI 生成或显著 AI 修改内容做上传披露。
- TikTok 要求真实感 AIGC 标注，并会利用 C2PA Content Credentials 自动标记。
- 中国《人工智能生成合成内容标识办法》把 AI 标识分为显式和隐式。
- C2PA/Content Credentials 是跨平台 provenance 元数据方向；本地无法签发时，也要在 manifest 里写 `not_supported` 和平台侧替代方案。
