# 验收总账 · 第3集

- 验收状态：阻断
- ⛔ block 9 · 🔴 high 0 · 🟡 medium 8

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 5 | 0 | 13 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 角色 | ⛔ block | 132 | 0 | 88 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | ⛔ block | 19 | 0 | 20 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 54 | 0 | 40 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 14 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | ⛔ block | 4 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 32 | 0 | 24 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 4 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CLIP04），疑节奏塌·掉留存 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 3 个长镜聚集（EP03_CLIP06→EP03_CLIP07→EP03_CLIP08），疑节奏塌·掉留存 
- warn [detect] 视线状态回读(X2):  视线状态回读(X2)   8 个视线/状态高风险镜当前 image_qc 精度为 degraded；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 8 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第3集/storyboard.json 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=9a580ba381d6d64a，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第3集/storyboard.json 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第3集/storyboard.json 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 角色问题
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)  分数比 floor 低≥0.6：更像头部区几何裁切没裁到头（大远景/群像裁到景物），非发型漂移——请并排人判；若确为裁切失真可忽略。  
- warn [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)  分数比 floor 低≥0.6：更像头部区几何裁切没裁到头（大远景/群像裁到景物），非发型漂移——请并排人判；若确为裁切失真可忽略。  
- warn [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)  分数比 floor 低≥0.6：更像头部区几何裁切没裁到头（大远景/群像裁到景物），非发型漂移——请并排人判；若确为裁切失真可忽略。  
- warn [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)    

### 资产问题
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集色调/光位漂移 L1=0.7437（vs 前 2 集基线，阈 warn=0.45·core block=0.8）——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集结构漂移 dHash 汉明=19（vs 前 2 集结构原型，阈 warn=18·core block=26）——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。
- warn [detect] 景深一致(DOF1):  景深一致(DOF1)   图片/EP03_CLIP06_a3.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比 1.126 vs 场景中位 0.73）；同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。 
- warn [detect] 景深一致(DOF1):  景深一致(DOF1)   图片/Clip02_first.png：景深档与同场景其它镜不一致——本镜偏浅景深(背景偏糊)（景深比 0.746 vs 场景中位 1.079）；同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/镇魔司制服态, CHAR_01__, CHAR_01__囚途残损态, CHAR_02, CHAR_02与飞鹰门众）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 LOC_02 本集出现 6 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。 
- warn [detect] image_qc_precision: image_qc_precision  None image_qc 精度为 degraded：正式进 video 前需补依赖重跑到 full 精度；普通人审记录只能辅助定位，不能替代 video/compose 前的 full QC gate。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头2·姜月初：台词含强情绪但配音标注「错愕心虚」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头12·陈青源：台词含强情绪但配音标注「急切恭敬」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音色声纹 @ voicemap:飞鹰门众人:  音色声纹   角色「飞鹰门众人」未在 voicemap 登记：渲染将走内置兜底猜测，跨集音色不稳。先在 设定库/voicemap.json 登记其音色键再配音。 
- warn [detect] 音色声纹 @ voicemap:陈青源:  音色声纹   角色「陈青源」未在 voicemap 登记：渲染将走内置兜底猜测，跨集音色不稳。先在 设定库/voicemap.json 登记其音色键再配音。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `飞鹰门众人` 未进入 storyboard。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第3集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=2b039e84f9118338，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第3集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第3集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- block [gate:image_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 CHAR_03 缺肖像/角色授权记录
- block [gate:image_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 GROUP_01 缺肖像/角色授权记录
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- block [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 CHAR_03 缺肖像/角色授权记录
- block [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 GROUP_01 缺肖像/角色授权记录
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- block [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)    
- block [detect] 天气时辰(W1):  天气时辰(W1)    

## 根因聚合

- block · asset:PROP_镇魔司制服 · 预防式合同
  - block [gate:image_preflight] 预防式合同 @ PROP_镇魔司制服: 预防式合同 reference_slot_gate: 道具/场景 PROP_镇魔司制服 引用槽位未绑定真实产物：出图/共享/图片/定妆_道具_镇魔司制服.png 不存在；出图/共享/图片/定妆_道具_镇魔司制服.png 不存在；出图/共享/图片/定妆_道具_镇魔司制服_比例.png 不存在
  - block [gate:image] 预防式合同 @ PROP_镇魔司制服: 预防式合同 reference_slot_gate: 道具/场景 PROP_镇魔司制服 引用槽位未绑定真实产物：出图/共享/图片/定妆_道具_镇魔司制服.png 不存在；出图/共享/图片/定妆_道具_镇魔司制服.png 不存在；出图/共享/图片/定妆_道具_镇魔司制服_比例.png 不存在
- block · asset:WEAPON_01 · image_prompt_lint / image prompt compiler / multimodal_continuity
  - warn [detect] image_prompt_lint: image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸
  - warn [detect] image_prompt_lint: image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀_比例.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无
  - warn [detect] image_prompt_lint: image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀_手持.png faceless 像素核验降级（未装 insightface/cv2——faceless 像素核验跳过，交人审）——跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无
- block · asset:reference_plan_第3集.json · 跨集记忆锚落实
  - block [gate:image_preflight] 跨集记忆锚落实 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/reference_plan_第3集.json: 跨集记忆锚落实 memory_anchor_contract 不可用：status=missing; errors=memory_anchor_plan_missing。缺失/陈旧记忆锚计划不得被下游参考规划默默忽略。
- block · asset:storyboard.json clip#6 · 实体排程
  - block [gate:image_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#6: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
  - block [gate:image_prompt_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#6: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
  - block [gate:image] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#6: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
- block · asset:storyboard.json clip#8 · 实体排程
  - block [gate:image_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#8: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
  - block [gate:image_prompt_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#8: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
  - block [gate:image] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#8: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
- block · asset:定妆_道具_镇魔司制服.png · 资产引用注册层
  - block [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/图片/定妆_道具_镇魔司制服.png: 资产引用注册层 reference_group.primary 路径不存在
- block · asset:第3集 VFX_墨虎谱影 · 资产引用注册层
  - block [gate:image_preflight] 资产引用注册层 @ 第3集 VFX_墨虎谱影: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `VFX_墨虎谱影`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
  - block [gate:image] 资产引用注册层 @ 第3集 VFX_墨虎谱影: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `VFX_墨虎谱影`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第3集 VFX_百妖谱 · 资产引用注册层
  - block [gate:image_preflight] 资产引用注册层 @ 第3集 VFX_百妖谱: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `VFX_百妖谱`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
  - block [gate:image] 资产引用注册层 @ 第3集 VFX_百妖谱: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `VFX_百妖谱`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · character:01_分镜出图.md · 共享定妆
  - block [gate:image_preflight] 共享定妆 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md: 共享定妆 本集逐镜引用了未过落档自检的共享定妆/资产 `PROP_镇魔司制服`（registry `self_check_passed=false`）——脏定妆是锚点，脸/结构漂了下游每镜继承；先过自检并把该项置 true（或人工复核后 `image_qc --mark-finalized`），再付费出图。
  - block [gate:image] 共享定妆 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md: 共享定妆 本集逐镜引用了未过落档自检的共享定妆/资产 `PROP_镇魔司制服`（registry `self_check_passed=false`）——脏定妆是锚点，脸/结构漂了下游每镜继承；先过自检并把该项置 true（或人工复核后 `image_qc --mark-finalized`），再付费出图。
- block · character:CHAR_01 · 表情连续(EXP1) / 实体记忆(EMB) / image_prompt_lint / 脸漂实测 / 生图AI一致性 / image prompt compiler
  - warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_04：角色 CHAR_01 相邻镜情绪硬跳（惊→喜）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
  - warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_07：角色 CHAR_01 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
  - warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/镇魔司制服态, CHAR_01__, CHAR_01__囚途残损态, CHAR_02, CHAR_02与飞鹰门众）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- block · character:CHAR_02 · image_prompt_lint / 实体排程 / image prompt compiler
  - warn [detect] image_prompt_lint: image_prompt_lint  None 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs rear_three_quarter(1.000)，差 0.050>0.035；身体中心线不齐：side(0.485) vs rear_three_quarter(0.625)，差 0.140>0.055——像素几何是
  - block [gate:image_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#2: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：CHAR_02。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
  - warn [gate:image_preflight] image prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/角色定妆.md ## 裴长青（`CHAR_02/“濒死重伤态”`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:43>16
- block · character:CHAR_02__濒死重伤态 · character_consistency
  - block [detect] character_consistency @ CHAR_02__濒死重伤态: character_consistency  CHAR_02__濒死重伤态 跨集脸漂移趋势 high：CHAR_02__濒死重伤态 第1集→第3集 mean 0.4424→0.1918 drop=0.2506。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。 

## 依赖传播

- nodes=40 · edges=59 · clips=8 · images=17 · videos=0
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第3集.json`

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
| 姜月初（CHAR_01） | character | ⛔ block | ⛔ | ⛔ | 🟢 |
| 03（CHAR_03） | character | ⛔ block | 🟢 | ⛔ | 🟢 |
| 裴长青（CHAR_02） | character | ⛔ block | 🟢 | ⛔ | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| LOC_02（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_横刀） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸骸荒野（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 镇魔司制服（PROP_镇魔司制服） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| GROUP_01（GROUP_01） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    

## ⛔ 03（CHAR_03）
- [warn]  景深一致(DOF1)   图片/EP03_CLIP06_a3.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比 1.1
- [warn]  表情连续(EXP1)   Clip_07：角色 CHAR_03 相邻镜情绪硬跳（惊→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没
- [warn]  节奏密度(Rhythm)   连续 4 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CL

## ⛔ 裴长青（CHAR_02）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/镇魔司制服态, CHAR_01__, CHAR_01__囚
- [block] character_consistency  CHAR_02__濒死重伤态 跨集脸漂移趋势 high：CHAR_02__濒死重伤态 第1集→
- [warn] image_prompt_lint  None 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs

## 🟡 虎妖（BEAST_01）
- [warn] image_prompt_lint  None 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_qu

## 🟡 LOC_02（LOC_02）
- [warn]  场景平面(FP1)   场景 LOC_02 本集出现 6 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记
- [warn] image_prompt_lint  None 资产 LOC_02：出图/共享/图片/定妆_场景_LOC_02.png faceless 像

## 🟡 横刀（WEAPON_01）
- [warn] image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素
- [warn] image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀_比例.png faceless
- [warn] image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀_手持.png faceless

## 🟡 横刀（WEAPON_横刀）
- [warn] image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀.png faceless 像素
- [warn] image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀_比例.png faceless
- [warn] image_prompt_lint  None 资产 WEAPON_01：出图/共享/图片/定妆_武器_横刀_手持.png faceless

## 🟡 尸骸荒野（LOC_01）
- [warn]  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集色调/光位漂移 L1=0.7437（vs 前 2 集基线，阈 warn=0.45·c
- [warn]  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集结构漂移 dHash 汉明=19（vs 前 2 集结构原型，阈 warn=18·co
- [warn] image_prompt_lint  None 资产 LOC_01：出图/共享/图片/定妆_场景_尸骸荒野.png faceless 像素核

## 🟡 镇魔司制服（PROP_镇魔司制服）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/镇魔司制服态, CHAR_01__, CHAR_01__囚

## 未归属到具体角色/资产的一致性问题
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [block]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  景深一致(DOF1)   图片/Clip02_first.png：景深档与同场景其它镜不一致——本镜偏浅景深(背景偏糊)（景深比 0.74
- [warn]  糊/低质(N4)    
- [warn]  天气时辰(W1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
