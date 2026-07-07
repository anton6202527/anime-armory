# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 4 · 🔴 high 0 · 🟡 medium 21

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 65 | detect, gate:compose, gate:image_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 角色 | ⛔ block | 1 | 0 | 109 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video, review-ui, score |
| 资产 | 🟡 warn | 0 | 0 | 23 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 镜头 | ⛔ block | 6 | 0 | 219 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 音频 | ⛔ block | 2 | 0 | 20 | detect, gate:compose, gate:image, gate:review, gate:video_preflight, gate:video, review-ui, score |
| 字幕 | 🟡 warn | 0 | 0 | 5 | review-ui, score |
| 合规 | 🟡 warn | 0 | 0 | 6 | gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 1 | 0 | 20 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_prompt_preflight, gate:video, review-ui, score |

### 剧情问题
- warn [detect] 节奏密度(Rhythm) @ 脚本/第1集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：57.4 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s > 5s，前3秒易掉留存 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_01__镇魔司伪装态: character_consistency  CHAR_01__镇魔司伪装态 锚点门 N3：CHAR_01__镇魔司伪装态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_02__濒死战损态: character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_04__常态: character_consistency  CHAR_04__常态 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） 
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） 
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） 
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） 

### 资产问题
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden
- warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/
- warn [gate:image_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:image_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:image_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:image_preflight] 人物在场链 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6→clip#7: 人物在场链 实体在下一 Clip 出现但缺入画/换场解释：VFX_系统面板。若是新入场，请把 entry_exit 写成机器真值。

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
- warn [gate:compose] 原生音轨 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4: 原生音轨 clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声
- block [gate:compose] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRAD
- warn [gate:image] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
- warn [gate:image] 配音情绪弧(VEA) @ 脚本/第1集/voiceover.txt: 配音情绪弧(VEA) 镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [gate:review] 原生音轨 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4: 原生音轨 clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声
- block [gate:review] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRAD
- warn [gate:video_preflight] 配音 @ 第1集: 配音 先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频

### 字幕问题
- warn [review-ui] 图中文字渲染一致性（OCR 校验） @ episode: 图中文字渲染一致性（OCR 校验） 文字渲染(OCR1): block=0 warn=6 ok=0 skipped=False
- warn [review-ui] 图中文字渲染一致性（OCR 校验） @ EP01_CLIP02: 图中文字渲染一致性（OCR 校验） 文字渲染(OCR1) detail: Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_02 定位产物：出图/第1集/
- warn [review-ui] 图中文字渲染一致性（OCR 校验） @ EP01_CLIP07: 图中文字渲染一致性（OCR 校验） 文字渲染(OCR1) detail: Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_07 定位产物：出图/第1集/
- warn [review-ui] 图中文字渲染一致性（OCR 校验） @ EP01_CLIP08: 图中文字渲染一致性（OCR 校验） 文字渲染(OCR1) detail: Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_08 定位产物：出图/第1集/
- warn [review-ui] 图中文字渲染一致性（OCR 校验） @ EP01_CLIP09: 图中文字渲染一致性（OCR 校验） 文字渲染(OCR1) detail: Clip_09 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_09 定位产物：出图/第1集/

### 合规问题
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
- warn [detect] 视频VLM判题(VLM1):  视频VLM判题(VLM1)   本机未配置重型 VLM runner；此文件仅占位并指向 manifest，不能作为 pass 结论。 
- warn [gate:compose] 一致性总审 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 一致性总审 另有 24 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。
- warn [gate:image] 一致性总审 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 一致性总审 另有 7 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。

## 根因聚合

- block · audio:consistency_findings_第1集.json · 证据等级
  - block [gate:compose] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRAD
  - warn [gate:image] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
  - block [gate:review] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRAD
- block · character:score_第1集.json · 角色 DNA/形体一致性（脸/发型/身形/手）
  - block [score] 角色 DNA/形体一致性（脸/发型/身形/手） @ 生产数据/score_第1集.json: 角色 DNA/形体一致性（脸/发型/身形/手）: status=fail score=16 block=2 warn=1
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: score status=fail total=80 threshold=85
- block · shot:resident_presence_第1集.json · 现实覆盖
  - block [gate:compose] 现实覆盖 @ 生产数据/resident_presence_第1集.json: 现实覆盖 场景常驻陈设在场(OWLv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/resident_presence.py "
  - block [gate:review] 现实覆盖 @ 生产数据/resident_presence_第1集.json: 现实覆盖 场景常驻陈设在场(OWLv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/resident_presence.py "
- block · shot:scene_embed_第1集.json · 现实覆盖
  - block [gate:compose] 现实覆盖 @ 生产数据/scene_embed_第1集.json: 现实覆盖 场景语义嵌入(DINOv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧
  - block [gate:review] 现实覆盖 @ 生产数据/scene_embed_第1集.json: 现实覆盖 场景语义嵌入(DINOv2) 适用却休眠：项目登记了它要查的数据，但交付前它没真跑（缺后端/sidecar）——「跑了数据却没执行一致性」正是这种休眠。装好后端真验，或显式 N2D_ALLOW_DEGRADED_QC=1 计债放行。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧
- block · shot:score_第1集.json · 场景/构图连续性 / 多模态漂移
  - block [score] 场景/构图连续性 @ 生产数据/score_第1集.json: 场景/构图连续性: status=fail score=0 block=4 warn=32
  - warn [score] 多模态漂移 @ 生产数据/score_第1集.json: 多模态漂移: status=warn score=88 block=0 warn=8
- block · shot:成片 · 进度凭据对账
  - block [gate:review] 进度凭据对账 @ 第1集/成片: 进度凭据对账 进度「成片」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：compose 仍有 3 个 block 级问题（见 gate_findings_compose_第1集.json）。修掉 block 后重跑 → python3 skills/n2d-dashboard/scripts/dashboard.py gate "创作区
- warn · asset:EP01_CLIP02 · UI/系统面板/HUD 一致性
  - warn [review-ui] UI/系统面板/HUD 一致性 @ EP01_CLIP02: UI/系统面板/HUD 一致性 系统面板(UI1) detail: 检出 6 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 定位镜头：Clip_02 定位产物：设定库/ui_a
- warn · asset:WEAPON_01 · 人物在场链
  - warn [gate:image_preflight] 人物在场链 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#5→clip#6: 人物在场链 实体在下一 Clip 出现但缺入画/换场解释：WEAPON_01。若是新入场，请把 entry_exit 写成机器真值。
  - warn [gate:video_preflight] 人物在场链 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#5→clip#6: 人物在场链 实体在下一 Clip 出现但缺入画/换场解释：WEAPON_01。若是新入场，请把 entry_exit 写成机器真值。
  - warn [gate:video_prompt_preflight] 人物在场链 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#5→clip#6: 人物在场链 实体在下一 Clip 出现但缺入画/换场解释：WEAPON_01。若是新入场，请把 entry_exit 写成机器真值。
- warn · asset:asset · image_prompt_lint
  - warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/
  - warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场
  - warn [detect] image_prompt_lint: image_prompt_lint  None 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden
- warn · asset:asset_registry.json asset#1 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#3 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_prompt_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变

## 依赖传播

- nodes=104 · edges=228 · clips=11 · images=31 · videos=16
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
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村村口与村道（LOC_03） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱金光（VFX_百妖谱金光） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| GROUP_飞鹰门众人（GROUP_飞鹰门众人） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| GROUP_狼妖群（GROUP_狼妖群） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [warn] multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本
- [warn] multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本

## 🟡 陈青源（CHAR_04）
- [warn] character_consistency  CHAR_04__常态 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） 
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_04/常态「基础」（出图/共享/图片/定妆_CHAR_04__常态

## 🟡 青面郎君（CHAR_05）
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态

## 🟡 虎山神 / 虎妖（CHAR_03）
- [warn] image_prompt_lint  None 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：近景
- [warn] image_prompt_lint  None 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：缺『
- [warn] image_prompt_lint  None 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_

## 🟡 裴长青（CHAR_02）
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸
- [warn] image_prompt_lint  None 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchan
- [warn] image_prompt_lint  None 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchan

## 🟡 百妖谱金光（VFX_百妖谱金光）
- [warn] image_prompt_lint  None 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：
- [warn] image_prompt_lint  None 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel
- [warn] image_prompt_lint  None 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reve

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  色温调色(GRADE1)   图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs
- [warn]  色温调色(GRADE1)   图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243
- [warn]  色温调色(GRADE1)   图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 v
- [warn]  色温调色(GRADE1)   图片/Clip08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.127 v
- [warn]  色温调色(GRADE1)   图片/Clip08_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.14 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
