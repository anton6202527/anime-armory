# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 6 · 🔴 high 0 · 🟡 medium 19

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 5 | 0 | 72 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 322 | 0 | 78 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 41 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 1 | 0 | 7 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | ⛔ block | 1 | 0 | 14 | detect, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 7 | detect |
| 合规 | 🟡 warn | 0 | 0 | 3 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 5 | 0 | 42 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜2 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜3 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜6 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜7 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜8 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜9 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜10 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大荒碎星戟、周身白气。` 声明至镜1，但镜11 仍保留。 

### 角色问题
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_02（magic_burst）：剪辑峰值钉在 [3.8]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_11（magic_burst）：剪辑峰值钉在 [4.2]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_13（magic_burst）：剪辑峰值钉在 [5.5]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 

### 镜头问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_CHENG_LAO, CHAR_EMPEROR_TANG, CHAR_GARRISON_SURVIVORS, CHAR_JIANG_YUECHU, CHAR_JIANG_YUECHU/战场形态, CHAR_JIANG_YUECHU/静修）但缺 entity_memory_bank；后续镜头无法按已验收
- warn [detect] image_qc_precision: image_qc_precision  None image_qc 精度为 degraded：正式进 video 前需补依赖重跑到 full 精度；普通人审记录只能辅助定位，不能替代 video/compose 前的 full QC gate。 
- warn [detect] scene_consistency: scene_consistency  None 接缝接力 未执行：视觉机检不可用；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。 
- warn [detect] style_consistency: style_consistency  None 风格归属无法机检：style_contract 未登记风格锚（style_anchor）。请在定妆阶段出 1–2 张「冷灰写实3D国风漫剧」风格锚图、登记进 style_contract.style_anchor，后续每集出图帧才能对锚做风格归属佐证。当前降级为人判：逐图核对是否踩 风格禁忌：禁欧美魔幻脸、页游
- block [gate:image_preflight] 参考规划落实 @ 创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/reference_plan_第1集.json: 参考规划落实 逐镜参考规划有 20 条行动项未确认落实（无持久主体 ID 后端×大变化镜 11 镜）：镜头 EP01_CLIP01、EP01_CLIP02、EP01_CLIP03、EP01_CLIP04、EP01_CLIP05、EP01_CLIP06、EP01_CLIP07、EP01_CLIP08…。请按 reference_plan_第1集.md 把补拍/
- warn [gate:image] image_qc_precision: image_qc_precision image_qc 精度为 degraded：正式进 video 前需补依赖重跑到 full 精度；普通人审记录只能辅助定位，不能替代 video/compose 前的 full QC gate。
- warn [gate:image] scene_consistency: scene_consistency 接缝接力 未执行：视觉机检不可用；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。
- warn [gate:image] style_consistency: style_consistency 风格归属无法机检：style_contract 未登记风格锚（style_anchor）。请在定妆阶段出 1–2 张「冷灰写实3D国风漫剧」风格锚图、登记进 style_contract.style_anchor，后续每集出图帧才能对锚做风格归属佐证。当前降级为人判：逐图核对是否踩 风格禁忌：禁欧美魔幻脸、页游高饱和、塑料

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头4·旁白：台词含强情绪但配音标注「压低」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头17·旁白：台词含强情绪但配音标注「硬切」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头34·旁白：台词含强情绪但配音标注「压住」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头16 皇帝下旨] 朝堂钟声一记」→「[镜头35 集尾钩] 面板轻颤、空气」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `镇魔卫` 未进入 storyboard。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `年轻校尉` 未进入 storyboard。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_01 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_09 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_10 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_12 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_13 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/从变身少女开始斩妖除魔/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/从变身少女开始斩妖除魔/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_年轻校尉_断臂校尉.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_年轻校尉_断臂校尉_45度.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_姜月初_战场形态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_姜月初_战场形态_45度.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_姜月初_战场形态_侧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_姜月初_战场形态_背.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_姜月初_战场形态_半身.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_姜月初_战场形态_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · audio:leitmotif_registry.json · 音乐母题(LM1)
  - block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:关键场景] 本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。。如确认为可接受，写入 生产数据/consistency_advisory_si
- block · character: 觉醒蓝调母本 · 跨集成长一致性
  - block [gate:image_preflight] 跨集成长一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/prompt/角色定妆.md ## CHAR_JIANG_YUECHU / 姜月初 / 觉醒蓝调母本: 跨集成长一致性 成长派生形态 `姜月初/觉醒蓝调母本` 的定妆未声明从锚定形态`战场形态` 的正脸/脸部特写 image2image 派生（evolution_profile 渐进升级）。纯文生图重抽新脸=同一个人被换成另一张脸，下游每镜还会忠实继承错脸。请写明：以 `定妆_<角色>_<锚定形态>` 正脸/脸部特写为母图做 image2image 派生，只升
  - block [gate:image] 跨集成长一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/prompt/角色定妆.md ## CHAR_JIANG_YUECHU / 姜月初 / 觉醒蓝调母本: 跨集成长一致性 成长派生形态 `姜月初/觉醒蓝调母本` 的定妆未声明从锚定形态`战场形态` 的正脸/脸部特写 image2image 派生（evolution_profile 渐进升级）。纯文生图重抽新脸=同一个人被换成另一张脸，下游每镜还会忠实继承错脸。请写明：以 `定妆_<角色>_<锚定形态>` 正脸/脸部特写为母图做 image2image 派生，只升
- block · character:00_总览.md · 共享定妆 / 跨集角色定义
  - block [gate:image_preflight] 共享定妆 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/00_总览.md: 共享定妆 本集引用的共享定妆仍有未完成项：| ⬜ | 角色 | `CHAR_JIANG_YUECHU/战场形态` | `出图/共享/图片/定妆_姜月初_战场形态_主参考.jpeg` |
  - warn [gate:image_prompt_preflight] 跨集角色定义 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/00_总览.md: 跨集角色定义 本集出图总览引用了角色「年轻校尉」(CHAR_YOUNG_CAPTAIN)，却未出现其 identity_registry 锚定相任一描述符（二十多岁大唐镇魔卫校尉·断一臂·破损黑铁甲·灰蓝布衣·疲惫感激眼神）——可能跨集重新派生而非复用定妆。请核对本集发型/瞳色/服装/配饰与定妆库一致，并在总览引用锚定相（或角色参考图）以防跨集悄悄变样。
  - warn [gate:image_prompt_preflight] 跨集角色定义 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/00_总览.md: 跨集角色定义 本集出图总览引用了角色「大唐皇帝」(CHAR_EMPEROR_TANG)，却未出现其 identity_registry 锚定相任一描述符（中年大唐皇帝·疲惫威严·玄金龙纹朝服·高位御案后·冷色烛光）——可能跨集重新派生而非复用定妆。请核对本集发型/瞳色/服装/配饰与定妆库一致，并在总览引用锚定相（或角色参考图）以防跨集悄悄变样。
- block · character:01_分镜出图.md ## 镜头 10 — EP01_CLIP10 点睛奖励：化龙经无上 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 10 — EP01_CLIP10 点睛奖励：化龙经无上: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 10 — EP01_CLIP10 点睛奖励：化龙经无上: 角色一致性 多人同框（姜月初_战场形态_主参考.jpeg/赤蛟绘卷虚影）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处方。
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 10 — EP01_CLIP10 点睛奖励：化龙经无上: 角色一致性 单镜多角色同框（姜月初_战场形态_主参考.jpeg/赤蛟绘卷虚影）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；否则分层合成阶段仍会串
- block · character:01_分镜出图.md ## 镜头 11 — 🔑关键镜 EP01_CLIP11 三色龙鳞与龙珠觉醒 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 11 — 🔑关键镜 EP01_CLIP11 三色龙鳞与龙珠觉醒: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 11 — 🔑关键镜 EP01_CLIP11 三色龙鳞与龙珠觉醒: 角色一致性 多人同框（三色龙珠/姜月初_觉醒蓝调_母本.jpeg/尸城破屋）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处方。
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 11 — 🔑关键镜 EP01_CLIP11 三色龙鳞与龙珠觉醒: 角色一致性 单镜多角色同框（三色龙珠/姜月初_觉醒蓝调_母本.jpeg/尸城破屋）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；否则分层合成阶段仍
- block · character:01_分镜出图.md ## 镜头 12 — EP01_CLIP12 系统提示：是否衍化内景 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 12 — EP01_CLIP12 系统提示：是否衍化内景: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 12 — EP01_CLIP12 系统提示：是否衍化内景: 角色一致性 多人同框（姜月初_觉醒蓝调_母本.jpeg/尸城破屋）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处方。
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 12 — EP01_CLIP12 系统提示：是否衍化内景: 角色一致性 单镜多角色同框（姜月初_觉醒蓝调_母本.jpeg/尸城破屋）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；否则分层合成阶段仍会串脸或无
- block · character:01_分镜出图.md ## 镜头 13 — 🔑关键镜 EP01_CLIP13 阴山雾影硬断 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 13 — 🔑关键镜 EP01_CLIP13 阴山雾影硬断: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 13 — 🔑关键镜 EP01_CLIP13 阴山雾影硬断: 角色一致性 多人同框（姜月初_觉醒蓝调_母本.jpeg/姜月初_觉醒蓝调母本）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处方。
  - block [gate:image] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 13 — 🔑关键镜 EP01_CLIP13 阴山雾影硬断: 角色一致性 单镜多角色同框（姜月初_觉醒蓝调_母本.jpeg/姜月初_觉醒蓝调母本）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；否则分层合成阶段
- block · character:01_分镜出图.md ## 镜头 2 — 🔑关键镜 EP01_CLIP02 白气护体与精气洪流 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 2 — 🔑关键镜 EP01_CLIP02 白气护体与精气洪流: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 2 — 🔑关键镜 EP01_CLIP02 白气护体与精气洪流: 角色一致性 多人同框（大荒碎星戟/姜月初_战场形态_主参考.jpeg/巴西郡尸城战场/白气缠绕）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 2 — 🔑关键镜 EP01_CLIP02 白气护体与精气洪流: 角色一致性 单镜多角色同框（大荒碎星戟/姜月初_战场形态_主参考.jpeg/巴西郡尸城战场/白气缠绕）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标
- block · character:01_分镜出图.md ## 镜头 3 — EP01_CLIP03 阴山未成，压下燃灯 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 3 — EP01_CLIP03 阴山未成，压下燃灯: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 3 — EP01_CLIP03 阴山未成，压下燃灯: 角色一致性 多人同框（姜月初_战场形态_主参考.jpeg/巴西郡尸城战场）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处方。
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 3 — EP01_CLIP03 阴山未成，压下燃灯: 角色一致性 单镜多角色同框（姜月初_战场形态_主参考.jpeg/巴西郡尸城战场）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；否则分层合成阶段仍会
- block · character:01_分镜出图.md ## 镜头 8 — EP01_CLIP08 破屋静修，灌注赤鳞妖尊 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 8 — EP01_CLIP08 破屋静修，灌注赤鳞妖尊: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 8 — EP01_CLIP08 破屋静修，灌注赤鳞妖尊: 角色一致性 多人同框（大荒碎星戟/姜月初_战场形态_主参考.jpeg/尸城破屋/赤蛟绘卷虚影）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 8 — EP01_CLIP08 破屋静修，灌注赤鳞妖尊: 角色一致性 单镜多角色同框（大荒碎星戟/姜月初_战场形态_主参考.jpeg/尸城破屋/赤蛟绘卷虚影）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；
- block · character:01_分镜出图.md ## 镜头 9 — EP01_CLIP09 染朱奖励：化龙经圆满 · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 9 — EP01_CLIP09 染朱奖励：化龙经圆满: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 9 — EP01_CLIP09 染朱奖励：化龙经圆满: 角色一致性 多人同框（姜月初_战场形态_主参考.jpeg/赤蛟绘卷虚影）缺 `区分锚点` 字段：同框角色发色/发型/服装主色越接近，越易被模型平均成同一张脸。逐主体写 5–7 个互斥锚点（各自唯一发色/发型/服装主色HEX/标志配饰）并确保两两不撞色；可读 reference_planner 的 `distinct_anchors` 处方。
  - block [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md ## 镜头 9 — EP01_CLIP09 染朱奖励：化龙经圆满: 角色一致性 单镜多角色同框（姜月初_战场形态_主参考.jpeg/赤蛟绘卷虚影）虽登记了分层/合成，但缺 `多人同框身份槽位`。无持久角色 ID 后端必须逐主体写 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位，每个槽位绑定 `CHAR_xx/形态`、画面位置、视线、自己的脸部参考/表情库和 primary 星标；否则分层合成阶段仍会串
- block · character:EP01_CLIP01.png · character_consistency
  - block [detect] character_consistency @ 图片/EP01_CLIP01.png: character_consistency  图片/EP01_CLIP01.png 崩脸 G1 block：图片/EP01_CLIP01.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/EP01_CLIP01.png: character_consistency 崩脸 G1 block：图片/EP01_CLIP01.png（脸/身份漂移机检）

## 依赖传播

- nodes=38 · edges=75 · clips=13 · images=0 · videos=0
- graph: `创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=2

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_JIANG_YUECHU） | character | ⛔ block | 🟢 | ⛔ | 🟢 |
| 年轻校尉（CHAR_YOUNG_CAPTAIN） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 大唐皇帝（CHAR_EMPEROR_TANG） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 程老（CHAR_CHENG_LAO） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 朝堂群臣（CHAR_COURT_MINISTERS） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 巴西郡残兵（CHAR_GARRISON_SURVIVORS） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 巴西郡尸城战场（LOC_BAXI_BATTLEFIELD） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 巴西郡尸城大全景（LOC_BAXI_BATTLEFIELD_ESTABLISH） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 大唐朝堂（LOC_TANG_COURT） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 尸城破屋（LOC_BROKEN_HOUSE） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 姜月初识海/阴山内景（LOC_CONSCIOUSNESS_SEA） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 大荒碎星戟（WEAPON_DAHUANG_HALBERD） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 御案（PROP_IMPERIAL_DESK） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 系统面板光幕（VFX_SYSTEM_PANEL） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 精气洪流（VFX_ESSENCE_STREAMS） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 三色龙珠（VFX_THREE_DRAGON_ORBS） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 阴山雾影（VFX_YINSHAN_MIST） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 巴西郡急报/朝廷信札（PROP_STATE_LETTER） | prop | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 白气缠绕（VFX_WHITE_QI） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 赤蛟绘卷虚影（VFX_RED_FLOOD_DRAGON_SCROLL） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_JIANG_YUECHU）
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大

## 🟡 年轻校尉（CHAR_YOUNG_CAPTAIN）
- [warn]  语义谱系(P0)   配音角色 `年轻校尉` 未进入 storyboard。 
- [warn]  成本路由(K1)   出图/共享/图片/定妆_年轻校尉_断臂校尉.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_年轻校尉_断臂校尉_45度.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 大唐皇帝（CHAR_EMPEROR_TANG）
- [warn]  状态百科(P1)   CHAR_EMPEROR_TANG 在镜1后应保持 `疲惫但威严，不出现战场状态。`，但镜4 prompt 未见状态
- [warn]  状态百科(P1)   CHAR_EMPEROR_TANG 在镜1后应保持 `疲惫但威严，不出现战场状态。`，但镜5 prompt 未见状态
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_CHENG_LAO, CHAR_EMPEROR_TANG, CHAR_GARRIS

## 🟡 程老（CHAR_CHENG_LAO）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_CHENG_LAO, CHAR_EMPEROR_TANG, CHAR_GARRIS
- [warn]  成本路由(K1)   出图/共享/图片/定妆_程老_朝堂常态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模
- [warn]  成本路由(K1)   出图/共享/图片/定妆_程老_朝堂常态_45度.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 朝堂群臣（CHAR_COURT_MINISTERS）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_朝堂群臣_群臣剪影_剪影.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 巴西郡残兵（CHAR_GARRISON_SURVIVORS）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_CHENG_LAO, CHAR_EMPEROR_TANG, CHAR_GARRIS
- [warn]  成本路由(K1)   出图/共享/图片/定妆_巴西郡残兵_残兵剪影_剪影.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 巴西郡尸城战场（LOC_BAXI_BATTLEFIELD）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_巴西郡尸城战场.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 🟡 大荒碎星戟（WEAPON_DAHUANG_HALBERD）
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP01-07 战场形态：玄衣赤氅、右肩暗金凶兽护肩、大

## 🟡 三色龙珠（VFX_THREE_DRAGON_ORBS）
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP11-13 觉醒预备：三色龙鳞、玉色龙角、三色龙珠短
- [warn]  状态百科(P1)   CHAR_JIANG_YUECHU 的状态 `EP01_CLIP11-13 觉醒预备：三色龙鳞、玉色龙角、三色龙珠短

## 未归属到具体角色/资产的一致性问题
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
