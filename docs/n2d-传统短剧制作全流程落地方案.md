# n2d 传统短剧制作全流程审查与落地方案

> 记录日期：2026-07-02  
> 目的：把传统短剧从小说开发、编剧改编、导演排戏、制片拆解、拍摄、后期、验收的流程，落成 n2d 可执行的文件、脚本和 gate。

## 1. 行业判断

微短剧已经不是只靠粗放投流的内容形态。广电总局 2025-02-05 通知要求分类分层审核、白名单和总编辑内容负责制；2026-06-24《微短剧发展管理办法（征求意见稿）》进一步把微短剧定义为单集少于 20 分钟、主题主线明确、情节连续完整、人物角色突出的剧集，并要求分类实行备案公示和发行许可制度。AI 制作的微短剧还应在每集明显位置添加提示标识。

QuestMobile《2026短剧行业洞察报告》把 AI 漫剧列为短剧产业链里的独立内容形态，提到 AI 原生制作方通过 AI 工具实现“一人一剧组”的高效生产。这个判断和 n2d 的方向一致：n2d 不应追求“一步生成成片”，而应把传统剧组的编剧、导演、一副导演、场记、制片、后期职能拆成可签收文件。

参考：
- 国家广播电视总局：《关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知》 https://www.nrta.gov.cn/art/2025/2/5/art_113_70148.html
- 国家广播电视总局：《微短剧发展管理办法（征求意见稿）》 https://www.nrta.gov.cn/art/2026/6/24/art_113_73514.html
- QuestMobile：《2026短剧行业洞察报告》 https://pdf.dfcfw.com/pdf/H3_AP202605271822903507_1.pdf
- ScreenSkills Director / First AD / Script Supervisor 职责说明
- StudioBinder Pre-Production / Script Breakdown 工作流
- Filmmakers Academy 180-degree rule

## 2. 传统短剧怎么做

### 2.1 编剧拿到小说

专业编剧不会直接把小说逐字改成台词。第一步是开发判断：

- 版权、题材、平台、受众、发行地区和合规边界。
- 一句话卖点：观众为什么点开，为什么追下去。
- 系列圣经：主角欲望、世界观规则、人物弧、反派/系统/真相长线钩子。
- 前 3-5 集追更骨架：第 1 集立钩，第 2 集承接并抬高代价，第 3 集兑现小弧或制造关注/付费卡点。
- 改编取舍：小说文本分成成戏、旁白带过、后文带出、合并、删除；关键改动必须保住动机、因果、伏笔、状态和人物弧。
- 剧本写作：场景、动作、对白、旁白、屏幕文字、情绪标注、钩子点、爽点和集尾断点。
- 读稿/改稿：查对白活人感、场必转、信息回报、情绪回报和假 cliffhanger。

### 2.2 导演拿到剧本

专业导演也不会直接把剧本拆成 prompt。导演先排戏：

- 每场戏的戏剧目的：让观众知道什么、担心什么、期待什么。
- 人物欲望和阻碍：谁想要什么，谁挡住他。
- 走位和权力关系：谁在前景/中景/后景，谁逼近，谁退让。
- 轴线和视线：正反打、过肩、移动方向和道具视线要连续；跨轴必须有叙事动机。
- 景别进程：定场镜建立空间，中景建立关系，近景/特写打情绪峰值。
- 运镜动机：推、拉、摇、移、跟、升降必须服务压迫、揭示、追随、释放或信息落点。
- 衔接设计：动作接、视线接、声音桥、J cut、L cut、空镜缓冲、首尾帧接力。
- 竖屏短剧规则：9:16 里脸要可读，多用 Z 轴纵深，不把横屏调度简单裁切成竖屏。

### 2.3 一副导演/制片组做什么

剧本和分镜定稿后，进入制片拆解：

- 按场景/镜头列角色、场景、道具、服装、妆发、VFX、SFX、BGM、字幕/花字。
- 标出高风险镜头：多人同框、口型、打斗、系统面板、奇观、大场景、跨镜接缝。
- 做连续性拆解：服装、伤痕、持物、知识状态、位置状态、视线和轴线。
- 做拍摄通告单：拍摄顺序、依赖资产、人工停审点、失败降级方案。

在 n2d 里，出图/出视频就是 AI 拍摄工位，`production_breakdown` 等于一副导演 + 制片主任 + 场记的前置交接。

## 3. n2d 当前能力

已有：

- P-1 开发包：`skills/n2d-script/scripts/development_pack.py`
- P-2 导演排戏包：`skills/n2d-script/scripts/director_blocking_pack.py`
- 剧本质量契约：`script_quality_gate.py`
- 导演运镜计划：`director_camera_plan.py`
- 景别/转场审查：`shot_grammar_audit.py`
- review gate、score、review-ui、production_readiness 证据链

缺口已补：

- P-3 制片拆解包：`skills/n2d-script/scripts/production_breakdown.py`
- 进度假绿审计：`python3 skills/n2d/progress.py audit-acceptance <作品根> [--fix]`

## 4. 新的 n2d 流水线

```text
小说
  ↓
P-1 开发包
  series_bible / adaptation_strategy / season_arc / production_feasibility / pilot_greenlight
  ↓ confirmed
Stage 1 编剧改编
  raw 边界复核 / adaptation_triage / voiceover / bgm / 封面 / 角色场景卡
  ↓
P-2 导演排戏包
  director_beat_sheet / axis_blocking_map / shot_progression_plan / transition_map / vertical_composition_plan / edit_rhythm_map
  ↓ confirmed
Stage 2 分镜设计
  storyboard / 分镜剧本 / 素材清单 / 字幕 / 镜头时长 / script_quality_contract
  ↓
P-3 制片拆解包
  production_breakdown / continuity_breakdown / ai_call_sheet
  ↓ confirmed
AI 拍摄与后期
  n2d-image → n2d-video → n2d-compose → n2d-review
```

## 5. P-3 文件口径

命令：

```bash
python3 skills/n2d-script/scripts/production_breakdown.py <作品根> 第N集 scaffold --write
python3 skills/n2d-script/scripts/production_breakdown.py <作品根> 第N集 check --json --write-missing
```

必填文件：

- `脚本/第N集/production_breakdown.json`：逐镜角色、场景、道具、服装、VFX/overlay、声音、后端风险、部门交接。
- `脚本/第N集/continuity_breakdown.json`：逐镜起止状态、视线、轴线、服化道、持物、知识状态、转场守则。
- `脚本/第N集/ai_call_sheet.md`：AI 拍摄通告单，列生产目标、依赖、拍摄顺序、停审点和后期交接。

检查产物：

- `生产数据/production_breakdown_check_第N集.json`
- `生产数据/production_handoff_pack_第N集.md`

签收口径：三个文件都必须 `status=confirmed`，且不能含 `待补/TODO/TBD` 占位；否则 `run.py next` 在 `image_prompt` 前阻断。

## 6. 现有项目迁移

优先顺序：

1. `金睛缉妖录`：第 1 集处于出图前，最适合按 P-1/P-2/P-3 重新打样。
2. `那妖魔是姜大人`：先修复“验收✅但配音⬜”假绿，再补 P-1/P-2/P-3。
3. `仙界闭关小能手`：先迁移 manifest，再补 P-1/P-2/P-3 并重新走验收。

推荐命令：

```bash
python3 skills/n2d/progress.py audit-acceptance '创作区/制漫剧/那妖魔是姜大人' --fix
python3 skills/n2d/_lib/n2d_contract.py migrate-version '创作区/制漫剧/仙界闭关小能手'

python3 skills/n2d-script/scripts/development_pack.py '创作区/制漫剧/金睛缉妖录' scaffold --write
python3 skills/n2d-script/scripts/director_blocking_pack.py '创作区/制漫剧/金睛缉妖录' 第1集 scaffold --write
python3 skills/n2d-script/scripts/production_breakdown.py '创作区/制漫剧/金睛缉妖录' 第1集 scaffold --write
python3 skills/n2d/run.py next '创作区/制漫剧/金睛缉妖录' 第1集 --json
```

## 7. 产品原则

- 不把“能生成”当作“能交付”。
- 不让分镜临场发明导演排戏。
- 不让出图 prompt 临场发明制片拆解。
- 不让验收签收覆盖上游缺口。
- 每个贵工位前都要有可签收的文字、导演、制片、合规和连续性证据。
