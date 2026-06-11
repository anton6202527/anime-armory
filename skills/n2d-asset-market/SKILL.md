---
name: n2d-asset-market
description: 跨项目 n2d 资产库/模板市场：把角色原型、identity_registry 片段、定妆组、视频模型路由经验导出成可复用 asset pack，并导入新剧时 fork 新身份、重置后端 Character ID/Face Lock/LoRA 状态。Use when asked about 跨项目角色库, 模板市场, 资产库, 复用定妆, 复用角色, 导入角色模板, 导出角色模板, identity_registry 复用, 路由模板, 成本摊薄.
---

# n2d-asset-market — 跨项目资产库 / 模板市场

你是 **n2d 跨项目资产管理员**。目标不是把旧剧角色原样搬到新剧，而是把“可复用的原型、定妆结构、registry 片段、路由经验”做成本地资产包，降低每部剧从零建库的成本。

## 触发

- 用户说：跨项目角色库、模板市场、资产库、复用定妆、复用角色、导入角色模板、导出角色模板、identity_registry 复用、路由模板、摊薄成本。
- 开新剧、建角色卡、出图新增角色/场景/道具之前。
- `n2d-image` 将要新增共享定妆项，但项目里没有命中。
- 某类镜头的视频路由反复成功或失败，值得沉淀成模板。

## 给用户的提示方式

**不要让用户背 CLI。** 遇到上述触发点，AI 先用人话提示：

> 我会先查跨项目资产库，看有没有可复用的角色原型、场景定妆或路由模板；命中就问你是否导入，没命中再新建。

用户只需要说：

- “查资产库”
- “把冷宫废妃模板导入为沈念”
- “把这个角色导出成模板”
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

导出视频模型路由经验：

```bash
python3 skills/n2d-asset-market/scripts/market.py export-routes <作品根> 第1集 --slug 宫斗对峙路由
```

> 简写包装（便于记忆，等价上面的显式子命令）：`export_pack.py <作品根> CHAR_XXX`（= `market.py export-character … --character-id`）、`import_pack.py <作品根> <资产包> --as-id … --as-name …`（= `market.py import-character …`）。两者只是 `runpy` 转发到 `market.py`，行为完全一致；脚本/文档优先用显式 `market.py` 子命令。

## 工作流

### 1. 开新剧 / 建角色卡前

1. 运行 `market.py list`。
2. 如果命中角色原型，向用户确认：“是否导入为本剧的新角色？”
3. 用户确认后运行 `import-character`，传新 `--as-id` / `--as-name`。
4. 运行 `n2d-identity --write`。
5. 再进入 `n2d-script` / `n2d-image` 的角色卡、定妆、出图流程。

### 2. 旧剧资产沉淀

1. 选择已经跑通、定妆稳定、授权清楚的角色。
2. 运行 `export-character`。
3. 检查 `资产库/characters/<slug>/asset_pack.json` 的 `license`、`style_tags`、`tags`。
4. 如果只是原型模板，保持 `license.reuse=template_only`。

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
├── scenes/<slug>/              # ⚠️ 预留结构：list 会扫，但暂无 export/import-scene 命令（手建可被 list 识别）
├── props/<slug>/               # ⚠️ 预留结构：同上，暂无 export/import-prop 命令
└── templates/model_routes/<slug>/
    └── asset_pack.json         # export-routes / import-routes
```

> 当前只有 `characters/` 与 `templates/model_routes/` 有成对的导出/导入命令；`scenes/`/`props/` 是为后续扩展预留的目录约定，尚未实现专用命令，先按需手建（`pack_dir` 已能按 `asset_type` 落到对应子目录）。

Schema 见 `references/schema.md`。

## 和其它 skill 的关系

- `n2d-script`：建角色卡前先查资产库，命中则导入原型再改写本剧设定。
- `n2d-image`：新增共享定妆前先查资产库，命中则导入定妆组和 registry fragment。
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
