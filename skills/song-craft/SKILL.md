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

- **选择点不写死**：后端、用途、时长、语言、BPM、调性、生成版数、挑版策略、AI 使用披露都读 `<作品根>/_设置.md`，没有再按 `skills/_偏好约定.md` 处理。
- **脚本不伪装云端自动化**：没有凭证或后端 SDK 时，只生成稳定 prompt 包、take manifest 和合规留痕；真正调用 Suno/Udio/ACE-Step/DiffRhythm 由对应后端工具完成。
- **多版是默认工程事实**：音乐生成随机性高，正式定稿应从 `歌/takes_manifest.json` 记录的多版里挑，不把第一版默认为成品。
