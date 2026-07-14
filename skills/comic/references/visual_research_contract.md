# 历史/公版名著视觉研究合同

`comic` 对历史题材、公版名著和存在多个影视版本的改编项目，在首张文字定妆之前用 `设定库/visual_research.json` 保存机器真值。它只记录来源 URL、研究发现和派生设计决策；脚本不访问网络、不下载图片，也不把影视截图变成生图附件。

## 执行

```bash
python3 skills/comic/scripts/visual_research_contract.py "创作区/画漫画/作品名" scaffold --write
python3 skills/comic/scripts/visual_research_contract.py "创作区/画漫画/作品名" check --strict --json
```

`scaffold --write` 只补缺失合同，永不覆盖已有研究。它会尝试从 `_设置.md` 读取 `STYLE_...` 风格锚；也可显式传 `--style-anchor-id STYLE_EXAMPLE`。`status=complete` 只表示合同内容完整，不等于人工风格锚、角色定妆或多视图批准。

## 最小验收

- `project_style_anchor_id` 是稳定 `STYLE_...` ID，不是模糊画风句子或某在世画师/IP 名称。
- `sources[]` 至少有 1 项 `film_tv_narrative` 官方/版权方影视叙事参考，以及 2 个不同 URL 的 `museum_primary | institution_primary | archive_primary` 一手参考。
- 每项来源记录 `source_id / title / url / provider / accessed_at / type / usage_boundary / findings`，`usage_boundary` 固定为 `research_only`。
- `derived_style.summary` 归纳本项目风格，`decisions[]` 至少三项，且用 `evidence_source_ids[]` 追溯到实际来源。可用维度是 `character / costume_class / environment / props / palette / composition / lighting / material_finish / narrative_coverage`。
- `rights_rules` 显式为 research-only：禁止演员肖像直接锚定，禁止剧照作为生图参考，禁止复制具体构图/镜头/整套服饰组合，生产中只使用已授权或可开放使用的资产。
- 合同内不得出现 `local_path / image_path / attachment_path / download_path / reference_image`；可视化审阅图和真实生图附件属于后续资产与权利流程，不由研究合同偷渡。

## 设计边界

影视参考用于识别叙事覆盖、阶层可读性、场面调度和观众已有视觉预期；博物馆/机构一手参考用于服制、道具、建筑、地貌、色彩和空间语法。最终 `derived_style` 必须是独立的项目设计决策，不是“照某剧/某演员/某幅画生成”。
