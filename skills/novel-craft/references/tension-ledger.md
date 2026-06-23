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

## 行级 / 段落级微张力（micro-tension）

上面的 `chapter_tension_curve` 是**章级**张力（宏观节奏，防"连续平淡"）。但章级达标 ≠ 段落耐读——一章整体是高潮，中间仍可能有大段"信息平推、读者走神"的死水段。微张力（Donald Maass《Writing the Breakout Novel》的核心主张："tension on every page"）补的就是这一层：**翻开任意一页，那一页都该有一缕未解的小情绪在拉着读者往下读**。

微张力不靠外部冲突（不是每段都要打架），而靠**情绪的微小不确定**：

- **来源四型**：① 不安 / 隐忧（连平静场景下也潜着一丝不对劲）；② 怀疑 / 悬而未决（一个没说破的疑点）；③ 期待 / 渴望（角色想要却没到手）；④ 矛盾情绪（又爱又恨、想说又咽回去——与 `dialogue.md` 潜台词同源）。
- **连描写/独白也要带张力**：纯景物、纯心理若只是中性铺陈=死水。给它一点情绪指向（人物在这景里"等什么/怕什么"），描写就活了（与 `描写.md`「描写服务情绪」联动）。
- **对白尤其**：表面寒暄之下要有暗流，无博弈的对白是微张力黑洞（见 `dialogue.md`）。

### 段落级自检（写完一页/一段问）
- [ ] 这一段有没有至少一缕"未解的小情绪"（疑/忧/盼/矛盾）拉着读者？
- [ ] 有没有连续多段是纯信息平推 / 中性描写 / 无博弈对白的"死水段"？
- [ ] 平静过渡场景，是否仍埋了一点不安或期待，而非彻底松弛？

> 与章级的分工：`tension_score` 防"哪一章塌"，微张力防"哪一页让人弃读"。`novel-balance` 的信息密度曲线可辅助定位死水段；微张力本身偏人判，是写时与精修时的逐段意识，不强求机检。
