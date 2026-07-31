---
name: song-craft
description: Shared machine contracts and deterministic helpers for the song-* skill family — song project _meta/_设置/_进度 fields, user choice points, default workflow, A&R brief, reference boundaries, melody/chord packets, take-manifest conventions, rights metadata, release pack, and AI audio usage disclosure. Other song-* skills reference these by file path; users can also invoke directly for song pipeline contract, take manifest, or AI usage disclosure questions. Triggers song contract, song-craft, 写歌合约, 默认写歌流程, A&R简报, 参考曲边界, 和弦草图, 多版挑版, takes_manifest, AI音频使用披露, 歌曲合规留痕, split sheet, release pack.
---

# song-craft — 写歌线共享契约

`song-craft` 是 `song-*` 家族的机器单一真值源，不直接写歌、不直接生成音频。它只沉淀可复用的字段、选择点、状态表和合规留痕脚本，避免每个 skill 各自硬写一套。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md` / `_meta.json`、路由阶段、生成多版 take manifest 时 |
| 默认工作流 | `scripts/song_workflow.py` | 从 A&R 简报到发布回测，检查每步证据并给下一步命令 |
| A&R 简报 | `scripts/song_brief.py` | 写 `创作/song_brief.json`，固化目标听众、核心承诺、hook 截止时间、声音身份和成功指标 |
| 参考曲边界 | `scripts/reference_pack.py` | 写 `素材/reference_pack.json`，记录参考曲用途与禁止模仿边界 |
| 旋律/和声草图 | `scripts/melody_chord_packet.py` | 写 `歌/song_form.json`、`chord_sheet.md`、`topline_notes.md`，给作曲任务包提供曲式/和声/topline 方向 |
| 歌词 prosody | `scripts/lyric_prosody_check.py` | 写 `词/lyric_prosody.json`，检查 hook、标题、副歌、字密度和乐句对称 |
| 权益元数据 | `scripts/rights_metadata.py` | 写 `合规/rights_metadata.json` + `split_sheet.md`，记录词曲 split、ISRC/ISWC/PRO/MLC/SoundExchange 状态 |
| 发布交付包 | `scripts/release_pack.py` | 写 `导出/release_pack.json`，绑定音频、歌词、take、母带、AI 披露、权益元数据 hash |
| 阶段质量闸门 | `scripts/quality_gate.py` | compose/select 前验证上游证据、六维试听与音频 hash；例外必须写理由 |
| 母版格式交付 | `scripts/master_delivery.py` | 从 `混音/pre_master.wav` 生成无隐式响度归一的 24-bit PCM `导出/master.wav` 与 hash receipt |
| 发行级元数据 | `scripts/release_metadata.py` | 分离 track/release metadata：artist roles、language、explicit、date、territories、P/C line 与标识符 |
| AI 音频使用披露 | `scripts/ai_usage.py` | 发布或对外交付前记录歌词/旋律/编曲/人声/混母等组件级 AI 使用情况 |

## 共享脚本

```bash
python3 skills/song/song-craft/scripts/song_workflow.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/song_brief.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/reference_pack.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/lyric_prosody_check.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/melody_chord_packet.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/quality_gate.py "<写歌作品根>" --stage compose --write
python3 skills/song/song-craft/scripts/master_delivery.py "<写歌作品根>"
python3 skills/song/song-craft/scripts/release_metadata.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/rights_metadata.py "<写歌作品根>" \
  --rights-status original --derivative-type original --sample-usage-status none \
  --voice-authorization-status synthetic --write
python3 skills/song/song-craft/scripts/release_pack.py "<写歌作品根>" --write
python3 skills/song/song-craft/scripts/ai_usage.py "<写歌作品根>" \
  --audio-mode AI-generated \
  --lyrics-mode AI-generated \
  --publish-target 抖音 \
  --component "lyrics|AI-assisted|人工改词|LLM" \
  --component "composition_arrangement_vocal|AI-generated|人工挑版和审听|Suno"
```

输出：
- `合规/ai_usage.json`
- `合规/AI使用说明.md`

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、脚本不伪装云端自动化 B4、阶段回写 B5、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../docs/skill-design-principles.md)，此处只列 song 线特有原则。song 的选择点目录：`skills/song/song-craft/references/选择点与偏好.md`。

- **多版是默认工程事实**：音乐生成随机性高，正式定稿应从 `歌/takes_manifest.json` 记录的多版里挑，不把第一版默认为成品。
- **标准分层**：硬标准、项目合同、平台建议、人判标准不得混为一谈。逐阶段定义与官方依据见 `references/production-standards.md`。
- **选中版不是母版**：select 只产生带 hash 的 `pre_master.wav`；正式交付必须再生成 `导出/master.wav`、跑 BS.1770 检查并重建 release pack。
- **发布不是只有 wav**：正式交付必须同时有母带检查、权益元数据、AI 使用披露和 release pack；缺任一项都不能声称“发行就绪”。
- **参考曲只作方向**：reference pack 只能迁移情绪、能量曲线、配器类别和段落功能；不得复刻旋律、歌词、hook/riff、声纹或标志性编曲。
- **作品卡片字段（synopsis / cover）**：立项脚本在 `_meta.json` 固化 `synopsis`（一句话简介，≤240 字，取自 `创作/song_brief.json` 核心承诺，缺失时用 `theme`+`genre/mood` 组一句，占位后续回填）。song 是纯音频线、无图片产物，故 `cover` 恒为 `null`、不出封面，桌面卡片自动回退产线图标占位。写入用 `write_if_absent` 语义只补缺、不覆盖用户已填内容。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 将选择点（如 BPM/调性）直接写死在提示词中 | 统一从 `_设置.md` 读取，确保整个管线的私有偏好可以被沉默沿用或跨环节修改 |
| 忘记运行 `ai_usage.py` 留痕 | 发布或对外交付前必须进行 AI 使用披露，否则可能会被交付质检驳回 |
| 只给成品 wav，不给 split/rights 元数据 | 跑 `rights_metadata.py` 和 `release_pack.py`，否则版税、登记和平台交付都无法追踪 |
