# n2d 跨项目资产包 schema

资产包是一个本地目录，核心文件为 `asset_pack.json`。默认库根：

```text
资产库/
├── characters/<slug>/asset_pack.json
├── scenes/<slug>/asset_pack.json
├── props/<slug>/asset_pack.json
├── weapons/<slug>/asset_pack.json
├── outfits/<slug>/asset_pack.json
├── vfx/<slug>/asset_pack.json
├── motifs/<slug>/asset_pack.json
├── combat/<slug>/asset_pack.json
└── templates/model_routes/<slug>/asset_pack.json
```

注意：这份 schema 描述的是**跨项目模板市场包**。项目内长线角色资产包使用 `设定库/character_assets/<CHAR_ID>__<slug>/manifest.json`，用于同一部剧内归拢 reference / prompts / lora / voice / adapters / qc；它可以作为导出来源，但不是 `asset_pack.json`，也不能替代 `identity_registry.json`。

## 通用字段

```json
{
  "kind": "n2d_cross_project_asset_pack",
  "version": 1,
  "asset_type": "character",
  "slug": "冷宫废妃",
  "title": "冷宫废妃",
  "source_project": "创作区/制漫剧/旧剧",
  "exported_at": "2026-06-08T00:00:00Z",
  "license": {
    "status": "user_owned_or_synthetic",
    "reuse": "template_only",
    "notes": ""
  },
  "style_tags": ["古风", "宫廷", "写实漫剧"],
  "tags": ["女主", "冷宫", "复仇"]
}
```

`license.reuse`：

- `template_only`：只能复用结构、锚点句、prompt 套路；导入新剧必须 fork 新身份。
- `same_ip`：同一 IP / 同一宇宙可复用原角色。
- `licensed_reuse`：有授权证据，可跨项目复用。

`asset_type`：

- `character`：角色原型，导入即 fork 新身份。
- `scene` / `prop` / `weapon` / `outfit` / `vfx`：非角色资产，导入合并到 `asset_registry.json`。
- `motif`：题材母题/复现桥段，导入重置 progression。
- `combat`：招式/打斗套路，导入 reskin 清关键帧。
- `route_template`：视频模型路由经验，只作参考。

## character pack

角色包包含一个 `identity_registry.json` 片段和 `files/` 下的定妆 PNG。若源项目有 `设定库/character_assets/.../manifest.json`，导出时可把其中的 lora/voice/adapters/qc 缺口说明写入 `notes` 或扩展字段，但跨项目导入仍按 fork 处理。

关键字段：

- `character_template.original_character`：来源角色 ID/name。
- `character_template.fork_required=true`：导入新剧时默认必须 fork。
- `registry_fragment.characters[]`：可并入新项目 `出图/共享/identity_registry.json` 的角色片段。
- `files[]`：导出的定妆文件、role、sha256。

导入默认行为：

- 新项目必须传 `--as-id` / `--as-name`。
- 定妆 PNG 复制到新项目 `出图/共享/图片/定妆_<新角色>.png` 等路径。
- 原 Character ID / Face Lock / reference controls / LoRA ready 状态默认重置，避免跨项目假登记。
- 导入后必须跑 `n2d-identity` 生成 adapter matrix。

## non-character asset pack（场景/道具/武器/服装/VFX）

通用非角色资产包来源于项目内 `出图/共享/asset_registry.json`，保存一条可复用资产及其 `reference_group` 文件：

```json
{
  "kind": "n2d_cross_project_asset_pack",
  "version": 1,
  "asset_type": "weapon",
  "slug": "霜纹长剑",
  "title": "霜纹长剑",
  "asset_registry_fragment": {
    "kind": "n2d_asset_reference_registry",
    "version": 1,
    "assets": [
      {
        "id": "WEAPON_01",
        "type": "weapon",
        "name": "霜纹长剑",
        "reference_group": {"primary": "files/霜纹长剑.png"},
        "weapon_profile": {"silhouette": "窄长直剑，短护手，一手半握柄"},
        "constraints": {"structure": "一柄一刃，窄长直剑"},
        "drift_forbidden": ["blade_shape", "palette"]
      }
    ]
  },
  "files": [{"role": "primary", "path": "files/霜纹长剑.png", "exists": true}]
}
```

命令与目录：

| asset_type | CLI | 目录 | ID 前缀 | registry type 别名 |
|---|---|---|---|---|
| `scene` | `export-scene` / `import-scene` | `资产库/scenes` | `LOC_` | `scene` / `location` |
| `prop` | `export-prop` / `import-prop` | `资产库/props` | `PROP_` | `prop` |
| `weapon` | `export-weapon` / `import-weapon` | `资产库/weapons` | `WEAPON_` | `weapon` / `magic_weapon` / `equipment` / `armory` |
| `outfit` | `export-outfit` / `import-outfit` | `资产库/outfits` | `OUTFIT_` | `outfit` / `costume` |
| `vfx` | `export-vfx` / `import-vfx` | `资产库/vfx` | `VFX_` | `vfx` / `effect` |

导入默认行为：

- 必须传 `--as-id` / `--as-name`，按新项目命名合并，避免 ID 冲突。
- 参考图复制到目标项目 `出图/共享/图片/定妆_<新资产名>*.png`。
- 写入 `source_asset_pack` / `source_asset_slug` 溯源。
- `--owner` 可覆盖道具或武器所属角色；服装/VFX 通常通过逐镜 prompt 绑定到穿戴角色或使用场景。
- 导入后必须在逐镜 prompt 的「资产引用注册层」显式引用对应 `LOC_` / `PROP_` / `WEAPON_` / `OUTFIT_` / `VFX_`，再重跑 image/video gate。

约束口径：

- `weapon` 必须保留 `weapon_profile`，锁剪影、比例、材质、纹样、战斗用法和禁漂项；实体武器/法宝不要只放 VFX。
- `outfit` 必须保留 `outfit_profile`，锁剪影、层次、领袖腰摆、材质、纹样、色卡和适配体型；普通角色形态服装仍归 `identity_registry.forms[].wardrobe_profile`，不滥建 `OUTFIT_`。
- `vfx` 建议保留 `vfx_params` 和结构化 `lifecycle`，系统面板/技能拖尾等可沉淀为模板；具体数值和文字仍应在新剧 compose/overlay 层重建。

## combat pack（招式/打斗套路）

打斗包把**一整套打斗套路**沉淀成可跨剧复用的结构包。真值源是项目内 `出图/共享/combat_registry.json`（kind `n2d_combat_registry`）：

```json
{
  "kind": "n2d_combat_registry",
  "version": 1,
  "combat_sets": [
    {
      "combat_id": "COMBAT_万妖妖力近战",
      "name": "万妖妖力近战",
      "element_skin": "暗金妖力",
      "rhythm_preset": { "speed_curve": "蓄力慢→出招快→命中顿→收势留白", "hit_stop_frames": 4 },
      "bound_weapons": ["WEAPON_01"],
      "bound_vfx": ["VFX_02", "VFX_03", "VFX_04"],
      "moves": [
        {
          "move_id": "SM_01", "name": "噬腕·夺刃", "type": "命中类",
          "five_frame_template": ["起手", "发力", "命中", "受击", "收势"],
          "action_choreography": { "attack_path": "...", "impact_frame": "...", "contact_points": ["..."], "force_direction": "...", "recovery_beat": "..." },
          "keyframe_refs": { "起手": "出图/第N集/图片/...png", "命中": "..." }
        }
      ]
    }
  ]
}
```

`export-combat`：导出一条 combat set + 它绑定的 `WEAPON_`/`VFX_`（从 `asset_registry.json` 抽出，参考图拷进 `files/`）。

`import-combat` 默认行为（**reskin 重置**，与角色重置 Character ID / 母题重置 progression 同构）：

- combat set 合并进新剧 `combat_registry.json`（去重 `combat_id`，可 `--as-id` 改名）；写 `source_combat_pack`/`source_combat_slug` 溯源。
- **每招 `keyframe_refs` 被清空、标 `needs_keyframe_regen=true`**：关键帧 PNG 是项目专属可执行产物，不迁移，必须在新剧重出起手/命中关键帧、重过 image/video gate。被清掉的路径写进 `资产库导入记录.md`。
- 保留 `five_frame_template` / `action_choreography` / `rhythm_preset` 骨架——这正是"稍加改动就能复用"的结构。
- 绑定 `WEAPON_`/`VFX_` 合并进新剧 `asset_registry.json`、参考图复制到 `出图/共享/图片/`；**换皮**（元素主色/武器剪影/角色）在新剧重出图时落地，定妆锁形作起点模板。

## route_template pack

路由模板包保存某集 `video_model_routes.json` 的经验。

它只作参考，不直接覆盖新项目逐 Clip 路由。新剧仍需读自己的 `storyboard.json` 运行 `n2d-model-router`，再用模板对照“同类镜头当时为什么这样路由”。
