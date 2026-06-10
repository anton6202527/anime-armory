# 流程自审操作手册（模式②）—— 让写小说产线可重复自我优化

把"人工复盘整条 novel 线"固化成一条可复跑流程。产出 = 一份**建议报告**（默认不自动改 skill）。与 `n2d-review`/`mv-review`/`song-review` 的模式② 同构。

## 何时跑
- 用户主动要（"novel 还能优化啥""过一遍写小说流程"）。
- 写完一批书/一个长项目后的阶段复盘。
- **接了新工艺/平台变化时**（平台热题材换代、新爽点套路、新章纲/留存方法、AI 写作最佳实践更新）——最高价值触发点。

## 先跑本地静态治理检查
联网对标前先跑：

```bash
python3 skills/novel-review/scripts/self_audit.py
python3 skills/novel-review/scripts/self_audit.py --project-root "<作品根>"
```

该脚本**只读不改、不联网**，检查 novel-* registry、`novel-author` 路由表、`skills/README.md` 索引、`_进度.md` 加锁写入口、`state_ledger.json` 原子写、批量写章队列、项目级市场基准新鲜度。若本地治理已有 block/warn，优先修这些，再进入下面的联网取证。

## 三轴取证（联网，必带年月）
按写小说三大验收维分轴搜，每轴落到"当前 SOTA 做法 + 证据链接 + 日期"：

| 轴 | 搜什么 | 映射到 novel 的 |
|---|---|---|
| **题材 / 市场契合** | 红果/番茄/晋江/抖音漫剧当下热题材与套路、黄金三章、完读率留存机制、平台分档 | `novel-score`（复用 `scripts/collect_market_baseline.py`）/ `novel-create` 立项题材选择 |
| **写作工艺** | 章纲编织、单章节奏、爽点密度、钩子/反转布置、show-don't-tell、文风一致 | `novel-craft/references/{outline,chapter,expand,continue,condense}.md` |
| **一致性 / 合规来源** | 设定圣经/锚点一致性方法、跨章人设防崩、公版/授权来源边界、原文照搬判定 | `novel-create`/`novel-spinoff` 设定与锚点 + fetch/spinoff/rewrite 合规闸门 + `mechanical_check.py` |
| **能力演进**（横切） | 长文本一致性、子代理逐章写作、AI 审稿/查重工具 | 各 skill 的子代理 prompt / `mechanical_check.py` 检查项 |

> 搜索词带"2026""最新""最佳实践""扑街/翻车"更易命中实战贴；中文为主（国内网文生态），英文补 AI-writing 圈一轮。

## 对照 → 差距清单
逐 skill 把"基准做法"对到 `novel-*/SKILL.md` + `novel-craft/references/*` + `novel-author/Q&A.md`：

- **先查已实现**：很多"新做法"产线早做了（如黄金三章钩子、爽点憋放、设定圣经单一真值、锚点表、原文照搬机检、容错铁律）。**已实现的不重复立项**——只在报告里标"✅ 已覆盖"一行带过。
- **找真差距**：只记"基准有、novel 没有或更弱"的。每条写成：
  ```
  差距：<一句话>
  证据：<链接>（采集 <年-月>）
  落点：<改哪个 skill 哪段 / 或新立项>
  优先级：must（影响成品质量/合规）/ optional（增稳/提效）
  可脚本化：是/否（是→能进 mechanical_check.py）
  ```
- **分三类处置**：① 硬约束（铁律/合规）② 可选增强（opt-in 段）③ 机检项（脚本）。

## 起草 + 落地（人确认后）
1. 高价值项**起草** skill edit（写成 diff 级描述：改哪段、加什么铁律/段落）。
2. **改任何 skill → 必同步 `skills/README.md` 索引**（仓库硬约定，缺了视为未完成）。
3. **默认不自动改产线**：模式②产报告，用户拍板后再由对应 skill / 人执行编辑。**报告一次性·不留存**：只讲给用户，**不在 skill 目录存 `_流程自审_*.md`**（已 gitignore）；每次重审都重跑全流程，不依赖任何旧存档。

## 防过期 / 防噪声铁律
- 每条建议**带来源链接 + 采集日期**；旧报告里的建议可能已被采纳或已过时，落地前重新核对当前 skill。
- 容错铁律同模式①：只报"真差距"，不把"换种说法会更好"的主观偏好堆进来。
- 题材热度会变（某题材退潮/某套路烂大街）——写"能力/方法"而非死绑某个当红题材名；具体热题材属 `novel-score` 的实时拉取，正文写通用原则。
- **与 `novel-score` 分工**：score 判一部作品"值不值得做"，本模式判"整条产线哪里该升级"；两者共用 `novel-score/references/market-baseline.md` + `novel-score/scripts/collect_market_baseline.py` 的热榜拉取思路，别各拉一份。

## 一次自审的标准产物
```
# novel 流程自审 <年-月-日>
## 三轴取证摘要（含来源链接）
## 差距清单（按优先级）
  - [must] …  落点：novel-xxx 某段
  - [optional] …
## 已覆盖（✅ 一行带过，证明查过没重复）
## 建议落地顺序 + 是否需要改 README
```
