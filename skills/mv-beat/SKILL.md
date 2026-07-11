---
name: mv-beat
description: 制MV 卡点分析 — 用 librosa 的 HPSS/打击乐 onset 检测 BPM、动态 tempo、beats、估算小节相位与能量，人工确认 downbeat/段落后生成 beatgrid.json，驱动 mv-plan/mv-video。Use when asked to 分析卡点 / 卡点 / 提取节拍 / beatgrid / BPM. Triggers 卡点, 节拍分析, beatgrid, BPM, 踩点, mv-beat.
---

# mv-beat — 卡点分析（制MV 线）

检测 `创作区/制MV/<曲名>/歌/song.*` 的节拍，支持 wav/mp3/m4a/flac，产 `节拍/beatgrid.json`。下游 `mv-plan` 用它拆 clip/timeline，`mv-video` 用它定 clip 时长，`mv-compose` 用 timeline 顺序合成并提示卡点状态（**副歌踩 downbeats 切、verse 缓**）。**自包含**，只用通用工具 librosa。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`卡点策略`、`节拍提取后处理`（是否手动干预覆盖 librosa）。

## 依赖
```bash
pip install librosa soundfile   # Mac 友好，纯 CPU 可跑
```

## 用法
```bash
python3 <skill>/scripts/beat_detect.py 创作区/制MV/<曲名> --meter 4
python3 <skill>/scripts/beat_detect.py 创作区/制MV/<曲名> --meter 4 --downbeat-phase 2 --confirm-timing
```
产 `节拍/beatgrid.json`：
- `bpm` / `tempo_candidates[]`：主 BPM + 半速/倍速候选，便于人工校正。
- `beats[]` / `downbeats[]`：打击乐拍点与按 onset 相位估算的小节首；未确认时不是正式真值。
- `tempo_curve[]`：局部速度曲线；用于发现变速、rubato 和全局 BPM 不可靠的段落。
- `energy_map[]`：按秒聚合的能量/起音强度，给高能段和转场判断。
- `sections[]`：只消费 `_meta.section_timings` 的真实起止，不再把结构名按歌长等分伪装成段落检测。
- `timing_verified` / `downbeat_phase_confidence` / `downbeat_method`：正式 `mv-plan` 的证据字段。
- `duration` / `meter` / `song`：基础对账字段。

## 工作流
1. 确认 `歌/song.*` 已就位（用户提供或本项目内维护）。
   - 若 `_设置.md` 为 `歌曲输入时序=后配歌曲` 且 `歌/` 还没有最终音频，先停下：让用户补入最终音频，不能用估算节奏替代 beatgrid。
2. 跑 beat_detect.py → beatgrid.json。
3. 校对 BPM/动态 tempo、拍号和小节第一拍相位；把真实段落起止写入 `_meta.section_timings`。
4. 用 `--downbeat-phase N --confirm-timing` 重跑。正式项目 `timing_verified=false` 会被下游 gate 阻断。
5. 回写 `_进度.md` 卡点行 ✅。下一步 `mv-plan` 生成 `分镜/clip_plan.json`。

## 卡点原则（喂给 mv-video / mv-compose）
- **副歌**：每个 downbeat 切一刀（强节奏感）；**verse**：缓，2-4 拍一切。
- **爽点/高潮**：对齐一个 downbeat，画面同帧砸下。
- clip 时长 = 相邻卡点之差（mv-video 出 clip 按此定时长，别等长）。

## 常见错误
| 错误 | 纠正 |
|---|---|
| BPM 被测成半速/倍速 | 听一下校正；改 bpm 重排或调 meter |
| 无歌就跑 | 先放入 `歌/song.*`（用户提供或本项目内维护） |
| 后配歌曲路线用 rough 蓝图直接卡点 | 先补最终歌，再跑 beatgrid；rough 蓝图只服务视觉方向 |
| clip 等长不卡点 | mv-video 按 beatgrid 相邻卡点定 clip 时长 |
| 把 `beats[::4]` 当真 downbeat | 听辨并确认小节相位；用 `--downbeat-phase` 留痕，不能默认第一拍就是小节首 |
