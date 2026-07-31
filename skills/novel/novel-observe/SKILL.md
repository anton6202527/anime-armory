---
name: novel-observe
description: Living-material and field-observation layer for novel projects. Use when a novel needs richer lived detail, human behavior, interview notes, workplace/local texture, sensory anchors, or a reusable material bank before drafting or revision. Produces 素材/观察札记.jsonl and 素材/观察素材库.md; draft/edit workflows can select entries by tag/domain/dramatic use. Does not write prose and does not replace novel-research fact evidence. Triggers 生活观察, 素材库, 采访纪要, 田野笔记, 人物行为, 生活感, 烟火气, 现实质感, 场景素材, 五感素材, observation bank, field notes, lived detail.
---

# novel-observe — 生活观察与素材库

本 skill 补的是“作家的眼睛和耳朵”：把生活观察、采访纪要、职业场景、人物小动作、方言口吻、空间气味和真实尴尬感沉淀成可检索素材。它不写正文，也不替代 `novel-research` 的事实证据层；研究包回答“事实是否正确”，观察库回答“读起来像不像活人活事”。

产物落在作品根：

- `素材/观察札记.jsonl`：结构化素材条目。
- `素材/观察素材库.md`：给人读的索引。
- `写作任务/观察素材_第NN章.md`：按章节筛选出的可注入写章素材包。

## 何时使用

- 新书立项前，需要把“题材想法”变成有生活质感的场景、人物和物件。
- `novel-review` / `novel-edit` 发现人物悬浮、对白像信息播报、场景没烟火气、职业文只有资料没有人味。
- 写医疗、法律、金融、学校、职场、县城、餐饮、物流等现实场景：先跑 `novel-research` 核事实，再用本 skill 补生活观察。
- 用户提供采访、聊天记录、游记、工作笔记、图片描述或零散素材，希望纳入项目素材库。

## 工作流

1. 初始化素材库：

```bash
python3 skills/novel/novel-observe/scripts/observe.py scaffold "<作品根>"
```

2. 添加观察条目：

```bash
python3 skills/novel/novel-observe/scripts/observe.py add "<作品根>" \
  --source observation \
  --domain "县城医院" \
  --text "候诊区叫号屏坏了一半，护士靠喊名字维持秩序。" \
  --sensory "消毒水味、塑料椅发黏、雨伞滴水声" \
  --behavior "家属嘴上说不急，手一直捏缴费单" \
  --dramatic-use "pressure,character_detail,setting" \
  --tags "医院,等待,焦虑"
```

3. 检查素材是否可用：

```bash
python3 skills/novel/novel-observe/scripts/observe.py check "<作品根>"
```

4. 为写章/编辑选素材：

```bash
python3 skills/novel/novel-observe/scripts/observe.py select "<作品根>" \
  --tag 医院 --dramatic-use pressure --limit 5
```

需要稳定落文件时：

```bash
python3 skills/novel/novel-observe/scripts/observe.py select "<作品根>" \
  --tag 医院 --dramatic-use pressure --limit 5 --chapter 3 --write-packet
```

产物写到 `写作任务/观察素材_第03章.md`。`draft_packets.py` 暂不自动生成观察，素材选择由 agent/作者按章节需要决定；落文件后可把该文件作为章节任务包的补充必读材料。

## 条目标准

每条观察至少要能回答三件事：

- **具体细节**：看见、听见、闻到、摸到的是什么，不能只写“很真实”。
- **人的反应**：人在压力、欲望、羞耻、权力差、等待或误解中怎么动作。
- **戏剧用途**：这条素材能服务什么：冲突、人物、场景、潜台词、节奏、隐喻或职业质感。

## 与其它 skill 的边界

- `novel-research`：事实、法规、流程、专业细节证据；本 skill 是生活材料。
- `novel-create`：立项和蓝图；本 skill 给蓝图提供素材燃料。
- `novel-craft`：写章任务包、场景卡；本 skill 给场景卡补 sensory anchor 和 behavior detail。
- `novel-edit`：如果编辑计划指出“人物悬浮/场景薄”，先补本素材库，再改文。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把事实资料当生活素材 | 事实进 `novel-research`；观察条目必须有人的行为和可感细节 |
| 只写抽象结论 | 改成具体物、动作、声音、气味、空间关系 |
| 采集隐私信息 | 真实人物默认匿名化；不记录身份证号、电话、住址等敏感信息 |
| 素材不标用途 | 每条都写 `dramatic_use`，否则写章时很难调用 |
