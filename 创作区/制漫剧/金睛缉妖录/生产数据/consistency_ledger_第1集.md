# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 11 · 🔴 high 0 · 🟡 medium 8

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 1 | 0 | 30 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 157 | 0 | 83 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 44 | detect, gate:image_preflight, gate:image |
| 镜头 | ⛔ block | 34 | 0 | 42 | detect, gate:image_preflight, gate:image |
| 音频 | ⛔ block | 6 | 0 | 15 | detect, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 1 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 5 | 0 | 33 | detect, gate:image_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 11 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11→EP01_CLIP12），疑节奏塌·掉留存 
- warn [detect] 视线状态回读(X2):  视线状态回读(X2)   12 个视线/状态高风险镜当前 image_qc 精度为 degraded；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 12 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第1集/storyboard.json 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=7be11bd44ccda7b3，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第1集/storyboard.json 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第1集/storyboard.json 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `换皮妖/陈贵皮相` 未进入 storyboard。；缺：换皮妖/陈贵皮相
- warn [gate:image_preflight] 状态百科(P1) @ 状态百科(P1): 状态百科(P1) CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜6 仍保留。

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
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_10（fight_exchange）：剪辑峰值钉在 [1.5]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_11（magic_burst）：剪辑峰值钉在 [5.2]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜6 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜7 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜8 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜9 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜10 仍保留。 
- warn [detect] 状态百科(P1):  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜11 仍保留。 

### 镜头问题
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 陈宅正屋桌边 本集出现 4 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 陈宅正屋 本集出现 3 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_陈宅正屋.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] image_qc_precision: image_qc_precision  None image_qc 精度为 degraded：正式进 video 前需补依赖重跑到 full 精度；普通人审记录只能辅助定位，不能替代 video/compose 前的 full QC gate。 
- warn [detect] scene_consistency: scene_consistency  None 接缝接力 未执行：无 /Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/出图/第1集/图片——出图后再跑接缝机检。；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。 
- warn [detect] style_consistency: style_consistency  None 风格归属无法机检：style_contract 未登记风格锚（style_anchor）。请在定妆阶段出 1–2 张「冷灰写实3D国风漫剧」风格锚图、登记进 style_contract.style_anchor，后续每集出图帧才能对锚做风格归属佐证。当前降级为人判：逐图核对是否踩 风格禁忌：禁Q版、禁现代家具
- block [detect] multimodal_continuity @ 图片/Clip01_first.png: multimodal_continuity  图片/Clip01_first.png 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP01_CLIP01` · 死人喝茶冷开 · evidence_search） 的 `PROP_BLOOD_THRESHOLD`（门槛半干血迹）登记了 must_not_have=器官、大面积血泊；scale=None。文字约束
- block [detect] multimodal_continuity @ 图片/Clip01_first.png: multimodal_continuity  图片/Clip01_first.png 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP01_CLIP01` · 死人喝茶冷开 · evidence_search） 的 `PROP_STILL_TEA`（不动热茶）登记了 must_not_have=现代杯柄、文字茶杯；scale=None。文字约束不能证明既有 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头4·旁白：台词含强情绪但配音标注「低沉」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头17·旁白：台词含强情绪但配音标注「急促」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头19·旁白：台词含强情绪但配音标注「爆发」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `换皮妖/陈贵皮相` 未进入 storyboard。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第1集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=19cf905694aa3203，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第1集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第1集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 

### 生产操作问题
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_SHEN_YAN__常态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_PEIJUE__常态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_FANGZHENG__局部参考_剪影局部.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_CHEN_WIFE__局部参考_剪影局部.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_PEIJUE__常态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_SHEN_YAN__常态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_FANGZHENG__局部参考_剪影局部.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · audio:leitmotif_registry.json · 音乐母题(LM1)
  - block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:重复同维度] 音乐母题 MOTIF_jinjing_gold_eye 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_h
  - block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:重复同维度] 音乐母题 MOTIF_jinjing_gold_eye 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；f
  - block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:重复同维度] 音乐母题 MOTIF_skin_demon 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=9f
- block · character:Clip01_end.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip01_end.png: character_consistency  图片/Clip01_end.png 崩脸 G1 block：图片/Clip01_end.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 崩脸 G1 block：图片/Clip01_end.png（脸/身份漂移机检）
- block · character:Clip01_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip01_first.png: character_consistency  图片/Clip01_first.png 崩脸 G1 block：图片/Clip01_first.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 崩脸 G1 block：图片/Clip01_first.png（脸/身份漂移机检）
- block · character:Clip01_mid.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip01_mid.png: character_consistency  图片/Clip01_mid.png 崩脸 G1 block：图片/Clip01_mid.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip01_mid.png: character_consistency 崩脸 G1 block：图片/Clip01_mid.png（脸/身份漂移机检）
- block · character:Clip02_end.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip02_end.png: character_consistency  图片/Clip02_end.png 崩脸 G1 block：图片/Clip02_end.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip02_end.png: character_consistency 崩脸 G1 block：图片/Clip02_end.png（脸/身份漂移机检）
- block · character:Clip02_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip02_first.png: character_consistency  图片/Clip02_first.png 崩脸 G1 block：图片/Clip02_first.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 崩脸 G1 block：图片/Clip02_first.png（脸/身份漂移机检）
- block · character:Clip02_mid.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip02_mid.png: character_consistency  图片/Clip02_mid.png 崩脸 G1 block：图片/Clip02_mid.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip02_mid.png: character_consistency 崩脸 G1 block：图片/Clip02_mid.png（脸/身份漂移机检）
- block · character:Clip03_end.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip03_end.png: character_consistency  图片/Clip03_end.png 崩脸 G1 block：图片/Clip03_end.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip03_end.png: character_consistency 崩脸 G1 block：图片/Clip03_end.png（脸/身份漂移机检）
- block · character:Clip03_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip03_first.png: character_consistency  图片/Clip03_first.png 崩脸 G1 block：图片/Clip03_first.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip03_first.png: character_consistency 崩脸 G1 block：图片/Clip03_first.png（脸/身份漂移机检）
- block · character:Clip03_mid.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip03_mid.png: character_consistency  图片/Clip03_mid.png 崩脸 G1 block：图片/Clip03_mid.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip03_mid.png: character_consistency 崩脸 G1 block：图片/Clip03_mid.png（脸/身份漂移机检）
- block · character:Clip04_end.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip04_end.png: character_consistency  图片/Clip04_end.png 崩脸 G1 block：图片/Clip04_end.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip04_end.png: character_consistency 崩脸 G1 block：图片/Clip04_end.png（脸/身份漂移机检）
- block · character:Clip04_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip04_first.png: character_consistency  图片/Clip04_first.png 崩脸 G1 block：图片/Clip04_first.png（脸/身份漂移机检） 
  - block [gate:image] character_consistency @ 图片/Clip04_first.png: character_consistency 崩脸 G1 block：图片/Clip04_first.png（脸/身份漂移机检）

## 依赖传播

- nodes=33 · edges=79 · clips=12 · images=0 · videos=0
- graph: `/Users/lalala/learn/anime-arsenal/创作区/制漫剧/金睛缉妖录/生产数据/consistency_dependency_graph_第1集.json`

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
| 陈妻（CHAR_CHEN_WIFE） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 门槛半干血迹（PROP_BLOOD_THRESHOLD） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 雨水泥脚印（PROP_MUD_FOOTPRINT） | prop | ⛔ block | 🟢 | ⛔ | 🟢 |
| 干净皂靴（PROP_CLEAN_BLACK_BOOT） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 不动热茶（PROP_STILL_TEA） | prop | ⛔ block | 🟢 | ⛔ | 🟢 |
| 半片旧铜（PROP_OLD_COPPER_HALF） | prop | ⛔ block | 🟢 | ⛔ | 🟢 |
| 沈砚（CHAR_SHEN_YAN） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 换皮妖·陈贵皮相（CHAR_PI_DEMON_CHENGUI） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 裴决（CHAR_PEIJUE） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 坊正（CHAR_FANGZHENG） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 靖京西坊陈宅正屋（LOC_CHEN_HOUSE） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 笔录纸（PROP_RECORD_PAPER） | prop | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 裴决短刀（WEAPON_PEIJUE_SHORT_BLADE） | weapon | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 金睛旧金光（VFX_JINJING_GOLD_EYE） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 换皮妖揭皮显相（VFX_SKIN_DEMON_REVEAL） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 裴决冷蓝符火（VFX_PEIJUE_FU_FIRE） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 陈妻（CHAR_CHEN_WIFE）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_CHEN_WIFE, CHAR_CHEN_WIFE__, CHAR_PEIJUE,
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_CHEN_WIFE__局部参考_剪影局部.png 生成事件缺 cost/provi
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_CHEN_WIFE__局部参考_剪影局部.png 生成事件缺 cost/provi

## ⛔ 门槛半干血迹（PROP_BLOOD_THRESHOLD）
- [block] multimodal_continuity  图片/Clip01_first.png 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP01_
- [block] multimodal_continuity  图片/Clip02_first.png 高风险道具禁形/尺寸未逐图确认：镜头 2（`EP01_
- [block] multimodal_continuity  图片/Clip03_first.png 高风险道具禁形/尺寸未逐图确认：镜头 3（`EP01_

## ⛔ 雨水泥脚印（PROP_MUD_FOOTPRINT）
- [block] multimodal_continuity  图片/Clip02_first.png 高风险道具禁形/尺寸未逐图确认：镜头 2（`EP01_
- [block] multimodal_continuity  图片/Clip03_first.png 高风险道具禁形/尺寸未逐图确认：镜头 3（`EP01_
- [block] multimodal_continuity  图片/Clip04_first.png 高风险道具禁形/尺寸未逐图确认：镜头 4（`EP01_

## ⛔ 干净皂靴（PROP_CLEAN_BLACK_BOOT）
- [block] multimodal_continuity  图片/Clip03_first.png 高风险道具禁形/尺寸未逐图确认：镜头 3（`EP01_
- [block] multimodal_continuity  图片/Clip04_first.png 高风险道具禁形/尺寸未逐图确认：镜头 4（`EP01_
- [block] multimodal_continuity  图片/Clip08_first.png 高风险道具禁形/尺寸未逐图确认：镜头 8（`EP01_

## ⛔ 不动热茶（PROP_STILL_TEA）
- [block] multimodal_continuity  图片/Clip01_first.png 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP01_
- [block] multimodal_continuity  图片/Clip03_first.png 高风险道具禁形/尺寸未逐图确认：镜头 3（`EP01_
- [block] multimodal_continuity  图片/Clip04_first.png 高风险道具禁形/尺寸未逐图确认：镜头 4（`EP01_

## ⛔ 半片旧铜（PROP_OLD_COPPER_HALF）
- [block] multimodal_continuity  图片/Clip05_first.png 高风险道具禁形/尺寸未逐图确认：镜头 5（`EP01_
- [warn] image_prompt_lint  None 资产 PROP_OLD_COPPER_HALF：出图/共享/图片/定妆_道具_半片旧铜.pn
- [warn] image_prompt_lint  None 资产 PROP_OLD_COPPER_HALF：出图/共享/图片/定妆_道具_半片旧铜_比例

## 🟡 沈砚（CHAR_SHEN_YAN）
- [warn]  表情连续(EXP1)   Clip_07：角色 CHAR_SHEN_YAN 相邻镜情绪硬跳（悲→惊）——确认有节拍/事件依据，否则表演 O
- [warn]  表情连续(EXP1)   Clip_07：角色 CHAR_SHEN_YAN__ 相邻镜情绪硬跳（悲→惊）——确认有节拍/事件依据，否则表演
- [warn]  表情连续(EXP1)   Clip_08：角色 CHAR_SHEN_YAN 相邻镜情绪硬跳（惊→悲）——确认有节拍/事件依据，否则表演 O

## 🟡 换皮妖·陈贵皮相（CHAR_PI_DEMON_CHENGUI）
- [warn]  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜6 仍保留。
- [warn]  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜7 仍保留。
- [warn]  状态百科(P1)   CHAR_PI_DEMON_CHENGUI 的状态 `陈贵皮相，温和假笑，动作过静。` 声明至镜5，但镜8 仍保留。

## 🟡 裴决（CHAR_PEIJUE）
- [warn]  多视角身份包(MVIEW)   核心/长线角色 CHAR_SHEN_YAN, CHAR_PI_DEMON_CHENGUI, CHAR_PE
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_CHEN_WIFE, CHAR_CHEN_WIFE__, CHAR_PEIJUE,
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_PEIJUE__常态_正面.png 生成事件缺 cost/provider 记账；

## 🟡 坊正（CHAR_FANGZHENG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_FANGZHENG__局部参考_剪影局部.png 生成事件缺 cost/provi
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_FANGZHENG__局部参考_剪影局部.png 生成事件缺 cost/provi
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_FANGZHENG__局部参考_剪影局部.png 生成事件缺 cost/provi

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
