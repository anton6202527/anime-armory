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
声音连续 / J-cut（默认开启 0.25s）：
    bash <skill>/compose.sh <作品根> 第N集 zh
    J_CUT_SEC=0 bash <skill>/compose.sh <作品根> 第N集 zh       # 关闭 J-cut
    J_CUT_SEC=0.35 bash <skill>/compose.sh <作品根> 第N集 zh    # 更强的声音先行
    # 基于 配音/时长清单.json + line_*.wav 重建轻量提前入声的 voice_jcut.wav。
    # 只适合旁白、系统音、背身/侧脸说话、转场声；正面口型特写保持 J_CUT_SEC=0。
    # 建议范围 0.15-0.35，脚本上限 0.4，避免破坏音画同步。
clip 原生音频：
    # 默认转码时剥掉 AI clip 原生音轨，避免原生台词与 n2d-voice 配音双人声
    KEEP_CLIP_AUDIO=1 bash <skill>/compose.sh <作品根> 第N集 zh
    # 仅当确认 clip 里是可用环境音、无原生人声时才开；脚本会低音量混入环境底。

## 输入约定
- clips：<作品根>/出视频/第N集/视频/*.mp4（n2d-video 产物）
- 配音轨：<作品根>/出视频/第N集/配音/voice_{zh,en}.wav（n2d-voice 产物，可选）
- 字幕：<作品根>/脚本/第N集/字幕_{中文,英文}.srt

## 配音轨来源 / 占位守门 / 先出视频后配音拟合
- **VOICEFILE 覆盖**：默认用 `配音/voice_{zh,en}.wav`；设 `VOICEFILE=/path/x.wav` 可指定别的轨（如拟合轨）。
- **占位守门**：`时长清单.json` 含占位句且未设 VOICEFILE 时，compose 拒绝合成（占位≠真实时长）。rough preview 用 `ALLOW_PLACEHOLDER_COMPOSE=1` 放行。
- **`制作模式=先出视频后配音`（快速 demo·不推荐）**：合成前必须拟合后期补录的真音到已成片镜头长：
  ```
  python3 <skill>/fit_voice_to_clips.py <作品根> 第N集 zh            # dry-run 对账
  python3 <skill>/fit_voice_to_clips.py <作品根> 第N集 zh --apply    # 出 voice_zh_fitted.wav
  VOICEFILE=<作品根>/出视频/第N集/配音/voice_zh_fitted.wav bash <skill>/compose.sh <作品根> 第N集 zh
  ```
  有 overflow（真音远超槽位）时脚本退出码 2、不产轨 → 回 /n2d-video 重出该镜头加长，或调 `FIT_MAX_STRETCH`。详见 SKILL「先出视频后配音」节。

## BGM 来源（提示用户给丰富选项 + 鉴定可行）
ⓐ Suno 生成给文件 ⓑ 素材库 ⓒ 本地文件(BGMFILE) ⓓ 占位。用户自由描述需求 → 鉴定(存在/格式/时长够循环/版权)→ 可行照办，不可行说明并给替代。

## 转场音效（可选）
用户给 2~5 个 SFX 文件 → 在 clip 边界铺；不给跳过。

## 衔接策略
- `故事板.md` 每个 Clip 的「衔接设计」决定后期策略：match cut / eyeline / 动作切主要靠上游首尾帧；空镜缓冲作为独立 clip 保留；声音先行用 `J_CUT_SEC` 显式开启。
- BGM 默认全程连续，不随 clip 边界断开；`BGM_OFFSET` 用来把 drop 对齐爽点。
- 不在 compose 阶段临时硬塞未知空镜。需要空镜缓冲时，在 n2d-script 阶段写成正式 Clip，n2d-image/n2d-video 出图出视频后再合成。

## 行业参考（决定音频时展示）
90 秒一集漫剧工作室标配：1 条循环 BGM + 2~5 个转场音效 + AI 角色配音。

## 进度回写
完成后回写「成片」列：`python3 <novel2drama skill>/progress.py set <作品根> 第N集 成片 ✅`。

## 字幕字号微调 + 样式分级
- 基础字号：`ZH_SIZE`(默认50) / `EN_SIZE`(默认34)。
- **样式分级**（自动）：compose 把 `配音/时长清单.json` 复制为 `_work/manifest.json`，render_subs 据 `角色`/`钩子` 字段分级——旁白/系统句→灰色小一号、爽点(钩子=climax)句→暖金大一号、其余 normal。增量可调：`NARR_DZH`(-8)`NARR_DEN`(-4) / `EMPH_DZH`(+6)`EMPH_DEN`(+2)。无 manifest 时全部 normal（=原行为）。

## 打斗后期（补打击感）
- **命中顿帧 hit-stop**：命中那帧定格 2-4 帧。
- **变速**：蓄力略慢(0.9x)→出招快(1.1x)→命中瞬间慢镜(0.5x)。
- **打击音效**：出招 `whoosh` + 命中帧 `impact 重低音`，卡在命中帧那一帧。
- **重击/法术爆发**：叠 1 帧轻闪白 + 2 帧微震屏（幅度小，别晃晕）。
- **BGM 鼓点对齐命中帧**（用 BGM_OFFSET 平移 drop 到命中时间戳）。
- 详见 `n2d-script/references/打斗分镜.md §九 9.4`。

## 仙侠场面后期（飞行/追逐/渡劫/炼丹/法阵/大场面/斗法对轰/神魂）
> 含这些奇观的集按 `n2d-script/references/仙侠场面分镜.md` 各节"后期要点"。
- **御剑飞行**：叠风声/破空底噪 + 速度线节奏；机动/俯冲处镜头加速感配音效，抵达留白缓收。
- **追逐**：快节奏脚步/破风 + 心跳低频；险情瞬间 BGM 抽一下放大危机，甩开=喘息留白。
- **渡劫雷击**：同打斗命中四件套但更猛——**顿帧 + 炸雷重低音 + 强闪白（可满帧白1帧）+ 震屏**；每道雷音量/闪白逐道加大，末劫顶；突破=光柱起 + **BGM 推到全曲最高潮** + 过曝0.3s + 长留白。
- **炼丹炼器**：过程低回专注 → 开炉前一滞 → 开炉清越一响 + 短光爆（失败=炸炉：闪白+震屏+轰响）。
- **大阵法阵**：起阵低频嗡鸣渐强 → 激活一记轰然光爆 + BGM 推顶 → 阵纹流转持续音。
- **大场面 establish**：空灵 BGM + 环境音（风/钟/鹤唳/诵经底噪），慢、给足时长（2-4s），是"喘息+沉浸"位，别抢戏。
- **斗法对轰**：撞点持续轰鸣 + 光团明灭；压制时音量推高；破防=炸雷级 impact+闪白+震屏 + BGM 抽真空再起。
- **神魂**：元神出窍/神识=缥缈 BGM+空灵嗡鸣+波纹音；夺舍相争=低频压迫+两音色拉锯，夺舍成=一记定音+瞳色变特写；神魂攻击命中=闷响+魂体闪。

## 定稿前自检（建议）
合成前跑一遍时长一致性守门：
    python3 <n2d-script skill>/validate_timings.py <作品根> 第N集
核对 配音轨≈字幕末行≈镜头时长累计 + 中英字幕句数一致 + line_*.wav 齐；有硬不一致退出码 1 并提示重跑哪步。
