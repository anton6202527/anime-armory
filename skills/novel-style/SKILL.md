---
name: novel-style
description: 文风指纹提取与深度克隆 — 通过对标杆文本(名家作品、爆款Demo)进行"指纹"分析(句式频率、描写偏好、对白占比、特定词汇库),生成《文风指纹.json》。在后续写作中作为底层约束注入,实现文笔的深度克隆,确保长篇小说文风不漂移。Use when asked to 提取文风, 克隆文笔, 模仿某人风格, 风格分析, 文风指纹, style fingerprint, prose cloning, style analysis. Triggers 文风指纹, 文笔克隆, 风格提取, 指纹分析, 模仿写作, novel style, prose fingerprint.
---

# novel-style — 文风指纹与深度克隆

解决 AI 写作“翻译腔”、“模板化”以及长篇文风前后不一的问题。

## 核心机制（确定性，纯标准库，不调 LLM）

1. **指纹提取 (Fingerprint Extractor)**：`extract_style.py` 对样本做**可复现的文本统计**——句长分布(均长/中位/短句比/长句比)、对白占比(引号字符比)、虚词密度(的地得/标点/破折省略)、词频锚点(无分词环境下 2-4 字 n-gram 计数滤停用词)、节奏标签。**语义层**（"像不像名家的气口"）由 LLM 结合指纹人判，本脚本只给确定性骨架。
2. **指纹用途**：① 写作时把指纹摘要注入 `novel-create`/`novel-continue` 的 prompt；② `--compare` 算两份指纹（锚点 vs 候选章）的**漂移分**，供 `novel-review` 当"文风漂移"机检（见 `novel-review/scripts/consistency_audit.py`）。

## 工作流

### 1. 提取锚点指纹
```bash
python3 skills/novel-style/scripts/extract_style.py --source "<锚点章/样本路径>" --output "<作品根>/设定/风格指纹.json"
```
- 支持 `.txt`, `.md`, 目录（目录按章号自然序拼接）。
- 产出字段：`syntax_profile` / `dialogue_ratio` / `descriptive_habits` / `lexicon_anchor` / `rhythm`（schema 见 `references/fingerprint-schema.md`）。

### 2. 漂移比对（给 review 做机检）
```bash
python3 skills/novel-style/scripts/extract_style.py --compare "<作品根>/设定/风格指纹.json" "<某章.md>" --json-out "<作品根>/审稿/style_drift.json"
```
- 第二个参数可是指纹 `.json` 或章节文本（文本会先自动提指纹再比）。
- 输出 `drift_score`（0=一致，越大越漂）+ 超带宽的 `flags`。`drift_flag` 为真只是**机检线索**，是否真崩仍由 LLM 人判（伏笔/刻意变奏可豁免）。

### 3. 写作时注入
把指纹摘要按模板喂给写作 prompt：
> "严格对齐以下文风指纹：[摘要]。保持短促节奏，禁止堆砌形容词。"

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
  "rhythm": {"pace_tag": "fast_pulse"}
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
