# 市场判断证据规则

市场、平台、出海、改编、AI 质检阈值都属于易过期信息。SKILL 正文只写工作流，不写死“成功率/规模/年产量/检测阈值”等数字。

## 权威位置

- `评分/market_baseline_<YYYY-MM-DD>.json`：由 `collect_market_baseline.py` 或人工结构化证据生成，必须含采集日期、来源、链接/出处、适用平台。
- `资料/专业资料包_<主题>.md` + `资料/research_sources.json`：平台规则、出海合规、职业/行业细节等需要 fact-by-source 的证据包。
- `评分/score_report.json.market_baseline.freshness`：导出前由 QA gate 读取；过期或 freshness blocking 时阻断，除非有带作用域 waiver。

## 写作/评分使用

- 没有日期和来源的“热门套路”“平台规则”“改编概率”只能作为待验证假设。
- 涉及平台投稿、商业连载、出海、短剧/漫剧改编时，先刷新 market baseline 或专业资料包，再写入蓝图/评分。
- 文档和 prompt 可描述方向性判断，但不得把旧数字当当前事实复用。
