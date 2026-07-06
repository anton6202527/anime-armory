# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 6 · 🔴 high 0 · 🟡 medium 20

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 9 | 0 | 125 | detect, gate:compose, gate:image_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 角色 | ⛔ block | 91 | 0 | 94 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video, review-ui, score |
| 资产 | ⛔ block | 3 | 0 | 37 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 镜头 | ⛔ block | 119 | 0 | 209 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 音频 | ⛔ block | 8 | 0 | 32 | detect, gate:compose, gate:image_preflight, gate:image, gate:review, gate:video_preflight, gate:video, review-ui, score |
| 字幕 | 🟡 warn | 0 | 0 | 19 | detect, gate:compose, review-ui, score |
| 合规 | 🟡 warn | 0 | 0 | 7 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 43 | 0 | 69 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_prompt_preflight, gate:video, review-ui, score |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm) @ 脚本/第1集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：57.4 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s > 5s，前3秒易掉留存 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_01__囚犯初醒态_脸部特写.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__诈死复苏态_脸部特写.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_01__镇魔司伪装态: character_consistency  CHAR_01__镇魔司伪装态 锚点门 N3：CHAR_01__镇魔司伪装态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_02__濒死战损态: character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸（非阻断） 

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_10（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- block [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.127 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip08_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.14 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 
- warn [detect] 多人对话音画(DAV):  多人对话音画(DAV)   检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 
- warn [detect] 成片统一(C1):  成片统一(C1)   storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。 
- warn [detect] 成片统一(C1):  成片统一(C1)   缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第1集/配音/voice_zh.wav 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=584f6548fdede418，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第1集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver
- warn [gate:compose] 原生音画 @ 创作区/制漫剧/那妖魔是姜大人/_设置.md: 原生音画 原生音画：当前 视频原生音轨=丢弃，但 native_speech 台词在 clip 原片音轨里；compose 将按有效策略自动「保留原片音轨」以免丢失原生台词（确需强制丢弃须设 VIDEO_NATIVE_AUDIO_POLICY_EXPLICIT=1）

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_09 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_10 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_11 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [gate:compose] 原生音画字幕对齐 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/native_av_subtitle_alignment_第1集.json: 原生音画字幕对齐 缺 native AV 字幕对齐 sidecar：原生音画说话镜不走前期配音 SRT，成片后必须用 whisperx 或等效词级对齐生成中文字幕并写 `kind=n2d_native_av_subtitle_alignment`、status、word_level、subtitle_path。 compose 可先出 draft，但 rev

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:compose] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:review] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · asset:asset · 打斗撞点(SPEC-APEX) / 结构化交互图谱(I2) / 系统面板(UI1)
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_10（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- block · asset:storyboard.json clip#1 · 专项镜头模板
  - block [gate:image_preflight] 专项镜头模板 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#1: 专项镜头模板 复杂镜头疑似「realm_portal」，但缺 template/template_contract；回 n2d-script 按 references/专项镜头模板库.md 套模板，不要从零写 prompt
  - block [gate:image] 专项镜头模板 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#1: 专项镜头模板 复杂镜头疑似「realm_portal」，但缺 template/template_contract；回 n2d-script 按 references/专项镜头模板库.md 套模板，不要从零写 prompt
- block · audio:EP01_CLIP02 · 音画同步
  - block [review-ui] 音画同步 @ EP01_CLIP02: 音画同步 mechanical[原生音轨] 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4: clip 含原生音轨；compose 默认应丢弃。若按 opt-in 混入环境声，需确认低风险、无口型、无原生人声
- block · audio:consistency_findings_第1集.json · 证据等级
  - warn [gate:image] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
  - block [gate:review] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRAD
  - warn [gate:video] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
- block · audio:episode · 音画同步 / 音色一致性
  - warn [review-ui] 音画同步 @ episode: 音画同步 音画同步(AV1): block=0 warn=0 ok=0 skipped=True
  - warn [review-ui] 音画同步 @ episode: 音画同步 多人对话音画(DAV): block=0 warn=1 ok=0 skipped=False
  - warn [review-ui] 音画同步 @ episode: 音画同步 多人对话音画(DAV) detail: 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 定位产物：生产数据/dialogue_av_alignment_第1集.json、合成/第1集
- block · audio:pilot_acceptance_第1集.json · 预防式合同
  - block [gate:review] 预防式合同 @ 生产数据/pilot_acceptance_第1集.json: 预防式合同 pilot_release_gate: 第1集缺 pilot_acceptance；先用 2-3 个代表镜头验证脸/场景/动作/口型/接缝/路由。
- block · audio:score_第1集.json · 音画同步 / 音色一致性
  - block [score] 音画同步 @ 生产数据/score_第1集.json: 音画同步: status=fail score=37 block=1 warn=2
  - warn [score] 音色一致性 @ 生产数据/score_第1集.json: 音色一致性: status=warn score=88 block=0 warn=1
- block · character:01_分镜出图.md ## 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange） · prompt / 角色一致性
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）: prompt 中文图片 prompt 缺字段：身份保持
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - block [gate:image] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）: prompt 中文图片 prompt 缺字段：身份保持
- block · character:01_分镜出图.md ## 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame） · prompt / 角色一致性
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）: prompt 中文图片 prompt 缺字段：身份保持
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）: prompt 中文图片 prompt 缺字段：镜头构图
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）: prompt 中文图片 prompt 缺字段：动作瞬间
- block · character:01_分镜出图.md ## 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ） · prompt
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）: prompt 中文图片 prompt 缺字段：身份保持
  - block [gate:image] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）: prompt 中文图片 prompt 缺字段：身份保持
- block · character:01_分镜出图.md ## 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal） · prompt / 角色一致性
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）: prompt 中文图片 prompt 缺字段：身份保持
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - block [gate:image] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）: prompt 中文图片 prompt 缺字段：身份保持
- block · character:01_分镜出图.md ## 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse） · prompt / 角色一致性
  - block [gate:image_preflight] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）: prompt 中文图片 prompt 缺字段：身份保持
  - warn [gate:image_preflight] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - block [gate:image] prompt @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md ## 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）: prompt 中文图片 prompt 缺字段：身份保持

## 依赖传播

- nodes=103 · edges=220 · clips=11 · images=31 · videos=16
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=0

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 陈青源（CHAR_04） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 青面郎君（CHAR_05） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村村口与村道（LOC_03） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟡 warn | 🟢 | 🟡 | 🟢 |
| GROUP_飞鹰门众人（GROUP_飞鹰门众人） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| GROUP_狼妖群（GROUP_狼妖群） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [warn]  多视角身份包(MVIEW)   核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_iden
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/囚犯初醒态, CHAR_01/百妖谱能力触发态, CHAR

## 🟡 陈青源（CHAR_04）
- [warn] character_consistency  CHAR_04__常态 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） 
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_04/常态「基础」（出图/共享/图片/定妆_CHAR_04__常态

## 🟡 青面郎君（CHAR_05）
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态

## 🟡 虎山神 / 虎妖（CHAR_03）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png 生成事件缺 cost/provider 记账；无
- [warn]  成本路由(K1)   出图/共享/图片/定妆_特效_VFX_虎妖黑血妖气.png 生成事件缺 cost/provider 记账；无法计算重
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__诈死复苏态_45度.png 生成事件缺 cost/provider 记账；

## 🟡 裴长青（CHAR_02）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/囚犯初醒态, CHAR_01/百妖谱能力触发态, CHAR
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_02__濒死战损态_正面.png 生成事件缺 cost/provider 记账；无
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_02__濒死战损态_45度.png 生成事件缺 cost/provider 记账；

## 🟡 荒野尸骸战场（LOC_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_荒野尸骸战场.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 横刀（WEAPON_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_武器_横刀.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 🟡 妖气（VFX_妖气）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_特效_VFX_虎妖黑血妖气.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 系统面板（VFX_系统面板）
- [warn]  系统面板(UI1)   检出 6 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核
- [warn]  系统面板(UI1)   检出 6 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continui
- [warn]  打斗撞点(SPEC-APEX)    Clip_10（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continui
- [warn]  色温调色(GRADE1)   图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs
- [warn]  色温调色(GRADE1)   图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243
- [warn]  色温调色(GRADE1)   图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 v

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
