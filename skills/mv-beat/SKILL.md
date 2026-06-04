---
name: mv-beat
description: 制MV 卡点分析 — 用 librosa 检测成品歌的 BPM / beats / downbeats，生成 节拍/beatgrid.json，驱动下游剪辑卡点（副歌踩鼓点切）。mv 系列自包含。Use when asked to 分析卡点 / 卡点 / 提取节拍 / beatgrid / BPM. Triggers 卡点, 节拍分析, beatgrid, BPM, 踩点, mv-beat.
---

# mv-beat — 卡点分析（制MV 线）

检测 `制MV/<曲名>/歌/song.wav` 的节拍，产 `节拍/beatgrid.json`。下游 mv-video 用它定 clip 时长、mv-compose 用它卡点剪辑（**副歌踩 downbeats 切、verse 缓**）。**自包含**，只用通用工具 librosa。

## 依赖
```bash
pip install librosa soundfile   # Mac 友好，纯 CPU 可跑
```

## 用法
```bash
python3 <skill>/scripts/beat_detect.py 制MV/<曲名> [--meter 4]
```
产 `节拍/beatgrid.json`：`bpm` / `beats[]`(每拍秒) / `downbeats[]`(小节首) / `duration` / `sections[]`(留空，由 mv-lyric-sync 或人工填段落起始秒)。

## 工作流
1. 确认 `歌/song.*` 已就位（来自 写歌/ 或用户）。
2. 跑 beat_detect.py → beatgrid.json。
3. 校对 BPM 是否合理（偶尔会半速/倍速，肉眼听一下；不对手动改 bpm 并按 60/bpm 重排 beats，或用 `--meter` 调拍号）。
4. （可选）把段落起始秒填进 `sections`（intro/verse/chorus…），供 mv-image 段落↔画面映射。
5. 回写 `_进度.md` 卡点行 ✅。下一步 mv-image 出图。

## 卡点原则（喂给 mv-video / mv-compose）
- **副歌**：每个 downbeat 切一刀（强节奏感）；**verse**：缓，2-4 拍一切。
- **爽点/高潮**：对齐一个 downbeat，画面同帧砸下。
- clip 时长 = 相邻卡点之差（mv-video 出 clip 按此定时长，别等长）。

## 常见错误
| 错误 | 纠正 |
|---|---|
| BPM 被测成半速/倍速 | 听一下校正；改 bpm 重排或调 meter |
| 无歌就跑 | 先放入 `歌/song.*`（写歌线产或用户给） |
| clip 等长不卡点 | mv-video 按 beatgrid 相邻卡点定 clip 时长 |
| 想复用 n2d 脚本 | mv 系列独立，用自带 beat_detect.py |
