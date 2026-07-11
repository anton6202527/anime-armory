---
name: mv-lyric-sync
description: 制MV 卡拉OK字幕 — 用 whisperx 把已知歌词强制对齐到成品歌或 vocals 人声轨，按字符级时间戳和原歌词行映射，产自适应画幅的 karaoke.ass、lyrics.lrc 与置信度报告。Use when asked to 卡拉OK字幕 / 歌词对齐 / 字符级时间戳 / 生成LRC/ASS / 对齐报告. Triggers 卡拉OK, 歌词字幕, 歌词对齐, 字符级对齐, LRC, ASS字幕, 对齐报告, mv-lyric-sync.
---

# mv-lyric-sync — 卡拉OK字幕（制MV 线）

把 `词/lyrics.md` 的歌词**强制对齐**到 `歌/song.*`（或更干净的 vocals 人声轨），产 `字幕/karaoke.ass`（逐字 `\k` 高亮）+ `字幕/lyrics.lrc`（逐行）+ `字幕/alignment_report.json`（QA 对账）。**自包含**，只用通用工具 whisperx。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`字幕语言`、`卡拉OK样式`（颜色/字体偏好）、`强制对齐引擎`（本地 cpu/gpu 或 API，如果扩展支持的话）。

## 依赖
```bash
pip install whisperx   # 首次下 wav2vec2 对齐模型；CPU 可跑(慢)，有 CUDA 更快
```

## 用法
```bash
python3 <skill>/scripts/align.py 创作区/制MV/<曲名> [--lang zh] [--device cpu]
python3 <skill>/scripts/align.py 创作区/制MV/<曲名> --audio 创作区/制MV/<曲名>/歌/vocals.wav
```
- 读 `歌/song.*`（或 `--audio` 指定 vocals）+ `词/lyrics.md`（剥段落标签/占位）→ 强制对齐（拿**已知歌词**当 transcript，不靠转写猜词）→ 写 `字幕/karaoke.ass` + `lyrics.lrc` + `alignment_report.json`。

## 工作流
1. 确认 `歌/song.*` + `词/lyrics.md`（定稿）就位。
   - 若 `_设置.md` 为 `歌曲输入时序=后配歌曲` 且最终 `歌/song.*` 未入库，先停下：本阶段不能对 rough 蓝图或估算歌词做正式对齐。
2. （可选）人声更干净：先用 demucs 分离出 vocals，再用 `--audio 歌/vocals.wav` 对齐（对齐更准）。
3. 跑 align.py。脚本入口会先过 `mv-craft/scripts/gate.py lyric_sync`：缺最终 `歌/song.*`、`词/lyrics.md` 或歌词行为空时直接阻断。
4. 看 `alignment_confidence`、逐行 `line_confidence` 与覆盖率。低于 90% 或任一行低于 85% 时只落报告、不推进阶段。
5. ASS 分辨率、字号和安全区从目标画幅生成；确需带低置信度进入人工流程时显式 `--allow-low-confidence` 留痕。

## 产物
- `karaoke.ass`：逐字高亮（mv-compose 有 libass 时 `subtitles=` 烧）。
- `lyrics.lrc`：逐行（mv-compose 无 libass 时走自带 `render_lyrics.py` Pillow overlay）。
- `alignment_report.json`：字符覆盖率、逐行置信度和警告，供 `mv-review` 机检引用。

## 常见错误
| 错误 | 纠正 |
|---|---|
| 歌词与实唱不一致致对齐乱 | lyrics.md 改成与实际演唱一致再跑 |
| 伴奏太响对齐不准 | 先 demucs 分离 vocals 再对齐 |
| 有字幕但 review 提示缺对齐报告 | 重跑新版 align.py，产 `alignment_report.json` |
| 没填词就跑 | 先补齐本项目 `词/lyrics.md` |
| 后配歌曲还没最终歌就对齐字幕 | 等用户补入最终 `歌/song.*` 后再跑 |
