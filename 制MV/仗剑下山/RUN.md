# 《仗剑下山》MV 执行手册（需你的工具/账号的步骤）

本机已就绪：✅ ffmpeg ✅ dreamina(即梦) ✅ gemini。缺：Suno、librosa、whisperx、Pillow（按需 pip 装）。
**已由 Claude 完成（创作+规划）**：歌词、创作蓝图、视觉蓝图、角色卡(锚点句)、场景卡、20 张出图 prompt、20 个 clip 计划。
**下面是需要你跑的生成步骤**（多数因要账号/交互登录/未装库，Claude 在非交互 shell 里跑不了）。

## 1) 出歌（song-compose）—— Suno 或 ACE-Step
- Suno：suno.com Custom 模式，把 `写歌/仗剑下山/歌/_suno_prompt.txt` 的 STYLE 贴 style 框、`词/lyrics.md` 歌词贴 lyrics 框 → 多生几版挑最佳 → 下载 mp3。
- 归一：`python3 skills/song-compose/scripts/place_song.py 写歌/仗剑下山 <下载的.mp3> --split`
- 拷进制MV：`cp 写歌/仗剑下山/歌/song.wav 制MV/仗剑下山/歌/song.wav`
- （把好歌发我，我接着帮你跑下面的卡点/对齐/合成。）

## 2) 卡点（mv-beat）
- `pip install librosa soundfile` 后：`python3 skills/mv-beat/scripts/beat_detect.py 制MV/仗剑下山`
- 产 `节拍/beatgrid.json`；据 downbeats 回填 `出视频/视频/01_clips.md` 各 clip 时长。

## 3) 出图（mv-image）—— dreamina 需在你的【交互式终端】登录
- `dreamina relogin`（扫码）后，按 `出图/common/00_出图.md` + `出图/段落/01_分镜出图.md` 逐张：
  `dreamina text2image --prompt "<prompt>" --ratio 9:16 --resolution_type 2k --model_version 3.0`（异步, query_result 下载）
- 先出定妆锁脸 → 设为参考图 → 出 20 张分镜（每张已含锚点句）。落 `出图/`。

## 4) 出视频（mv-video）—— dreamina image2video（交互式）
- 按 `出视频/视频/01_clips.md`，clip 时长用 beatgrid，逐 clip：
  `dreamina image2video --image <出图PNG> --prompt "<人物运动+镜头运动+动态细节>" --duration <卡点时长> --aspect 9:16`
- 落 `出视频/视频/Clip<NN>_*.mp4`。

## 5) 卡拉OK字幕（mv-lyric-sync）
- `pip install whisperx` 后：`python3 skills/mv-lyric-sync/scripts/align.py 制MV/仗剑下山 --lang zh`
- 产 `字幕/karaoke.ass` + `lyrics.lrc`。

## 6) 合成成片（mv-compose）—— 本机 ffmpeg 可跑！
- 有了 歌 + 视频clips(+字幕)：`bash skills/mv-compose/mv_compose.sh 制MV/仗剑下山 9:16`
- 无 libass 烧 .ass 时会自动用 `render_lyrics.py`（需 `pip install Pillow`）。
- 出 `成片_MV.mp4`。
