# split_plan 存储、迁移与回退

## 为什么改为 v3

`split_plan.json` v2 为每个规范化段落重复保存对象键、source-unit ID、字符区间、逐段 SHA、正文预览和 signals，随后又把有 signals 的段落复制进 `arc_anchors`。长篇的正文已经存在于作品根 `小说/*.txt`，这些字段都可由「源快照 + 规范化规则 + unit index」确定性派生；重复内嵌会同时放大磁盘体积和 `json.load` 峰值内存。

v3 默认把 `source_units` 写成 `normalized_source_reference_v1`：

- 保留 unit 总数、规范化全文 SHA、字符数和 ID 格式；
- 只保存稀疏的 `[unit_index, signal_bitmask]`；
- 不再逐段内嵌正文 preview 和 SHA；
- `arc_anchors` 只保存开发包人工锚，源 signals 由 compact axis 按需派生；
- `episodes`、source-unit span、boundary candidates、beam paths、materialized 状态不变。

这不是删减结构事实。调用方需要旧 v2 单元对象时，用：

```python
units = list(split_novel.iter_source_units(plan, normalized_source_paras))
anchors = list(split_novel.iter_arc_anchors(plan, normalized_source_paras))
count = split_novel.source_unit_count(plan)
```

这些 helper 同时接受既有 verbose v2 与 compact v3；v3 派生前会核对段落数和规范化全文 SHA，源不一致时拒绝伪造映射。

## 迁移既有作品

`split_plan.json`、`_拆集机器索引.md` 是机器产物；`脚本/第N集/raw.txt`、`_拆集复核.md`、`_进度.md` 是保留项。优先做**原位存储迁移**，不重新计算拆集、候选边界或 beam，也不需要 git/VCS：

```bash
python3 skills/n2d/n2d-script/scripts/split_novel.py \
  "<作品根>/小说/<剧名>.txt" \
  --out "<作品根>" \
  --compact-existing-plan
```

命令会逐段核对旧 v2 的 ID、offset、字符数、SHA、preview 与 signals；再验证 source-signal anchors 镜像完整，只有全部通过才原子替换计划。旧 v2 会压缩保存在 `生产数据/迁移收据/split_plan.v2.<sha>.json.gz`，同目录落机器可读迁移收据。收据绑定迁移前后 plan SHA/体积、生产语义 SHA、rehydrate 结果，以及每个 raw、`_拆集复核.md`、`_进度.md` 的 SHA 与 mtime；任一保留项变化会自动恢复 v2 计划和旧机器索引。

这是从 verbose v2 读取并迁移的一次性操作，旧计划仍会被完整加载一次；迁移后的日常读取才获得 v3 的低内存收益。若旧计划已损坏、源快照漂移或不是 v2，命令 fail-closed，不猜测重建。

迁移后先核对：

- `schema_version == 3`；
- `source_units_storage == normalized_source_reference_v1`；
- `source_unit_count(plan)` 与迁移前一致；
- 已 materialize 的 raw SHA 未变化；
- `_拆集复核.md`、`_进度.md` 及逐个 raw 的收据指纹未变化；
- 收据 `production_semantics_unchanged == true`、`rehydrated_v2_units_equal == true`。

确认无误后仍保留 gzip 备份到一个完整生产周期结束；它通常远小于未压缩 v2，不应把 46MB 级副本长期平铺在项目根。

## 回退 verbose v2

若某个外部消费者尚未接入兼容 helper，可用同一命令加 `--legacy-plan-v2` 回退：

```bash
python3 skills/n2d/n2d-script/scripts/split_novel.py \
  "<作品根>/小说/<剧名>.txt" \
  --out "<作品根>" \
  --by-chapter \
  --limit 10 \
  --legacy-plan-v2
```

回退只改变机器计划存储，不授权覆盖人工脚本、人工拆集复核或已生产媒体。外部工具不得直接假定 `source_units` 永远是 list；应统一通过上述 helper 读取。

## 实施人工批准的拆集窗口

人工批准跨越多个机器集的 source-unit 映射后，用 `scripts/apply_split_mapping.py` 实施，不要手工同步多个文件。映射 JSON 顶层为：

```json
{
  "schema_version": 1,
  "kind": "n2d_approved_split_mapping",
  "approval": {"reviewer": "user:owner", "roles": ["director", "producer"], "approved_at": "带时区时间"},
  "window": {"start_episode": 1, "end_episode": 10, "start_source_unit_id": "U000001", "end_source_unit_id": "U002458", "next_source_unit_id": "U002459"},
  "episodes": [
    {"episode": 1, "start_source_unit_id": "U000001", "end_source_unit_id": "U000342", "source_chapters": "1–2", "core_scene": "…", "end_hook": "…"}
  ]
}
```

窗口必须逐集连续、无空洞、无重叠；`next_source_unit_id` 必须紧接末单元。工具只覆盖 `_进度.md` 显示 raw 已完成且所有下游列仍为空/不适用的集，并要求被吸收的旧机器集和待平移后缀都未 materialized。成功后在 `生产数据/边界收据/` 保存覆盖前 tar.gz、实施收据和每个受影响文件的新旧 SHA；plan 的 `human_approved_windows` 指回该收据。若任一写入失败，工具按内存快照恢复全部被触碰文件。

要精确恢复迁移前的同一份计划，优先使用收据绑定的 gzip 备份，解压后 SHA 必须等于收据 `rollback.expected_restored_sha256`；`--legacy-plan-v2` 是从当前源重新生成 verbose v2 的兼容回退，不等同于逐字节恢复历史计划。
