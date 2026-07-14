---
name: comic-identity
description: 画漫画角色/场景/道具一致性流程。Use when comic panels show character drift, wrong faces, changed outfits, inconsistent monsters/props/locations, missing shared reference images, needing 定妆/identity_registry/reference anchors, rerun plans for affected panels, or a consistency gate before comic-compose for projects under 创作区/画漫画. Produces 出图/共享/identity_registry.json, 出图/共享/图片 anchors, comic identity reports, and panel rerun targets. Triggers 漫画一致性, 角色一致性, 定妆, 换脸, 脸漂, 共享参考, identity_registry, comic-identity.
---

# comic-identity — 漫画共享定妆与一致性闸门

在 `comic-image` 和 `comic-compose` 之间补一层一致性流程：先把会反复出现的人物、妖物、场景、道具、系统资产落成共享参考，再让逐格出图真实消费这些参考图。不要把人物漂移的图直接交给 `comic-compose`。

用户给了“定型图/标准图/这张就是主角”的图片时，把它当作最高优先级锚点写进 `identity_registry.json`，并同步提炼 `character_dna`、`dna_contract`、`variant_policy` 和 `forbidden_inheritance`。同一角色的童年、少年、成年、闭关前后、受伤、觉醒、境界变化、换装都必须从这张定型图继承脸型、发际线、发量、眼型、气质和标志物，只能改变年龄比例、状态、服饰层和特效强度。截图里的播放按钮、搜索框、字幕、水印、平台 UI、竖排标题或可读文字不是设定，必须列入禁继承项。

## 输入

- `脚本/第N话/panel_script.json`：每格的 `references` 真值。
- `出图/第N话/prompt/panel_jobs.json`：逐格出图任务和当前引用绑定。
- `出图/第N话/panels/*.png`：已采纳或待复核的面板图。
- `出图/共享/图片/` 与 `出图/共享/identity_registry.json`：共享定妆库。

## 输出

- `出图/共享/identity_registry.json`：schema v2 统一机器真值；角色含 `forms/outfits/expressions/states/default_binding`，`FX_`/`VFX_` 统一为 `vfx`，`SYS_`/`PROP_`/`OUTFIT_` 保持各自标准类型。
- `出图/共享/图片/<REF_ID>__anchor.png`：可传给生图后端的锚点图。
- `出图/共享/图片/<CHAR_ID>__front.png` / `__three_quarter.png` / `__side.png` / `__back.png` / `__face.png`：人物标准多视图包。项目 `_设置.md` 的 `定妆级别` 默认是 `长线专门定妆`，常驻角色进入批量生产前必须补齐。
- `生产数据/comic_identity_anchors_第N话.json`：非人物共享锚点生成记录。
- `生产数据/comic_identity_views_第N话_contact_sheet.jpg`：人物多视图 QA 拼图，用于快速检查是否缺图、串脸或视图不对。
- `生产数据/comic_identity_report_第N话.json/md`：缺失引用、每格真实参考输入数、重抽目标。
- `生产数据/comic_model_pack_signoffs/<CHAR_ID>.json`：绑定全部必需视图 SHA 的人审签收；任一视图变化自动 stale。
- `生产数据/comic_model_pack_report.json`：多视图技术缺陷、同源证据、签收状态和 `ready/needs_approval/needs_fix`。
- 更新 `panel_jobs.json` 中每个 reference 的真实 `path`。
- `设定库/共享资产索引.md`：从 comic 自己的统一 registry 派生的单一人读总览；registry 仍是机器真值，不再为每个角色/资产复制 manifest 目录树。

## 快速命令

新项目先建立合法的空 v2 registry；`init` 幂等且不会创建任何图片，也不会伪造 `ready` 资产：

```bash
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" init --write --json
```

在定妆出图前先用纯文本登记稳定资产 ID。`CHAR_`/`MON_` 会自动补齐可供分格脚本引用的
`FORM_BASE / OUTFIT_BASE / EXPR_NEUTRAL / STATE_BASE` 与 `default_binding`，状态保持
`needs_reference`；`LOC_`/`PROP_`/`STYLE_` 同样只登记合同，不生成或假装已有参考图：

```bash
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" upsert \
  --asset-id CHAR_LIN --name "林冲" --tier core_full \
  --character-dna "豹头环眼；发际线、眼型、身材比例和标志伤痕固定" \
  --forbidden-inheritance "不得继承演员脸、临时手持物或单格走位" --write --json
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" upsert \
  --asset-id LOC_TEMPLE --name "伏魔殿" --description "布局、主光和常驻物件待视觉研究后锁定" --write --json
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" upsert \
  --asset-id PROP_SEAL --name "伏魔殿石碣封印" --write --json
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" upsert \
  --asset-id STYLE_SONG_CINEMATIC --name "宋画电影感" --notes "研究来源与禁复刻项写入视觉参考研究" --write --json
```

`story_bible.md` 中每个具名角色使用稳定标题 `### 人读名称 CHAR_STABLE_ID`（妖物用
`MON_`）；文字首锚会按完整 ID 读取该标题下的设定，不会把 `CHAR_LIN` 误匹配成
`CHAR_LINCHONG`。

旧 registry 先预览迁移，再显式写回 schema v2；迁移保留旧资产，但核心角色旧 `ready` 降为 `needs_approval`：

```bash
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" migrate --json
python3 skills/comic-identity/scripts/registry_v2.py "创作区/画漫画/作品名" migrate --write --json
```

从已采纳面板种下共享锚点：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 seed \
  --map CHAR_JYC=P002 --map CHAR_PEI=P005 --map MON_TIGER=P004 --overwrite
```

已有 `panel_jobs.json` 后，生成一致性报告并回填可解析路径：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 report --write
```

按长线口径生成常驻角色专门定妆多视图：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend auto --characters CHAR_JYC,CHAR_PEI --views front,three_quarter,side,back,face
```

生成完先做确定性技术检查，再由人并排确认角色、视图标签、比例、基线、服装标志与中性姿态。签收绑定当前全部视图 SHA，不能用旧 receipt 放行新图片：

```bash
python3 skills/comic-identity/scripts/model_pack.py "创作区/画漫画/作品名" check --write --json
python3 skills/comic-identity/scripts/model_pack.py "创作区/画漫画/作品名" signoff \
  --characters CHAR_JYC --confirm-all --reviewer "责任编辑" --reason "五视图并排复核通过" --json
```

批量定妆会在每个角色/视图完成后立即输出 `[ok]` 进度；不要等整批结束才判断是否卡住。`--max-attempts` 是总尝试次数，不是额外重试次数。
恢复中断批次时，已有有效图会以 `character_view_reused` 写入本次 manifest，保留路径、SHA 和原始 source 证据；不能只记 `skipped` 数而丢掉逐项可追溯性。
单一视图的多人选角批次会输出最多三列的 casting 网格；完整多视图批次仍输出“角色为行、视图为列”的 turn-around 矩阵，便于发现串脸和视图错误。
`--overwrite` 重抽共享锚或角色视图时，旧采纳图必须先归档到 `出图/共享/candidates/<asset>/<variant>/`，新图验证为有效 PNG 后再原子替换；每次实际生成还要把完整提示快照写入 `生产数据/comic_identity_prompts/`，并在 source/manifest 记录 prompt 路径与 SHA。

从小说/剧本直接开画、还没有任何角色锚点时，先显式允许用文字设定生成首张 `front`，再用这张 front 派生其它视图：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend codex --characters CHAR_JYC,CHAR_PEI --views front,three_quarter,side,back,face --allow-text-anchor
```

生成妖物、场景、道具等非人物共享锚点：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 anchors \
  --refs MON_TIGER,LOC_STREET,PROP_SWORD
```

Codex 图像通道不可用或需要真实图生图后端时，可显式走即梦官方 CLI：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 views \
  --backend dreamina --characters CHAR_JYC,CHAR_PEI --views front,three_quarter,side,back,face \
  --model-version 5.0 --resolution-type 2k
```

报告里的 `rerun_targets` 交给 `comic-image` 重抽：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 \
  --targets P003,P004 --force --max-attempts 3
```

从当前 `identity_registry.json` 生成项目内单一共享资产索引：

```bash
python3 skills/comic-identity/scripts/library.py "创作区/画漫画/作品名" --write
```

旧项目若存在纯机器派生的 `角色库/`、`资产库/`，可一次性安全迁移：

```bash
python3 skills/comic-identity/scripts/library.py "创作区/画漫画/作品名" --write --remove-legacy-views
```

迁移只会删除内容完全由 `manifest.json`、`00_索引.json` 组成的旧视图；发现图片、说明或其它人工文件会立即拒绝删除。这一步采用工业资产包的真值/视图分离思想，但实现、schema 和真值均属于 comic，不引入视频路由、配音、外部训练状态或其它系列项目 ID。漫画线根目录 `_资产库/` 是跨作品复用包，不属于这次项目内去重。

## 工作流

1. 若本话还没有 `出图/第N话/prompt/panel_jobs.json`，先用 `comic-image` 的 `build_panel_jobs.py` 生成；再跑 `report --write`。若有 `missing_refs`，先补共享参考，不要合成。
2. 对常驻角色和关键资产建立锚点。短 demo 可从已采纳面板种 `__anchor.png`；默认长线口径应换成正面/45度/侧面/背面和关键表情的专门定妆图。用 `views` 子命令从当前 anchor 生成并登记多视图；`--backend auto` 会优先用可用后端，必要时可显式指定 `dreamina`。
   - `STYLE_` 风格锚必须生成单幅非叙事校准画，同时可读人物脸/手、线条层级、肤色、衣料与场景材质、三值明暗和特效边缘；不得用含义不明的抽象图、拼贴或角色卡代替。`FX_`/`VFX_` 锚则单独校准形状语言、运动方向、色域和留白关系。
   - 从源小说、源剧本或古文直接开画时，若还没有任何可采纳角色图，只能在用户确认图像生成成本后显式传 `--allow-text-anchor`，让 Codex 根据 `story_bible.md` 和 `identity_registry.json` 生成第一张 `front` 定妆；后续视图再以这张 front 为参考锚点。
   - 若项目已有可用 `STYLE_` 风格锚，文字生成首张 `front` 时必须把它作为真实 `style_only` 图片附件，并记录路径与 SHA-256；提示中明确禁止继承风格锚人物的脸、发型、服装、体态、姿态和构图。风格锚不能冒充角色身份锚。
   - 对公版经典、历史题材或已有多版影视改编的项目，首张文字定妆前必须完成项目 `设定库/visual_research.json`，并运行 `python3 skills/comic/scripts/visual_research_contract.py <作品根> check --strict --json`；人读笔记可另存 `设定库/视觉参考研究.md`，registry `notes` 只引用该合同，不得取代。优先源本、学术/博物馆/权威资料、官方/资料库式影视条目；只抽取服制、阶层、场景、道具和叙事功能。不要上传或复刻影视剧照，不要求画成某演员，不复制具体构图、镜头、服饰组合或露骨尺度。
   - `views` 默认对非 `front` 视图优先使用已存在的 `front` 定妆图作为参考锚点，避免原剧情格的坐跪、挥砍、裁切等动作姿态污染多视图；需要强制用原始锚点时传 `--no-prefer-front-anchor`。
   - `MON_`、`LOC_`、`PROP_` 等非人物资产用 `anchors` 生成 `__anchor.png` 并回写 registry；这些锚点必须先通过 `report --write` 绑定到 `panel_jobs.json`，再进入逐格出图。
   - `LOC_` 场景锚必须保持为无人物的纯场景资产；合同即使记录人物站位，也只在对应位置预留空白与走位空间，不得把具体人物、无身份剪影或角色表演固化进长期场景参考。人物由逐格任务另附已签收角色定妆图。
   - 除 `STYLE_` 本身外，非人物锚生成时若项目已有风格锚，必须把它作为真实 `style_only` 图片附件并记录 SHA；只继承线条、上色、明暗、材质、色域和墨晕，禁止复制风格锚人物、服装、物件、场景布局或构图。
3. 重新跑 `report --write`，确认每个带 reference 的格子都有真实图片路径。
4. 对 `rerun_targets` 用 `comic-image` 的 `--force --targets ...` 重抽。runner 会把参考图作为 `codex exec --image` 真实附件传入，并写 `生产数据/codex_reference_bundles/`。
5. 重抽后再跑一次 `report --write`。`missing_refs=[]` 且 `rerun_targets=[]` 后，才进入 `comic-compose`。
6. 长线项目在 registry 有新增/改名/分级后运行 `library.py --write`，刷新 `设定库/共享资产索引.md`；只改 registry，不手工修改自动索引。
   - 索引的已有参考数只统计真实存在的身份参考；尚未落盘的声明进入计划数，生成时使用的 style-only/anchor 输入不冒充身份参考。禁止递归扫描 source 元数据后把计划路径或生成依赖虚报成“已有参考”。

## 判定口径

- `reference id` 只是名字，不等于模型看见了参考图；必须有真实 `path`，并在生成记录里有 `reference_input_count > 0`。
- 带 `CHAR_` 或 `MON_` 的格子如果是旧图、没有 reference manifest、或生成时 `reference_input_count=0`，必须进 `rerun_targets`。
- `report` 会按 reference manifest 记录的 sha256 比对参考图当前内容：生成后换过锚点/定妆图内容（含 `seed --overwrite`）或参考文件消失的 ready 格进 `rerun_targets`（`stale_generated_refs` 给出逐图原因）；生成后新增的参考图不强制重抽。
- 多人同框不是删除剧情的理由；补齐每个主体的锚点，再重抽该格。
- 人物标准多视图是 `front / three_quarter / side / back / face`。`report --write` 会列 `missing_character_views`；`定妆级别=长线专门定妆` 时这些缺口是进入发布/连载审查前的阻断项。
- 角色 registry 的 `status` 必须诚实反映生产就绪度：缺视图是 `partial`；1×1、错误 source view、重复图片冒充不同视角或全身画布不一致是 `needs_fix`；核心角色文件齐全但没有当前 SHA 人审签收是 `needs_approval`；只有技术检查通过且 receipt 当前有效才是 `ready`。像素/直方图相似度只能 `warn`，不得替代并排人审。
- schema v2 的 `forms/outfits/expressions/states/default_binding` 是逐格状态真值。`state` 引用的 form/outfit/expression 必须已登记且彼此一致；不允许用显示名、松散文字或 panel-wide 单个 `outfit_id` 替代逐角色绑定。
- **服装子注册表（outfits）**：业界已验证的失效模式是"锁了脸锁不住领型/纽扣/花纹"。同一角色的每套换装在 `registry.assets[CHAR_x].outfits[OUTFIT_y]` 登记 `{id, name, description, forbidden, reference_images}`；分格脚本用该角色 `character_bindings[].outfit_id` 引用，并绑定与之相符的 `state_id`。`report` 会检查换装格的登记与服装参考图（`outfit_gaps`）。修复服装漂移优先补服装参考图重抽，不走"每套服装一个 LoRA"。
- 角色一致性不只看“像不像脸”。登记 `character_dna/dna_contract` 时必须覆盖脸型、眼型/眼距、鼻梁/嘴型、发际线、发型轮廓、服装主色、标志配饰/伤痕/灵纹、身高体态和眼神气质；这些字段会被 `comic-image` 写入逐格 prompt。
- 永久身份与临时调度必须拆开：永久身体特征/佩饰才进入 `character_dna`；剧情手持物、画面左右站位、注视目标、同框遮挡和一次性动作写入 `transient_props/staging_defaults` 或逐格契约。中性 `front/three_quarter/side/back/face` 不得把临时剧情物固化成角色身份。
- `visual_contract.scene_anchors` 里的 `LOC_` 场景锚同样属于 identity 层资产：关键场景必须登记布局、常驻物件、主光方向/冷暖、轴线视线和禁漂移项。缺场景锚时不要直接批量出图。
- 漫画格的眼神和完整性标准必须独立达标：角色必须有戏内 `gaze_target`，身体和关键道具必须完整可读；“漫画夸张”“Q版动态”不能作为换脸、换眼型、丢手脚、丢服装标志或场景漂移的豁免。
- `参考一致性策略` 选择高一致性长线口径或开启 `年龄形态继承` 时，角色资产必须有可读的 DNA/禁漂移项和形态继承说明；缺失时先回本 skill 补登记，不要让 `comic-image` 用松散 prompt 硬跑。
- 出图阶段不再生产空白气泡：台词、旁白、拟声词和气泡形状属于 `comic-compose`。旧图中遗留无字气泡时，优先回 `comic-image` 重出无气泡画面；无法重出时，合成阶段只能遮盖对应文字槽，不应留下空泡。

## 不做什么

- 不把其它生产线脚本或数据结构直接 import 到漫画线；本 skill 只使用漫画线自己的共享定妆、真实参考入参和重抽计划流程。
- 不做本地贴脸、换脸或裁脸贴回。修复脸漂应重抽整格或补定妆后重抽。
- 不替代 `comic-image` 生成图片，也不替代 `comic-compose` 嵌字。

## tier 分档必需视图与跨话记忆锚（2026-07 落地）

- **分档必需视图**：`identity.py` 的必需视图按 `library_tier` 分档——`core_full` 全五视图（front/three_quarter/side/back/face）、`recurring_standard` 三视图（front/three_quarter/face）、`named_minimal` 两视图（front/face）、`restricted_partial` 不要求；未标档保守按全五视图。此前对短线具名角色也一刀切全五视图属过度要求；档位只控生产深度，不改角色 DNA 真值。registry 每角色 `view_readiness.tier` 留痕。
- **跨话记忆锚**：`python3 skills/comic-identity/scripts/memory_anchor.py <作品根> 第N话 --write` 扫全部话次出场史，对**复现间隔 ≥2 话再登场**或**距首次登场 ≥5 话**的角色，把 registry 里最早 front/face 定妆钉为最高优先参考，落 `生产数据/comic_memory_anchor_第N话.json`。v2 计划记录全部 panel script、registry 与 pinned 图片 SHA 的 `inputs_fingerprint`；任一输入变化自动判 stale，长间隔角色在计划缺失/过期时不能建立正式出图包。
- **跨话角色漂移报表（report-only·审查阶段 gate 自动跑）**：单话 `character_consistency` 看不见"这角色从第几话开始崩、是不是跨话反复崩"。`python3 skills/comic-identity/scripts/drift_report.py <作品根> [--chapters 1-10] --write` 汇总各话已生成的 `生产数据/comic_character_consistency_第N话.json`，产 `生产数据/comic_identity_drift_report.{json,md}`：逐角色×逐话 🟢/🟡/🔴 时间线、`first_bad_chapter`、跨话漂移话次数，并按 findings 类别给工程化建议（缺参考→补 anchor/front/face；服装漂→补 outfits 子注册+参考图；跨话反复→补专门定妆多视图或换持久主体后端，漫画线不内置 LoRA；单话→按 rerun_targets 重抽）。只读各话报告、只写汇总——不重算像素、不改 registry、不重抽。`comic-review gate --stage review` 以 advisory 并入（info·不新增阻断，单话该拦的漂移已在 image 阶段拦过）。与 memory_anchor（事前钉锚）、reference_planner（事前处方）互补：这是**事后跨话**的"机器统计从哪话崩"。
