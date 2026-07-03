---
name: mv-craft
description: Shared machine contracts and deterministic helpers for the mv-* skill family — MV project _meta/_设置/_进度 fields, user choice points including `歌曲输入时序` (先传音乐 vs 后配歌曲), clip/timeline manifest conventions, video job manifest conventions, and AI visual usage disclosure. Other mv-* skills reference these by file path; users can also invoke directly for MV pipeline contract, manifest, or AI usage disclosure questions. Triggers mv contract, mv-craft, MV合约, 歌曲输入时序, timeline_manifest, clip_plan, video_jobs, AI视觉使用披露, MV合规留痕.
---

# mv-craft — 制MV线共享契约

`mv-craft` 是 `mv-*` 家族的机器单一真值源，不生成画面、不出视频。它只沉淀字段、选择点、阶段表、manifest 约定和合规留痕脚本，避免 `mv-image` / `mv-video` / `mv-compose` 各自解释同一件事。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV用途`、`歌曲输入时序`、`MV视觉风格`、`MV规划粒度`、`卡点策略`、`生图AI`、`MV一致性增强` 等。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md` / `_meta.json`、按 `歌曲输入时序` 决定阶段顺序、生成 clip/timeline/video job manifest 时 |
| 阶段 gate | `scripts/gate.py` | `mv-plan` / `mv-video` / `mv-lyric-sync` / `mv-compose` 等正式阶段开跑前做确定性前置检查 |
| 进度回写 | `scripts/progress_set.py` + `scripts/mv_utils.py` | 阶段脚本完成后回写 `_进度.md`，并同步 `_meta.has_song/has_lyrics` |
| AI 视觉使用披露 | `scripts/ai_usage.py` | 发布、交平台前记录输入歌、AI 生图/视频等使用情况（仅项目留痕；AI 标识/披露/水印不由本流水线处理，移到工具之外按平台/地区法规自行处理） |

## 共享脚本

```bash
python3 skills/mv-craft/scripts/gate.py "<制MV作品根>" plan
python3 skills/mv-craft/scripts/progress_set.py "<制MV作品根>" plan

python3 skills/mv-craft/scripts/ai_usage.py "<制MV作品根>" \
  --visual-mode AI-generated \
  --video-mode AI-generated \
  --publish-target 抖音
```

输出：
- `合规/ai_usage.json`
- `合规/AI使用说明.md`

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、阶段回写 B5、脚本不伪装云端自动化 B4、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../docs/skill-design-principles.md)，此处只列 mv 线特有原则。mv 的选择点目录：`skills/mv-craft/references/选择点与偏好.md`。

- **manifest 是源头**：clip 时长、转场、尾帧、prompt、已登记视频都落 manifest；`mv-compose` 不再凭文件名猜时间线。
- **脚本先过 gate（本线前置条件）**：正式产物阶段默认调用 `scripts/gate.py`，缺最终 `歌/song.*`、歌词、beatgrid、正式视觉蓝图、首帧或已选视频时先停下。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 直接手工改写 manifest.json 内容 | manifest 文件是各 stage 传递数据的机器契约，手动修改极易破坏其字段规范，应通过对应的阶段脚本重新生成 |
| 发布前遗漏 ai_usage 留痕 | 作品在脱离管线并发布前，必须在合规/目录下调用披露脚本并填写具体授权模式，否则质检将失败 |
| 偏好设定硬编码 | 管线中的卡点策略/粒度等不可写死，须经由此处统一定义的方式并从 `_设置.md` 读取 |
| 绕过 gate 手工跑下游 | 先跑对应 stage gate；如果确实要临时兜底，必须显式传该阶段的 fallback 参数并在交付说明里标注 |
