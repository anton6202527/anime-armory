# 模拟读者人格 + 信号 schema

## 人格库（`simulate_panel.py` 内置）

| ID | 名称 | 关注 | 确定性信号关键词（密度/千字） |
|---|---|---|---|
| `rookie` | 小白爽文党 | 节奏/升级/反杀/不憋屈 | 打脸·逆袭·碾压·突破·反杀·升级·解气·吊打… |
| `logic` | 逻辑考据党 | 设定自洽/体系/无降智 | 因为·所以·原理·规则·体系·境界·代价·破绽… |
| `emote` | 情感互动党 | 弧光/CP/张力/金句 | 心疼·温柔·守护·告白·暧昧·心动·眼泪·羁绊… |
| `critic` | 毒舌老书虫 | 同质化/文笔/新意 | 退婚·老爷爷·系统·穿越·重生·赘婿·扮猪吃虎… |

> `critic` 的关键词是**套路命中**（命中越多越像老梗），与其它人格"越多越好"相反。

## 信号 schema（`评分/reader_panel_signals.json`）

```json
{
  "date": "2026-06-09",
  "schema_version": 2,
  "kind": "novel_synthetic_reader_probe",
  "evidence_type": "synthetic_probe",
  "validation_status": "unvalidated",
  "decision_authority": "context_only",
  "numeric_score_eligible": false,
  "scope": "opening",
  "chapters_read": [1, 2, 3],
  "sampled_chars": 6200,
  "personas": {
    "rookie": {"name":"小白爽文党","focus":"…","keyword_density_per_kchar": 4.8}
  },
  "hook_strength": 0.62,                 // 章末钩子标记密度 0-1
  "lexical_diversity": 0.81,             // 4-gram 去重率，低=重复/水
  "cliche_density_per_kchar": 2.1,       // 套路命中密度
  "retention_proxy": 0.58,               // 表面代理 0-1，不是留存预测
  "retention_prior": 0.58                // schema v1 兼容别名
}
```

**retention_proxy 公式**（确定性表面代理，非真实留存、非校准预测）：
`0.45·min(爽点密度/6,1) + 0.35·钩子强度 + 0.20·min(多样性/0.9,1) − 0.10·min(套路密度/5,1)`，clamp 到 [0,1]。

## 判读

- 信号是**确定性表面代理**；人格输出是合成假设。两者都需编辑回到正文逐条验证。
- `retention_proxy`（兼容名 `retention_prior`）在 `novel-score` 只作 context-only 展示，**不进入自动数值调分**。
- 人格至少选 3 个差异化的；单人格视角会偏。
- 合成探针≠真实读者；即使补全人格输出，也不能据此声称“读者会怎样”或“留存是多少”。
