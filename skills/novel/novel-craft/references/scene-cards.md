# 场景卡（Scene Cards）

章节是交付单位，**场景才是打磨单位**。一个高质量章节通常由 1-5 个场景组成；每个场景必须有目标、阻碍、冲突、转折和价值变化，否则就容易变成信息播报、纯对白或注水过渡。

2026 强化版场景卡同时承载“人物引擎”：人物嘴上要什么、真正缺什么、误信什么、怕什么、用什么策略、越过哪条底线要付出什么代价。这样场景不是事件推事件，而是人物用自己的缺陷和欲望把局面推坏或推开。

路径：

```text
设定/scene_cards.json
```

## 最小字段

```json
{
  "schema_version": 1,
  "kind": "novel_scene_cards",
  "scenes": [
    {
      "id": "SC001-01",
      "chapter": 1,
      "scene_no": 1,
      "pov": "主角名",
      "location": "地点",
      "time": "时间",
      "desire": "本场景里 POV 想要什么",
      "obstacle": "谁/什么阻止他",
      "conflict": "场面上的冲突",
      "turn": "场景末发生的不可逆转折",
      "value_shift": "情绪/关系/权力/信息从什么变成什么",
      "outcome": "场景结局极性：yes / yes-but / no-and / no-but（可留空）",
      "plotline": "本场所属情节线自由标签：主线/某支线名（可留空）",
      "turn_source": "转折能动性来源：主角行动 / 对手行动 / 盟友援手 / 伏笔兑现 / 巧合（可留空）",
      "reveal_or_payoff": "揭示或兑现了什么",
      "subtext": "对白或动作底下真正争的东西",
      "sensory_anchor": "一个具体五感锚点",
      "want": "角色表层想要什么（可与 desire 相同，但要更口语/当下）",
      "need": "角色真正需要面对/学会/承认什么",
      "misbelief": "角色此刻相信但可能是错的东西",
      "wound": "这个误信来自哪个旧伤/经历",
      "fear": "如果失败，角色最怕暴露或失去什么",
      "tactic": "角色本场用什么策略争取目标：讨好/威胁/回避/试探/交换/牺牲",
      "moral_boundary": "角色不愿越过的底线；若越过，必须造成后果",
      "choice_cost": "场末选择带来的代价"
    }
  ]
}
```

## 写作标准

- `desire` 必须具体，不能写“推动剧情”。
- `obstacle` 必须能造成阻力，不能只是背景。
- `turn` 必须改变局面：信息、权力、关系、目标、资源或危险至少一项变化。
- `value_shift` 写成“从 A 到 B”，例如“从安全感到被背叛”“从劣势到握住证据”。
- `outcome` 是 try-fail 循环纪律（Swain/Sanderson）：`yes`=干净达成、`yes-but`=达成但付代价、`no-and`=失败且恶化、`no-but`=失败但有转机。中段应以 `yes-but`/`no-and` 为主；连续 `yes` 会被 `manuscript_map` 的 `OUTCOME-YES-RUN` 提示（无阻力连胜=张力自由落体）。
- `plotline` 标注本场所属情节线；同一线连续过长会被 `PLOTLINE-LONG-RUN` 提示（金圣叹"横云断山"：文长无断则累坠，插间笔再续）。
- `turn_source` 是巧合纪律（Pixar 第 19 条）：**巧合可以把人物推进麻烦，不可以把人物捞出麻烦**。`巧合`+有利 outcome 会被 `TURN-COINCIDENCE-RESCUE` 提示——改成主角行动/付代价换来，或补一笔伏笔升级成 `伏笔兑现`；`巧合`+失败结局完全合法（天降横祸是好戏）。
- `subtext` 帮对白有戏：角色嘴上谈 A，底下争 B。
- `sensory_anchor` 防止场景漂浮：声音、气味、温度、材质、空间位置至少一个。
- `want/need/misbelief/wound/fear/tactic/moral_boundary/choice_cost` 构成人物引擎。缺这些字段不一定阻断写作，但会让人物容易变成剧情工具人。
- 每场必须有一个**有代价的选择**。如果角色没有选择，只是被剧情推着走，先回 scene card 补 `tactic` 和 `choice_cost`。

## 用法

章纲定稿后、写 Demo 或批量写章前：

```bash
python3 skills/novel/novel-craft/scripts/scene_cards.py scaffold "<作品根>" --range 1-5
python3 skills/novel/novel-craft/scripts/scene_cards.py check "<作品根>"
```

`draft_packets.py` 会读取当前章节的场景卡并注入任务包。缺字段的场景卡会被 QA gate 标记，结构级问题先回章纲或 scene cards，不要直接润色正文。

## 反模式

| 错误 | 纠正 |
|---|---|
| 场景卡写成剧情摘要 | 写 POV 当场想要什么、被什么阻碍、场末怎样变了 |
| 每场只有事件没有转折 | 补 `turn` 和 `value_shift`；没有变化就合并或删除 |
| 对白场没有潜台词 | 写清 `subtext`，再回 `dialogue.md` 精修对白 |
| 人物只完成剧情任务 | 补 `want/need/fear/tactic/choice_cost`，让动作来自人物内驱 |
