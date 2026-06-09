---
name: mv-craft
description: Shared machine contracts and deterministic helpers for the mv-* skill family — MV project _meta/_设置/_进度 fields, user choice points, clip/timeline manifest conventions, video job manifest conventions, and AI visual usage disclosure. Other mv-* skills reference these by file path; users can also invoke directly for MV pipeline contract, manifest, or AI usage disclosure questions. Triggers mv contract, mv-craft, MV合约, timeline_manifest, clip_plan, video_jobs, AI视觉使用披露, MV合规留痕.
---

# mv-craft — 制MV线共享契约

`mv-craft` 是 `mv-*` 家族的机器单一真值源，不生成画面、不出视频。它只沉淀字段、选择点、阶段表、manifest 约定和合规留痕脚本，避免 `mv-image` / `mv-video` / `mv-compose` 各自解释同一件事。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md` / `_meta.json`、生成 clip/timeline/video job manifest 时 |
| AI 视觉使用披露 | `scripts/ai_usage.py` | 发布、交平台前记录输入歌、AI 生图/视频、换脸、水印/AI 标识等使用情况 |

## 共享脚本

```bash
python3 skills/mv-craft/scripts/ai_usage.py "<制MV作品根>" \
  --visual-mode AI-generated \
  --video-mode AI-generated \
  --publish-target 抖音
```

输出：
- `合规/ai_usage.json`
- `合规/AI使用说明.md`

## 设计原则

- **选择点不写死**：MV 用途、视觉风格、规划粒度、卡点策略、视频后端、规格、画幅、AI 使用披露都读 `<作品根>/_设置.md`。
- **manifest 是源头**：clip 时长、转场、尾帧、prompt、已登记视频都落 manifest；`mv-compose` 不再凭文件名猜时间线。
- **不伪装云端自动化**：没有后端 SDK/凭证时，只生成稳定 job 包；外部生成后再登记。
