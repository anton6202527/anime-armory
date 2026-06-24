# 弧段记忆（Arc Memory）

长篇写到几十章后，固定“前 3 章窗口 + 状态账本”仍不够。`retrieval.py` 能召回旧章片段，但还需要一层**弧段级摘要**，把一组章节的剧情进展、情绪推进、人物变化和未收钩子压缩成稳定记忆。

路径：

```text
设定/arc_summaries.json
设定/emotional_progression.json
```

## arc_summaries.json

```json
{
  "schema_version": 1,
  "kind": "novel_arc_summaries",
  "arcs": [
    {
      "id": "ARC-001",
      "range": "1-5",
      "title": "初入局",
      "plot_summary": "这 5 章发生了什么",
      "character_changes": ["主角从被动求生到主动设局"],
      "open_threads": ["谁泄露了密信"],
      "payoffs": ["第3章的羞辱在第5章完成第一次反击"],
      "carry_forward": ["下一弧必须继续追查密信来源"]
    }
  ]
}
```

## emotional_progression.json

```json
{
  "schema_version": 1,
  "kind": "novel_emotional_progression",
  "chapters": [
    {
      "chapter": 5,
      "dominant_emotion": "压抑后的反击爽感",
      "tension_score": 8,
      "reader_promise_progress": "第一次兑现打脸承诺",
      "next_emotional_debt": "反击带来的代价尚未出现"
    }
  ]
}
```

## 用法

每 3-5 章或每个自然 arc 写完后：

```bash
python3 skills/novel-craft/scripts/arc_memory.py scaffold "<作品根>" --arc 1-5 --title "初入局"
```

脚本只建骨架和截取证据片段；`plot_summary`、人物变化、情绪债务等字段由 AI/人工读该窗口后补全。`draft_packets.py` 会把当前章命中的 arc 摘要注入写章包，和 BM25 历史回溯互补。
