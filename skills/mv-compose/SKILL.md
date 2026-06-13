---
name: mv-compose
description: MV 合成成片（mv 系列自包含，不依赖 n2d-compose）— 把 制MV/曲名/ 的 分镜/timeline_manifest.json 选中 clips（默认严格，不按目录猜；显式 --allow-fallback 才临时回退出视频/视频/文件顺序）+ 歌/song.*(整首歌作主音轨) + (可选)字幕/karaoke.ass 卡拉OK字幕烧成 成片_MV.mp4。剪辑点对齐 mv-plan/beatgrid，字幕缺失时优雅降级；无 libass 时用 mv 自带 render_lyrics.py。Use when asked to 合成MV / 出MV成片 / 歌轨合成 / 烧卡拉OK字幕 / MV导出. Triggers 合成MV, MV成片, 出MV, 卡拉OK烧录, 歌轨合成, mv-compose.
---

# mv-compose — MV 合成成片（mv 系列·自包含）

把一支 MV 的 `分镜/timeline_manifest.json` 选中 clips + `歌/song.*`(整首歌=主音轨) + (可选)`字幕/karaoke.ass`(卡拉OK逐字字幕) 烧成 `成片_MV.mp4`。默认严格服从 timeline，不按目录猜顺序；临时救场才显式传 `--allow-fallback`。

> **完全独立**：本 skill 不依赖 n2d-compose 或任何其他 skill；只用通用工具 ffmpeg + 自带 `render_lyrics.py`。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`合成画幅`。

## 核心原则
- **歌是主音轴**：MV 用整首 `歌/song.*` 作主音轨，支持 `.wav/.mp3/.m4a/.flac`；clip 自带音效一律静音/极低。不做配音 ducking。
- **timeline 驱动剪辑**：默认读 `分镜/timeline_manifest.json` 的 `clips[].video_path` 顺序。timeline 由 `mv-plan` 创建、由 `mv-video/scripts/video_jobs.py --select` 更新；缺 timeline 或缺已选视频会被 gate 阻断，只有显式 `--allow-fallback` 才按 `出视频/视频/*.mp4` 文件顺序临时退化拼接。
- **卡点驱动剪辑**：剪辑点对齐 `节拍/beatgrid.json`（副歌踩鼓点切、verse 缓）。**clip 时长由 mv-plan/mv-video 在上游就对齐**（出 clip 时按段落/鼓点定时长）；compose 保留不等长化，并校验总时长≈歌长。
- **卡拉OK字幕**：优先 `.ass` 逐字高亮（需 ffmpeg 带 **libass**）；无 libass → 用 **mv 自带 `render_lyrics.py`**（Pillow 渲染逐行 PNG → overlay），从 `.lrc`/`.ass` 取行级时间。
- **按转场类型接 clip，别盲拼**（接力链末端兜底）：读 `timeline_manifest.json` / `clip_plan.json` 每个接缝的 `transition` 决定接法——`卡点硬切 / 动作切 / 有尾帧接力的硬切` 直接硬切（踩 downbeat 同帧砸下最稳）；`空镜缓冲` 契约要缓冲但 `视频/` 缺对应空镜 clip → **停下报警**（缺料），别默默硬切；`闪白 / 光效切` 按 clip 自带处理；**非有意硬切又视觉跳变明显**的接缝可加 **0.1–0.3s 微交叉溶解**兜底（ffmpeg `xfade`，不依赖 libass，仅该接缝局部重编码、其余仍直拼）。**副歌踩鼓点的有意硬切不要加溶解**（会泄掉卡点冲击）。
- **优雅降级**：无字幕 → 纯歌+画面；无 timeline / 缺视频不静默降级，除非显式 `--allow-fallback`。

## 输入前置（作品根=`制MV/<曲名>/`）
- `分镜/timeline_manifest.json`（mv-plan 产、mv-video 挑版后更新；必需，显式 fallback 除外）
- `出视频/视频/*.mp4`（mv-video 产；显式 fallback 时才按目录顺序兜底）
- `歌/song.*`（song 线产出或用户上传；必需，支持 wav/mp3/m4a/flac）
- `节拍/beatgrid.json`（mv-beat 产；默认必需，显式 fallback 时才允许缺失）
- `字幕/karaoke.ass` 或 `字幕/lyrics.lrc`（mv-lyric-sync 产；可选）

若 `_设置.md` 为 `歌曲输入时序=后配歌曲`，本阶段只能在最终 `歌/song.*` 入库、`mv-beat` 和正式 `mv-plan` 完成后执行；rough 视觉蓝图不能直接合成。

## 工作流
```bash
bash <skill>/mv_compose.sh <制MV作品根> [aspect=16:9|9:16|1:1]
bash <skill>/mv_compose.sh <制MV作品根> 16:9 --allow-fallback  # 临时救场才用
# 真歌轨：歌/song.* 已在；字幕自动探测 .ass→.lrc→无
```
1. 先过 `mv-craft/scripts/gate.py compose`：缺最终歌、歌词、beatgrid、正式蓝图、clip_plan、timeline 或已选视频时停下。显式 `--allow-fallback` 会跳过 compose gate，并按目录顺序救场。
2. 统一画幅(默认 16:9 1920x1080，竖屏传 9:16)/30fps → 拼接。
3. 校验拼接总时长 vs `歌/song.*` 时长：差值大则告警（提示回 mv-plan/mv-video 按 beatgrid 调 clip 或补空镜）。
4. 铺 `歌/song.*` 为唯一主音轨（clip 原声静音）。
5. 字幕：`.ass`(有 libass)烧录 / 无 libass → 调本 skill `render_lyrics.py`(Pillow 逐行 PNG overlay) / 无字幕则跳过。
6. 输出 `成片_MV.mp4`；回写 `_进度.md` 成片行。

## 依赖（仅通用工具，无 skill 依赖）
- **ffmpeg**（必需）。`.ass` 卡拉OK逐字需 libass 编译版（`ffmpeg -filters | grep subtitles`）。
- **Pillow**（无 libass 时的字幕降级，`render_lyrics.py` 用）。

## 详细参考
- 调用 / 画幅 / 字幕降级：`references/usage.md`
- 上游：`song` 线或用户上传(歌) · `mv-beat`(beatgrid) · `mv-lyric-sync`(卡拉OK) · `mv-video`(clips)

## 常见错误
| 错误 | 纠正 |
|---|---|
| 把 clip 拉成等长 | beatgrid 卡点曲线就是 MV 节奏，保留不等长 |
| clip 总时长和歌对不上 | 上游 mv-video 按 beatgrid 调 clip 时长；compose 只校验告警 |
| 合成顺序跟分镜不一致 | 用 `mv-video/scripts/video_jobs.py --select` 更新 timeline；compose 优先读 `timeline_manifest.json` |
| 缺 timeline 时让 compose 猜顺序 | 默认会阻断；只有明确知道是临时救场才传 `--allow-fallback` |
| 拿 .ass 在无 libass 的 ffmpeg 上烧 | 自动降级本 skill `render_lyrics.py`（Pillow overlay） |
| 用配音 ducking 逻辑做 MV | MV 主音轴是整首歌，不 ducking |
| 所有接缝一律裸切 | 按 timeline/clip_plan 的 `transition` 接：有意硬切踩鼓点硬切、跳变接缝微溶解、缺空镜缓冲报警 |
| 后配歌曲 rough 蓝图没补最终歌就合成 | 先补 `歌/song.*`，跑 `mv-beat` 与正式 `mv-plan`，再合成 |
| 想复用 n2d-compose 的脚本 | 本系列完全独立，用自带 mv_compose.sh + render_lyrics.py |
