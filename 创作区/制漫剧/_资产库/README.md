# 制漫剧系列资产库

本目录只服务 `制漫剧` 生产线，用于本系列不同作品之间复用资产。它不是仓库根公共层，也不能成为其它生产线的运行时依赖。

推荐结构：

- `characters/<slug>/asset_pack.json`
- `scenes/<slug>/asset_pack.json`
- `props|weapons|outfits|vfx/<slug>/asset_pack.json`
- `motifs|combat/<slug>/asset_pack.json`
- `templates/model_routes/<slug>/asset_pack.json`

每个包必须自包含：清单、权利/复用范围、注册表片段及所有被引用文件都在包目录内，且 `portability.requires_source_library=false`。跨系列、跨仓库或跨机器时，只交付所需的单个包；目标系列复制/分叉后自行适配，不得回指本目录。

作品根 `角色库/` 是本作品的角色生产包；稳定且值得跨作品复用的角色、场景、道具等再显式导出到这里。`设定库/` 继续保存作品的语义真值与角色圣经，不被本目录替代。
