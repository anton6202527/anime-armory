# 场景卡（Scene Cards）

章节是交付单位，**场景才是打磨单位**。一个高质量章节通常由 1-5 个场景组成；每个场景必须有目标、阻碍、冲突、转折和价值变化，否则就容易变成信息播报、纯对白或注水过渡。

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
      "reveal_or_payoff": "揭示或兑现了什么",
      "subtext": "对白或动作底下真正争的东西",
      "sensory_anchor": "一个具体五感锚点"
    }
  ]
}
```

## 写作标准

- `desire` 必须具体，不能写“推动剧情”。
- `obstacle` 必须能造成阻力，不能只是背景。
- `turn` 必须改变局面：信息、权力、关系、目标、资源或危险至少一项变化。
- `value_shift` 写成“从 A 到 B”，例如“从安全感到被背叛”“从劣势到握住证据”。
- `subtext` 帮对白有戏：角色嘴上谈 A，底下争 B。
- `sensory_anchor` 防止场景漂浮：声音、气味、温度、材质、空间位置至少一个。

## 用法

章纲定稿后、写 Demo 或批量写章前：

```bash
python3 skills/novel-craft/scripts/scene_cards.py scaffold "<作品根>" --range 1-5
python3 skills/novel-craft/scripts/scene_cards.py check "<作品根>"
```

`draft_packets.py` 会读取当前章节的场景卡并注入任务包。缺字段的场景卡会被 QA gate 标记，结构级问题先回章纲或 scene cards，不要直接润色正文。

## 反模式

| 错误 | 纠正 |
|---|---|
| 场景卡写成剧情摘要 | 写 POV 当场想要什么、被什么阻碍、场末怎样变了 |
| 每场只有事件没有转折 | 补 `turn` 和 `value_shift`；没有变化就合并或删除 |
| 对白场没有潜台词 | 写清 `subtext`，再回 `dialogue.md` 精修对白 |
