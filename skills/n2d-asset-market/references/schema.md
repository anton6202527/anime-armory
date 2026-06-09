# n2d 跨项目资产包 schema

资产包是一个本地目录，核心文件为 `asset_pack.json`。默认库根：

```text
资产库/
├── characters/<slug>/asset_pack.json
├── scenes/<slug>/asset_pack.json
├── props/<slug>/asset_pack.json
└── templates/model_routes/<slug>/asset_pack.json
```

## 通用字段

```json
{
  "kind": "n2d_cross_project_asset_pack",
  "version": 1,
  "asset_type": "character",
  "slug": "冷宫废妃",
  "title": "冷宫废妃",
  "source_project": "制漫剧/旧剧",
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

## character pack

角色包包含一个 `identity_registry.json` 片段和 `files/` 下的定妆 PNG。

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

## route_template pack

路由模板包保存某集 `video_model_routes.json` 的经验。

它只作参考，不直接覆盖新项目逐 Clip 路由。新剧仍需读自己的 `storyboard.json` 运行 `n2d-model-router`，再用模板对照“同类镜头当时为什么这样路由”。
