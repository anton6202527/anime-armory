# n2d Failure Taxonomy

- 集：第1集
- 状态：warn
- 升级 block：0
- 分类：{'backend': 18, 'director_blocking': 76, 'image_prompt': 154, 'production_breakdown': 16, 'qc': 126, 'script': 85}

## Return Plan

| category | owner | block | fix | rerun |
|---|---|---:|---|---|
| backend | 模型路由/后端适配 | 0 | 回到模型路由、能力证据、seed/参考输入、口型/原生音画策略和失败降级方案。 | `python3 skills/n2d-model-router/scripts/router.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --json`<br>`python3 skills/n2d/scripts/release_verdict.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --json` |
| director_blocking | 导演/分镜 | 0 | 回到导演排戏包、轴线图、景别进程、转场/首尾帧接力，先修可拍性和剪辑连续性。 | `python3 skills/n2d-script/scripts/director_blocking_pack.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 check --json`<br>`python3 skills/n2d-review/scripts/gate.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 image --json` |
| image_prompt | 出图提示/美术资产 | 0 | 回到参考包、定妆、场景 atlas、逐镜 prompt 和 image_qc，禁止只靠文字外貌描述补救。 | `python3 skills/n2d-image/scripts/image_qc.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --prop-shape-report`<br>`python3 skills/n2d-review/scripts/gate.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 image --json` |
| production_breakdown | 制片主任/场记 | 0 | 回到 production_breakdown、continuity_breakdown、ai_call_sheet、identity/asset registry 和 production_events。 | `python3 skills/n2d-script/scripts/production_breakdown.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 check --json`<br>`python3 skills/n2d/scripts/release_verdict.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --json` |
| qc | QC/验收 | 0 | 重跑过期 QC、score、ledger、review-ui 和校准集，确认报告指纹对应当前产物。 | `python3 skills/n2d-review/scripts/consistency_ledger.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集`<br>`python3 skills/n2d-review-ui/scripts/review_ui.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --write --export-findings --markdown`<br>`python3 skills/n2d/scripts/release_verdict.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --json` |
| script | 编剧/故事编辑 | 0 | 回到剧本改编、voiceover、伏笔/状态账本，先修动机、因果、台词、信息回报和集尾钩。 | `python3 skills/n2d-review/scripts/gate.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 review --json`<br>`python3 skills/n2d/scripts/failure_taxonomy.py /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人 第1集 --json` |

## Findings

| category | stage | severity | escalated | reason | message |
|---|---|---|---|---|---|
| qc | compose | warn | warn | - | distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放 |
| script | compose | warn | warn | - | start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。 |
| script | compose | info | info | - | clip 数 16 与 storyboard clips 11 不一致；final_timeline_probe 已验证成片时间线，raw split 数量差异仅作原料说明 |
| script | compose | warn | warn | - | clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声 |
| qc | compose | info | info | - | clip 总长 125.78s 与镜头时长累计 120.52s 差 5.26s；final_timeline_probe 已验证最终成片时长，raw split 总长差异仅作原料说明 |
| backend | compose | warn | warn | - | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（已显式降级 QC 放行·自负其责） |
| image_prompt | compose | warn | warn | - | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚 |
| qc | compose | warn | warn | - | 一致性审计发现问题 |
| image_prompt | compose | info | info | - | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=compose |
| image_prompt | compose | warn | warn | - | 场景语义嵌入(DINOv2) 适用但休眠（后端没真验证），已通过项目设置 internal_only + demo放行（自负其责·已计债）；本次交付未真验该轴一致性。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env） |
| image_prompt | compose | warn | warn | - | 场景常驻陈设在场(OWLv2) 适用但休眠（后端没真验证），已通过项目设置 internal_only + demo放行（自负其责·已计债）；本次交付未真验该轴一致性。跑 python3 skills/n2d-review/scripts/resident_presence.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 e |
| qc | compose | warn | warn | - | 另有 47 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。 |
| qc | compose | warn | warn | - | 本集本次 gate 凭 3 条降级 QC waiver 放行（交付边界·非满档一致性交付）：维度 现实覆盖、证据等级。这些维度未在满档(full)精度下验证，全靠 N2D_ALLOW_DEGRADED_QC 显式放行——已记账 `full_grade=false`，装齐依赖复跑可消账。 |
| qc | image_preflight | warn | warn | - | distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放 |
| image_prompt | image_preflight | warn | warn | - | 统一标准已按「Codex」自动加载弥补措施：加载 reference_group + face_embedding：正/45度/侧/半身/脸锚/表情库按镜头风险选入参；近景/大表情/暗光镜强制同源脸锚或表情参考，并用 full image_qc 回验；长线核心角反复漂移时升档到原生主体或 LoRA，不降低角色一致性标准。这些是后端差异的执行补偿，不降低 n2 |
| production_breakdown | image_preflight | warn | warn | - | 适配层评分建议升档：当前「Codex」score=15，推荐「Seedream Universal Reference (访问入口 Seedream 官方 API)」score=57。理由：推荐后端能力=persistent_subject,multi_reference,high_fidelity_reference；若确认切换，先统一 `_设置.md`  |
| image_prompt | image_preflight | warn | warn | - | 本集脸漂风险 high（分95.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| image_prompt | image_preflight | warn | warn | - | 本集脸漂风险 high（分93.5·multi_reference）：已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，不再因预测 high 在 preflight 阶段硬阻断。 |
| image_prompt | image_preflight | warn | warn | - | 本集脸漂风险 high（分90.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| director_blocking | image_preflight | warn | warn | - | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分46）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分42）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分30）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_preflight | info | info | - | 本集物料漂移风险 medium（分30）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| qc | image_preflight | info | info | - | 本集物料漂移风险 medium（分29）：颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。 |
| director_blocking | image_preflight | warn | warn | - | 逐镜参考规划有 10 条行动项未确认落实（无持久主体 ID 后端×大变化镜 0 镜）：镜头 EP01_CLIP02、EP01_CLIP03、EP01_CLIP04、EP01_CLIP05、EP01_CLIP06、EP01_CLIP07、EP01_CLIP08、EP01_CLIP09…。请按 reference_plan_第1集.md 把补拍/多样参考/控制网 |
| director_blocking | image_preflight | info | info | - | director_camera_plan_第1集.json（11 镜）的出图运镜词汇已现身 prompt 包（命中 5/5：起幅、运动余量、构图防呆、导演意图、镜头/机位）——文档级已消费。要逐镜精确归属请落 director_camera_plan_applied_第1集.json（结构化签收）。 |
| director_blocking | image_preflight | info | info | - | director_camera_plan_第1集.json（11 镜）的出视频运镜词汇已现身 prompt 包（命中 6/6：起幅、落幅、镜头运动、运动精修、动态细节、导演意图）——文档级已消费。要逐镜精确归属请落 director_camera_plan_applied_第1集.json（结构化签收）。 |
| qc | image_preflight | info | info | - | skill 有改动但仅限横切/QC/gate 层（n2d），不影响本阶段输入物料；如需可跑 `python3 skills/n2d-update/scripts/update_plan.py check "创作区/制漫剧/那妖魔是姜大人" 第1集` 复核。 |
| image_prompt | image_preflight | warn | warn | - | identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_狼妖群__常态_布料局部.png 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空 |
| image_prompt | image_preflight | warn | warn | - | identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_狼妖群__常态_手部局部.png 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空 |
| image_prompt | image_preflight | warn | warn | - | identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_飞鹰门众人__常态_布料局部.png 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空 |
| image_prompt | image_preflight | warn | warn | - | identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_飞鹰门众人__常态_手部局部.png 磁盘缺失；补出该图或修 registry 路径，否则锁脸参考落空 |
| image_prompt | image_preflight | warn | warn | - | 定妆图 定妆_CHAR_01__囚犯初醒态.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除 |
| image_prompt | image_preflight | warn | warn | - | 定妆图 定妆_CHAR_01__囚犯初醒态_表情_克制.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除 |
| image_prompt | image_preflight | warn | warn | - | 定妆图 定妆_CHAR_01__囚犯初醒态_表情_震动.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除 |
| image_prompt | image_preflight | warn | warn | - | 定妆图 定妆_CHAR_02__濒死战损态.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除 |
| image_prompt | image_preflight | warn | warn | - | 定妆图 定妆_CHAR_03__诈死复苏态.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会按文件名把它当参考、与 registry 锁的不是同一套 → 登记进 registry 或删除 |
| production_breakdown | image_preflight | warn | warn | - | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| production_breakdown | image_preflight | warn | warn | - | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| production_breakdown | image_preflight | warn | warn | - | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| production_breakdown | image_preflight | warn | warn | - | 该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 signature_equipment 中绑定。 |
| script | image_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：尸骸前景、荒野尸场。若是有意不连续，请把转场写清楚。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03、巨岩、黑色妖血。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03、巨岩、黑色妖血。若是有意不连续，请把转场写清楚。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_02、WEAPON_01。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03、VFX_虎山神摹影。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：WEAPON_01。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03、VFX_虎山神摹影。若是有意不连续，请把转场写清楚。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：VFX_系统面板。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03。若是有意不连续，请把转场写清楚。 |
| script | image_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03。若是新入场，请把 entry_exit 写成机器真值。 |
| script | image_preflight | info | info | - | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| script | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| script | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image_preflight | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| script | image_preflight | info | info | - | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| director_blocking | image_preflight | warn | warn | - | 多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保持体量优势。」；虎山神「远大于姜月初和裴长青，同框必须保持体量优势。」；裴长青「比姜月初高约一个头；与虎山神相比明显弱势。」 在 registry 声明了相对身量(relative_scale)，但本 |
| image_prompt | image_preflight | warn | warn | - | 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image_preflight | warn | warn | - | 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| script | image_preflight | warn | warn | - | 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| script | image_preflight | warn | warn | - | 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image_preflight | warn | warn | - | 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image_preflight | warn | warn | - | 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image_preflight | warn | warn | - | 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image_preflight | warn | warn | - | 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image_preflight | warn | warn | - | 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image_preflight | warn | warn | - | 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image_preflight | warn | warn | - | 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| script | image_preflight | warn | warn | - | 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| script | image_preflight | warn | warn | - | 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| script | image_preflight | warn | warn | - | 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image_preflight | warn | warn | - | 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image_preflight | warn | warn | - | 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image_preflight | warn | warn | - | 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image_preflight | warn | warn | - | 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image_preflight | warn | warn | - | 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image_prompt_preflight | info | info | - | 平台审核缺字段：platform（发布/合成前需补；当前 image 阶段不阻断） |
| image_prompt | image_prompt_preflight | info | info | - | 平台审核缺字段：policy_profile（发布/合成前需补；当前 image 阶段不阻断） |
| image_prompt | image_prompt_preflight | info | info | - | pre_broadcast_review 不能停在 pending（境内投放须先过播前审核）（发布/合成前需补；当前 image 阶段不阻断） |
| image_prompt | image_prompt_preflight | warn | warn | - | 本集脸漂风险 high（分95.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| image_prompt | image_prompt_preflight | warn | warn | - | 本集脸漂风险 high（分93.5·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| image_prompt | image_prompt_preflight | warn | warn | - | 本集脸漂风险 high（分90.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| director_blocking | image_prompt_preflight | warn | warn | - | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。 |
| image_prompt | image_prompt_preflight | info | info | - | 本集物料漂移风险 medium（分42）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_prompt_preflight | info | info | - | 本集物料漂移风险 medium（分30）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image_prompt_preflight | warn | warn | - | 基础视觉风格「冷灰写实3D国风漫剧」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。 |
| qc | image | warn | warn | - | distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放 |
| image_prompt | image | warn | warn | - | 本集脸漂风险 high（分95.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| image_prompt | image | warn | warn | - | 本集脸漂风险 high（分93.5·multi_reference）：已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，不再因预测 high 在 preflight 阶段硬阻断。 |
| image_prompt | image | warn | warn | - | 本集脸漂风险 high（分90.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。 |
| director_blocking | image | warn | warn | - | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分46）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分42）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分30）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| image_prompt | image | info | info | - | 本集物料漂移风险 medium（分30）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| qc | image | info | info | - | 本集物料漂移风险 medium（分29）：颜色/拖尾强锁：写死 color_target(HSV) 与拖尾长度，避免跨镜窜色（特效最易漂）。 |
| script | image | warn | warn | - | start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。 |
| script | image | info | info | - | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| script | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| script | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| director_blocking | image | warn | warn | - | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| script | image | info | info | - | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| director_blocking | image | warn | warn | - | 多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保持体量优势。」；虎山神「远大于姜月初和裴长青，同框必须保持体量优势。」；裴长青「比姜月初高约一个头；与虎山神相比明显弱势。」 在 registry 声明了相对身量(relative_scale)，但本 |
| backend | image | warn | warn | - | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（已显式降级 QC 放行·自负其责） |
| image_prompt | image | warn | warn | - | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚 |
| image_prompt | image | warn | warn | - | 一致性审计发现问题 |
| image_prompt | image | warn | warn | - | 主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） |
| image_prompt | image | warn | warn | - | 光位锚声明主光在「left」，实测最亮区却偏「right」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 |
| image_prompt | image | warn | warn | - | 主光方位 right→left 硬翻转（疑光位跳·人比对相邻镜） |
| script | image | warn | warn | - | 镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 |
| image_prompt | image | warn | warn | - | 图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | image | warn | warn | - | 图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | image | warn | warn | - | 图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | image | warn | warn | - | 图片/Clip08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.127 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | image | info | info | - | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=image |
| qc | image | warn | warn | - | 另有 5 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0.14 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine=0.16 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_mid.png DINO/CLIP cosine=0.15 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip02_end.png DINO/CLIP cosine=0.11 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip02_first.png DINO/CLIP cosine=0.23 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip02_mid.png DINO/CLIP cosine=0.16 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip03_end.png DINO/CLIP cosine=0.17 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip03_first.png DINO/CLIP cosine=0.20 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip03_mid.png DINO/CLIP cosine=0.23 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip04_end.png DINO/CLIP cosine=0.12 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip04_first.png DINO/CLIP cosine=0.17 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip04_mid.png DINO/CLIP cosine=0.13 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip05_end.png DINO/CLIP cosine=0.15 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip05_first.png DINO/CLIP cosine=0.10 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip05_mid.png DINO/CLIP cosine=0.11 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip06_end.png DINO/CLIP cosine=0.11 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip06_end_reaction.png DINO/CLIP cosine=0.14 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip06_first.png DINO/CLIP cosine=0.18 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip06_mid.png DINO/CLIP cosine=0.21 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip06_mid_reaction.png DINO/CLIP cosine=0.04 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip07_end.png DINO/CLIP cosine=0.04 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip07_first.png DINO/CLIP cosine=0.03 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip07_mid.png DINO/CLIP cosine=0.02 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip08_end.png DINO/CLIP cosine=0.05 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip08_first.png DINO/CLIP cosine=0.02 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip08_mid.png DINO/CLIP cosine=0.05 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip09_end.png DINO/CLIP cosine=0.17 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip09_first.png DINO/CLIP cosine=0.12 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip09_mid.png DINO/CLIP cosine=0.13 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip10_end.png DINO/CLIP cosine=0.13 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip10_first.png DINO/CLIP cosine=0.13 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip10_mid.png DINO/CLIP cosine=0.09 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| qc | image | warn | warn | - | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip11_first.png DINO/CLIP cosine=0.12 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 |
| director_blocking | image | warn | warn | - | 景别像素兜底：镜3 声明 CU(特写) 但 出图/第1集/图片/Clip03_end.png 实测脸占比 0.9% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 |
| director_blocking | image | warn | warn | - | 景别像素兜底：镜6 声明 CU(特写) 但 出图/第1集/图片/Clip06_end.png 实测脸占比 0.3% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 |
| director_blocking | image | warn | warn | - | 景别像素兜底：镜7 声明 CU(特写) 但 出图/第1集/图片/Clip07_end.png 实测脸占比 0.3% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 |
| director_blocking | image | warn | warn | - | 景别像素兜底：镜8 声明 CU(特写) 但 出图/第1集/图片/Clip08_end.png 实测脸占比 0.7% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 |
| director_blocking | image | warn | warn | - | 景别像素兜底：镜9 声明 CU(特写) 但 出图/第1集/图片/Clip09_end.png 实测脸占比 1.0% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 |
| director_blocking | image | warn | warn | - | 景别像素兜底：镜11 声明 CU(特写) 但 出图/第1集/图片/Clip11_first.png 实测脸占比 4.7% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 |
| image_prompt | image | warn | warn | - | 锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断） |
| image_prompt | image | warn | warn | - | 锚点门 N3：CHAR_01__镇魔司伪装态 主参考非单张清晰正脸（非阻断） |
| image_prompt | image | warn | warn | - | 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸（非阻断） |
| image_prompt | image | warn | warn | - | 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） |
| image_prompt | image | warn | warn | - | 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image | warn | warn | - | 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| script | image | warn | warn | - | 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| script | image | warn | warn | - | 镜头 3（`EP01_CLIP03` · 镇魔司压迫交易 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image | warn | warn | - | 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 4（`EP01_CLIP04` · 被迫扶裴南行 · multi_character_same_frame）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image | warn | warn | - | 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 5（`EP01_CLIP05` · 虎妖诈死复苏 · reveal_reaction_chain）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image | warn | warn | - | 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 6（`EP01_CLIP06` · 裴长青最后一击被踹飞 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image | warn | warn | - | 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image | warn | warn | - | 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 7（`EP01_CLIP07` · 百妖谱第一次开启 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image | warn | warn | - | 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image | warn | warn | - | 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 8（`EP01_CLIP08` · 系统规则指向唯一活物 · system_panel）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| script | image | warn | warn | - | 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| script | image | warn | warn | - | 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| script | image | warn | warn | - | 镜头 9（`EP01_CLIP09` · 刀尖抬起 · dialogue_shot_reverse）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image | warn | warn | - | 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image | warn | warn | - | 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 10（`EP01_CLIP10` · 刺杀裴长青 · fight_exchange）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| production_breakdown | image | warn | warn | - | 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：用了 `定妆_特效_百妖谱金色古卷面板.png`(特效) 但未绑 `VFX_百妖谱金光`；写上资产 id 执行端才会自动取 reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移） |
| image_prompt | image | warn | warn | - | 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。 |
| image_prompt | image | warn | warn | - | 镜头 11（`EP01_CLIP11` · 我只想活下去 · multi_character_same_frame）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句） |
| image_prompt | image | warn | warn | - | 脸部锚弱信噪比 CHAR_04/常态「基础」（出图/共享/图片/定妆_CHAR_04__常态.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 |
| image_prompt | image | warn | warn | - | 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 |
| image_prompt | image | warn | warn | - | 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 |
| image_prompt | image | warn | warn | - | VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。 |
| production_breakdown | image | info | info | - | 本集出现累积状态关键词（伤口/觉醒）但无 visual_state_ledger.json——状态可能跨镜/跨集演进，建议跑 `python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --audit` 建账本锁状态（简单剧确认后可忽略；本提示不阻断）。 |
| qc | review | warn | warn | - | distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放 |
| qc | review | info | info | - | explicit_label.status 尚非 done；成片未确认已落显式标签（AI 标识非阻断；发布前按目标地区/平台补齐） |
| script | review | warn | warn | - | start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。 |
| script | review | info | info | - | clip 数 16 与 storyboard clips 11 不一致；final_timeline_probe 已验证成片时间线，raw split 数量差异仅作原料说明 |
| script | review | warn | warn | - | clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声 |
| qc | review | info | info | - | clip 总长 125.78s 与镜头时长累计 120.52s 差 5.26s；final_timeline_probe 已验证最终成片时长，raw split 总长差异仅作原料说明 |
| backend | review | warn | warn | - | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（已显式降级 QC 放行·自负其责） |
| image_prompt | review | warn | warn | - | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚 |
| qc | review | warn | warn | - | 一致性审计发现问题 |
| image_prompt | review | info | info | - | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=review |
| image_prompt | review | warn | warn | - | 场景语义嵌入(DINOv2) 适用但休眠（后端没真验证），已通过项目设置 internal_only + demo放行（自负其责·已计债）；本次交付未真验该轴一致性。跑 python3 skills/n2d-review/scripts/scene_embed.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 env） |
| image_prompt | review | warn | warn | - | 场景常驻陈设在场(OWLv2) 适用但休眠（后端没真验证），已通过项目设置 internal_only + demo放行（自负其责·已计债）；本次交付未真验该轴一致性。跑 python3 skills/n2d-review/scripts/resident_presence.py "创作区/制漫剧/那妖魔是姜大人" 第1集 --write（需对应重型后端 e |
| qc | review | warn | warn | - | 另有 47 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。 |
| production_breakdown | review | warn | warn | - | 一致性验收总账仍有 medium=24；可人工签收，但需逐项看角色/资产/镜头/声音跨集账本。 |
| qc | review | warn | warn | - | 本集本次 gate 凭 3 条降级 QC waiver 放行（交付边界·非满档一致性交付）：维度 现实覆盖、证据等级。这些维度未在满档(full)精度下验证，全靠 N2D_ALLOW_DEGRADED_QC 显式放行——已记账 `full_grade=false`，装齐依赖复跑可消账。 |
| qc | video_preflight | warn | warn | - | distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放 |
| image_prompt | video_preflight | warn | warn | - | 前期物料可能已过期：n2d, n2d-image, n2d-script, n2d-video 自上次 skill 基线后有改动，可能影响本阶段（video）的输入物料。出图/出视频是花钱且不可逆的步骤——先跑 `python3 skills/n2d-update/scripts/update_plan.py check "创作区/制漫剧/那妖魔是姜大人"  |
| script | video_preflight | warn | warn | - | start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。 |
| director_blocking | video_preflight | info | info | - | director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第1集.json·SHA 绑定 plan+prompt）。 |
| director_blocking | video_preflight | info | info | - | director_camera_plan_第1集.json（11 镜）的出视频运镜词汇已现身 prompt 包（命中 6/6：起幅、落幅、镜头运动、运动精修、动态细节、导演意图）——文档级已消费。要逐镜精确归属请落 director_camera_plan_applied_第1集.json（结构化签收）。 |
| script | video_preflight | info | info | - | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| backend | video_preflight | warn | warn | - | 生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录 / 会员态有效 / API key·额度可用（或一次 dry-run）。内网/自定义供应商可导出 N2D_VIDEO_BACKEND_BASE_URL 或对应 *_BASE_URL 启用自动探活。。 |
| image_prompt | video_preflight | warn | warn | - | 1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；确认基线后端仍合适，否则 --write-baseline 刷新基线。Clip_02(realm_portal):dreamina→seedance |
| script | video_preflight | info | info | - | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| script | video_preflight | info | info | - | 出视频 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| image_prompt | video_prompt_preflight | info | info | - | 平台审核缺字段：platform（发布/合成前需补；当前 video 阶段不阻断） |
| image_prompt | video_prompt_preflight | info | info | - | 平台审核缺字段：policy_profile（发布/合成前需补；当前 video 阶段不阻断） |
| image_prompt | video_prompt_preflight | info | info | - | pre_broadcast_review 不能停在 pending（境内投放须先过播前审核）（发布/合成前需补；当前 video 阶段不阻断） |
| production_breakdown | video_prompt_preflight | warn | warn | - | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| script | video_prompt_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：尸骸前景、荒野尸场。若是有意不连续，请把转场写清楚。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03、巨岩、黑色妖血。若是新入场，请把 entry_exit 写成机器真值。 |
| script | video_prompt_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03、巨岩、黑色妖血。若是有意不连续，请把转场写清楚。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_02、断刀。若是新入场，请把 entry_exit 写成机器真值。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03、VFX_虎妖黑血妖气。若是新入场，请把 entry_exit 写成机器真值。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：WEAPON_01。若是新入场，请把 entry_exit 写成机器真值。 |
| script | video_prompt_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03、VFX_虎妖黑血妖气。若是有意不连续，请把转场写清楚。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：VFX_系统面板。若是新入场，请把 entry_exit 写成机器真值。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03。若是新入场，请把 entry_exit 写成机器真值。 |
| script | video_prompt_preflight | warn | warn | - | 实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03。若是有意不连续，请把转场写清楚。 |
| script | video_prompt_preflight | warn | warn | - | 实体在下一 Clip 出现但缺入画/换场解释：CHAR_03。若是新入场，请把 entry_exit 写成机器真值。 |
| director_blocking | video_prompt_preflight | info | info | - | director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第1集.json·SHA 绑定 plan+prompt）。 |
| director_blocking | video_prompt_preflight | info | info | - | director_camera_plan_第1集.json（11 镜）的出视频运镜注入已逐镜签收落实（director_camera_plan_applied_第1集.json·SHA 绑定 plan+prompt）。 |
| script | video_prompt_preflight | warn | warn | - | `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子 |
| image_prompt | video_prompt_preflight | warn | warn | - | 生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录 / 会员态有效 / API key·额度可用（或一次 dry-run）。内网/自定义供应商可导出 N2D_VIDEO_BACKEND_BASE_URL 或对应 *_BASE_URL 启用自动探活。。 |
| image_prompt | video_prompt_preflight | info | info | - | skill 有改动但仅限横切/QC/gate 层（n2d），不影响本阶段输入物料；如需可跑 `python3 skills/n2d-update/scripts/update_plan.py check "创作区/制漫剧/那妖魔是姜大人" 第1集` 复核。 |
| qc | video | warn | warn | - | distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放 |
| script | video | warn | warn | - | start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。 |
| director_blocking | video | info | info | - | director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第1集.json·SHA 绑定 plan+prompt）。 |
| director_blocking | video | info | info | - | director_camera_plan_第1集.json（11 镜）的出视频运镜词汇已现身 prompt 包（命中 6/6：起幅、落幅、镜头运动、运动精修、动态细节、导演意图）——文档级已消费。要逐镜精确归属请落 director_camera_plan_applied_第1集.json（结构化签收）。 |
| script | video | info | info | - | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| backend | video | warn | warn | - | 生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录 / 会员态有效 / API key·额度可用（或一次 dry-run）。内网/自定义供应商可导出 N2D_VIDEO_BACKEND_BASE_URL 或对应 *_BASE_URL 启用自动探活。。 |
| image_prompt | video | warn | warn | - | 1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；确认基线后端仍合适，否则 --write-baseline 刷新基线。Clip_02(realm_portal):dreamina→seedance |
| script | video | info | info | - | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| script | video | info | info | - | 出视频 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| backend | video | warn | warn | - | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（已显式降级 QC 放行·自负其责） |
| image_prompt | video | warn | warn | - | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚 |
| qc | video | warn | warn | - | 一致性审计发现问题 |
| image_prompt | video | info | info | - | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=video |
| qc | video | warn | warn | - | 另有 47 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。 |
| image_prompt | consistency | warn | warn | - | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚 |
| qc | consistency | warn | warn | - | Clip_01_死人堆惊醒.mp4 |
| qc | consistency | warn | warn | - | Clip_02_看见虎妖尸身_part1.mp4 |
| qc | consistency | warn | warn | - | Clip_02_看见虎妖尸身_part2.mp4 |
| qc | consistency | warn | warn | - | Clip_03_镇魔司压迫交易_part1.mp4 |
| qc | consistency | warn | warn | - | Clip_03_镇魔司压迫交易_part2.mp4 |
| qc | consistency | warn | warn | - | Clip_05_虎妖诈死复苏_part1.mp4 |
| qc | consistency | warn | warn | - | Clip_05_虎妖诈死复苏_part2.mp4 |
| qc | consistency | warn | warn | - | Clip_06_裴长青最后一击被踹飞_part1.mp4 |
| qc | consistency | warn | warn | - | Clip_06_裴长青最后一击被踹飞_part2.mp4 |
| qc | consistency | warn | warn | - | Clip_07_百妖谱第一次开启_part1.mp4 |
| qc | consistency | warn | warn | - | Clip_07_百妖谱第一次开启_part2.mp4 |
| qc | consistency | warn | warn | - | Clip_08_系统规则指向唯一活物.mp4 |
| qc | consistency | warn | warn | - | Clip_09_刀尖抬起.mp4 |
| qc | consistency | warn | warn | - | Clip_10_刺杀裴长青.mp4 |
| qc | consistency | warn | warn | - | Clip_11_我只想活下去.mp4 |
| image_prompt | consistency | warn | warn | - | 图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | consistency | warn | warn | - | 图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | consistency | warn | warn | - | 图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | consistency | warn | warn | - | 图片/Clip08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.127 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | consistency | warn | warn | - | 图片/Clip08_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.14 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| image_prompt | consistency | warn | warn | - | 图片/Clip08_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.158 vs 场景中位 -0.091）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 |
| qc | consistency | warn | warn | - | Clip01_mid.png |
| qc | consistency | warn | warn | - | Clip04_mid.png |
| qc | consistency | warn | warn | - | Clip05_first.png |
| qc | consistency | warn | warn | - | 主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） |
| qc | consistency | warn | warn | - | 光位锚声明主光在「left」，实测最亮区却偏「right」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 |
| qc | consistency | warn | warn | - | 主光方位 right→left 硬翻转（疑光位跳·人比对相邻镜） |
| script | consistency | warn | warn | - | 镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 |
| script | consistency | warn | warn | - | 节奏/留存 advisory 总分偏低：57.4 |
| script | consistency | warn | warn | - | 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 |
| script | consistency | warn | warn | - | 开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s > 5s，前3秒易掉留存 |
| qc | consistency | warn | warn | - | 本机未配置重型 VLM runner；此文件仅占位并指向 manifest，不能作为 pass 结论。 |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| qc | consistency | warn | warn | - | DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| image_prompt | consistency | warn | warn | - | 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧、姿态/光流或 VLM 回读速度曲线、命中帧和距离/空间曲线是否成立。 |
| image_prompt | consistency | warn | warn | - | 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧、姿态/光流或 VLM 回读速度曲线、命中帧和距离/空间曲线是否成立。 |
| director_blocking | consistency | warn | warn | - | Clip_01 large_establishing 缺 Motion Control ready 输入：camera_path, depth_sequence, parallax_layers。 |
| director_blocking | consistency | warn | warn | - | Clip_02 realm_portal 缺 Motion Control ready 输入：depth_sequence, camera_path, spatial_path, vfx_layers。 |
| qc | consistency | warn | warn | - | Clip_06 fight_exchange 缺高动态后验证据字段：contact_map。 |
| qc | consistency | warn | warn | - | Clip_06 fight_exchange 动作关键维未实测：optical_flow_direction, limb_artifact, motion_blur_plausibility（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact runner 写 生产数据/spectacle_mo |
| qc | consistency | warn | warn | - | Clip_10 fight_exchange 缺高动态后验证据字段：contact_map。 |
| qc | consistency | warn | warn | - | Clip_10 fight_exchange 动作关键维未实测：optical_flow_direction, limb_artifact, motion_blur_plausibility（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact runner 写 生产数据/spectacle_mo |
| backend | consistency | warn | warn | - | 创作区/制漫剧/那妖魔是姜大人/合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| image_prompt | consistency | warn | warn | - | 出图/第1集/图片/Clip06_mid_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| image_prompt | consistency | warn | warn | - | 出图/第1集/图片/Clip06_end_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| backend | consistency | warn | warn | - | 合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| backend | consistency | warn | warn | - | 出视频/第1集/视频/Clip_06_裴长青最后一击被踹飞_part2.mp4 有多次 pass 记录但缺 redraw_reason/验收选择原因；后续无法判断哪版是正片依据。 |
| image_prompt | review_ui | info | info | - | 锚点门(N3): block=0 warn=0 ok=0 skipped=True |
| image_prompt | review_ui | info | info | - | 脸(G1): block=0 warn=0 ok=33 skipped=False |
| image_prompt | review_ui | info | info | - | 无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True |
| image_prompt | review_ui | warn | warn | - | 跨集脸漂(G5): block=0 warn=1 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 发型(H1): block=0 warn=0 ok=33 skipped=False |
| image_prompt | review_ui | info | info | - | 辨识标记(MK1): block=0 warn=0 ok=0 skipped=True |
| image_prompt | review_ui | warn | warn | - | 片内时序(N2): block=0 warn=15 ok=1 skipped=False |
| image_prompt | review_ui | info | info | - | 手部/解剖(N5): block=0 warn=0 ok=0 skipped=True |
| image_prompt | review_ui | info | info | - | 身高比例(R1): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 跨集体型(R2): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 外观判官(VAP): block=0 warn=0 ok=0 skipped=True |
| image_prompt | review_ui | info | info | - | 主体视频一致(S2V): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 表情连续(EXP1): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 表情过锁(EXP3): block=0 warn=0 ok=0 skipped=True |
| image_prompt | review_ui | info | info | - | 状态化表情(EXP2): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 多视角身份包(MVIEW): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | warn | warn | - | mechanical[一致性] 第1集: 脸部相似度度量已跳过（未装 face_recognition/insightface）——崩脸暂由人判清单覆盖；装库后跑 scripts/face_consistency.py 自动给每镜 vs 定妆锚点打分 |
| image_prompt | review_ui | info | info | - | 服装配色(N1): block=0 warn=0 ok=33 skipped=False |
| director_blocking | review_ui | info | info | - | 场景(O2): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 接缝接力: block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 轴线视线(X1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | warn | warn | - | 天气时辰(W1): block=0 warn=6 ok=0 skipped=False |
| director_blocking | review_ui | warn | warn | - | 色温调色(GRADE1): block=0 warn=6 ok=27 skipped=False |
| director_blocking | review_ui | info | info | - | 字幕安全区(L2): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 空间站位(B1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 物件常驻(O3): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 物件状态(OST): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 在场检测(O3V): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 视线状态回读(X2): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 场景平面(FP1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 相机空间轨迹(CAM1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | warn | warn | - | 运动质量(MOT1): block=0 warn=2 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 运动语法(MG1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | warn | warn | - | 高动态成片证据(SPECV): block=0 warn=6 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 世界一致性(WCS): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | warn | warn | - | mechanical[尾帧] 第1集: 本集需要尾帧接力 10 处 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity]: block=0 warn=10 skipped=False metrics={"avg_dhash_distance": 27.7, "max_dhash_distance": 35, "pairs": 10} |
| qc | review_ui | info | info | - | 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True |
| qc | review_ui | info | info | - | 译名一致(TX1): block=0 warn=0 ok=0 skipped=True |
| qc | review_ui | info | info | - | mechanical[字幕] 第1集: 检测到 fitted 配音轨 voice_*_fitted.wav：逐句原始时长清单 start 不再代表成片时间轴，跳过字幕起点漂移对账；以 compose/visual 的成片≈配音≈字幕末行对账为准。 |
| qc | review_ui | info | info | - | visual[subtitle_ocr]: block=0 warn=0 skipped=True |
| qc | review_ui | info | info | - | visual[subtitle_ocr] 缺 pytesseract/Pillow，字幕 OCR 跳过 |
| backend | review_ui | info | info | - | 音画同步(AV1): block=0 warn=0 ok=0 skipped=True |
| backend | review_ui | info | info | - | 多人对话音画(DAV): block=0 warn=0 ok=0 skipped=False |
| backend | review_ui | warn | warn | - | mechanical[完整性] 第1集: 产物快照：配音句 28 · 视频片段 16 · 成片 3 |
| backend | review_ui | warn | warn | - | mechanical[时长] 第1集: 源 clip 物理总长 125.78s 与镜头时长累计 120.52s 差 5.26s；已检测到 fitted 配音轨且成片 120.10s≈锁定槽位，split 时长已由 compose Time-Warp 修正。 |
| script | review_ui | info | info | - | visual[av_duration]: block=0 warn=0 skipped=False metrics={"final_sec": 120.117007, "srt_sec": 120.515, "storyboard_sec": 120.515, "voice_sec": 120.515034} |
| backend | review_ui | warn | warn | - | visual[av_duration] 音画时长对账通过：成片 120.12s |
| backend | review_ui | warn | warn | - | visual[lip_sync]: block=0 warn=1 skipped=False metrics={"mouth_visible_no_hits": 5, "mouth_visible_yes_hits": 6} |
| backend | review_ui | warn | warn | - | visual[lip_sync] 发现 6 处可见口型风险，但缺 lip-sync/SyncNet 外部检测报告 |
| qc | review_ui | info | info | - | 音色声纹: block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | warn | warn | - | 配音情绪弧(VEA): block=0 warn=1 ok=0 skipped=False |
| qc | review_ui | info | info | - | 口音方言(ACC): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | warn | warn | - | 声纹机检不可用：mode=no_speaker_backend precision=insufficient_precision；未装 resemblyzer/speechbrain 声纹后端——本机无法量音色相似度，交还人判（脸侧缺 insightface 同样降级） |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm): block=0 warn=3 ok=0 skipped=False |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：57.4 定位产物：脚本/第1集/storyboard.json |
| script | review_ui | warn | warn | - | visual[final_rhythm_density]: block=0 warn=1 skipped=False metrics={"clip_count": 11, "final_sec": 120.117, "hook_count": 10, "hook_interval_sec": 12.012, "shot_density_per_min": 5 |
| script | review_ui | warn | warn | - | visual[final_rhythm_density] 成片镜头密度 5.5/min 偏慢，可能前段留不住 |
| image_prompt | review_ui | info | info | - | 风格(S1): block=0 warn=0 ok=33 skipped=False |
| image_prompt | review_ui | info | info | - | 糊/低质(N4): block=0 warn=0 ok=0 skipped=False |
| image_prompt | review_ui | info | info | - | 景深一致(DOF1): block=0 warn=0 ok=33 skipped=False |
| qc | review_ui | info | info | - | 语义谱系(P0): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True |
| script | review_ui | info | info | - | 台词语域(D1): block=0 warn=0 ok=0 skipped=True |
| qc | review_ui | warn | warn | - | 视频VLM判题(VLM1): block=0 warn=1 ok=0 skipped=False |
| qc | review_ui | warn | warn | - | 视频VLM判题(VLM1) detail: 本机未配置重型 VLM runner；此文件仅占位并指向 manifest，不能作为 pass 结论。 定位产物：生产数据/video_vlm_consistency_第1集.json、出视频/第1集/video_vlm_consistency.json |
| script | review_ui | info | info | - | 伏笔兑现(SP1): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 状态百科(P1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | info | info | - | 状态转场视频证据(ST1): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 多模态(P2): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | warn | warn | - | 视频语义一致(VSEM): block=0 warn=8 ok=0 skipped=False |
| qc | review_ui | info | info | - | 特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True |
| qc | review_ui | info | info | - | 实体记忆(EMB): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 契约继承: block=0 warn=0 ok=5 skipped=False |
| image_prompt | review_ui | info | info | - | 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md |
| script | review_ui | info | info | - | 交互接触(I1): block=0 warn=0 ok=0 skipped=False |
| script | review_ui | info | info | - | 持有账本(POS): block=0 warn=0 ok=0 skipped=False |
| script | review_ui | info | info | - | 结构化交互图谱(I2): block=0 warn=0 ok=0 skipped=False |
| script | review_ui | info | info | - | 物理因果链(CG1): block=0 warn=0 ok=0 skipped=False |
| script | review_ui | info | info | - | 物理事件图(PHY): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 成片统一(C1): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 成片时间线探针(FT1): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 系列包装(PKG): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 系列调色(GRD): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 环境声(AMB): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 声音空间(ASP): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 生成配方(RCP): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 强配方Schema(RCP2): block=0 warn=0 ok=0 skipped=False |
| backend | review_ui | warn | warn | - | 成本路由(K1): block=0 warn=10 ok=0 skipped=False |
| image_prompt | review_ui | warn | warn | - | 成本路由(K1) detail: 创作区/制漫剧/那妖魔是姜大人/合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、合成/第1集/成片_第1 |
| qc | review_ui | info | info | - | 人审校准集(CAL): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 一致性探针包(PROBE): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 视频证据完整性(EVID): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 真值源(TRUTH): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 系统面板(UI1): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False |
| qc | review_ui | info | info | - | 文字渲染(OCR1): block=0 warn=0 ok=0 skipped=False |
| director_blocking | review_ui | warn | warn | - | 运动质量(MOT1) detail: 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧、姿态/光流或 VLM 回读速度曲线、命中帧和距离/空间曲线是否成立。 定位镜头：Clip_01 定位产物：生产数据/motion_quality_第1集.jso |
| director_blocking | review_ui | warn | warn | - | 高动态成片证据(SPECV) detail: Clip_01 large_establishing 缺 Motion Control ready 输入：camera_path, depth_sequence, parallax_layers。 定位镜头：Clip_01 定位产物：出视频/第1集/control/Clip_01/motion_control_m |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 死人堆惊醒 接缝 dHash 距离 29 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s > 5s，前3秒易掉留存 定位镜头：EP01_CLIP01、Clip_01 定位产物：脚本/第1集/storyboard.json |
| qc | review_ui | warn | warn | - | 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_01 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consist |
| director_blocking | review_ui | warn | warn | - | 运动质量(MOT1) detail: 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧、姿态/光流或 VLM 回读速度曲线、命中帧和距离/空间曲线是否成立。 定位镜头：Clip_02 定位产物：生产数据/motion_quality_第1集.jso |
| director_blocking | review_ui | warn | warn | - | 高动态成片证据(SPECV) detail: Clip_02 realm_portal 缺 Motion Control ready 输入：depth_sequence, camera_path, spatial_path, vfx_layers。 定位镜头：Clip_02 定位产物：出视频/第1集/control/Clip_02/motion_contro |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 看见虎妖尸身 接缝 dHash 距离 24 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| backend | review_ui | warn | warn | - | mechanical[原生音轨] 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4: clip 含原生音轨；compose 默认应丢弃。若按 opt-in 混入环境声，需确认低风险、无口型、无原生人声 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 镇魔司压迫交易 接缝 dHash 距离 28 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| qc | review_ui | warn | warn | - | 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_03 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consist |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 被迫扶裴南行 接缝 dHash 距离 24 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| qc | review_ui | warn | warn | - | 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_04 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consist |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| qc | review_ui | warn | warn | - | 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_05 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consist |
| director_blocking | review_ui | warn | warn | - | 高动态成片证据(SPECV) detail: Clip_06 fight_exchange 缺高动态后验证据字段：contact_map。 定位镜头：Clip_06 定位产物：生产数据/spectacle_video_qc_第1集.json、出视频/第1集 |
| director_blocking | review_ui | warn | warn | - | 高动态成片证据(SPECV) detail: Clip_06 fight_exchange 动作关键维未实测：optical_flow_direction, limb_artifact, motion_blur_plausibility（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact run |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| image_prompt | review_ui | warn | warn | - | 成本路由(K1) detail: 出图/第1集/图片/Clip06_mid_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位镜头：Clip_06 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图 |
| image_prompt | review_ui | warn | warn | - | 成本路由(K1) detail: 出图/第1集/图片/Clip06_end_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位镜头：Clip_06 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图 |
| director_blocking | review_ui | warn | warn | - | mechanical[衔接] clip#7: start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，需无缝尾帧接力时再原样继承 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| script | review_ui | warn | warn | - | 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、 |
| script | review_ui | warn | warn | - | mechanical[视频] 第1集: 检测到 split-part 视频：物理 MP4 16 / 逻辑 clip 11 / storyboard 11 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 死人堆惊醒 接缝 dHash 距离 29 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 看见虎妖尸身 接缝 dHash 距离 24 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 看见虎妖尸身 接缝 dHash 距离 24 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 镇魔司压迫交易 接缝 dHash 距离 28 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 镇魔司压迫交易 接缝 dHash 距离 28 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 被迫扶裴南行 接缝 dHash 距离 24 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |
| director_blocking | review_ui | warn | warn | - | visual[image_similarity] 被迫扶裴南行 接缝 dHash 距离 24 > 22：视觉差异较大，按剪辑语义人判是否为合法跳切 |

## Preventive Rule Updates

| category | gate | severity | rule |
|---|---|---|---|
| backend | audio_timing_gate | must_update | 高频口型/路由/模型能力问题出现后，提升 mouth_policy、voice_or_native_policy、fallback backend 和能力证据要求。 |
| director_blocking | interaction_physics_gate | must_update | 高频调度/接缝/动作问题出现后，提升动作分解、屏幕站位、接触点、首尾帧/转场降级方案要求。 |
| image_prompt | reference_slot_gate | must_update | 高频脸漂/道具漂/风格漂问题出现后，提升真实参考、多视角、身份锁句和 prompt 继承回执要求。 |
| production_breakdown | reference_slot_gate | must_update | 高频资产/场记问题出现后，提升引用槽位 path/hash、状态机、适用后端和降级策略要求。 |
| qc | release_verdict | must_update | 高频 QC 新鲜度/验收问题出现后，提升证据指纹、母版 hash、review-ui/ledger 新鲜度和人工签收要求。 |
| script | episode_promise_gate | must_update | 高频剧情/动机/因果问题出现后，提升每集承诺合同的 promise/obstacle/payoff/cliffhanger 与 source_trace_ids 填写要求。 |
