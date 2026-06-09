# 视频 prompt 格式（Stage 5）

把 `脚本/第N集/故事板.md` 的 Clip 表派生为**开箱即用**的视频 prompt 文件夹：`出视频/第N集/prompt/`。

---

## 1. 单 Clip prompt 块标准格式

```markdown
## Clip K（时长 Ns · 镜头 N1[+N2]）　**节奏**：铺垫·长镜 / 加速·碎切 / 爽点·CU硬切 / 留白·定格　**张力**：克制 / 紧张 / 爆发 / 释放

**首帧**：`出图/第N集/镜头N1_<描述>.png`
**尾帧**（接力契约 `需要尾帧?=是` 时**必用**，平台支持双帧的走 frames2video）：`出图/第N集/图片/镜头N_end.png`（n2d-image 出的尾帧=下一 Clip 首帧构图）
**场景**：{场景名}（夜晚/内）
**导演意图**：{这一镜在剧情里的功能，不写"画面好看"，写"为什么这样拍"；例如压迫/试探/藏锋/释放/钩子}
**起幅**：{从首帧/上一 Clip 接什么姿态、站位、视线、道具、场景状态开始；首帧已锁死，不重设视觉变量}
**落幅**：{结尾停到哪里，给下一镜接什么；必须服务下一 Clip 入点或可切出的空镜/物件}
**场面调度**：{人物左右站位、前后景关系、轴线方向、视线方向、出入画方向；无人物镜写画面重心与环境运动层次}
**表演节拍**：{按时间段写唯一主动作链，如 [0-2s] 抬眼 [2-5s] 压住呼吸 [5-7s] 定住；空镜则写光/雾/水/符纹节拍}
**专项镜头模板**（复杂镜必填，普通镜写“无”）：{从 `storyboard.json.template_contract` 读取 template_id + beats + blocking + camera_rule + continuity_must + negative + 专属字段；`hug_or_pull` 必写接触点/力量方向/释放帧，`multi_character_same_frame` 必写角色槽位/脸优先级，`ensemble_blocking` 必写站位/焦点层级/人群简化；本 Clip 人物运动/镜头运动/衔接约束必须服从它}
**模型路由**（每 Clip 必填，来自 `video_model_routes.json`）：{shot_type；primary_backend；fallback_backends；mode=image2video|frames2video|text2video|multi_shot；native_audio_policy；identity_requirement；risk_flags；motion_control摘要；rationale；degrade_plan；`生视频AI` 只作普通镜/兜底，不固定每 Clip}
**Motion Control / 物理交互控制**（高危接触镜必填，普通镜写“无”）：{从 `video_model_routes.json.motion_control` 读取 level/manifest_path/required_inputs/failure_modes/gate_policy；若 level=required，manifest 必须 ready 或 degrade_only；ready=pose/depth/instance/contact 控制资产齐，degrade_only=不直接生成全身接触而拆手部/反打/释放帧；ready 控制资产若写远端 uri，必须同时写 scheme=https/s3/gs、verified_at=YYYY-MM-DD、sha256/checksum/etag 之一，裸 uri/file:// 不放行}
**角色身份注册层**（含角色镜必填，普通镜写“无”）：{优先从 `生产数据/identity_adapter_matrix.json` 读取本角色/形态在目标后端的 binding；回溯 `出图/共享/identity_registry.json` 取 registry id、reference_group、高危角度、禁漂项；写明 Character ID / Face Lock / reference controls / LoRA / fallback reference_group 状态}
**原生音画策略**（每 Clip 必填，默认丢弃）：{audio_intent=none|ambience|native_sfx；risk=low|medium|high；mouth_visible=yes|no；speech_policy=no_native_speech；compose_policy=丢弃|低音量混入环境声|保留原片音轨；review=生成后确认无原生人声}
**衔接设计**：
- 入点：{承接上一个 Clip 的动作/视线/声音/空镜}
- 出点：{本 Clip 结束时停住的姿态/视线/道具/画面重心}
- 转场：{match cut / eyeline cut / 动作切 / 空镜缓冲 / 声音先行(J-cut) / 硬切}
- 连贯性：{轴线方向、人物左右站位、出入画方向、首尾帧约束}

**continuity**（必填，自动读取相邻 Clip 派生；缺字段先补，不提交生成）：
- start_state：{从上一 Clip 末尾/本 Clip 首帧承接的人物姿态、站位、视线、道具状态、场景状态}
- action：{本 Clip 内唯一主动作链，幅度可控，不重设人物/场景}
- end_state：{给下一 Clip 承接的结尾姿态、视线方向、画面重心或可切出的物件/空镜}
- constraints：{服装发型、人物左右站位、轴线方向、光线、天气、道具、背景布局保持一致}
- negative：{不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声}

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
\`\`\`
continuity:
  start_state: {start_state}
  action: {action}
  end_state: {end_state}
  constraints: {constraints}
  negative: {negative}
导演意图：{导演意图，一句话，不给模型重画面，只给它理解运动目的};
起幅：{起幅};
落幅：{落幅};
场面调度：{场面调度，尤其轴线/左右站位/画面重心};
表演节拍：{表演节拍};
专项模板约束：{若有 template_contract，写明本 Clip 必须遵守的模板动作/站位/运镜/负向；普通镜写“无”};
模型路由约束：{读取 video_model_routes.json；本镜 primary_backend=...，fallback=...，mode=...，native_audio_policy=...，identity_requirement=...；prompt 只使用 primary 后端真实支持的能力，不能混用其它后端专属能力；失败按 degrade_plan 切 fallback 或拆镜};
物理交互约束：{若 motion_control.level=required，先读取 motion_control_manifest.json；status=ready 时按 pose_sequence/depth_sequence/instance_masks/contact_map 控制资产生成；status=degrade_only 时不直接生成全身复杂接触，按 degrade_plan 拆手部特写/反打/释放帧；禁止只靠文本 prompt 让模型猜两人遮挡、手部归属、武器接触};
身份锁定约束：{读取 identity_adapter_matrix.json + identity_registry.json；若目标后端 binding ready，则写入 Character ID / Face Lock / reference controls / LoRA trigger 等平台参数；否则回退首帧+尾帧+reference_group；保持 drift_forbidden，避开高危角度};
原生音画约束：{默认禁止原生人声；若 audio_intent=ambience/native_sfx，则只允许环境声/动作音效，禁止台词/旁白/哼唱，生成后需确认无原生人声};
人物运动：{角色 A 动作链}；{角色 A 表情变化}；
镜头运动：{推/拉/跟/环绕/固定 + 速度词，如"缓慢推近 0.5x"}；   ← 由"节奏/张力"决定：铺垫=缓慢推/固定，爽点=轻甩/环绕/快推
动态细节：{烛火摇曳 / 晨雾流动 / 衣袂飘动 / 妖气扩散 / 发丝飘动 ...};
衔接约束：开头承接 continuity.start_state，动作只执行 continuity.action，结尾停在 continuity.end_state，保持 continuity.constraints，避开 continuity.negative，按{转场}服务下一镜；
声音约束：无对白、无旁白、不要生成原生人声；若故事板标声音先行，仅作为后期 n2d-compose 的剪辑意图，不让视频模型自行生成台词；
（末尾追加平台风格词，参见 platforms.md）
\`\`\`

### 视频 prompt（英文，目标=安全兜底/Veo/海外）
\`\`\`
continuity:
  start_state: ...
  action: ...
  end_state: ...
  constraints: ...
  negative: ...
director intent: ...;
opening frame state: ...;
ending frame state: ...;
blocking: ...;
performance beats: ...;
character motion: ...;
camera motion: dolly in slowly;
dynamic detail: candle flame flickering, hair strands swaying;
continuity constraint: begin from continuity.start_state, perform only continuity.action, end on continuity.end_state, preserve continuity.constraints, avoid continuity.negative, designed for ... transition;
native audio policy: audio_intent=none by default; for low-risk ambience/native SFX only, allow environmental sound effects but no speech, no narration, no humming, no generated native voice;
\`\`\`

> **中英双 prompt**：中文和英文视频 prompt 默认都写。英文不是只给海外平台；当中文 prompt 被平台安全策略误伤、被自动规避改写，或生成结果明显跑偏时，直接切英文版作为同义兜底。

### 平台参数
- primary_backend / fallback_backends / mode / 模型质量档 / 时长 / 帧率 / 画幅 / image2video 强度 / identity adapter / native_audio_policy

### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
1. ✅ 首帧 PNG 已落档并与 Clip 编号匹配
2. ✅ 导演调度字段：导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍齐全，且都服务剧情，不重定首帧视觉
3. ✅ ④人物运动：动作链明确、幅度可控、可由首帧自然推出
4. ✅ ②镜头运动：推/拉/跟/环绕/固定等词明确，速度词明确，不只写"运镜"
5. ✅ 动态细节：烛火/雨丝/衣袂/雾气/灵光等 ≥1 条，且不改首帧设定
6. ✅ ⑦张力：运镜与"节奏/张力"一致（铺垫缓慢、爽点短促、留白定格）
7. ✅ 衔接设计：入点/出点/转场/轴线方向已从 `故事板.md` 读取，并写进 prompt 的衔接约束
8. ✅ continuity：start_state/action/end_state/constraints/negative 五字段齐全，且已读取上一/下一 Clip 的衔接信息
9. ✅ 模型路由：已读取 `video_model_routes.json`，本镜有 primary/fallback/mode/rationale/degrade_plan，且平台参数只写目标后端支持的能力
10. ✅ Motion Control：高危接触镜已读取 route.motion_control；manifest 为 ready 或 degrade_only；已写 failure_modes，生成后会查 FeatureMelting/特征融化
11. ✅ 原生音画策略：已填 audio_intent/risk/mouth_visible/speech_policy/compose_policy；默认丢弃，只有低风险无口型无台词镜头才 opt-in 环境声/音效；J-cut 只交给 compose，不交给视频模型生成声音
12. ✅ 复杂镜头：已继承 `专项镜头模板`，且人物运动/镜头运动/衔接约束未违反 template_contract
13. ✅ 角色身份注册层：含角色 Clip 已读取 `identity_adapter_matrix.json` + `identity_registry.json`，明确 Character ID/Face Lock/reference controls/LoRA 或 fallback reference_group，且未违反高危角度/禁漂项
14. ✅ 复杂度可控：无超复杂打斗/多人混战；复杂动作已有降级方案

### 自检（生成后逐条过 · 落档闸门）
> 生成后过/重跑判定。筛选宽容：轻微偏差放行，只命中硬伤才重跑或改 prompt。

- [ ] 首帧一致性：开头画面与 `出图/第N集/镜头N1_<描述>.png` 人物脸/服装/场景一致，无明显漂移
- [ ] 人物运动：动作方向正确、幅度自然，无肢体扭曲、脸部抖动、多人脸错乱
- [ ] 镜头运动：符合 prompt 的推/拉/跟/固定等设计，无突兀乱甩或无意义缩放
- [ ] 动态细节：至少 1 个动态细节成立，且没有引入现代物件/文字/logo/水印
- [ ] 导演调度：视频实际完成了本镜导演意图；起幅、落幅、场面调度和表演节拍没有偏离
- [ ] 模型路由：结果符合本镜 primary 后端强项；若连续失败，按 fallback_backends/degrade_plan 重跑，不临场乱换后端
- [ ] Motion Control / FeatureMelting：高危物理接触镜检查手部归属、肢体边界、遮挡顺序、武器/接触点是否漂移；有手脚融合、肢体融化、穿模或人物边界混淆则废料重跑或拆镜
- [ ] 衔接落点：结尾画面能自然接下一 Clip 的首帧/空镜/视线方向；若不能，标记改 prompt、补尾帧或插空镜缓冲
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；若本镜 opt-in 环境声/音效，确认仅为环境底并在总览「原生音画 opt-in 清单」标记；交 n2d-compose 按选择点处理
- [ ] 落档判定：⬜通过落 `出视频/第N集/视频/ClipK_<描述>.mp4` ｜ ⬜进废料重跑 ｜ ⬜改 prompt/拆 Clip 后重跑

### 降级方案
（若 image2video 推不动该动作，怎么改 prompt 或拆 Clip）
```

---

## 2. 故事板 Clip 表 → 视频 prompt 派生规则

`故事板.md` 每段 Clip 包含 1~2 个分镜，每分镜已写了"镜头：景别/距离/机位/运镜"+"画面动态描述"。派生时：

**先做本集导演一致性契约 + 本集基础视觉风格契约，再写单 Clip。** 单条 prompt 只能解决本镜可生成，不能保证整段剪起来像同一场戏、同一风格。生成 `01_clips.md` 前，必须在 `00_总览.md` 写「本集导演一致性契约」和「本集基础视觉风格契约」。

> **契约源在出图，不在这里重发明**：色调 / 光位 / 轴线·视线 / 人物状态 / 景别这些视觉变量，在 `n2d-image` 阶段已经被烤进首帧像素（见 `出图/第N集/prompt/00_总览.md`「本集视觉一致性契约」五字段）。本契约**继承**那一份——主色调=出图色调基线、轴线=出图场景轴线·视线、剧情状态锁=出图角色状态演进表；视频只负责把它们落实到运动/运镜/剪辑，不得与出图侧打架（改了=与首帧冲突=闪烁漂移）。出图侧缺契约时，应回 `n2d-image` 补齐再出视频。
> **基础视觉风格也继承，不重发明**：风格名 / 视觉基调 / 镜头与构图 / 光色策略 / 运动边界 / 风格禁忌来自 `storyboard.json.style_contract` → `出图/第N集/prompt/00_总览.md`「本集基础视觉风格契约」。视频阶段只能把它落实到与首帧相容的运动，不能把首帧改成另一种风格。旧 `cinematic_contract` 仅兼容旧项目。
> **专项镜头模板也继承，不重发明**：`storyboard.json clips[]` 的 `template/template_contract` 是复杂镜头的动作和空间真值源。视频阶段把它转成 `专项镜头模板` 字段、人物运动、镜头运动、衔接约束和降级方案；不得把打斗/追逐/反打/法术/飞行/亲密互动/拥抱拉扯/多人同框/群像站位重新自由发挥。
> **模型路由也继承，不临场乱选**：`video_model_routes.json` 是视频后端选择真值源。默认 `视频模型路由=自动按镜头路由`，打斗/追逐/对话反打/飞行/空镜/法术爆发/亲密互动/拥抱拉扯/多人同框/群像站位按后端能力选 primary/fallback；`生视频AI` 只做普通镜/兜底。逐 Clip prompt 必须把路由表转成 `模型路由` 字段、中文 prompt 的 `模型路由约束` 和平台参数，不得把不同后端专属能力混写。
> **Motion Control 也继承，不靠文本猜物理**：`video_model_routes.json.motion_control` 是复杂物理交互的控制真值源。打斗命中、拥抱、抓腕、拉扯、近距离接触必须有 `motion_control_manifest.json`；ready 才能直接走 pose/depth/instance/contact 控制生成，degrade_only 则必须拆成手部特写、反打、释放帧等可控短镜。OpenPose/DWPose 只锁姿态，遮挡顺序和身体归属还要靠 depth/instance masks/contact_map 或拆镜。
> **资产身份注册层也继承，不重发明**：`出图/共享/identity_registry.json` 是角色/形态身份真值源，`生产数据/identity_adapter_matrix.json` 是可执行视图。视频阶段先读 matrix 确定目标后端是 Character ID / Face Lock / reference controls / LoRA / reference_group fallback，再回 registry 取 `reference_group`、`angle_policy` 和 `drift_forbidden`；不能在视频 prompt 现场凭记忆写临时 ID。
> **原生音画策略也继承选择点，不临场乱开**：默认 `视频原生音轨=丢弃`。只有纯空镜/转场/远景氛围/背身侧脸等低风险镜头可写 `audio_intent=ambience|native_sfx`，并在总览「原生音画 opt-in 清单」列明为什么无口型、无台词、无原生人声风险。

至少包含：

- **主色调**：本集/本段默认色调，哪些色彩或特效只能在指定爽点后出现（如金瞳、妖气、系统光）。
- **镜头语法**：铺垫/对峙/爽点/留白各用什么运镜；禁止无理由乱甩、乱推、随机环绕。
- **轴线**：同场景主要人物左右站位、视线方向、出入画方向；换轴必须有反打/空镜/动作理由。
- **剧情状态锁**：关键状态不能提前泄露，如觉醒前不发光、受伤前无伤、变身前不出现变体。
- **场景状态**：同场景连续 Clip 的灯位、雨雾、门窗方向、道具位置、背景布局如何继承。

`gate.py --stage video` 会阻断缺「本集导演一致性契约」或缺上述字段的出视频流程。

「本集基础视觉风格契约」至少包含：

- **风格名**：来自 `_设置.md` 的 `基础视觉风格`。
- **视觉基调**：该风格的角色比例、材质/线条、画面密度和整体质感。
- **镜头与构图**：该风格下可用的景别、透视、留白、剪影或线稿纪律。
- **光色策略**：主色 + 强调色 + 强调色出现时机。
- **运动边界**：与风格相容的推/拉/跟/固定/弹性运动；禁止无理由乱甩和随机变风格。
- **风格禁忌**：随所选风格派生。写实电影感可禁插画化/游戏CG；二次元赛璐璐不应禁“插画感”，而应禁照片皮肤/3D塑料/风格跳变。

`gate.py --stage video` 会阻断缺「本集基础视觉风格契约」或缺上述字段的出视频流程。

| 故事板字段 | 视频 prompt 哪里用 |
|---|---|
| 时长 | "时长 Ns"（标题）+ 平台参数 |
| 场景名 | "场景"行 |
| 本段剧情功能 / 钩子 / 爽点位置 | "导演意图"；先说明这一镜为什么存在，再写动作 |
| 上一 Clip 末帧 / 本 Clip 首帧 | "起幅"；必须承接首帧，不重新发明姿态/站位/状态 |
| 下一 Clip 入点 / 接缝契约 | "落幅"；必须服务下一镜，不能只让本镜好看 |
| 轴线 / 左右站位 / 前后景 | "场面调度"；锁人物空间关系和画面重心 |
| 配音时长 / 情绪停顿 / 动作链 | "表演节拍"；用 [0-2s] 这类时间段写可执行的表演 |
| `template/template_contract`（复杂镜头） | "专项镜头模板"字段 + 人物运动/镜头运动/衔接约束/降级方案；不从零写复杂动作 |
| `video_model_routes.json`（模型适配层） | "模型路由"字段 + 中文 prompt 的"模型路由约束" + 平台参数里的 primary/fallback/mode/identity adapter/native_audio_policy；不固定一个视频模型 |
| `video_model_routes.json.motion_control` + `control/Clip_XX/motion_control_manifest.json`（复杂物理交互） | "Motion Control / 物理交互控制"字段 + 中文 prompt 的"物理交互约束" + 生成后 FeatureMelting 自检；ready 走控制资产，degrade_only 走拆镜 |
| `identity_adapter_matrix.json` + `identity_registry.json`（角色/形态） | "角色身份注册层"字段 + 中文 prompt 的"身份锁定约束" + 平台参数里的 Character ID/Face Lock/reference controls/LoRA；无注册则 fallback reference_group |
| `视频原生音轨` 选择点 / 低风险声音意图 | "原生音画策略"字段 + 中文 prompt 的"原生音画约束" + `00_总览.md`「原生音画 opt-in 清单」；compose 阶段按 `丢弃/低音量混入环境声/保留原片音轨` 处理 |
| **节奏注记**（铺垫/加速/爽点/留白） | 标题"节奏"+ 决定运镜速度（铺垫=缓慢/固定，爽点=快推/轻甩，留白=固定定格） |
| **衔接设计**（入点/出点/转场/连贯性） | "衔接设计"块 + prompt 里的"衔接约束"；决定是否要尾帧、空镜缓冲、按场景分批或后期 J-cut |
| 上一 Clip 的出点/下一 Clip 的入点 | `continuity.start_state` / `continuity.end_state`；自动读取相邻 Clip，缺失时按首帧、尾帧、视线方向、动作完成前后一拍推断 |
| 分镜 N 的镜头·景别/机位/运镜 | "镜头运动"行（多分镜则按顺序拼成镜头运动链）|
| 分镜 N 的人物动作 | `continuity.action` + "人物运动"行；只保留一个主动作链，避免模型额外发挥 |
| 分镜 N 的动态细节（烛火/雾气等） | "动态细节"行 |
| 角色/场景/首帧约束 | `continuity.constraints` / `continuity.negative`；固定服装发型、轴线、站位、光线、道具、背景，禁止换脸换衣新增人物改场景 |

**张力 → 运镜映射**（`导演节奏.md §四/§五`）：

| 张力 | 情绪 | 运镜 | 节奏注记多为 |
|---|---|---|---|
| 克制 | 压迫/克制/铺垫 | 固定 或 极缓推近 | 铺垫·长镜 |
| 紧张 | 逼近/对峙/危机 | 缓推 / 跟拍 | 加速·碎切 |
| 爆发 | 爽点/反转/觉醒 | 快推 + 轻甩 / 环绕（高光） | 爽点·CU硬切 |
| 释放 | 收尾/孤独/喘息 | 缓拉远 / 固定定格 | 留白·定格 |

**关键转写动作**：
- 把"全景·推镜" → "镜头运动：缓慢推近"
- 把"惊醒坐起" → "人物运动：从平躺到坐起，双眼骤然睁开"
- 把"烛火摇曳" → "动态细节：烛火左右摇曳幅度 1cm"

**多分镜合段时**：在"人物运动"和"镜头运动"里分别按时间顺序串成两条链，比如：
```
人物运动：[0-2s] 平卧 → 惊醒坐起；[2-4s] 环顾四周；[4-7s] 跌跌撞撞下床走向铜镜；
镜头运动：[0-2s] 固定全景 → [2-4s] 缓慢推近 → [4-7s] 跟随角色低角度移动；
```

**衔接设计转写**：
- `转场=match cut / 动作切`：prompt 末尾写清"结尾停在动作完成前一拍/完成后一拍"，并优先设置尾帧。
- `转场=eyeline cut`：prompt 写清人物视线方向（看向画右/画左/镜头外上方），下一 Clip 首帧要承接被看的对象或反打。
- `转场=空镜缓冲`：本 Clip 出点写成可切出的物件/环境动态；若故事板已有独立空镜 Clip，视频生成时按场景/段落分批，不跳过空镜。
- `转场=声音先行(J-cut)`：视频 prompt 仍禁止原生人声，只在 `00_总览.md` 标注给 n2d-compose；正面说话特写不使用 J-cut，避免口型错位。
- `转场=硬切`：仅用于爽点/反转/惊吓；必须有明确的情绪理由，不能作为默认省事转场。

**continuity 自动派生规则**：
- `start_state`：优先取上一 Clip 的 `end_state`；若无上一 Clip，取本 Clip 首帧描述 + 入点。
- `action`：取本 Clip 人物动作主链，删掉"换场景/换衣/新增人物/大幅复杂动作"等会破坏连续性的内容。
- `end_state`：优先服务下一 Clip 的入点/首帧；若下一 Clip 是反打/空镜，结尾停在视线方向、手部道具、门帘、烛火等可切出的画面重心。**接力契约 `需要尾帧?=是` 时，end_state 必须与 n2d-image 出的 `镜头N_end.png` 尾帧一致，并把它设为本 Clip 尾帧做双帧引导。**
- `constraints`：从同场景连续 Clip 继承服装发型、人物左右站位、轴线、视线方向、光线、天气、道具、背景布局；场景切换时只继承角色定妆和道具状态。
- `negative`：默认写入"不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声"；按镜头风险追加"不要手指变形/不要多人脸错乱/不要大幅旋转镜头"。

---

## 3. `00_总览.md` 必含字段

- 本集 Clip 总数 + 总时长（应与故事板一致）
- **本集导演一致性契约**：主色调 / 镜头语法 / 轴线 / 剧情状态锁 / 场景状态（缺任一项，`gate.py --stage video` 阻断）
- **本集资产身份速查**：本集入镜角色/形态 registry id、目标视频后端角色身份状态、fallback reference_group、高危角度、禁漂项（缺 `identity_registry.json` 或字段不全，`gate.py --stage video` 阻断）
- **本集身份 Adapter Matrix 摘要**：本集入镜角色在 primary/fallback 后端的 Character ID / Face Lock / reference controls / LoRA / reference_group binding；来自 `生产数据/identity_adapter_matrix.json`
- **本集模型路由表**：逐 Clip 写 shot_type、primary_backend、fallback_backends、mode、native_audio_policy、identity_requirement、risk_flags、degrade_plan（缺则 `gate.py --stage video` 阻断）
- **本集 Motion Control 清单**：仅高危物理交互镜必填；逐 Clip 写 level、manifest_path、status=ready|degrade_only、required_inputs、failure_modes、degrade_plan。缺 ready/degrade_only manifest 时 `gate.py --stage video` 阻断。
- **原生音画 opt-in 清单**：仅当本集有 `audio_intent=ambience|native_sfx` 或 `_设置.md 视频原生音轨 != 丢弃` 时必填；逐 Clip 写 audio_intent、低风险理由、mouth_visible、speech_policy、compose_policy、生成后审查结论
- 进度（已完成 / 总数）
- 每 Clip 状态表（Clip K | 时长 | 首帧 | 尾帧 | 转场 | J-cut | 空镜缓冲 | 状态 ✅/⏳/⬜ | 落档路径）
- 首帧 PNG 来源速查（对应 Stage 4 的 `出图/第N集/镜头N_*.png`）
- 已知降级（如 Clip 3 image2video 跑不稳，改成 Clip3a/3b 两短段）

## 3.1 检查清单强制要求

每个 Clip prompt 块必须同时包含两段检查，保持与 n2d-image 的"出图前八维自查 + 生成后落档闸门"同级严谨：

- `导演意图 / 起幅 / 落幅 / 场面调度 / 表演节拍`：五个导演调度字段缺一不可。它们负责把 prompt 从"动作说明"升级成"可剪辑的镜头调度"。
- `检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）`：提交前检查 prompt 是否合格。
- `自检（生成后逐条过 · 落档闸门）`：生成后检查视频是否通过、进废料重跑，或改 prompt/拆 Clip。

只写一个泛化 checklist 不合格；缺导演调度字段或任一检查段，都要先补齐再提交视频生成。

---

## 4. 文生视频 vs 图生视频判定

| 镜头类型 | 用哪种 | 理由 |
|---|---|---|
| 主角出场、对话、动作戏 | **图生视频** | 一致性必须靠首帧锁脸 |
| 反派揭面、形态变化 | **图生视频** | 同上，首帧 = Stage 4 该形态定妆图 |
| 纯空镜（蛛网特写 / 残烛 / 风吹）| **文生视频** | 无人物，省一步 |
| 转场（白光闪过 / 黑屏过渡）| **文生视频** | 同上 |
| 氛围镜头（远景城池 / 山雨欲来）| **文生视频** | 无人物或人物极远 |

文生视频 Clip 在本集 `出视频/第N集/prompt/01_clips.md` 标注：`**模式**：文生视频（无首帧）`

---

## 打斗类 Clip（命中/招式）

> 含武打/法术的 Clip 按 `n2d-script/references/打斗分镜.md` 工艺。要点：

- **命中类 clip 必用首尾帧**（起手帧 → 命中帧），让 AI 只做帧间插值，不自由编动作。
- 人物运动写**"力链"**（拧腰 → 送肩 → 沉肘 → 出掌/出剑），不是"打一拳"。
- 命中给**慢镜/子弹时间**；特效写**轨迹方向**（如"青色剑气自右下向左上飞出、拖光尾"）。
- 复杂招式**降级拆**成"起手 clip + 命中 clip"两短段。
- 详见 `n2d-script/references/打斗分镜.md`（§七 落地速查、§九 示例 9.3）。

---

## 仙侠场面类 Clip（御剑飞行/追逐/渡劫/炼丹/法阵/大场面/斗法对轰/神魂）

> 含这些仙侠奇观的 Clip 按 `n2d-script/references/仙侠场面分镜.md` 工艺。要点：

- **飞行/追逐 = 锁姿态、动背景**（最值钱一条）：人物姿态几乎不变（一动就崩），prompt 写"**人物姿态保持/原地跑动循环；云层/山河/前景遮挡物向后高速流动；镜头侧向跟飞 or 跟拍；衣袂剑穗发丝向后疾飘 + 速度线**"。速度感来自背景与镜头，不来自人物变形。机动镜（俯冲/转向）才让人物小幅动，且用镜头同步运动掩护。
- **追逐**用正反打（追者镜↔逃者镜）+ 轴线一致，靠剪辑制造距离递进；别一镜两人追。
- **渡劫雷击**用首尾帧（雷蓄于云 → 雷柱触体），人物锁姿态承受，雷光/闪烁交给特效后期。
- **炼丹/法阵/突破**爆发镜给受控运动：开炉=炉盖掀飞+成丹升起旋光；激活=符文连缀+光柱起；突破=光柱上升+缓抬头。
- **大场面 establish** 用慢运镜（航拍缓降/缓摇/缓推），人物极远或入画，不要求一镜内既恢弘又细节全清。
- **斗法对轰**：撞点镜用首尾帧（相撞→撞点偏移）锁能量走向；放招人锁顶法姿态、只动光效。
- **神魂**：元神升起用首尾帧（肉身→元神升起）；"二我"锁两者姿态、只动半透明度/光；夺舍扑入用首尾帧。
- 复杂奇观**降级拆**成"起手 clip + 爆发 clip"两短段。
- 详见 `n2d-script/references/仙侠场面分镜.md`（各节"视频要点" + §九 落地速查）。

---

## 5. 进度表新增列

Stage 5 第一次跑时，往 `_进度.md` 表头追加 `视频prompt` + `视频` 两列：

```
| ... | 出图prompt | 出图 | 视频prompt | 视频 |
| 第K集 | ✅ | ✅ | 16/16 | ✅ | 4/8 |
```

- `视频prompt` ✅ / ⬜：本集 `出视频/第N集/prompt/` 全套写完
- `视频`：`已完成 MP4 / 本集 Clip 总数`
数`
