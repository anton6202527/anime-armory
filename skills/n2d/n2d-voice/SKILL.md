---
name: n2d-voice
description: Voice casting, timing and rendering stage of n2d — 默认先做项目级声音选角与无 WAV 文本时长基准，音色定妆通过后才生成最终逐句配音；可为口型可见镜头显式生成可信表演/导引音轨。最终音轨写 line_NN.wav、voice_{zh,en}.wav、时长清单.json 与 voice_key 跨集一致性证据。支持 CosyVoice / GPT-SoVITS / MiniMax / 火山等后端与声音克隆合规闸门。Use when asked to 配音、声音选角、音色定妆、导引音轨、最终配音、声音克隆、时长清单。
---

# n2d-voice — 声音选角、时间基准与最终配音

你是 **AI 漫剧声音导演与配音执行**。默认先把 `voiceover.txt` 变成两份不含音频的前期合同：① 项目级 `设定库/voice_casting.json`（声音选角/音色定妆）② 本集 `合成/第N集/配音/timing_estimate.json`（文本估算的时间基准）。音色获批后，才把需要的台词渲染为 `line_NN.wav`、`voice_{zh,en}.wav` 与实测 `时长清单.json`。

> **落档位置（2026 调整）**：配音产物落 **`合成/第N集/配音/`**（不在 `出视频/`）——`出视频/` 只放各镜头 clips，配音/成片都归「合成」层，与 n2d-compose 同住。`render_voice.py` 已按此写盘。

> **零字节产物铁律**：`ClipNN_voice.wav/json` 的 0-byte 文件不是占位证据，而是无效产物；preflight `check` 必须阻断。先运行 `python3 skills/n2d/n2d-voice/voice_preflight.py doctor <作品根> [第N集]` 只读审计，确认后加 `--apply` 只删除这些旧式零字节文件。新流程用 `timing_estimate.json` 表示未渲染时间基准，不再创建空 WAV/JSON。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在执行脚本里**。按 `../skills/n2d/references/选择点与偏好.md` 读 `<作品根>/_设置.md`；缺失的普通可逆项由 producer-owned 推荐器采用安全默认并继续，用户已有值永不覆盖。仅 `普通选择策略=逐项询问` 时才展示菜单；声音克隆/参考音授权、付费、合规与最终验收仍每次确认。

本 skill 涉及的选择点：`配音后端`、`制作模式`、`合规用途`。默认 `制作模式=混合自动路由`：制作先后顺序由每个镜头的声音策略决定，不再给整个项目强制套同一种顺序。声音克隆/参考音授权不是普通偏好，必须同时写入 `合规/compliance_manifest.json`。

## 核心原则
- **⛔ 声音克隆合规闸门（non-negotiable·每次确认 + 合规包留痕）**：克隆/复刻/零样本参考音只能是 ①本人嗓 / ②已授权他人嗓 / ③纯合成音色；复刻真人歌手/演员/公众人物需本人授权（2026 opt-in）。这是项目约定里的"合规/不可逆"点，**即使 `_设置.md` 记过也每次重确认**。脚本侧：`voice_clone.py` 需显式 `VOICE_CLONE_AUTHORIZED=1`；**零样本后端（CosyVoice/Fish/GSV/IndexTTS/Vox）也同级硬闸门**——`render_voice.py` 一旦检测到任一 `<后端>_REF_*` 参考音（即要用参考音克隆嗓音）就要求 `VOICE_CLONE_AUTHORIZED=1`，否则停止；用默认嗓（不喂参考音）才无需授权。长期审计侧：必须把 `voice.uses_voice_clone=true`、`voice.status=licensed|self_owned|synthetic`、授权证据和适用角色写入 `合规/compliance_manifest.json`；`gate.py --stage video|compose|review` 会阻断未授权或无证据的克隆音。**两道闸门缺一不可**：运行时 `VOICE_CLONE_AUTHORIZED=1`（拦生成）与合规包 `voice` 授权段（拦付费 video/compose/review gate）是两层，满足其一仍会被另一层拦。**`distribution_intent=internal_only` 不豁免声音克隆授权**——它只免平台审核/出海本地化。详见 references/cloning.md 与 `n2d-compliance`。（AI 标识/AI 披露/水印只做非阻断发布待办。）
- **默认不是最终配音先行，而是时间基准先行**：先运行 `voice_preflight.py prepare`。它只解析文本、估时并建立选角表，**不会生成任何 WAV**；`timing_estimate.json` 可用于 animatic、字幕初定时、旁白/口外音节奏和画面先行镜头，但不能冒充最终声音或可见口型表演证据。
- **声音选角先行，最终配音后置**：先用少量、有代表性的 audition 台词锁角色声音；所有必需角色通过定妆后，才允许 `render_voice.py` 批量生成 `purpose=final` 音轨。不要为了推进状态机合成一整集注定删除的次品配音。
- **口型可见镜头例外看“表演音轨”，不看“最终成片音轨”**：对白近景、正反打、嘴部可见镜头必须先有已批准表演音轨或可信导引音轨，才能直接驱动表演；没有时先生成中性闭口/静止口型的基础视频，再走独立后期口型 pass。最终高质量声音仍可替换，但替换后必须重做口型/时间对账。
- **旁白、内心戏、口外音只需粗时间基准**：默认用无 WAV 文本估时推进；需要听节奏时才显式生成少量 `purpose=guide` 导引轨。动作、空镜、蒙太奇直接画面先行。
- **旧占位轨只做兼容，不再是默认前期产物**：旧项目已有 `占位:true` 时仍按 `⏳rough` 识别，但新混合流程用 `timing_estimate.json`，不调用 macOS `say`、不落静音 line WAV。混合模式下后端失败或空音频直接失败，不再用静音 WAV 冒充成功。
- **真音替换后的回流（zh 改了，en/BGM 也要跟）**：占位/旧 zh 换真实配音重跑后，时间轴变了——**已生成的 `voice_en.wav` 与 BGM 总时长不会自动失效**。回流必须：① 回跑 `n2d-script` 阶段2(finalize) 重定时；② 若已出英文配音，**重跑 `n2d-voice … en`**（en 句长/时间轴随 zh 变）；③ BGM 按新总时长在 compose 重铺。漏跑 en 会导致中英轨错位。
- **单句合成失败不伪造成功**：混合模式的 final/guide 生成遇到限流、超时、空音频时必须失败并保留可重试信息；已经成功的句子可复用，但失败句不能降级成静音占位后继续签收。
- **用户显式选择项目级旧模式时保持兼容**：`配音先行` 仍可要求全片真音先出；`先出视频后配音` 仍可整集画面先行；二者都不是新项目默认。新默认 `混合自动路由` 把它们拆成逐镜头策略。
- **`制作模式`=`原生音画`（native AV）时，说话镜不在本步配音**：`制作模式=原生音画` 时，对话/说话镜由视频后端一次原生生成台词+口型+环境声（见 `n2d-model-router` `native_speech` 路由），**这些镜头不出逐句 `时长清单`、不在本步跑配音**。本步只处理仍需配音先行的部分（如旁白/纯画外音镜头、或用户对个别镜头要求精细念白时的回退配音）；整剧若全程原生音画，本步可整体跳过。注意：原生人声仍受声音克隆合规闸门约束（仿真人音色需授权）。
- **念白是表演，不是平读**：voiceover.txt 每句的 `情绪/语速/停顿/钩子` 标注**会驱动 TTS**（不是注释）——这是留存的一部分，见 `n2d/references/导演节奏.md §六`。
- **后端可插拔但不静默换路**：按声音定妆表锁定的 backend/model/voice_id 调用 CosyVoice、GPT-SoVITS、MiniMax、火山等；混合模式缺凭证、后端不匹配或音色未锁时直接阻断，不自动回退 macOS `say`。
- **🔒 音色定妆照（canonical 参考音冻结·防漂先行，非事后报漂）**：克隆/零样本后端的**参考音应钉死成每角色一条 canonical wav 全篇·跨集复用**——等价图像层「共享定妆库先行」。源头若每集临时喂不同样本（或不喂、靠后端零样本每次重克隆），音色会逐集漂，而声纹机检（`n2d-identity` `voice_print_consistency.py`）只能**事后 WARN**、不能预防。做法：在 `设定库/voiceprints/<角色>.wav` 冻结一条满意参考音（可由一次定妆配音挑定后冻结），voicemap 该角色条目加 `"ref":"设定库/voiceprints/<角色>.wav"`（可选 `"ref_text"` 逐字文本）。`render_voice.role_ref` 在 env 未显式指定参考音时**自动回退该 voicemap `ref`**（项目内相对路径，env 仍可临时覆盖）。**合规同级**：voicemap 钉死的 `ref` 与 env `<后端>_REF_*` 一样触发声音克隆授权闸门（须 `VOICE_CLONE_AUTHORIZED=1` + 合规包 `voice` 授权段），绝不因换成项目内文件就绕过。
- **一角一色（跨集持久绑定）**：角色→音色映射优先读 `<作品根>/设定库/voicemap.json`（`{"角色子串":{"key","mm","volc","speed","pitch","emo","ref","ref_text","accent"}}`；`ref`/`ref_text` 见上「音色定妆照」；可选 `accent`/`口音`/`方言` 锁该角色口音方言，由 `n2d-review` 的 `audio_continuity.py` 口音方言(ACC)检消费——同一 `key` 被多角色用却口音冲突=WARN，已锁口音的角色出验收听辨提醒），缺文件才回退内置(demo)映射，env 仍可覆盖。**新剧务必建 voicemap.json 把每个角色绑定音色**——否则新角色全部掉进默认嗓互相撞，且跨集靠每次手动 export env 极易漂。manifest 每句记 **`voice_key`**（契约标准字段 `n2d_contract.VOICE_KEY_FIELD`，=该句实际应用的 voicemap 音色键；macOS say 占位后端没有走 voicemap 选音，记 `say:<声音名>#placeholder` 留痕并显式声明非注册音色）+ `音色键`(legacy 中文字段，保留兼容)/`voice_id`/`情绪_已应用`。**`voice_key` 是一角一色跨集对账的数据源**：`n2d-identity` 的 `voice_consistency.py` 逐集读它对账 voicemap、产出音色跨集漂移报表（老清单缺该字段按 `insufficient_data` 跳过，不报假漂移）；`n2d-review` 机检同源。**这条对账已硬接进 image gate 渲染前自动落地**（`gate.py check_voice_cross_episode`，`--stage image`）：实际用键 ≠ voicemap 注册键 = **BLOCK**（确定性失配，出图前必须修，否则跨集换脸又换声）；同角色跨集换键 = WARN（可能附身/苍老/闪回有意换嗓，交人确认）；声纹 embedding 漂移（resemblyzer/speechbrain 后端可缺则静默跳过）= WARN。不再只靠人手动跑 `identity.py --write` 当副作用打印；占位/应急轨与未登记角色已排除，不会误 BLOCK。条目构造在 `voice_manifest.py`（独立模块·带单测）。
- **生产数据记账铁律（P0）**：每次配音生成后必须调用 `n2d-dashboard` 记录 `stage=voice` 事件：后端、耗时、成本、输出音轨、句数、失败/占位句数。若某句降级占位或重跑，必须在 `meta` 或 `redraw_reason` 里写明，方便后续统计“配音导致的重定时/返工”。
- **voice 不是付费闸门例外**：无 WAV 的 `voice_preflight.py prepare` 可自动执行；一旦进入云 TTS、克隆或其它实际 final/guide 渲染，`run.py` 会在 voice 工位先做付费确认与合规检查，不能等 video/compose 才拦住已经发生的声音费用。
- **统一电平**：每句 `loudnorm I=-16 LUFS / TP=-1.5 dBTP / LRA=11`（与 `render_voice.py` 实作一致；交付复核按这三项查，只查 -16 会漏掉真峰与动态范围）。成片母版的平台响度另由 `n2d-compose` 的 `loudness_conform.py` 按 `目标平台` 归一，与本句级电平是两层。
- **🔡 专名/多音字读音词典（念白文本与显示文本分离）**：配音先行管线最易翻车的是人名/境界/招式被 TTS 读错且跨集读音漂（重华/燕/朝/和… 多音字、生僻字、自造术语）。可选 `<作品根>/设定库/读音词典.json`（`{"重华":{"pinyin":"chóng huá","spoken":"虫华"}}`，值可裸字符串=spoken）。`render_voice` 解包台词后只对**喂 TTS 的念白文本**做谐音替换（`voice_lexicon.to_spoken`），**字幕/时长清单永远保留正名**——谐音只下到声学层。这是唯一跨后端通用的纠音手段（MiniMax/火山 不收音素；音素级后端另存 pinyin）。缺词典=原样念，零副作用。巡检：`python3 voice_lexicon.py <作品根> 第N集`（报将纠音词 + 术语表出现却没收的专名）。建议据 `global_style.md` 关键术语表起一份。
- **🏛 场景空间声学/混响（对白轨·可选）**：voice-first 对白此前全程 dry——山洞/大殿/旷野同一人声场无差别。可选 `<作品根>/设定库/声学表.json`（`{"冷宫大殿":"hall","密道":"cave","御花园":"outdoor","寝殿":"room"}`，场景名→预设）。`render_voice` 按每句所属场景在既有逐句 FX 链前置一段 `aecho` 混响（本机 ffmpeg 无 afir/areverb，统一用 aecho）。缺表=全 dry、与今日逐字节一致（严格零回归）。巡检：`python3 reverb_profile.py <作品根> 第N集`。
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
- 若使用参考音/克隆音色，先跑 `python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> 第N集 --init`，在 `voice` 段填 `uses_voice_clone=true`、授权状态、授权证据和适用角色；再跑 `python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> 第N集 --check`。只设 `VOICE_CLONE_AUTHORIZED=1` 不足以进入后续视频/合成 gate。

## 工作流
1. 前期准备（默认必跑）：
   ```bash
   python3 skills/n2d/n2d-voice/voice_preflight.py prepare <作品根> 第N集
   ```
   只写 `voice_casting.json` 与 `timing_estimate.json`，确认输出 `audio_generated=false`；此步回写 `配音=⏳rough`，含义是“时间基准已建立”，不是“已有粗 WAV”。
2. 声音试镜与定妆：为每个角色试听少量代表台词，把获批 backend/model/voice_id/canonical sample 写入选角锁：
   ```bash
   python3 skills/n2d/n2d-voice/voice_preflight.py lock <作品根> <角色> \
     --backend <后端> --voice-id <音色ID> --canonical-sample <试听样本路径> \
     --approved-by <签收人>
   python3 skills/n2d/n2d-voice/voice_preflight.py check <作品根> 第N集 --purpose final
   ```
3. 分镜/视频按 `production_mode_route_第N集.json` 推进：可见口型镜头读取已批准表演/guide 轨；没有表演轨时只出 neutral-mouth base plate，后续走 `lipsync_pass.py`。旁白/口外音和画面先行镜头使用无 WAV 时间基准。
4. 最终配音：选角检查通过后运行 `render_voice.py`。需要导引音轨时显式设 `N2D_VOICE_PURPOSE=guide`，输出到 `合成/第N集/配音_导引/`；默认 `final` 输出到 `配音/`。若用参考音，还必须满足 `VOICE_CLONE_AUTHORIZED=1` 与合规包授权。
5. final 音轨逐句生成 → loudnorm -16 → 实测时长，写 `line_NN.wav`、`voice_{zh,en}.wav`、`时长清单.json`；成功后回写 `配音=✅`。真实时长偏离前期估时后，回跑阶段2/OTIO，重做受影响口型而不是强行压速。
6. 记录生产数据：
   ```bash
   python3 skills/n2d/n2d-dashboard/scripts/dashboard.py record <作品根> \
     --episode 第N集 --stage voice --event generation \
     --asset <voice_zh.wav路径> --status pass \
     --duration-sec <配音耗时秒> --provider <CosyVoice|MiniMax|say|...> \
     --cost <成本数值> --unit <USD|CNY|credits> \
     --meta lines=<句数> --meta placeholder_lines=<占位句数>
   ```

## 完成后 · 详列下一步（收尾必做）

回写「配音」列后，跑 `python3 skills/n2d/progress.py <作品根>`（或 `run.py next <作品根>`，按 `制作模式` 给正确前沿），把「下一步」念给用户——调哪个 skill · 干什么 · 确切命令 · 可并行项：

```
第K集声音状态：
- casting：待选 / guide_approved / locked；列出仍未签收角色
- timing_estimate.json：N 句、总时长 ~Y 秒、audio_generated=false
- final 时长清单.json（若已生成）：N 句、实测总时长 ~Y 秒；voice_key 已逐句记录
- _进度.md「配音」：时间基准就绪=⏳rough / 最终真实配音=✅
下一步建议（以 progress.py 前沿为准）：
- 混合自动路由：继续 n2d-script 阶段2；口型可见镜头按 route 补表演/guide 轨或先出 neutral-mouth base plate
- 最终音色未锁：先完成声音试镜签收，不批量生成 WAV
- 最终配音已出：刷新阶段2/OTIO，完成后期口型与合成前音画对账
- 可并行：为第K+1集生成无 WAV 时间基准；共用角色沿用项目级 casting 锁
```

> ⚠️ `timing_estimate.json` 是有范围的编辑估时，不是隐藏的占位配音。成片/验收仍要求最终音轨；可见口型镜头还要求已批准表演轨或完成独立 lipsync pass。
> `制作模式=原生音画` 时说话镜不跑本 skill；本 skill 只处理旁白/系统音/非说话镜，回写后下一步通常直接 n2d-image。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 跳过合规检查，直接克隆音色 | 声音克隆合规是硬闸门，必须先在 `合规/compliance_manifest.json` 登记授权状态与证据 |
| 为了推进状态机先生成整集次品/静音 WAV | 改跑 `voice_preflight.py prepare`；用无音频 `timing_estimate.json` 锁大致时长，只为确有表演需要的镜头生成 guide |
| 改了 `voiceover.txt` 却没刷新时间基准 | `timing_estimate.json`、字幕、镜头时长已过期；先重跑 preflight，已有最终音轨时再重跑 final 配音与阶段2 |
| 未建立 `voicemap.json`，导致音色随机或漂移 | 跨集一致性依赖 `voicemap.json` 角色-音色绑定，新剧务必先建表 |
| 克隆参考音每集临时喂、不钉死 | 音色逐集漂、声纹机检只能事后报。每角色冻结一条 canonical 参考音到 `设定库/voiceprints/<角色>.wav` 并在 voicemap 写 `ref`（音色定妆照），全篇复用为克隆源 |
| 忽略 `render_voice.py` 的情绪/语速标注 | 念白是表演，必须按标注驱动 TTS 情绪和节奏 |
| 混合模式中单句生成失败仍写静音占位 | 不得把失败伪装成成功；保留已成功句并重试失败句，final/guide 清单未完整前不签收 |
| 把逐镜头混合路由当成模式冲突 | 混合正是默认：对白表演镜、旁白镜、动作/空镜、原生音画镜可走不同策略；统一由 route sidecar 记录 |
| `原生音画` 模式下仍给所有镜头配音 | 浪费额度。说话镜由视频后端出声，配音阶段只需处理旁白或非说话镜 |
| 漏记 `voice_key` 实际应用音色键 | 导致 `n2d-identity` 无法进行跨集音色一致性对账 |

## 声音克隆
见 references/cloning.md（MiniMax 复刻 / GPT-SoVITS / CosyVoice 本地克隆 + demucs 人声分离清洗）。

## 详细参考
- 后端接入与凭证：references/backends.md
- 声音克隆 + 人声分离：references/cloning.md
- 调用规范：references/usage.md
