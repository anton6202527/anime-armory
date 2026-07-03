# 验收总账 · 第2集

- 验收状态：阻断
- ⛔ block 2 · 🔴 high 0 · 🟡 medium 23

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 90 | detect, gate:image_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 角色 | 🟡 warn | 0 | 0 | 182 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video |
| 资产 | 🟡 warn | 0 | 0 | 58 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 镜头 | ⛔ block | 3 | 0 | 200 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 音频 | 🟡 warn | 0 | 0 | 15 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 7 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 8 | 0 | 55 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video, score |

### 剧情问题
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜3后应保持 `十四岁瘦削少年，粗布杂役服，初见破盆异状时茫然。`，但镜5 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜3后应保持 `十四岁瘦削少年，粗布杂役服，初见破盆异状时茫然。`，但镜9 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜17后应保持 `深夜披衣，困倦、疲惫、克制。`，但镜18 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜17后应保持 `深夜披衣，困倦、疲惫、克制。`，但镜20 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜17后应保持 `深夜披衣，困倦、疲惫、克制。`，但镜22 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜17后应保持 `深夜披衣，困倦、疲惫、克制。`，但镜23 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜17后应保持 `深夜披衣，困倦、疲惫、克制。`，但镜25 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜17后应保持 `深夜披衣，困倦、疲惫、克制。`，但镜27 prompt 未见状态锁。 

### 角色问题
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆/水桶与扁担 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景

### 资产问题
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[秀竹峰杂役院.png] 跨集色调/光位漂移 L1=1.33（vs 前 1 集基线，阈 warn=0.45）——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[秀竹峰杂役院.png] 跨集结构漂移 dHash 汉明=35（vs 前 1 集结构原型，阈 warn=18）——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG__, CHAR_JIANG_JIAN, CHAR_TAIXUMEN_ZHANGLAO, CHAR_ZHANG_LAODA）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_贺平生杂役小屋.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_贺平生杂役小屋_反打.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_后山挑水路.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 音频问题
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「16-30s：泼水瞬间给一个"哗"的」→「30-44s：白日挑水压缩段，扁担吱」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「山路挑水：扁担摩擦肩膀、水桶摇晃、急」→「机缘主题（破盆异象）：极轻空灵金属泛」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「机缘主题（破盆异象）：极轻空灵金属泛」→「不用欢快仙侠主题曲；不用史诗大合唱。」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=88863180b1df2f34，但复跑审计证据不完整。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=8a71a91fbbbc3a12，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第2集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): 张老大 锚点门(N3)    
- warn [detect] 锚点门(N3): 贺平生 锚点门(N3)    
- warn [detect] 锚点门(N3): 韩老三 锚点门(N3)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- block [detect] 风格(S1):  风格(S1)    

## 根因聚合

- block · ops:ops · 锚点门(N3) / 风格(S1) / 糊/低质(N4) / 天气时辰(W1) / 物理事件图(PHY) / 成本路由(K1) / 人审校准集(CAL) / 一致性探针包(PROBE)
  - warn [detect] 锚点门(N3): 张老大 锚点门(N3)    
  - warn [detect] 锚点门(N3): 贺平生 锚点门(N3)    
  - warn [detect] 锚点门(N3): 韩老三 锚点门(N3)    
- block · ops:production_events.jsonl · 强配方Schema(RCP2) / 生成配方(RCP)
  - block [gate:video] 强配方Schema(RCP2) @ 生产数据/production_events.jsonl: 强配方Schema(RCP2) [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_
  - block [gate:video] 强配方Schema(RCP2) @ 生产数据/production_events.jsonl: 强配方Schema(RCP2) [production一致性升级:重复同维度] 合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifac
  - block [gate:video] 生成配方(RCP) @ 生产数据/production_events.jsonl: 生成配方(RCP) [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=88863180b1df2f34，但复跑审计证据不完整。
- block · ops:score_第2集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第2集.json: 缺 score JSON；验收总账无法闭环
- block · shot:图片 · 风格(S1)
  - warn [gate:image] 风格(S1) @ 出图/第2集/图片: 风格(S1) [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题
  - warn [gate:image] 风格(S1) @ 出图/第2集/图片: 风格(S1) [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题
  - warn [gate:image] 风格(S1) @ 出图/第2集/图片: 风格(S1) [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题
- warn · asset:asset · 交互接触(I1) / 结构化交互图谱(I2) / 成本路由(K1)
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn · asset:asset_registry.json asset#1 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#10 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#10: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#10: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#10: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#6 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#6: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#6: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#6: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#7 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#7: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#7: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ 创作区/制漫剧/仙界闭关小能手/出图/共享/asset_registry.json asset#7: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · audio:audio · 音乐衔接(BGM) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1) / 环境声(AMB)
  - warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「16-30s：泼水瞬间给一个"哗"的」→「30-44s：白日挑水压缩段，扁担吱」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
  - warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「山路挑水：扁担摩擦肩膀、水桶摇晃、急」→「机缘主题（破盆异象）：极轻空灵金属泛」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
  - warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「机缘主题（破盆异象）：极轻空灵金属泛」→「不用欢快仙侠主题曲；不用史诗大合唱。」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn · audio:第2集 · 配音
  - warn [gate:image_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image_prompt_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
- warn · character:Clip16_end.png · character_consistency
  - warn [detect] character_consistency @ 图片/Clip16_end.png: character_consistency  图片/Clip16_end.png 发型 H1 初筛：图片/Clip16_end.png（发色/发型轮廓离群，非阻断） 
  - warn [gate:image] character_consistency @ 图片/Clip16_end.png: character_consistency 发型 H1 初筛：图片/Clip16_end.png（发色/发型轮廓离群，非阻断）

## 依赖传播

- nodes=135 · edges=365 · clips=27 · images=53 · videos=0
- graph: `创作区/制漫剧/仙界闭关小能手/生产数据/consistency_dependency_graph_第2集.json`

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
| 贺平生（CHAR_HE_PINGSHENG） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 张老大（CHAR_ZHANG_LAODA） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 韩老三（CHAR_HAN_LAOSAN） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 江剑（CHAR_JIANG_JIAN） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 贺平生杂役小屋（LOC_ZAYI_HUT） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 黑陶破盆（PROP_HEI_TAO_PEN） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 碧绿灵水（PROP_GREEN_WATER） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 盆底微绿亮点（VFX_BASIN_MICROGLOW） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 水桶与扁担（PROP_SHUI_TONG） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 后山挑水路（LOC_HOUSHAN_WATER_PATH） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 杂役饭棚（LOC_ZAYI_FOOD_YARD） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 杂役饭碗（PROP_FOOD_BOWL） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 两口巨大水缸（PROP_WATER_JARS） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 杂役院水缸区（LOC_ZAYI_WATER_JARS） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 灵米布袋（PROP_SPIRIT_RICE_BAG） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 灰败灵米（PROP_GRAY_RICE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 贺三杰（CHAR_HE_SANJIE） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 群杂役（CROWD_ZAYI） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 太虚门远景修士剪影（CROWD_TAIXU_CULTIVATOR） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🟡 贺平生（CHAR_HE_PINGSHENG）
- [warn] 贺平生 锚点门(N3)    
- [warn] 贺平生 脸(G1)    
- [warn] 贺平生 发型(H1)    

## 🟡 张老大（CHAR_ZHANG_LAODA）
- [warn] 张老大 锚点门(N3)    
- [warn]  状态百科(P1)   张老大 在镜14后应保持 `早饭场粗声关照，表情像好意但压迫。`，但镜15 prompt 未见状态锁。 
- [warn]  状态百科(P1)   张老大 在镜14后应保持 `早饭场粗声关照，表情像好意但压迫。`，但镜16 prompt 未见状态锁。 

## 🟡 韩老三（CHAR_HAN_LAOSAN）
- [warn] 韩老三 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG, CHAR_HE_PI
- [warn] character_consistency  韩老三 锚点门 N3：韩老三 主参考非单张清晰正脸（非阻断） 

## 🟡 江剑（CHAR_JIANG_JIAN）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG, CHAR_HE_PI

## 🟡 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HE_PINGSHENG, CHAR_HE_PI

## 🟡 贺平生杂役小屋（LOC_ZAYI_HUT）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_贺平生杂役小屋.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_贺平生杂役小屋_反打.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 黑陶破盆（PROP_HEI_TAO_PEN）
- [warn]  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- [warn]  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- [warn]  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景

## 🟡 碧绿灵水（PROP_GREEN_WATER）
- [warn]  状态百科(P1)   黑陶破盆 的状态 `满盆碧绿灵水，盆底微绿亮点。` 声明至镜7，但镜26 仍保留。 
- [warn]  状态百科(P1)   黑陶破盆 的状态 `满盆碧绿灵水，盆底微绿亮点。` 声明至镜7，但镜27 仍保留。 
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_碧绿灵水.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 🟡 盆底微绿亮点（VFX_BASIN_MICROGLOW）
- [warn]  状态百科(P1)   黑陶破盆 的状态 `满盆碧绿灵水，盆底微绿亮点。` 声明至镜7，但镜26 仍保留。 
- [warn]  状态百科(P1)   黑陶破盆 的状态 `满盆碧绿灵水，盆底微绿亮点。` 声明至镜7，但镜27 仍保留。 
- [warn]  成本路由(K1)   出图/共享/图片/定妆_特效_盆底微绿亮点.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 水桶与扁担（PROP_SHUI_TONG）
- [warn]  无脸崩坏(G1b)    黑陶破盆/水桶与扁担 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- [warn]  无脸崩坏(G1b)    黑陶破盆/水桶与扁担 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- [warn]  无脸崩坏(G1b)    水桶与扁担 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景

## 🟡 后山挑水路（LOC_HOUSHAN_WATER_PATH）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_后山挑水路.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_后山挑水路_反打.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 杂役饭棚（LOC_ZAYI_FOOD_YARD）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_杂役饭棚.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_杂役饭棚_反打.png 生成事件缺 cost/provider 记账；无法计算重试性价

## 🟡 杂役饭碗（PROP_FOOD_BOWL）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_杂役饭碗.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 🟡 杂役院水缸区（LOC_ZAYI_WATER_JARS）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_杂役院水缸区.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_杂役院水缸区_反打.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 灵米布袋（PROP_SPIRIT_RICE_BAG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_灵米布袋.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 🟡 灰败灵米（PROP_GRAY_RICE）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_灰败灵米.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模
- [warn] image_prompt_lint  None 镜头 25（`EP02_CLIP25` · 灰败灵米揭克扣 · ）：近景/特写镜头缺乏物理镜
- [warn] image_prompt_lint  None 镜头 27（`EP02_CLIP27` · 灰败灵米唤醒盆底微光 · ）：近景/特写镜头缺乏

## 未归属到具体角色/资产的一致性问题
- [warn]  跨集场景漂移(SCNX)    场景[秀竹峰杂役院.png] 跨集色调/光位漂移 L1=1.33（vs 前 1 集基线，阈 warn=0.
- [warn]  跨集场景漂移(SCNX)    场景[秀竹峰杂役院.png] 跨集结构漂移 dHash 汉明=35（vs 前 1 集结构原型，阈 warn
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [block]  风格(S1)    
- [block]  风格(S1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
