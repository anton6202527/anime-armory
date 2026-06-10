# n2d-score Schema

`n2d-score` 的机器真值写入：

```text
制漫剧/<剧名>/生产数据/score_第N集.json
制漫剧/<剧名>/生产数据/score_第N集.md
```

## JSON 顶层

```json
{
  "kind": "n2d_episode_review_score",
  "version": 1,
  "root": "制漫剧/<剧名>",
  "episode": "第1集",
  "generated_at": "2026-06-08T00:00:00+00:00",
  "threshold": 85,
  "total_score": 83,
  "status": "fail",
  "score_inputs": {
    "consistency": "生产数据/score_inputs/第1集_consistency.json",
    "mechanical": "生产数据/score_inputs/第1集_mechanical.json",
    "visual": "生产数据/score_inputs/第1集_visual.json",
    "identity": "生产数据/score_inputs/第1集_identity.json"
  },
  "dimensions": [],
  "auto_return_tasks": [],
  "unmapped_findings": [],
  "enqueued_batch_tasks": 3
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `kind` | string | 固定为 `n2d_episode_review_score` |
| `version` | integer | schema 版本 |
| `root` | string | 作品根 |
| `episode` | string | 标准集名，如 `第1集` |
| `generated_at` | string | UTC ISO 时间 |
| `threshold` | integer | 通过阈值，默认 `85` |
| `total_score` | integer | 七维加权总分，0-100 |
| `status` | string | `pass` / `warn` / `fail` |
| `score_inputs` | object | 输入缓存路径：consistency / mechanical / visual / identity（跨集漂移，registry+insightface 可用时才有） |
| `dimensions` | array | 七个维度分 |
| `auto_return_tasks` | array | 低分维度聚合后的回流建议 |
| `unmapped_findings` | array | 无法归到七维的 findings（如 完整性/水印/视频）；不再静默丢弃。含 block 级时整集不给 `pass`，并入 `data_collection_tasks` 出 `triage_unmapped` 分诊任务 |
| `enqueued_batch_tasks` | integer | 可选；启用 `--enqueue-low` 后写入的 batch 任务数 |

## dimensions[]

固定七维，不允许改名：

| key | label | 权重 | 默认回流 |
|---|---|---:|---|
| `character_consistency` | 角色一致性 | 20 | `image` |
| `outfit_consistency` | 服装一致性 | 12 | `image` |
| `scene_consistency` | 场景一致性 | 12 | `image` |
| `subtitle_correctness` | 字幕正确性 | 16 | `script_stage2` |
| `audio_visual_sync` | 音画同步 | 16 | `compose` |
| `rhythm_density` | 节奏密度 | 12 | `script_stage2` |
| `style_consistency` | 风格一致性 | 12 | `image` |

每项结构：

```json
{
  "key": "character_consistency",
  "label": "角色一致性",
  "weight": 20,
  "score": 53,
  "status": "fail",
  "blocks": 1,
  "warnings": 1,
  "infos": 0,
  "skipped": false,
  "evidence": ["脸(G1): block=1 warn=0 ok=4 skipped=False"],
  "return_to_stage": "image",
  "rerun_scope": "回 n2d-image 重出崩脸/身份漂移镜头；必要时补 identity_registry / reference_group。"
}
```

评分规则：

- 无信号维度：`score=70`，`status=insufficient_data`，不会静默通过。
- 每个 block 扣 `35` 分，每个 warn 扣 `12` 分，每个 info 扣 `2` 分。
- 任一 block 使维度 `fail`。
- 维度分低于阈值但无 block 时为 `warn`。

## visual checks

`--run-checks` 现在还会调用：

```bash
python3 skills/n2d-score/scripts/visual_checks.py <作品根> 第N集 --json
```

并缓存到：

```text
生产数据/score_inputs/第N集_visual.json
```

结构：

```json
{
  "kind": "n2d_score_visual_checks",
  "version": 1,
  "episode": "第1集",
  "sections": {
    "image_similarity": {
      "blocks": 0,
      "warnings": 1,
      "skipped": false,
      "metrics": {"max_dhash_distance": 18},
      "evidence": ["Clip 2 接缝 dHash 距离 18 > 14"]
    },
    "subtitle_ocr": {},
    "av_duration": {},
    "lip_sync": {},
    "final_rhythm_density": {}
  }
}
```

映射：

| section | 映射维度 | 说明 |
|---|---|---|
| `image_similarity` | `scene_consistency` | 尾帧与下一首帧 dHash 距离，接近实际跳切观感 |
| `subtitle_ocr` | `subtitle_correctness` | 成片底部字幕 OCR 抽检；缺 OCR 依赖则 skipped |
| `av_duration` | `audio_visual_sync` | 成片、配音主轨、SRT、storyboard 时长对账 |
| `lip_sync` | `audio_visual_sync` | 接外部 lip-sync/SyncNet 报告；无报告但 prompt 有 `mouth_visible=yes` 时给风险 warn |
| `final_rhythm_density` | `rhythm_density` | 成片镜头密度、钩子间隔、集尾钩子 |

## auto_return_tasks[]

低于阈值、`fail` 或 `insufficient_data` 的维度按 `return_to_stage` 聚合：

```json
{
  "return_to_stage": "image",
  "dimensions": ["角色一致性", "服装一致性"],
  "scope": "回 n2d-image 重出崩脸/身份漂移镜头；回 n2d-image 重出服装/配色漂移镜头；先检查定妆组和服装参考图。",
  "affected_artifacts": [],
  "affected_shots": []
}
```

启用 `--enqueue-low` 时，`n2d-score` 会把这些任务交给 `n2d-batch`，生成：

```text
制漫剧/<剧名>/生产数据/batch_queue.json
制漫剧/<剧名>/生产数据/batch_queue.md
```

## 输入缓存

`--run-checks` 会先调用：

```bash
python3 skills/n2d-review/scripts/consistency_audit.py <作品根> 第N集 --json
python3 skills/n2d-review/scripts/mechanical_check.py <作品根> 第N集 --json
python3 skills/n2d-score/scripts/visual_checks.py <作品根> 第N集 --json
```

并缓存到：

```text
生产数据/score_inputs/第N集_consistency.json
生产数据/score_inputs/第N集_mechanical.json
生产数据/score_inputs/第N集_visual.json
```

不带 `--run-checks` 时使用缓存，适合人工补充机检 JSON 后复评。
