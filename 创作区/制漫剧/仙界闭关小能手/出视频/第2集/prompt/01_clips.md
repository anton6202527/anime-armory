# 第2集 出视频逐镜 Prompt

## 剧本可看性合同 · 留存承诺账本
- R01: hook_id=EP01_TAIL_PAYOFF；promise=黑陶破盆微光意味着什么；opened_at=第1集尾钩；payoff_due=EP02_CLIP01-02；payoff_clip=EP02_CLIP01-02；payoff_evidence=半盆清水变满盆碧绿灵水，盆底微绿亮点游动。；payoff_status=paid
- R02: hook_id=EP02_MID_LOSS；promise=主角错倒掉的究竟是什么；opened_at=EP02_CLIP07；payoff_due=EP02_CLIP09；payoff_clip=EP02_CLIP09；payoff_evidence=旁白确认那是破盆第一次把凡水炼成灵水。；payoff_status=paid
- R03: hook_id=EP02_RICE_SHORT；promise=张老大说的十斤灵米是真是假；opened_at=EP02_CLIP20；payoff_due=EP02_CLIP24-25；payoff_clip=EP02_CLIP24-25；payoff_evidence=贺平生凭旧经验看出最多五斤，且米色灰败。；payoff_status=paid
- R04: hook_id=EP02_TAIL_RICE_CHANGE；promise=灰败灵米倒进破盆后会变成什么；opened_at=EP02_CLIP27；payoff_due=第3集冷开场；payoff_status=open；expected_next_handling=第3集冷开场必须兑现米变金或同等明确变化。
## 剧本可看性合同 · 观众问题账本
- Q01: question_id=Q01；signal=任务；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context=白日挑水十五趟压缩交代；明日还要二十趟，是不可能完成的任务。💥 - 44-58s 早饭张老大让老鲍多打肉，贺平生以
- Q02: question_id=Q02；signal=证据；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context=的破陶盆，此刻盆底正有一缕微光，缓缓游动。 | 延长异常证据，让观众确认破盆不是普通旧物。 | | EP02_CLI
- Q03: question_id=Q03；signal=任务；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context=> 十五趟挑水后天色全黑，贺平生疲惫回屋。 | 观众感到任务数量不合理。 | | EP02_CLIP12 | CU
- Q04: question_id=Q04；signal=证据；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context=ence_payoff": "本集给“破盆会变”的第一次证据，并在集尾用灰败灵米再次触发微光，承诺第3集米变金。"
- Q05: question_id=Q05；signal=为什么；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context="Q01", "question": "破盆为什么能把水变成灵水？", "opened_at"
- Q06: question_id=Q06；signal=证据；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context="dramatic_function": "延长异常证据，让观众确认破盆不是普通旧物。", "aud
- Q07: question_id=Q07；signal=任务；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context="audience_effect": "观众感到任务数量不合理。", "description"
- Q08: question_id=Q08；signal=系统；status=paid_or_progressed；expected_next_handling=本集兑现/推进；question_context=对白信息变成空间压迫：吃饭处和水缸区相邻，观众先看见劳动系统，再听到假关照。" }, {


生成后自检流程：按每个 Clip 的「自检（生成后逐条过）」逐条确认，未通过进入废料重跑。

## Clip 01（时长 5.76s · EP02_CLIP01 · 冷开·破盆满出碧绿灵水）
剧本可看性合同：dramatic_function=兑现上集破盆微光，直接给出本集核心异常。；audience_effect=观众在前三秒获得“破盆真的变了”的奇观答案。。

**首帧**：`出图/第2集/图片/Clip01_first.png`
**尾帧**：`出图/第2集/图片/Clip01_end.png`
导演意图：兑现上集破盆微光，直接给出本集核心异常。；为什么这样拍：观众在前三秒获得“破盆真的变了”的奇观答案。。
起幅：清晨小屋内，黑陶破盆放在窗边，半盆清水已变成满满一盆碧绿水。
落幅：清晨小屋内，黑陶破盆盛满碧绿水，盆沿冷光清楚。
场面调度：required_presence=PROP_HEI_TAO_PEN,PROP_GREEN_WATER,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 黑陶破盆占满画面，半盆清水已涨成满盆碧绿，屋内清晨冷光贴着盆沿。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 清晨小屋内，黑陶破盆放在窗边，半盆清水已变成满满一盆碧绿水。
- action: 黑陶破盆占满画面，半盆清水已涨成满盆碧绿，屋内清晨冷光贴着盆沿。
- end_state: 清晨小屋内，黑陶破盆盛满碧绿水，盆沿冷光清楚。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：无人物/空镜；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=none;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_01; allowed_voiceover_indices=[1]
- allowed_narration_indices=[1]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 1. 旁白: 不对劲——一夜之间，半盆清水，竟然变成了满满一盆碧绿灵水。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：无人物；只做道具/光效/环境微动。
镜头运动：ECU 俯拍微推；速度克制，服务本镜情绪，不乱甩。
情绪节奏：首屏钩子·静物异常。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW 的结构和数量。
衔接约束：从 清晨小屋内，黑陶破盆放在窗边，半盆清水已变成满满一盆碧绿水。 开始，只执行本镜动作，落到 清晨小屋内，黑陶破盆盛满碧绿水，盆沿冷光清楚。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：无；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 黑陶破盆占满画面，半盆清水已涨成满盆碧绿，屋内清晨冷光贴着盆沿。. Preserve character identity (无), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 02（时长 5.96s · EP02_CLIP02 · 盆底一缕微光游动）
剧本可看性合同：dramatic_function=延长异常证据，让观众确认破盆不是普通旧物。；audience_effect=观众确认这是持续异常，不是单帧错觉。。

**首帧**：`出图/第2集/图片/Clip02_first.png`
**尾帧**：`出图/第2集/图片/Clip02_end.png`
导演意图：延长异常证据，让观众确认破盆不是普通旧物。；为什么这样拍：观众确认这是持续异常，不是单帧错觉。。
起幅：清晨小屋内，黑陶破盆盛满碧绿水，盆沿冷光清楚。
落幅：破盆水下的微绿亮点在盆底缓慢游动。
场面调度：required_presence=PROP_HEI_TAO_PEN,PROP_GREEN_WATER,VFX_BASIN_MICROGLOW,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 镜头压到盆底，一缕细小微光在碧绿水下慢慢游动，周围仍像普通破盆。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 清晨小屋内，黑陶破盆盛满碧绿水，盆沿冷光清楚。
- action: 镜头压到盆底，一缕细小微光在碧绿水下慢慢游动，周围仍像普通破盆。
- end_state: 破盆水下的微绿亮点在盆底缓慢游动。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_02; allowed_voiceover_indices=[2]
- allowed_narration_indices=[2]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 2. 旁白: 那只昨夜还黑乎乎的破陶盆，此刻盆底正有一缕微光，缓缓游动。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：镜头压到盆底，一缕细小微光在碧绿水下慢慢游动，周围仍像普通破盆。。
镜头运动：ECU 固定微动；速度克制，服务本镜情绪，不乱甩。
情绪节奏：冷开延迟·微光停顿。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW 的结构和数量。
衔接约束：从 清晨小屋内，黑陶破盆盛满碧绿水，盆沿冷光清楚。 开始，只执行本镜动作，落到 破盆水下的微绿亮点在盆底缓慢游动。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 镜头压到盆底，一缕细小微光在碧绿水下慢慢游动，周围仍像普通破盆。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 03（时长 1.55s · EP02_CLIP03 · 贺平生僵住）
剧本可看性合同：dramatic_function=让主角第一次接触异常，但保持无知。；audience_effect=观众看见主角还没理解价值，产生替他急。。

**首帧**：`出图/第2集/图片/Clip03_first.png`
**尾帧**：`出图/第2集/图片/Clip03_end.png`
导演意图：让主角第一次接触异常，但保持无知。；为什么这样拍：观众看见主角还没理解价值，产生替他急。。
起幅：破盆水下的微绿亮点在盆底缓慢游动。
落幅：贺平生站在门边，目光落到破盆上。
场面调度：required_presence=CHAR_HE_PINGSHENG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生站在门边僵住，十四岁瘦小身形被清晨冷光切出轮廓。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 破盆水下的微绿亮点在盆底缓慢游动。
- action: 贺平生站在门边僵住，十四岁瘦小身形被清晨冷光切出轮廓。
- end_state: 贺平生站在门边，目光落到破盆上。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_03; allowed_voiceover_indices=[3]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[3]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 3. 贺平生: 这……
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生站在门边僵住，十四岁瘦小身形被清晨冷光切出轮廓。。
镜头运动：CU 静停；速度克制，服务本镜情绪，不乱甩。
情绪节奏：短促反应。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW 的结构和数量。
衔接约束：从 破盆水下的微绿亮点在盆底缓慢游动。 开始，只执行本镜动作，落到 贺平生站在门边，目光落到破盆上。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生站在门边僵住，十四岁瘦小身形被清晨冷光切出轮廓。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 04（时长 5.76s · EP02_CLIP04 · 误判满盆绿水）
剧本可看性合同：dramatic_function=建立主角误判的逻辑基础。；audience_effect=观众理解主角误判不是蠢，而是信息不足。。

**首帧**：`出图/第2集/图片/Clip04_first.png`
**尾帧**：`出图/第2集/图片/Clip04_end.png`
导演意图：建立主角误判的逻辑基础。；为什么这样拍：观众理解主角误判不是蠢，而是信息不足。。
起幅：贺平生站在门边，目光落到破盆上。
落幅：贺平生弯身看盆，困惑未解。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,PROP_GREEN_WATER,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生弯身看向盆里，困惑写在脸上，碧绿水面占画面下半部。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生站在门边，目光落到破盆上。
- action: 贺平生弯身看向盆里，困惑写在脸上，碧绿水面占画面下半部。
- end_state: 贺平生弯身看盆，困惑未解。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_04; allowed_voiceover_indices=[4]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[4]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 4. 贺平生: 我昨晚分明只舀了半盆清水，怎么一夜就满了，还绿成这样？
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生弯身看向盆里，困惑写在脸上，碧绿水面占画面下半部。。
镜头运动：MCU 轻推；速度克制，服务本镜情绪，不乱甩。
情绪节奏：误判建立。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN 的结构和数量。
衔接约束：从 贺平生站在门边，目光落到破盆上。 开始，只执行本镜动作，落到 贺平生弯身看盆，困惑未解。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生弯身看向盆里，困惑写在脸上，碧绿水面占画面下半部。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 05（时长 6.28s · EP02_CLIP05 · 近看判作腐坏）
剧本可看性合同：dramatic_function=把观众先知和主角误判拉开差距。；audience_effect=观众的先知感增强，期待他别倒掉。。

**首帧**：`出图/第2集/图片/Clip05_first.png`
**尾帧**：`出图/第2集/图片/Clip05_end.png`
导演意图：把观众先知和主角误判拉开差距。；为什么这样拍：观众的先知感增强，期待他别倒掉。。
起幅：贺平生弯身看盆，困惑未解。
落幅：碧绿水面被误认为腐坏水，盆仍停在屋内。
场面调度：required_presence=PROP_HEI_TAO_PEN,PROP_GREEN_WATER,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 水面近景发绿发浑，盆沿旧缺口清楚，观众能看出异常但少年只觉得坏了。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生弯身看盆，困惑未解。
- action: 水面近景发绿发浑，盆沿旧缺口清楚，观众能看出异常但少年只觉得坏了。
- end_state: 碧绿水面被误认为腐坏水，盆仍停在屋内。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_05; allowed_voiceover_indices=[5]
- allowed_narration_indices=[5]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 5. 旁白: 离得近了他才看清，那水是真绿，碧绿碧绿的，像是整盆都腐坏透了。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：水面近景发绿发浑，盆沿旧缺口清楚，观众能看出异常但少年只觉得坏了。。
镜头运动：ECU 水面细节；速度克制，服务本镜情绪，不乱甩。
情绪节奏：观众先知压力。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN 的结构和数量。
衔接约束：从 贺平生弯身看盆，困惑未解。 开始，只执行本镜动作，落到 碧绿水面被误认为腐坏水，盆仍停在屋内。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 水面近景发绿发浑，盆沿旧缺口清楚，观众能看出异常但少年只觉得坏了。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 06（时长 4.64s · EP02_CLIP06 · 决定不用破盆盛水）
剧本可看性合同：dramatic_function=让误判进入行动前的决定点。；audience_effect=观众预感错失即将发生。。

**首帧**：`出图/第2集/图片/Clip06_first.png`
**尾帧**：`出图/第2集/图片/Clip06_end.png`
导演意图：让误判进入行动前的决定点。；为什么这样拍：观众预感错失即将发生。。
起幅：碧绿水面被误认为腐坏水，盆仍停在屋内。
落幅：贺平生决定不再用破盆盛水，手已伸向盆沿。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,PROP_GREEN_WATER,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生皱眉后退半步，把破盆从盛水容器降级成杂物。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 碧绿水面被误认为腐坏水，盆仍停在屋内。
- action: 贺平生皱眉后退半步，把破盆从盛水容器降级成杂物。
- end_state: 贺平生决定不再用破盆盛水，手已伸向盆沿。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_06; allowed_voiceover_indices=[6]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[6]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 6. 贺平生: 才一夜就变质……这盆子，以后可不能再用来盛水了。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生皱眉后退半步，把破盆从盛水容器降级成杂物。。
镜头运动：MS 固定；速度克制，服务本镜情绪，不乱甩。
情绪节奏：务实误解。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN 的结构和数量。
衔接约束：从 碧绿水面被误认为腐坏水，盆仍停在屋内。 开始，只执行本镜动作，落到 贺平生决定不再用破盆盛水，手已伸向盆沿。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生皱眉后退半步，把破盆从盛水容器降级成杂物。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 07（时长 6.35s · EP02_CLIP07 · 整盆灵水泼出窗外）
剧本可看性合同：dramatic_function=完成揪心反差，错失第一盆灵水。；audience_effect=观众获得本集第一次强烈揪心反差。。

**首帧**：`出图/第2集/图片/Clip07_first.png`
**尾帧**：`出图/第2集/图片/Clip07_end.png`
导演意图：完成揪心反差，错失第一盆灵水。；为什么这样拍：观众获得本集第一次强烈揪心反差。。
起幅：贺平生决定不再用破盆盛水，手已伸向盆沿。
落幅：碧绿水被倒出窗外，破盆变空。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,PROP_GREEN_WATER,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 少年端起破盆向窗外一倒，碧绿水流从画面边缘倾出，只保留一个干净动作。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生决定不再用破盆盛水，手已伸向盆沿。
- action: 少年端起破盆向窗外一倒，碧绿水流从画面边缘倾出，只保留一个干净动作。
- end_state: 碧绿水被倒出窗外，破盆变空。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_07; allowed_voiceover_indices=[7]
- allowed_narration_indices=[7]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 7. 旁白: 他没有多想，端起盆，把那一整盆碧绿，‖全泼到了窗外。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：少年端起破盆向窗外一倒，碧绿水流从画面边缘倾出，只保留一个干净动作。。
镜头运动：MS 动作侧面；速度克制，服务本镜情绪，不乱甩。
情绪节奏：反差爆点。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN 的结构和数量。
衔接约束：从 贺平生决定不再用破盆盛水，手已伸向盆沿。 开始，只执行本镜动作，落到 碧绿水被倒出窗外，破盆变空。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 少年端起破盆向窗外一倒，碧绿水流从画面边缘倾出，只保留一个干净动作。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 08（时长 2.32s · EP02_CLIP08 · 洗衣盆误用落点）
剧本可看性合同：dramatic_function=用务实小句把神器级价值降成生活旧物。；audience_effect=观众被生活化误用逗出苦笑。。

**首帧**：`出图/第2集/图片/Clip08_first.png`
**尾帧**：`出图/第2集/图片/Clip08_end.png`
导演意图：用务实小句把神器级价值降成生活旧物。；为什么这样拍：观众被生活化误用逗出苦笑。。
起幅：碧绿水被倒出窗外，破盆变空。
落幅：空破盆被当作洗衣旧盆放回屋内。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 空盆回到屋内，贺平生随手放下，语气像在处理一件普通旧物。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 碧绿水被倒出窗外，破盆变空。
- action: 空盆回到屋内，贺平生随手放下，语气像在处理一件普通旧物。
- end_state: 空破盆被当作洗衣旧盆放回屋内。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_08; allowed_voiceover_indices=[8]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[8]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 8. 贺平生: 以后……就拿它洗衣服吧。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：空盆回到屋内，贺平生随手放下，语气像在处理一件普通旧物。。
镜头运动：CU 手边道具；速度克制，服务本镜情绪，不乱甩。
情绪节奏：荒诞落点。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN 的结构和数量。
衔接约束：从 碧绿水被倒出窗外，破盆变空。 开始，只执行本镜动作，落到 空破盆被当作洗衣旧盆放回屋内。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 空盆回到屋内，贺平生随手放下，语气像在处理一件普通旧物。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GREEN_WATER、PROP_HEI_TAO_PEN), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 09（时长 6.34s · EP02_CLIP09 · 旁白确认灵水价值）
剧本可看性合同：dramatic_function=确认错失价值，形成观众替主角着急的爽前压抑。；audience_effect=观众明确知道主角损失了什么。。

**首帧**：`出图/第2集/图片/Clip09_first.png`
**尾帧**：`出图/第2集/图片/Clip09_end.png`
导演意图：确认错失价值，形成观众替主角着急的爽前压抑。；为什么这样拍：观众明确知道主角损失了什么。。
起幅：空破盆被当作洗衣旧盆放回屋内。
落幅：破盆空置墙角，观众知道灵水已被错失。
场面调度：required_presence=PROP_HEI_TAO_PEN,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 破盆空空停在墙角，盆底残留一粒微绿亮点，观众理解错失价值。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 空破盆被当作洗衣旧盆放回屋内。
- action: 破盆空空停在墙角，盆底残留一粒微绿亮点，观众理解错失价值。
- end_state: 破盆空置墙角，观众知道灵水已被错失。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_09; allowed_voiceover_indices=[9]
- allowed_narration_indices=[9]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 9. 旁白: 他不知道，那不是腐水，而是破盆第一次把凡水炼成了灵水。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：破盆空空停在墙角，盆底残留一粒微绿亮点，观众理解错失价值。。
镜头运动：ECU 物件停拍；速度克制，服务本镜情绪，不乱甩。
情绪节奏：旁白补刀。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_HEI_TAO_PEN、PROP_SHUI_TONG 的结构和数量。
衔接约束：从 空破盆被当作洗衣旧盆放回屋内。 开始，只执行本镜动作，落到 破盆空置墙角，观众知道灵水已被错失。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 破盆空空停在墙角，盆底残留一粒微绿亮点，观众理解错失价值。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_HEI_TAO_PEN、PROP_SHUI_TONG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 10（时长 4.82s · EP02_CLIP10 · 破盆被丢回墙角）
剧本可看性合同：dramatic_function=把剧情从灵水错失推到现实劳役压力。；audience_effect=观众从奇物线回到生存线，节奏不悬空。。

**首帧**：`出图/第2集/图片/Clip10_first.png`
**尾帧**：`出图/第2集/图片/Clip10_end.png`
导演意图：把剧情从灵水错失推到现实劳役压力。；为什么这样拍：观众从奇物线回到生存线，节奏不悬空。。
起幅：破盆空置墙角，观众知道灵水已被错失。
落幅：贺平生挑起水桶离开小屋。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,PROP_SHUI_TONG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 破盆被搁在墙角，贺平生挑起水桶离屋，画面转入白日劳作。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 破盆空置墙角，观众知道灵水已被错失。
- action: 破盆被搁在墙角，贺平生挑起水桶离屋，画面转入白日劳作。
- end_state: 贺平生挑起水桶离开小屋。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_10; allowed_voiceover_indices=[10]
- allowed_narration_indices=[10]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 10. 旁白: 哐啷一声把盆丢在墙角，贺平生挑起水桶，又往后山去了。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：破盆被搁在墙角，贺平生挑起水桶离屋，画面转入白日劳作。。
镜头运动：MS 空屋切出；速度克制，服务本镜情绪，不乱甩。
情绪节奏：白日转场。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_HEI_TAO_PEN、PROP_SHUI_TONG 的结构和数量。
衔接约束：从 破盆空置墙角，观众知道灵水已被错失。 开始，只执行本镜动作，落到 贺平生挑起水桶离开小屋。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 破盆被搁在墙角，贺平生挑起水桶离屋，画面转入白日劳作。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_HEI_TAO_PEN、PROP_SHUI_TONG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 11（时长 6.08s · EP02_CLIP11 · 十五趟挑水压到天黑）
剧本可看性合同：dramatic_function=用压缩劳动把挑水数量升级为身体压力。；audience_effect=观众感到任务数量不合理。。

**首帧**：`出图/第2集/图片/Clip11_first.png`
**尾帧**：`出图/第2集/图片/Clip11_end.png`
导演意图：用压缩劳动把挑水数量升级为身体压力。；为什么这样拍：观众感到任务数量不合理。。
起幅：贺平生挑起水桶离开小屋。
落幅：十五趟挑水后天色全黑，贺平生疲惫回屋。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_SHUI_TONG,LOC_HOUSHAN_WATER_PATH；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 挑水路以三段压缩：肩上扁担、桶内水晃、天色由亮转黑。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生挑起水桶离开小屋。
- action: 挑水路以三段压缩：肩上扁担、桶内水晃、天色由亮转黑。
- end_state: 十五趟挑水后天色全黑，贺平生疲惫回屋。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_11; allowed_voiceover_indices=[11]
- allowed_narration_indices=[11]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 11. 旁白: 昨日挑了五趟，今日要挑十五趟。等他把活全干完，天又黑透了。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：挑水路以三段压缩：肩上扁担、桶内水晃、天色由亮转黑。。
镜头运动：WS 压缩蒙太奇；速度克制，服务本镜情绪，不乱甩。
情绪节奏：压力升级压缩。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_HOUSHAN_WATER_PATH、PROP_HEI_TAO_PEN、PROP_SHUI_TONG 的结构和数量。
衔接约束：从 贺平生挑起水桶离开小屋。 开始，只执行本镜动作，落到 十五趟挑水后天色全黑，贺平生疲惫回屋。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 挑水路以三段压缩：肩上扁担、桶内水晃、天色由亮转黑。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_HOUSHAN_WATER_PATH、PROP_HEI_TAO_PEN、PROP_SHUI_TONG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 12（时长 6.11s · EP02_CLIP12 · 明日二十趟压力）
剧本可看性合同：dramatic_function=把明日二十趟变成下一个现实危机。；audience_effect=观众意识到明日压力更大。。

**首帧**：`出图/第2集/图片/Clip12_first.png`
**尾帧**：`出图/第2集/图片/Clip12_end.png`
导演意图：把明日二十趟变成下一个现实危机。；为什么这样拍：观众意识到明日压力更大。。
起幅：十五趟挑水后天色全黑，贺平生疲惫回屋。
落幅：贺平生坐在床沿发愁，明日二十趟压力落下。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_SHUI_TONG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 夜里贺平生坐在床沿喘息，肩颈红痕与空水桶说明十五趟的重量。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 十五趟挑水后天色全黑，贺平生疲惫回屋。
- action: 夜里贺平生坐在床沿喘息，肩颈红痕与空水桶说明十五趟的重量。
- end_state: 贺平生坐在床沿发愁，明日二十趟压力落下。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_12; allowed_voiceover_indices=[12]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[12]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 12. 贺平生: 十五趟就到极限了……明天二十趟，我到底怎么挑得动？
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：夜里贺平生坐在床沿喘息，肩颈红痕与空水桶说明十五趟的重量。。
镜头运动：CU 疲惫独白；速度克制，服务本镜情绪，不乱甩。
情绪节奏：明日压力落身。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_SHUI_TONG 的结构和数量。
衔接约束：从 十五趟挑水后天色全黑，贺平生疲惫回屋。 开始，只执行本镜动作，落到 贺平生坐在床沿发愁，明日二十趟压力落下。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 夜里贺平生坐在床沿喘息，肩颈红痕与空水桶说明十五趟的重量。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_SHUI_TONG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 13（时长 4.44s · EP02_CLIP13 · 早饭场转入假关照）
剧本可看性合同：dramatic_function=切入早饭场，为假关照铺地。；audience_effect=观众准备看张老大的新动作。。

**首帧**：`出图/第2集/图片/Clip13_first.png`
**尾帧**：`出图/第2集/图片/Clip13_end.png`
导演意图：切入早饭场，为假关照铺地。；为什么这样拍：观众准备看张老大的新动作。。
起幅：贺平生坐在床沿发愁，明日二十趟压力落下。
落幅：早饭饭棚建立，张老大的声音切入。
场面调度：required_presence=LOC_ZAYI_FOOD_YARD；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 饭棚晨光偏冷，粗木桌和大锅在前景，张老大的声音先到画面。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生坐在床沿发愁，明日二十趟压力落下。
- action: 饭棚晨光偏冷，粗木桌和大锅在前景，张老大的声音先到画面。
- end_state: 早饭饭棚建立，张老大的声音切入。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=none;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_13; allowed_voiceover_indices=[13]
- allowed_narration_indices=[13]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 13. 旁白: 也是这天早上，开饭时张老大特意吩咐了一句。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：饭棚晨光偏冷，粗木桌和大锅在前景，张老大的声音先到画面。。
镜头运动：WS 饭棚建立；速度克制，服务本镜情绪，不乱甩。
情绪节奏：假关照铺垫。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL、PROP_SHUI_TONG 的结构和数量。
衔接约束：从 贺平生坐在床沿发愁，明日二十趟压力落下。 开始，只执行本镜动作，落到 早饭饭棚建立，张老大的声音切入。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=veo 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 饭棚晨光偏冷，粗木桌和大锅在前景，张老大的声音先到画面。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL、PROP_SHUI_TONG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 14（时长 5.16s · EP02_CLIP14 · 张老大吩咐加肉）
剧本可看性合同：dramatic_function=张老大用关照话术隐藏剥削动机。；audience_effect=观众听出表面好意下的压迫。。

**首帧**：`出图/第2集/图片/Clip14_first.png`
**尾帧**：`出图/第2集/图片/Clip14_end.png`
导演意图：张老大用关照话术隐藏剥削动机。；为什么这样拍：观众听出表面好意下的压迫。。
起幅：早饭饭棚建立，张老大的声音切入。
落幅：张老大用关照口吻吩咐加肉。
场面调度：required_presence=CHAR_ZHANG_LAODA,PROP_FOOD_BOWL,LOC_ZAYI_FOOD_YARD；offscreen_presence=FUNCTION_LAO_BAO_OFFSCREEN；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 张老大半身入画，粗壮手掌按在桌边，笑意像关照但压住空气。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 早饭饭棚建立，张老大的声音切入。
- action: 张老大半身入画，粗壮手掌按在桌边，笑意像关照但压住空气。
- end_state: 张老大用关照口吻吩咐加肉。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_14; allowed_voiceover_indices=[14]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[14]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 14. 张老大: 老鲍，给这小子多打点肉，一定要吃饱——不然没力气挑水。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：张老大半身入画，粗壮手掌按在桌边，笑意像关照但压住空气。。
镜头运动：MS 单主体压迫；速度克制，服务本镜情绪，不乱甩。
情绪节奏：施恩口吻压迫。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL 的结构和数量。
衔接约束：从 早饭饭棚建立，张老大的声音切入。 开始，只执行本镜动作，落到 张老大用关照口吻吩咐加肉。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 张老大半身入画，粗壮手掌按在桌边，笑意像关照但压住空气。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 15（时长 1.55s · EP02_CLIP15 · 贺平生懵懂道谢）
剧本可看性合同：dramatic_function=证明少年仍相信底层规则里的小善意。；audience_effect=观众心疼少年太容易相信。。

**首帧**：`出图/第2集/图片/Clip15_first.png`
**尾帧**：`出图/第2集/图片/Clip15_end.png`
导演意图：证明少年仍相信底层规则里的小善意。；为什么这样拍：观众心疼少年太容易相信。。
起幅：张老大用关照口吻吩咐加肉。
落幅：贺平生捧碗道谢，仍把对方当好意。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_FOOD_BOWL,LOC_ZAYI_FOOD_YARD；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生捧碗抬头，眼里有受宠若惊的单纯。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 张老大用关照口吻吩咐加肉。
- action: 贺平生捧碗抬头，眼里有受宠若惊的单纯。
- end_state: 贺平生捧碗道谢，仍把对方当好意。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_15; allowed_voiceover_indices=[15]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[15]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 15. 贺平生: 谢谢张老大！
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生捧碗抬头，眼里有受宠若惊的单纯。。
镜头运动：CU 少年反应；速度克制，服务本镜情绪，不乱甩。
情绪节奏：幼年信任。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL、PROP_WATER_JARS 的结构和数量。
衔接约束：从 张老大用关照口吻吩咐加肉。 开始，只执行本镜动作，落到 贺平生捧碗道谢，仍把对方当好意。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生捧碗抬头，眼里有受宠若惊的单纯。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_FOOD_YARD、PROP_FOOD_BOWL、PROP_WATER_JARS), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 16（时长 8.70s · EP02_CLIP16 · 旁白点破真剥削）
剧本可看性合同：dramatic_function=把假关照的真意翻给观众，完成权力关系落点。；audience_effect=观众确认“关照”服务剥削，情绪转冷。。

**首帧**：`出图/第2集/图片/Clip16_first.png`
**尾帧**：`出图/第2集/图片/Clip16_end.png`
导演意图：把假关照的真意翻给观众，完成权力关系落点。；为什么这样拍：观众确认“关照”服务剥削，情绪转冷。。
起幅：贺平生捧碗道谢，仍把对方当好意。
落幅：两口水缸压住画面，观众明白关照服务于干活。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_WATER_JARS,LOC_ZAYI_WATER_JARS；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 两口水缸占据画面后部，贺平生小小身影被日常劳动压住。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生捧碗道谢，仍把对方当好意。
- action: 两口水缸占据画面后部，贺平生小小身影被日常劳动压住。
- end_state: 两口水缸压住画面，观众明白关照服务于干活。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_16; allowed_voiceover_indices=[16]
- allowed_narration_indices=[16]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 16. 旁白: 贺平生只当是关心。他还太小，看不出这“关照”里，护的从来不是他，是那两口必须挑满的水缸。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：两口水缸占据画面后部，贺平生小小身影被日常劳动压住。。
镜头运动：WS 水缸压迫；速度克制，服务本镜情绪，不乱甩。
情绪节奏：真意点破。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_WATER_JARS、PROP_FOOD_BOWL、PROP_WATER_JARS 的结构和数量。
衔接约束：从 贺平生捧碗道谢，仍把对方当好意。 开始，只执行本镜动作，落到 两口水缸压住画面，观众明白关照服务于干活。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 两口水缸占据画面后部，贺平生小小身影被日常劳动压住。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_WATER_JARS、PROP_FOOD_BOWL、PROP_WATER_JARS), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 17（时长 4.04s · EP02_CLIP17 · 夜里门板被拍响）
剧本可看性合同：dramatic_function=夜访开启第二段压迫，转入灵米事件。；audience_effect=观众进入夜间第二个悬念。。

**首帧**：`出图/第2集/图片/Clip17_first.png`
**尾帧**：`出图/第2集/图片/Clip17_end.png`
导演意图：夜访开启第二段压迫，转入灵米事件。；为什么这样拍：观众进入夜间第二个悬念。。
起幅：两口水缸压住画面，观众明白关照服务于干活。
落幅：深夜门板被拍响，贺平生从床上惊醒。
场面调度：required_presence=CHAR_HE_PINGSHENG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 深夜小屋内门板忽然震动，床上的少年被惊醒。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 两口水缸压住画面，观众明白关照服务于干活。
- action: 深夜小屋内门板忽然震动，床上的少年被惊醒。
- end_state: 深夜门板被拍响，贺平生从床上惊醒。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_17; allowed_voiceover_indices=[17]
- allowed_narration_indices=[17]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 17. 旁白: 这一夜他刚躺下，门外就传来了拍门声。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：深夜小屋内门板忽然震动，床上的少年被惊醒。。
镜头运动：CU 门板震动；速度克制，服务本镜情绪，不乱甩。
情绪节奏：夜访起势。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_WATER_JARS 的结构和数量。
衔接约束：从 两口水缸压住画面，观众明白关照服务于干活。 开始，只执行本镜动作，落到 深夜门板被拍响，贺平生从床上惊醒。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 深夜小屋内门板忽然震动，床上的少年被惊醒。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_WATER_JARS), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 18（时长 6.52s · EP02_CLIP18 · 张老大夜访寒暄）
剧本可看性合同：dramatic_function=张老大以熟络口吻降低少年戒心。；audience_effect=观众对张老大的笑产生警惕。。

**首帧**：`出图/第2集/图片/Clip18_first.png`
**尾帧**：`出图/第2集/图片/Clip18_end.png`
导演意图：张老大以熟络口吻降低少年戒心。；为什么这样拍：观众对张老大的笑产生警惕。。
起幅：深夜门板被拍响，贺平生从床上惊醒。
落幅：张老大进屋寒暄，手里布袋未打开。
场面调度：required_presence=CHAR_ZHANG_LAODA,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 张老大站在门内侧，布袋压在手里，脸上堆出熟络笑意。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 深夜门板被拍响，贺平生从床上惊醒。
- action: 张老大站在门内侧，布袋压在手里，脸上堆出熟络笑意。
- end_state: 张老大进屋寒暄，手里布袋未打开。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_18; allowed_voiceover_indices=[18]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[18]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 18. 张老大: 平生啊，今儿累不累？我都看见了，昨儿五趟，今儿十五趟，你也没歇着。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：张老大站在门内侧，布袋压在手里，脸上堆出熟络笑意。。
镜头运动：MS 门内压迫；速度克制，服务本镜情绪，不乱甩。
情绪节奏：假暖拉近。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT 的结构和数量。
衔接约束：从 深夜门板被拍响，贺平生从床上惊醒。 开始，只执行本镜动作，落到 张老大进屋寒暄，手里布袋未打开。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 张老大站在门内侧，布袋压在手里，脸上堆出熟络笑意。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 19（时长 1.55s · EP02_CLIP19 · 贺平生疲惫应答）
剧本可看性合同：dramatic_function=让少年疲惫状态暴露，便于被话术拿捏。；audience_effect=观众看见少年没有讨价还价的余力。。

**首帧**：`出图/第2集/图片/Clip19_first.png`
**尾帧**：`出图/第2集/图片/Clip19_end.png`
导演意图：让少年疲惫状态暴露，便于被话术拿捏。；为什么这样拍：观众看见少年没有讨价还价的余力。。
起幅：张老大进屋寒暄，手里布袋未打开。
落幅：贺平生低声承认疲惫。
场面调度：required_presence=CHAR_HE_PINGSHENG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生披衣站起，困倦和疲惫都压在短短回答里。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 张老大进屋寒暄，手里布袋未打开。
- action: 贺平生披衣站起，困倦和疲惫都压在短短回答里。
- end_state: 贺平生低声承认疲惫。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_19; allowed_voiceover_indices=[19]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[19]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 19. 贺平生: 有点……累。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生披衣站起，困倦和疲惫都压在短短回答里。。
镜头运动：CU 低声回答；速度克制，服务本镜情绪，不乱甩。
情绪节奏：疲惫低答。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_SPIRIT_RICE_BAG 的结构和数量。
衔接约束：从 张老大进屋寒暄，手里布袋未打开。 开始，只执行本镜动作，落到 贺平生低声承认疲惫。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生披衣站起，困倦和疲惫都压在短短回答里。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_SPIRIT_RICE_BAG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 20（时长 7.55s · EP02_CLIP20 · 十斤灵米施恩话术）
剧本可看性合同：dramatic_function=抛出十斤灵米的大承诺，制造施恩假象。；audience_effect=观众产生“真有十斤吗”的验账期待。。

**首帧**：`出图/第2集/图片/Clip20_first.png`
**尾帧**：`出图/第2集/图片/Clip20_end.png`
导演意图：抛出十斤灵米的大承诺，制造施恩假象。；为什么这样拍：观众产生“真有十斤吗”的验账期待。。
起幅：贺平生低声承认疲惫。
落幅：张老大把十斤灵米的说法抛给少年。
场面调度：required_presence=CHAR_ZHANG_LAODA,PROP_SPIRIT_RICE_BAG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 张老大把布袋举到灯下，袋口露出灰白米粒，话术先把恩情放大。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生低声承认疲惫。
- action: 张老大把布袋举到灯下，袋口露出灰白米粒，话术先把恩情放大。
- end_state: 张老大把十斤灵米的说法抛给少年。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=reveal_reaction_chain;primary_backend=seedance;fallback=dreamina;mode=image2video;native_audio_policy=none;identity_requirement=character_id_or_reference_group;degrade_plan=Split into evidence insert, first reaction, and follow-up reaction if faces or evidence drift.
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_20; allowed_voiceover_indices=[20]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[20]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 20. 张老大: 你看这是什么？上仙可怜咱们杂役，发了灵米。别人一个月二斤，却给你——十斤。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：张老大把布袋举到灯下，袋口露出灰白米粒，话术先把恩情放大。。
镜头运动：MCU 布袋亮出；速度克制，服务本镜情绪，不乱甩。
情绪节奏：施恩话术。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_SPIRIT_RICE_BAG 的结构和数量。
衔接约束：从 贺平生低声承认疲惫。 开始，只执行本镜动作，落到 张老大把十斤灵米的说法抛给少年。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 张老大把布袋举到灯下，袋口露出灰白米粒，话术先把恩情放大。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_SPIRIT_RICE_BAG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 21（时长 1.72s · EP02_CLIP21 · 贺平生问缘由）
剧本可看性合同：dramatic_function=保留少年疑问，让观众准备验账。；audience_effect=观众跟随少年的疑问继续看下去。。

**首帧**：`出图/第2集/图片/Clip21_first.png`
**尾帧**：`出图/第2集/图片/Clip21_end.png`
导演意图：保留少年疑问，让观众准备验账。；为什么这样拍：观众跟随少年的疑问继续看下去。。
起幅：张老大把十斤灵米的说法抛给少年。
落幅：贺平生对十斤灵米感到意外。
场面调度：required_presence=CHAR_HE_PINGSHENG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生抬眼问原因，画面保持少年低位，疑问很轻。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 张老大把十斤灵米的说法抛给少年。
- action: 贺平生抬眼问原因，画面保持少年低位，疑问很轻。
- end_state: 贺平生对十斤灵米感到意外。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_21; allowed_voiceover_indices=[21]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[21]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 21. 贺平生: 为啥我有十斤？
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生抬眼问原因，画面保持少年低位，疑问很轻。。
镜头运动：CU 少年疑问；速度克制，服务本镜情绪，不乱甩。
情绪节奏：幼年疑问。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_SPIRIT_RICE_BAG 的结构和数量。
衔接约束：从 张老大把十斤灵米的说法抛给少年。 开始，只执行本镜动作，落到 贺平生对十斤灵米感到意外。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生抬眼问原因，画面保持少年低位，疑问很轻。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_SPIRIT_RICE_BAG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 22（时长 3.96s · EP02_CLIP22 · 张老大催找容器）
剧本可看性合同：dramatic_function=把容器选择导回破盆，完成物件闭环。；audience_effect=观众注意到破盆会重新参与剧情。。

**首帧**：`出图/第2集/图片/Clip22_first.png`
**尾帧**：`出图/第2集/图片/Clip22_end.png`
导演意图：把容器选择导回破盆，完成物件闭环。；为什么这样拍：观众注意到破盆会重新参与剧情。。
起幅：贺平生对十斤灵米感到意外。
落幅：张老大催贺平生找容器接米。
场面调度：required_presence=CHAR_ZHANG_LAODA,PROP_SPIRIT_RICE_BAG,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 张老大把布袋口往下压，催他找东西接米，语气轻松却不容拒绝。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生对十斤灵米感到意外。
- action: 张老大把布袋口往下压，催他找东西接米，语气轻松却不容拒绝。
- end_state: 张老大催贺平生找容器接米。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_22; allowed_voiceover_indices=[22]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[22]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 22. 张老大: 挑水的活儿重呗。哗——找个东西，我给你倒。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：张老大把布袋口往下压，催他找东西接米，语气轻松却不容拒绝。。
镜头运动：CU 布袋下倾；速度克制，服务本镜情绪，不乱甩。
情绪节奏：顺势占便宜。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、PROP_SPIRIT_RICE_BAG 的结构和数量。
衔接约束：从 贺平生对十斤灵米感到意外。 开始，只执行本镜动作，落到 张老大催贺平生找容器接米。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 张老大把布袋口往下压，催他找东西接米，语气轻松却不容拒绝。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、PROP_SPIRIT_RICE_BAG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 23（时长 4.00s · EP02_CLIP23 · 灵米倒入破盆）
剧本可看性合同：dramatic_function=让灰败灵米进入破盆，为集尾变化埋实物因。；audience_effect=观众看到破盆和灵米完成绑定。。

**首帧**：`出图/第2集/图片/Clip23_first.png`
**尾帧**：`出图/第2集/图片/Clip23_end.png`
导演意图：让灰败灵米进入破盆，为集尾变化埋实物因。；为什么这样拍：观众看到破盆和灵米完成绑定。。
起幅：张老大催贺平生找容器接米。
落幅：灰白灵米落进黑陶破盆。
场面调度：required_presence=CHAR_ZHANG_LAODA,PROP_HEI_TAO_PEN,PROP_SPIRIT_RICE_BAG,PROP_GRAY_RICE,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 灰白米粒从布袋快速落进黑陶破盆，盆沿旧缺口与米粒形成清楚对比。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 张老大催贺平生找容器接米。
- action: 灰白米粒从布袋快速落进黑陶破盆，盆沿旧缺口与米粒形成清楚对比。
- end_state: 灰白灵米落进黑陶破盆。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_23; allowed_voiceover_indices=[23]
- allowed_narration_indices=[23]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 23. 旁白: 屋里能盛米的，只有那只破陶盆。张老大把布袋一抖，米全倒了进去。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：灰白米粒从布袋快速落进黑陶破盆，盆沿旧缺口与米粒形成清楚对比。。
镜头运动：ECU 快速米落盆；速度克制，服务本镜情绪，不乱甩。
情绪节奏：容器回扣。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、PROP_SPIRIT_RICE_BAG 的结构和数量。
衔接约束：从 张老大催贺平生找容器接米。 开始，只执行本镜动作，落到 灰白灵米落进黑陶破盆。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 灰白米粒从布袋快速落进黑陶破盆，盆沿旧缺口与米粒形成清楚对比。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、PROP_SPIRIT_RICE_BAG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 24（时长 5.60s · EP02_CLIP24 · 贺平生识破斤两）
剧本可看性合同：dramatic_function=少年凭旧经验识破斤两，第一次显出敏锐。；audience_effect=观众获得少年并不傻的认知反转。。

**首帧**：`出图/第2集/图片/Clip24_first.png`
**尾帧**：`出图/第2集/图片/Clip24_end.png`
导演意图：少年凭旧经验识破斤两，第一次显出敏锐。；为什么这样拍：观众获得少年并不傻的认知反转。。
起幅：灰白灵米落进黑陶破盆。
落幅：贺平生看出盆中米量不足，并低声说出最多五斤。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,PROP_GRAY_RICE,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生盯着盆中米量，眼神从感激转为迟疑，低声说出斤两不对。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 灰白灵米落进黑陶破盆。
- action: 贺平生盯着盆中米量，眼神从感激转为迟疑，低声说出斤两不对。
- end_state: 贺平生看出盆中米量不足，并低声说出最多五斤。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_24; allowed_voiceover_indices=[24]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[24]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 24. 贺平生: 江叔做外门弟子时，每月也是十斤灵米，都是我替他领的……这一盆，‖哪有十斤？最多五斤。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生盯着盆中米量，眼神从感激转为迟疑，低声说出斤两不对。。
镜头运动：CU 少年起疑；速度克制，服务本镜情绪，不乱甩。
情绪节奏：识破斤两。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、PROP_SPIRIT_RICE_BAG 的结构和数量。
衔接约束：从 灰白灵米落进黑陶破盆。 开始，只执行本镜动作，落到 贺平生看出盆中米量不足，并低声说出最多五斤。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生盯着盆中米量，眼神从感激转为迟疑，低声说出斤两不对。. Preserve character identity (CHAR_HE_PINGSHENG、CHAR_ZHANG_LAODA), asset structure (LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、PROP_SPIRIT_RICE_BAG), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 25（时长 4.20s · EP02_CLIP25 · 灰败灵米揭克扣）
剧本可看性合同：dramatic_function=揭示克扣与劣质米双重压迫。；audience_effect=观众确认克扣成立，憋屈感升级。。

**首帧**：`出图/第2集/图片/Clip25_first.png`
**尾帧**：`出图/第2集/图片/Clip25_end.png`
导演意图：用灰败米粒的视觉证据补足克扣成立。；为什么这样拍：观众确认克扣成立，憋屈感升级。。
起幅：贺平生看出盆中米量不足，并低声说出最多五斤。
落幅：灰败米粒在月光下显出最差成色。
场面调度：required_presence=PROP_GRAY_RICE,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 月光扫过米面，白米里混着灰败绿意，劣质感直接露出来。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生看出盆中米量不足，并低声说出最多五斤。
- action: 月光扫过米面，白米里混着灰败绿意，劣质感直接露出来。
- end_state: 灰败米粒在月光下显出最差成色。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_25; allowed_voiceover_indices=[25]
- allowed_narration_indices=[25]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 25. 旁白: 月光下，那米白里泛着一点灰败的绿——是仙人都看不上、最差的那一等。被克扣了一半，他一眼就看得出。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：月光扫过米面，白米里混着灰败绿意，劣质感直接露出来。。
镜头运动：ECU 灰败米粒证据；速度克制，服务本镜情绪，不乱甩。
情绪节奏：克扣揭示。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN 的结构和数量。
衔接约束：从 贺平生看出盆中米量不足，并低声说出最多五斤。 开始，只执行本镜动作，落到 灰败米粒在月光下显出最差成色。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 月光扫过米面，白米里混着灰败绿意，劣质感直接露出来。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 26（时长 4.45s · EP02_CLIP26 · 弱小吞下憋屈）
剧本可看性合同：dramatic_function=把识破却讨不回的无力感落到人物身上。；audience_effect=观众理解此刻不能硬刚，只能等机会。。

**首帧**：`出图/第2集/图片/Clip26_first.png`
**尾帧**：`出图/第2集/图片/Clip26_end.png`
导演意图：把识破却讨不回的无力感落到人物身上。；为什么这样拍：观众理解此刻不能硬刚，只能等机会。。
起幅：灰败米粒在月光下显出最差成色。
落幅：贺平生知道讨不回，只能把委屈咽下。
场面调度：required_presence=CHAR_HE_PINGSHENG,PROP_HEI_TAO_PEN,PROP_GRAY_RICE,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 贺平生垂眼沉默，手指收紧又松开，最后把话咽回去。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 灰败米粒在月光下显出最差成色。
- action: 贺平生垂眼沉默，手指收紧又松开，最后把话咽回去。
- end_state: 贺平生知道讨不回，只能把委屈咽下。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_26; allowed_voiceover_indices=[26]
- allowed_narration_indices=[]; allowed_character_dialogue_indices=[26]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- dialogue: 26. 贺平生: 知道又能怎样？我这点本事，讨得回来吗……
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：贺平生垂眼沉默，手指收紧又松开，最后把话咽回去。。
镜头运动：CU 克制吞声；速度克制，服务本镜情绪，不乱甩。
情绪节奏：无力吞下。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW 的结构和数量。
衔接约束：从 灰败米粒在月光下显出最差成色。 开始，只执行本镜动作，落到 贺平生知道讨不回，只能把委屈咽下。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 贺平生垂眼沉默，手指收紧又松开，最后把话咽回去。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。

## Clip 27（时长 8.00s · EP02_CLIP27 · 灰败灵米唤醒盆底微光）
剧本可看性合同：dramatic_function=用破盆再次反应收尾，承诺第3集爽点。；audience_effect=观众得到下一集“灰败米会变什么”的明确追看理由。。

**首帧**：`出图/第2集/图片/Clip27_first.png`
导演意图：用破盆再次反应收尾，承诺第3集爽点。；为什么这样拍：观众得到下一集“灰败米会变什么”的明确追看理由。。
起幅：贺平生知道讨不回，只能把委屈咽下。
落幅：破盆盛着灰败灵米，盆底微绿亮点重新游动。
场面调度：required_presence=PROP_HEI_TAO_PEN,PROP_GRAY_RICE,VFX_BASIN_MICROGLOW,LOC_ZAYI_HUT；offscreen_presence=无；forbidden_presence=CHAR_HAN_LAOSAN,CHAR_TAIXUMEN_ZHANGLAO,CHAR_JIANG_JIAN；无人物镜锁画面重心和道具位置。
表演节拍：0-30% 建立起幅；30-80% 执行 门栓顶好后屋里安静下来，破盆盛着灰败灵米，盆底微绿亮点再次游动。；80-100% 稳到尾帧/落幅。
运动精修：低幅度、重心稳定、手部归属清晰、脸部与发髻不拉变形，FeatureMelting/特征融化必须检查。
环境交互：动作带动衣褶/水面/微光/尘雾/阴影的细微反馈，不改变资产结构。
衔接设计：承接上一镜状态，按 storyboard continuity 进入下一镜；尾帧保留 0.3s。
continuity:
- start_state: 贺平生知道讨不回，只能把委屈咽下。
- action: 门栓顶好后屋里安静下来，破盆盛着灰败灵米，盆底微绿亮点再次游动。
- end_state: 破盆盛着灰败灵米，盆底微绿亮点重新游动。
- constraints: 只继承本镜已发生的状态、光位、轴线、资产和身份；禁止新增未登记实体。
- negative: 不换脸、不改年龄身高、不改服装、不改场景、不烤字、不生成原生人声。
角色身份注册层：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；脸部特写/表情参考按 identity_registry。
近景/反打身份锁定：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；表情锚=起幅到落幅；表情幅度=微/中；锁脸不锁情；配角不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由：shot_type=dialogue_shot_reverse;primary_backend=seedance;fallback=dreamina;mode=voice_conditioned_lipsync;native_audio_policy=lipsync_condition_only;identity_requirement=character_id_or_reference_group;degrade_plan=后端不支持音频参考口型 / 口型对不齐 → 回退 image2video 静音出片 + 后期 MuseTalk 对口型 pass（见 n2d-video 对口型节）；或分镜规避用侧脸/背身/OTS 配旁白。
原生音画策略：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
对白事实合同摘录：
```text
对白事实锁 / Dialogue-Fact Contract:
- clip: Clip_27; allowed_voiceover_indices=[27]
- allowed_narration_indices=[27]; allowed_character_dialogue_indices=[]
- 视频生成阶段只允许画内角色说 listed dialogue；旁白不由视频模型生成音频，旁白音频在 compose 阶段叠加。
- 不得重复前后 Clip 已分配对白/旁白/屏幕文案；不得自由改写年龄、身高、数量、灵根等数字/设定事实。
- narration_for_compose_only: 27. 旁白: 他把门栓顶死，倒头就睡。却没看见——盛着灰败灵米的破陶盆，盆底那缕微光，‖又开始动了。
- narration_audio_policy: compose_stage_only; video_model_must_not_generate_narration_voice.
- screen_text_overlay: none; 不要让视频模型生成文字
- 屏幕文案只作为后期 compose overlay，不要在视频画面里烤字、写字、生成字幕卡。
- canonical_facts: 贺平生.age=十四岁; 贺平生.height=少年偏矮，约155-160cm；与张老大同框时明显矮一头，与韩老三同框时到其肩颈以下; 贺平生.spiritual_root=五行灵根; 剧情账本.daily_water_trips=一天至少二十趟
- forbidden_fact_values: 13 岁, 13岁, 15 岁, 15岁, 15趟, 16 岁, 16岁, 16趟, 170cm, 175cm, 180cm, 一米七, 一米八, 十三岁, 十五岁, 十五趟, 十六岁, 十六趟, 十几趟, 单灵根, 变异灵根, 天灵根, 火灵根
- 若后端无法严格遵守以上对白与事实锁，本段宁可无对白，也不要生成额外台词或改数值。
```
### 视频 prompt（中文，目标=路由 primary/fallback）
```text
首帧保持：严格继承 `首帧` PNG 的构图、角色身份、场景光位、道具位置和色调，不重画新脸/新服装/新场景。
人物运动：门栓顶好后屋里安静下来，破盆盛着灰败灵米，盆底微绿亮点再次游动。。
镜头运动：ECU 盆底尾钩；速度克制，服务本镜情绪，不乱甩。
情绪节奏：集尾钩子。
动态细节：衣摆/呼吸/水面/灵光/尘雾/冷光只做低幅度细节，主体结构不漂。
运动精修约束：幅度小于首尾帧可解释范围；锁脸型、五官比例、发型发髻、服装配色、手部归属、身体重心和接触点；不得穿模或特征融化。
环境交互约束：动作必须带动对应光影/水面/衣褶/尘雾/道具细微反馈，但不能改变 LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW 的结构和数量。
衔接约束：从 贺平生知道讨不回，只能把委屈咽下。 开始，只执行本镜动作，落到 破盆盛着灰败灵米，盆底微绿亮点重新游动。；保留尾帧 0.3s 方便剪辑。
身份锁定约束：CHAR_HE_PINGSHENG；reference_group=identity_registry.reference_group；face_lock/reference controls 优先，fallback 保持同源定妆。
近景身份锁定约束：脸型、五官比例、眼距、鼻梁、下颌、发型发髻、标志配饰、服装配色保持；配角近景不稳则 MCU/OTS/侧脸/手部/物件反应保真实现。
模型路由约束：按 primary_backend=seedance 的首尾帧能力提交；失败才按 fallback/degrade_plan，不临场换后端。
原生音画约束：audio_intent=none；risk=low；mouth_visible=no_or_post_dub；speech_policy=no_native_speech；compose_policy=丢弃视频原生音轨/后期叠配音字幕。
声音约束：不生成原生人声、旁白、台词、哼唱或字幕卡；所有对白/旁白/字幕由 compose 阶段处理。
禁止：换脸、改年龄、改身高、改服装、改场景、改光位、新增人物/道具、现代物件、文字/logo/水印、额外手、多肢、穿模、主体融合。
```
### 视频 prompt（英文，fallback）
```text
Keep the first frame identity and layout. Animate only the scripted motion: 门栓顶好后屋里安静下来，破盆盛着灰败灵米，盆底微绿亮点再次游动。. Preserve character identity (CHAR_HE_PINGSHENG), asset structure (LOC_ZAYI_HUT、PROP_GRAY_RICE、PROP_HEI_TAO_PEN、VFX_BASIN_MICROGLOW), lighting, screen direction, and final frame continuity. Silent image-to-video, no text, no watermark, no extra people.
```
### 检查清单（视频三件套自查·最易漏 ④人物运动 / ②镜头运动 / ⑦张力）
- [ ] 首帧 PNG 与 storyboard.firstframe_png 一致，首帧保持字段已落实。
- [ ] 导演意图/起幅/落幅/场面调度/表演节拍/运动精修/环境交互齐全。
- [ ] 模型路由 primary/fallback/mode/degrade_plan 已继承，失败才切 fallback。
- [ ] 原生音画策略为 no_native_speech/post_dub_only，字幕和配音交 compose。
- [ ] FeatureMelting/特征融化、动作编排、身份锁、资产锁、在场链已检查。
### 自检（生成后逐条过 · 落档闸门）
- [ ] 首帧一致性：人物脸/服装/场景/光位无漂移。
- [ ] 人物运动：方向、速度曲线、空间路径和落点正确。
- [ ] 物理守卫：无穿模、拉脸、手部归属错乱、多肢或特征融化 FeatureMelting。
- [ ] 镜头运动：符合推/拉/固定/轻跟等设计，无乱甩。
- [ ] 动态细节 & 环境交互成立，不引入文字/logo/现代物件。
- [ ] 原生音画：无 AI 自带台词/旁白/哼唱；compose 阶段处理声音。
