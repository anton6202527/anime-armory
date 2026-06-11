---
name: mv-craft
description: Shared machine contracts and deterministic helpers for the mv-* skill family — MV project _meta/_设置/_进度 fields, user choice points, clip/timeline manifest conventions, video job manifest conventions, and AI visual usage disclosure. Other mv-* skills reference these by file path; users can also invoke directly for MV pipeline contract, manifest, or AI usage disclosure questions. Triggers mv contract, mv-craft, MV合约, timeline_manifest, clip_plan, video_jobs, AI视觉使用披露, MV合规留痕.
---

# mv-craft — 制MV线共享契约

`mv-craft` 是 `mv-*` 家族的机器单一真值源，不生成画面、不出视频。它只沉淀字段、选择点、阶段表、manifest 约定和合规留痕脚本，避免 `mv-image` / `mv-video` / `mv-compose` 各自解释同一件事。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV用途`、`MV视觉风格`、`MV规划粒度`、`卡点策略`、`生图AI`、`MV一致性增强` 等。

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

- **选择点不写死**：MV 用途、视觉风格、规划粒度、卡点策略、生图后端、MV 一致性增强、视频后端、规格、画幅、AI 使用披露都读 `<作品根>/_设置.md`。
- **manifest 是源头**：clip 时长、转场、尾帧、prompt、已登记视频都落 manifest；`mv-compose` 不再凭文件名猜时间线。
- **不伪装云端自动化**：没有后端 SDK/凭证时，只生成稳定 job 包；外部生成后再登记。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 直接手工改写 manifest.json 内容 | manifest 文件是各 stage 传递数据的机器契约，手动修改极易破坏其字段规范，应通过对应的阶段脚本重新生成 |
| 发布前遗漏 ai_usage 留痕 | 作品在脱离管线并发布前，必须在合规/目录下调用披露脚本并填写具体授权模式，否则质检将失败 |
| 偏好设定硬编码 | 管线中的卡点策略/粒度等不可写死，须经由此处统一定义的方式并从 `_设置.md` 读取 |
