# 编辑修订工作单（编剧级整体改良提案）

- 埋了没还的伏笔：0
- 主线接不上处：1
- 琐碎支线提案精简：0
- 不合理点候选（待核原著）：0


## 主线接不上（承接点接回 spine.depends_on）
- SRC_CAUSE_005：西门庆对仆役、下层女性和办事人的占有与惩罚不断升级 → 宋惠莲等人受辱死亡，来旺等被驱逐，家庭内部积累恐惧、怨恨和背叛

> 像真实编剧整体改良：① 砍/合 tangent_candidates 里的琐碎支线以突出主情节；② 补还或删除 foreshadow_debt 里埋了没还的伏笔；③ mainline_gaps 处把主线承接点接回 spine.depends_on；④ unreasonable_beats 逐条核对原著：真是硬伤就写进 story_spine.continuity_fixes（最小改动+no_contradiction_proof+touches_protected 标注），是原著本有合理铺垫或有意为之就在 revision_ledger 记 dismiss 理由。所有改动落回 story_spine.json 的 threads[].decision/connectivity 与 continuity_fixes，再跑 story_spine.py check 做防瞎编+衔接硬校验。禁止臆造任何 id；改后主线必须仍衔接。unreasonable_beats 全是候选不是定论——不得据它凭空加情节，只能核原著后做最小修补或标注。
