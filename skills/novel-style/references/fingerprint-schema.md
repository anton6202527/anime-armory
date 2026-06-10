# 风格指纹 schema（`extract_style.py` 产物）

确定性文本统计，纯标准库，无随机性 → 同一文本同一指纹，可复现、可比对。

## 字段

| 字段 | 含义 | 算法 |
|---|---|---|
| `schema_version` | 版本，当前 `1` | 常量 |
| `source` | 样本路径/标识 | 入参 |
| `sampled_chars` | 参与统计的 CJK 字数 | `[一-鿿]` 计数 |
| `sentence_count` | 有效句数 | 按 `。！？!?…\n` 切分后非空句 |
| `syntax_profile.avg_sentence_length` | 句均长（CJK 字） | 句长均值 |
| `syntax_profile.median_sentence_length` | 句长中位 | 排序取中 |
| `syntax_profile.short_sentence_ratio` | 短句比（≤12 字） | 占比 |
| `syntax_profile.long_sentence_ratio` | 长句比（≥30 字） | 占比 |
| `dialogue_ratio` | 对白字数占比 | 各引号对内 CJK 字 / 总字 |
| `descriptive_habits.de_particle_density` | 的地得 / 100 字 | 虚词密度，高=描写绵密 |
| `descriptive_habits.punctuation_density` | 标点 / 100 字 | 节奏疏密 |
| `descriptive_habits.ellipsis_dash_per_kchar` | 省略/破折 / 1000 字 | 停顿/气口偏好 |
| `descriptive_habits.comma_to_period_ratio` | 逗号:句号 | >2 长句绵延，<1 短促 |
| `lexicon_anchor[]` | 词频锚点 `{term,count}` | 2-4 字 n-gram 滤停用词，count≥3，去短词噪声 |
| `rhythm.pace_tag` | `fast_pulse`/`measured`/`dense` | 由句均长+短/长句比派生 |

## 漂移比对（`--compare`）输出

```json
{
  "drift_score": 0.21,        // 各指标相对差均值，0=一致
  "drift_flag": true,         // 是否有指标越带宽
  "metrics": { "<指标>": {"anchor":.., "candidate":.., "rel_diff":..} },
  "flags": [ {"metric":"avg_sentence_length","rel_diff":0.41,"band":0.35,"severity":"建议级"} ]
}
```

带宽（相对差超过即 flag）：句均长 .35 / 短句比 .40 / 长句比 .50 / 对白比 .50 / 的地得 .40 / 逗号句号比 .45；`pace_tag` 变化也记一条。

## 判读

- `drift_flag` 为真 = **机检线索**，不是定论。伏笔章、刻意变奏（战斗→抒情切换）、引文密集章都可能合理偏移 → 人判后可豁免。
- 锚点取**已过审的 Demo 章 / 风格标杆章**，别拿全本平均当锚点（会把漂移摊平）。
- 题材切换不可跨用指纹：仙侠指纹比对职场文必然高 `drift_score`，无意义。
