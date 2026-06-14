---
name: novel-balance
description: 情节热力图与节奏平衡仪 — 扫描全书文本的"情绪起伏度"和"信息密度",产出情节热力图(Heatmap)。识别高潮密集度、平淡铺垫期、节奏断裂点。自动给出"注水警告"或"节奏脱节"预警。Use when asked to 分析节奏, 情节热力图, 测一下注水, 节奏平衡, 扫一下全书起伏, plot heatmap, pacing balance, pacing analysis. Triggers 情节热力图, 节奏平衡, 节奏分析, 注水预警, 高潮密集度, 节奏断裂, novel balance, plot balance.
---

# novel-balance — 情节热力图与节奏平衡仪

解决长篇小说中期“注水严重”或“节奏过快/过慢”导致读者流失的问题。

## 核心机制

1. **维度提取**：
   - **情绪值 (Conflict/Emotion)**：每章的冲突强度、转折数量。
   - **信息量 (Info Density)**：新人物、新地图、新设定揭露的速度。
   - **爽点密度 (Payoff)**：期待感被满足的频率。
2. **可视化/量化报告**：生成章节维度的“心电图”，标注冗余期。

## 工作流

### 1. 生成热力图报告
```bash
python3 skills/novel-balance/scripts/pacing_analyzer.py "<作品根>" [--range 1-100]
```
- 读取全量/部分章节。
- 产出：`评分/情节热力图_<日期>.md`。

### 2. 节奏预警
- **注水预警**：连续 5 章情绪值低于 3 分，信息量低于 2 分。
- **脱节预警**：高潮结束后没有合理的缓冲期，直接进入下一个高潮（导致读者疲劳）。
- **烂尾预警**：伏笔回收率过低。

## 报告示例
| 章节 | 冲突强度 | 信息密度 | 爽点分 | 判定 |
|---|---|---|---|---|
| 第12章 | 8 | 4 | 7 | ✅ 节奏紧凑 |
| 第13章 | 3 | 1 | 2 | ⚠️ 建议压缩/注水 |
| 第14章 | 2 | 1 | 1 | 🔴 严重注水, 弃书点 |

## 与家族其它 Skill 的边界与联动

- **vs novel-review / novel-score（别混）**：balance 给"全书哪段塌"的鸟瞰节奏曲线；`novel-review` 逐章挑硬伤（这章钩子弱不弱）；`novel-score` 判"能不能火"。**balance 不把热力图喂给 score**——score 自有 `payoff_density` 维度、独立判定；两者只是概念互补，无数据依赖。
- **→ novel-condense / novel-promote**：注水段推给 `novel-condense` 压缩；高燃章推给 `novel-promote` 当宣发爆点源。修法回写章纲（`novel-craft/references/outline.md`），本 skill 不直接改文。
- **novel-craft (章纲编织)**：编排章纲时预填目标热力值，作为写作时的“配速员”。
- 确定性信号的**口径文档**是 `references/heatmap-method.md`；其**代码侧单一定义源**是 `skills/novel/_lib/keyword_banks.py`——爽点/冲突/钩子/情感/套路词表在那里定义一次，novel-balance / novel-simulate / novel-promote 共同 import，不再逐脚本复制（避免漂移）。novel-simulate 的 `爽点关键词` 与本 skill 的 `爽点密度` 即共用其中的 `PAYOFF_KW`。
- **按目标平台调档**：脚本读 `目标平台` 选择点（经 `keyword_banks.classify_platform` 归一为 `商业爽文向`/`品质向`，口径同 novel-score）。品质向小说节奏天然更缓、爽点稀薄是文体而非注水，故收紧"低冲突=注水"阈值，且不据爽点低升级到 🔴弃书点风险；爽文向保留原密尺。

## 详细参考
- 两条曲线算法、预警规则、修法回流：`references/heatmap-method.md`

## 常见错误

| 错误 | 纠正 |
|---|---|
| 盲目追求高分 | 节奏要有疏有密，全程 10 分的情绪值会造成读者审美疲劳 |
| 忽略信息揭露 | 只打架没进展叫“干打”，也属于广义上的注水 |
