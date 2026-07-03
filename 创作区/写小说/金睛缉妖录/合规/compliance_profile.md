# 合规 Profile

- 生成日期：2026-06-30
- 项目：/Users/wesley/learn/anime-arsenal/创作区/写小说/金睛缉妖录
- 阻断：0
- 提醒：1
- input_fingerprint：`7197c7031e9acf0e321444e699f9885f7194021dcaa093065e0410f7d39c2635`

## Target Axes

- kdp: False
- china_public: True
- eu: False
- microdrama_cn: True
- outbound: False
- regions: GLOBAL

## Input Fingerprint

- chapters: 24 `f428c779def3b659c02cad1cbe4e06deec8044744c37801289a0757f669642f4`
- exports: 5 `e81cc06155c80ab304d4953dbfca8cba5fc952f347ae3c587c0f708e39a2a9cb`
- ai_usage: `a7c7d334c7d8690ae7e0e9f77220ecf2df8601bb65ba1014a16a659f86f36a1b`

## Requirements

| id | severity | status | reason | sources |
|---|---|---|---|---|
| cn_ai_labeling_plan | blocking | ok | 面向中国公开发布的 AI 生成/辅助内容需准备显式标识、隐式元数据标识和留痕方案。；本地确认：confirmed_at=2026-06-30；by=Codex 收尾质检；note=内部转制交接包已保留 合规/AI使用说明.md、合规/ai_usage.json 与 compliance_profile；公开上线/投放前在作品简介、交付清单或片尾执行 AI 辅助显式标识，并按 GB 45438-2025/平台要求补隐式元数据标识和留痕。 | SRC-CN-AI-LABEL-20260623, SRC-GB45438-20260623 |
| cn_microdrama_permit_or_record | warning | action_required | 小说侧只能预检；成片上线/引流前需按网络微短剧分层分类审核取得许可证或完成上线备案/登记并标注编号。 | SRC-NRTA-MICRODRAMA-20260623 |

## Source Provenance

- SRC-KDP-AI-20260623: Amazon KDP Content Guidelines - AI content (https://kdp.amazon.com/help/topic/G200672390)
- SRC-KDP-IP-20260623: Amazon KDP Intellectual Property Rights FAQ (https://kdp.amazon.com/help/topic/G200672400)
- SRC-CN-AI-LABEL-20260623: 人工智能生成合成内容标识办法 (https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm)
- SRC-GB45438-20260623: GB 45438-2025 网络安全技术 人工智能生成合成内容标识方法 (https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F32EA2A561F1886CD8D606513512D547)
- SRC-EU-AI-ACT-20260623: EU Code of Practice on Transparency of AI-Generated Content (https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)
- SRC-NRTA-MICRODRAMA-20260623: 国家广播电视总局办公厅关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知 (https://www.nrta.gov.cn/art/2025/2/5/art_113_70148.html)
