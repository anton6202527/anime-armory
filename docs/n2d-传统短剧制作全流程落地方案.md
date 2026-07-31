# n2d 传统短剧制作全流程审查与落地方案

> 记录日期：2026-07-02；更新：2026-07-03  
> 目的：把传统短剧从小说开发、编剧改编、导演排戏、制片拆解、拍摄、后期、验收的流程，落成 n2d 可执行的文件、脚本和 gate。

## 1. 行业判断

微短剧已经不是只靠粗放投流的内容形态。广电总局 2025-02-05 通知要求分类分层审核、白名单和总编辑内容负责制；2026-06-24《微短剧发展管理办法（征求意见稿）》进一步把微短剧定义为单集少于 20 分钟、主题主线明确、情节连续完整、人物角色突出的剧集，并要求分类实行备案公示和发行许可制度。AI 制作的微短剧还应在每集明显位置添加提示标识。

QuestMobile《2026短剧行业洞察报告》把 AI 漫剧列为短剧产业链里的独立内容形态，提到 AI 原生制作方通过 AI 工具实现“一人一剧组”的高效生产。这个判断和 n2d 的方向一致：n2d 不应追求“一步生成成片”，而应把传统剧组的编剧、导演、一副导演、场记、制片、后期职能拆成可签收文件。

参考：
- 国家广播电视总局：《关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知》 https://www.nrta.gov.cn/art/2025/2/5/art_113_70148.html
- 国家广播电视总局：《微短剧发展管理办法（征求意见稿）》 https://www.nrta.gov.cn/art/2026/6/24/art_113_73514.html
- 中央网信办等：《人工智能生成合成内容标识办法》 https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm
- 国家标准 GB 45438-2025《网络安全技术 人工智能生成合成内容标识方法》 https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=F32EA2A561F1886CD8D606513512D547
- OpenAI Sora 2 Prompting Guide https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide
- Google Cloud Veo 3.1 Prompting Guide https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
- Kling Element Library User Guide https://kling.ai/quickstart/klingai-element-library-3-user-guide
- Runway Gen-4 World Consistency https://runwayml.com/research/introducing-runway-gen-4
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

- P-1 开发包：`skills/n2d/n2d-script/scripts/development_pack.py`
- P-2 导演排戏包：`skills/n2d/n2d-script/scripts/director_blocking_pack.py`
- 剧本质量契约：`script_quality_gate.py`
- 导演运镜计划：`director_camera_plan.py`
- 景别/转场审查：`shot_grammar_audit.py`
- review gate、score、review-ui、production_readiness 证据链

缺口已补：

- P-3 制片拆解包：`skills/n2d/n2d-script/scripts/production_breakdown.py`
- 进度假绿审计：`python3 skills/n2d/progress.py audit-acceptance <作品根> [--fix]`
- progress DAG 红灯审计：`python3 skills/n2d/progress.py audit-dag <作品根> --json`
- 发布 verdict 聚合器：`python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --json`
- 失败归因与 report-only 升级：`python3 skills/n2d/scripts/failure_taxonomy.py <作品根> 第N集 --json`
- 首集 pilot 签收检查：`python3 skills/n2d/scripts/pilot_check.py check <作品根> 第1集 --write-missing --json`
- 预防式合同 gate：`python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第N集 --stage <stage> --write --json`

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
预防式合同
  episode_promise / shot intent / reference slots / interaction physics / audio timing / pilot acceptance
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
python3 skills/n2d/n2d-script/scripts/production_breakdown.py <作品根> 第N集 scaffold --write
python3 skills/n2d/n2d-script/scripts/production_breakdown.py <作品根> 第N集 check --json --write-missing
```

必填文件：

- `脚本/第N集/production_breakdown.json`：逐镜角色、场景、道具、服装、VFX/overlay、声音、后端风险、部门交接。
- `脚本/第N集/continuity_breakdown.json`：逐镜起止状态、视线、轴线、服化道、持物、知识状态、转场守则。
- `脚本/第N集/ai_call_sheet.md`：AI 拍摄通告单，列生产目标、依赖、拍摄顺序、停审点和后期交接。

检查产物：

- `生产数据/production_breakdown_check_第N集.json`
- `生产数据/production_handoff_pack_第N集.md`

签收口径：三个文件都必须 `status=confirmed`，且不能含 `待补/TODO/TBD` 占位；否则 `run.py next` 在 `image_prompt` 前阻断。

## 5.5 预防式合同口径

新增统一合同：`脚本/第N集/preventive_contracts.json`。它不是“多加几个检测器”，而是在进入下游贵工位前签下可执行承诺：

| gate | 阶段 | 必填 | 缺失时 |
|---|---|---|---|
| `episode_promise_gate` | `script_stage2` 前 | opening hook、promise、obstacle、payoff/progress、cliffhanger | 不进分镜，回 `script_stage1` |
| `shot_intent_gate` | `image_prompt` 前 | 每个 Clip 的 dramatic_function 与 editing_intent | 不生成出图 prompt，回 `script_stage2` |
| `reference_slot_gate` | `image/image_preflight` 前 | 核心角色/道具/场景的 reference_slots 与 identity/lock strategy | 不付费生图，回 `image_prompt` |
| `interaction_physics_gate` | `video_prompt/video_preflight` 前 | 持物、接触、打斗、多人同框、法术特效的动作分解、接触点、站位、降级方案 | 不生成/提交视频 prompt，回 `script_stage2` |
| `audio_timing_gate` | `video_prompt/video/compose` 前 | 对白近景、原生音画、后配音的口型/字幕/声纹/时长策略 | 不进视频或合成，回 `script_stage2` |
| `pilot_release_gate` | `review/release` | 第1集 `pilot_acceptance_第1集.json` 覆盖 face/scene/action/lipsync/seam/routing 且至少 2 个 Clip | `release_verdict` 直接 blocked |

命令：

```bash
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第N集 --stage script_stage2 --write --write-missing --json
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第N集 --stage image_prompt --write --json
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第N集 --stage image --write --json
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第N集 --stage video_prompt --write --json
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第N集 --stage compose --write --json
```

`run.py next` 会自动在对应阶段跑这些 gate。`--write-missing` 只负责脚手架缺失字段，脚手架默认为 `status=draft`，仍然阻断；必须由编剧/导演/制片视角补齐并改为 `status=confirmed`。

## 6. 现有项目迁移

优先顺序：

1. `金睛缉妖录`：第 1 集处于出图前，最适合按 P-1/P-2/P-3 重新打样。
2. `那妖魔是姜大人`：先修复“验收✅但配音⬜”假绿，再补 P-1/P-2/P-3。
3. `仙界闭关小能手`：先迁移 manifest，再补 P-1/P-2/P-3 并重新走验收。

推荐命令：

```bash
python3 skills/n2d/progress.py audit-acceptance '创作区/制漫剧/那妖魔是姜大人' --fix
python3 skills/n2d/_lib/n2d_contract.py migrate-version '创作区/制漫剧/仙界闭关小能手'

python3 skills/n2d/n2d-script/scripts/development_pack.py '创作区/制漫剧/金睛缉妖录' scaffold --write
python3 skills/n2d/n2d-script/scripts/director_blocking_pack.py '创作区/制漫剧/金睛缉妖录' 第1集 scaffold --write
python3 skills/n2d/n2d-script/scripts/production_breakdown.py '创作区/制漫剧/金睛缉妖录' 第1集 scaffold --write
python3 skills/n2d/run.py next '创作区/制漫剧/金睛缉妖录' 第1集 --json
```

## 7. 产品原则

- 不把“能生成”当作“能交付”。
- 不让分镜临场发明导演排戏。
- 不让出图 prompt 临场发明制片拆解。
- 不让验收签收覆盖上游缺口。
- 每个贵工位前都要有可签收的文字、导演、制片、合规和连续性证据。

## 8. 2026-07-03 审查结论

当前“大流程”方向是合理的：从小说先进入专业编剧拆解，再由导演排戏、制片拆解，最后才交给 AI 出图/出视频/合成，这比“小说直接 prompt 成片”更接近真实剧组，也更适合长线角色一致性和平台合规。

但这个流程还不能只靠“阶段顺序”保证质量。实时资料显示，2026 年主流视频模型已经提供更多参考控制：Sora 2 支持角色参考、20 秒片段、扩展和 batch；Veo 3.1 强化了 9:16、音画、first/last frame、ingredients/reference；Kling Elements 用多角度 element 稳定角色/道具/场景；Runway Gen-4 也把世界一致性作为核心卖点。这些能力能加强执行，但不能替代编剧、导演和制片签收；模型仍会漂移、即兴、忘记上游意图，所以 n2d 必须把“创作判断”和“生成执行”拆开，并让每个下游产物反证上游。

实际跑数暴露出的核心问题：

- 进度表会假绿：例如某项目第 1 集 `配音=⬜`，但分镜、素材、字幕和成片已 `✅`。旧的 `audit-acceptance` 只抓 `验收=✅` 假绿，抓不到成片/视频/出图已经越过上游的情况。
- 验收凭据分散：gate、score、ledger、review-ui、image_qc、生成配方、合规各自有状态，但没有一个单点 verdict 能告诉人“能不能交付、只能内部看、只能 demo、还是必须返工”。
- report-only 会被忽略：大量 warn 如果一直停留在报告里，人审只会在看坏图时才发现；低分、核心镜头、生产模式和投放模式下，warn 应自动升级为 block。
- 首集没有强制 pilot：首集应该先用 2-3 个代表镜头验证脸、主场景、动作、口型、接缝和后端路由，再放量整集。
- 人审问题没有系统回流：发现坏图后只改图，容易错过根因。问题必须归因到 `script` / `director_blocking` / `production_breakdown` / `image_prompt` / `backend` / `qc`，再决定回哪一层重修。

## 9. 五项补强落地

### 9.1 Progress DAG Audit

命令：

```bash
python3 skills/n2d/progress.py audit-dag <作品根> --json
```

规则：

- 下游列只要进入 `✅`、`⏳rough`、`partial`、`manual-waived`、`stale`，就必须检查上游依赖。
- `✅` 表示真实完成；`⏳rough` 只在 `先出视频后配音` 的前中段可临时推进，不能让 `成片/验收` 通过。
- `manual-waived` 不等于完成，只能提示待复核；`stale` 直接 block。
- `验收=✅` 仍由 `audit-acceptance` 兜底；DAG audit 负责抓更早的“下游越权完成”。

红灯示例：`配音=⬜` 但 `分镜设计/素材清单/字幕中/成片=✅`，输出 `downstream_started_before_prereq`，退出码 `2`。

### 9.2 Release Verdict Aggregator

命令：

```bash
python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --json
python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --write
```

聚合项：

- `progress_dag`
- 首集 `pilot`
- `compliance`
- `gate_findings_*`
- `score_<集>.json`
- `consistency_ledger_<集>.json`
- `review_ui_<集>.json` 与 `review_ui_findings_<集>.json`
- `image_qc/<集>/image_qc_<集>.json` 的 full 精度与 inputs_fingerprint 新鲜度
- `generation_recipe_manifest_<集>.json`
- `failure_taxonomy`

输出状态：

- `pass`：所有交付证据通过，且不是内部用途限制。
- `blocked`：任一硬性组件 block。
- `demo-only`：无硬 block，但还有 warn，不能正式投放。
- `internal-only`：证据通过但 `distribution_intent=internal_only`，只能内部看。

### 9.3 Report-only Findings 升级策略

命令：

```bash
python3 skills/n2d/scripts/failure_taxonomy.py <作品根> 第N集 --json
python3 skills/n2d/scripts/failure_taxonomy.py <作品根> 第N集 --profile production --write
```

升级规则：

- 核心镜头、主角脸、口型、高潮/开场/结尾等 warn 自动升 block。
- 同一维度连续多次出现，自动升 block。
- score 低或 `status!=pass` 时，相关 report-only warn 自动升 block。
- `--profile production` 下 warn 自动转硬约束。
- 合规意图不是内部/demo 时，warn 自动转硬约束。

归因分类：

- `script`：剧情、动机、因果、台词、伏笔、节奏。
- `director_blocking`：分镜、景别、机位、轴线、调度、动作/视线接缝。
- `production_breakdown`：资产、身份注册、连续性拆解、通告单、生成事件账本。
- `image_prompt`：角色脸、服装、场景、道具、风格、参考图、出图 prompt。
- `backend`：模型路由、seed、口型、音画、Motion Control、后端能力。
- `qc`：score、review-ui、image_qc、指纹新鲜度、校准集。

### 9.4 首集 Pilot 强制签收

命令：

```bash
python3 skills/n2d/run.py pilot <作品根> 第1集 --json
python3 skills/n2d/scripts/pilot_check.py scaffold <作品根> 第1集
python3 skills/n2d/scripts/pilot_check.py check <作品根> 第1集 --json
```

签收文件：

```text
生产数据/pilot_acceptance_第1集.json
```

通过条件：

- 至少 2 个代表镜头，建议 2-3 个。
- coverage 必须覆盖 `face`、`scene`、`action`、`lipsync`、`seam`、`routing`。
- `checks` 中每项必须 `pass/ok/accepted`。
- `status` 必须 `accepted/pass/green`。

`release_verdict.py` 对第 1 集强制检查该文件；缺失或未签收时直接 `blocked`。

### 9.5 人审问题回流

人审不再只写“这张图坏了”。每条问题至少要能回答：

- 坏在什么层：`script` / `director_blocking` / `production_breakdown` / `image_prompt` / `backend` / `qc`。
- 是否核心镜头或连续多次。
- 是否需要回滚上游文件，而不是只重出当前图。
- 修复后要重跑哪些证据：gate、score、ledger、review-ui、image_qc、generation recipe、release verdict。

推荐闭环：

```bash
python3 skills/n2d/scripts/failure_taxonomy.py <作品根> 第N集 --write
python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --write
```

## 10. 新增迁移顺序

现有项目先跑无写入审计：

```bash
python3 skills/n2d/progress.py audit-dag '创作区/制漫剧/那妖魔是姜大人' --json
python3 skills/n2d/scripts/release_verdict.py '创作区/制漫剧/那妖魔是姜大人' 第1集 --json
python3 skills/n2d/scripts/failure_taxonomy.py '创作区/制漫剧/仙界闭关小能手' 第2集 --json
```

处理优先级：

1. 先修 progress DAG 红灯。状态表是调度真相，不能允许下游完成态盖住上游空洞。
2. 再补 `preventive_contracts.json`。没有承诺、逐镜意图、引用槽位、交互物理、音频时长策略，不再进入下游贵工位。
3. 再补首集 pilot。没有 pilot 的项目，不再放量整集。
4. 再修 release verdict 的硬 block：image_qc stale、score 低、review-ui 陈旧、缺生成配方、合规缺字段。
5. 最后按 failure taxonomy 逐层返工，先修 `script/director_blocking/production_breakdown`，再重出 prompt/图/视频，避免只修结果图。

## 11. 八项优化 + 预防式合同的当前落地口径

这些点不再只是原则，已落成可执行护栏：

| 优化点 | 落地位置 | 阻断口径 |
|---|---|---|
| 预防式合同先于检测器 | `skills/n2d/scripts/preventive_contracts.py` + `run.py next` + `gate.py` | `episode_promise_gate`、`shot_intent_gate`、`reference_slot_gate`、`interaction_physics_gate`、`audio_timing_gate`、`pilot_release_gate` 缺任一对应字段即阻断当前阶段 |
| 不只做编剧/导演，补 showrunner/制片/场记层 | `skills/n2d/n2d-script/scripts/production_breakdown.py` + `release_verdict.py` 的 `production_handoff` | `production_breakdown.json`、`continuity_breakdown.json`、`ai_call_sheet.md` 必须 confirmed 且无 `待补/TODO`；否则 release blocked |
| 进度表是 DAG，不是打勾表 | `python3 skills/n2d/progress.py audit-dag <作品根> --json` | 下游列已动而上游非法，退出码 `2`；`⏳rough` 不能放行成片/验收 |
| 首集必须 pilot | `pilot_check.py` + `release_verdict.py` 的 `pilot_release_gate` | 第1集缺 `pilot_acceptance_第1集.json` 或 coverage/checks 未过，release blocked |
| 统一 verdict | `python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --json` | 聚合 DAG、P-3、pilot、合规、gate、score、ledger、review-ui、image_qc、生成配方、新鲜度、taxonomy，输出 `pass/blocked/demo-only/internal-only` |
| report-only 自动升级 | `failure_taxonomy.py` | 核心镜头、重复出现、低分、production、投放意图触发 warn→block |
| 人审问题回流根因层 | `failure_taxonomy.py` 的 `return_plan` | 每类问题带 owner、fix_strategy、rerun_after_fix，不再只修结果图 |
| 生成可复现/可追责 | `generation_recipe_manifest_<集>.json` + `release_verdict.py` 的 `generation_recipe` | 缺 provider/model/channel/route/prompt/reference/seed/cost/event 或资产 hash 不匹配，release blocked |
| QC/发布证据必须新鲜 | `image_qc inputs_fingerprint` + `release_evidence_freshness` | image_qc stale、review-ui 早于 score/ledger、母版晚于 score/ledger/review-ui/配方，release blocked |

推荐每集收尾跑：

```bash
python3 skills/n2d/progress.py audit-dag <作品根> --json
python3 skills/n2d/n2d-script/scripts/production_breakdown.py <作品根> 第N集 check --json
python3 skills/n2d/scripts/failure_taxonomy.py <作品根> 第N集 --write
python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --write
```

如果是第 1 集，还必须先补：

```bash
python3 skills/n2d/run.py pilot <作品根> 第1集 --json
python3 skills/n2d/scripts/pilot_check.py scaffold <作品根> 第1集
python3 skills/n2d/scripts/pilot_check.py check <作品根> 第1集 --json
```

发布判定解释：

- `pass`：可作为交付候选。
- `blocked`：至少一个硬门未过，不能 demo 冒充成片。
- `demo-only`：没有硬 block，但还有 warn，只能内部/样片演示。
- `internal-only`：证据通过但合规意图限制为内部，不得外发/投放。
