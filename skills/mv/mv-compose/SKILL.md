---
name: mv-compose
description: MV 专业合成与交付 — 严格按 timeline 拼接选中 clips，以正式歌为主音轴，烧录字幕，先生成 ProRes/PCM mezzanine master，再派生 BT.709/H.264/48kHz MP4，运行 delivery QC 与 provenance。Use when asked to 合成MV / 出MV成片 / 母版 / 交付QC / 烧卡拉OK字幕 / MV导出. Triggers 合成MV, MV成片, MV母版, 交付QC, 卡拉OK烧录, mv-compose.
---

# mv-compose — MV 合成成片（mv 系列·自包含）

把一支 MV 的 `分镜/timeline_manifest.json` 选中 clips + `歌/song.*`(整首歌=主音轨) + (可选)`字幕/karaoke.ass`(卡拉OK逐字字幕) 烧成 `成片_MV.mp4`。默认严格服从 timeline，不按目录猜顺序；临时救场才显式传 `--allow-fallback`。

> **完全独立**：本 skill 只用通用工具 ffmpeg + 自带 `render_lyrics.py`。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`合成画幅`。

## 核心原则
- **歌是主音轴**：MV 用整首 `歌/song.*` 作主音轨，支持 `.wav/.mp3/.m4a/.flac`；clip 自带音效一律静音/极低。不做配音 ducking。
- **timeline + OTIO 驱动剪辑**：默认读 `timeline_manifest.json`，开跑先刷新 V1 画面 + A1 正式歌曲的 `timeline.otio`/receipt，再过 compose gate。缺 timeline/已选视频/新鲜 OTIO/签收会阻断；`--allow-fallback` 只能按目录写预览，不能成为正式交付。
- **卡点驱动剪辑**：剪辑点对齐 `节拍/beatgrid.json`（副歌踩鼓点切、verse 缓）。**clip 时长由 mv-plan/mv-video 在上游就对齐**（出 clip 时按段落/鼓点定时长）；compose 保留不等长化，并校验总时长≈歌长。
- **卡拉OK字幕**：优先 `.ass` 逐字高亮（需 ffmpeg 带 **libass**）；无 libass → 用 **mv 自带 `render_lyrics.py`**（Pillow 渲染逐行 PNG → overlay），从 `.lrc`/`.ass` 取行级时间。
- **接缝意图在锁版前决定**：`beat_cut`/`section_break`/`match_action`/`terminal` 已由 plan、video QC 与 picture lock 分类签收。正式 shell 保留锁定切点，不自动给问题接缝加溶解；需 dissolve/空镜时回 timeline/OTIO 明确编辑决定或补镜，不能在最终导出时偷偷“美化”。
- **优雅降级**：无字幕 → 纯歌+画面；无 timeline / 缺视频不静默降级，除非显式 `--allow-fallback`。
- **母版优先**：先输出 `成片_MV_master.mov`（ProRes 422 HQ / 10-bit / PCM 48kHz），再派生 BT.709、H.264 High、yuv420p、AAC 48kHz 的平台 MP4。
- **母版前不多损一代**：画幅/时长统一和拼接的内部中间件也用 ProRes 422 HQ/10-bit；不先压 H.264 再“升回”ProRes。H.264 只出现在最终平台派生版。
- **色彩边界**：视频 QC 会识别 PQ/HLG/BT.2020 并阻断未显式 tone-map 的 HDR 素材；无标签输入需按 Rec.709 人工确认，不能把“补输出标签”当作色彩转换。
- **帧率不拍脑袋改 30**：默认继承首个锁版 clip 的帧率，也可用 `MV_OUTPUT_FPS` 明确指定。
- **不截歌、不批量变速**：默认素材长则 trim、短则尾帧 hold；只有逐镜显式 `retime` 才 setpts。画面与歌差值必须 ≤ `max(100ms, 2帧)`，之后把最后画面精确 hold 到歌曲尾；不使用 `-shortest` 吃掉尾音。
- **交付可追溯**：合成后强制运行 `delivery_qc.py` 与 `provenance.py`，记录编码/音轨/色彩/响度和所有 ingredient hash。

## 输入前置（作品根=`创作区/制MV/<曲名>/`）
- `分镜/timeline_manifest.json`（mv-plan 产、mv-video 挑版后更新；必需，显式 fallback 除外）
- `出视频/视频/*.mp4`（mv-video 产；显式 fallback 时才按目录顺序兜底）
- `歌/song.*`（用户提供或本项目内维护；必需，支持 wav/mp3/m4a/flac）
- `节拍/beatgrid.json`（mv-beat 产；默认必需，显式 fallback 时才允许缺失）
- `字幕/karaoke.ass` 或 `字幕/lyrics.lrc`（mv-lyric-sync 产；可选）
- 正式项目还要求新鲜的 inherit/video QC、视频语义签收和绑定当前 animatic 的 picture lock。

若 `_设置.md` 为 `歌曲输入时序=后配歌曲`，本阶段只能在最终 `歌/song.*` 入库、`mv-beat` 和正式 `mv-plan` 完成后执行；rough 视觉蓝图不能直接合成。

## 工作流
```bash
bash <skill>/mv_compose.sh <制MV作品根> [aspect=16:9|9:16|1:1]
bash <skill>/mv_compose.sh <制MV作品根> 16:9 --allow-fallback  # 临时救场才用
# 真歌轨：歌/song.* 已在；字幕自动探测 .ass→.lrc→无
```
1. 正式模式先刷新 OTIO/receipt，再过 `mv-craft/scripts/gate.py compose`：除最终歌、beatgrid、plan/timeline、已选视频外，还校验 semantic prompts、pacing、picture lock、视频语义签收和 OTIO 编辑合同；启用字幕/唱演时才要求歌词与 alignment。fallback 跳过这些检查，但只产 `预览/fallback_preview.mp4`。
2. 统一目标画幅，帧率继承锁版素材或由 `MV_OUTPUT_FPS` 指定 → 拼接。
3. 校验拼接总时长 vs `歌/song.*`：正式模式超过 `max(100ms, 2帧)` 直接拒产；回 mv-plan/mv-video 修时间线。通过后只补亚帧级尾帧，不截歌。
4. 铺 `歌/song.*` 为唯一主音轨（clip 原声静音）。
5. 字幕：`.ass`(有 libass)烧录 / 无 libass → 调本 skill `render_lyrics.py`(Pillow 逐行 PNG overlay) / 无字幕则跳过。
6. 输出 ProRes/PCM 母版，再派生 SDR MP4。
7. 强制 delivery QC、全链路 provenance；QC 对比输入歌与输出的时长、integrated loudness/true peak，防止母带被无意改响或截短。可另用 `provenance.py --embed-c2pa` 生成带 Content Credentials 的副本。
8. 全部通过后回写 `_进度.md`。

## 依赖（仅通用工具，无 skill 依赖）
- **ffmpeg**（必需）。`.ass` 卡拉OK逐字需 libass 编译版（`ffmpeg -filters | grep subtitles`）。
- **Pillow**（无 libass 时的字幕降级，`render_lyrics.py` 用）。

## 详细参考
- 调用 / 画幅 / 字幕降级：`references/usage.md`
- 上游：本项目输入歌 · `mv-beat`(beatgrid) · `mv-lyric-sync`(卡拉OK) · `mv-video`(clips)

## 常见错误
| 错误 | 纠正 |
|---|---|
| 把 clip 拉成等长 | beatgrid 卡点曲线就是 MV 节奏，保留不等长 |
| clip 总时长和歌对不上 | 上游 mv-plan/mv-video 修时间线；正式 compose 会拒产，不用 `-shortest` 或批量变速掩盖 |
| 合成顺序跟分镜不一致 | 用 `mv-video/scripts/video_jobs.py --select` 更新 timeline；compose 优先读 `timeline_manifest.json` |
| 缺 timeline 时让 compose 猜顺序 | 默认会阻断；只有明确知道是临时救场才传 `--allow-fallback` |
| 拿 .ass 在无 libass 的 ffmpeg 上烧 | 自动降级本 skill `render_lyrics.py`（Pillow overlay） |
| 用配音 ducking 逻辑做 MV | MV 主音轴是整首歌，不 ducking |
| 到最终导出才给坏接缝统一加溶解 | 回 picture lock/OTIO 明确剪辑决定或补镜；compose 不偷偷改已经锁定的切点 |
| 后配歌曲 rough 蓝图没补最终歌就合成 | 先补 `歌/song.*`，跑 `mv-beat` 与正式 `mv-plan`，再合成 |
| 想用别的合成脚本 | 本系列完全独立，用自带 mv_compose.sh + render_lyrics.py |
