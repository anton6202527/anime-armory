---
kind: n2d_ai_call_sheet
version: 1
episode: 第1集
status: confirmed
---
# 第1集 — AI 拍摄通告单

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
| 1 | EP01_CLIP01 | LOC_JINGYANGGANG/夜/外 | 4.893 | fight_exchange | 镜内尾锚（非接力） |
| 2 | EP01_CLIP02 | LOC_JINGYANGGANG/夜/外 | 10.229 | fight_exchange | 镜内尾锚（非接力） |
| 3 | EP01_CLIP03 | LOC_JINGYANGGANG→LOC_YANGGU_STREET/蒙太奇 | 13.02 | ensemble_blocking | 按 seam_mode 剪辑；无尾锚要求 |
| 4 | EP01_CLIP04 | LOC_YANGGU_STREET/日/外内并置 | 10.145 | ensemble_blocking | 镜内尾锚（非接力） |
| 5 | EP01_CLIP05 | LOC_YANGGU_STREET→LOC_WUDA_HOME/日 | 8.67 | multi_character_same_frame | 镜内尾锚（非接力） |
| 6 | EP01_CLIP06 | LOC_WUDA_HOME/日→月余蒙太奇 | 14.692 | relationship_turn | 按 seam_mode 剪辑；无尾锚要求 |
| 7 | EP01_CLIP07 | LOC_WUDA_HOME/雪夜/内 | 12.677 | dialogue_shot_reverse | 镜内尾锚（非接力） |
| 8 | EP01_CLIP08 | LOC_WUDA_HOME/雪夜/内 | 10.228 | dialogue_shot_reverse | 镜内尾锚（非接力） |
| 9 | EP01_CLIP09 | LOC_WUDA_HOME/雪夜/内 | 14.281 | dialogue_shot_reverse | 镜内尾锚（非接力） |
| 10 | EP01_CLIP10 | LOC_WUDA_HOME/雪夜/内 | 10.699 | reveal_reaction_chain | 镜内尾锚（非接力） |
| 11 | EP01_CLIP11 | LOC_WUDA_HOME/雪夜/内 | 10.129 | relationship_turn | 镜内尾锚（非接力） |
| 12 | EP01_CLIP12 | LOC_YANGGU_STREET/雪夜/外 | 5.766 | relationship_turn | 镜内尾锚（非接力） |
| 13 | EP01_CLIP13 | LOC_COUNTY_YAMEN/日/内 | 7.946 | dialogue_shot_reverse | 镜内尾锚（非接力） |
| 14 | EP01_CLIP14 | LOC_WUDA_HOME/清晨/门外 | 6.569 | dialogue_shot_reverse | 按 seam_mode 剪辑；无尾锚要求 |
| 15 | EP01_CLIP15 | LOC_CITY_GATE↔LOC_YANGGU_STREET/清晨/外内并置 | 5.786 | reveal_reaction_chain | 镜内尾锚（非接力） |

## 人工停审点
- 动作/打斗/追逐/高运动镜必须优先审动作线、命中点、收势和可读性。
- 系统面板、状态数值、标题卡和任何文字镜必须确认留白与 overlay 安全区，不允许 AI 烤字。
- 集尾钩、关系转折和高情绪近景必须确认情绪转折与下一集问题清楚。

## 后期交接
- BGM hit 对齐本集爽点、反转、系统信息和集尾钩；J/L cut 用环境声、动作声和 UI 音效衔接。
- 真实配音在先出视频后补，compose 前必须替换 rough timing 并复核字幕/镜头时长。
- 全集保持冷灰写实 3D 国风漫剧，百妖谱金色光只作为剧情信息焦点，不改角色定妆。
