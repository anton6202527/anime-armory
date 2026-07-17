# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 6 · 🔴 high 0 · 🟡 medium 16

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 1 | 0 | 5 | detect, gate:image_preflight |
| 角色 | ⛔ block | 43 | 0 | 63 | detect, gate:image_preflight, gate:image_prompt_preflight |
| 资产 | ⛔ block | 25 | 0 | 24 | detect, gate:image_preflight, gate:image_prompt_preflight |
| 镜头 | ⛔ block | 13 | 0 | 38 | detect, gate:image_preflight, gate:image_prompt_preflight |
| 音频 | 🟡 warn | 0 | 0 | 18 | detect, gate:image_preflight, gate:image_prompt_preflight |
| 字幕 | 🟡 warn | 0 | 0 | 9 | detect |
| 合规 | ⛔ block | 3 | 0 | 3 | detect, gate:image_preflight, gate:image_prompt_preflight, compliance |
| 生产操作 | ⛔ block | 21 | 0 | 69 | detect, gate:image_preflight, gate:image_prompt_preflight, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 4 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05），疑节奏塌·掉留存
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 7 个长镜聚集（EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11→EP01_CLIP12→EP01_CLIP13），疑节奏塌·掉留存
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 13 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。
- block [gate:image_preflight] 跨集记忆锚落实 @ 创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/memory_anchor_plan_第1集.json: 跨集记忆锚落实 memory_anchor_plan 的 registry/drift/storyboard 输入指纹缺失或已过期。
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子

### 角色问题
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_08：角色 CHAR_01 相邻镜情绪硬跳（惧→惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_08：角色 CHAR_02 相邻镜情绪硬跳（惧→惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_08：角色 CHAR_04 相邻镜情绪硬跳（惧→惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_09：角色 CHAR_01 相邻镜情绪硬跳（惊→惧）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_09：角色 CHAR_04 相邻镜情绪硬跳（惊→惧）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。
- block [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   identity_eval_pack 缺当前 identity_registry_sha256 或指纹已过期；定妆/形态/档位改动后必须重建验收包。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_01__常态_脸部特写_脸锚裁切.png 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=040107f474ef7d65，但复跑审计证据不完整。

### 资产问题
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。

### 镜头问题
- warn [detect] 空间站位(B1): 入出画 空间站位(B1)   入出画 站位/遮挡与同场景首镜冲突：right/front → None/back（疑重新调度·交人判）
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/反噬跪地态, CHAR_01/囚途染血态, CHAR_01/囚途残损态, CHAR_01__, CHAR_01__常态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场.png 生成事件缺配方字段：mode, seed/seed_degrade, declared_recipe_hash；已可推导 hash=cb1d93b4af3643de，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场_反打.png 生成事件缺配方字段：mode, seed/seed_degrade, declared_recipe_hash；已可推导 hash=47be6e3dc967b7f2，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场_平面图.png 生成事件缺配方字段：mode, seed/seed_degrade, declared_recipe_hash；已可推导 hash=12fb32ec9cfcfd15，但复跑审计证据不完整。
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 LOC_01 本集出现 13 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场_反打.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头12·虎山神：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头16·系统：台词含强情绪但配音标注「中性清晰」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头18·姜月初：台词含强情绪但配音标注「急促盘算」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头22·系统：台词含强情绪但配音标注「中性清晰」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头28·系统：台词含强情绪但配音标注「中性清晰」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「镜头13：裴长青强行起身时心跳加速；」→「镜头20–22：姜月初“抱歉”后留 」；调性/速度whiplash，加渐变过渡或确认是卡点切。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   voiceover 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=d4ae5893ec01d6f3，但复跑审计证据不完整。
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   voiceover 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_vers

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_06 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_09 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_10 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_11 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_12 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/从变身少女开始斩妖除魔/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- block [gate:image_preflight] 生图AI一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/_设置.md: 生图AI一致性 全项目生图优先 Codex / GPT Image 2；非 Codex/OpenAI 图片后端必须先由用户明确签核，并写 合规/image_backend_override.json 后才能付费出图。当前：Dreamina/即梦官方 CLI
- block [gate:image_preflight] 生图AI一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/production_events.jsonl: 生图AI一致性 全项目生图优先 Codex / GPT Image 2；非 Codex/OpenAI 图片后端必须先由用户明确签核，并写 合规/image_backend_override.json 后才能付费出图。当前：dreamina_official_cli
- block [gate:image_preflight] 生图AI一致性 @ 创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/production_events.jsonl: 生图AI一致性 全项目生图优先 Codex / GPT Image 2；非 Codex/OpenAI 图片后端必须先由用户明确签核，并写 合规/image_backend_override.json 后才能付费出图。当前：dreamina_official_cli
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/从变身少女开始斩妖除魔/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__常态 锚点门(N3)
- warn [detect] 锚点门(N3): CHAR_02__常态 锚点门(N3)
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_01__常态_三视图.png 生成事件缺配方字段：mode, seed/seed_degrade, declared_recipe_hash；已可推导 hash=f5b496c0d906abf9，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_01__常态_45度.png 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=3e1a562d674815e6，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_01__常态_侧.png 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=2993309ff8a10dff，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_01__常态_后45度.png 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=4f136afc514b10d5，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_01__常态_背.png 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=f16d9440844cf463，但复跑审计证据不完整。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   出图/共享/图片/定妆_CHAR_02__常态.png 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=2e51c7d38ec1b052，但复跑审计证据不完整。

## 根因聚合

- block · asset:PROP_断刀 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ PROP_断刀: 预防式合同 reference_slot_gate: 道具/场景 PROP_断刀 引用槽位未绑定真实产物：出图/共享/图片/定妆_道具_断刀_手持.png 不存在；出图/共享/图片/定妆_道具_断刀_手持.png 不存在；出图/共享/图片/定妆_道具_断刀_比例.png 不存在
- block · asset:PROP_横刀 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ PROP_横刀: 预防式合同 reference_slot_gate: 道具/场景 PROP_横刀 引用槽位未绑定真实产物：出图/共享/图片/定妆_武器_横刀_手持.png 不存在；出图/共享/图片/定妆_武器_横刀_手持.png 不存在；出图/共享/图片/定妆_武器_横刀_比例.png 不存在
- block · asset:PROP_翻覆囚车 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ PROP_翻覆囚车: 预防式合同 reference_slot_gate: 道具/场景 PROP_翻覆囚车 引用槽位未绑定真实产物：出图/共享/图片/定妆_道具_翻覆囚车.png 不存在；出图/共享/图片/定妆_道具_翻覆囚车_手持.png 不存在；出图/共享/图片/定妆_道具_翻覆囚车_手持.png 不存在
- block · asset:PROP_虎首 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ PROP_虎首: 预防式合同 reference_slot_gate: 道具/场景 PROP_虎首 引用槽位未绑定真实产物：出图/共享/图片/定妆_道具_虎首.png 不存在；出图/共享/图片/定妆_道具_虎首_手持.png 不存在；出图/共享/图片/定妆_道具_虎首_手持.png 不存在
- block · asset:VFX_百妖谱 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ VFX_百妖谱: 预防式合同 reference_slot_gate: 道具/场景 VFX_百妖谱 引用槽位未绑定真实产物：出图/共享/图片/定妆_特效_百妖谱.png 不存在；出图/共享/图片/定妆_特效_百妖谱.png 不存在；出图/共享/图片/定妆_特效_百妖谱.png 不存在
- block · asset:VFX_系统面板 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ VFX_系统面板: 预防式合同 reference_slot_gate: 道具/场景 VFX_系统面板 引用槽位未绑定真实产物：出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 不存在；出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 不存在；出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 不存在
- block · asset:VFX_道行反噬 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ VFX_道行反噬: 预防式合同 reference_slot_gate: 道具/场景 VFX_道行反噬 引用槽位未绑定真实产物：出图/共享/图片/定妆_特效_道行反噬.png 不存在；出图/共享/图片/定妆_特效_道行反噬.png 不存在；出图/共享/图片/定妆_特效_道行反噬.png 不存在
- block · asset:VFX_道行灌注 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ VFX_道行灌注: 预防式合同 reference_slot_gate: 道具/场景 VFX_道行灌注 引用槽位未绑定真实产物：出图/共享/图片/定妆_特效_道行灌注.png 不存在；出图/共享/图片/定妆_特效_道行灌注.png 不存在；出图/共享/图片/定妆_特效_道行灌注.png 不存在
- block · asset:VFX_黑妖血 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ VFX_黑妖血: 预防式合同 reference_slot_gate: 道具/场景 VFX_黑妖血 引用槽位未绑定真实产物：出图/共享/图片/定妆_特效_黑妖血.png 不存在；出图/共享/图片/定妆_特效_黑妖血.png 不存在；出图/共享/图片/定妆_特效_黑妖血.png 不存在
- block · asset:WEAPON_01 · 共享定妆 / image prompt compiler
  - block [gate:image_preflight] 共享定妆 @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/第1集/prompt/01_分镜出图.md: 共享定妆 本集逐镜引用了未过落档自检的共享定妆/资产 `WEAPON_01`（registry `self_check_passed=false`）——脏定妆是锚点，脸/结构漂了下游每镜继承；先过自检并把该项置 true（或人工复核后 `image_qc --mark-finalized`），再付费出图。
  - block [gate:image_preflight] image prompt compiler @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/prompt/道具定妆.md ## 横刀（`WEAPON_01`）: image prompt compiler 共享资产编译图片请求结构错误：compiled_backend_mismatch:codex!=dreamina。请重新运行 n2d-image image_prompt_pack.py，完整合同不得直接提交。
  - warn [gate:image_preflight] image prompt compiler @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/prompt/道具定妆.md ## 横刀（`WEAPON_01`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16
- block · asset:asset · 结构化交互图谱(I2) / 生成配方(RCP) / 系统面板(UI1)
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
  - block [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block · asset:特效定妆.md ## 百妖谱金色古卷面板（`VFX_系统面板`） · image prompt compiler
  - block [gate:image_preflight] image prompt compiler @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/prompt/特效定妆.md ## 百妖谱金色古卷面板（`VFX_系统面板`）: image prompt compiler 共享资产编译图片请求结构错误：compiled_backend_mismatch:codex!=dreamina。请重新运行 n2d-image image_prompt_pack.py，完整合同不得直接提交。
  - warn [gate:image_preflight] image prompt compiler @ 创作区/制漫剧/从变身少女开始斩妖除魔/出图/共享/prompt/特效定妆.md ## 百妖谱金色古卷面板（`VFX_系统面板`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:27>16

## 依赖传播

- nodes=31 · edges=68 · clips=13 · images=0 · videos=0
- graph: `创作区/制漫剧/从变身少女开始斩妖除魔/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=7

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎山神（CHAR_04） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 荒野押解/虎妖现场（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（PROP_横刀） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 断刀（PROP_断刀） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 翻覆囚车（PROP_翻覆囚车） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 百妖谱（VFX_百妖谱） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 道行灌注（VFX_道行灌注） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎首（PROP_虎首） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 黑妖血（VFX_黑妖血） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 道行反噬（VFX_道行反噬） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__常态 锚点门(N3)
- [warn]  配音情绪弧(VEA)   镜头18·姜月初：台词含强情绪但配音标注「急促盘算」归平淡(neutral)——配音会念平、情绪跟不上画面；改标
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「镜头13：裴长青强行起身时心跳加速；」→「镜头20–22：

## 🟡 裴长青（CHAR_02）
- [warn] CHAR_02__常态 锚点门(N3)
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「镜头13：裴长青强行起身时心跳加速；」→「镜头20–22：
- [warn]  表情连续(EXP1)   Clip_08：角色 CHAR_02 相邻镜情绪硬跳（惧→惊）——确认有节拍/事件依据，否则表演 OOC（情绪没

## 🟡 虎山神（CHAR_04）
- [warn]  配音情绪弧(VEA)   镜头12·虎山神：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标
- [warn]  表情连续(EXP1)   Clip_08：角色 CHAR_04 相邻镜情绪硬跳（惧→惊）——确认有节拍/事件依据，否则表演 OOC（情绪没
- [warn]  表情连续(EXP1)   Clip_09：角色 CHAR_04 相邻镜情绪硬跳（惊→惧）——确认有节拍/事件依据，否则表演 OOC（情绪没

## 🟡 荒野押解/虎妖现场（LOC_01）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场.png 生成事件缺配方字段：mode, seed/seed_de
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场_反打.png 生成事件缺配方字段：mode, seed/seed
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_场景_荒野押解_虎妖现场_平面图.png 生成事件缺配方字段：mode, seed/see

## 🟡 横刀（WEAPON_01）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_武器_横刀.png 生成事件缺配方字段：mode, seed/seed_degrade,
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_武器_横刀.png 强配方 schema 缺字段：prompt_sha256,
- [warn]  成本路由(K1)   出图/共享/图片/定妆_武器_横刀.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 🟡 横刀（PROP_横刀）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_武器_横刀.png 生成事件缺配方字段：mode, seed/seed_degrade,
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_武器_横刀.png 强配方 schema 缺字段：prompt_sha256,
- [warn]  成本路由(K1)   出图/共享/图片/定妆_武器_横刀.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 🟡 断刀（PROP_断刀）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_道具_断刀.png 生成事件缺配方字段：mode, seed/seed_degrade,
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_道具_断刀.png 强配方 schema 缺字段：prompt_sha256,

## 🟡 翻覆囚车（PROP_翻覆囚车）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_道具_翻覆囚车.png 生成事件缺配方字段：mode, seed/seed_degrade
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_道具_翻覆囚车.png 强配方 schema 缺字段：prompt_sha25

## 🟡 百妖谱金色古卷面板（VFX_系统面板）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 生成事件缺配方字段：mode, seed/seed_de
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 强配方 schema 缺字段：prompt_

## 🟡 百妖谱（VFX_百妖谱）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 生成事件缺配方字段：mode, seed/seed_de
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_特效_百妖谱.png 生成事件缺配方字段：mode, seed/seed_degrade,
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_特效_百妖谱金色古卷面板.png 强配方 schema 缺字段：prompt_

## 🟡 道行灌注（VFX_道行灌注）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_特效_道行灌注.png 生成事件缺配方字段：mode, seed/seed_degrade
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_特效_道行灌注.png 强配方 schema 缺字段：prompt_sha25

## 🟡 虎首（PROP_虎首）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_道具_虎首.png 生成事件缺配方字段：mode, seed/seed_degrade,
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_道具_虎首.png 强配方 schema 缺字段：prompt_sha256,

## 🟡 黑妖血（VFX_黑妖血）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_特效_黑妖血.png 生成事件缺配方字段：mode, seed/seed_degrade,
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_特效_黑妖血.png 强配方 schema 缺字段：prompt_sha256

## 🟡 道行反噬（VFX_道行反噬）
- [warn]  生成配方(RCP)   出图/共享/图片/定妆_特效_道行反噬.png 生成事件缺配方字段：mode, seed/seed_degrade
- [warn]  强配方Schema(RCP2)   出图/共享/图片/定妆_特效_道行反噬.png 强配方 schema 缺字段：prompt_sha25

## 未归属到具体角色/资产的一致性问题
- [warn] 入出画 空间站位(B1)   入出画 站位/遮挡与同场景首镜冲突：right/front → None/back（疑重新调度·交人判）
- [warn]  配音情绪弧(VEA)   镜头16·系统：台词含强情绪但配音标注「中性清晰」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  配音情绪弧(VEA)   镜头22·系统：台词含强情绪但配音标注「中性清晰」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  配音情绪弧(VEA)   镜头28·系统：台词含强情绪但配音标注「中性清晰」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。
- [warn]  节奏密度(Rhythm)   连续 4 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CL
- [warn]  节奏密度(Rhythm)   连续 7 个长镜聚集（EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CL
- [warn]  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / s

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
