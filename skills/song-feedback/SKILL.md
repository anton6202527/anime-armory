---
name: song-feedback
description: Post-release feedback ingestion for song projects. Use after a song demo or release has real platform/test-listener data: plays, starts, completes, likes, saves, shares, comments, skip/drop points, short-video reuse, or A/B take performance. Writes 发行/feedback_events.jsonl, feedback_summary.json, and feedback_report.md; does not edit lyrics or audio.
---

# song-feedback — 歌曲发行/投放反馈回灌

把真实平台、测试听众或短视频投放数据回灌到写歌项目，判断哪个版本、hook、时长和发行策略有效。它不生成歌、不改词、不替代 `song-review` 的作品质检。

## 产物

- `发行/feedback_events.jsonl`：规范化逐条事件。
- `发行/feedback_summary.json`：按 take/platform/source 聚合播放、完播、点赞、收藏、分享、评论和短视频复用。
- `发行/feedback_report.md`：人读版回测报告与下一步建议。

## 用法

```bash
python3 skills/song-feedback/scripts/feedback_ingest.py "<写歌作品根>" \
  --input "<反馈.csv或.jsonl>" \
  --platform "抖音" \
  --source-name "首发小流量"
```

CSV/JSONL 字段可用英文或中文：

| 含义 | 字段 |
|---|---|
| take / 版本 | `take_id` / `take` / `版本` |
| 平台 | `platform` / `平台` |
| 同条件实验 | `experiment_id` / `实验` |
| 曝光/独立听众 | `impressions` / `曝光`，`unique_listeners` / `独立听众` |
| 播放/开始 | `plays` / `starts` / `播放` / `开始` |
| 完播 | `completes` / `complete` / `完播` |
| 跳出/跳过 | `skips` / `drops` / `跳出` |
| 点赞 | `likes` / `点赞` |
| 收藏 | `saves` / `收藏` |
| 分享 | `shares` / `分享` |
| 评论 | `comment` / `评论` / `text` |
| 二创/复用 | `reuses` / `短视频复用` |

## 判读原则

- 真实反馈优先于内部主观偏好，但小样本只作方向提示。
- A/B 只能在同平台、同 `experiment_id`、同批次和投放条件下比较；报告绑定当前发行音频 sha256。
- 少于 100 plays 标记 `insufficient`，只观察不改歌；100-499 为 `directional`；达到 500 才标记 `decision_ready`。阈值是本项目的决策纪律，不冒充平台通用真理。
- completion/skip/save/share 同时输出 95% Wilson proportion interval；即使达到固定样本数，区间仍太宽时也不能标记 `decision_ready`。
- 完播低不自动等于歌差，可能是投放人群、封面、标题或首屏 hook 问题；报告只给回流方向。
- 数据回测后，若要改歌，回 `song-lyrics` / `song-compose` / `song-review`，不要直接覆盖成品而不留版本。
