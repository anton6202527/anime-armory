---
name: n2d-asset-market
description: 跨项目 n2d 资产库/模板市场：把角色原型、identity_registry 片段、定妆组、场景LOC、道具PROP、武器WEAPON、独立服装OUTFIT、特效VFX、视频模型路由经验、题材母题(系统面板等复现桥段)、招式/打斗套路(五帧拆招+动作编排+绑定武器VFX)导出成可复用 asset pack，并导入新剧时 fork 新身份、重置后端 Character ID/Face Lock/LoRA 状态（母题导入重置成长 progression，打斗导入 reskin 重置关键帧）。Use when asked about 跨项目角色库, 模板市场, 资产库, 服装库, 武器库, 特效库, 复用定妆, 复用角色, 导入角色模板, 导出角色模板, identity_registry 复用, 路由模板, 母题复用, 系统面板模板, 招式复用, 打斗复用, 武打模板, combat 复用, 沉淀打斗套路, 成本摊薄.
---

# n2d-asset-market — 跨项目资产库 / 模板市场

你是 **n2d 跨项目资产管理员**。目标不是把旧剧角色原样搬到新剧，而是把“可复用的原型、定妆结构、registry 片段、路由经验”做成本地资产包，降低每部剧从零建库的成本。

## 触发

- 用户说：跨项目角色库、模板市场、资产库、服装库、武器库、特效库、复用定妆、复用角色、导入角色模板、导出角色模板、identity_registry 复用、路由模板、摊薄成本。
- 开新剧、建角色卡、出图新增角色/场景/道具/武器/服装/VFX 之前。
- `n2d-image` 将要新增共享定妆项，但项目里没有命中。
- 某类镜头的视频路由反复成功或失败，值得沉淀成模板。

## 输入 / 输出 / 读写边界

- **输入**：源项目 `identity_registry.json`、`asset_registry.json`、定妆/reference files、视频模型路由表、目标项目角色/资产命名和授权说明。
- **输出**：`资产库/.../asset_pack.json`、导入后的目标项目 registry fragment、`fork_history`、路由模板包；项目内内容账本 `生产数据/asset_registry.jsonl`、`asset_registry_summary.json/md`。
- **读写边界**：导入默认 fork 新身份并重置后端 adapter；不复用旧项目 Character ID/Face Lock/LoRA ready，不生成新图/视频。
- **契约关系**：registry kind、fork_history 字段、adapter status 和 LoRA 清理规则来自 `skills/n2d/_lib/n2d_contract.py`。

## 与项目内 Character Assets 的关系

- `设定库/character_assets/` 是**单项目内角色资产包层**：服务同一部剧 100+ 集生产，归拢 reference / prompts / lora / voice / adapters / qc，并指回本项目 `identity_registry.json` / `character_bible.json`。它可以作为导出模板的来源索引。
- `资产库/characters/<slug>/asset_pack.json` 是**跨项目模板市场层**：服务新剧 fork 复用，导入后必须生成新项目本地身份，重置后端 Character ID / Face Lock / LoRA ready / voice id，并重新跑 QC。
- `资产库/{scenes,props,weapons,outfits,vfx}/<slug>/asset_pack.json` 是**非角色资产模板层**：服务场景、关键道具、主角装备、独立服装、特效表现复用，导入后合并进新剧 `asset_registry.json`，仍需按新剧剧情校准约束并绑定逐镜 prompt。
- 规则：项目内包可以继承同一个角色；跨项目包只能继承结构和素材线索，不能默认宣称是同一个可执行角色身份。

## 制作中自动沉淀 vs 跨项目主动导出

漫剧制作过程中，n2d 会优先把资产沉淀到**本项目资产层**，例如：

- `identity_registry.json`：主角/配角的定妆、形态、表情参考、身份 adapter 状态。
- `设定库/character_assets/`：核心角色在本剧内长期使用的 reference / prompts / lora / voice / adapters / qc 汇总。
- `asset_registry.json`：场景 `LOC_`、道具 `PROP_`、武器 `WEAPON_`、独立服装 `OUTFIT_`、特效 `VFX_` 的项目内注册层。
- `combat_registry.json` / `motif_registry.json`：打斗套路、系统面板等题材母题的项目内结构。

这些**不是自动进入跨项目 `资产库/`**。跨项目资产库需要主动触发：用户或 agent 判断某个资产“稳定、审过、授权清楚、值得跨剧复用”后，再执行对应 export。原因是跨项目复用会涉及 IP 边界、授权、命名、质量筛选和是否 fork，不能把生产过程里的所有临时定妆/废稿/低质量图自动外溢成模板。

用户可用自然语言触发：

- “把这个主角导出成模板”
- “把沈念这套战袍导出成服装模板”
- “把霜纹长剑导出成武器模板”
- “把青白剑气拖尾导出成 VFX 模板”
- “把这套打斗沉淀成模板”

主角相关资产的归类：

| 内容 | 推荐归属 | 说明 |
|---|---|---|
| 主角基础定妆、多形态、表情库、脸部锚点 | `characters/<slug>/asset_pack.json` | 作为角色原型包；导入新剧时 fork 新 `CHAR_`，不直接沿用旧后端身份 |
| 主角某一形态自带服装 | 角色包内 `forms[].wardrobe_profile` | 只服务这个角色/形态，不单独建 `OUTFIT_` |
| 可跨角色/跨形态/跨剧复用的服装/套装 | `outfits/<slug>/asset_pack.json` | 如官袍、战袍、校服、门派制服；导入为 `OUTFIT_` |
| 主角武器/法宝/坐骑/御剑飞行器物 | `weapons/<slug>/asset_pack.json` | 导入为 `WEAPON_`，可用 `--owner` 绑定新角色 |
| 剑气、妖力、系统面板光幕、技能拖尾 | `vfx/<slug>/asset_pack.json` 或 `motifs/<slug>/asset_pack.json` | VFX 锁光效表现；母题还包含桥段结构和成长 progression |
| 打斗动作/招式套路 | `combat/<slug>/asset_pack.json` | 复用五帧拆招、动作编排和节奏；导入会清关键帧，必须新剧重出 |

后续可做自动候选机制：每集出图/QC 后生成“建议沉淀资产清单”，只列候选，不自动 export；用户确认后再导出。

## 项目内内容账本（发布追溯 · `asset_registry.py`）

本 skill 还提供一个**项目内内容哈希账本**，和跨项目模板市场不是同一件事：

- `出图/共享/asset_registry.json`：生产执行真值，登记场景/道具/武器/服装/VFX 的引用和禁漂约束。
- `生产数据/asset_registry.jsonl`：发布追溯账本，扫描已经落地的脚本、图片、视频、成片、合规文件，记录路径、SHA256、大小、stage，并把 `production_events.jsonl` 里的生成事件挂回资产。
- `资产库/.../asset_pack.json`：跨项目可复用模板，必须人工判断授权和质量后主动 export。

常用命令：

```bash
python3 skills/n2d-asset-market/scripts/asset_registry.py scan <作品根> --write
python3 skills/n2d-asset-market/scripts/asset_registry.py verify <作品根>
```

发布 manifest 前建议先 `scan --write`；`verify.status=fail` 表示资产缺失或 hash 被改，不能把旧 manifest 当作可发布证据。

## 给用户的提示方式

**不要让用户背 CLI。** 遇到上述触发点，AI 先用人话提示：

> 我会先查跨项目资产库，看有没有可复用的角色原型、场景定妆或路由模板；命中就问你是否导入，没命中再新建。

用户只需要说：

- “查资产库”
- “把冷宫废妃模板导入为沈念”
- “把这个角色导出成模板”
- “把这套战袍导出成服装模板”
- “把这把剑导出成武器模板”
- “把这集路由沉淀成模板”

AI 内部再跑脚本。

## 核心规则

- **导入即 fork，溯源不断链**：跨项目默认不复用原角色 ID/name。必须生成新项目本地 `CHAR_...` 和新角色名，避免多剧撞脸撞身份。同时写入溯源：`source_asset_pack`/`source_asset_slug`（单层，兼容旧导入）+ 追加一条 `fork_history[]`（先继承源角色自带的链再追加，A→B→C 多级 fork 可回溯；字段键名以契约 `IDENTITY_FORK_HISTORY_ENTRY_FIELDS` 为准）。
- **后端原生 ID 默认重置 + 审计留痕**：Character ID / Face Lock / reference controls / LoRA ready 多数绑定账号、项目或训练数据。导入新剧默认改回 `unregistered` 或 `fallback_reference_group`，再由 `n2d-identity` 重新生成 adapter matrix；**被重置/被新模板移除的后端逐条记入 form 的 `preserve_review`**（原 status/mode/句柄/重置原因），导入者能看到"源项目曾在哪些后端注册过身份"，而不是被悄悄抹掉。若确需 `--preserve-adapters`，必须写 `--preserve-reason`；旧 registered/ready 只保留为 `candidate` 参考，不得直接当本项目可执行资产。
- **LoRA 重置/降级清失效路径（防指向旧项目）**：`.safetensors` 不随资产包迁移。重置/降级用 `pop` **彻底移除** lora 的 `model_path/model_hash/validation_report/train_job/card` 键（置空字符串仍是"残留字段"，schema 对账/diff 会把空串当已登记）并标 notes；`--preserve-adapters` 把 ready 降级为 `candidate` 时同样移除（只留 `base_model/trigger/dataset` 作重训参考），否则 gate 会读到指向旧项目的失效 model_path 误判文件存在。
- **资产包带授权字段**：默认 `template_only`。没有明确授权时，只复用模板结构，不复用“同一个可识别角色”。
- **多形态文件名必须去重**：角色有多个 form 时，引用图文件名写入 form 后缀，避免 `front/side/back` 等同名文件在导出或导入时互相覆盖。
- **路由模板只做参考**：新项目仍要按自己的 `storyboard.json` 跑 `n2d-model-router`，不能把旧剧逐 Clip 路由表直接覆盖过来。
- **先轻量后市场**：本 skill 先做本地 `资产库/` + CLI。等多部剧跑出真实复用频次，再做 UI、评分、排行。

## 常用命令

查看提示：

```bash
python3 skills/n2d-asset-market/scripts/market.py hint
```

列出资产库：

```bash
python3 skills/n2d-asset-market/scripts/market.py list
```

导出角色模板：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-character <作品根> --character-id CHAR_XXX --slug 冷宫废妃
```

导入角色模板到新剧：

```bash
python3 skills/n2d-asset-market/scripts/market.py import-character <作品根> 资产库/characters/冷宫废妃 --as-id CHAR_SHENNIAN --as-name 沈念
python3 skills/n2d-identity/scripts/identity.py <作品根> --write
```

导出 / 导入场景模板：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-scene <作品根> --asset-id LOC_XXX --slug 冷宫寝殿
python3 skills/n2d-asset-market/scripts/market.py import-scene <作品根> 资产库/scenes/冷宫寝殿 --as-id LOC_01 --as-name 冷宫寝殿
```

导出 / 导入道具模板：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-prop <作品根> --asset-id PROP_XXX --slug 赐死托盘
python3 skills/n2d-asset-market/scripts/market.py import-prop <作品根> 资产库/props/赐死托盘 --as-id PROP_01 --as-name 赐死托盘 --owner CHAR_LIU
```

导出 / 导入武器模板：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-weapon <作品根> --asset-id WEAPON_XXX --slug 霜纹长剑
python3 skills/n2d-asset-market/scripts/market.py import-weapon <作品根> 资产库/weapons/霜纹长剑 --as-id WEAPON_01 --as-name 霜纹长剑 --owner CHAR_SHEN
```

导出 / 导入独立服装模板：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-outfit <作品根> --asset-id OUTFIT_XXX --slug 玄青窄袖官袍
python3 skills/n2d-asset-market/scripts/market.py import-outfit <作品根> 资产库/outfits/玄青窄袖官袍 --as-id OUTFIT_01 --as-name 玄青窄袖官袍
```

导出 / 导入特效模板：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-vfx <作品根> --asset-id VFX_XXX --slug 青白剑气拖尾
python3 skills/n2d-asset-market/scripts/market.py import-vfx <作品根> 资产库/vfx/青白剑气拖尾 --as-id VFX_01 --as-name 青白剑气拖尾
```

导出视频模型路由经验：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-routes <作品根> 第1集 --slug 宫斗对峙路由
```

跨剧复用母题（系统面板等复现桥段·穿越/系统流）：

```bash
# 导出：母题定义 + 绑定的成长 VFX（VFX_系统面板 含 forms/lifecycle）+ 参考图
python3 skills/n2d-asset-market/scripts/market.py export-motif <作品根> --slug 系统面板
# 导入：合并进目标 motif_registry + asset_registry，progression 成长档重置（新剧从 Lv.1 起）
python3 skills/n2d-asset-market/scripts/market.py import-motif <作品根> 资产库/motifs/系统面板
```

跨剧复用招式/打斗套路（五帧拆招 + 动作编排 + 绑定 WEAPON_/VFX_）：

```bash
# 导出：一条 combat set（招式骨架 + 节奏 preset）+ 绑定的武器/特效定妆 + 参考图
python3 skills/n2d-asset-market/scripts/market.py export-combat <作品根> --combat-id COMBAT_万妖妖力近战 --slug 万妖妖力近战
# 导入：合并进目标 combat_registry + asset_registry；reskin 重置（清关键帧 PNG，须新剧重出）
python3 skills/n2d-asset-market/scripts/market.py import-combat <作品根> 资产库/combat/万妖妖力近战 --as-id COMBAT_雷霆近战
```

> 打斗 pack 只复用**结构**（五帧拆招 / 力链 / contact / 速度曲线 / 节奏 preset + 武器VFX定妆锁形），不复用"同一把可识别武器"或具体数值。导入后**每招关键帧 PNG 被清空、标 `needs_keyframe_regen`**：必须在新剧分镜按五帧拆招重织进 `故事板.md`、换皮（元素主色/武器剪影/角色）、重出起手/命中关键帧，再重跑 image/video gate。工艺总纲见 `n2d-script/references/打斗分镜.md`。

> 母题 pack 只复用**结构**（镜头模板 system_panel / 台词腔 / VFX 定妆锁色锁形 / overlay 文字层规格），不复用具体剧情数值；导入后 progression 重置，需在新剧分镜上跑 `motif_detector.py` 重新检测桥段、`--write` 绑定 Clip，再重跑 image/video gate。详见 `n2d-script/references/题材母题框架.md`。

> 简写包装（便于记忆，等价上面的显式子命令）：`export_pack.py <作品根> CHAR_XXX`（= `market.py export-character … --character-id`）、`import_pack.py <作品根> <资产包> --as-id … --as-name …`（= `market.py import-character …`）。两者只是 `runpy` 转发到 `market.py`，行为完全一致；脚本/文档优先用显式 `market.py` 子命令。

## 工作流

### 1. 开新剧 / 建角色卡前

1. 运行 `market.py list`。
2. 如果命中角色原型，向用户确认：“是否导入为本剧的新角色？”
3. 用户确认后运行 `import-character`，传新 `--as-id` / `--as-name`。
4. 运行 `n2d-identity --write`。
5. 再进入 `n2d-script` / `n2d-image` 的角色卡、定妆、出图流程。

### 2. 旧剧资产沉淀

1. 选择已经跑通、定妆稳定、授权清楚、确实值得跨剧复用的资产。
2. 按资产类型运行 `export-character` / `export-outfit` / `export-weapon` / `export-vfx` / `export-combat` 等命令。
3. 检查 `资产库/<type>/<slug>/asset_pack.json` 的 `license`、`style_tags`、`tags`。
4. 如果只是原型模板，保持 `license.reuse=template_only`；没有授权证据时不得把“同一个可识别角色/武器/服装”当成跨项目可执行资产复用。

### 3. 路由经验沉淀

1. 某集 `video_model_routes.json` 在审片后证明有效。
2. 运行 `export-routes`。
3. 新项目需要类似镜头时，先跑自己的 `n2d-model-router`，再用该模板对照调参。

## 文件结构

```text
资产库/
├── characters/<slug>/          # export-character / import-character 全链支持
│   ├── asset_pack.json
│   └── files/
├── scenes/<slug>/              # export-scene / import-scene：LOC_ 场景定妆 + constraints
├── props/<slug>/               # export-prop / import-prop：PROP_ 道具定妆 + lifecycle/structure
├── weapons/<slug>/             # export-weapon / import-weapon：WEAPON_ 武器/法宝实体 + weapon_profile
├── outfits/<slug>/             # export-outfit / import-outfit：OUTFIT_ 独立服装/套装 + outfit_profile
├── vfx/<slug>/                 # export-vfx / import-vfx：VFX_ 特效表现 + vfx_params/lifecycle
├── motifs/<slug>/              # export-motif / import-motif：母题定义 + 绑定成长 VFX（import 重置 progression）
├── combat/<slug>/              # export-combat / import-combat：招式五帧+动作编排+绑定 WEAPON_/VFX_（import reskin 清关键帧）
└── templates/model_routes/<slug>/
    └── asset_pack.json         # export-routes / import-routes
```

`characters/`、`scenes/`、`props/`、`weapons/`、`outfits/`、`vfx/` 与 `templates/model_routes/` 都有成对导出/导入命令。非角色资产导入会合并到目标项目 `出图/共享/asset_registry.json`，复制参考图到 `出图/共享/图片/`；导入后仍要在逐镜 prompt 的「资产引用注册层」绑定对应 `LOC_` / `PROP_` / `WEAPON_` / `OUTFIT_` / `VFX_`，并重跑 image/video gate。

若源项目已有 `设定库/character_assets/<CHAR_ID>__<slug>/manifest.json`，导出角色模板时优先读取其中的 reference/prompts/lora/voice/adapters/qc 缺口说明；导出的 `asset_pack.json` 仍要按跨项目 schema 写 fork_required 和 adapter 重置策略。

Schema 见 `references/schema.md`。

## 和其它 skill 的关系

- `n2d-script`：建角色/场景/关键道具/武器/独立服装/VFX 前先查资产库，命中则导入原型再改写本剧设定；设计含打斗的集前先查 `combat/`，命中则 import-combat 复用招式套路（按 `打斗分镜.md` 五帧拆招织进故事板）。
- `n2d-image`：新增共享定妆前先查资产库，命中则导入定妆组和 `identity_registry` / `asset_registry` fragment；核心/长线角色在项目内同步维护 `设定库/character_assets/` manifest。
- `n2d-identity`：导入角色后必须重建 adapter matrix。
- `n2d-model-router`：路由模板仅作对照，逐集路由仍由它生成。
- `n2d-dashboard`：后续可统计资产复用次数、节省重抽成本、模板成功率。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把旧剧 Character ID 直接复制到新剧 | 默认重置，重新注册 |
| 多部剧共用同一个具体脸 | 除非同 IP 且授权明确，否则只复用模板结构 |
| 导入后不跑 n2d-identity | 必跑，matrix 才是下游可执行视图 |
| 用旧剧 route table 覆盖新剧 | 只作参考，新剧按 storyboard 重新路由 |
| 把角色某一形态自带衣服全都导成 OUTFIT_ | 普通角色服装仍归 `identity_registry.forms[].wardrobe_profile`；只有跨角色/跨形态/跨集复用的独立服装才进 `OUTFIT_` |
| 武器只放 PROP_ 或只放 VFX_ | 实体剑/刀/法宝/飞行器物进 `WEAPON_`；VFX_ 只锁光效表现 |
