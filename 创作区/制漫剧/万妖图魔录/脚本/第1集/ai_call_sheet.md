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
| 1 | EP01_CLIP01 | 夕照尸场，贯胸虎妖在画右上高位睁眼起身，姜月初中景僵住，裴长青低位失血。 | 8.435 | multi_character_same_frame | 镜内尾锚（非接力） |
| 2 | EP01_CLIP02 | 黑场时间字卡后，姜月初从尸骸间睁眼，撑地坐起。 | 6.15 | 铺垫·长镜 | 按 seam_mode 剪辑；无尾锚要求 |
| 3 | EP01_CLIP03 | 姜月初以动作检查囚服、尸骸和荒野地貌，旁白压缩世界信息。 | 7.632 | 铺垫·长镜 | 按 seam_mode 剪辑；无尾锚要求 |
| 4 | EP01_CLIP04 | 赤云纹插入后，姜月初走到安全距离查看贯胸虎尸，只给半拍松气。 | 11.028 | reveal_reaction_chain | 按 seam_mode 剪辑；无尾锚要求 |
| 5 | EP01_CLIP05 | 裴长青从尸堆低位开口，姜月初发现他的伤势并转身准备独自离开。 | 8.614 | reveal_reaction_chain | 按 seam_mode 剪辑；无尾锚要求 |
| 6 | EP01_CLIP06 | 断刀从画右后飞来钉进姜月初脚前硬土，她脚尖僵住。 | 5.439 | 爽点·CU硬切 | 按 seam_mode 剪辑；无尾锚要求 |
| 7 | EP01_CLIP07 | 姜月初与倒地裴长青沿既定轴线谈判，断刀作为中间筹码，最后她伸手。 | 13.487 | dialogue_shot_reverse | 按 seam_mode 剪辑；无尾锚要求 |
| 8 | EP01_CLIP08 | 姜月初扶裴长青半站，两人朝画左南向出口挪动。 | 2.4 | hug_or_pull | 镜内尾锚（非接力） |
| 9 | EP01_CLIP09 | 两人停步回看，虎妖从同一巨石旁站起，画面追上冷开。 | 5.874 | reveal_reaction_chain | 按 seam_mode 剪辑；无尾锚要求 |
| 10 | EP01_CLIP10 | 虎妖高位宣告吞食意图；裴低声点破半步鸣骨和天赋神通，俯身从同僚尸旁捡起完整横刀并压低重心。 | 9.188 | multi_character_same_frame | 按 seam_mode 剪辑；无尾锚要求 |
| 11 | EP01_CLIP11 | 裴沿既定轴线冲锋斩落，虎妖单脚迎击，裴被反向踢回姜月初脚边。 | 9.586 | fight_exchange | 镜内尾锚（非接力） |
| 12 | EP01_CLIP12 | 姜月初低头看裴，再抬眼看虎妖；虎妖高位慢步逼近一小步。 | 6.113 | 留白·定格 | 按 seam_mode 剪辑；无尾锚要求 |
| 13 | EP01_CLIP13 | 外界声场抽空，黑金无字古卷底框在姜月初右上视野展开，金墨光丝照亮她的眼。 | 13.473 | system_panel | 按 seam_mode 剪辑；无尾锚要求 |
| 14 | EP01_CLIP14 | 姜月初主观近景看虎妖虚焦巨影，手指空握又松开。 | 3.794 | 加速·碎切 | 按 seam_mode 剪辑；无尾锚要求 |
| 15 | EP01_CLIP15 | 姜月初视线从虎妖移到裴长青，再落到裴右侧的完整横刀；不移动，只改变选择目标。 | 6.582 | reveal_reaction_chain | 按 seam_mode 剪辑；无尾锚要求 |
| 16 | EP01_CLIP16 | 姜月初握刀起身，裴先看刀再看她；她不回避视线，只说抱歉。 | 3.074 | relationship_turn | 按 seam_mode 剪辑；无尾锚要求 |
| 17 | EP01_CLIP17 | 完整横刀沿既定方向刺入裴胸口，克制避开猎奇；少量暗红血点溅上姜月初脸颊。 | 4.369 | fight_exchange | 镜内尾锚（非接力） |
| 18 | EP01_CLIP18 | 裴长青错愕看姜月初，只吐出一个你字；声音断后切向姜月初的后果反应。 | 0.893 | 留白·定格 | 按 seam_mode 剪辑；无尾锚要求 |
| 19 | EP01_CLIP19 | 姜月初脸颊新血点清晰，她握刀的手轻颤却不松开；无系统到账、无音乐，1.3秒后硬切黑。 | 1.3 | 留白·定格 | 按 seam_mode 剪辑；无尾锚要求 |

## 人工停审点
- 动作/打斗/追逐/高运动镜必须优先审动作线、命中点、收势和可读性。
- 系统面板、状态数值、标题卡和任何文字镜必须确认留白与 overlay 安全区，不允许 AI 烤字。
- 集尾钩、关系转折和高情绪近景必须确认情绪转折与下一集问题清楚。

## 后期交接
- BGM hit 对齐本集爽点、反转、系统信息和集尾钩；J/L cut 用环境声、动作声和 UI 音效衔接。
- 真实配音在先出视频后补，compose 前必须替换 rough timing 并复核字幕/镜头时长。
- 全集保持冷灰写实 3D 国风漫剧，百妖谱金色光只作为剧情信息焦点，不改角色定妆。
