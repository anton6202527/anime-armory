---
kind: n2d_ai_call_sheet
version: 1
episode: 第1集
status: confirmed
---
# 第1集 — AI 拍摄通告单

> 这是 Stage 2 分镜之后、出图 prompt 之前的制片交接单。confirmed 表示已按 storyboard / continuity / 合规包完成出图 prompt 前交接。

## 生产日目标
- 本轮目标：先生成第 2 层出图 prompt；共享定妆已存在时优先打样高风险长镜、多人反打镜和黑陶破盆微光镜，再进入全集出图。

## 放行前依赖
- P-1 开发包 confirmed；P-2 导演排戏包 confirmed；本 P-3 包 confirmed 后才进入出图 prompt。
- 角色/场景/道具/VFX 参考从共享 identity_registry / asset_registry 继承；新增缺口由出图 prompt 标为 reference plan。
- 任务字卡、疑问花字、字幕和其他可读文字走 compose overlay；生图/视频只留干净画面与安全区。
- 合规包按 internal_only demo 使用，平台审核/备案/出海本地化留到转投放前补齐。

## 拍摄顺序
| 顺序 | Clip | 场景 | 秒数 | 风险/模板 | 保持项 |
|---|---|---|---|---|---|
| 1 | EP01_CLIP01 |  | 25.459 | dialogue_shot_reverse | 尾帧 |
| 2 | EP01_CLIP02 |  | 13.332 | task_order | 尾帧 |
| 3 | EP01_CLIP03 |  | 3.662 | compressed_flashback | 无尾帧要求 |
| 4 | EP01_CLIP04 |  | 5.859 | night_route_choice | 尾帧 |
| 5 | EP01_CLIP05 |  | 10.943 | labor_montage | 尾帧 |
| 6 | EP01_CLIP06 |  | 18.351 | object_discovery | 无尾帧要求 |

## 人工停审点
- 动作/打斗/追逐/高运动镜必须优先审动作线、命中点、收势和可读性。
- 任务字卡、疑问花字、标题卡和任何文字镜必须确认留白与 overlay 安全区，不允许 AI 烤字。
- 集尾钩、关系转折和高情绪近景必须确认情绪转折与下一集问题清楚。

## 后期交接
- BGM hit 对齐本集爽点、反转、破盆微光和集尾钩；J/L cut 用环境声、动作声和短促花字音效衔接。
- 真实配音在先出视频后补，compose 前必须替换 rough timing 并复核字幕/镜头时长。
- 全集保持冷灰写实 3D 国风漫剧，黑陶破盆的暖金微光只作为剧情信息焦点，不改角色定妆。
