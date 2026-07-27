---
kind: n2d_ai_call_sheet
version: 1
episode: 第3集
status: confirmed
---
# 第3集 — AI 拍摄通告单

> 这是 Stage 2 分镜之后、出图 prompt 之前的制片交接单。confirmed 表示已按 storyboard / continuity / 合规包完成出图 prompt 前交接。

## 生产日目标
- 本轮目标：先生成第 2 层出图 prompt；共享定妆已存在时优先打样高风险动作镜与系统面板镜，再进入全集出图。

## 放行前依赖
- P-1 开发包 confirmed；P-2 导演排戏包 confirmed；本 P-3 包 confirmed 后才进入出图 prompt。
- `ai_shooting_schedule.json` 已列出高风险优先级、后端槽位、预算/并发护栏和 batch rerun scope。
- `continuity_bible.json` 已把 source/storyboard/entity/state/sidecar 聚合成场记真值源。
- 角色/场景/道具/VFX 参考从共享 identity_registry / asset_registry 继承；新增缺口由出图 prompt 标为 reference plan。
- 系统文字、状态数值、字幕和花字走 compose overlay；生图/视频只留空面板与安全区。
- 合规包按 internal_only demo 使用，平台审核/备案/出海本地化留到转投放前补齐。

## 拍摄顺序
| 顺序 | Clip | 场景 | 秒数 | 风险/模板 | 保持项 |
|---|---|---|---|---|---|
| 1 | EP03_CLIP01 | LOC_02/未来片段·官道群跪 | 10.52 | ensemble_blocking | 按 seam_mode 剪辑；无尾锚要求 |
| 2 | EP03_CLIP02 | LOC_01/荒野边缘浅坟 | 7.441 | 慢·静场 | 按 seam_mode 剪辑；无尾锚要求 |
| 3 | EP03_CLIP03 | LOC_01/荒野边缘换装 | 11.755 | dialogue_shot_reverse | 镜内尾锚（非接力） |
| 4 | EP03_CLIP04 | LOC_02/官道行路 | 15.383 | 快盘算转骤停 | 按 seam_mode 剪辑；无尾锚要求 |
| 5 | EP03_CLIP05 | LOC_02/官道对峙 | 4.428 | ensemble_blocking | 按 seam_mode 剪辑；无尾锚要求 |
| 6 | EP03_CLIP06 | LOC_02/官道陈情 | 15.551 | dialogue_shot_reverse | 按 seam_mode 剪辑；无尾锚要求 |
| 7 | EP03_CLIP07 | LOC_02/官道群跪 | 12.221 | ensemble_blocking | 镜内尾锚（非接力） |
| 8 | EP03_CLIP08 | LOC_02/官道集尾 | 11.534 | ensemble_blocking | 镜内尾锚（非接力） |

## 人工停审点
- 动作/打斗/追逐/高运动镜必须优先审动作线、命中点、收势和可读性。
- 系统面板、状态数值、标题卡和任何文字镜必须确认留白与 overlay 安全区，不允许 AI 烤字。
- 集尾钩、关系转折和高情绪近景必须确认情绪转折与下一集问题清楚。

## 后期交接
- BGM hit 对齐本集爽点、反转、系统信息和集尾钩；J/L cut 用环境声、动作声和 UI 音效衔接。
- 真实配音在先出视频后补，compose 前必须替换 rough timing 并复核字幕/镜头时长。
- 全集保持冷灰写实 3D 国风漫剧，百妖谱金色光只作为剧情信息焦点，不改角色定妆。
