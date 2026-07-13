---
name: novel-aesthetic
description: Positive craft sample and aesthetic judgement bank for novel projects. Use when the user wants to learn why a scene works, build an authorized/public-domain/self-owned model of good writing, compare a draft against positive examples, or strengthen taste beyond error-checking. Produces 设定/aesthetic_bank.json and 设定/审美样本库.md. Refuses unauthorized imitation of living authors and does not copy sample prose. Triggers 审美样本, 正向样本, 为什么这段好, 学习好文, 文学审美, 好章节拆解, 高光场景, 语言质感, taste, aesthetic bank, positive examples.
---

# novel-aesthetic — 正向审美样本库

`novel-review` 擅长找问题，`novel-score` 擅长判市场；本 skill 负责补另一半：**什么是好，为什么好，怎么迁移而不照抄**。它把项目 Demo、自有/授权/公版样本中的高光场景拆成可复用的审美判断，形成“正向标尺”。

产物落在作品根：

- `设定/aesthetic_bank.json`：机器可读样本库。
- `设定/审美样本库.md`：给人读的拆解。

## 合规边界

- 样本必须是 `project-demo`、`user-owned`、`licensed` 或 `public-domain`。
- 不做“像某某在世作者一样写”的姓名式复刻。
- 只提取结构、节奏、视角、情绪机制、语言策略和转写规则；不把样本文句当模板复制。

## 工作流

1. 初始化：

```bash
python3 skills/novel-aesthetic/scripts/aesthetic_bank.py scaffold "<作品根>"
```

2. 登记一个正向样本：

```bash
python3 skills/novel-aesthetic/scripts/aesthetic_bank.py add "<作品根>" \
  --sample-id OPENING-001 \
  --source-title "项目Demo第1章" \
  --source-rights project-demo \
  --dimension opening,prose,scene \
  --why-it-works "主角不是解释处境，而是用一个带羞耻感的动作暴露困境。" \
  --transfer-rule "开篇先给行动中的人，再让环境细节折射人物处境。" \
  --anti-copy-note "保留机制，不复用原句和专名。"
```

3. 检查样本库：

```bash
python3 skills/novel-aesthetic/scripts/aesthetic_bank.py check "<作品根>"
```

4. 为写章/编辑抽取审美对照：

```bash
python3 skills/novel-aesthetic/scripts/aesthetic_bank.py prompt "<作品根>" \
  --dimension prose --limit 3
```

## 样本拆解维度

- `opening`：开篇如何立人、立冲突、立读者期待。
- `scene`：场景目的、阻碍、转折和高光瞬间。
- `character`：人物选择如何暴露内在欲望或底线。
- `dialogue`：潜台词、信息差、一人一腔。
- `prose`：句式、意象、叙述距离、留白。
- `structure`：反转、伏笔、弧段配速。
- `theme`：题旨如何通过选择和后果出现，而不是靠说教。
- `novelty` / `surprise` / `premise`（**新颖度信号源**）：这段/这个前提**新在哪、违背了什么读者惯例、为什么让人意外但服气**。登记时建议同时填 `--why-it-is-new`。这三维让审美库不只当"工艺正向标尺"，也当创意正向信号源：`draft_packets.py` 装配写章包时会**优先注入** novelty 维度样本（至多 2 条，标 🌟），并显示 `why_it_is_new`，让登记的想象力样本真正到达写作端；`novel-score` ⑧ novelty 维度也可引用。

## 与其它 skill 的联动

- `novel-create`：Demo 过审后，把项目自己的高光章登记成第一批审美样本。
- `novel-style`：style 负责统计和漂移；本 skill 负责“为什么好”的语义判断。
- `novel-edit`：line edit 前可先抽取审美对照，避免只按扣分项机械润色。
- `novel-score`：品质向/文学向项目评分时可引用样本库，防止只按商业爽点尺衡量。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把审美样本当仿写模板 | 只迁移机制，不迁移原句、专名和独特表达 |
| 只登记“好看” | 必须写清 `why_it_works` 和 `transfer_rule` |
| 使用未知权利样本 | 拒绝；先确认自有、授权或公版 |
| 样本库只放外部作品 | 项目 Demo 的有效高光也要登记，这是最安全的风格锚 |
