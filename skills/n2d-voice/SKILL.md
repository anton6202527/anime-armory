---
name: n2d-voice
description: Stage 2 of n2d (前移到出图之前) — turn a 作品 episode's voiceover.txt into AI 角色配音：per-line audio + stitched voice track + 时长清单.json (每句实测时长，驱动下游镜头时长；逐句记 voice_key 实际应用音色键，一角一色跨集对账数据源，n2d-identity 消费). Multi-backend pluggable (CosyVoice / GPT-SoVITS 本地克隆 / MiniMax / 火山 / macOS say 占位), with voice-cloning + demucs 人声分离. Writes _进度.md 配音 column. Use when asked to 配音, 生成配音, 角色配音, 声音克隆, CosyVoice, GPT-SoVITS, 时长清单. Triggers 配音, 角色配音, 声音克隆, 克隆音色, CosyVoice, GPT-SoVITS, MiniMax配音, 时长清单, voice_key, voiceover.
---

# n2d-voice — 配音（前移到出图前）

你是 **AI 漫剧角色配音**。把一集的 `脚本/第N集/voiceover.txt` 变成：① 逐句音频 `配音/line_NN.wav` ② 整轨 `配音/voice_{zh,en}.wav` ③ **`配音/时长清单.json`**（每句实测时长 → 下游 n2d-script 阶段2 用它定稿镜头时长）。

> **落档位置（2026 调整）**：配音产物落 **`合成/第N集/配音/`**（不在 `出视频/`）——`出视频/` 只放各镜头 clips，配音/成片/水印都归「合成」层，与 n2d-compose 同住。`render_voice.py` 已按此写盘。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`配音后端`、`制作模式`（决定本步在出视频之前还是之后跑真实配音·见下）、`合规用途`。声音克隆/参考音授权不是普通偏好，必须同时写入 `合规/compliance_manifest.json`。

## 核心原则
- **⛔ 声音克隆合规闸门（non-negotiable·每次确认 + 合规包留痕）**：克隆/复刻/零样本参考音只能是 ①本人嗓 / ②已授权他人嗓 / ③纯合成音色；复刻真人歌手/演员/公众人物需本人授权（2026 opt-in）。这是项目约定里的"合规/不可逆"点，**即使 `_设置.md` 记过也每次重确认**。脚本侧：`voice_clone.py` 需显式 `VOICE_CLONE_AUTHORIZED=1`；**零样本后端（CosyVoice/Fish/GSV/IndexTTS/Vox）也同级硬闸门**——`render_voice.py` 一旦检测到任一 `<后端>_REF_*` 参考音（即要用参考音克隆嗓音）就要求 `VOICE_CLONE_AUTHORIZED=1`，否则停止；用默认嗓（不喂参考音）才无需授权。长期审计侧：必须把 `voice.uses_voice_clone=true`、`voice.status=licensed|self_owned|synthetic`、授权证据和适用角色写入 `合规/compliance_manifest.json`；`gate.py --stage video|compose|review` 会阻断未授权或无证据的克隆音。**两道闸门缺一不可**：运行时 `VOICE_CLONE_AUTHORIZED=1`（拦生成）与合规包 `voice` 授权段（拦付费 video/compose/review gate）是两层，满足其一仍会被另一层拦。**`distribution_intent=internal_only` 不豁免声音克隆授权与 AI 标识**——它只免平台审核/出海本地化。详见 references/cloning.md 与 `n2d-compliance`。
- **配音先行**：本阶段在出图/出视频**之前**跑。配音时长决定镜头时长（节奏可控、后期省成本），**不**在这里按窗口压速。
- **醒目提示：macOS `say` 中文可能输出空音频**：若 `say` 生成的中文音频无有效 duration，`render_voice.py` 会**自动降级为静音占位时长轨**（按文本长度/语速/钩子估算每句时长，写 `line_NN.wav` / `voice_zh.wav` / `时长清单.json`，并在 manifest 标 `占位:true`、写 `_占位说明.md`）。这不是有声朗读，只能用于 rough timing。
- **占位分阶段 = 两遍制 rough→refine（关键）**：占位/估算时长是**第一遍 rough timeline**（只为跑通骨架 / 字幕初定时 / 节奏预览），真实配音是**第二遍 refine**（重定时 + 增量重出受影响镜头）。`render_voice.py` 只要发现任一句占位，就回写 `_进度.md` `配音=⏳rough`；只有全句真实音频才回写 `配音=✅`。`配音先行` 模式下 `⏳rough` 不能越过 image/video 付费闸门；`先出视频后配音` 模式下它只是用户主动选择的时间脚手架，可推进到出视频，但合成前必须补真音并拟合。macOS `say` 占位**只服务出图/出视频前的 rough timing**，不要把它当成可投放配音。
- **真音替换后的回流（zh 改了，en/BGM 也要跟）**：占位/旧 zh 换真实配音重跑后，时间轴变了——**已生成的 `voice_en.wav` 与 BGM 总时长不会自动失效**。回流必须：① 回跑 `n2d-script` 阶段2(finalize) 重定时；② 若已出英文配音，**重跑 `n2d-voice … en`**（en 句长/时间轴随 zh 变）；③ BGM 按新总时长在 compose 重铺。漏跑 en 会导致中英轨错位。
- **单句合成失败不毁整集**：API/本地后端逐句生成时，单句失败（限流/超时/服务挂）**只把该句降级为静音占位并标 `占位:true`**，其余句正常产出、整集不中断；出图前按占位提示补那几句即可。
- **`制作模式`=`先出视频后配音`（快速 demo·不推荐）时本步跑两次**（见 n2d SKILL「制作模式」节，必向用户复述不推荐理由）：第一次（出图前）只出**占位/估算 `时长清单.json`** 当时间脚手架，**不追求音质**；真实配音第二次跑（**出视频之后、合成之前**）。这条路把"占位时长驱动出图/出视频"的返工风险显式留给了用户——能跑通但音画大概率对不准。`配音先行`（默认）永远在出图前就出真实配音，本步只跑一次。
- **`制作模式`=`原生音画`（native AV）时，说话镜不在本步配音**：`制作模式=原生音画` 时，对话/说话镜由视频后端一次原生生成台词+口型+环境声（见 `n2d-model-router` `native_speech` 路由），**这些镜头不出逐句 `时长清单`、不在本步跑配音**。本步只处理仍需配音先行的部分（如旁白/纯画外音镜头、或用户对个别镜头要求精细念白时的回退配音）；整剧若全程原生音画，本步可整体跳过。注意：原生人声仍受声音克隆合规闸门约束（仿真人音色需授权 + AI 标识）。
- **念白是表演，不是平读**：voiceover.txt 每句的 `情绪/语速/停顿/钩子` 标注**会驱动 TTS**（不是注释）——这是留存的一部分，见 `n2d/references/导演节奏.md §六`。
- **后端可插拔**：检测 env 决定后端，优先级 CosyVoice/GPT-SoVITS(本地克隆·质量优先) > MiniMax/火山(云·省事) > macOS say(占位)。缺凭证回退 say 并告警。
- **一角一色（跨集持久绑定）**：角色→音色映射优先读 `<作品根>/设定库/voicemap.json`（`{"角色子串":{"key","mm","volc","speed","pitch","emo"}}`），缺文件才回退内置(demo)映射，env 仍可覆盖。**新剧务必建 voicemap.json 把每个角色绑定音色**——否则新角色全部掉进默认嗓互相撞，且跨集靠每次手动 export env 极易漂。manifest 每句记 **`voice_key`**（契约标准字段 `n2d_contract.VOICE_KEY_FIELD`，=该句实际应用的 voicemap 音色键；macOS say 占位后端没有走 voicemap 选音，记 `say:<声音名>#placeholder` 留痕并显式声明非注册音色）+ `音色键`(legacy 中文字段，保留兼容)/`voice_id`/`情绪_已应用`。**`voice_key` 是一角一色跨集对账的数据源**：`n2d-identity` 的 `voice_consistency.py` 逐集读它对账 voicemap、产出音色跨集漂移报表（老清单缺该字段按 `insufficient_data` 跳过，不报假漂移）；`n2d-review` 机检同源。条目构造在 `voice_manifest.py`（独立模块·带单测）。
- **生产数据记账铁律（P0）**：每次配音生成后必须调用 `n2d-dashboard` 记录 `stage=voice` 事件：后端、耗时、成本、输出音轨、句数、失败/占位句数。若某句降级占位或重跑，必须在 `meta` 或 `redraw_reason` 里写明，方便后续统计“配音导致的重定时/返工”。
- **统一电平**：每句 loudnorm -16 LUFS。
- **时长清单是产线桥梁**：每句 ffprobe 量时长写入 `时长清单.json`，这是配音驱动镜头的关键产物。同时写 `时长清单.meta.json`（记录配音那一刻 `voiceover.txt` 的台词指纹 + 后端 + 时间）——`validate_timings.py` 用它抓"配音之后又改了 `voiceover.txt`（改词/插句/删句）导致时长清单/字幕/镜头时长全部过期"这条失配链（`delete_shot` 的强制对账只覆盖删镜）。改台词后必须重跑 `n2d-voice` 刷新指纹与时长，再回跑 n2d-script 阶段2。

## 表演指导（情绪/语速/停顿/钩子 → 念白）
`render_voice.py` 解析 voiceover.txt 的 `[镜头N·角色·情绪·(语速)] 台词 (钩子)`，落实到念白：

| 标注 | 解析 | 落到 TTS |
|---|---|---|
| **情绪** | 归类成 angry/fearful/sad/happy/serious/neutral（关键词匹配，兼容旧自由词） | **MiniMax 逐句覆盖角色默认 emotion**（走情绪集，`serious→neutral`）；**火山后端不逐句驱动情绪**（只用角色固定情绪），情绪吃重的集选 MiniMax/IndexTTS-2。每句实际下发的情绪记进 manifest `情绪_已应用` 字段（可见火山的"角色固定"与 MiniMax 的 serious 降级），不再静默 |
| **语速 快/慢** | ×1.10 / ×0.90 | 叠到角色基速（clamp 0.7~1.5）；say 后端体现在 rate |
| **停顿 `||`** | 替换成逗号 | TTS 自然气口（反转词前留一拍） |
| **钩子 ⚡/💥/🪝**（或行尾裸词 钩子/爽点/集尾） | 从念白文本剥掉（不念出来），记进 `时长清单.json` 的 `钩子` 字段 | 句后留"悬念呼吸"拍：hook 0.6s / 爽点 0.7s / 集尾 1.0s（env `GAP_HOOK/GAP_CLIMAX/GAP_END` 可调，常规句 `LINE_GAP` 0.4s） |

> 情绪只标自由词（旧格式）也能跑——按关键词归类，归不到就 neutral。要"导演级念白"，按 formats §6 标全情绪+语速+停顿+钩子。`时长清单.json` 逐句含 `情绪`/`钩子`（供下游分镜/卡点参考）和 `voice_key`（实际应用音色键·跨集音色对账数据源，见上「一角一色」）。

## 输入前置
- `脚本/第N集/voiceover.txt` 存在（n2d-script 阶段1 产物）。否则报错建议先 n2d-script。
- 若使用参考音/克隆音色，先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init`，在 `voice` 段填 `uses_voice_clone=true`、授权状态、授权证据和适用角色；再跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第N集 --check`。只设 `VOICE_CLONE_AUTHORIZED=1` 不足以进入后续视频/合成 gate。

## 工作流
1. 解析 voiceover.txt → 逐句(镜头·角色·情绪·文本)。
2. 选后端（见 references/backends.md）；按角色映射音色。
3. 若本次要用参考音，确认 `VOICE_CLONE_AUTHORIZED=1` 且 `合规/compliance_manifest.json` 的 `voice` 授权段已填；未满足时停止，不生成。
4. 逐句生成 → loudnorm -16 → 量时长。若 macOS `say` 中文为空音频,自动生成静音占位轨并告警。
5. 写 `配音/line_NN.wav` + 拼 `voice_{zh,en}.wav` + 写 `时长清单.json`。
6. 回写 `_进度.md` 该集「配音」列：全句真实配音写 `✅`；任一句占位/估算写 `⏳rough`（旧项目曾写成 `✅` 的，用 `python3 skills/n2d/progress.py audit-placeholders <作品根> --fix` 降级）。
7. 记录生产数据：
   ```bash
   python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
     --episode 第N集 --stage voice --event generation \
     --asset <voice_zh.wav路径> --status pass \
     --duration-sec <配音耗时秒> --provider <CosyVoice|MiniMax|say|...> \
     --cost <成本数值> --unit <USD|CNY|credits> \
     --meta lines=<句数> --meta placeholder_lines=<占位句数>
   ```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 跳过合规检查，直接克隆音色 | 声音克隆合规是硬闸门，必须先在 `合规/compliance_manifest.json` 登记授权状态与证据 |
| 出图前仍使用 macOS `say` 占位且不告警 | 占位时长不准，出图前必须换真实配音重定时，否则视频返工成本极高 |
| 改了 `voiceover.txt` 却没重跑配音 | 时长清单/字幕/镜头时长已过期，必须重跑 `n2d-voice` 刷新指纹，再回跑 `n2d-script` 阶段2 |
| 未建立 `voicemap.json`，导致音色随机或漂移 | 跨集一致性依赖 `voicemap.json` 角色-音色绑定，新剧务必先建表 |
| 忽略 `render_voice.py` 的情绪/语速标注 | 念白是表演，必须按标注驱动 TTS 情绪和节奏 |
| 忽略单句合成失败，导致整集中断 | 单句失败应降级为占位，保证整集产出，事后补全 |
| 混合使用 `配音先行` 和 `先出视频后配音` 模式 | 严禁混用。模式在 `_设置.md` 定死，逻辑按模式分支，不可凭空跳跃 |
| `原生音画` 模式下仍给所有镜头配音 | 浪费额度。说话镜由视频后端出声，配音阶段只需处理旁白或非说话镜 |
| 漏记 `voice_key` 实际应用音色键 | 导致 `n2d-identity` 无法进行跨集音色一致性对账 |

## 声音克隆
见 references/cloning.md（MiniMax 复刻 / GPT-SoVITS / CosyVoice 本地克隆 + demucs 人声分离清洗）。

## 详细参考
- 后端接入与凭证：references/backends.md
- 声音克隆 + 人声分离：references/cloning.md
- 调用规范：references/usage.md
