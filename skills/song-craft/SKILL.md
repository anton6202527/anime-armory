---
name: song-craft
description: Shared machine contracts and deterministic helpers for the song-* skill family — song project _meta/_设置/_进度 fields, user choice points, stage table, take-manifest conventions, and AI audio usage disclosure. Other song-* skills reference these by file path; users can also invoke directly for song pipeline contract, take manifest, or AI usage disclosure questions. Triggers song contract, song-craft, 写歌合约, 多版挑版, takes_manifest, AI音频使用披露, 歌曲合规留痕.
---

# song-craft — 写歌线共享契约

`song-craft` 是 `song-*` 家族的机器单一真值源，不直接写歌、不直接生成音频。它只沉淀可复用的字段、选择点、状态表和合规留痕脚本，避免每个 skill 各自硬写一套。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md` / `_meta.json`、路由阶段、生成多版 take manifest 时 |
| AI 音频使用披露 | `scripts/ai_usage.py` | 发布、交平台、交 MV 前记录歌词/音频/音色的 AI 使用情况 |

## 共享脚本

```bash
python3 skills/song-craft/scripts/ai_usage.py "<写歌作品根>" \
  --audio-mode AI-generated \
  --lyrics-mode AI-generated \
  --publish-target 抖音
```

输出：
- `合规/ai_usage.json`
- `合规/AI使用说明.md`

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、脚本不伪装云端自动化 B4、阶段回写 B5、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../docs/skill-design-principles.md)，此处只列 song 线特有原则。song 的选择点目录：`skills/song-craft/references/选择点与偏好.md`。

- **多版是默认工程事实**：音乐生成随机性高，正式定稿应从 `歌/takes_manifest.json` 记录的多版里挑，不把第一版默认为成品。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 将选择点（如 BPM/调性）直接写死在提示词中 | 统一从 `_设置.md` 读取，确保整个管线的私有偏好可以被沉默沿用或跨环节修改 |
| 忘记运行 `ai_usage.py` 留痕 | 发布或交接给 MV 管线之前，必须进行 AI 使用披露，否则可能会被下游质检驳回 |
