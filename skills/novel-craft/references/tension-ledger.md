# Tension & Curiosity Ledger (张力与悬念账本)

一致性追踪不应只停留在"客观事实"（死活、位置），更要追踪**情绪 ROI（投资回报率）**。
`tension_ledger.json` 用于确保故事不会连续平淡，且给读者的承诺均被兑现。

## Ledger Schema

```json
{
  "unresolved_hooks": [
    {
      "id": "hook_001",
      "question": "是谁在王敦的药里下了毒？",
      "introduced_in_chapter": 3,
      "urgency": "high"
    }
  ],
  "reader_promises": [
    {
      "id": "promise_001",
      "promise": "主角发誓要在冬雪降临前杀死国王",
      "deadline_event": "初雪降临"
    }
  ],
  "chapter_tension_curve": [
    { "chapter": 1, "tension_score": 8, "dominant_emotion": "curiosity" },
    { "chapter": 2, "tension_score": 4, "dominant_emotion": "relief" }
  ]
}
```

## 逻辑哨兵（Logic Sentry）验证规则
1. **钩子过期**：如果一个 `urgency="high"` 的 hook 超过 10 章未被提及或解决，哨兵报 `🟡 建议级：悬念发霉`。
2. **承诺违约**：如果世界观状态触发了 `deadline_event`，但承诺未兑现，哨兵报 `🔴 阻断级：读者承诺违约`。
3. **张力疲劳**：如果连续 3 章 `tension_score < 5`，哨兵报 `🟡 建议级：连续平淡，节奏塌陷预警`。
