# n2d Genre Packs

Genre pack 是题材层契约，不是核心状态机。核心 n2d 只读取这些 JSON 来补充：

- 典型高风险场景
- 分镜/视频动作契约字段
- 出图/出视频 QC 重点
- 风格绑定建议与降级方案

`_设置.md` 仍只需一个 `题材` 字段，兼容 `仙侠` 这类单题材值，也支持
`系统流+修仙+悬疑` / `自定义（系统流、修仙、悬疑）` 这类复合值。路由只匹配
pack 的 `genre_key`、`label` 或显式 `aliases`，不做近义词猜测；例如当前没有
`志怪` pack 或 alias 时，`志怪` 单独出现不会被擅自映射，`志怪悬疑` 则只因
显式包含 `悬疑` 而命中 `suspense`。

组合优先级固定为：题材原值中首次出现位置 → 同位置较长匹配词 → pack 路径 / key
稳定序。旧消费者继续读取 `genre.genre_key`（优先级第一项）；新消费者读取
`genre.matched_genre_keys`。组合后的动作字段、QC、降级方案按优先级稳定去重；同一
`scene_archetypes[].id` 合并字段和来源 pack。`activation.state` 区分
`genre_unmatched`、`storyboard_missing/empty/invalid`、`no_scene_archetype_triggered`
与 `scene_archetypes_triggered`，所以 `active_scenes=0` 不再混淆“未匹配”和“尚未触发”。

新增题材时复制一个 pack，保持 `kind=n2d_genre_pack`、`version=1`，再跑：

```bash
python3 skills/n2d/scripts/genre_packs.py validate --all
```
