---
name: mv-beat
description: 制MV 卡点分析 — 用 librosa 检测成品歌的 BPM / tempo_candidates / energy_map / beats / downbeats，生成 节拍/beatgrid.json，驱动下游 mv-plan/mv-video 剪辑卡点（副歌踩鼓点切）。mv 系列自包含。Use when asked to 分析卡点 / 卡点 / 提取节拍 / beatgrid / BPM. Triggers 卡点, 节拍分析, beatgrid, BPM, 踩点, mv-beat.
---

# mv-beat — 卡点分析（制MV 线）

检测 `制MV/<曲名>/歌/song.wav` 的节拍，产 `节拍/beatgrid.json`。下游 `mv-plan` 用它拆 clip/timeline，`mv-video` 用它定 clip 时长，`mv-compose` 用 timeline 顺序合成并提示卡点状态（**副歌踩 downbeats 切、verse 缓**）。**自包含**，只用通用工具 librosa。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`卡点策略`、`节拍提取后处理`（是否手动干预覆盖 librosa）。

## 依赖
```bash
pip install librosa soundfile   # Mac 友好，纯 CPU 可跑
```

## 用法
```bash
python3 <skill>/scripts/beat_detect.py 制MV/<曲名> [--meter 4]
```
产 `节拍/beatgrid.json`：
- `bpm` / `tempo_candidates[]`：主 BPM + 半速/倍速候选，便于人工校正。
- `beats[]` / `downbeats[]`：每拍与小节首秒点。
- `energy_map[]`：按秒聚合的能量/起音强度，给高能段和转场判断。
- `sections[]`：若 `_meta.structure` 已有，先按歌长等分成初始段落；之后可人工改为真实段落起止。
- `duration` / `meter` / `song`：基础对账字段。

## 工作流
1. 确认 `歌/song.*` 已就位（来自 写歌/ 或用户）。
2. 跑 beat_detect.py → beatgrid.json。
3. 校对 BPM 是否合理（偶尔会半速/倍速，肉眼听一下；不对手动改 bpm 并按 60/bpm 重排 beats，或用 `--meter` 调拍号）。
4. （可选）把 `sections` 改成真实段落起止（intro/verse/chorus…），供 `mv-plan` 更准地拆 clip。
5. 回写 `_进度.md` 卡点行 ✅。下一步 `mv-plan` 生成 `分镜/clip_plan.json`。

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
| `sections` 只是等分 | 人工把真实段落起止写回 `sections`，再跑 mv-plan |
| 想复用 n2d 脚本 | mv 系列独立，用自带 beat_detect.py |
