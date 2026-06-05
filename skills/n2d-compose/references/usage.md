# 调用规范
默认双语字幕 + 中文配音：
    bash <skill>/compose.sh <作品根> 第N集 bilingual
单语出海/国内：
    bash <skill>/compose.sh <作品根> 第N集 zh    # 国内：中字+中配
    bash <skill>/compose.sh <作品根> 第N集 en    # 出海：英字+英配
真实 BGM：
    BGMFILE=/path/to/music.mp3 bash <skill>/compose.sh <作品根> 第N集 zh
卡点（让 BGM drop 落在爽点那一帧，导演节奏.md §五）：
    BGMFILE=/path/to/music.mp3 BGM_OFFSET=12.5 bash <skill>/compose.sh <作品根> 第N集 zh
    # BGM_OFFSET=从 BGM 第几秒起播。算法：成片里爽点累计时间戳（故事板 💥爽点 @ 0:48）
    # 减去 BGM 文件里 drop 的时间戳 → 反推 offset，使 drop 与爽点画面对齐。
产物：<作品根>/出视频/第N集/成片_第N集_{mode}.mp4

## 可调参数（默认=原行为，全部可选）
质量/速度（粗剪 vs 定稿）：
    VIDEO_CRF=26 VIDEO_PRESET=ultrafast bash <skill>/compose.sh <作品根> 第N集   # 快速粗剪迭代
    VIDEO_CRF=18 VIDEO_PRESET=slow bash <skill>/compose.sh <作品根> 第N集        # 发布定稿（默认 18/medium）
BGM ducking（配音压 BGM 的力度）：
    DUCK_RATIO=12 bash ... # 快节奏动作：配音前置、BGM 压狠（默认 8）
    DUCK_RATIO=4  bash ... # 文艺/悬疑：BGM 重要、温和压低
    # 其余：DUCK_THRESHOLD(0.05) DUCK_ATTACK(20) DUCK_RELEASE(400)
clip 原生音频：
    # 默认转码时剥掉 AI clip 原生音轨，避免原生台词与 n2d-voice 配音双人声
    KEEP_CLIP_AUDIO=1 bash <skill>/compose.sh <作品根> 第N集 zh
    # 仅当确认 clip 里是可用环境音、无原生人声时才开；脚本会低音量混入环境底。

## 输入约定
- clips：<作品根>/出视频/第N集/视频/*.mp4（n2d-video 产物）
- 配音轨：<作品根>/出视频/第N集/配音/voice_{zh,en}.wav（n2d-voice 产物，可选）
- 字幕：<作品根>/脚本/第N集/字幕_{中文,英文}.srt

## BGM 来源（提示用户给丰富选项 + 鉴定可行）
ⓐ Suno 生成给文件 ⓑ 素材库 ⓒ 本地文件(BGMFILE) ⓓ 占位。用户自由描述需求 → 鉴定(存在/格式/时长够循环/版权)→ 可行照办，不可行说明并给替代。

## 转场音效（可选）
用户给 2~5 个 SFX 文件 → 在 clip 边界铺；不给跳过。

## 行业参考（决定音频时展示）
90 秒一集漫剧工作室标配：1 条循环 BGM + 2~5 个转场音效 + AI 角色配音。

## 进度回写
完成后回写「成片」列：`python3 <novel2drama skill>/progress.py set <作品根> 第N集 成片 ✅`。

## 字幕字号微调 + 样式分级
- 基础字号：`ZH_SIZE`(默认50) / `EN_SIZE`(默认34)。
- **样式分级**（自动）：compose 把 `配音/时长清单.json` 复制为 `_work/manifest.json`，render_subs 据 `角色`/`钩子` 字段分级——旁白/系统句→灰色小一号、爽点(钩子=climax)句→暖金大一号、其余 normal。增量可调：`NARR_DZH`(-8)`NARR_DEN`(-4) / `EMPH_DZH`(+6)`EMPH_DEN`(+2)。无 manifest 时全部 normal（=原行为）。

## 定稿前自检（建议）
合成前跑一遍时长一致性守门：
    python3 <n2d-script skill>/validate_timings.py <作品根> 第N集
核对 配音轨≈字幕末行≈镜头时长累计 + 中英字幕句数一致 + line_*.wav 齐；有硬不一致退出码 1 并提示重跑哪步。
