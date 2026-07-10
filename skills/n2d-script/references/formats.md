# 素材标准格式模板（Stage 1）

所有每集脚本素材按本文档模板填写。**提示词一律中文为主 + 英文备用**。

> 下文 prompt 示例以**生图模型 = `生图模型` 所选具体模型（默认 GPT Image 2），经 `生图AI/生图渠道` 所选官方/已登录入口访问（默认 Codex CLI；非 Codex/OpenAI 后端需用户签核例外），生视频模型/渠道后移到 n2d-video 出视频前由 router/probe 决定** 的写法为准。若用户已固定生视频模型，image prompt 末尾拼对应模型的图像风格锚定句；未固定时拼通用视频兼容锚定（核心分镜/卡片不变）。

> **视频兼容锚定规则**：出图阶段不强迫用户先选生视频后端。已固定模型时拼目标生视频模型的"图像风格锚定句"；未固定时拼通用视频兼容锚定并记录 `video_backend_decision=deferred`，由 n2d-video 选择能消化现有首帧的后端（见 `platforms.md` 各档案）。

> **出图 prompt 两层架构（共享 + 本集）属于 Stage 2**，不在本文档；由 `n2d-image` skill 负责。本 skill 的角色卡只写"① 定妆照 prompt"作为 Stage 2 的来源。

---

## 0. 中段开工前情资产包（设定库/中段开工前情资产包.md）

当作品不是从第 1 章/第 1 集开始制作，而是从中间章节、爆点窗口或投放测试窗口开工，先用：

```bash
python3 skills/n2d-script/scripts/midstart_context.py <作品根> scaffold --target "第48章" --window "第45-52章"
python3 skills/n2d-script/scripts/midstart_context.py <作品根> check
```

模板字段必须补齐；没有的项写"无"，不要留"待补"。

```markdown
# 中段开工前情资产包

## 0. 起点
- 目标起点：第48章
- 制作窗口：第45-52章
- 起点选择理由：从第48章大反转做爆点打样

## 1. 主角角色卡 / 身份基准
- 主角常态定妆基准：常态年龄、脸型五官、发型、服装、配色、身份阶层；不得混入当前章节临时伤/泪/觉醒态
- 主角当前章节形态：本窗口开始时已有的伤、服装、觉醒态、战损、境界外显；无则写无
- 主角禁漂锚点：3-5 个绝不能漂的识别锚点
- 主角当前战力/境界：等级、系统数值、武器/法宝、能力限制；无体系则写无
- 主角当前关系状态：与男主/反派/同伴/家族/宗门/系统的关系温度与敌友状态

## 2. 角色形象生命周期
- 生命周期文件：`设定库/characters/_生命周期.md`
- 当前窗口前已发生变化：按 章节/集 -> 角色 -> 变化 -> 定妆动作 列出；无则写无
- 当前窗口内预计变化：哪些角色会换装、觉醒、受伤、变体、年龄跳；无则写无
- 下游定妆动作：哪些形态要先建常态定妆，哪些要建当前形态/变体定妆

## 3. 前情摘要
- 前情摘要：300-800 字，说明到目标起点前主角经历、关键选择、当前处境
- 当前目标：目标起点这一段主角想要什么
- 主矛盾：谁阻拦/什么危机/什么误会或谜团
- 未兑现伏笔：观众需要知道但本窗口不能提前泄露的伏笔、真相、系统规则；无则写无

## 4. 关键角色 / 场景 / 道具卡
- 关键角色卡：本窗口会出现的具名角色，说明已建卡路径或待建卡摘要
- 关键场景卡：本窗口会出现的主场景，说明已建卡路径或待建卡摘要
- 关键道具/法宝/系统资产：武器、法宝、证物、系统面板、特效 VFX；无则写无

## 5. 目标章节前后窗口
- 边界复核窗口：第45-52章
- 窗口前承接点：目标起点前一幕停在哪里，人物姿态/情绪/信息状态是什么
- 目标集冷开场：0-3 秒能抓人的画面/台词/危机；不是过渡交代
- 窗口后钩子：本次制作窗口末端准备断在哪里，下一集怎么起
- 边界决策：保留 / 并入前集 / 并入后集 / 前后挪段；写原因

## 6. 开工结论
- 允许开工结论：可以从该起点开工 / 先补第X章前情 / 先建定妆变体 / 先调整边界
- 风险备注：主角当前形态易污染常态定妆、关系反转不能提前剧透、战力状态需锁等；无则写无
```

这份资产包不替代角色卡、生命周期表、场景卡和道具卡；它是中段开工时的最小上下文索引。正式出图前仍要由 `n2d-image` 生成共享定妆与 `identity_registry.json`。

机器侧另有一个轻量范围声明：`脚本/episode_scope.json`。当项目保留了早期样例集，但本轮实际从中段窗口开工，必须声明窗口，避免 `antecedent_audit.py --strict` 把有意跳过误判成删集事故。

```json
{
  "window_start": "第5集",
  "intentional_gaps": ["第3集", "第4集"],
  "reason": "第1-2集为样例验证，本轮投放窗口从第5集开始"
}
```

---

## 0.5 改编取舍表（脚本/adaptation_triage.json 或 脚本/第N集/adaptation_triage.json）

在写 `voiceover.txt` 前先落这张表。它回答“原文哪些必须成戏，哪些可以旁白带过/后文带出/合并/删除”，避免把弱信息硬拆成 clip，增加无意义接缝。

```json
{
  "kind": "n2d_adaptation_triage",
  "version": 1,
  "scope": "第1集",
  "source_fingerprint": "sha256:...",
  "items": [
    {
      "id": "AT_001",
      "source_span": "raw.txt:第3-8段",
      "beat_function": ["冲突起因", "人物动机"],
      "decision": "dramatize",
      "change_type": "preserve",
      "reason": "女主第一次做选择，后果会推动本集爽点，必须拍出来",
      "delivery": "进入 voiceover 镜头1-3，并在 storyboard Clip_01-02 成戏",
      "risk_if_removed": "观众不知道她为什么反抗"
    },
    {
      "id": "AT_002",
      "source_span": "raw.txt:第9-11段",
      "beat_function": ["世界观信息"],
      "decision": "narrate",
      "reason": "信息必要但无动作和冲突，拍成镜头会拖节奏",
      "delivery": "旁白一句：沈家三代守冷宫，早被京城遗忘。",
      "risk_if_removed": "低；只影响背景理解"
    },
    {
      "id": "AT_003",
      "source_span": "raw.txt:第15段",
      "beat_function": ["伏笔"],
      "decision": "defer",
      "change_type": "reorder",
      "reason": "此处解释会打断追杀节奏，后文可由玉佩发光自然带出",
      "delivery": "第2集 Clip_04 道具特写 + 男主台词带出",
      "adaptation_delta": {
        "changed_from": "原文此处直接解释玉佩来历",
        "changed_to": "本集只给玉佩异常特写，来历延后到第2集对峙时揭示",
        "preserved_function": ["伏笔", "道具重要性", "后续揭示"],
        "short_drama_reason": "先给视觉悬念，避免追杀段停下来讲设定",
        "payoff_guard": "第2集 Clip_04 必须兑现"
      },
      "risk_if_removed": "中；必须在 payoff_due 前兑现"
    },
    {
      "id": "AT_004",
      "source_span": "raw.txt:第18-20段",
      "beat_function": ["冲突升级", "爽点前压迫"],
      "decision": "dramatize",
      "change_type": "intensify",
      "reason": "原文压迫分散在三段内心戏，短剧改成当众逼问 + 近景反应，高潮更集中。",
      "delivery": "voiceover 镜头4-5；storyboard Clip_03 用公开对质模板",
      "adaptation_delta": {
        "changed_from": "女主独自内心意识到被陷害",
        "changed_to": "反派当众逼她认罪，女主从沉默到反击",
        "preserved_function": ["被陷害", "女主识破", "反击动机"],
        "short_drama_reason": "把内心戏外化成冲突，提升短剧可看性",
        "payoff_guard": "后续仍需保留反派设局的因果证据"
      },
      "risk_if_removed": "高；改写后必须保住设局因果"
    }
  ],
  "decision_values": {
    "dramatize": "必须成戏，进入 voiceover/storyboard",
    "narrate": "用短旁白/独白/系统音带过",
    "defer": "后文通过动作、道具、对白或结果带出",
    "merge": "并入相邻强节拍，不独立成 clip",
    "omit": "重复或非剧情必要，删掉不伤因果/动机/伏笔/状态"
  },
  "change_type_values": {
    "preserve": "保留原功能和主要细节",
    "compress": "压缩段落或信息密度",
    "reorder": "重排揭示顺序或把解释延后",
    "rewrite_detail": "改某个细节表达，但保留剧情功能",
    "intensify": "强化冲突/压迫/爽点/情绪峰",
    "add_hook": "为短剧开场/集尾补视觉或台词钩子",
    "combine_minor_role": "合并不重要小角色或路人功能"
  }
}
```

硬规则：

- `omit` 不得用于人物动机、因果、选择后果、伏笔/兑现、状态变化、关系转折、系统规则。
- `defer` 必须写 `delivery` 和预计承接位置；否则等同于漏交代。
- `narrate` 只能短，不把一整段设定塞成长旁白；长设定要拆成后文自然露出。
- 关键细节/剧情允许为短剧节奏稍作改写，但必须写 `change_type` + `adaptation_delta.changed_from/changed_to/preserved_function/short_drama_reason/payoff_guard`。没有这组字段的改写，在 `source_adaptation_audit.py --strict` 中仍会被当作疑似漏剧情。
- 每个进入 `voiceover.txt` 的剧情 beat 应能追溯到 `decision=dramatize|narrate|merge`，避免漏掉必要源文。

---

## 0.6 剧本质量交接合同（生产数据/script_quality_contract_第N集.json）

阶段2 定稿后必须由 `script_quality_gate.py --strict --write` 生成。它不是“评分报告”，而是 `n2d-script` 交给 `n2d-image` / `n2d-video` 的制片合同：把“好看”拆成下游必须消费的字段。

```json
{
  "kind": "n2d_script_quality_contract",
  "version": 1,
  "episode": "第1集",
  "status": "pass",
  "required_consumption_fields": [
    "core_attraction",
    "first_3s_visual_hook",
    "retention_promise_ledger",
    "pacing_allocation",
    "clip_dramatic_function",
    "audience_question_ledger",
    "performance_cues"
  ],
  "signable_fields": {
    "core_attraction": {
      "category": "强反转",
      "why_watch": "观众想看女主如何当众反杀并拿回主动权",
      "audience_payoff": "压迫兑现为打脸，且留下下一集追问"
    },
    "first_3s_visual_hook": {
      "visual_hook": "雨夜门槛血迹 + 女主被当众逼跪，反派鞋底干净",
      "content_promise": "谁杀了人、女主怎么翻盘",
      "muted_readable": true,
      "expected_metric": {"primary": "retention_3s", "target": 0.72}
    },
    "retention_promise_ledger": [
      {
        "hook_id": "H01",
        "promise_type": "truth_reveal",
        "opened_at": "Clip_01",
        "promise": "鞋底干净为何是破绽",
        "payoff_due": "第1集",
        "payoff_status": "paid",
        "payoff_evidence": "Clip_06 当众揭穿"
      }
    ],
    "pacing_allocation": {
      "primary_runtime_focus": ["Clip_01", "Clip_04", "Clip_06"],
      "compressed_clip_ids": ["Clip_02"],
      "strategy": "主时长给冷开场、打斗/揭穿高光和集尾钩；背景解释用旁白一笔带过，不独立成长 Clip。"
    },
    "clip_dramatic_functions": [
      {
        "clip_id": "Clip_01",
        "duration": 3,
        "pacing_role": "冷开场主钩",
        "runtime_priority": "primary",
        "dramatic_function": "用可视证据提出观众问题",
        "audience_effect": "让观众立刻判断女主被冤，并期待她反击",
        "spectacle_story_function": "无"
      }
    ],
    "audience_question_ledger": {"questions": []},
    "performance_cues": []
  },
  "findings": [],
  "summary": {"status": "pass", "blocks": 0, "warnings": 0, "clips": 8}
}
```

硬规则：

- `core_attraction` 必须回答“这一集凭什么好看/观众为什么看”，不是只写题材标签。
- `first_3s_visual_hook` 必须可画、静音可读，并明确内容承诺或观众问题。
- `pacing_allocation` 必须说明主时长给哪些核心/高光 Clip，哪些桥接、解释、反应或气氛 Clip 一笔带过；缺该字段会阻断出图前合同。
- 每个 Clip 建议写 `pacing_role` + `runtime_priority`。长 Clip 必须说明它为什么值得长；低优先级/解释/桥接 Clip 超过轻量时长时，不能继续按低优先级放行。
- 标为低优先级、解释、桥接、普通反应、一笔带过的 Clip 必须保持短；超过轻量时长时不能靠 `compression_plan` 放行，必须缩短，或重定级为 `primary/highlight` 并写明它承载的主干/反转/打斗/兑现功能。
- 剧情经济性字段建议：每个 Clip 同步写 `economy_intent`（`premium_detail`/`selective_detail`/`compact_story`/`montage_bridge`/`micro_reaction`）和 `target_story_clip_sec`。默认解释、情报、赶路、普通反应只给 2-6s；揭示/对质/反派登场 5-8s；战斗/动作、男女主或核心人物强情绪交流才给 8-15s 详拍。`story_economy_audit.py --strict` 会把非详拍超长段挡回编剧阶段，`shot_split_decision.py` 会将其标成 `compress_before_video`。
- 每个 Clip 必须有 `dramatic_function`；首镜、尾镜、爽点、反转、高潮、真相揭示等关键镜必须有 `audience_effect`。
- 打斗、追逐、飞行、大场景、法术爆发等奇观镜必须写 `spectacle_story_function`：奇观服务哪个剧情/情绪/信息回报，不能只写“酷炫”。
- 下游消费必须写 `生产数据/script_contract_applied_第N集.json`，按 `出图` / `出视频` scope 分别绑定 prompt SHA 与 contract SHA。`n2d-image` 自动写 `出图` scope；视频 prompt 写好后跑：

```bash
python3 skills/n2d-video/scripts/script_contract_receipt.py <作品根> 第N集 --scope 出视频
```

---

## 1. 角色卡（设定库/characters/角色名.md，全篇唯一，首次出现即建卡）

```markdown
# 角色卡 — {姓名}（ID: CHAR_01）

- 姓名 / 年龄 / 性别：
- 身份：
- 计划出场集数：（整数；主角/长线可写预计总集数，未知写“待确认”；供角色库分档，不等同主体 ID/LoRA 档位）
- 性格关键词：（3~5个）
- 固定外貌：发型、发色、脸型、肤色、特征（疤/痣等）
- 固定体态：（可视化+相对的定性词，如「精瘦运动型 / 宽肩高挑 / 娇小纤细」；避免「壮/大/丰满」这类量级模糊词，图像模型读不动）
- 相对身量（如有第二角色作标尺）：（以某主角为标尺写相对关系，如「比沈念高半个头 / 三人中最高、肩最宽」；多人同框出图据此锁谁比谁高/壮，写入 `identity_registry.forms[].physical_scale.relative_scale`）
- 绝对身高/体重（选填·仅写作元数据）：（如 178cm / 体型偏胖；**只供编剧连续性与推导上面的相对词，不进出图 prompt**——绝对数字 175cm/60kg 对图像模型基本是装饰、占 token 却 steer 不动像素）
- 固定服装：款式、颜色、材质、配饰
- 固定配色：（主色+辅色，便于一致性）
- 固定表情风格 / 动作习惯：
- 外部人物参考图使用范围（如有）：只取脸型 / 五官 / 眼睛神态 / 体态比例 / 身材气质；发型、发饰、服装、配饰、妆容、身份阶层和剧情状态必须按小说原文、角色圣经、当前形态变体与本集剧情决定，不继承参考图衣装。若用户声明为“定型参考图”，补 `reference_lineage`：参考图路径 / sha256 / 锁定的脸部 DNA / 可变项 / 禁漂项；少年态、成年态、觉醒态、高阶态等年龄或形态变体都必须从该 lineage 派生，不得无账换脸。

## 妆造拆解（锁一致性用）
- 发型/发色/发饰：（如：乌黑长发半披，无华饰 / 双环髻）
- 妆容：（如：素颜清淡、唇色淡 / 烟熏冷艳 / 病态苍白）
- 服装：（上下身款式、领口、袖型、材质、新旧、腰带）
- 配饰：（簪、耳饰、玉佩、腰牌等；没有也写"无"）
- 色卡：主色 + 辅色 + 点缀色（便于跨集统一）
- 服装选择评分卡：（剧情身份/阶层信号、剪影辨识度、与其他主要角色主色差异、竖屏小图可读性、AI 可复现难度、动作/视频友好度、跨集复用价值；低分项先改服装，不带病进入出图）
- `wardrobe_profile` 源头：（剪影 / 层次 / 领型 / 袖型 / 腰封 / 下摆 / 材质 / 纹样 / 主辅点缀色 HEX或HSV / 禁漂项 / 本形态允许状态；后续同步到 `identity_registry.characters[].forms[].wardrobe_profile`）
- **识别锚点（3-5 个绝不能漂的特征，跨集锁脸/锁妆造的最高优先）**：（如 沈念：① 凤眼薄唇 ② 乌黑长发半披素布发带 ③ 左腕淡旧疤 ④ 月白粗布旧宫装）
- **锚点句（把上面压成一句，每张分镜 prompt 末尾必拼，确保不漂移）**：（如「凤眼薄唇·乌黑半披发带·月白粗布·左腕淡疤」）
- 形态变体：（如沈念 常态/觉醒态；记录差异点，避免漂移）
- **形象里程碑（跨集生命周期·Gap2）**：（按集号列本角色的造型/年龄/服装/标志变化，如「第3集 换嫁衣→婚礼变体；第20集 十年后年龄跳+华发；第40集 黑化冷色造型」。全局汇总见 `设定库/characters/_生命周期.md`；每个里程碑到达前由 `n2d-image` 派生对应『形态变体』定妆，避免锁死后返工。年龄敏感长线角色必须写 `form + 年龄/年龄档 + 目标文件前缀 + reference_lineage`，如 `18岁少年态 → 定妆_贺平生_18岁少年*.png ← CHAR_HE_PINGSHENG 定型参考图脸部 DNA`。无变化写「全程沿用」）

**① 定妆照 / 角色参考图 Prompt（中文）：** ← Stage 2 会据此生成定妆组，作为后续所有镜头与视频首帧的"角色参考/图生图"锚点
角色定妆设定图：{姓名}，{年龄性别}，先做正面中性主参考 + 半身或全身服装锚 + 同源脸部特写；若角色库档位为 core_full，再做 45° + 侧面 + 背面 + 三视图人审拼版；recurring_standard 再做 45°，侧背按镜头补；named_minimal 在近景/侧背/多集复用时升档；{发型妆容服装配饰色卡}，干净浅灰纯色背景，柔和均匀打光、无强阴影，五官清晰、服装完整可辨；若使用外部人物参考图，只继承脸型/五官/眼睛神态/体态比例/身材气质，不继承参考图服装/发型/配饰/妆容；按 `基础视觉风格` 的角色设定图，高细节，竖版9:16
（备注：`core_full` = 主角/核心长线/计划出场≥10集；`recurring_standard` = 多集复现配角；`named_minimal` = 具名短线；`restricted_partial` = 只露局部/剪影。角色库档位控制资产深度，后端主体 ID/face embedding/LoRA 另行定档。）

**① 英文（备用）：**
character design / reference sheet: {name}, minimum named-character set with front-face neutral main reference + half-body or full-body outfit reference + same-source face closeup; add 3/4, side, back and turnaround according to library_tier and actual shot needs, {hair makeup outfit accessories palette}, clean light-grey solid background, soft even lighting no harsh shadows, clear face and complete outfit, Chinese ancient-fantasy webcomic character sheet, ultra detailed, vertical 9:16

**② Codex 图片 Prompt（中文·常态出镜）：**
（角色锚定描述，含外貌+妆造+气质+画风词，用于实际分镜出图）

**② 英文（备用）：**
（同上英文）
```

> 流程：先用 ① 定妆照锁定角色 → 用所选 `生图模型` 经 `生图AI/生图渠道` 访问入口，以定妆组做参考派生 → 之后每个分镜与视频首帧都基于它生成，保证脸和妆造不漂移。**实际生成定妆照在 Stage 2（`n2d-image`）做**，本 skill 只准备 prompt。
> 后续所有镜头严格复用角色卡，禁止外貌/发型/服装/年龄漂移，除非剧情明确要求并在卡上记录"变体"。年龄变体必须有带年龄/年龄档的 form 与定妆文件名，不用低龄定妆冒充成年/高阶阶段。

---

## 1.1 角色形象生命周期时间线（设定库/characters/_生命周期.md，全局唯一·Gap2）

**为什么单列一个全局产物**：角色卡的『形态变体』『形象里程碑』是**单角色**视角；但"第几集谁该变造型/年龄跳/换装"是**跨集×跨角色**的排程问题。定妆库一旦锁死，到第 N 集才发现该变=返工。对标字节小云雀短剧 Agent 的"全局角色管理·全生命周期形象变化自动扫描"。本文件是拆集/建卡阶段就预规划的**全局形象排程表**。

**怎么产**：建卡后跑 `python3 skills/n2d-script/scripts/lifecycle_scan.py <作品根> --write`（确定性预扫 raw，扫"时间/年龄、换装/造型、形态/状态"三类信号 → 候选里程碑）→ 人确认/合并到「人工确认时间线」。自动段每次扫描重生成，人工区保留。

```markdown
# {剧名} — 角色形象生命周期时间线（跨集·全局产物）

## 人工确认时间线
| 集 | 角色 | 形象变化 | 定妆动作（新建变体/换卡/沿用） |
|---|---|---|---|
| 第3集 | 沈念 | 大婚换嫁衣凤冠 | 新建『婚礼态』变体定妆 |
| 第20集 | 沈念 | 十年后年龄跳+华发 | 新建『中年态』变体定妆，文件前缀 `定妆_沈念_中年态` |
| 第52集 | 贺平生 | 14岁少年长到18岁少年 | 新建 `18岁少年态`，文件前缀 `定妆_贺平生_18岁少年`，从14岁正脸/脸部特写派生 |

<!-- AUTO:lifecycle_scan 以下为每次扫描重生成… -->
## 自动检测里程碑候选（已建卡角色：…）
| 集 | 信号类别 | 触发词 | 片段 | 疑似涉及角色 | 待人确认 |
| … |
```

**下游怎么用**：① `n2d-image` 在里程碑集到达前派生对应『形态变体』定妆，而非临场重画；年龄敏感角色的新形态定妆文件名必须带年龄或年龄档；② `n2d-identity` 跨集漂移报表把里程碑当**预期变化基线**——里程碑解释的形象变化=合法演进，里程碑之外的形象变化=漂移（崩脸/服装漂/年龄漂）。这条与 `n2d-identity` 的**集内** state 校验、`visual_contract.角色状态演进` 的**集内**单调推进互补，专补"跨集造型排程"这一层。

---

## 2. 场景卡（设定库/locations/场景名.md，全篇唯一）

```markdown
# 场景卡 — {场景名}（ID: LOC_01）

- 建筑/环境风格：
- 时间 / 天气 / 光线：
- 主色调 / 氛围：

**Codex 图片 Prompt（中文）：** （含环境+光线+色调+画风）
**英文 Prompt（备用）：**
```

---

## 3. 分镜剧本（脚本/第N集/分镜剧本.md）— 逐镜头脚本

每集 6~16 个镜头（随剧情闭环、爽点密度和实测节奏浮动，以 SKILL.md 为准）。每镜头：

```markdown
## 镜头 N
**画面视觉描述：** 时间/光线/环境 + 人物动作 + 表情 + 构图/景别/机位/运镜。
**台词 / 音效 / 旁白：** 台词（角色·情绪）：「…」 | 旁白：「…」 | 音效：[…]
```

节奏硬约束（详见 `n2d/references/导演节奏.md`）：0-3s 冷开场/倒叙钩，前15秒立核心悬念+第一个矛盾，中段每15-20秒一个钩子/信息增量、≥1次反转，集尾 cliffhanger 硬断。镜头时长走曲线（铺垫长镜 / 爽点碎切 / 爽点后留白），不要等长堆叠。

---

## 4. 故事板 Clip 表（脚本/第N集/故事板.md）— **AI 视频生成输入**

把相邻分镜合成 **片段（Clip）**，每片段 1~2 个分镜，作为"一次视频生成"的单元。剧本阶段按剧情节奏、动作闭环和接力契约合成 Clip，**不因首跑未选视频后端而硬按某个 8s/15s 上限切碎**；到 n2d-video 出视频前，再用实际路由后端能力复核单 Clip 上限，必要时只做不破坏剧情连贯的拆段接力或 reroute。

```markdown
## Clip 表（分镜连贯性校验后）

**片段1（Clip 1）：时长：7秒**　**节奏**：铺垫·长镜　**累计**：0:00-0:07
**场景**：{场景名}（夜晚/内）
**衔接设计**（接力契约）：
- 入点：**原样抄上一个 Clip 的「出点」**（同一句话——接力链单一真值，不允许相邻镜各写各的）；首帧构图如何接住上一镜尾势。
- 出点：本 Clip 结束时人物姿态/视线/道具/空镜停在哪里，下一 Clip 从哪里接。**这句会成为下一 Clip 的入点。**
- 转场：match cut / eyeline cut / 动作切 / 空镜缓冲 / 声音先行(J-cut) / 硬切。
- 需要尾帧?：是/否。**默认首尾双帧接力：除最终 Clip 外均为是**（n2d-image 出尾帧 PNG=下一 Clip 首帧构图，**尾帧命名=对应首帧名+`_end`**：`镜头N_xxx.png`→`镜头N_end.png`、`Clip_NN.png`→`Clip_NN_end.png`；n2d-video 用首尾双帧引导锁死接点）；只有换场空镜/时间大跳/明确不连续的接缝可设否，并必须写豁免原因。
- 中段锚帧/编辑切点?（risk-only）：普通单拍默认不补 `_mid`。`shots[]` 有多个明确 `lens/camera/shot_size` 时，E1 在每个切点写 `continuity.anchors[].use=edit_cut`；高运动模板、≥8s 多拍连续镜或中段漂移实证按 R1/R2/R3 写 `use=split/keyframe` 多锚。用户显式 `中段锚帧默认=开启` 且后端单次请求原生支持 3+ 帧时，普通 D0 才补一张 `_mid`。`use=qc/reference` 只作视频验收，不得被 runner 当时间轴输入。声明即必须填全字段，gate 阻断缺项/不递增/越界/缺 PNG；`--write` 写回 `policy.midframe_default_mode=risk_only|explicit_opt_in`。执行分 `edit_cut / native_multiframe / split_relay / first_last / first_only`，缺边界图或需 reroute 在付费前 BLOCK。
- 连贯性：轴线方向、人物左右站位、出入画方向、首尾帧是否可用于双帧引导；非最终 Clip 不能省略接力契约。
- 在场链：本 Clip 画面内出现谁/哪些关键物件，谁仍在场但只在画外，谁禁止出现；若相邻 Clip 有人物或物件新增/消失，必须写入画/出画/反打画外/换场/空镜/时间跳跃原因，不允许交给视频模型随机补人。
**分镜1：0-4s**
镜头：{景别}，{距离}，{机位角度}，{运镜}。
{画面动态描述：人物运动 + 镜头运动 + 动态细节，如烛火摇曳/晨雾流动}
**分镜2：4-7s**
镜头：…
{…}

> **节奏字段**（`导演节奏.md §四/§五`）：每 Clip 标 `铺垫·长镜` / `加速·碎切` / `爽点·CU硬切` / `留白·定格` 之一。
> 临近爽点的 Clip 逐个变短（碎切加速），爽点用 CU/ECU + 硬切，爽点后给一个 `留白·定格` Clip。
> 爽点 Clip 额外标累计时间戳（如 `💥爽点 @ 0:48`）——n2d-compose 用它把 BGM drop / 重音效卡在这帧。
> **衔接设计是硬字段**：每个 Clip 必须写。n2d-video 读取它生成视频 prompt 的"衔接/转场约束"，n2d-compose 读取同一意图执行声音连续、BGM 卡点、可选 J-cut 和空镜缓冲。没有衔接设计的故事板不能进入正式出视频，只能 rough preview。

## 物品补充设计清单
（本集出现但未建卡的关键道具，列出并补 prompt；无则写"无遗漏"）
```

> 视频 prompt 必须显式描述**人物运动 + 镜头运动 + 动态细节**。**含打斗按 `打斗分镜.md`：五帧拆招（起手/发力/命中/受击/收势）、命中帧必出独立图、攻防用正反打；仍避免一镜内多人混战、超复杂同框动作。** **含接吻/近吻/拥抱/抓腕/牵手/搀扶按 `亲密动作精修标准.md`：锁年龄语境、同意/非露骨边界、脸部角度、接触点、遮挡顺序、身体部位归属、释放/停住帧。** **含御剑飞行/御兽坐骑/马车载具/飞舟御物/追逐/渡劫/打坐静修/炼丹炼器/大阵/大场面 establish/斗法对轰/神魂 按 `仙侠场面分镜.md`：飞行/御兽/马车/飞舟/追逐「锁主体形态，速度交给背景、视差、步态循环、轮转和镜头」、渡劫炼丹法阵对轰「爆发帧(命中·撞点)单独出图 + 奇观元素入库」、静修「锁坐姿、呼吸周天、灵气路径和内在结果」、神魂「元神=肉身半透明派生治"二我"」、大场面「三镜由远及近 + 比例尺」。** **含穿越/系统流/测灵觉醒/契约召唤/秘境入口/阵法/炼制/静修/双修/神魂按 `玄幻穿越场面分镜.md` 与 `静修炼制双修精修标准.md`：入口与落点锁定，系统/测灵文字走 overlay，契约兽/丹炉/阵法/元神入库，每镜只给一个结果；双修只做成年人、自愿、非露骨的能量循环/疗伤表达。** **含现代车辆/车流、手机/电脑/监控屏幕、搜证/物证发现、尾随/潜入/暗走廊按 `现代都市悬疑场面分镜.md`：车辆锁车体/车道/轮转/车流，屏幕文字走 overlay，物证锁 reveal_frame/证据链，尾随锁遮挡层/光影/距离曲线。** 大量人群、高频切换等 AI 难生成动作仍从简。
> 空镜缓冲不是补丁位，而是故事板阶段就要设计的正式 Clip：换场、跳时空、强情绪转折、AI 难接的姿态变化，都优先插 1-2s 空镜/物件镜（门帘、烛火、雨滴、符纸、手部）承接。下游 compose 只负责保留它的呼吸，不在成片上硬塞未知空镜。

必须同步输出机器可读 `storyboard.json`（**接力契约 + 视觉契约 + 基础视觉风格契约的机器可读载体**——下游结构化消费衔接、视觉一致性与所选风格；缺它或缺必填字段时 `dashboard.py gate --stage image_preflight|video_preflight|image|video|compose`（生产入口，底层调 `n2d-review/scripts/gate.py --json`）会阻断）。

**`visual_contract` 是视觉契约的上游真值源（keystone）**：轴线·视线、场景光位、人物状态演进、景别阶梯本质都是**分镜设计阶段（本 skill）的导演决策**——在写 `故事板.md` 时就该定死，**不是留给 n2d-image 对着分镜剧本凭空发明**。n2d-image 的「本集视觉一致性契约」**继承本块**（见 `n2d-image/references/prompt_format.md §2.1`），逐镜 `视线方向/光位锚` 字段从这里取真值。凡视频改不动、要烤进首帧像素的视觉变量，源头都在这。

**`style_contract` 是基础视觉风格的上游真值源**：风格来自选择点 `基础视觉风格` 与 `global_style.md`。不要只在 prompt 末尾加 `cinematic/realistic/anime`；必须在分镜设计阶段定死风格名、视觉基调、镜头与构图、光色策略、运动边界和风格禁忌。n2d-image 的「本集基础视觉风格契约」继承本块，把所选风格烤进首帧；n2d-video 再继承同一契约，只做与风格相容的运动。缺字段时 gate 阻断。旧 `cinematic_contract` 仅作历史兼容。

**`template` + `template_contract` 是复杂镜头的上游真值源**：凡 Clip 涉及打斗、追逐、对话反打、真相揭示/身份曝光、公开对质/审讯/谈判、法术爆发、飞行、御兽/坐骑、马车/载具行进、飞舟/御物飞行、现代车辆/车流、手机/电脑/监控屏幕、搜证/物证发现、尾随/潜入/暗走廊、渡劫突破、打坐静修、炼丹炼器、阵法仪式、神魂显化、穿越/传送/秘境入口、契约召唤、测灵/天赋觉醒、双修合修、接吻近吻、亲密互动、拥抱拉扯、关系转折、多人同框、群像站位，必须按 `专项镜头模板库.md` 选模板并写契约。仙侠高频场面参考 `仙侠场面分镜.md`；静修/炼制/双修参考 `静修炼制双修精修标准.md`；接吻/拥抱等亲密动作参考 `亲密动作精修标准.md`；玄幻/穿越高频场面参考 `玄幻穿越场面分镜.md`；都市/悬疑高频场面参考 `现代都市悬疑场面分镜.md`。允许的模板 ID：`fight_exchange`、`chase`、`dialogue_shot_reverse`、`reveal_reaction_chain`、`public_confrontation`、`magic_burst`、`flight`、`mount_ride`、`vehicle_ride`、`vessel_flight`、`road_vehicle`、`screen_insert`、`evidence_search`、`stealth_stalk`、`tribulation_breakthrough`、`meditation_cultivation`、`alchemy_forging`、`dual_cultivation`、`kiss_or_near_kiss`、`array_ritual`、`soul_manifestation`、`realm_portal`、`contract_summon`、`talent_test`、`intimate_interaction`、`hug_or_pull`、`relationship_turn`、`multi_character_same_frame`、`ensemble_blocking`、`multi_person_blocking`（legacy）。普通空镜/单人静态反应可省略；复杂镜头缺模板或字段不全时 gate 阻断。

每个 clip 带 `continuity` 块，`start_state` 应等于上一 clip 的 `end_state`。同时带 `entity_schedule`，让“谁在画面里 / 谁在画外 / 谁禁止出现 / 谁入画出画”成为机器真值源：

```json
{
  "id": "Clip_02",
  "entity_schedule": {
    "characters": ["CHAR_SHEN", "CHAR_LIU"],
    "objects": ["PROP_鸩酒托盘"],
    "locations": ["LOC_冷宫寝殿"],
    "required_presence": ["CHAR_SHEN", "PROP_鸩酒托盘"],
    "offscreen_presence": ["CHAR_LIU"],
    "forbidden_presence": ["CHAR_GUARDS"],
    "knowledge_state": {"CHAR_SHEN": ["知道酒有毒"]}
  },
  "continuity": {
    "start_state": "沈念半坐床榻，鸩酒托盘在前景画左",
    "end_state": "沈念压住呼吸，视线落到托盘",
    "transition": "eyeline cut",
    "entry_exit": "柳娘子从画面右后退到画外，仍在场但不入镜；禁止新增侍卫",
    "need_endframe": true,
    "endframe_png": "出图/第1集/图片/Clip_02_end.png"
  }
}
```

相邻 Clip 若 `entity_schedule.characters/objects` 有差异，必须由 `continuity.entry_exit`、`offscreen_presence` 或转场（换场/空镜/时间跳跃/明确不连续）解释；否则 `n2d-review` 的 storyboard contract 会报“人物在场链”。这条专治“上一镜突然多出个人，下一镜又没有了”的随机视频问题。

**首屏留存契约（`first_3s_visual_hook`）**：顶层必须写 0-3 秒静音可读钩子。字段是硬 schema，缺任一项都会被 `beat_audit.py --strict` 阻断：

```json
"first_3s_visual_hook": {
  "visual_hook": "沈念脸部大特写，门外刀影压进画面，危机不用声音也能看懂",
  "hook_type": "危机",
  "content_proposition": "本集要回答：是谁要害沈念",
  "onscreen_text": "谁在门外？",
  "muted_safe_proof": "关声仍能从刀影+惊恐表情+标题卡理解悬念",
  "expected_metric": { "primary": "retention_3s", "target": 0.80 }
}
```

> **`visual_hook` 不只收"冲突"（GAP-2）**：硬门只要求"有一个静音可读的视觉钩"。钩子类型按导演节奏 §二的五类——**悬念/欲望/反差/信息/危机**（+情绪冲突）皆可，悬念/欲望/情绪型冷开场不必硬填一个"冲突"。可选 `hook_type` 字段写明属哪类（写了才校验是否在表内，不写不罚）。旧项目写的 `visual_conflict` 仍被当作 `visual_hook` 的**向后兼容别名**，不会报错。

也可放在首个 clip 的 `retention.first_3s_visual_hook`，但顶层优先。缺该契约、`expected_metric.primary` 不是 `retention_3s/retention_6s`、`target` 低于当前 `retention_hook_floor`、烧屏文字过载，或无法证明 `muted_safe` 时，`beat_audit.py --strict` 会在正式出图 prompt 前阻断。voiceover 前约 6 秒也必须有钩子信号，不能 storyboard 写钩、台词节拍慢起。

**钩子承诺-兑现账本（`retention_promise_ledger`）**：每个开场钩、集尾钩和中段强信息钩都要有 `hook_id / promise_type / opened_at / promise / payoff_due`。本集兑现必须写 `payoff_status=paid|resolved` + `payoff_clip/payoff_evidence/paid_by_episode` 之一；跨集兑现写 `delayed_payoff_ep`。该账本用于避免假悬念、爽点不兑现和尾钩断线。

```json
"retention_promise_ledger": [
  {
    "hook_id": "OPEN_01",
    "promise_type": "opening_hook",
    "opened_at": "Clip_01 / 镜头1",
    "promise": "门外刀影是谁",
    "payoff_due": "Clip_04 / 镜头6",
    "payoff_status": "paid",
    "payoff_clip": "Clip_04",
    "payoff_evidence": "Clip_04 揭示门外刀影来自亲妹妹派来的黑衣人",
    "bait_risk": "low"
  },
  {
    "hook_id": "TAIL_01",
    "promise_type": "cliffhanger",
    "opened_at": "Clip_08 / 集尾",
    "promise": "黑衣人真正主使只露半句",
    "delayed_payoff_ep": "第2集",
    "bait_risk": "medium"
  }
]
```

**跨集 hook 桥接（`hook_bridge`）**：若上一集集尾钩抛出 A 线，本集冷开场有意先切 B 线、延迟回收或从另一个角度回答，必须在本集顶层或前两个 clip 写 `hook_bridge`。否则 `beat_audit.py --strict` 会按实体零重合报 `cross_ep_hook_break`。字段最少写 `from_episode` + `thread_id` + `bridge_text`，若直接回答上一集悬念写 `answers_prev_hook:true`，若延迟回收写 `delayed_payoff_ep`。

**逐镜头实体排程（`entity_schedule`）**：每个 clip 或 `shots[]` 子镜都应写角色、物件、地点、知识状态和必须出现项；shot 级覆盖 clip 级。`entity_schedule_audit.py` 会统计覆盖率，并对 clip/shot 字段中已出现但排程漏登的角色/物件/地点给 warn。该字段是 EntityBench 风格 per-shot schedule 的 n2d 真值层，供后续出图、视频、审片和叙事 KPI 共用。

```json
{ "episode": 1, "title": "本宫才是这皇宫最大的妖·第1集", "source": "原著章节1-2",
  "total_duration": 86.5,
  "policy": { "tailframe_default": true, "midframe_default": true },   // tailframe gate 要求 =true；midframe_default=true 时每镜须有中锚声明或豁免（anchor_planner --write 写入）

  "first_3s_visual_hook": {
    "visual_hook": "沈念惊醒特写，门外刀影压进画面",
    "hook_type": "危机",
    "content_proposition": "谁在门外，为什么要杀她",
    "onscreen_text": "谁在门外？",
    "muted_safe_proof": "关声也能从刀影+惊恐表情+标题卡理解危机",
    "expected_metric": { "primary": "retention_3s", "target": 0.80 }
  },
  "retention_promise_ledger": [
    { "hook_id": "OPEN_01", "promise_type": "opening_hook", "opened_at": "Clip_01", "promise": "门外是谁", "payoff_due": "Clip_04", "payoff_status": "paid", "payoff_clip": "Clip_04", "payoff_evidence": "黑衣人身份线索露出", "bait_risk": "low" },
    { "hook_id": "TAIL_01", "promise_type": "cliffhanger", "opened_at": "Clip_08", "promise": "真正主使半露", "delayed_payoff_ep": "第2集", "bait_risk": "medium" }
  ],
  "pacing_allocation": {
    "primary_runtime_focus": ["EP01_CLIP01", "EP01_CLIP04", "EP01_CLIP07"],
    "compressed_clip_ids": ["EP01_CLIP02"],
    "highlight_budget_note": "主时长留给冷开场危机、揭示/打斗高光、集尾钩；非关键背景解释走旁白和道具特写。",
    "compression_strategy": "解释/过渡 Clip 控制为短镜或并入相邻强节拍，避免弱信息独立占长 Clip。"
  },

  "visual_contract": {                            // ← 视觉契约种子（keystone）；n2d-image 继承，勿留空
    "色调基线": "冷青压暗红；金瞳/妖气只在镜7爽点后出现，之前不得泄露",
    "场景光位锚": {
      "冷宫寝殿": { "主光方向": "画左前", "色温": "3000K 暖", "动机光源": "残烛" }
    },
    "场景轴线视线": {
      // 站位 = 该场景**注册的跨镜空间布局（四维坐标锚）**：逐角色写「方位（画左/画右/居中）+ 前后景遮挡序（…前/…后）」。
      // 同 LOC 各镜不论换什么机位都须守这套站位/遮挡序（反打镜左右翻转合法）；n2d-review 的 空间站位(B1)
      // 机检（scene_blocking_continuity.py）按本字段对逐镜 blocking/continuity_must 验跨镜站位连续性，违锁=block。
      "冷宫寝殿": { "站位": "沈念居画左、柳娘子居画右后", "轴线": "床→门 横轴", "默认视线": "沈念看画右门口" }
    },
    "角色状态演进": {
      "沈念": [ { "自": "镜3", "状态": "左颊新伤", "保持": "至集尾不复原" },
                { "自": "镜7", "状态": "金瞳觉醒态", "保持": "镜7后" } ]
    },
    "景别阶梯": "镜1 ELS establish → 镜2-3 MS → 镜5 CU 爽点；相邻镜不撞同景别同机位"
  },

  "style_contract": {                             // ← 基础视觉风格契约；n2d-image/video 继承，勿留空
    "风格名": "国漫写实",
    "视觉基调": "东方幻想国漫，角色比例略理想化，场景和服装材质写实，高细节但不照片化",
    "镜头与构图": "保留影视景别和轴线；可用更强剪影、广角压迫和法术特写，但不随机变透视",
    "光色策略": "青灰为主，烛火金只在情绪转折处强调；强光来自月光、烛火、符阵或兵器反光",
    "运动边界": "慢推、固定、跟摇为主；爽点可短促环绕或轻甩，禁止无理由飞行镜头",
    "风格禁忌": ["欧美脸漂移", "页游塑料盔甲", "随机霓虹", "过度磨皮", "背景像贴图", "低幼Q版"]
  },

  "clips": [
    { "id": "EP01_CLIP01", "label": "冷开场", "duration": 7, "scene": "冷宫寝殿/夜/内",
      "rhythm": "铺垫·长镜",                         // 与 故事板.md 节奏注记一致（铺垫·长镜|加速·碎切|爽点·CU硬切|留白·定格）
      "pacing_role": "冷开场主钩",
      "runtime_priority": "primary",
      "compression_plan": "无；本镜是首屏钩，7s 用于建立危机、角色反应和下一镜接力。",
      "character_ids": ["CHAR_01", "CHAR_02"],
      "object_ids": ["PROP_玉佩"],
      "location_id": "LOC_冷宫寝殿",
      "hook_bridge": {
        "from_episode": "第0集",
        "thread_id": "cold_palace_assassin",
        "answers_prev_hook": true,
        "bridge_text": "冷开场直接回答上一集门外黑影是谁，并把玉佩线索推进到本集。"
      },
      "entity_schedule": {
        "characters": ["CHAR_01/常态", "CHAR_02/常态"],
        "objects": ["PROP_玉佩"],
        "locations": ["LOC_冷宫寝殿"],
        "knowledge_state": { "CHAR_01": ["不知道玉佩为假"], "CHAR_02": ["知道玉佩为假"] },
        "required_presence": ["CHAR_01", "PROP_玉佩"]
      },
      "template": "dialogue_shot_reverse",            // 复杂镜头才填；普通空镜/单人反应可省略
      "template_contract": {                          // 复杂镜头模板契约；字段见 专项镜头模板库.md
        "template_id": "dialogue_shot_reverse",
        "beats": ["沈念听见门外脚步", "反打柳娘子逼近", "沈念抬眼回望"],
        "blocking": "沈念画左床榻，柳娘子画右门口，二人隔床幔对视",
        "camera_rule": "正反打守床→门横轴；过肩只从沈念肩后向画右拍，不越轴",
        "continuity_must": ["沈念画左、柳娘子画右", "烛火主光画左前", "沈念左颊伤不回退"],
        "negative": ["不要跳轴", "不要交换左右站位", "不要新增第三人正脸"],
        "axis": "床→门横轴",
        "eyeline": "沈念看画右门口，柳娘子看画左床榻",
        "shot_pairing": "Clip01A 沈念反应 CU / Clip01B 柳娘子过肩逼问"
      },
      "firstframe_png": "出图/第1集/图片/镜头01_冷开场.png",   // 由 n2d-image 落档后回填；gate image/video 必查
      "video_out": "出视频/第1集/视频/Clip01_冷开场.mp4",      // 由 n2d-video 落档后回填
      "continuity": {
        "start_state": "首帧：沈念蜷坐木榻、视线投向门口",
        "end_state": "沈念起身、右手扶榻、视线移向窗",   // ← 下一 clip 的 start_state 原样复制这句
        "eyeline": "沈念视线画右门口（继承 visual_contract.场景轴线视线，正反打镜按此对位）",
        "shot_size": "MS（继承 visual_contract.景别阶梯，不撞上一镜）",
        "expression_span": "大",                         // ← opt-in·近景表情跨度 微|中|大；本镜脸的情绪从起到止跨几档（平静→爆哭=大）。缺=不追踪。
                                                        //    `大`+近景/特写/反打 → gate 强制 need_endframe=true 走首尾双帧只插值（首=起表情/尾=止表情同源定妆），
                                                        //    否则单首帧硬扛跨情绪表情=脸型/五官随表情漂移（脸被表情带着重画的头号根因）。同情绪小变化用 微/中。
        "微表情节拍": "起：AU4 眉头紧锁+AU7 眼睑收紧+AU24 抿唇（隐忍）→ 止：AU1+AU4 眉头拧起+AU15 嘴角下压+welling tears（将哭）；屏息、下颌微颤",
                                                        // ← 近景/特写人物镜必填·FACS/AU 级微表情线索（眉/眼/鼻唇/嘴/呼吸微动）。expression_span=大 时首帧=起 AU 组、尾帧=止 AU 组。
                                                        //    单一真值源 n2d_const.MICRO_EXPRESSION_FIELD / FACS_AU_REGIONS；AU 术语优先英文，中文给口语化等义。详见 n2d-image「近景微表情深化铁律」。
        "transition": "match_cut",                      // match_cut|eyeline|action_cut|empty_buffer|j_cut|hard_cut
        "need_endframe": true,                          // 默认 true；非最终 Clip 若 false 必填 endframe_exempt_reason
        "endframe_png": "出图/第1集/图片/镜头02_end.png",     // need_endframe 时由 n2d-image 落档后回填
        "midframe": {                                   // ← 中段锚帧·单锚帧手写糖（默认规划；执行成本按后端能力：native multiframe / split / qc）
          "midframe_png": "出图/第1集/图片/镜头01_mid.png",   // 命名=首帧名+`_mid`；由 n2d-image 落档后回填
          "split_at_sec": 4.0,                          // 建议锚点秒数；native multiframe 为时间轴约束，split 时为 A 段时长
          "reason": "9s 三拍动作，redraw×2 中段动作漂移"      // 必填：为什么需要中锚（漂移风险/重抽记录/三帧契约默认）
        },
        "anchors": [                                    // ← 可选·N 锚帧链通用形（与 midframe 二选一，同时声明 gate 阻断；重动作长镜/动作链必填）
          // 由 scripts/anchor_planner.py 自动识别+规划写入（打斗等高运动模板/≥8s 长镜/起手-命中-收势链/漂移重抽实证），也可手写
          { "anchor_png": "出图/第1集/图片/镜头01_x_a1.png",  // 命名=首帧名+`_aK`（三帧契约默认中锚=首帧名+`_mid`）；n2d-image 落档后回填
            "at_sec": 4.0,                              // 焊点秒数，严格递增；use=split 时各段 ≥ 目标后端最短时长
            "use": "split",                             // split=拆段接力 | qc=不拆段·视频验收中段基准/多参考 | reference=多参考输入
            "reason": "auto: R1 高运动模板 fight_exchange（10s/3拍）" }
        ],
        "midframe_exempt_reason": "极短镜 <3s，中帧与首尾几乎重合（三帧契约豁免）"  // 仅 policy.midframe_default=true 且本镜无锚帧时必填
      },
      "shots": [ { "t": "0-4s", "lens": "全景·推镜", "desc": "...", "video_prompt": "...",
                   "entity_schedule": { "characters": ["CHAR_01/常态"], "objects": ["PROP_玉佩"], "locations": ["LOC_冷宫寝殿"] } } ] }
  ]}
```

> **字段权责**：`duration` = 所含镜头时长之和（来自 `镜头时长.json`，配音驱动，勿手填臆造——`validate_timings.py` 会对账 ∑clip.duration ≈ ∑镜头时长）；`firstframe_png`/`endframe_png`/`midframe.midframe_png`/`anchors[].anchor_png` 由 n2d-image 落档回填、`video_out` 由 n2d-video 回填（本 skill 先按命名约定占位）；`anchors` 可由 `scripts/anchor_planner.py` 自动规划（dry-run 报告→人确认→`--write` 注回）；`visual_contract` + `style_contract` + `continuity` + 复杂镜头 `template_contract` 由本 skill 在分镜设计时写死。

---

## 5. 素材清单（脚本/第N集/素材清单.md）— **AI 图片生成输入（简版）**

本集需要出图的所有角色/场景/关键道具，逐条给 prompt：

```markdown
## 角色出图
### CHAR_01 {姓名} @ 本集状态（如：惊醒/战斗）
中文 Prompt：（复用角色卡锚定 + 本集动作表情 + 景别 + 按 `基础视觉风格` 派生的画风词与光色）
英文 Prompt：

## 场景出图
### LOC_01 {场景名}
中文 Prompt：
英文 Prompt：

## 关键道具
### 残烛
中文 Prompt：
英文 Prompt：
```

> 这是 Stage 1 出的**简版清单**——给 Stage 2 作为来源。Stage 2 的 `n2d-image` 会基于此 + 共享库扫描，生成"开箱即用"的两层 prompt 文件夹。

---

## 6. 配音文案（脚本/第N集/voiceover.txt）— 带表演 + 留存标注

按镜头顺序逐条。**情绪/语速/停顿不是注释，会驱动 n2d-voice 的念白表演**；钩子标记落实 `导演节奏.md` 的留存曲线。

**格式**：`[镜头N·角色·情绪·(语速)] 台词  (钩子标记)`

```
[镜头1·沈念·茫然·慢] 这不是……我的寝室。  ⚡钩子
[镜头2·旁白·低沉] 林婉儿，户部侍郎嫡女，三日前暴毙冷宫。
[镜头5·沈念·冷冽·快] 谁害的我，|| 我让她十倍奉还。  💥爽点
[镜头8·沈念·阴狠·慢] 这条命，|| 我自己说了算。  🪝集尾
```

字段说明：
- **情绪**（必填，用具体词）：茫然 / 愤怒 / 惊恐 / 冷冽 / 悲伤 / 窃喜 / 坚定 / 阴狠 / 低沉 / 平静…… → n2d-voice 映射成 TTS 的 emotion + 语速微调。
- **语速**（可选，缺省=常速）：`快`（吵架/逼问/危机/爽点反击）/ `慢`（独白/悲伤/盘算/集尾留悬念）。
- **停顿**：句中用 `||` 标一拍气口（关键反转词前留白制造紧张），n2d-voice 会在该处插入短停顿。
- **钩子标记**（句尾，可选）：`⚡钩子` / `💥爽点` / `🪝集尾`——标出留存曲线节点，供 n2d-voice 微调（爽点重音、集尾拖长尾音）与 n2d-compose 卡点参考。**这些标记是给产线读的，n2d-voice 会从念白文本里剥掉、不会念出来。**

> 兼容旧格式：不写语速/停顿/钩子也能跑（退回按角色默认音色）。但要"导演级留存"，按上面标全。

---

## 7. BGM 与音效（脚本/第N集/bgm.txt）

```
整体情绪：阴森压抑 → 高潮爆发
BGM风格：国风暗黑 / 弦乐渐强 / 低频鼓点
关键音效点：[镜头4 诡异铜铃] [镜头6 重低音心跳] [镜头7 妖气爆裂]
```

---

## 8. 封面 / 首图（脚本/第N集/封面.md）

一张高点击率竖版封面，含本集最大爽点或钩子、主角清晰正脸、强情绪、可叠加标题留白。给中文+英文 prompt。

---

## 9. 字幕（脚本/第N集/字幕_中文.srt [+ 字幕_英文.srt]）— 语言看 `字幕语言` 选择点

**翻译语言是投放选择，不写死**：按 `../skills/n2d/references/选择点与偏好.md` 的 `字幕语言` 选择点决定。**默认 中文-only**（对齐 `skills/n2d/references/选择点与偏好.md` 与 finalize 默认；国内投放只产 `字幕_中文.srt`）；项目显式选 **中英双语 / 仅英文**（海外投放：TikTok / ReelShort / YouTube / 北美短剧）时才产 `字幕_英文.srt`，**与中文同一套时间码**。`字幕_英文.srt` 同时可作海外/复用/英文 prompt 兜底资产。

标准 **SRT** 格式，可直接导入剪辑软件 / 上传平台。下面英文一节仅在选了中英双语 / 仅英文时适用；项目只做中文时无需产英文（如需英文 prompt 兜底可另存译文草稿，不进 `字幕_英文.srt`、不勾 `字幕英`）。

**时间码来源**：把 `voiceover.txt` 的每条台词/旁白，按 `故事板.md` 各 Clip/分镜的累计时长依次排进时间轴；一镜多句则在该镜窗口内平分。实操由 `finalize_storyboard.py` 用 `时长清单.json` 自动重定时产出，不必手算。

**折行宽度**：`finalize_storyboard.py` 折行（中文 `_wrap_zh` 约 19 字/行、英文 `_wrap_en` 约 42 字符/行）只是 SRT 内的参考换行；**最终竖屏排版与是否再折行以渲染端 `n2d-compose/render_subs.py` 的字号/可用宽度为准**。两端宽度若调，需一并对账，避免 SRT 折好的行到 PNG 又被二次折行/溢出。

**英文翻译要点**：口语化、贴短剧语境、长度适配字幕（每行 ≤ 约 42 字符、≤2 行）；保留人名音译统一（沈念 Shen Nian、林婉儿 Lin Wan'er、柳娘子 Madam Liu）；系统提示用游戏化英文（如 "Demon Bloodline activated."）。

```srt
1
00:00:00,000 --> 00:00:03,000
这里……不是我的宿舍。

2
00:00:03,000 --> 00:00:08,000
粗麻、霉味、蛛网……这是哪儿？
```
英文版同一时间码：
```srt
1
00:00:00,000 --> 00:00:03,000
This... isn't my dorm room.

2
00:00:03,000 --> 00:00:08,000
Coarse cloth, mildew, cobwebs... where am I?
```
