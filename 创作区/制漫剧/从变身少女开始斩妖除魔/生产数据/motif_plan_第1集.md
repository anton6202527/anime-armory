# 题材母题检测 — 第1集

- **题材判定：系统流**（置信度 1.0，命中 2 词）　命中：系统/面板
- 母题桥段：1 处（系统面板家族 1 处）

## 母题增强建议（人确认后 `--write` 注回）

### EP01_CLIP12　命中 system_panel（3 词：光幕/系统面板/面板）
- 母题：`MOTIF_系统面板`（system_panel）套模板 `system_panel`
- 成长档建议：level=1 / panel_tier=v1（占位·按剧情改实际数值/属性）
- 增强落点：
  - **场景/道具**：AI 出锁色锁形发光光幕底框（`VFX_系统面板`，禁烤文字/数字）
  - **台词**：系统音腔（机械/简短，`narrator_role=系统`→字幕灰小字）；主角反应=爽点
  - **overlay 数值层**：合成期叠清晰 title/level/attrs（n2d-compose render_panel）

---
确认后：`python3 motif_detector.py <作品根> 第1集 --write` 注回 storyboard + 写 motif_registry.json。
详见 `n2d-script/references/题材母题框架.md`。
