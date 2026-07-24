# 编辑修订工作单（编剧级整体改良提案）

- 埋了没还的伏笔：3
- 主线接不上处：0
- 琐碎支线提案精简：1

## 与主线不相干的琐碎支线（提案 cut/compress，突出主情节）
- **THREAD_QINGMIAN**（青面郎君威胁线·分1）→ 提案 compress

## 埋了没还的伏笔（补还或删设定）
- SRC_FORESHADOW_001 🔒受保护：受保护伏笔，必须补还回收，不能砍
- SRC_FORESHADOW_002 🔒受保护：受保护伏笔，必须补还回收，不能砍
- SRC_FORESHADOW_003 🔒受保护：受保护伏笔，必须补还回收，不能砍

> 像真实编剧整体改良：① 砍/合 tangent_candidates 里的琐碎支线以突出主情节；② 补还或删除 foreshadow_debt 里埋了没还的伏笔；③ mainline_gaps 处把主线承接点接回 spine.depends_on；④ 不合理点写进 story_spine.continuity_fixes（最小改动+no_contradiction_proof）。所有改动落回 story_spine.json 的 threads[].decision/connectivity 与 continuity_fixes，再跑 story_spine.py check 做防瞎编+衔接硬校验。禁止臆造任何 id；改后主线必须仍衔接。
