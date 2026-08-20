---
name: n2d-script
description: Stage 1+定稿 of n2d — 阶段1把小说改成 voiceover/bgm/封面/角色场景卡并做围读签收；阶段2默认消费“无 WAV 时间基准 + 逐镜声音路线”：可见口型对白走表演音轨或基础视频→后期表演，旁白/口外音用估时，动作/空镜画面先行，原生音画按镜头合同。阶段2把在场链、seam_mode 接缝分类和模式证据锁成机器合同，并用 animatic + OTIO 时间线签收后生成 P-3 制片交接包。 Use when given a novel path, asked to start from a middle chapter/window, refine an episode, design storyboards, subtitles or recurring motif scenes. Triggers 拆集, 中段开工, 分镜剧本, 故事板, 素材清单, 配音文案, BGM, 封面 prompt, 双语字幕, SRT, 题材检测, 母题, 系统面板.
---

# n2d-script — 阶段1 剧本改编 + 阶段2 分镜设计（模式感知）

你是 **AI 漫剧编剧室 + 导演预演 + 制片交接合同**。两阶段：**阶段1 剧本改编**（台词先行，不做分镜）→ table read 围读签收 → 声音选角/时间基准 → 制作模式逐镜路由 → **阶段2 分镜设计**（默认“时间基准先行”，不是“最终配音先行”）→ animatic + OTIO 粗剪签收 → P-3 制片拆解。**不出图、不出视频**——那是 `n2d-image` 和 `n2d-video` 的事；但本阶段必须把“好看”和“紧凑”拆成可签收字段与哈希绑定审批，而不是只交一份散文剧本/分镜。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在执行脚本里**。按 `../skills/n2d/references/选择点与偏好.md` 读 `<作品根>/_设置.md`；缺失的普通可逆项由 producer-owned 推荐器选一个题材/规模感知的安全默认、以 `source=auto_recommended` 落档并继续，用户已有值永不覆盖。仅 `普通选择策略=逐项询问` 时才展示菜单；合规、不可逆、付费和最终验收仍每次确认。

本 skill 涉及的选择点：`制作模式`（决定阶段2 是否等真实配音·见阶段2 触发）、`题材`/`母题增强`（弱选择点·检测预填可覆盖：motif_detector 识别题材与系统面板等复现母题桥段·见阶段2「题材母题检测」+ `references/题材母题框架.md`）、`基础视觉风格`（写入 global_style + style_contract·见第 2 步）、`视频模型路由`（默认自动按镜头路由；本阶段只记录用户主动固定约束，具体后端到 n2d-video 决定）、`生图AI`、`画幅`、`首切范围`（首次拆集是部分先切还是全篇粗切·见第 1 步）、`字幕语言`（中文/中英双语/仅英文·见阶段2）、`脚本批次`（量产时几集一停·见「脚本批次」段）、`中段锚帧默认`（默认 `关闭`=risk-only；普通单拍不补 `_mid`，只有显式 `开启` 且执行后端单次请求原生支持 3+ 帧才补 D0；E1 编辑切点与 R1/R2/R3 高风险连续动作不受该开关影响）、`目标平台`、`发行地区`、`合规用途`。源文本版权/改编权按设计宪法 D4 默认用户为原著作者并写入 `合规/compliance_manifest.json`；明确第三方来源时才要求授权 evidence/ref。

`拆集节奏` 与 `变现模式` 都是内部软默认/高级覆盖项，不列入首跑询问。`拆集节奏` 默认 `前长后短`（旧 `_设置.md` 的 `单集时长` 继续兼容读取）；`变现模式`（`免费`默认 / `付费` / `海外`）决定**剧级追更骨架**的策略，但付费/解锁卡点只能来自项目 `_设置.md` 的 `付费卡点集/付费墙集`，或 `脚本/paywall_policy.json` 的平台合同/第一方数据；未知时只提示、不猜第 8/10 集、更不硬挡。`题材` 弱选择点同时切换 `split_novel`/`boundary_audit` 的**边界词典**（古装爽文 vs 女频情感/悬疑/都市，治非爽文题材粗拆退化成无闭环）。

## 核心原则

- **集 = 戏剧节拍单元，≠ 章，≠ 时长容器**：一集必须优先保证剧情连贯性和剧情丰满，形成完整 **冲突→爽点/反转→钩子** 闭环。`split_novel.py` 拆出的只是**粗胚脚手架**；精修时以 `raw.txt` 为素材按节拍重切。**集边界怎么定（切在哪）= 拆集第一难题，按优先级 P0→P6 下刀，必读 `references/拆集法.md`**——核心：先找结尾断点不找开头、每集一个完整「憋—放」闭环、切点要让下集能冷开场；字数/时长永远让位于节拍，不能为凑时长切断闭环，也不能为省时长删掉必要镜头、铺垫、动机或承接。
- **好看必须可签收，而不是一句“更精彩”**：`n2d-script` 不是单纯“剧本/分镜生成器”，而是上游制片合同。阶段2 定稿必须产 `script_quality_contract_第N集.json/md`：`core_attraction`（本集卖点/观众为什么看）、`first_3s_visual_hook`（0-3 秒无声也能读懂的视觉钩）、`retention_promise_ledger`（承诺/悬念/兑现）、`pacing_allocation`（主时长给哪些核心/高光 Clip，哪些桥接/解释/反应一笔带过）、逐 Clip `dramatic_function` + `pacing_role/runtime_priority` + 关键镜 `audience_effect`、`audience_question_ledger`（开放问题和下一步处理）、`performance_cues`、奇观镜 `spectacle_story_function`。`n2d/run.py next` 到 image_prompt 前会跑 `script_quality_gate.py --strict --write`；缺字段先回本阶段补，不把“看起来能画但没有追看理由”的东西交给下游。
- **时长按戏剧权重分配，不平均分配**：主干先行，精彩章节吃主时长；非关键桥接、背景解释、普通反应、氛围过门要短，能旁白/后文/相邻节拍带出就不要独立成长 Clip。`storyboard.json` 每个 Clip 写 `pacing_role` + `runtime_priority`；顶层写 `pacing_allocation`。长 Clip 必须说明它为什么值得长（主看点/高光/反转/打斗/兑现）；标成过渡/解释/一笔带过的 Clip 超过轻量时长时，必须缩短，若确实承载主干/反转/打斗/兑现就重定级为 `primary/highlight` 并写越长理由，不能靠 `compression_plan` 保留低优先级长镜。否则 `script_quality_gate.py --strict` 会阻断进入出图/出视频。紧凑不是删因果，而是把非主干压成最短可读，把打斗、强反转、情绪峰、视觉奇观拍足。
- **剧情经济性优先（省视频额度）**：默认一条短视频要承担多个信息点，不能把小说式解释、赶路、普通沉默/反应、背景情报拍成 20-35s 长段。阶段2 定稿后跑 `story_economy_audit.py <作品根> 第N集 --write`：战斗/动作、男女主或核心人物强情绪交流可给 8-15s story_clip 详拍；揭示/对质/反派登场控制 5-8s；解释、情报、赶路、普通反应压到 2-6s 或并入相邻强戏。`--strict` 会阻断非战斗/非强情绪的超长 story_clip 进入贵工位；**集内冗余机检（2026-07 实跑痛点回修·report-only 起步）**：`redundancy_audit.py <作品根> 第N集 --write` 查四类经济性审查看不见的冗余——台词两两同义反复（char-2gram Jaccard≥0.6）、同一事实短语 ≥3 行复现（措辞不同的复述）、整集旁白/系统占比 >50%（流水账感）、storyboard (场景×景别×角色) 相同的构图重复计划；`run.py` 在 image_prompt 前自动跑（落 `生产数据/redundancy_audit_第N集.*`），误报校准后再议升 `--strict` 硬闸。`shot_split_decision.py` 会把这类镜头标成 `compress_before_video`，先回编剧压缩，而不是机械拆成多个付费视频段。**集级生成次数预算 + 合并优先（2026-07-22 clip 经济性回修）**：单 Clip 时长预算之外还要看整集会产生多少次付费生成——2026 多镜叙事后端单次生成可承载多个镜位（Seedance 2.0 单次 4-15s 一次 3-5 镜、Kling 3.0 multi-shot 单次 15s；采集 2026-07-22 会过期），简单叙事优先「更少更长的多镜单拍」而不是逐节拍独立 clip。阶段2 定稿后 `run.py` 会自动跑 `clip_economy_planner.py <作品根> 第N集 --write`（report-only·全启发式·宪法 B10），产出 `生产数据/clip_economy_plan_第N集.*`：当前 vs 采纳后的预计生成次数、相邻同场景合并候选组（并成一个 story_clip + `take_policy=single_take_multishot`，各源 Clip 降级为内部 `shots[]` 镜位行）、弱信息微镜并入相邻强戏候选、**单 Clip 补 take_policy 候选**（相邻合不动但内部被编辑镜位强拆成多 take 的 ≤15s 非高风险镜——真实项目主浪费点常在这里）。加 `--emit-merge-draft` 可把合并组落成可审阅的 `clip_economy_merge_draft_第N集.json` 草案骨架（status=draft，voiceover 三轨/entity_schedule/continuity 仍须编剧手工归并重签）。合并/补字段是签收产物变更，由编剧精修时确认后改 storyboard，脚本不自动改写；高动作模板/R1·R3 风险锚/奇观镜不进候选（安全拆分优先；E1 edit_cut/R2/D0 派生锚不挡合并，合并后重跑 anchor_planner）。**复杂度感知预算 + `片段经济` 强度档（2026-07-23·治「简单叙事拆成太多 clip」让预算真正咬合）**：生成次数预算不再是平摊的 10/min，而是按本集**叙事广度**分档——场景数+角色数定基准（simple 6 / standard 9 / complex 12 次每分钟），动作/奇观镜按 0.5/镜加成（打斗合理需要更多镜位，不把「一段打斗拆成几个 clip」误判成叙事复杂）。选择点 `片段经济`（`保守`默认=仅 warn 不阻断，兼容老项目 / `紧凑` / `极简`=预算再收紧一档）：写 `紧凑/极简` 时，当每分钟预计生成次数**超本集复杂度预算且存在可采纳的合并/单拍多镜省次数**，`run.py` 在出图/出视频前经 `clip_economy_gate`（`clip_economy_planner.py … --strict`）**阻断**，逼简单叙事先合并再进贵工位；只挡「有可采纳省次数」的超预算（可执行不死锁），已无候选的天然高密度镜放行。**两条正交轴（2026-07-24 补齐）**：除 `takes/min`（一个 clip 拆几次生成）外，另立 `clips/min` **clip 数预算**（simple 6 / standard 8 / complex 11 clip每分钟）——治「作者把简单叙事拆成太多 clip」，密度轴治不了 clip 数（clip 数在 storyboard 编排期就定死、后续只并 take 不减 clip）；超预算出 `clip_count_over_budget`（`紧凑/极简`+有合并候选→block），逼合并相邻同景节拍减 clip 总数。再加「每个 clip 简短点」轴：超单次生成窗口、被拆成 ≥3 段付费 part 的长 clip 点名 `long_clips_force_part_split`（warn），建议把 beat 写短到单次窗口一段成或补 `single_take_multishot` 直接减 part 数。两轴均沉没成本豁免（已生成 clip 不追溯）。见 `n2d/references/选择点与偏好.md` `片段经济`。
- **跨集承接合同（防集与集之间断线）**：前 5 集每集 storyboard 顶层必须写 `series_handoff.previous_episode_pickup` / `opening_bridge` / `ending_throw` / `next_episode_receivable_hook`（或等价 `hook_bridge` + `retention_promise_ledger`）。第2集以后必须明示接住上一集问题、延迟兑现或切 B 线理由；非完结集必须抛给下一集可承接的问题/目标/未兑现承诺。`image_prompt_preflight/image_preflight` 会 BLOCK 缺字段和 `同上/待补/内容过薄` 的空合同，不让断线分镜进入出图。
- **story_clip / video_shot / generation take 三层铁律**：`storyboard.json clips[]` 可用 `story_clip` 表达完整小情节；`shots[]` 是剪辑镜位；后端请求只是 generation take。先按镜位/动作语法拆物理 shot：多个明确 `lens/camera/shot_size` 即使父 Clip 只有 5s 也拆；再按后端时长上限拆过长连续 take。**唯一例外：`take_policy=single_take_multishot`**——Clip 显式声明该字段且叙事跨度 ≤15s、非大表情/奇观/高生成风险镜时，内部镜位交 multishot-native 后端（Seedance/Kling 3.0 等）一次生成，`shots[]` 编成「镜头1/2/…」阶梯而不拆独立付费 take；后端不支持、跨度超窗或命中 R1 高运动/R3 漂移实证时自动回落 edit_cut 拆 take（`shot_split_decision`/`anchor_planner`/出视频 preflight 同口径机检，不靠人记）。`story_span_sec`、`edit_target_sec`、`backend_request_sec` 不得混用。4-8s 只作为多数后端的生成舒适区，不是剪辑硬下限；2s 插入镜可请求后端最短 4/5s 后裁尾。连续 take >12s 必须有拆段计划，>15s 未拆父段仍禁止直提。
- **内心戏主体隔离铁律（防重复感）**：心理反应、内心独白、心声、顿悟/疑惧这类主观镜头，默认按 **单主体 CU/MCU/手部/眼神/光影符号** 处理，只保留思考主体和必要情绪符号；其他人物、妖魔、系统面板、武器或道具转 `offscreen_presence`、虚焦剪影、记忆符号或 `forbidden_presence`，不要因为上一镜有人/物在场就继续清晰展示，避免观感像重复生成。若确需让妖魔/敌人/道具同框形成压迫，必须写 `inner_focus_context_reason` 或 `inner_focus_allow_context=true`，并说明它只作后景/剪影/虚焦压迫，不抢主观情绪焦点。
- **逐 Clip 实体排程 + 去重信息增量铁律**：阶段2 每个含角色/物件/地点 ID 的 Clip 必须写完整 `entity_schedule.characters/objects/locations/required_presence/offscreen_presence/forbidden_presence`，并把 `continuity.entry_exit` 写成机器真值；同一实体不能同时可见/必在又标 `offscreen_presence` 或 `forbidden_presence`。相邻 Clip 若同场景、同实体、同模板/动作/戏剧功能，必须合并、改变景别/动作/信息增量，或显式写 `duplicate_intent_reason`（回放/闪回/故意复现/拆段接力）。`video_prompt_preflight/video_preflight` 会把缺排程、漏登记、画外矛盾和无理由重复 Clip 拦回 `script_stage2`，避免把重复、陌生人/陌生物乱入、槽位串脸留给生视频模型碰运气。
- **改编取舍先于精修写词，允许有账的短剧化改写**：拿到 raw 后不要把每段原文都硬拆成镜头。先做 `adaptation_triage`：`dramatize/成戏`（冲突、选择、后果、反转、情绪峰、视觉高光，必须拍出来）、`narrate/旁白一笔带过`（必要信息但弱视觉/弱动作，用 1-2 句旁白或独白带过）、`defer/后文带出`（当前停下来解释会拖节奏，可在后面通过行为/对话/道具自然露出）、`merge/并入相邻节拍`（过渡或承接，随强戏一起处理）、`omit/删除`（重复、无因果负载、删掉不伤动机/伏笔/状态）。为短剧紧凑、高潮叠起、好看，可以适度 `rewrite_detail/reorder/intensify/add_hook/combine_minor_role`：改细节、重排揭示顺序、强化冲突、补视觉钩、合并小角色或把平铺信息变成更强的戏。但每次改关键细节/剧情都必须写 `adaptation_delta`，说明 changed_from/changed_to、保住的剧情功能、为什么更短剧化、伏笔/人物弧如何不破。取舍不是省成本删戏：凡承载人物动机、因果、选择后果、伏笔/兑现、状态变化、关系转折、系统规则的段落，不能无账删除；要么成戏，要么明确用旁白/后文带出或有账改写承接。
- **角色/场景一致性第一**：先建卡（含定妆 prompt），后续所有分镜严格复用。形态变体（觉醒态/银牌态）单列；长线角色发生年龄跳/成长阶段变化时也必须单列形态，新增/重出 form 与定妆文件名写年龄或年龄档，旧 form 至少补 `age_band` 和 legacy alias。若用户给“定型参考图/男女主参考图”，角色卡必须把它登记成身份基准：后续少年态、成年态、高阶态、受伤态、觉醒态都要从同一参考图的脸型、五官比例、眼神和气质派生，不得因为年龄变化临时换脸；同时明确哪些是剧情服装/发饰/特效变化，哪些是不可漂移的角色 DNA。
- **接缝先分类，再决定是否接力**：每个 Clip→下一 Clip 必须显式写 `seam_mode`：`continuous_take_relay / match_on_action / graphic_match / eyeline_cut / reaction_cut / insert_cutaway / j_cut / l_cut / dissolve / hard_cut / intentional_discontinuity`。只有 relay 要上一尾帧=下一首帧与边界 SHA；动作匹配看动作相位/方向，graphic match 看前后匹配元素和构图关系，视线/J-L/反应/插入/溶解各看自己的证据。下游 image/video/compose/review 继承同一分类；旧项目迁移候选仍须 P-2 签收。
- **拆段接力三轨分配铁律**：分镜或 video_preflight 把一个逻辑镜拆成 A/B 两个物理 Clip 时，必须同步拆 `dialogue / narration / screen_text` 三轨：`voiceover_indices` 互斥，且按角色对白 vs 旁白分出 `dialogue_indices` / `narration_indices`；屏幕文案写 `screen_text_lines[]`，每条带 `render_policy=compose_overlay_only`。A/B 可以在画面上有 0.5-1.5s 接力反应或动作重叠，但对白、旁白、屏幕文案都不能重叠，尤其原生音画 `native_speech` 不得让上下半段都拿同一句“问年龄/回答年龄”。**执行分工是铁律**：角色对白可交原生音画后端做口型；旁白一律是 compose 阶段音频，不交视频模型直接生成；屏幕文案/花字/字幕一律是 compose 阶段 overlay，不让视频模型烤字。屏幕文案只用于章节钩子、关键数字、状态变化和静音可读证明，不承载长解释。拆完必须生成或刷新 `生产数据/dialogue_fact_contract_第N集.json`（由 n2d-review 的 `dialogue_fact_guard.py --write` 产出），把每个物理 Clip 的 allowed dialogue/narration/screen_text 和年龄/身高/灵根/数量事实锁死；年龄、身高、趟数、灵根等数字事实只抄角色卡、剧情账本和 `voiceover.txt`，不许在视频 prompt 里自由改写。
- **状态/交互/因果账本前置（review warn 回灌）**：阶段2 不是只交镜头文本，还要把“谁在场、谁触碰谁、什么状态如何变化、物理后果是什么”结构化。凡出现抓腕/拉扯/拥抱/攻击命中/法术碰撞/系统面板数值变化/身份揭示/伤势变化/持物转移，storyboard 必须同步产或刷新 `生产数据/state_transition_manifest_第N集.json`、`interaction_graph_第N集.json`、`contact_graph_第N集.json`、`causal_event_graph_第N集.json` 或等价字段；缺这些 sidecar 时，review/score 会把状态连续、交互连续、物理因果列为缺证据，下一轮先回本阶段补合同，不先让图/视频临场猜。
- **复杂镜头套模板，不从零写 prompt**：打斗、追逐、对话反打、真相揭示/身份曝光、公开对质/审讯/谈判、法术爆发、飞行、御兽/坐骑、马车/载具行进、飞舟/御物飞行、现代车辆/车流、手机/电脑/监控屏幕、搜证/物证发现、尾随/潜入/暗走廊、渡劫突破、打坐静修、炼丹炼器、双修合修、阵法仪式、神魂显化、穿越/传送/秘境入口、契约召唤、测灵/天赋觉醒、接吻/近吻、亲密互动、拥抱/拉扯、关系转折、多人同框、群像站位都先读 `references/专项镜头模板库.md`，在 `storyboard.json` 写 `template` + `template_contract`。模板不是限制创作，而是把动作节拍、轴线、站位、证据/反应链、关系前后态、起落幅、关键帧和负向约束结构化，避免每次临场发明导致 AI 崩动作/跳轴/乱站位/情绪断层。静修/炼制/双修另读 `references/静修炼制双修精修标准.md`；接吻/拥抱/牵手/搀扶另读 `references/亲密动作精修标准.md`；双修只按成年人、自愿、非露骨的能量循环/疗伤表达。
- **传统正反打落地铁律（对话/对峙）**：`dialogue_shot_reverse` 不是“换个角度拍两个人”，而是 180° 行动轴线 + 屏幕左右/9:16 纵深高低位关系 + 互补视线 + A/B 成对 coverage。凡使用该模板，`template_contract` 必填 `axis / screen_sides / eyeline / shot_pairing / coverage_order / camera_coverage / lens_height_distance_match / crossing_axis_policy / buffer_or_reestablishing`；P-2 签收后跑 `shot_reverse_contract.py --write` 物化独立 `脚本/第N集/shot_reverse_contract.json`，P-3 `continuity_bible.json` 必须继承 `shot_reverse_continuity`。**不要在已签 P-2 后默认加 `--sync-axis-map`**：该参数会改写签收证据并使哈希失效；只在 P-2 签收前，或明确重开 P-2 且准备重新签收时使用。无理由越轴、A/B 左右交换、看镜头替代看戏内对象、OTS 没有前景肩部、近景多人同框不拆反打，全部按连续性硬伤处理。传统影视镜头语法优先读 `references/传统影视镜头语法库.md` / `cinematic_coverage_grammar.json`。
- **重动作多中帧铁律**：打斗、追逐、法术/武技撞点、多主体接触、抓腕/拉扯/拥抱等重动作镜，只要单 Clip 时长 `>=8s`，或同一 Clip 包含“起手/蓄力/逼近 → 命中/接触/撞点 → 反应/收势/余波”动作链，`storyboard.json` 必须写 `continuity.anchors[]`，不能只写 `continuity.midframe`。定稿后先跑 `python3 skills/n2d/n2d-script/scripts/anchor_planner.py <作品根> 第N集 --write`，再让 n2d-image 出对应 `_a1.._aN` PNG；video gate 会对缺 anchors 的长/重动作镜 WARN 或 BLOCK，触发 n2d-video 自动走 native_multiframe 或 split_relay，而不是等成片断动作后返工。
- **普通镜不设“三帧最低要求” + 编辑镜位先拆 take**：`中段锚帧默认` 的全局缺省为关闭（risk-only）。普通单拍用首帧或首尾帧；只有高风险连续动作、漂移实证或用户显式 opt-in 才补中段锚。相反，`shots[]` 一旦明确写出多个 `lens/camera/shot_size`，它表达的是编辑切换，不是“一条视频里的多个提示词段”：`anchor_planner` 在镜位边界写 `use=edit_cut`，`shot_split_decision`/runner 把每个 shot 变成独立物理 take。父 Clip 即使不足 5s 也照拆；每条 take 的剪辑目标可短于后端最短生成档，后端多出的尾巴由视频 prompt 保持落幅、compose 裁尾。
- **平台无关核心 + 平台档案**：分镜/卡片/节拍/字幕都平台无关；各平台档案见 `references/platforms.md`。本阶段不选择具体生视频后端；视频阶段默认 `视频模型路由=自动按镜头路由`，由 `n2d-video` 在出视频前通过 router/probe 决定目标视频模型/渠道，只有固定模式、账号/交付硬约束或无法自动执行时才询问并落档；旧 `生视频AI` 只作兼容 fallback。
- **爽剧节奏 = 留存工程**：`拆集节奏` 只是内部节奏预设/容量软目标，不设硬上限或下限，也不在首跑打断用户选择。最终一集多长由剧情闭环、爽点释放、集尾钩子和配音/原生音画实测共同决定；短集和长集都可保留，前提是 **冲突→爽点/反转→钩子** 成立。**导演的第一任务是"让观众这一秒划不走"**——0-3秒冷开场、前6秒必须有钩子、前15秒立钩子+矛盾，中段只保留有信息增量/情绪推进/动作推进的 Clip，非关键解释用短旁白或一笔带过；每15-20秒一个钩子/信息增量、≥1次反转、集尾 cliffhanger 硬断。阶段2 的 `storyboard.json` 必写 `first_3s_visual_hook` 硬字段（`visual_hook（冲突/悬念/欲望/反差/信息/危机皆可，旧名 visual_conflict 兼容，可选 hook_type 标类）/ content_proposition / onscreen_text / muted_safe_proof / expected_metric`；`primary=retention_3s/retention_6s` 且 `target` 不低于当前 `retention_hook_floor`，烧屏文字不得过载）、`retention_promise_ledger`（每个开场/尾钩的 `hook_id / promise_type / opened_at / promise / payoff_due`，本集到期必须补 `payoff_status + payoff_evidence`）和 `pacing_allocation`（主时长/压缩时长分配），否则 `beat_audit --strict` / `script_quality_gate --strict` 会在正式出图 prompt 前阻断。详见 `n2d/references/导演节奏.md`，这是治"节奏平/中段划走/不追下集"的核心；若其中有 `n2d-feedback` 投放数据快照，下一批分镜优先吸收高留存开场、强追更 cliffhanger、付费卡点和低跳出镜头密度。
- **基础视觉风格前置**：风格是选择点，不是 skill 铁律。先按 `基础视觉风格` 写 `global_style.md`（菜单见 `n2d/references/visual_styles.md`），阶段2 写 `storyboard.json` 时必须同时写 `style_contract`（风格名 / 视觉基调 / 镜头与构图 / 光色策略 / 运动边界 / 风格禁忌 / `style_anchor`）。用户要求参考当前影视、红果或同类漫剧时，先按该 reference 的“视觉竞品研究”流程搜索核验，把有日期、有来源且区分事实/视觉推断的结论写入 `设定库/视觉竞品研究.md`，再与原著、用户参考图合成契约；竞品只拆可迁移变量，不复制演员脸、具体镜头、海报版式、Logo、水印或另一 IP 的独占符号。`style_anchor` 默认指向 `出图/共享/图片/风格锚_<风格名>.png`，由 n2d-image 先生成/签收并登记 registry；缺锚不得进入正式分镜图或视频。下游出图/出视频继承这份契约，不靠末尾补 `cinematic/realistic/anime` 这类泛词。旧 `cinematic_contract` 仅兼容旧项目。
- **合规与版权前置（P0 · 改编前先建包）**：首次拆集/改编前先跑 `python3 skills/n2d/n2d-compliance/scripts/compliance.py <作品根> --init`，至少填 `rights.source_text`、`rights.adaptation`、`distribution_intent`、`platform_review.targets` 的初始状态。按设计宪法 D4，仓库创作源文本和同源漫剧改编默认 `original`，不得要求用户反复补原著/改编授权证据；只有明确第三方来源才改为 `licensed/user_declared/public_domain` 等路径并留 evidence/ref。进入出图/出视频/合成前仍会由 `gate.py` 硬拦 unknown/pending/unlicensed；不要等成片后才追平台审核、角色/声音授权或出海本地化。
- **对白活人感（写 voiceover/台词前必读 `references/对白与活人感.md`）**：AI 能写对白、难写活人感——直陈情绪、说教、旁白代角色总结是短剧头号劝退，也是 AI 输给真人的那一格。改编不是把旁白念出来：把源小说的叙述/心理描写**转成被角色说出来、做出来**的台词（潜台词>直给、show-not-tell、动机藏进行为、设定靠情境逼出、留白、言行不一、信息不对称）；每个有台词的角色落「角色声音卡」做到**遮名盲听辨人**；冷开场首句带钩、爽点台词情绪+信息双回报、长度贴口播时长。写完用 `python3 scripts/subtext_audit.py <作品根> 第N集` 自检（**advisory·不阻断**，宪法 B10），命中的 AI 味回参考对应条改。
- **画风统一**：依项目 `global_style.md` 与 `style_contract`；禁止跑到未选择的风格（如未选 Q版却低幼化）或跨镜画风漂移。
- **生产数据记账铁律（P0）**：阶段1 剧本改编、阶段2 分镜设计完成后，都要调用 `n2d-dashboard` 记录 `stage=script` 事件：耗时、使用的模型/agent/provider、产物路径、涉及集数；若边界重切、分镜返工或 validate_timings 失败，记录 `redraw_reason` 或 QA 事件。脚本文本便宜但会决定下游贵工位，成本和返工不能漏算。
- **低成本验收先于贵工位（P0）**：阶段1 后先做 `table_read_packet`，检查台词可演性、角色声音、信息密度和时长风险；此时尚无 storyboard，`story_economy` 明确记为 `not_applicable_before_storyboard`，不能拿提前运行产生的 `missing_storyboard` 假阻塞影响围读判断。阶段2 后先做 `animatic_packet` + timed animatic HTML/JSON，检查镜头节奏、信息可读、连续性和贵工位风险。两者都是 `story_acceptance_packets.py` 生成/检查的前置包，不新增 `_进度.md` 列，但未 confirmed 或 executable preview 生成失败时，`run.py next` 会阻断进入下一贵工位。

## 入口

**情境 A — 首次拿到小说**（作品根不存在）：
执行"第 1 步 首批 10 集粗切 + 建骨架" → "第 2 步 全局" → "第 3 步 精修第1集"。**默认先做前 10 集试切**：`split_novel.py` 省略 `--limit` 时只落地前 10 集 raw 脚手架，但 `脚本/split_plan.json` 默认 compact v3，以源快照指纹、规范化 source-unit 索引和稀疏信号轴保存全书规划，并保留每集 span、`boundary_candidates` 与 advisory Top-3 beam paths；需要旧逐单元对象时必须经兼容 helper 重建，不直接假定 `source_units` 是 list。机器摘要写 `脚本/_拆集机器索引.md`，人工决定只写 `脚本/_拆集复核.md`，续切不得覆盖人工文件。存储/迁移/回退见 `references/split_plan_storage.md`。完成后报告，让用户决定继续精修、用 `--limit N` 续切、用 `--all` 补全，或调 `n2d-image` 出图。
> 首批 10 集、Top-3、beam width 24 与精修前 5–10 集窗口是 n2d 当前的可调工程默认值，不是行业统一标准；真正硬约束是全书 source span 可追溯、双侧叙事合同成立、人工文件不被覆盖，以及变更决策有已应用收据。完整验收表见 `n2d-review/references/production_acceptance_v2.md`。
> **首跑先定 `制作模式`**：默认由 `普通选择策略` 直接落 `混合自动路由`（声音选角 + 无 WAV 时间基准先行，再逐镜分流）；只有显式逐项询问才展示混合/配音先行/原生音画/先视频后配音菜单。阶段1后 `production_mode_router.py` 逐集写逐镜执行合同，不覆盖用户已有选择。
> **生视频后端选择后移到 n2d-video**：拆集前只记录用户已明确给出的固定模型/渠道或账号硬约束；否则写/沿用 `视频模型路由=自动按镜头路由`，不展示 `生视频模型` + `生视频渠道` 菜单。真正的 primary/fallback、渠道、CLI/API 可用性和回退/保真实现方案，由 `n2d-video` 出视频前按每个 Clip 的能力需求、router/probe 和适配层决定。
> **首跑再定 `基础视觉风格`**：`split_novel.py` 用 `recommend_style()` 按题材给出候选排名；默认策略直接把最优可用推荐写入 `_设置.md` 和 `global_style.md`，不单独停线。只有显式逐项询问才展示 `n2d/references/visual_styles.md` 菜单；用户选参考媒体识别时，先归一成预设或 `自定义（...）` 六字段契约，不把临时入口原样落档。用户已有值始终优先。

**情境 B — 精修某具体集**（作品根已存在）：
跳到"第 3 步 精修该集"。先读 `_进度.md` 看该集物料列状态；再读 `脚本/boundary_review.json`（若存在），只消费 blocker code、双侧边界合同与 receipt/semantic evidence 都通过的决策，别机械照搬单个 `raw.txt`。

**情境 C — 从中间章节/中间集开始制作**：
先做"第 -1 步 中段开工前情资产包"，再进入拆集/精修。不要只把目标章节切出来直接写 voiceover；否则主角常态定妆会被当前章节临时状态污染，人物关系/战力/道具/伏笔会断层，后续补前面章节时容易返工。

## 脚本批次（选择点 · 集级停审 + 报边界，量产时用）

物料脚本是**纯文本**（便宜、快、改起来零成本），所以**不做集内逐物料项停审**（那只增摩擦不省成本）——voiceover 这种一集的词必须连起来读才看得出节奏。但**跨集量产**（一次改编/分镜很多集）需要节奏控制，且物料层最值钱的复核点是**集边界（切在哪）**——边界错了，下游配音/出图/出视频全返工。所以这里的"切分"是**集级**的，重点在**每集先报边界决策**。

按 `../skills/n2d/references/选择点与偏好.md` 读 `脚本批次`。默认推荐 `小批`（每批 5 集）并在每批末报告；`普通选择策略=推荐方案自动继续` 时报告不额外暂停，显式 `逐项询问` 才让用户先选档。

- **逐集**：每改编/分镜 1 集报告一次边界决策与物料清单；适合第 1 集打样或用户显式要求细审。
- **小批**（默认推荐 5 集）：每 N 集附 5–10 集边界复核窗口；默认策略记录报告后自动继续。
- **整批一次过**：一口气改编/分镜用户指定范围，最后统一报告；适合边界已经结构化签收。

**逐集/小批循环**（每单位）：定边界 → 产物料 → 记录「边界决策 + 物料清单」→ 默认继续下一单位。第 1 集仍单独产出并重过 P-1/P-2/P-3 合同；报告本身不是用户停点，哈希签收和高风险边界照常执行。

## 工作流

### 第 -3 步 — P-1 剧集开发包（拆集/写词前先过制片绿灯）

拿到小说后不要直接写第1集 voiceover。先把作品从“小说文本”提升成一份可生产的短剧开发包，确认这部剧为什么值得追、怎么改、前 3-5 集怎么留人、哪些资产/镜头/声音/合规会卡住。`split_novel.py` 首跑会自动在 `<作品根>/开发包/` 创建草稿；`n2d/run.py next|enter` 在 `script_stage1` 前会自动跑 `development_pack.py check --write-missing`，未确认则阻断。

```bash
python3 skills/n2d/n2d-script/scripts/development_pack.py <作品根> scaffold --write
python3 skills/n2d/n2d-script/scripts/development_pack.py <作品根> check --json --write-missing
```

五个必填产物：

- `开发包/series_bible.md`：一句话卖点、目标受众、主角欲望、长线悬念、世界观规则、核心爽感、角色弧。
- `开发包/adaptation_strategy.json`：`dramatize/narrate/defer/merge/omit/rewrite` 的总策略；明确哪些剧情功能不能删。
- `开发包/season_arc.json`：前 3-5 集追更小弧、冷开场、兑现/反转、集尾断点、付费/关注卡点、名场面排布。
- `开发包/production_feasibility.json`：核心角色、场景、道具、奇观、声音、模型路由、合规风险与降级方案。
- `开发包/pilot_greenlight.md`：第1集/第1-3集/高风险 Clip 的打样清单、通过标准和小批量放量条件。

**完成与签收分离**：模板默认 `status: draft`；内容补齐并删除 `待补/TODO` 后置为 `confirmed`，只表示“可审”，不等于批准。随后用独立的 `开发包/signoff.json` 绑定当前输入与五件套 SHA；P-1 至少需要 creative（导演/总编剧/showrunner）和 producer 两个角色组批准，作者身份不能自签。单人团队可以用同一个明确 `reviewer_id` 分别承担两个角色，但仍要留下两条角色记录：

```bash
python3 skills/n2d/n2d-script/scripts/signoff.py <作品根> p1 approve --reviewer-id user:<姓名或账号> --reviewer-role director
python3 skills/n2d/n2d-script/scripts/signoff.py <作品根> p1 approve --reviewer-id user:<姓名或账号> --reviewer-role producer
```

任何上游输入或待签产物变化都会使哈希失效并要求重签；创建文件、把状态改成 confirmed、或由生成者写一句“已确认”，都不能代替签收。

### 第 -2 步 — 源理解合同 gate（最上游·所有源先理解再拆集）

不能把小说只当章节切分材料。拆集前必须先把编剧理解变成可审计输入：现代白话理解、长篇伏笔、爽点/承诺账、人物动机、因果链、改编边界、设定/战力规则。`run.py next` 在 `script_stage1` 最上游已自动跑 `source_language.py`；只要作品根下有 `小说/*.txt`，没有 confirmed 的源理解合同就阻断。

```bash
python3 skills/n2d/n2d-script/scripts/source_language.py <作品根>            # 源理解合同 check
python3 skills/n2d/n2d-script/scripts/source_language.py <作品根> --scaffold # 建/刷新源理解合同脚手架
```

- `source_language.py` 仍会识别 `modern_zh` / `classical_zh` / `non_chinese`，但 register 不决定是否放行。明清章回体/近世白话保持 `modern_zh` 兼容，并另标 `register_profile=late_imperial_vernacular`，使用专门脚手架；`囬/囘/廻/節` 等异体章回标题也按章节单位识别。
- 处理三步：
  1. `--scaffold` 生成 `设定库/source_comprehension.md` + `设定库/source_comprehension.json`（机器记录·register/信号/status/contract）。
  2. 补全 `source_comprehension.md` 和 JSON 的 `understanding_contract`。必填块：`modern_understanding`、`episode_promise_basis`、`character_motives`、`causality_chain`、`foreshadowing_ledger`、`adaptation_boundaries`、`power_system_rules`；疑似系统流/修炼/战力题材时，等级规则、成长限制、战力一致性必须写实，不能只写“不适用”。
     - 若 `register_profile=late_imperial_vernacular`，还必须补 `premodern_adapter`：`coverage_scope`、逐回/逐章 `unit_glosses`、`historical_terms`、诗词/评论策略、说书套语策略、历史语境、敏感内容策略与 `dialogue_style_target`。默认目标是“现代可懂白话为骨，保留关键古称谓和少量章回韵味”；不逐字硬译、不满篇仿古，也不把诗词、作者议论、说书套语和剧情正文机械等权成戏。
  3. 把 `source_comprehension.json` 的 `status` 置 `confirmed` → 闸放行。**下游从源理解合同拆集**，后续每集承诺、分镜意图、制片拆解、引用槽位、动作物理、音频时长和 release verdict 都要能追溯到这层理解。

> 文体识别纯关键词密度判定（强文言标记 vs「的」密度 vs 现代虚词；CJK 占比判外文）·不调模型·保守（现代白话夹"之乎者也"成语不误判）。判定阈值/标记集见 `source_language.py` 顶部常量。

### 第 -1 步 — 中段开工前情资产包（从中间章节开始时必做）

当用户说"从第 X 章开始做"、"先做中间爆点"、"不从第1章开始"、"拿第 N 集打样"时，先创建并补齐 `设定库/中段开工前情资产包.md`：

```bash
python3 skills/n2d/n2d-script/scripts/midstart_context.py <作品根> scaffold --target "第48章" --window "第45-52章"
python3 skills/n2d/n2d-script/scripts/midstart_context.py <作品根> check
```

如果用户只说"从大反转附近"、"从女主觉醒后"、"大概从某段开始"这类模糊起点，不要把定位问题丢回给用户：先扫描章节标题、目录和关键词命中段，自己判断最接近的章号，再调用 `split_novel.py --start-chapter <章号>`。`--start-chapter` 只负责裁出本次 raw 脚手架；它不能替代下面这份前情资产包。

最少必须补齐五块：

- **主角角色卡/身份基准**：常态外貌、当前章节形态、禁漂锚点、战力/境界、关系状态。常态定妆与当前形态分开，别把受伤、战损、觉醒、黑化等临时状态写进常态定妆。
- **角色形象生命周期**：第几章/第几集发生换装、觉醒、受伤、变体、年龄跳；哪些变化要提前建新形态定妆，哪些只是集内状态。年龄跨度大的主角/长线角色必须规划 `年龄/年龄档 → form → 定妆文件前缀`，不能让14岁、18岁、成年、高阶长生态共用一套无年龄标识定妆。
- **前情摘要**：到目标章节前的主角经历、关键选择、当前目标、主矛盾、未兑现伏笔/系统规则。
- **关键角色/场景/道具卡**：目标窗口会出现的具名角色、主场景、武器/法宝/证物/系统面板/VFX，缺卡先补卡。
- **目标章节前后窗口**：至少看目标章节前后几章或 5-10 集窗口，写清前一幕承接、0-3 秒冷开场、窗口末端钩子和边界决策。

`midstart_context.py check` 通过后才能进入正式写词。`n2d/run.py next` 在 `script_stage1` 前若发现该文件，会自动检查；仍有待补字段时会 block。若确实没有某项，写"无"即可通过，不要留"待补"。

### 第 0 步 — 确认双轴

跟用户确认（缺省即用默认）：
- 小说路径
- **视频后端硬约束**（可选；默认不问）—— 只读/记录用户主动指定的固定后端、单账号、交付限制；没有这类硬约束时保持 `视频模型路由=自动按镜头路由`，具体 `生视频模型/生视频渠道` 延后到 n2d-video 阶段。旧 `生视频AI` 兼容读取
- **目标生图模型/渠道**—— 按 `生图模型 + 生图AI/生图渠道` 选择点；当前 n2d 正式出图默认 OpenAI GPT Image 系列 via Codex，可选官方多参考/主体后端；不把 `同视频模型/渠道` 写成默认，也不用即梦/Dreamina 生图兜底
- **基础视觉风格**（决定 global_style 与 style_contract）——默认由 `普通选择策略` 自动落推荐值；显式逐项询问时才用 `n2d/references/visual_styles.md` 菜单

详见 `references/platforms.md` 的"两轴架构"章节。**输出位置 = 作品根（与 `小说/` 同级）**：脚本素材进 `脚本/第N集/`；全局 `_进度.md` 放作品根；`global_style.md` / `characters/` / `locations/` 进作品根的 `设定库/`。`global_style.md` 只记录基础视觉风格、视频路由策略和"生视频后端延后到 n2d-video"；自动模式下具体逐 Clip 后端见 `video_model_routes.json`。

> **关键铁律**：Stage 1 不再决定生视频模型。出图阶段使用 `基础视觉风格` + 视频兼容锚定策略生成首帧；到 n2d-video 阶段，router 必须优先选择能消化现有首帧风格/锚定的后端。若用户临时固定一个与已出图风格不兼容的后端，必须停下提示重出图/重拼锚定或改路由，不能静默硬切。

### 第 0.5 步 — 主线提炼 + 支线剪枝（拆集前的全书改编策略 · 像真编剧一样整体掌控）

拆集前，像真实编剧改编长篇一样先**提炼主线、砍掉偏离主线的旁枝、修不合理点**，而不是把每条支线都逐集成戏——否则简单叙事也会被拆成过多集/节拍/clip。这一层落 `开发包/story_spine.json`，由 `run.py next` 在 `script_stage1` 消费 `development_pack` 后自动跑（消费 `设定库/source_comprehension.json` 因果链/伏笔账 + `开发包/adaptation_strategy.json` 受保护功能）。

**先拿机检提案，再做语义取舍（`editorial_revision.py`·整体改良的提案层）**：不要对着空 story_spine 从零起草。`run.py` 会在 story_spine 前自动跑 `editorial_revision.py build`，机检挖出四类编辑信号落 `开发包/editorial_revision_worksheet.md`——① **与主线不相干的琐碎支线**（贡献分低的 tangent/supporting 线程，按最该砍排序 → 提案 cut/compress）；② **埋了没还的伏笔**（`status=open` 却没线程回收 → 补还或删设定，受保护伏笔必须补还）；③ **主线接不上处**（`must_keep` 因果承接点没被任何 spine 节点 `depends_on` 引用）；④ **不合理点候选**（2026-07-24 补齐「改掉不合理的地方」的信号真空）：机检因果链/动机/力量体系里的巧合便利天降词面（contrivance）、动机缺阻力/选择压力（motive_without_stakes）、世界观设了代价却无代价用力（uncosted_power_use）、前因缺失零重叠（ungrounded_cause·保守判）——**全是候选不是定论**，你必须**逐条核对原著**：真是硬伤就写进 `continuity_fixes`（最小改动+`no_contradiction_proof`），是原著本有铺垫/有意为之就在 `revision_ledger` 记 dismiss；**绝不据候选凭空加情节**。你**像真实编剧**据此做语义判断：砍琐碎、合冗余、修不合理、突出主情节，把决定落回 `story_spine.json` 的 `threads[].decision/connectivity` 与 `continuity_fixes`。**贡献分是机械信号防误判**——承载受保护伏笔/主线因果依赖/高权重的支线分高、不会被当琐碎误砍。

```bash
python3 skills/n2d/n2d-script/scripts/editorial_revision.py <作品根> build --write   # 机检编辑提案 → 工作单
python3 skills/n2d/n2d-script/scripts/story_spine.py <作品根> scaffold --write
# 据工作单把 threads 决策/continuity_fixes 填进 story_spine.json，再：
python3 skills/n2d/n2d-script/scripts/editorial_revision.py <作品根> check --json     # 防瞎编：动作账 id 必须真实 + 砍除须有 reroute
python3 skills/n2d/n2d-script/scripts/story_spine.py <作品根> check --json --write-missing
```

> **防瞎编铁律（改编不能编）**：`editorial_revision.check` 与 `story_spine.check` 都只认 `source_comprehension`/`story_spine` 里**真实存在的 id**——`revision_ledger` 引用任何臆造的 foreshadow/causal/thread id → block；任何 `cut/fold` 动作缺 `reroute`（砍后主线/伏笔由谁承接）→ block。这就是「你得整体掌控小说、不能瞎编、改了之后要能和后面主要情节衔接上」的机器保证。

产物 `开发包/story_spine.json`：
- `mainline_logline` + `spine[]`：一句话主线 + 主线节点链（每节点写 `source_span`、`causal_role`、`depends_on`），把"主情节"从散文里拎出来。
- `threads[]`：把每条线程分 `class`=`spine`（主线）/`supporting`（服务主线的支线）/`tangent`（偏离主线的旁枝），给 `decision`=`keep`/`compress`/`fold_into_main`/`cut`。**所有非 keep 决策必须写 `connectivity`**：`payoff_reroute`（裁后伏笔/因果由谁承接或明确退役理由）+ `no_orphan_proof`（证明裁后无孤儿伏笔、下游主线不断裂）；引用 `opens_foreshadow`/`pays_foreshadow` 必须是 `source_comprehension` 里真实存在的 `trace_id`（**禁止臆造**）。给 `cut_keywords/source_spans` 让下游免账；`decision=cut` 线程的 `source_spans` 写成严格机读的「第X章 / 第X-Y章」（或整数 `source_chapters`，机器优先）时，`split_novel.py` 拆集会把这些章**整章剔除出集内容**（enforce 档真剔、advisory 预览记账、冲突章宁保不剔、逐章记账进 `split_plan.json.spine_pruning`，详见 `references/拆集法.md` §主线剪枝）。
- `continuity_fixes[]`：把原著不合理/矛盾点改掉，每条写 `fix` + `no_contradiction_proof`（证明不与后文已确认事件冲突，引用 SPINE/SRC_FORESHADOW id）；触及受保护功能要格外证明。
- `protected_invariants`：镜像 `adaptation_strategy.protected_functions`，cut/fold 线程不得触碰。

**强度选择点 `主线剪枝`**（见 `n2d/references/选择点与偏好.md`）：`保守`=仅建议不阻断（兼容已拆集老项目）；`突出主线`（推荐新作品）/`激进精简`=缺 confirmed 且过校验的 story_spine 时阻断写词。`_设置.md` 未写此键时按 advisory，不阻断老项目。

**忠实底线**：只对**已确认**的因果链/伏笔账操作；改编要能和后面主要情节衔接；带 `do_not_drop_reason` 的伏笔若唯一承载线程被 cut 且无 reroute → block（防孤儿伏笔）。**主线衔接机检（2026-07-23·把「改了要衔接上」从散文断言升级为机器验证）**：`story_spine.py check` 现消费 `spine[].depends_on` + 线程 `connectivity.downstream_mainline_deps` + 源理解合同因果链，构成主线依赖图并硬核：① 被主线节点 `depends_on` 的源因果依赖，若其所有承载线程都被裁/折叠且无 `payoff_reroute` → `mainline_dependency_orphaned`（裁后主线接不上）；② 源因果链标 `must_keep` 的承接点被裁/折叠且无 reroute → `must_keep_cause_cut_without_reroute`；③ `depends_on`/`downstream_mainline_deps` 引用不在源因果链/伏笔账/主线 id 里的 → `causal_dep_fabricated`（禁止臆造依赖）。无因果链的老项目不误报；enforce 档(`突出主线/激进精简`)才阻断，`保守`仅 advisory。被 spine 显式 `cut/compress/fold` 且给了 `cut_keywords` 的支线，其源文内容在 `source_adaptation_audit` 按"全书级有账剪枝"免账，不必再逐句登记 `adaptation_triage`——这就是"裁一条支线"和"逐句免账"之间的省力接口。

### 第 1 步 — 自动拆集 + 建骨架

**拆集节奏不再询问用户，也不默认锚定字数**。系统内部默认 `拆集节奏=前长后短`，只表示节奏倾向；旧项目 `_设置.md` 的 `单集时长` 仅作兼容读取。拆集是三层：

> **三层拆集**：① 章/场景/强钩候选出粗胚（估总集数 + 给精修窗口留素材）→ ② **节拍重切**：把边界 snap 到最近的「完整节拍 + cliffhanger」处（可前后挪段、并集、拆上下）→ ③ 配音/原生音画后用**实测时长**做节奏校准。**节拍盖过字数，剧情闭环盖过时长，剧情丰满盖过省时长。**
>
> ②的"切在哪"按优先级下刀，**开拆前必读 `references/拆集法.md`**：**P0** 先找结尾断点不找开头 → **P1** 每集完整 **冲突→爽点/反转→钩子** 闭环（杜绝纯铺垫集）→ **P2** 切点让下集能 0-3s 冷开场 → **P3** 钩子密度达标、平淡段并入相邻集（杜绝纯过渡集）→ **P4** 时长只作软节奏意图，不设硬上下限 → **P5** 尽量切在换景/换视角/时间跳跃的自然幕界（降跨集崩脸·利复用）→ **P6** 新角色分摊登场、首集加权（扛世界观+系列总钩）。**低优先级永远让位高优先级**。

按当下 AI 漫剧主流（2026：竖屏漫剧常见 1~2 分钟，精品/剧场向更长）保留节奏倾向，但**不作为首跑菜单**。读 `<作品根>/_设置.md` 的 `拆集节奏`（兼容旧键 `单集时长`）；缺则静默用默认「前长后短」。只有用户明确要求改变拆集节奏时，才把高级覆盖写入 `_设置.md`。`--target` 是高级参数，默认不传；传入后也只用于报告/人工复核，不参与切点决策。

| 预设 | 节奏意图 | 备注 |
|---|---|---|
| **前长后短**（默认·推荐） | 第1集更充分立世界观/主角欲望/系列总钩；后续碎快追更 | 不写入硬字数 |
| 均衡 | 不挑前后、均匀中速 | 只影响人工节奏判断 |
| 快节奏 | 红果/抖音碎切、极致留存 | 倾向更密的钩子候选 |
| 长集 | 剧场/精品漫剧，容纳更完整的大场戏 | 倾向更完整的大场戏闭环 |
| 自定义 | 用户主动给一个软目标或节奏描述 | 只作报告/人工复核 |

> ⚠️ **字数↔时长是高方差代理，非 1:1**：原文→台词压缩率因段落剧烈波动——对白/打斗段压缩少，环境/心理描写段压缩多。默认粗拆不锚字数；`--target` 只是高级报告参考。**不允许为了追 target 把一场戏、一个爽点或一个集尾钩子切断**。最终短/长都可以，关键是剧情连贯且闭环完整。
> ⚠️ **禁止为省时长删剧情**：可以压缩重复描写、合并平淡段、调整边界、提高台词密度；不能删掉人物动机、冲突起因、铺垫承接、伏笔回收、动作转折等必要镜头/段落。任何删除都必须能说明"重复/非剧情必要"，并写入边界决策。

**首批试切铁律（2026-07-14 修订）**：首次拆集默认 **只落地前 10 集**，但结构规划必须覆盖全书。`split_plan.json` 默认 compact v3，以源快照 + 规范化 source-unit 索引 + 稀疏 signals 保存全书章节/场景/看点线索，并保留所有机器分集的 source-unit span、每个边界的局部 Top-3 候选和全局 beam Top-3 路径；旧 verbose v2 仅供 `--legacy-plan-v2` 兼容/回滚，消费者统一用 `iter_source_units()` / `iter_arc_anchors()` / `source_unit_count()`。候选优化只用结构/句形/软均衡评分，题材词典不能硬排除边界。confirmed `开发包/season_arc.json` 会连 SHA 与意图一起纳入；只有显式给出 `boundary_after_source_unit_id/source_unit_id/source_unit_span` 时才给 beam 加约束，未映射就诚实标 `unmapped`，不从散文臆造切点。结果必须经语义复核后才改 raw。

- **部分先切**（默认·推荐）：省略 `--limit` 时落地前 10 集；也可 `--limit N` 明确首批/续切数量。仍按全本候选断点估算总集数，只是不创建未审目录。
- **全篇粗切**（显式）：传 `--all`，一次粗切整本，写全篇 raw 脚手架；只在前 10 集压缩率、边界和节奏策略确认后使用。

```bash
# 默认不传 --target；--target 只作报告/人工复核参考，不参与切点决策
# 首切范围=部分先切（默认）：只落地前 10 集；compact split_plan v3 仍保存全书规划，机器/人工复核文件分离
python3 <skill>/scripts/split_novel.py "<小说路径>"
# 有「第X章」时强烈建议加 --by-chapter，让边界先贴章节（更接近节拍）：
python3 <skill>/scripts/split_novel.py "<小说路径>" --by-chapter
# 章本身≈一个戏剧节拍单元时，用 --per-chapter 每章独立成一集（最贴节拍；长章保持整章，精修时再拆）：
python3 <skill>/scripts/split_novel.py "<小说路径>" --per-chapter
# 从中段开工：先补前情资产包；若用户只给模糊剧情点，先读章节/关键词定位到章号再传参
python3 <skill>/scripts/split_novel.py "<小说路径>" --by-chapter --start-chapter 48 --limit 10
# 续切：重跑同一命令加大 --limit（旧集 + 进度勾选保留）
# ⚠️ 补全必须沿用首跑的切分模式；若人工显式传过 --target，补全时也沿用同一报告参考
python3 <skill>/scripts/split_novel.py "<小说路径>" --by-chapter --limit 30
# 全篇粗切：只在前 10 集策略确认后显式触发
python3 <skill>/scripts/split_novel.py "<小说路径>" --by-chapter --all
# 首切会自动从本剧源文本生成 n2d 本线源书分析包：
# 设定库/source_analysis.json + source_analysis.md，并用角色候选预填 _角色总表.md
python3 <skill>/scripts/split_novel.py "<小说路径>" --by-chapter
```

**② 节拍重切（粗胚之后必做）**：split 出的是候选断点粗胚，**逐集按 `references/拆集法.md` 的 P0→P6 + 自查清单核对边界**——核心是 P0/P1：每集结尾是否落在强断点（危机悬置/真相半露/反转预告）上，且本集是否完成 **冲突→爽点/反转→钩子**。某集若结尾停在半场戏/平淡处，把边界往前或后挪到最近的反转/钩子（**宁可大幅偏离字数参考，也要保剧情连贯、剧情丰满和集尾硬断**）。`--by-chapter` 让边界贴章节，但**章界 ≠ 节拍界**，仍须人工核。

**精修窗口铁律（避免粗拆污染定稿）**：`raw.txt` 只是脚手架，**精修阶段每次看 5-10 集窗口**，先重判边界再写词。不要只打开单集 raw 就动笔；尤其遇到短集提示（短但闭环完整可保留）、章内续切、结尾是逗号/冒号/系统音半句、或开头是承接句时，必须把前后集一起读，决定“保留 / 并入前集 / 并入后集 / 前后挪一段”。可先跑确定性预筛：
```bash
python3 <skill>/scripts/boundary_audit.py <作品根>          # 全剧 raw 边界体检 + 剧级追更骨架
python3 <skill>/scripts/boundary_audit.py <作品根> 2-10     # 精修窗口体检
python3 <skill>/scripts/boundary_audit.py <作品根> --strict # 阶段1入口硬门：有风险且无复核记录则先停
python3 <skill>/scripts/boundary_audit.py <作品根> --json   # 机器可读（series_arc 块）
python3 <skill>/scripts/boundary_review.py draft <作品根> --write # 刷新 boundary_review_draft.json；不覆盖人工 boundary_review.json
python3 <skill>/scripts/boundary_review.py sign <作品根> '<blocker_id>' --decision keep --notes '语义判断' --reviewer '<人工声明 reviewer 标识>' --semantic-evidence '闭环/承接证据'
python3 <skill>/scripts/boundary_review.py sign <作品根> '<blocker_id>' --decision keep --notes '代理语义判断' --reviewer 'delegate:n2d-agent' --semantic-evidence '闭环/承接证据' --delegated  # 仅有效自主授权
python3 <skill>/scripts/boundary_review.py sign <作品根> '<blocker_id>' --decision rewrite --notes '已实施的修改' --reviewer '<人工声明 reviewer 标识>' --source-mapping-file '<source_mapping.json>'
python3 <skill>/scripts/boundary_review.py check <作品根> --json   # 校验 blocker code + 双侧边界合同 + 决策/实施收据
```

若导演批准的是一个会吞并/平移多集的完整 source-unit 窗口，不要手工分别覆盖 raw、plan 和进度。先写 `kind=n2d_approved_split_mapping` v1 JSON（含审批人/角色、窗口、逐集连续 source-unit 范围、`next_source_unit_id`），再运行：

```bash
python3 <skill>/scripts/apply_split_mapping.py <作品根> <approved_mapping.json> --json
```

实施器只接受仍为 raw-only 的窗口；它验证源快照与连续映射，保留覆盖前 tar.gz 和新旧 SHA 收据，重建 raw，刷新 `split_plan.json` / `_拆集机器索引.md` / `_进度.md`，并把从 `next_source_unit_id` 起仍未 materialized 的机器后缀重编号。窗口或后缀已有下游产物时必须拒绝，改走专项返工/迁移计划。实施后再对旧 strict blocker 运行 `boundary_review.py sign ... --decision rewrite --source-mapping-file ...`，把旧合同与当前左右 raw SHA 绑定起来。
`boundary_audit` 在逐集表之外还输出全局 **「剧级追更骨架」**（即使 CLI 只审 2-10 集，剧级曲线也始终使用全剧 rows）与稳定 `blockers[]`。每项 blocker 都有 code、`E0001-E0002` 双侧边界合同、左右 raw SHA 和合同 SHA；上集弱收口与下集弱冷开同权，不能只因上一集有钩就放行。标点与语义词钩独立计分，普通感叹号不会重复计成强钩。付费 blocker 只对项目明确配置的卡点生效；未配置时保持 advisory。

**伏笔兑现账本脚手架（SP1·导出端·2026-06-22；2026-06-24 升格）**：拆集后跑 `python3 skills/n2d/n2d-script/scripts/setup_payoff_ledger.py <作品根> [--episodes 1-10] --write`，从各集 voiceover/故事板按显式悬念/钩子标记**捞候选伏笔**写成 `设定库/setup_payoff_ledger.json` 草稿（不自动判定哪句是伏笔·不覆盖已填 payoff·`payoff_ep` 留空交编剧填）。给每个坑填兑现集或标 `status=ongoing` 后，`n2d-review` 的 SP1 会校验坑没填/兑现早于种下/缺种下集——补「直接给小说文件、不经上游小说创作线时漫剧侧无叙事连续性兜底」。`P0/P1` 管语义/视觉状态跨集，SP1 管「叙事坑」跨集，正交。
> **2026-06-24 升格两点**：① **自动捞候选**——除显式标记外，还按"挖坑句式"（到底是谁/为何/身世/神秘信物/不对劲…）捞无标记的弱信号候选，标 `status=candidate` 交编剧确认或删（治"作者漏标 → 真伏笔永不进账"），只认显式标记的坑才进闸、弱信号不拦流水线。② **stage2 收尾闸**——`n2d/run.py next` 到 `image_prompt` 前自动跑 `setup_payoff_ledger.py <作品根> --gate 第N集`：本集检出显式伏笔但账本缺登记或没填兑现集 → **block 出图**（坑挖了不填不让进贵工位；标 `ongoing` 放行）。

**剧情完整性账本（SI1·文本期·report-first）**：拆集/voiceover 后跑 `python3 skills/n2d/n2d-script/scripts/story_integrity_audit.py <作品根> [第N集] --write`，生成/更新 `设定库/story_integrity_ledger.json`、`设定库/thread_scheduler.json`、`设定库/pilot_arc_contract.json`。自动线程 ID 按开坑集稳定为 `T_E0001`，逐集增量执行也不会从 T001 重启覆盖前集；同集尾重写仍更新原线程。它检查 **选择→后果链**、**角色动机向量**、**A/B/C 线调度**、**前 3-5 集追剧契约**、**假 cliffhanger**、**对白是否推进选择/揭示/施压/关系/动作**。

**剧情/分镜质量启发式套件（2026-06-24·report-only·"先抽结构再判"不内联问 LLM）**——补 SI1「信号在不在 vs 执行好不好」盲区，全 warn/info 透出不阻断（已自动接进出图前置链）：
- **因果链图（A1·`causal_graph.py`）**：按 Causal Plot Graph（R²·arXiv:2503.15655）抽前向因果图，flag **天降/为反转而反转候选**（反转💥或"突然/竟然/原来"惊变却无因果入边、台词也没说因）+ **因果覆盖率过低** + **A6 降智/工业糖精**（冲突/误会靠角色不沟通/无视铁证硬维持）。铁律：先抽因果结构再判，绝不内联问 LLM「合理吗」（防套刻板印象·arXiv:2410.23884）。
- **场必转/价值转（A2·`scene_turn_audit.py`）**：戏剧结构白区（arXiv:2602.15851）的"compute-don't-ask"启发式——**价值极性零翻转**（场不转·一潭死水）/**憋→放结构**（全负到底没放=憋死、全正到底没铺垫=糖精；铺垫憋屈量≈爽点上限）/**转折点堆太早**（LLM 通病·arXiv:2407.13248）。
- **潜台词/去AI味（A5·`subtext_audit.py`）**：ImpScore（arXiv:2411.05172）思路的纯文本代理，flag **自陈情绪**（"我好难过"）/**旁白情绪概括**/**动机过度解释**（因为…所以…）/**身份直给 exposition** + 集级**直白率**。潜台词是人 vs AI 真差距、说教是短剧头号劝退。
- **人物弧光（A3·`character_arc_ledger.py`）**：2026 头部分水岭。scaffold `设定库/character_arc_ledger.json`（人填 want/need/flaw/arc），机检 **want-vs-need 缺位/相等**（无内在矛盾·PsyAgent 2601.06158）/**挣来的转变**（转变前无失败/挣扎=突然顿悟·earned-change）/**核心角色无弧光登记**。
- **景别进程 + 转场（B1/B2·`shot_grammar_audit.py`）**：分镜导演审美机检（阶段2），见阶段2 出图前置。
- **导演运镜审查 + Prompt 落地（`director_camera_plan.py`）**：阶段2 定稿后读取 `storyboard.json`，逐 Clip 审查景别、既有 `camera_motion`、`camera_motivation/运镜动机`、视线关系和 `template_contract.camera_rule`，输出 `生产数据/director_camera_plan_第N集.json/md`。普通镜、对白反打和大表情近景默认固定机位；只有明确运镜动机或连续空间动作才推荐移动，同时把非 POV 的戏内视线与三分之四/侧向/OTS 头眼关系写进 `视线表演` 注入，防人物迎镜头。sidecar 给出图侧 `起幅·运动余量/视线表演` 和视频侧 `导演意图/起幅/落幅/镜头运动/视线表演/运动精修`；若 `video_model_routes.json` 存在，还按路由后端已验证的 `control_idiom` 附 `后端控制写法`。**下游 gate 强制消费（两档收据）**：`n2d-review` 的 `check_director_camera_plan_consumption` 在出图(`image_preflight`)/出视频(`video_preflight/video`)付费前核对落实——**Tier A 逐镜精确**：落了 SHA 绑定 plan+prompt 的结构化签收档 `生产数据/director_camera_plan_applied_第N集.json`（`kind=n2d_director_camera_plan_application`, `accepted=true`, `reviewer`, `plan_sha256`, `scopes[].{scope,prompt_path,prompt_sha256,applied_clip_ids}`）时，按 `applied_clip_ids` 逐镜判，未签收镜里高潮/关键镜(KEY_SCENE_MARKERS)→BLOCK、普通镜→WARN；plan/prompt 改了 SHA 不符→自动回退烟雾档。**Tier B 文档级烟雾**（无签收档）：核对整包是否出现结构化镜头词，含高潮镜且零词汇→BLOCK、普通镜→WARN。
> 全是启发式**初筛**，只 flag 候选交人判、不计算真分、不臆造——深层动机/世界观自洽/台词质感/导演审美仍需人判。**绝不堆噪声淹没硬伤**（容错铁律）。

**叙事状态台账（NS1·知识/位置/关系跨集·2026-06-24）**：视觉 `state_ledger` 只管伤/泪/妆/服，**知识/位置/关系**这条叙事轴此前无人看守——最容易出又最难发现的硬伤（A 第3集还不知道、第5集却表现知道；上集在甲地、本集无转场却到乙地）。跑 `python3 skills/n2d/n2d-script/scripts/narrative_state_audit.py <作品根> --write` 从各集 voiceover 捞候选写 `设定库/narrative_state_ledger.json`（知识条目自动用 `【…】/《…》` 专名预填 `keyword`，`character/known_from_ep` 交编剧填；自由文本不臆断谁知道什么）。填全后 `narrative_state_audit.py <作品根> --check` 或 `n2d-review` 的 NS1 做**确定性跨集校验**：**知识倒流**（声明第K集才知道，但更早集该角色已提及该 keyword）+ **位置瞬移**（同角色相邻有声明的集换地点、两集都无转场词）。诚实边界同 SP1：校验只跑在字段填全的条目上。
`n2d/run.py next` 进入 `script_stage1` 前会自动跑 strict 版。`boundary_review.py draft --write` 每次刷新机器文件 `脚本/boundary_review_draft.json`，只在首次缺失时创建人工文件 `脚本/boundary_review.json`，续切/重审绝不覆盖签收决定。决定不要手改 JSON：用 `boundary_review.py sign`（`record` 为等价别名）按**精确 `blocker_id`** 原子写入。标准模式的 `keep` 必须显式给非空 notes、`semantic_evidence` 和可追责人工 reviewer；自动/agent/bot/system 身份不能冒充人审。只有 `人工批准策略=仅高风险停审` 且 `autonomy_authorization.json` 有效，才可用 `delegate:n2d-agent + --delegated` 代理签 `keep`，记录授权人和授权 SHA。`move/merge/split/rewrite` 永远不可代理：须先真实改完左右 `raw.txt`，再由人工 reviewer 绑定改前合同、当前新 SHA 与 source mapping；左右 SHA 都没变、合同陈旧/未知或 reviewer 声明缺失都会拒写。`accept_risk` 只能确认 advisory，不能解除 strict blocker。

**前长后短的落地**：粗胚默认按章/场景/强钩候选切；**第1集**在精修时主动加权，必要时并入更多开篇内容来立世界观、主角欲望和系列总钩。真正节奏靠**爽点/钩子重切(②) + 配音/原生音画实测(③)**校准；不要为了让第1集或后续集落到某个秒数而拆断完整闭环。脚本自动剥离开头简介/标签/看点等元数据（`--keep-frontmatter` 可保留）。

**约定**：小说应放在 `创作区/制漫剧/<剧名>/小说/<剧名>.docx`。若用户给的是裸文件，`split_novel.py` 会把读取到的正文同步落一份规范副本到 `创作区/制漫剧/<剧名>/小说/<剧名>.txt`，供 `source_check.py --record` 建源指纹；原始 docx/txt 可继续保留。**默认输出到 `创作区/制漫剧/<剧名>/`**（作品根直接铺各阶段子文件夹）。

生成的骨架：

```
创作区/制漫剧/<剧名>/
├── 小说/<剧名>.docx          ← 原文
├── _进度.md                  逐集勾选进度表
├── 设定库/
│   ├── global_style.md       全局画风/世界观（第 2 步精修）
│   ├── characters/           角色卡（第 2 步建卡）
│   └── locations/            场景卡（第 2 步建卡）
└── 脚本/
    └── 第N集/
        └── raw.txt           拆集出来的原文片段
```

向用户报告：输出路径、**首批粗切索引/已粗切几集**、全书 source-unit/候选边界/beam paths 数量、字数范围、`脚本/split_plan.json`、机器 `脚本/_拆集机器索引.md` 与人工 `脚本/_拆集复核.md` 路径；若只做首批/部分先切，提示「先审前 10 集压缩率与边界，满意后用 `--limit N` 续切或 `--all` 补全」。

> ⚠️ **拆分是粗胚脚手架，不是最终集边界**（一章 ≠ 一集）。第 3 步精修时以 `raw.txt` 为素材按戏剧节拍重切：一个节拍可跨多章合并、长章可拆上/下集。集数与 raw 分块不必一一对应。

> **记源指纹基线**（拆完即记，供日后发现源文本更新）：`split_novel.py` 会自动写 `小说/<剧>.txt` 规范副本；拆完跑一次
> `python3 <n2d skill>/source_check.py <作品根> --record`。
> 之后每次进 `n2d` 会自检源是否被改过 → 列出变动章/受影响集/是否触及已生产集（见 n2d「源新鲜度自检」节）。已有 `split_plan.json` 时，源变更要先判断受影响边界，再按最小范围返工。

### 第 2 步 — 先定全局（只做一次）

1. 通读小说（或抽样若干集）确定 `global_style.md`：
   - 顶部记 **视频模型路由策略** + **生视频后端延后决策说明** + **目标图AI**
   - 按 `基础视觉风格` 写「基础视觉风格」与「基础视觉风格契约（style_contract 源头）」；风格选项/派生词见 `n2d/references/visual_styles.md`。用户要求结合当前影视/平台样本时，先完成 `设定库/视觉竞品研究.md`，把基底风格与只在特定叙事域启用的副风格写清，禁止随机跨镜混搭
   - 画风词、世界观、统一负面词（负面词随基础视觉风格派生；不要把“插画感/游戏CG”等只适用于写实风格的禁忌套到所有风格）
   - ⚙️仙侠玄幻可选：在 `global_style.md` 补**境界体系 / 主要势力 / 关键术语表**结构化小节（境界多、势力杂的题材，避免跨集漂）；主角/核心反派长期使用的武器、法宝实体到 `n2d-image` 立 `WEAPON_xx` 武器库条目并写 `weapon_profile`，剑气/灵力/护体光等表现另立 `VFX_xx`；共享 prompt 放 `法宝定妆.md` / `特效定妆.md` 专类（见 `n2d-image/references/prompt_format.md §1`）
2. **跨项目资产库提醒（不要让用户背 CLI）**：为主要角色/场景建卡前，AI 先提示一句：“我会先查 `创作区/制漫剧/_资产库/` 有没有可复用的角色原型、场景定妆或路由模板；命中再问你是否导入，没命中再新建。”然后后台跑 `python3 skills/n2d/n2d-asset-market/scripts/market.py list`。若用户说“导入某模板为某角色”，用 `n2d-asset-market import-character` 导入并 fork 新身份，再跑 `python3 skills/n2d/n2d-identity/scripts/identity.py <作品根> --write`。用户只需做选择，不需要记命令。
3. 为**主要角色/场景**建卡，存入 `设定库/characters/`、`设定库/locations/`。格式见 `references/formats.md §1 §2`：
   - 角色卡必含**妆造拆解**（发型/妆容/服装/配饰/色卡）、**服装选择评分卡**、`wardrobe_profile` 源头、**预计/计划出场集数**（能判断时写整数，未知写待确认）+ **① 分档定妆 prompt 源头**：所有具名角色先写正面主参考 + 半身/全身服装锚 + 脸锚；`core_full`（主角/核心长线/预计或结构化 storyboard 可见出场≥10集）必须写齐**正面 / 前3/4 / 侧面 / 后3/4 / 背面五角独立参考 + turnaround 人审拼版 + 同源脸部特写/表情锚**，复现配角补前3/4，具名短线的侧背按真实分镜补；干净背景、中英双版 + **② 出镜 prompt**。这个集数与叙事 scope 供 `n2d-image` 决定 `core_full / recurring_standard / named_minimal / restricted_partial`，不等于主体 ID/LoRA 档位。
   - **年龄敏感长线角色**（少年长大、十年后、成年/中年/长生态、境界跨度明显）必须在角色卡写「形象里程碑」和定妆命名：`<年龄或年龄档><形态>`，后续目标文件用 `定妆_<角色>_<年龄或年龄档>_<形态>*.png`。已存在的无年龄旧文件只能作为 legacy alias；新增/重出不得继续无年龄命名。
   - 若用户给外部人物参考图，角色卡必须写明**参考图只借脸型/五官/眼神/体态/身材气质**；发型、发饰、服装、配饰、妆容、身份阶层和剧情状态仍按小说原文、角色圣经、当前形态变体与本集剧情决定，不继承参考图衣装。若用户明确说这是“定型参考图”，则它同时是跨年龄/跨形态身份基准：少年态、成年态、觉醒态、高阶态都必须从同一脸部 DNA 派生，角色卡的「形象里程碑」要写清 `form + age_band + reference_lineage`，后续定妆文件名带年龄或形态，不允许无账换脸。
   - 若参考图还用于制作风格识别，`global_style.md` 必须把识别出的风格归一成具体 `基础视觉风格` 或 `自定义（...）` 六字段契约，并写明**禁止继承截图 UI/播放按钮/字幕/搜索框/水印/平台标签**；这些只作风格和人物参考，不进入成片画面。
   - **本 skill 只生成 prompt 文本**——实际出定妆照在 Stage 4 (`n2d-image`) 做
4. 新角色/场景在其首次出现的那一集补建卡；补建前同样先查跨项目资产库。
5. **角色形象生命周期时间线（跨集·全局产物·Gap2）**：主要角色建卡后跑 `python3 skills/n2d/n2d-script/scripts/lifecycle_scan.py <作品根> --write` —— 确定性预扫 raw 的"时间/年龄、换装/造型、形态/状态"里程碑信号，写/刷新 `设定库/characters/_生命周期.md`（自动段每次重生成，确认区保留）。标准模式由人确认/合并候选；“仅高风险停审”模式由代理只确认源文有明确证据的可逆候选，含糊年龄跳、身份变化或会触发额外付费定妆的条目仍停审。确认结果再写回角色卡『形象里程碑』。涉及年龄跳/成长阶段的行，定妆动作必须写清 `form`、年龄/年龄档、目标文件前缀和上一阶段派生来源（如 `18岁少年态 → 定妆_某角色_18岁少年*.png ← 14岁常态脸锚`）。这是 n2d 此前缺的**跨集造型排程**层；里程碑集到达前由 `n2d-image` 提前派生『形态变体』定妆，也作 `n2d-identity` 跨集漂移的预期变化基线。格式见 `references/formats.md §1.1`。

### 第 3 步 — 阶段1·剧本改编（台词先行，**不做分镜**）

> 流程铁律（默认 **混合自动路由**）：`剧本改编 → 声音选角 + 无 WAV 时间基准 → 分镜/OTIO → 逐镜音画生成 → 音色定妆后 final voice → 必要口型 pass → compose`。对白表演镜、旁白/口外音、动作/空镜/蒙太奇和 native AV 镜各走适合自己的路径；阶段1后 `production_mode_router.py` 写逐镜执行合同，不把项目强制成一种先后顺序。

先按戏剧节拍确定本集边界（合并/拆分 `raw.txt`，一章 ≠ 一集）——边界决策按 `references/拆集法.md` P0→P6，过一遍其自查清单再写词。**实际取材优先级**：`脚本/boundary_review.json` 中 blocker code、双侧 SHA 和 applied receipt 都通过的窗口决策 > 当前集 `raw.txt` + 前后 2-4 集 raw 的人工重切 > 单集 raw。若签收标了“第9+10合并为一个精修单元”，写第9集 voiceover 时应同时消费第9/10集 raw；第10集则暂不单独推进，等窗口定稿后再回写进度。

**写词前先做改编取舍（新增前置层）**：在边界确认后、`voiceover.txt` 之前，逐段/逐节拍建立 `脚本/第N集/adaptation_triage.json`（批量或窗口层可先写 `脚本/adaptation_triage.json`，再按集落地）。JSON 根字段必须用 `items` 数组承载逐条取舍；不要改成 `beats`、`entries` 等别名，否则 `source_adaptation_audit` 读不到有账改写证据。每条记录写 `source_span`、`beat_function`（动机/冲突/选择/后果/伏笔/关系/状态/世界观/过渡）、`decision`（`dramatize` / `narrate` / `defer` / `merge` / `omit`）、`change_type`（`preserve` / `compress` / `reorder` / `rewrite_detail` / `intensify` / `add_hook` / `combine_minor_role` 等）、`reason`、`delivery`（若 narrate/defer/merge/改写，写由哪句旁白、哪场后文或哪个相邻节拍承接）、`adaptation_delta`（changed_from/changed_to/preserved_function/short_drama_reason/payoff_guard）、`risk_if_removed`。规则：弱信息不硬拆成 clip；能后文自然带出的设定，不在当前集停下来解释；重复心理/环境描写优先压成一句旁白或并入动作；关键细节可以为短剧爽感与节奏稍作改动，但必须保住因果、动机、伏笔、状态变化和角色弧，并写清改写账。取舍完成后再写留存曲线和 voiceover，否则会把“不重要但占字数”的原文误当成镜头，导致节奏散、clip 多、接缝多。

**写词前先设计留存曲线**（导演动作，不可跳过 —— 必读 `n2d/references/导演节奏.md`）：
- **开场（0-3s）**：定一个冷开场或倒叙钩——本集最炸的画面/台词放最前，禁止 logo/慢空镜/长旁白起。
- **前 15 秒**：立住核心悬念/欲望 + 第一个矛盾。
- **中段**：每 15-20 秒安排一个钩子/信息增量（悬念/欲望/反差/信息/危机五选），张力阶梯上抬，≥1 次反转，爽点留"憋—放"距离。
- **集尾**：选一种 cliffhanger（危机悬置/真相半露/反转预告）硬断，**别把这段戏讲完**。
- 把这条曲线先列成"节拍点表"（开场钩 / 钩子1 / 钩子2 / 爽点 / 集尾钩 各在哪），再据此写词。

产出：

0. `adaptation_triage.json`（或窗口层 `脚本/adaptation_triage.json` + 本集摘录）— 改编取舍/短剧化改写表。根字段固定为 `items` 数组；每个源文节拍必须有 `decision` 和 `delivery`，证明不成戏的内容已经被旁白、后文、相邻节拍、删除理由或短剧化改写接住。`omit` 只能用于重复/非剧情必要内容；`defer` 必须写后续由哪场戏、哪句台词、哪个道具/行为带出；`narrate` 必须能压成短旁白/独白，不得把弱信息硬拆成一个视觉空转 clip；改关键细节/剧情时必须写 `change_type` + `adaptation_delta`，作为 `source_adaptation_audit` 的有账改编证据。
1. `voiceover.txt` — 逐台词脚本，**升级格式**：`[镜头N·角色·情绪·(语速)] 台词  (钩子标记)`。**这定义镜头划分骨架**（几镜、每镜说什么），是 n2d-voice 的输入。
   - `情绪` 用具体词（茫然/愤怒/惊恐/冷冽/悲伤/窃喜/坚定/阴狠…），**会驱动配音念白**，不是注释。
   - `语速` 可选（快/慢，缺省常速）：吵架逼问危机用快，独白悲伤盘算用慢。
   - 关键反转词前用 `||` 标一拍停顿；句尾按留存曲线标 `⚡钩子` / `💥爽点` / `🪝集尾`。
   - 详见 `references/formats.md §6`。
2. `bgm.txt` — 整体情绪 + BGM 风格 + 关键音效点（标爽点/反转的"重音"音效点，供后期卡点）
   - **音乐母题登记（LM1·跨集一致）**：像 `voice_key` 一角一色那样，给主要角色/情绪主题登记**主题动机**到 `设定库/leitmotif_registry.json`（`{motifs:[{id, subject, desc}]}`，schema 见 `n2d-review/references/扩展一致性登记表.md`），让"主角出场旋律""反派低频动机"跨集可复现不串用；n2d-review 的 `音乐母题(LM1)` 据此对账。
3. `封面.md` — 高点击率封面/首图 prompt
（角色/场景卡见第 2 步。**本步不写 分镜剧本 / 故事板 / 素材清单 / 字幕** —— 它们的镜头切分与时长要由真实配音决定，属配音后的"阶段2 分镜设计"。）

完成后在 `_进度.md` 勾选阶段1列：`剧本改编` / `bgm` / `封面` ✅。默认下一步先运行 `python3 skills/n2d/n2d-voice/voice_preflight.py prepare <作品根> 第N集`（无 WAV），再运行 `python3 skills/n2d/scripts/production_mode_router.py <作品根> 第N集 --write` 并回跑阶段2。音色未签收前不批量 final 配音，也不要直接出图。同时记录生产数据：

```bash
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py record <作品根> \
  --episode 第N集 --stage script --event generation \
  --asset 脚本/第N集/voiceover.txt --status pass \
  --duration-sec <本阶段耗时秒> --provider <LLM或agent> \
  --meta phase=script_adaptation
```

> **本 skill 不写出图 prompt**（即 `出图/共享/图片/` 与 `出图/第N集/图片/` 下的所有 prompt + PNG）。物料齐后用户调 `n2d-image`，那个 skill 才负责出图 prompt 两层架构。

**批量提示**：用户要“一次多集”时，默认按 `脚本批次=小批`（5 集）记录边界决策和物料清单并自动继续；显式逐项询问时才停下来选逐集/小批/整批。逐集复用同一批角色卡/场景卡，保证跨集一致，不重新发明角色外貌。若 `人工批准策略=仅高风险停审` 且授权有效，低风险签收也可由代理按当前哈希完成；移动/合并/拆分/重写 raw 仍必须人工批准。

### 第 4 步 — 报告 + 推进（收尾必做：详列下一步）

每集物料齐后，**回写进度 → 跑 `python3 skills/n2d/progress.py <作品根>`（或 `run.py next <作品根>`，按 `制作模式` 给出正确前沿）→ 把它的「下一步」念给用户**（调哪个 skill · 干什么 · 确切命令 · 可并行项）。下一步随 `制作模式` 不同：

```
第K集 阶段1(剧本改编) 齐：
- voiceover(台词) / bgm / 封面 ✅；角色/场景卡复用
- _进度.md 已勾选阶段1 列
下一步建议（以 progress.py 前沿为准）：
- 配音先行（默认）：先 n2d-voice <作品根> 第K集 配音 + 统计每句台词时长，配音齐后回跑 n2d-script 阶段2 分镜设计
- 原生音画：直接回跑 n2d-script <作品根> 第K集 做阶段2 分镜设计（说话镜不跑配音，按脚本时长驱动）
- 先出视频后配音：n2d-voice 出占位时长清单当脚手架 → 回跑阶段2（FINALIZE_ALLOW_PLACEHOLDER=1）
- 可并行：n2d-script <作品根> 第K+1集 精修下一集物料（低成本前期，不阻塞本集）
```

## 阶段1.2 — Table read 围读验收包（导演排戏前先听戏）

Stage 1 交出 voiceover 后，不要直接进入导演排戏。先做低成本围读验收：检查台词是否像角色本人会说、信息密度是否能被口播消化、情绪转折是否有可演依据、时长风险是否会把后续镜头推爆。`n2d/run.py next|enter` 在 `script_stage2` 前会自动跑：

```bash
python3 skills/n2d/n2d-script/scripts/story_acceptance_packets.py <作品根> 第N集 check --kind table_read --json --write-missing
```

缺文件时会在 `脚本/第N集/` 生成 `table_read_packet.json/.md` 与 `table_read_signoff.json`。补完内容、把包置为 `confirmed` 后，标准模式由 director/head_writer 运行 `signoff.py` 签当前输入与证据哈希；“仅高风险停审”模式由 `run.py` 调 `autonomy.py approve` 自动写 delegated signoff。每条 blocker/warn 仍须有处理结论或结构化风险签收；内容或签收任一未通过时不会进入 P-2。

## 阶段1.5 — P-2 导演排戏包（分镜前先排戏）

围读确认后，不要直接把台词逐句翻译成 storyboard。先做导演排戏：把本集拆成戏剧 beat，确定人物怎么站、怎么走、看向哪里，镜头如何由远到近、如何接、什么时候动、为什么动。`n2d/run.py next|enter` 在 `script_stage2` 前会自动跑：

```bash
python3 skills/n2d/n2d-script/scripts/director_blocking_pack.py <作品根> 第N集 check --json --write-missing
```

缺文件时会在 `脚本/第N集/` 生成六份草稿，并在 `生产数据/director_blocking_pack_第N集.md` 汇总：

- `director_beat_sheet.json`：每个 beat 的戏剧功能、观众问题、情绪变化、导演意图、必须补的反应镜。
- `axis_blocking_map.json`：场景轴线、视线、前中后景站位、入出场、权力关系和跳轴例外。
- `shot_progression_plan.json`：建立镜头、景别阶梯、峰值 CU/ECU、运镜类型和运镜动机。
- `transition_map.json`：每个接缝的出点/入点、match/eyeline/action/J/L/空镜/硬切、尾帧和声音桥。
- `vertical_composition_plan.json`：9:16 安全区、脸部可读性、Z 轴纵深、overlay/字幕区和竖向运动。
- `edit_rhythm_map.json`：前 3 秒钩子、前 6 秒命题、中段钩子密度、爽点/留白、集尾 cliffhanger 和声音/BGM cue。

**签收口径**：六件套默认 `draft`，补齐后置为 `confirmed` 只表示可审。标准模式下，`director_blocking_signoff.json` 仍由 director 与 producer/editor 两个角色组分别批准；“仅高风险停审”模式下，代理只能在六件套 confirmed、授权有效且哈希当前时写 `delegated_autonomy` 签收，明确记录负责人豁免独立人审，不能把自动产物伪装成导演亲审。

对话/对峙段在 P-2 confirmed 后再跑一遍正反打合同审计：

```bash
python3 skills/n2d/n2d-script/scripts/shot_reverse_contract.py <作品根> 第N集 --write --json
```

它会写 `脚本/第N集/shot_reverse_contract.json`、`生产数据/shot_reverse_contract_第N集.md` 和 `生产数据/shot_reverse_contract_check_第N集.json`，并审计 A/B 站位互补、互补视线、非 POV 看镜头、OTS 前景肩部、越轴缓冲、近景锚定图待补等问题。9:16 对峙可签 `vertical_depth_9x16`（前景/后景、上/下、高/低位），但仍要明确 A/B 和视线方向。

## 阶段2.4 — Animatic 粗剪验收包（出图 prompt 前先看节奏）

Stage 2 交出 `storyboard.json` 和 `镜头时长.json` 后，先做一次低成本但可执行的 animatic 验收：`story_acceptance_packets.py` 会物化 `animatic_第N集.json/.html`，并在 `生产数据/timelines/第N集/` 写可持续编辑的 `editorial_timeline.otio` 与签收专用的不可变 `animatic_timeline.otio` 快照，再跑 `story_economy_audit.py --strict --write`。没有图时用 timed slate；后续 accepted 视频只刷新 working OTIO，不篡改已签 animatic 快照。

```bash
python3 skills/n2d/n2d-script/scripts/story_acceptance_packets.py <作品根> 第N集 check --kind animatic --json --write-missing
```

缺文件时会生成 `animatic_packet.json/.md` 与 `animatic_signoff.json`。内容 confirmed 后，标准模式由 director 与 editor/producer 两个角色组分别运行 `signoff.py`；“仅高风险停审”模式由代理绑定 packet、OTIO/timed preview 与当前输入哈希签收。风险接受仍须显式记录 `approved_with_risk`、risk 与 waiver reason，不能被普通代理默认吞掉。内容、预览、剧情经济性或签收任一未通过，都不会进入出图 prompt。

## 阶段2.5 — P-3 制片拆解包（出图 prompt 前先交接）

Animatic 确认后，不要直接让 n2d-image 临场理解“要拍什么”。先做制片拆解：逐镜列角色、场景、道具、服装、妆发、VFX/overlay、声音、后端风险；再做连续性拆解、镜头间 continuity_chain、场记连续性 bible、AI 拍摄排期、AI 拍摄通告单和 batch 队列种子。`n2d/run.py next|enter` 在 `image_prompt` 前会自动跑：

```bash
python3 skills/n2d/n2d-script/scripts/production_breakdown.py <作品根> 第N集 check --json --write-missing
```

必填文件：

- `脚本/第N集/production_breakdown.json`
- `脚本/第N集/continuity_breakdown.json`
- `脚本/第N集/continuity_chain.json`
- `脚本/第N集/continuity_bible.json`
- `脚本/第N集/ai_shooting_schedule.json`
- `脚本/第N集/ai_call_sheet.md`
- `生产数据/ai_shooting_schedule_batch_seed_第N集.json`
- `生产数据/ai_shooting_schedule_batch_seed_第N集.md`

**签收口径**：六件套默认 `draft`。内容 confirmed 后，标准模式由 producer/assistant_director/script_supervisor 之一签 `production_handoff_signoff.json`；“仅高风险停审”模式由代理按项目授权签收，但不授予付费出图/出视频权限。`continuity_chain.json` 是接缝机器真值：每个 Clip→下一 Clip 必须显式写 `seam_mode` 与该类型的 `seam_evidence`；只有 `continuous_take_relay` 要求上一镜尾帧 SHA 与下一镜首帧相同，其他切法按动作相位、视线目标、反应对象、插入物、声桥、叠化或有意不连续理由验收。旧数据可用 `seam_migrate.py <作品根> 第N集 --write` 生成待审候选，但会重置 P-2 签收，不能把推断当导演亲审。P-3 不新增进度列，内容或签收未通过均不会进入出图 prompt。

导入队列时用：

```bash
python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --from-shooting-schedule <作品根>/生产数据/ai_shooting_schedule_batch_seed_第N集.json
```

## 阶段2 — 分镜设计（时间基准就绪后回跑，**逐镜声音路由驱动**）

**触发**：`混合自动路由` 下先跑 `python3 skills/n2d/n2d-voice/voice_preflight.py prepare <作品根> 第N集`，得到 `voice_casting.json + timing_estimate.json`，回写 `配音=⏳rough`；这里的 rough 表示“设计态时间基准”，不表示生成过占位音频。`finalize_storyboard.py` 可直接消费它并写 `镜头时长.meta.json(provisional=true)`。`配音先行` 固定模式仍要求 `配音=✅` 与真实 `时长清单.json`；`原生音画` 按 storyboard 计划时长；旧 `先出视频后配音` 可兼容估时。**进入本阶段前必须先过 table read 围读包 + P-2 导演排戏包**；storyboard 还必须消费 `production_mode_route_第N集.json#clip_routes`，给每镜保留 timing basis、声音策略和最终声音阶段。

> **不要再为估时生产 WAV**：混合默认的 `timing_estimate.json` 本身就是合法时间脚手架，不需要 `FINALIZE_ALLOW_PLACEHOLDER=1`，也不生成 `时长清单.json`。该环境变量只保留给旧项目已有的占位音频清单；新项目若走到 `say`/静音占位，说明路由错了，应回声音前期而不是继续制造废料。

**先做 Clip 时长分配，再按时间基准置信度设计分镜**：最终表演轨可锁精确停顿；`text_estimate_no_audio` 只锁大致槽位，应给旁白/口外音留可裁余量；`base_video_then_post_lipsync` 的可见口型镜只设计中性基础表演，最终嘴型与细表情留给后期驱动。先在 `storyboard.json` 顶层写 `pacing_allocation`，再给每个 Clip 写 `pacing_role` + `runtime_priority`，并继承 `audio_strategy/timing_basis/final_voice_stage`。低优先级 Clip 只给完成信息传递的最短画面；高光 Clip 给足起手、命中、反应和留白。

> **多人同框分镜调度铁律（P0·剧情优先·把同框做对而非避开·设计宪法 C6）**：多角色同框是下游出图脸漂/串脸最高发点——**但这是"要用对方法做"，不是"该回避"**。**镜头该不该多人同框由剧情决定，不为迁就后端把人物删到舒适区**；后端在变强、会越来越强，按当下短板砍戏会过期。分镜阶段要做的是**把同框戏拍全 + 给下游一条把它做对的执行路径**：① 双人/多人**特写(CU/ECU)优先拆成「单人 CU + 反打」**（`shots[].lens` 写单人景别，配 `template=dialogue_shot_reverse`）——这是**更专业的对话/对峙调度**（正反打把每个人都拍清楚），不是为躲后端；② 需要同框成像时优先**establish 全景/中景 + 景别分层**（清晰主角领镜、其余过肩/前后景/反打承接），让观众看清每个人；③ **任一清晰同框 ≥2 具名脸都必须登记执行路径**：在 `storyboard.json` / `template_contract` 写 `character_ids`，并给下游落 `多人同框身份槽位`（LEFT/RIGHT/FOREGROUND/BACKGROUND 等逐主体绑定 `CHAR_xx/形态`、视线、脸部参考、primary 星标）+ `多人同框执行策略`（`native_subject_slots` / `regional_construct_required` / `split_composite_required` / `单人分层出图` 等）。2-3 张清晰脸只是相对省钱的构图区，**不是免登记区**；≥4 清晰脸、多人近景、强交互/遮挡镜优先拆反打、景别分层或分别出图+合成。gate 对 ≥2 具名同框缺槽位/策略即 BLOCK，登记了才进入下游制作；④ 确属远景群像在 clip 描述里显式标 `远景/群像`，远景背景人不按清晰具名脸处理。这条不削弱戏剧性，也不删戏——正反打/景别分层/分区合成都是把同框戏做扎实的手段。


1. **确定字幕语言**（`字幕语言` 选择点，不写死）：按 `../skills/n2d/references/选择点与偏好.md` 读 `<作品根>/_设置.md`→全局默认；仍缺时自动采用 **中文-only** 并继续，不另起问答。**翻译是投放选择**，项目显式选 **中英双语/仅英文**（海外投放 TikTok/ReelShort/YouTube/北美短剧）时才产 `字幕_英文.srt`——此时**先按 `references/formats.md §9` 把英文翻译写进 `脚本/第N集/字幕_英文.srt`**（任意时间码即可，finalize 会重定时），再跑桥接脚本。
   - **海外/英文字幕发布闸**：项目选中英双语/仅英文、发行地区含海外，或合规用途写正式投放时，必须维护 `设定库/translation_glossary.json`：覆盖人名、称谓、境界、招式、口头禅、系统提示语。无该表或类别缺覆盖时，compose/review gate 会 BLOCK；确无某类术语要在 glossary `coverage` 中显式标 `not_applicable`。
   先跑桥接脚本，得到真实时间轴字幕 + 每镜时长：
   ```bash
   python3 <skill>/finalize_storyboard.py <作品根> 第N集            # 默认按已存在的字幕轨重定时(中文必出，英文若有则重定时)
   SUB_LANG=zh   python3 <skill>/finalize_storyboard.py <作品根> 第N集   # 强制只产中文(忽略残留英文)
   SUB_LANG=zh,en python3 <skill>/finalize_storyboard.py <作品根> 第N集  # 强制产中英(海外投放)
   ```
   产出 `脚本/第N集/字幕_中文.srt` + 可选英文轨 + `镜头时长.json` + `镜头时长.meta.json`。meta 明确 `final_voice` 或 `text_estimate_no_audio`；后者为 provisional，只能作为剪辑/画面时间基准，不能充当最终音画同步证据。
   > **占位闸门**：若该集配音仍是占位音色（`时长清单.json` 有 `占位:true`），本脚本**默认拒绝定稿**（exit 2）——占位时长是估算值，定稿后会锁进镜头时长/故事板 Clip 时长，出视频按错时长生成会大返工。先 `n2d-voice` 换真实配音重跑，再回跑本步；仅 rough preview 可 `FINALIZE_ALLOW_PLACEHOLDER=1` 放行（产物不可用于正式出视频）。
   > **定稿后自检（收尾必跑·闸门）**：`python3 <skill>/validate_timings.py <作品根> 第N集`。真实配音核对 WAV/清单/字幕/镜头；混合估时核对 voiceover 指纹、估时行、字幕和镜头累计，并明确打印“仍需最终声音签收”；原生音画核对 storyboard 计划时长。exit 0 只表示当前时间链自洽，不会把 provisional 估时升级成最终配音。
   > **逐镜创作意图黑板（单一意图源·StageC·2026-06-26）**：定稿后跑 `python3 <skill>/scripts/shot_intent.py <作品根> 第N集` 写 `脚本/第N集/shot_intent.json`——把逐镜意图（expression_span/need_endframe/motion_intensity/景别/action_beat/identity_requirement）+ `allowed_evolution`（允许的演进白名单）收敛成**下游只读派生**的权威对象，治"意图散在 storyboard/state_continuity/asset_registry/_设置/series_bible 五处、冲突只能事后两两对消"的掣肘根因。最高价值用法：在 `allowed_evolution` 里**显式声明**某角色某镜的脸/发/服装/道具就该变（把条目 `field` 标成 `costume/face/hair/prop`、填 `from_shot/to_shot`、置 `source="author"`）——补回关键词检测漏掉的有意改动（如"无痕易容"），`n2d-review` 的 face/hair/costume 锁会经 `state_continuity` 自动把该镜 block 降 warn，不再误伤剧情。重建保留作者已声明条目。核心逻辑在 `n2d/_lib/n2d_intent.py`（跨 skill 单一真值源）。
   > **投放回灌先验注入（finalize 自动·向后兼容）**：定稿时若存在 `生产数据/creative_priors.json`（`n2d-feedback --write-priors` 写的机器可读第一方先验，kind `n2d_creative_priors`），`finalize_storyboard.py` 自动读它，把 A/B 胜出的开场/集尾断点/封面/标题 winner 作为**建议先验**——落 `脚本/第N集/applied_creative_priors.json` 证据 + per-field `decisions.status=applied` + 打印逐维度提示（winner / paired-lift / n）。**缺该文件则 no-op**（向后兼容，不影响定稿）；先验是建议非硬约束，但一旦存在，`beat_audit --strict` 要求本集对每条先验写明 `applied` 或 `rejected + rejected_reason`，不能静默吞掉第一方投放信号。设计本集/下一批开场与集尾断点时优先参考这些已被投放数据验证的胜出变体。
   > **真验证采纳·非橡皮图章（F2·2026-06-26）**：finalize 不再无条件盖 `applied`——它按 `storyboard.json` 的 **`creative_variants_used`** 字段（`{字段:{variant:本集采用的变体, reason?:不采用胜出时的理由}}`，字段如 `opening_variant`/`cliffhanger_cut_variant`/`cover_variant`/`title_variant`）真验证：采用胜出变体→`applied`；采用他变体且写理由→`rejected`(可解释)；采用他变体无理由 / 未声明→`pending`（beat_audit --strict 会拦）。**所以存在先验时，阶段2 设计 storyboard 必须显式声明 `creative_variants_used`**（用了哪个变体；不采胜出就写理由），否则本集卡在 `pending`。这把「投放胜出信号」从「跑一下就算确认」收紧成「分析师对每条信号真决策」。
   > **源文覆盖 + 集内留存节拍 + 剧情完整性体检（出图前置·Gap4/5/SI1）**：`n2d/run.py next` 到 `image_prompt` 前会自动跑 `python3 <skill>/scripts/source_adaptation_audit.py <作品根> 第N集 --strict --json`、`python3 <skill>/scripts/beat_audit.py <作品根> 第N集 --strict --json` 与 `python3 <skill>/scripts/story_integrity_audit.py <作品根> 第N集 --write --json`。`source_adaptation_audit` 核对 `raw.txt` 的系统/专名/关键事件没有从 voiceover/storyboard 中完全消失，并追加检查源文承担的 **动机/冲突原因/选择/后果/反转/关系变化/系统规则** 等场景功能没有被压缩删掉；若关键细节/剧情为短剧节奏做了改写、重排或强化，必须在 `adaptation_triage.json` 写 `change_type/adaptation_delta`，审计会把这类有账改写降为 info，而不是误判成漏剧情。**反向防瞎编（2026-07-23·report-first）**：前向审计只查 source→adaptation（漏没漏），`run.py` 另在 image_prompt 前跑 `source_adaptation_audit.py … --check-fabrication` 查 adaptation→source（有没有瞎编）——扫 voiceover 里出现、源文没有、也无 `adaptation_delta` 有账引入的专名/称谓/设定（【】《》括注 + 王爷/长老/宗主等称谓），标 `fabricated_entity_candidate`（warn·report-only，不阻断）；被 `adaptation_triage`（combine_minor_role/rewrite 等）或 `story_spine` 登记的记 info。治"改了之后瞎编/自造设定"；裸人名不查（无模型易误伤）。`beat_audit` 读 voiceover 钩子标记 + `镜头时长.json` 真实秒，机检 **开场冷启 / 钩子间隔（>20s 报）/ ≥1 反转 / 集尾 cliffhanger / 镜头时长曲线**，并判 **情绪回报 vs 信息回报**（爽点若全是情绪宣泄、零信息增量则报）；`story_integrity_audit` 写剧情账本/线程/前几集契约，报告 **选择→后果、动机向量、A/B/C 线到期、假 cliffhanger、对白推进功能**。**钩子检测不再只认 ⚡💥🪝 标记**：作者漏标时按台词内容推断钩子（危机/反转/真相/悬念词），消除 hook_gap/集尾钩误报（集尾有 cliffhanger 内容却漏标 → `ending_hook_unmarked` 提示补标记，而非误判没钩）。还机检 **情绪节奏弧**（从 `[情绪]` 标注建设计态情绪曲线：≥6 拍情绪只有 1–2 档或七成平缓/缺峰值 → `flat_emotion_arc`，治"全程温吞"；与 n2d-voice 声学能量曲线互补、定稿前可跑）。**还机检 集间因果钩子闭合（`cross_ep_hook_break`·2026-06-24）**：上一集以 cliffhanger 收尾、抛出某人/物，本集冷开场却一个都没接住（首/尾各 3 拍的具名实体零重合）→ 钩子接力断线、观众看不懂前因，strict 下 block（证据不足或确有重合一律放过，宁漏报不误拦）。源文覆盖/节拍的 must/warn 先回 n2d-script 修，不把文字问题带进出图 prompt；`story_integrity_audit` 默认 warn/info 作为报告透出，只有 block/must 才阻断，`--strict` 可人工升格。跨集套路同质化 + **P2 跨集冷开场链**（含集间实体重合校验）可手动跑 `beat_audit.py <作品根> --series`（其末尾还有 **G-S1 中段×高熵一致性审计优先表** `narrative_risk_profile` + **看点高潮位复核** `highlight_climax_profile`：用真实 `镜头时长.json` 量每集最强看点落在时间轴哪个百分位，flag 集内"虎头蛇尾"`highlight_too_early`（看点堆前段、高潮后长尾无钩）与"平庸无看点集"`no_highlight_beat`（北极星：每集须一个核心看点）；无真实时长的集静默跳过，到 storyboard 定稿才激活，与 `boundary_audit` 拆集层的词面奇观初筛分层互补·report-only）。**剧情/分镜质量启发式三件套（2026-06-24·report-only·warn 透出不阻断）**也在此前置链自动跑：`causal_graph.py`（A1 天降/为反转而反转候选 + 因果覆盖率）、`subtext_audit.py`（A5 直白情绪/动机/exposition + 直白率）、`shot_grammar_audit.py`（B1 撞景别/缺定场/爆点没怼近/无景别反差/30°法则代理）——它们只 flag 候选交人判，深层剧情/导演审美仍靠人。
   > **导演运镜 sidecar（出图/出视频 prompt 前置）**：storyboard 定稿后跑 `python3 skills/n2d/n2d-script/scripts/director_camera_plan.py <作品根> 第N集 --write`，把每 Clip 的节奏、景别、既有运镜转成 `image_prompt_injection` 与 `video_prompt_injection`。命中 `camera_move_missing` / `camera_move_unstructured` / `camera_speed_missing` 时，先人工修 storyboard 的 `camera_motion` / `template_contract.camera_rule`，或在下游 prompt 明确落实结构化运镜词和速度档。
   > **剧本质量交接合同（出图/出视频 prompt 前置·硬闸）**：storyboard 定稿后跑 `python3 skills/n2d/n2d-script/scripts/script_quality_gate.py <作品根> 第N集 --strict --write`，输出 `生产数据/script_quality_contract_第N集.json/md`。它把“好看”拆成可签收字段：本集核心看点、0-3s 视觉钩、留存承诺账本、逐 Clip 戏剧功能、关键镜观众效果、开放观众问题、表演 cues、奇观服务剧情说明。`n2d-image` 生成 prompt 时会把这些字段写入 `00_总览.md` 和逐镜 prompt，并写 `生产数据/script_contract_applied_第N集.json` 的 `出图` scope；`n2d-video` 生成/人工整理 `01_clips.md` 后必须跑 `python3 skills/n2d/n2d-video/scripts/script_contract_receipt.py <作品根> 第N集 --scope 出视频` 写 `出视频` scope。后续 gate 会按合同 SHA + prompt SHA 检查消费收据，缺失或过期即回本阶段/对应 prompt 阶段重做。
   > **前因依赖检查（出图前置·删集/跳章·2026-06-24）**：`image_prompt` 前还自动跑 `python3 <skill>/scripts/antecedent_audit.py <作品根> 第N集 --strict --json`。`source_adaptation_audit` 只逐集查"本集源覆盖"、从不回看"被引用的前情交代集是否还在"；本检查补这条跨集轴——按**集号内缝隙**（留存集号 min~max 间缺号 = 中间集被删/跳过，窗口起点不算）判定本集是否坐落在被删集之后，并列出本集首现、断档前从未交代过的实体（引入疑在被删集）。命中 → 恢复被删集或在本集补一句前情，strict 下 block。全剧前因依赖图：`antecedent_audit.py <作品根> --series`。
   > **剧级质量/资源均衡视图（对冲虎头蛇尾·2026-06-24·report-only）**：逐集 gate 只看单集，看不见全剧曲线；2026 漫剧头号死因「虎头蛇尾」（前几集堆完钩子/反转、中后段密度雪崩）的苗头拆集就能看见。攒够若干集后跑 `python3 <skill>/scripts/series_balance.py <作品根>`：复用 beat_audit 各集信号，量**前 1/3 vs 后 1/3** 的钩子密度/反转率/镜数落差，报 `back_loaded_decline(_severe)`/`reversal_drought_late`/`shot_count_decline`。默认 report-only（`--strict` 仅在后段密度<前段一半时 exit 1），是"视图"不是硬闸——拿它在拆集阶段重排高能桥段、别把好戏都堆开头。
   > **分镜可生成性/成本风险评分（出图前置·非生成）**：`n2d/run.py next` 到 `image_prompt` 前还会跑 `python3 <skill>/scripts/shot_risk_audit.py <作品根> 第N集 --json`，按长镜、高运动、说话近景、大表情、多人同框、VFX/道具等给每 Clip 打风险分。`must`（如清晰同框 ≥2 具名角色缺 `多人同框身份槽位`/`多人同框执行策略`、多人近景未拆或未登记真分层、大表情近景缺尾帧）阻断回 n2d-script（**要求登记把它做对的执行策略，不是删戏**·C6 剧情优先）；普通高风险以 warn 透出，建议拆 establish+反打/登记 split_composite 把同框拍全、补 `_mid/_aK`、换更强模型或先进 `n2d/run.py pilot <作品根> 第1集` 做代表 Clip 小样。随后 `story_economy_audit.py <作品根> 第N集 --write --json` 先给每镜分配经济性目标（详拍/选择性详拍/压缩/蒙太奇/反应插入）；`shot_split_decision.py <作品根> 第N集 --write --json` 再把叙事权重、分镜语法需求、生成风险、剧情经济性和 story_clip/video_shot 时长策略合成 `生产数据/shot_split_plan_第N集.json/md`，逐镜给出 `keep_single` / `compress_before_video` / `split_video_shots` / `split_reaction` / `split_establish_detail_reaction` / `template_required` / `add_mid_or_multi_anchor` / `defer_to_composite` 决策；`duration>12s` 的 Clip 会写 `video_shot_segments[]`，`duration>15s` 标记 `direct_submit_allowed=false`，但非详拍长镜会优先标 `compress_before_video`。它是出图/出视频前的可复核拆镜依据；硬阻塞仍由合同、剧情经济性、risk gate 和 n2d-video 付费边界执行。
   > **高动态/大场景专项契约（出图前置·硬闸门）**：`n2d/run.py next` 到 `image_prompt` 前还会跑 `python3 <skill>/scripts/spectacle_contract_audit.py <作品根> 第N集 --strict --json`。打斗、追逐、法术/武技爆发、飞行/腾云驾雾、御兽/坐骑、马车/载具行进、飞舟/御物飞行、现代车辆/车流、尾随/潜入必须写 `template` + `template_contract` 的动作编排字段（beats、speed_curve、spatial_path、camera_path、readability_beats、degrade_plan、`keyframe_plan`、`post_cue_points`、`physics_guard` + attack/impact/contact、charge/release/collision、screen_direction/distance、flight/altitude/pose、mount_contact/gait_cycle、vehicle_lock/wheel_rotation/harness_lock、lane_lock/traffic_flow、occlusion_layers/light_shadow_lock 等专属字段）；屏幕插入/搜证必须写设备/overlay 或物证/证据链字段；大场景/大场面必须写 `large_scene_contract` 或 `spectacle_contract`（geography_map、scale_reference、parallax_planes、landmark_anchor、camera_path、establishing_progression、reuse_asset_id）。缺字段先回本阶段补，不把“精彩打斗/剑气爆发/骑兽狂奔/马车疾驰/车流疾驰/暗处尾随/宏大场面”这种散文 prompt 带进付费链路。
   > **高动态制作计划 + sequence 总账 + probe pack（出图前置·非生成）**：同一前置会写 `生产数据/spectacle_plan_第N集.json/md`、`spectacle_sequence_plan_第N集.json/md`、`scene_layer_pack_plan_第N集.json/md` 与 `spectacle_probe_pack_第N集.json/md`。`spectacle_plan` 列出每个打斗/追逐/法术武技爆发/飞行/御兽/马车/飞舟/现代车辆/尾随潜入/屏幕插入/搜证/大场景 Clip 的缺契约字段、所需 Motion Control 输入、回退/保真实现方案、剪辑 cues 和 `premium_passes`；`spectacle_sequence_plan` 把连续打斗/追逐/腾云/御兽/载具/飞舟/现代车辆/尾随潜入/大场景合成 sequence 级总账，锁 clip_order、subject_slots、asset_persistence、path_lock、handoff_states 和 reference_clip_policy，video gate 缺它会 BLOCK；动作序列还带 **逐拍拆镜 `beat_decomposition`（起手/命中/反应一拍一镜）+ `premium_coverage_policy`（关键帧覆盖/命中峰值可读/剪辑音效同步）+ 负向身份锁词 `negative_identity_lock`（钉死脸/服装/配饰/年龄漂移）+ 多角色同框策略 `same_frame_policy`（≥2 具名脸必须有槽位+执行策略；>2 建议拆正反打/景别分层）+ 运动强度档 `motion_intensity`(0–3) + 3–4 角度定妆建议**，供出图/出视频 prompt 注入；gate `动作节拍预算` 闸把「一镜塞完整攻防回合(跨≥3 节拍类别)」拦回拆镜（production 升 BLOCK），高速运动镜首尾双帧不可豁免；`scene_layer_pack` 为大场景/腾云场景脚手架 `设定库/scene_layers/<LOC>/scene_layer_pack.json`，锁 landmark_anchor、scale_reference、depth/parallax planes 和 reusable bg keyframes；`spectacle_probe_pack` 从本集各挑一个代表 Clip 做小样矩阵，并给出 `生产数据/spectacle_backend_benchmark.json` 的填写 schema。后续 `n2d-model-router` 会读取该 benchmark，把真实 probe 结果回灌到 primary/fallback。**打斗剪辑 cue↔apex 对齐审计（storyboard 定稿后·report-only）**：跑 `python3 <skill>/scripts/combat_cue_apex_audit.py <作品根> 第N集` 写 `生产数据/combat_cue_apex_第N集.json/md`，把"剪辑 hit-stop/震屏/SFX/闪白峰值必须对齐命中/apex"从散文 post_rule 兑现成对账——`fight_exchange/magic_burst` 的 `impact_frame/collision_or_apex_frame` 须带 `<秒>s`（否则 `combat_apex_untimestamped`），且 `anchor_planner` 须在该秒注回 keyframe 锚（否则 `combat_cue_apex_no_keyframe`），keyframe 锚也应有剪辑峰值落上去（否则 `combat_apex_no_edit_cue`·info）。**已接 n2d-review 硬闸**：consistency_audit 把它 in-process 卷进「打斗撞点(SPEC-APEX)」维度，warn 码(untimestamped/no_keyframe)在**核心打斗镜（核心场景 LOC 或 高潮/爆点/关键 key 镜）× 交付边界(compose/review)** 升 BLOCK（与 W2/W3 光照核心场景硬化同口径·可经 `consistency_advisory_signoff` 签收降回 WARN）；非核心普通打斗镜保持 advisory。**打斗剪辑节奏曲线（advisory-only·report-only）**：跑 `python3 <skill>/scripts/combat_rhythm_audit.py <作品根> 第N集` 写 `生产数据/combat_rhythm_第N集.json/md`，审 fight_exchange/magic_burst 镜的切点节奏——`combat_pacing_too_slow`（平均切点间隔 > 区域慢阈值·国内~5s/海外~3.5s）/`combat_rhythm_flat`（≥3 切近乎等长=缺起伏，有 apex 却没向命中拍收紧时附注）。**全 info·不升 BLOCK**（节奏曲线是审美非硬伤，阈值带 internal-heuristic provenance·无公开打斗切点基准·不造假闸；撞点对齐硬伤才走上面的 SPEC-APEX 硬闸）。阈值单一真值在 `industry_benchmark.json proxy_thresholds.{combat_cut_interval_slow_sec,overseas_combat_cut_interval_slow_sec}`。
2. `分镜剧本.md` — 逐镜头视觉脚本（画面描述）。**镜头切分参考配音时长**：单镜台词过长可拆成多镜。**每镜按导演视角八维写画面意图**（`n2d/references/导演视角prompt.md`）——本阶段先定文字层的 ①镜头(景别+焦段) ②机位(角度/过肩，机位即态度) ④动作 ⑤场景 ⑥光影(动机光/调性，光替剧情说话) ⑦情绪+张力，外加 **与前后镜衔接方式（match cut / 首尾帧 / eyeline / 空镜）**；这是 n2d-image 把分镜图打成"剧照"而非"插画"的源头。多人/复杂打斗拆成单人正反打。**含战斗/飞行/突破/武技高光的集先按 `references/动作奇观精修标准.md` 写 `keyframe_plan` / `post_cue_points` / `physics_guard`**；**含打坐静修/炼丹炼器/双修合修的集按 `references/静修炼制双修精修标准.md` 写姿态、呼吸、能量路径、阶段流程、火候曲线、成品揭示和双修成年人自愿非露骨边界**；**含接吻/近吻/拥抱/抓腕/牵手/搀扶的集按 `references/亲密动作精修标准.md` 写年龄语境、同意边界、非露骨边界、脸部角度、接触点、遮挡顺序、身体部位归属和释放/停住帧**；**含打斗的集按 `references/打斗分镜.md` 拆**（五帧拆招 / 命中帧必出独立图 / 攻防正反打）；**含御剑飞行/御兽坐骑/马车载具/飞舟御物/追逐/渡劫突破/打坐静修/炼丹炼器/大阵/大场面 establish/斗法对轰/神魂(神识·元神出窍·夺舍) 等仙侠奇观的集按 `references/仙侠场面分镜.md` 拆**（飞行/御兽/马车/飞舟/追逐锁主体形态、速度交给背景/视差/步态/轮转/镜头 / 渡劫炼丹法阵对轰爆发帧(命中·撞点)单独出图 + 奇观元素入库 / 静修锁坐姿、吐纳周天和内在结果 / 神魂元神=肉身半透明派生治"二我" / 大场面三镜由远及近）。**含穿越/系统流/玄幻学院/血脉觉醒/契约召唤/秘境入口/炼丹炼器/双修合修/阵法仪式/神魂夺舍等场面的集按 `references/玄幻穿越场面分镜.md` 拆**（穿越锁入口与落点；系统/测灵文字走 overlay；契约兽/丹炉/阵法/元神入库；每镜只给一个结果；双修只做成年人、自愿、非露骨的能量循环/疗伤表达）。**含现代车辆/车流、手机/电脑/监控屏幕、搜证/物证发现、尾随/潜入/暗走廊等都市/悬疑场面的集按 `references/现代都市悬疑场面分镜.md` 拆**（车辆锁车体/车道/轮转/车流；屏幕文字走 overlay；物证锁 reveal_frame/证据链；潜入锁遮挡层/光影/距离曲线）。**含打斗、追逐、对话反打、真相揭示/身份曝光、公开对质/审讯/谈判、法术爆发、飞行、御兽/坐骑、马车/载具、飞舟/御物、现代车辆、屏幕插入、搜证、尾随潜入、渡劫突破、打坐静修、炼丹炼器、双修合修、接吻近吻、亲密互动、拥抱/拉扯、阵法仪式、神魂显化、穿越传送、契约召唤、测灵觉醒、关系转折、多人同框、群像站位的复杂镜头，先按 `references/专项镜头模板库.md` 选模板，再写具体镜头。**
3. `故事板.md` + **`storyboard.json`** — Clip 表（相邻分镜合片段；人物运动 + 镜头运动 + 动态细节 + **衔接设计**）。`storyboard.json` 是必需的机器可读接缝契约 **+ 留存契约 + 视觉契约种子 + 基础视觉风格契约种子 + 专项镜头模板契约 + 逐镜头实体排程**；缺它或缺必填字段时下游 gate 会阻断。**必写留存契约**：顶层 `first_3s_visual_hook`（0-3 秒静音可读的画面钩、烧屏字幕/标题卡、`muted_safe_proof`）+ `retention_promise_ledger`（开场/集尾/中段强钩的承诺-兑现账本：`hook_id / promise_type / opened_at / payoff_due`，延迟兑现写 `delayed_payoff_ep`）。**必写 `visual_contract` 种子块（keystone）**：本集色调基线 + 每场景光位锚（主光方向/色温/动机光源）+ 每场景轴线·视线（站位/轴线/默认视线）+ 每角色状态演进（伤/泪/妆/服随镜号单调推进，不回退不提前泄露）+ 景别阶梯。高频/主场景 `LOC_xx` 还要在 `asset_registry.json` 或场景卡补 `floor_plan`、`doors_windows`、`axis_rules`、`screen_direction_rules`，否则 production gate 会把“场景平面 FP1”升为 BLOCK。**必写 `style_contract` 种子块**：风格名 + 视觉基调 + 镜头与构图 + 光色策略 + 运动边界 + 风格禁忌 + `style_anchor`，来自 `_设置.md` 的 `基础视觉风格` 与 `global_style.md`，不要临场重发明；`style_anchor` 是风格归属机检真值，缺失或路径非图片时下游硬阻断。**复杂 Clip 必写 `template` + `template_contract`**：模板 ID、beats、blocking、camera_rule、continuity_must、negative 以及模板专属字段；打斗/追逐/反打/揭示反应链/公开对质/关系转折/法术/飞行/御兽/坐骑/马车/载具/飞舟/现代车辆/屏幕插入/搜证/尾随潜入/渡劫突破/打坐静修/炼丹炼器/双修合修/接吻近吻/亲密互动/拥抱拉扯/阵法仪式/神魂显化/穿越传送/契约召唤/测灵觉醒/多人同框/群像站位缺模板会被 gate 阻断。**每个 clip/shot 应写 `entity_schedule` + 在场链字段**（characters / objects / locations / knowledge_state / required_presence / offscreen_presence / forbidden_presence），并在 `continuity.entry_exit` 写清人物/关键物件的入画、出画、画外保留或换场原因，作为 EntityBench 风格 per-shot schedule 真值；出图前 `entity_schedule_audit.py` 会报告覆盖率和漏登，storyboard contract 会阻断连续接缝里未解释的实体凭空出现/消失。若本集开头有意不接上一集实体、而是切 B 线或延迟回收，前两个 clip 或顶层必须写 `hook_bridge`（from_episode / thread_id / bridge_text / answers_prev_hook 或 delayed_payoff_ep），否则 `beat_audit --strict` 会把实体零重合报断线。核心道具、武器、证物、法宝一旦在 storyboard 中出现“持有/拿着/佩戴/背负/握住”等关系，必须同步维护 `production_consistency`/POS 持有账本或等价 `possession_ledger`，不再等到交接/丢失时才补。主角/核心反派长期使用的武器、法宝实体还必须在脚本阶段给出 `WEAPON_xx` 需求：名称、归属角色、审美方向、剪影尺度、携带方式、战斗用法、VFX 签名、禁漂项，并要求 n2d-image 写入 `asset_registry.weapon_profile` 与角色 `signature_equipment`；坐骑、马车、飞舟、现代车辆、手机/电脑、证物等长期复用对象同样要登记 `BEAST/MOUNT`、`VEHICLE/PROP` 或 `PROP/EVIDENCE` 需求，锁剪影、接触/牵引、轮组/阵纹、屏幕文字层、证物编号/污渍和禁漂项，不能留给出图临场发明。**这些是分镜设计阶段就该定死的导演决策，不是留给 n2d-image 凭空发明**——轴线/光位/状态/构图/光色/武器/坐骑/载具/屏幕/证物形态一旦在出图烤进像素，出视频救不回；n2d-image 的「本集视觉一致性契约」和「本集基础视觉风格契约」继承本块（schema 见 `references/formats.md §4`）。`continuity` 块每 clip 另填 `eyeline`/`shot_size`（从 visual_contract 取真值）。**Clip 时长 = 所含镜头时长之和（来自 `镜头时长.json`，配音驱动）**；阶段2 只按剧情节奏设计 Clip，不因未选后端硬切；到 n2d-video 前再由 router 按所选/可用后端的单 Clip 上限检查，超上限才拆 Clip或换长镜后端，别一刀切 8s。相邻镜是否复用边界帧由 `continuity.seam_mode` 决定，不再给所有非最终 Clip 强制尾帧。
   - **每 Clip 必写接缝分类**：从 `continuous_take_relay / match_on_action / graphic_match / eyeline_cut / reaction_cut / insert_cutaway / j_cut / l_cut / dissolve / hard_cut / intentional_discontinuity` 选择并填证据。只有 relay 设 `need_endframe=true`；其他模式分别锁动作相位、匹配图形/构图、视线、反应/插入对象、声桥、叠化或跳切理由。
   - **每 Clip 标节奏注记**（`导演节奏.md §四/§五`）：`铺垫·长镜` / `加速·碎切` / `爽点·CU硬切` / `留白·定格` 四选，让镜头时长成"曲线"而非等长堆叠——铺垫拉长、临近爽点逐个变短、爽点后给 1-2s 留白。
   - **每 Clip 落导演运镜 sidecar**：定稿后跑 `director_camera_plan.py --write`，用 `CAMERA_MOVE_LEXICON` 审查/推荐推、拉、摇、移、升降、跟拍、固定等结构化运镜。下游出图读 `image_prompt_injection` 决定首帧起幅余量；下游出视频读 `video_prompt_injection` 填导演调度七字段。
   - **标爽点累计时间戳**（如 `💥爽点 @ 0:48`）：供 n2d-compose 把 BGM drop / 重音效卡在这一帧。
   - 设计完对照 `分镜语法.md`（镜头空间）+ `导演节奏.md`（时间留存）**两份**自查清单。
   - **关键帧/编辑切点自动规划（storyboard.json 定稿后必跑）**：运行 `python3 skills/n2d/n2d-script/scripts/anchor_planner.py <作品根> 第N集`。默认 `中段锚帧默认=关闭`，普通单拍不补 `_mid`；E1 多 `lens/camera/shot_size` 镜位边界始终出 `use=edit_cut`，R1/R2/R3 高风险连续动作/长镜/漂移实证始终出执行锚。只有用户显式开启且后端单次请求原生支持 3+ 帧时，普通 D0 镜才加 `_mid`。
     - **执行语义**：`use=edit_cut` 生成前后 take 共用边界图；`use=split/keyframe` 进入 native multiframe 或 split relay；`use=qc/reference` 只作验收，runner 不消费。first-frame-only/未知后端不再默认建议为所有普通镜额外花一张中帧图。
     - **流程**：先 dry-run 产 `生产数据/anchor_plan_第N集.json/md`（规则、边界、成本）→ 标准模式人确认；“仅高风险停审”模式由代理按风险最小、可逆、默认 risk-only 的方案记录理由 → `--write` 注回 `continuity.anchors` 与 `policy.midframe_default_mode=risk_only|explicit_opt_in`。下游 n2d-image 只出声明所需图片，n2d-video 按 `frame_strategy` 执行；任何会增加付费调用的选项仍在付费前 BLOCK。
   - **题材母题检测（storyboard.json 定稿后·检测+建议·确认后注入）**：跑 `python3 skills/n2d/n2d-script/scripts/motif_detector.py <作品根> 第N集`（默认 dry-run）识别**题材**（系统流/穿越/修仙…）与**复现母题桥段**（系统面板出现/升级/系统刷新/签到/抽奖/爆装备）→ 出 `生产数据/motif_plan_第N集.{json,md}` 给增强建议（场景/道具/台词/成长档/overlay 文字层）。穿越/系统流爽文的"系统面板"是高频复现且带成长属性（面板进化、等级只增不减）的核心爽点，做好观众爱看。标准模式人确认；“仅高风险停审”模式由代理依据源理解合同和题材证据选择最优、可逆方案并写理由，然后 `--write` 注回。任何改剧情因果、引入敏感题材或增加付费生成的选择仍停在对应闸门。**混合渲染**：AI 只出锁色锁形发光光幕底框（`VFX_系统面板`，禁烤文字数字），等级/属性数值由 n2d-compose 期 overlay 叠清晰文字层。完整契约见 `references/题材母题框架.md`；模板见 `references/专项镜头模板库.md` §0.2/§12。
4. `素材清单.md` — 角色/场景/道具的 AI 图片 prompt（复用角色卡锚定，**中文+英文双版默认都写**）。中文 prompt 偶尔会触发平台安全规避或误判，英文版作为同义兜底；执行下游出图/出视频时默认建议中英都保留，由平台/CLI 选择更稳的一版。

**完成后**：`_进度.md` 勾选 `分镜设计` / `素材清单` / `字幕中` ✅（默认中文-only 不勾 `字幕英`；项目显式选中英双语/仅英文且已产 `字幕_英文.srt` 时才同步勾 `字幕英`）。`奇观连续性` 列**无需手勾**——出图前 image_prompt prework 生成序列总账后自动回写（✅=有奇观且覆盖，—=无奇观）。记录生产数据：

```bash
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py record <作品根> \
  --episode 第N集 --stage script --event generation \
  --asset 脚本/第N集/storyboard.json --status pass \
  --duration-sec <本阶段耗时秒> --provider <LLM或agent> \
  --meta phase=storyboard_design
```

**收尾 · 详列下一步**（回写 `分镜设计`/`素材清单`/`字幕中` 后跑 `python3 skills/n2d/progress.py <作品根>`，把前沿念给用户）：

```
第K集 阶段2(分镜设计) 齐：
- 分镜剧本 / 故事板+storyboard.json / 素材清单 / 镜头时长.json / script_quality_contract ✅；validate_timings 与 script_quality_gate 通过
- _进度.md 已勾选阶段2 列
下一步建议：
- 先确认 animatic_packet + timed animatic + P-3 交接包（production_breakdown / continuity_breakdown / continuity_chain / continuity_bible / ai_shooting_schedule / ai_shooting_schedule_batch_seed / ai_call_sheet），再进 n2d-image <作品根> 第K集 出两层 prompt（共享定妆库 + 本集分镜）+ 出图 PNG
  （正式出图前会先过 dashboard gate image_preflight；缺 table_read/animatic/P-3/compliance/registries 会拦，按提示先补）
- 可并行：n2d-script <作品根> 第K+1集 推进下一集
```

## 后期删减（回流）

要删某镜时**回源头改、重跑回流，别在成片上剪**。可自动推导链一键完成：

```bash
python3 <skill>/delete_shot.py <作品根> 第N集 镜头6 [镜头7 ...]
```

自动：删 voiceover 行 + **同步删 `字幕_英文.srt` 对应块**（仅当海外双语该文件存在时；finalize 按 index 取 EN 文本，不同步必错位）+ reflow `时长清单.json`（保留句时长不变）+ 重拼 voice_zh.wav（有 ffmpeg）+ 重跑 finalize 重定时。**不动**设计文档(故事板/分镜剧本/bgm/可灵)与已生成 PNG/clip——按脚本末尾清单人工清理 + 重跑 `n2d-compose`。详见 `n2d/Q&A.md` Q27。

## 创作规范（硬约束，缺一不可）

- **`references/拆集法.md`（集边界）**——**北极星：每集一个核心看点（爽点/打脸·强反转·情绪峰·视觉奇观，好看=目标 / 合理·饱满=地板）** + P0→P6 拆集优先级（先找结尾断点/每集完整冲突→看点→钩子闭环/切点让下集冷开场/钩子密度/时长仅作软节奏意图/自然幕界/角色登场+首集加权）+ 逐集自查清单。**阶段1 拆集必读**——决定"切成几集、每集起止在哪、每集凭什么好看"。
- **`references/追更骨架.md`（剧级留存骨架·Gap1）**——P0→P6 单集边界**之上**的整部留存层：开篇黄金集群 / 情绪递进区 / 大反转集 / 付费·AD 卡点集 / 断点强度梯度，按 `变现模式`（免费/付费/海外）排布。**阶段1 拆集必读**——决定"整部怎么排、卡点在哪、断点强度怎么跨集分布"；机检走 `boundary_audit.py` 的「剧级追更骨架」段。各管一层：**追更骨架**(整部) → **拆集法**(集间边界) → **导演节奏**(集内时间) → **分镜语法**(每镜空间)。
- **剧情完整性账本（SI1·选择/动机/线程）**——`scripts/story_integrity_audit.py` 管每集是否真的发生了选择→后果、角色动机是否可见、A/B/C 线是否到期回收、前 3-5 集追剧契约是否清晰、集尾是否是假 cliffhanger、对白是否推进戏。**阶段1/2 文本期必跑**，默认报告优先；修的是剧情合理好看，不修时长。
- **`references/分镜语法.md`（空间）**——景别系统/节奏铁律/连贯三规则(轴线·30°·视线方向)/转场逻辑/运镜克制/构图/8条自查清单。**阶段2 必读**。
- **`n2d/references/导演节奏.md`（时间·留存）**——留存曲线/黄金3秒/钩子密度/爽点憋放/集尾cliffhanger/镜头时长曲线/卡点/念白节奏；若 `n2d-feedback` 已写入投放快照，按快照调优下一批开场、集尾和镜头密度。**阶段1 写词 + 阶段2 分镜都必读**。这是把漫剧从"能看"做到"追得停不下来"的那一层，也是红果爆款"画质普通但留人"的真正秘密。
- **`n2d/references/导演视角prompt.md`（画面意图·八维）**——把每镜 prompt 从画师视角("好看插画")升级成导演视角(镜头·机位·人物·动作·场景·光影·情绪·画质)。**阶段2 写分镜剧本时定其文字意图层**（①②④⑤⑥⑦），并用 `director_camera_plan.py --write` 把运镜建议落成 sidecar；下游 n2d-image/n2d-video 据此装配实战 prompt。
- **`../../docs/n2d-传统短剧导演排戏流程.md`（P-2 方法论）**——传统短剧导演拿到剧本后的排戏、调度、运镜、镜头衔接和竖屏短剧差异；解释为什么 n2d 在分镜前新增 P-2 导演排戏包。
- **`../../docs/n2d-传统短剧制作全流程落地方案.md`（P-1~P-3 方法论）**——传统短剧从小说开发、编剧改编、导演排戏、制片拆解、AI 拍摄到后期验收的完整落地方案；解释为什么 n2d 在出图 prompt 前新增 P-3 制片拆解包。
- **专项镜头模板库（复杂镜头·含打斗/追逐/对话反打/真相揭示/公开对质/关系转折/法术爆发/飞行/御兽坐骑/马车载具/飞舟御物/现代车辆/屏幕插入/搜证/尾随潜入/渡劫突破/打坐静修/炼丹炼器/双修合修/接吻近吻/亲密互动/拥抱拉扯/阵法仪式/神魂显化/穿越传送/契约召唤/测灵觉醒/多人同框/群像站位必读）：references/专项镜头模板库.md**——复杂镜头先选模板，再把 `template/template_contract` 写进 `storyboard.json`；gate 会阻断“只靠自由 prompt 写复杂动作/证据反应/关系转折”的 Clip。
- **传统影视镜头语法库（正反打/连续性剪辑/9:16 coverage）：references/传统影视镜头语法库.md + references/cinematic_coverage_grammar.json**——建立镜、双人镜、OTS、clean single、reaction、insert/cutaway、match on action、eyeline cut、J/L cut、re-establishing/buffer、纵轴对压、低角度压迫、信息揭示特写和蒙太奇省略的 n2d 合同写法。
- **静修 / 炼制 / 双修精修标准（打坐静坐冥想/炼丹炼器/双修合修必读）：references/静修炼制双修精修标准.md**——静修锁坐姿、呼吸、灵气路径和内在结果；炼制锁阶段流程、火候曲线、材料状态和成品揭示；双修只做成年人、自愿、非露骨的能量循环/疗伤表达。
- **亲密动作精修标准（接吻/近吻/拥抱/抓腕/牵手/搀扶必读）：references/亲密动作精修标准.md**——接吻锁年龄语境、同意、非露骨边界、脸部角度和接触/近接触帧；拥抱/拉扯锁接触点、力量方向、遮挡顺序、身体部位归属和释放/停住帧。
- **动作奇观精修标准（战斗/飞行/突破/武技高光必读）：references/动作奇观精修标准.md**——把“经费燃烧感”拆成 `keyframe_plan`、`post_cue_points`、`physics_guard`、premium QC 三项与场景配方；`magic_burst` 已进入奇观计划/序列/QC 链路。
- **玄幻/穿越场面（穿越落点/系统面板/测灵觉醒/契约召唤/炼丹炼器/阵法/神魂必读）：references/玄幻穿越场面分镜.md**——穿越锁入口与目的地，系统/测灵文字走 overlay，契约兽/丹炉/阵法/元神入库，结果拍给可读半拍。
- **现代都市/悬疑场面（车辆、屏幕、搜证、尾随潜入必读）：references/现代都市悬疑场面分镜.md**——都市/悬疑不只改光色；车辆要锁车体/车道/轮转/车流，屏幕信息走 overlay，物证要锁 reveal_frame/证据链，尾随要锁遮挡层/光影/距离曲线。
- **题材母题框架（穿越/系统流等复现桥段·系统面板/升级/签到/抽奖必读）：references/题材母题框架.md**——motif 一等概念总纲：检测器(`motif_detector.py`)→镜头模板(system_panel)→成长 VFX(`VFX_系统面板` lifecycle 只进不退)→overlay 数值层(n2d-compose) 全链，贯穿出图/出视频/合成。
- **打斗分镜（仙侠武侠武打/法术场面·含打斗集必读）：references/打斗分镜.md**——五帧拆招（起手/发力/命中/受击/收势）/ 命中帧必出独立图 / 攻防正反打 / 主角武器进 `WEAPON_xx` 武器库、特效进 `VFX_xx` / 打斗节奏曲线 + 全链示例。
- **仙侠场面分镜（御剑飞行/御兽坐骑/马车载具/飞舟御物/追逐/渡劫突破/炼丹炼器/大阵法阵/大场面 establish/斗法对轰/神魂(神识·元神出窍·夺舍)·含这些奇观的集必读）：references/仙侠场面分镜.md**——飞行/御兽/马车/飞舟/追逐「锁主体形态，速度交给背景、视差、步态循环、轮转和镜头」/ 渡劫炼丹法阵对轰「拆递增 + 爆发帧(命中·撞点)单独出图 + 奇观元素入库锁死」/ 神魂「元神=肉身半透明派生治"二我"、神识靠波纹给信息」/ 大场面「三镜由远及近 + 比例尺 + 地标复用」+ 各 stage 落地速查 + 全链示例。与打斗分镜同源（关键帧锁死、视频只受控运动、后期补"感"）。

> 各管一层：**拆集法**定"切在哪（集间）"→ **导演节奏**定"每集怎么走（集内时间）"→ **分镜语法**定"每镜怎么切（空间）"→ **导演视角prompt**定"每镜怎么写成 prompt（画面意图八维）"→ **专项镜头模板库**定"复杂镜头怎么拆成可控契约"。

## 平台提示词规范

见 `references/platforms.md`（各视频模型/渠道/生图模型/渠道档案：提示词语言/画幅/Clip时长/角色一致性机制/运镜词/负面词，及"如何新增平台"）。目标视频模型以 `video_model_routes.json` 为准，`_设置.md` 的 `生视频模型` 只作普通镜/固定模式目标，调用渠道以路由表和 `生视频渠道` 偏好共同决定；新作品首跑不强问具体视频模型/渠道。旧 `生视频AI` 只作兼容 fallback。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 按字数/章数机械切集 | 先找结尾强断点定边界，字数让位节拍（`拆集法.md` P0/P4，章≠集）|
| 只看单集 raw 就写 voiceover | 每次看 5-10 集窗口；先跑 `boundary_audit.py` 取得稳定 blockers，再用 `boundary_review.py draft/check`；机器 draft 与人工 `boundary_review.json` 分离，改边界须有 applied receipt |
| 短集独立成集但无强钩 | 短集(<650字)必须复核：有强爆点可保留，否则并入前/后集 |
| 为省时长删必要镜头/铺垫 | 不删剧情因果链；只压缩重复表达、合并边界或提高台词密度，必要删除必须写明"非剧情必要" |
| 为合并一集立刻重编号全剧 | 不要贸然重排 300 集目录；先在精修取材层合并/挪段，批量定稿后再统一整理进度表 |
| 切出"纯铺垫集"（整集无出口）| 每集装一个完整「憋—放」闭环，铺垫段并进有爽点的相邻集（P1/P3）|
| 角色做了选择但没有代价/后果 | 跑 `scripts/story_integrity_audit.py <作品根> 第N集 --write`，补可见 consequence：资源、关系、局势、身份或目标至少一项变化 |
| 角色突然行动、动机像外挂 | 在 voiceover/storyboard 补当前目标/恐惧/筹码/立场信号，写入 `story_integrity_ledger.json` 的 motivation vector |
| 集尾只有惊吓句，没有前因 | 集尾钩必须有前文实体/因果/揭示支撑，或在 storyboard 写 `hook_bridge/thread_id/delayed_payoff_ep`，避免假 cliffhanger |
| 对白连续解释世界观 | 每 2-3 句对白至少推进一次选择、施压、揭示、隐瞒、关系变化或动作；`dialogue_not_advancing` 命中后回写戏剧动作 |
| 集断点完整但平庸、没人想看 | 拆集北极星：每集先说出**核心看点**（爽点/打脸·强反转·情绪峰·视觉奇观 四选一），无看点/看点弱的集合并重构；好看是目标，合理与饱满是不能击穿的地板（不靠降智/糖精/删因果换好看）|
| 视觉奇观被埋中段或被切点劈半 | 奇观当整集锚点（北极星看点④·AI 漫剧差异点）；`boundary_audit.py` 视觉奇观放置初筛会报劈半/弱锚点 |
| 集尾停在半场戏/平淡处 | 边界 snap 到最近 cliffhanger（危机悬置/真相半露/反转预告），集尾硬断（P0）|
| 切出"以过渡戏开头"的集 | 切点要让下集能 0-3s 冷开场，否则前/后挪边界（P2）|
| 从中间章节直接写 voiceover | 先补 `设定库/中段开工前情资产包.md` 并跑 `midstart_context.py check`；常态定妆、当前形态、前情摘要、关键卡和前后窗口都要齐 |
| 跳过建卡直接出镜头 | 必先建角色/场景卡，镜头里复用锚定句 |
| 视频 prompt 只写画面不写运动 | 必含人物运动 + 镜头运动 + 动态细节 |
| 设计超复杂打斗/人群 | 改为 AI 易生成的单人/双人动作、固定或简单运镜 |
| 复杂镜头临场自由写 prompt | 先套 `专项镜头模板库.md`，在 `storyboard.json` 写 `template/template_contract`，再交给出图/出视频 |
| 平淡过渡、长旁白 | 先在 `adaptation_triage` 标 `narrate/defer/merge/omit`，再在 storyboard 写 `pacing_role=桥接解释一笔带过` + `runtime_priority=compressed/low`；非关键 Clip 只给最短可读画面，主时长留给冲突/爽点/钩子/打斗/反转 |
| 开场 logo/慢空镜/长旁白 | 0-3s 冷开场或倒叙钩，最炸的画面/台词放最前 |
| 中段一马平川 | 每 15-20 秒一个钩子/信息增量（`导演节奏.md §二`） |
| 集尾把戏讲完收干净 | 集尾 cliffhanger 硬断（危机悬置/真相半露/反转预告） |
| 镜头等长堆叠像 PPT | 镜头时长走曲线：铺垫长镜+爽点碎切加速+爽点后留白 |
| voiceover 只标台词不标情绪/节奏 | 每句标具体情绪+(语速)，反转词前 `||` 停顿，按曲线标 ⚡/💥/🪝 |
| 角色跨集外貌漂移 | 严格复用同一张角色卡 + 每镜 prompt 拼角色卡『锚点句』 |
| 分镜剧本只写"画面里有什么"（画师视角）| 按导演视角八维写画面意图（镜头·机位·人物·动作·场景·光影·情绪·张力），见 `导演视角prompt.md` |
| 随机切镜/连续同景别/跳轴 | 违反 `分镜语法.md`——景别有进有出、守轴线、相邻同主体机位差>30° |
| 镜头硬怼无衔接 | 用 match cut/首尾帧/eyeline/空镜过渡；爽点才用硬切+甩镜 |
| 输出散乱不入文件夹 | 所有素材写进 `第N集/` 对应文件 |
| 把出图 prompt 写进本 skill | 出图 prompt 是 `n2d-image` 的事，本 skill 只写 prompt 给那边作引用 |

## 详细案例与 Q&A

实战翻车 + 修正案例集中在 `n2d/Q&A.md`（调度器 skill 下，全阶段共用）。本 skill 涉及的相关问题：

- Q1：直接文生视频 vs 先出图再视频
- Q2：制作一集整体步骤
- Q34：能不能“先出视频后配音”（可选、非默认）—— 阶段2 在本模式下用估算时长，见上「阶段2 触发」
- 文件归档 / 目录铁律：见 `n2d/references/architecture.md §二`
- Q18：生图模型/渠道 vs 生视频模型/渠道关系
- Q19：定妆图跨集复用 / 共享层架构
