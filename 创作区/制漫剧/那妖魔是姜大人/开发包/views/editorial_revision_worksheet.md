# 编辑修订工作单（编剧级整体改良提案）

- 埋了没还的伏笔：3
- 主线接不上处：0
- 琐碎支线提案精简：1
- 不合理点候选（待核原著）：1

## 不合理点候选（机检·须逐条核对原著，绝不据此瞎编）
- **SRC_CAUSE_004**（ungrounded_cause）：此因果的 cause 与此前所有因果/伏笔/动机零重叠——可能缺前因（天降）。
## 与主线不相干的琐碎支线（提案 cut/compress，突出主情节）
- **THREAD_QINGMIAN**（青面郎君威胁线·分1）→ 提案 compress

## 埋了没还的伏笔（补还或删设定）
- SRC_FORESHADOW_001 🔒受保护：受保护伏笔，必须补还回收，不能砍
- SRC_FORESHADOW_002 🔒受保护：受保护伏笔，必须补还回收，不能砍
- SRC_FORESHADOW_003 🔒受保护：受保护伏笔，必须补还回收，不能砍

> 像真实编剧整体改良：① 砍/合 tangent_candidates 里的琐碎支线以突出主情节；② 补还或删除 foreshadow_debt 里埋了没还的伏笔；③ mainline_gaps 处把主线承接点接回 spine.depends_on；④ unreasonable_beats 逐条核对原著：真是硬伤就写进 story_spine.continuity_fixes（最小改动+no_contradiction_proof+touches_protected 标注），是原著本有合理铺垫或有意为之就在 revision_ledger 记 dismiss 理由。所有改动落回 story_spine.json 的 threads[].decision/connectivity 与 continuity_fixes，再跑 story_spine.py check 做防瞎编+衔接硬校验。禁止臆造任何 id；改后主线必须仍衔接。unreasonable_beats 全是候选不是定论——不得据它凭空加情节，只能核原著后做最小修补或标注。

## 动作账（已处理）
- **dismiss** `SRC_CAUSE_004`：不合理点候选（ungrounded_cause）核对原著后不成立：第1章百妖谱现身与规则展示先于其驱动杀裴决策；改编第1集 CLIP07 亦以『绝境触发→卷轴展…
- **compress** `THREAD_QINGMIAN`：机检提案 compress 采纳：贡献分低（无伏笔承载、无主线因果依赖）但 serves_mainline 指明其供给集尾钩——故压缩篇幅而非整线砍除，功能节拍…
- **schedule_payoff** `SRC_FORESHADOW_001`：按合同 payoff_plan（随镇魔司调查与姜家线逐步回收）保持 open 并延后：当前窗口（前5集）不硬塞身世揭示；THREAD_JIANG 已按 comp…
- **schedule_payoff** `SRC_FORESHADOW_002`：按合同 payoff_plan（先展示可验证规则、来源延后、每次新能力增补合同）延后：第1集已入画三条可验证规则；来源/上限/代价随狼妖弧新能力需要时增量释放（…
- **schedule_payoff** `SRC_FORESHADOW_003`：按合同 payoff_plan（在镇魔司追查、伪装身份与良知压力中持续推进）延后：第3集埋尸告别与取衣是本伏笔的持续推进拍（EP03_CLIP02 沉默半拍），…
