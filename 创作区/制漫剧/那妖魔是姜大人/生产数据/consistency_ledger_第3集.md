# 验收总账 · 第3集

- 验收状态：阻断
- ⛔ block 4 · 🔴 high 0 · 🟡 medium 18

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 5 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 2 | 0 | 91 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_prompt_preflight, gate:video |
| 资产 | 🟡 warn | 0 | 0 | 25 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 镜头 | ⛔ block | 10 | 0 | 151 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 音频 | 🟡 warn | 0 | 0 | 23 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 字幕 | 🟢 ok | 0 | 0 | 0 | — |
| 合规 | 🟡 warn | 0 | 0 | 7 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 39 | 0 | 52 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_prompt_preflight, gate:video, score, expression_state_consistency |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CLIP04→EP03_CLIP05→EP03_CLIP06→EP03_CLIP07→EP03_CLIP08→EP03_CLIP09→EP03_CLIP10），疑节奏塌·掉留存 
- warn [detect] 物理因果链(CG1):  物理因果链(CG1)   视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 跨集色调 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image] 跨集色调 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
- block [detect] 发型(H1): CHAR_01__囚犯初醒态 发型(H1)    
- warn [detect] 主体视频一致(S2V):  主体视频一致(S2V)   本集已有主体/角色契约和视频产物，但缺 subject_video_consistency；无法核验视频侧主体保真、多主体串脸、自然度和背景解耦。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_01__镇魔司伪装态_脸部特写_脸锚裁切.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_04__常态_脸部特写_脸锚裁切.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 跨集脸漂移趋势 medium：CHAR_01__囚犯初醒态 第1集→第2集 mean 0.406→0.4461 drop=-0.0401。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。 
- warn [detect] character_consistency @ 图片/Clip02_mid.png: character_consistency  图片/Clip02_mid.png 发型 H1 初筛：图片/Clip02_mid.png（发色/发型轮廓离群，非阻断） 

### 资产问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 PROP_镇魔司黑衣赤纹 出现于 4 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集色调/光位漂移 L1=0.6315（vs 前 2 集基线，阈 warn=0.45·core block=0.8）——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集结构漂移 dHash 汉明=24（vs 前 2 集结构原型，阈 warn=18·core block=26）——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip08_first_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.041 vs 场景中位 -0.164）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip08_first_a3.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.036 vs 场景中位 -0.164）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头1·旁白：台词含强情绪但配音标注「低沉」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头18·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头19·旁白：台词含强情绪但配音标注「悬停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·旁白：台词含强情绪但配音标注「沉下」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头33·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头35·旁白：台词含强情绪但配音标注「硬断」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「马队出现：鼓点加速，火把和马蹄声盖住」→「镜头20：姜月初“何事？”前留 0.」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 

## 根因聚合

- block · character:character · 跨集脸漂(G5) / 发型(H1) / 主体视频一致(S2V) / 成本路由(K1) / 叙事状态(NS1) / image_prompt_lint
  - warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
  - block [detect] 发型(H1): CHAR_01__囚犯初醒态 发型(H1)    
  - warn [detect] 主体视频一致(S2V):  主体视频一致(S2V)   本集已有主体/角色契约和视频产物，但缺 subject_video_consistency；无法核验视频侧主体保真、多主体串脸、自然度和背景解耦。 
- block · character:video_batch_第3集_03_03.json · 成片身份回验
  - block [gate:video] 成片身份回验 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/video_batch_第3集_03_03.json: 成片身份回验 Clip_03 已被 video_runner 标记 qc_blocked：成片身份回验 block：dense_face_watch 镜出现片内身份 warn×1；warn=粗筛交人判，不能静默 accept。重出本镜或确认误报后 --allow-qc-block 强制验收
- block · ops:Clip01_first_a1.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_first_a1.png: 中段锚帧 声明了锚帧 1 但锚帧 PNG 不存在
- block · ops:Clip01_first_a2.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_first_a2.png: 中段锚帧 声明了锚帧 2 但锚帧 PNG 不存在
- block · ops:Clip01_first_a3.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip01_first_a3.png: 中段锚帧 声明了锚帧 3 但锚帧 PNG 不存在
- block · ops:Clip02_mid.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip02_mid.png: 中段锚帧 声明了锚帧 1 但锚帧 PNG 不存在
- block · ops:Clip03_first_a1.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip03_first_a1.png: 中段锚帧 声明了锚帧 1 但锚帧 PNG 不存在
- block · ops:Clip03_first_a2.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip03_first_a2.png: 中段锚帧 声明了锚帧 2 但锚帧 PNG 不存在
- block · ops:Clip03_first_a3.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip03_first_a3.png: 中段锚帧 声明了锚帧 3 但锚帧 PNG 不存在
- block · ops:Clip03_first_a4.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip03_first_a4.png: 中段锚帧 声明了锚帧 4 但锚帧 PNG 不存在
- block · ops:Clip04_first_a1.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip04_first_a1.png: 中段锚帧 声明了锚帧 1 但锚帧 PNG 不存在
- block · ops:Clip04_first_a2.png · 中段锚帧
  - block [gate:video_prompt_preflight] 中段锚帧 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/图片/Clip04_first_a2.png: 中段锚帧 声明了锚帧 2 但锚帧 PNG 不存在

## 依赖传播

- nodes=113 · edges=166 · clips=10 · images=58 · videos=3
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第3集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=4

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 陈青源（CHAR_04） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 青面郎君（CHAR_05） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 上盘村村口与村道（LOC_03） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| GROUP_飞鹰门众人（GROUP_飞鹰门众人） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| GROUP_狼妖群（GROUP_狼妖群） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 百妖谱金光（VFX_百妖谱金光） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [block] CHAR_01__囚犯初醒态 发型(H1)    
- [warn]  配音情绪弧(VEA)   镜头18·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标

## 🟡 陈青源（CHAR_04）
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_04 出现于 10 镜，但 entity_memory_bank 没有已验收记忆条目。 
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_04__ 出现于 6 镜，但 entity_memory_bank 没有已验收记忆条目。
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_04__常态 出现于 6 镜，但 entity_memory_bank 没有已验收记忆条

## 🟡 青面郎君（CHAR_05）
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态

## 🟡 裴长青（CHAR_02）
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 荒野尸骸战场（LOC_01）
- [warn]  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集色调/光位漂移 L1=0.6315（vs 前 2 集基线，阈 warn=0.45
- [warn]  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集结构漂移 dHash 汉明=24（vs 前 2 集结构原型，阈 warn=18·

## 🟡 尸场物资包（PROP_尸场物资包）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_比例.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_手持.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 荒野官道夜路（LOC_02）
- [warn]  实体记忆(EMB)   重复/核心实体 LOC_02 出现于 7 镜，但 entity_memory_bank 没有已验收记忆条目。 
- [warn]  实体记忆(EMB)   重复/核心实体 LOC_02 荒野官道夜路 出现于 7 镜，但 entity_memory_bank 没有已验收记
- [warn]  场景平面(FP1)   场景 LOC_02 荒野官道夜路 本集复用 7 镜但缺 location_spatial_memory 条目；多视

## 🟡 横刀（WEAPON_01）
- [warn]  实体记忆(EMB)   重复/核心实体 WEAPON_01 横刀 出现于 4 镜，但 entity_memory_bank 没有已验收记忆

## 🟡 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹）
- [warn]  实体记忆(EMB)   重复/核心实体 PROP_镇魔司黑衣赤纹 出现于 4 镜，但 entity_memory_bank 没有已验收记忆
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_比例.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 飞鹰门马匹与火把（MOUNT_GROUP_01）
- [warn]  实体记忆(EMB)   重复/核心实体 MOUNT_GROUP_01 飞鹰门马匹与火把 出现于 4 镜，但 entity_memory_b
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png 生成事件缺 cost/provider 记账；无法计算

## 未归属到具体角色/资产的一致性问题
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
