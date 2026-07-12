---
name: novel-style
description: 文风指纹提取与漂移检测 — 对项目 Demo、自有/授权/公版样本做可复现的文本统计(句式频率、描写偏好、对白占比、词频锚点),生成《文风指纹.json》供后续保持一致性。拒绝未授权姓名式复刻当代作者。Use when asked to 提取文风, 风格分析, 文风指纹, 文风漂移, 保持笔力一致, style fingerprint, style analysis. Triggers 文风指纹, 风格提取, 指纹分析, 文风漂移, novel style, prose fingerprint.
---

# novel-style — 授权文风指纹与漂移检测

解决 AI 写作“翻译腔”、“模板化”以及长篇文风前后不一的问题。

合规边界：本 skill 只做**抽象统计指纹**，样本必须是项目 Demo、自有、已授权或公版文本；不得要求“像某某在世作者一样写”、不得把未授权作品名/作者名作为复刻目标。

## 核心机制（确定性，纯标准库，不调 LLM）

1. **指纹提取 (Fingerprint Extractor)**：`extract_style.py` 对样本做**可复现的文本统计**——句长分布(均长/中位/短句比/长句比)、对白占比(引号字符比)、虚词密度(的地得/标点/破折省略)、词频锚点(无分词环境下 2-4 字 n-gram 计数滤停用词)、节奏标签。
2. **语义风格档案 (Semantic Profile)**：统计之外，指纹还可保存 `narrative_distance`、`pov_filter`、`metaphor_source`、`silence_habit`、`emotion_delivery`、`dialogue_attack_mode`。这些字段由 AI/人工填写，用来形成独特叙述人格，而不是未授权复刻某作者。
3. **指纹用途**：① 写作时把指纹摘要注入 `novel-create`/`novel-continue` 的 prompt；② `--compare` 算两份指纹（锚点 vs 候选章）的**漂移分**，供 `novel-review` 当"文风漂移"机检（见 `novel-review/scripts/consistency_audit.py`）。

## 工作流

### 1. 提取锚点指纹
```bash
python3 skills/novel-style/scripts/extract_style.py --source "<锚点章/样本路径>" --output "<作品根>/设定/风格指纹.json" --source-rights project-demo|user-owned|licensed|public-domain
```
- 支持 `.txt`, `.md`, 目录（目录按章号自然序拼接）。
- 产出字段：`style_source_rights` / `syntax_profile` / `dialogue_ratio` / `descriptive_habits` / `lexicon_anchor` / `rhythm`（schema 见 `references/fingerprint-schema.md`）。
- 若填写 `--style-source-name` 或 `--style-source-author`，必须同时声明 `--source-rights project-demo|user-owned|licensed|public-domain`；`unknown` 会被拒绝。
- 可补语义风格字段，例如：

```bash
python3 skills/novel-style/scripts/extract_style.py \
  --source "<锚点章>" --output "<作品根>/设定/风格指纹.json" \
  --source-rights project-demo \
  --narrative-distance "深三限，贴近主角感官" \
  --metaphor-source "账本、旧物、雨水、金属" \
  --emotion-delivery "动作先于解释，关键处留半句"
```

### 2. 漂移比对（给 review 做机检）
```bash
python3 skills/novel-style/scripts/extract_style.py --compare "<作品根>/设定/风格指纹.json" "<某章.md>" --json-out "<作品根>/审稿/style_drift.json"
```
- 第二个参数可是指纹 `.json` 或章节文本（文本会先自动提指纹再比）。
- 输出 `drift_score`（0=一致，越大越漂）+ 超带宽的 `flags`。`drift_flag` 为真只是**机检线索**，是否真崩仍由 LLM 人判（伏笔/刻意变奏可豁免）。

### 3. 写作时注入
把指纹摘要按模板喂给写作 prompt：
> "参考以下文风指纹的抽象统计特征：[摘要]。保持短促节奏和对白密度，避免照搬样本文句、专名、固定表达。"

## 指纹示例 (`风格指纹.json`)
```json
{
  "schema_version": 1,
  "syntax_profile": {"avg_sentence_length": 15.2, "median_sentence_length": 13,
                     "short_sentence_ratio": 0.62, "long_sentence_ratio": 0.08},
  "dialogue_ratio": 0.34,
  "descriptive_habits": {"de_particle_density": 3.1, "punctuation_density": 21.4,
                         "ellipsis_dash_per_kchar": 1.8, "comma_to_period_ratio": 1.6},
  "lexicon_anchor": [{"term": "暗金", "count": 12}, {"term": "蛰伏", "count": 7}],
  "rhythm": {"pace_tag": "fast_pulse"},
  "semantic_profile": {
    "narrative_distance": "深三限",
    "pov_filter": "主角优先注意账目、手部动作和门口退路",
    "metaphor_source": "商业账本、旧物、雨水",
    "silence_habit": "高情绪处不解释完整因果",
    "emotion_delivery": "动作和物件先于心理命名",
    "dialogue_attack_mode": "客气话里藏试探"
  }
}
```

## 与家族其它 Skill 的联动

- **novel-create**：Demo 章过审后，提取 Demo 文风作为后续全本锚点指纹。
- **novel-rewrite**：提取原作指纹，重构时选"保留"或"平滑过渡"。
- **novel-review**：`consistency_audit.py` 调本脚本 `--compare` 把"文风漂移"从纯人判下沉成机检。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 样本过少 | 至少提供 3-5 万字样本以获得准确指纹 |
| 盲目堆砌词汇 | 指纹的核心是“节奏”和“句式”，不仅仅是几个词 |
| 跨题材套用 | 仙侠指纹不适用于职场文，需按项目提取 |
| 让文本“像某某作者本人” | 拒绝未授权姓名式复刻；改为抽象特征描述或使用自有/授权样本 |
| 只看统计指纹 | 补 `semantic_profile`，否则只能防漂移，不能形成稳定叙述人格 |
