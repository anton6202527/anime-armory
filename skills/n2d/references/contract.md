# n2d 机器契约

本文件是给人读的说明；脚本真值源在 `skills/n2d/_lib/n2d_contract.py`。原 `skills/common/` 公共层已删除，不存在兼容 shim；任何阶段、列名、gate、manifest 字段变更，都先改 `_lib/` 里的 contract，再让 SKILL.md 和脚本复述它。

## 1. 进度表 schema

`<作品根>/_进度.md` 是全作品进度 single source of truth。当前标准列：

```markdown
| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |
```

机器语义：

| 单元格 | 状态 |
|---|---|
| `✅` | 完成；在 `配音` 列只代表真实配音已可作为定稿输入 |
| `⬜` / 空 | 未开始 |
| `⏳rough` | 前期时间基准已建立，不是最终声音。新默认通常对应 `timing_estimate.json`（`audio_generated=false`）；旧项目也可能是占位轨。能推进哪些镜头由逐镜 route 决定 |
| `N/M` | 部分完成；仅 `N >= M` 算完成 |
| `—` / `N/A` / `无` | 本集不适用，路由视为已满足 |

`raw` 是源文本展示列，不计入生产完成度。`成片` / `验收` 是默认交付尾段：`合成阶段=启用` 时，`视频` 完成后继续路由到 compose/review/readiness，最终通过人工签收后才形成 `master_delivery_complete`。只有显式 `合成阶段=跳过` 才以 `clip_delivery_complete` 结束，它不是可发布母版。

### 收敛合同

- **一个执行状态**：`_进度.md` 是持久阶段记录，`run.py next --json` 给出的当前 `frontier.stage_key` 是任务准入的唯一裁决。queue、dashboard、manifest 都是派生视图；排队不等于准入，更不等于付款授权。即使有人手写整行 `✅`，terminal 仍会重验当前 verdict + acceptance receipt；证据缺失或过期时只能回到 review，不能返回 `done`。
- **一个内容哈希**：正式边界统一使用 `n2d_content_fingerprint`。它把全部直接输入、glob 展开结果、缺失输入、路由、模型/渠道、能力档和引用素材规范化后计算一个 SHA；生产收据必须保存可重算的明细，不能只记文件名或 mtime。release hash 还消费经过 schema、来源 SHA 与当前内容重验的事件审计和正式制品报告，并只投影目标集依赖；时间戳、mtime 等非语义字段不进入完成哈希。哈希不相等时旧 prompt、图片、视频或回执均不可复用。
- **一个阶段预算信封**：v2 envelope 精确绑定当前 frontier 的 line/project/stage/scope、具体 model/channel、canonical producer input SHA、expiry、max_calls、唯一 `phase_retry_round` 和 cost ceiling；真实 `approver + approval_reference + source_quote` 全部纳入摘要，agent/delegate/auto 不能冒充。`run.py`/supervisor 只对 fresh route task 和当前 fingerprint 做只读 probe，匹配且有余量才返回 authorized `needs_stage_execution`；只有 exact `n2d-batch` runner 能原子 consume，不能 issue/扩大。成本未知、超额、过期或任一绑定变化都回 `needs_payment_confirm`，v1 task/attempt authorization 继续兼容。
- **一个可恢复消费语义**：首次 v2 consume 写 `in_flight`；同 consumption ID 重入或任何 unresolved reservation 都禁止 provider 重提，账本幂等不等于 provider 可重放。只有原 submit/query 的持久 completion evidence，或 runner 成功且 paid-boundary/output/gate evidence 全部通过，才能 finalize。首次安全本地 compose 只有在 `BGM来源=无` 且 canonical master 不存在时免 envelope；已有 working/未验收/已验收 master、损坏收据或 resolver 不确定都按不可逆覆盖 fail-closed。
- **一个 worker 完成定义**：batch task 只有依次达到 `command_succeeded → artifact_verified → gate_passed` 才能提交为 `done`；真正花钱前 producer 必须现场重算并匹配授权 expectation，落 paid-boundary receipt；提交锁内再对当前产物逐个做存在性、SHA 与解码重验，生成唯一 `n2d_batch_completion_commit.digest`。runner 状态/exit code/执行边界相互矛盾、产物在 verify 后漂移、commit 被改写或 post gate 阻断时都不能成为 `done`；进入 `qa_blocked` 并按是否已越过付费边界结算预算，dry-run 只读且不 claim、不回写。
- **一个整集完成定义**：`master_delivery_complete = acceptable canonical release_verdict + fresh canonical acceptance_receipt`。receipt 只接受显式传入的当前 reviewer 与 `approved/accepted`，并绑定统一 resolver 选出的 canonical 母版、verdict、score、ledger、review-ui/findings 的当前 SHA；复核时会重新用 ffprobe 验证母版可播放及真实时长。事件链审计与 release-scope、strict、completion-input artifact validation 是 verdict required component，必须携带 kind/version/root/source/content 证据并与当前目标集制品相符；裸 `{status: pass}` 无效。旧 `review_signoff` 只作迁移诊断，绝不能继承 reviewer/decision 来签新母版；advisory/rejected/已删除或哈希过期的签收一律不能证明完成。
- **一个派生内容图**：`episode_graph_第N集.json` v2 给每个节点写局部 `content_sha256`，再把依赖节点 hash 传播为 `lineage_sha256`；逐 Clip root、整集 `artifact_root_sha256` 和 `change_set` 只用于判断最小失效/返工范围。它不是第二个内容指纹或状态：正式提交/复用仍绑定上面的 canonical `n2d_content_fingerprint`，整集完成仍只认 release verdict + acceptance receipt。
- **一个母版色彩语义**：`设定库/color_pipeline.json` 是交付色彩合同；默认 Rec.709 SDR，compose 显式写 primaries/transfer/matrix/range/pixel format，review 对 canonical master 用 ffprobe 重验。`series_grade` 管创作调色，不能替代编码标签；C2PA/AI provenance 的文件存在也不能替代对当前母版 SHA 的验证 receipt。

## 2. 阶段图

阶段顺序由 `n2d_contract.STAGE_GRAPH` 定义：

| key | label | owner | progress columns | gate | 回退目标 |
|---|---|---|---|---|---|
| `source` | 源文本落档 | `n2d-script` | `raw` | - | `source` |
| `script_stage1` | 阶段1·剧本改编 | `n2d-script` | `剧本改编 / bgm / 封面` | - | `script_stage1` |
| `voice` | 角色配音 | `n2d-voice` | `配音` | - | `voice` |
| `script_stage2` | 阶段2·分镜设计 | `n2d-script` | `分镜设计 / 素材清单 / 字幕中 / 字幕英` | - | `script_stage2` |
| `image_prompt` | 出图prompt | `n2d-image` | `出图prompt` | `image_preflight` | `image_prompt` |
| `image` | 出图 | `n2d-image` | `出图` | `image` | `image` |
| `video_prompt` | 视频prompt | `n2d-video` | `视频prompt` | `video_preflight` | `video_prompt` |
| `video` | 图生视频 | `n2d-video` | `视频` | `video` | `video` |
| `compose` | 合成成片（默认交付尾段） | `n2d-compose` | `成片` | `compose` | `compose` |
| `review` | 审查验收（默认最终尾段） | `n2d-review` | `验收` | `review` | `review` |

`skills/n2d/_lib/n2d_route.py` 从这张表派生旧的 `STAGES` 路由元组，供 `n2d/progress.py` 和 `n2d-progress/scan.py` 复用。不要再在别处手写另一张阶段表。`compose`/`review` 默认参与前沿；只有项目显式设 `合成阶段=跳过` 且本集未开始成片/验收时才裁掉尾段。

`source` 阶段除 `脚本/第N集/raw.txt` 外，还会由 `split_novel.py` 自动落 P-1 开发包草稿：`开发包/series_bible.md`、`adaptation_strategy.json`、`season_arc.json`、`production_feasibility.json`、`pilot_greenlight.md`。这些文件不新增 `_进度.md` 列；它们由 `run.py` 在 `script_stage1` 前置 `development_pack` gate 校验，必须全部 `confirmed` 后才进入正式剧本改编。

`script_stage2` 前先有 table read 围读包，不新增 `_进度.md` 列：`脚本/第N集/table_read_packet.json`、`table_read_packet.md`。这些文件由 `run.py` 在 `script_stage2` 前置 `story_acceptance_packets --kind table_read` gate 校验，必须 `confirmed` 后才进入 P-2；检查结果落 `生产数据/story_acceptance_packets_check_table_read_第N集.json`。

`script_stage2` 前还有一层 P-2 导演排戏包，不新增 `_进度.md` 列：`脚本/第N集/director_beat_sheet.json`、`axis_blocking_map.json`、`shot_progression_plan.json`、`transition_map.json`、`vertical_composition_plan.json`、`edit_rhythm_map.json`。这些文件由 `run.py` 在 `script_stage2` 前置 `director_blocking_pack` gate 校验，必须全部 `confirmed` 后才进入正式分镜；汇总说明落 `生产数据/director_blocking_pack_第N集.md`，检查结果落 `生产数据/director_blocking_pack_check_第N集.json`。

`image_prompt` 前先有 executable animatic 粗剪包，不新增 `_进度.md` 列：`脚本/第N集/animatic_packet.json`、`animatic_packet.md`、`生产数据/animatic_第N集.json`、`生产数据/animatic_第N集.html`。这些文件由 `run.py` 在 `image_prompt` 前置 `story_acceptance_packets --kind animatic` gate 校验；packet 必须 `confirmed`，timed HTML/JSON 必须能由 `storyboard.json` + `镜头时长.json` 生成后才进入 P-3；检查结果落 `生产数据/story_acceptance_packets_check_animatic_第N集.json`。

`image_prompt` 前还有一层 P-3 制片拆解包，不新增 `_进度.md` 列：`脚本/第N集/production_breakdown.json`、`continuity_breakdown.json`、`continuity_bible.json`、`ai_shooting_schedule.json`、`ai_call_sheet.md`、`生产数据/ai_shooting_schedule_batch_seed_第N集.json/md`。这些文件由 `run.py` 在 `image_prompt` 前置 `production_breakdown` gate 校验，必须全部 `confirmed` 且无 `待补/TODO` 后才进入出图 prompt；汇总说明落 `生产数据/production_handoff_pack_第N集.md`，检查结果落 `生产数据/production_breakdown_check_第N集.json`。batch seed 是 `n2d-batch queue.py plan --from-shooting-schedule` 的输入，把 AI 拍摄排期转换成 image/video 队列任务草案。

`review/release` 前不再只看最终 MP4。`run.py` 会先刷新 `final_timeline_probe.py --write` 和 `script_supervisor_log.py check --write-missing`：前者落 `生产数据/final_timeline_probe_第N集.json`、`生产数据/timelines/第N集/timeline.json`、`生产数据/views/rough_cut_preview_第N集.html`，形成 rough cut lock；后者落 `生产数据/script_supervisor_log_第N集.jsonl` 与摘要，要求 storyboard 每个 Clip 都能对到 accepted take 和真实资产。`production_locks.py` 按层检查 `video_material_lock`、`rough_cut_lock`、`picture_lock`；锁版后若出现缺失/陈旧/waiver/QC 降级，`creative_governance.py` 会强制 `生产数据/creative_decision_log.jsonl` 中存在 production-ready 决策账，再允许继续 release/readiness。

## 3. 制作模式

`_设置.md` 的 `制作模式` 是状态机变体，而不是散落规则：

| 模式 | 语义 |
|---|---|
| `混合自动路由` | **默认**（2026-07-10 起）。项目先锁声音选角与无 WAV 时间基准，再逐镜路由到表演音轨先行、基础视频后置口型、旁白/口外音后配、画面先行或原生音画；最终配音在音色定妆后生成。 |
| `配音先行` | 显式强控制/兼容模式。整项目真实配音先出，实测时长驱动分镜、出图和视频。 |
| `原生音画` | native AV 模式：说话镜由支持原生同步音画的后端一次生成台词+口型+环境声，主流程不把 `配音` 列作为硬依赖；配音层只用于旁白/系统音或单镜回退。最快看到出图/出视频，但少逐句音色控制。仿真人音色授权仍由 compliance gate 管。 |
| `先出视频后配音` | 显式整项目画面先行模式。用无 WAV 估时锁大致槽位，视频出齐后补真实配音；合成前若 final voice 缺失，路由会拦回 `n2d-voice`。 |

模式感知规则：

- `混合自动路由`：`配音=⏳rough` 表示 no-audio timing 就绪。旁白/画外音、动作、空镜等可继续；口型可见对白必须有获批表演轨，或只生成 neutral-mouth base plate 并在最终交付前完成独立 lipsync。成片所需 final voice 未齐时，compose/review 阻断。
- `配音先行`：`配音=⏳rough` 只算“已尝试”，不算满足；image/video gate 会阻断占位配音。
- `先出视频后配音`：`配音=⏳rough` 可满足分镜、出图、出视频的时间脚手架依赖；优先使用无 WAV `timing_estimate.json`。合成前必须补真实配音。
- `原生音画`：`配音` 对主流程视作可选旁白层；分镜时长来自 `storyboard.json clips[].duration`，compose 默认保留 clip 原生音轨，避免丢台词。

## 4. 每集 manifest

每集写 `脚本/第N集/manifest.json`。`progress.py set` 会在阶段回写时自动刷新；也可手动重建：

```json
{
  "kind": "n2d_episode_manifest",
  "schema_version": 2,
  "episode": "第1集",
  "stage": "all",
  "production_mode": "混合自动路由",
  "artifacts": [
    {
      "stage": "script_stage2",
      "path": "脚本/第1集/storyboard.json",
      "exists": true,
      "kind": "file",
      "sha256": "..."
    }
  ]
}
```

```bash
python3 skills/n2d/manifest.py <作品根> 第N集
python3 skills/n2d/manifest.py <作品根> 第N集 --stage video
```

manifest 是产物快照，不负责生成媒体。阶段脚本收尾时可以调用它，让后续 review/返工知道某一集当时依赖了哪些文件。

## 5. Gate 回滚输出

高风险阶段统一走：

```bash
python3 skills/n2d/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image_preflight|video_preflight|image|video|compose|review
python3 skills/n2d/n2d-review/scripts/gate.py <作品根> 第N集 --stage video --json  # 调试/机器消费入口
```

默认调用顺序：正式生图前跑 `image_preflight`，生图落档后跑 `image`；正式出视频前跑 `video_preflight`，MP4 落档后跑 `video`。preflight 与对应阶段复用同一套结构/合规/继承检查，但 findings、事件日志和 `gate_findings_<stage>_第N集.json` 分开落盘，便于定位“花钱前拦截”还是“生成后回验”。

JSON 输出保留旧字段：

```json
{"sev":"block","dim":"prompt","loc":"...","msg":"..."}
```

并追加结构化返工字段：

```json
{
  "return_to_stage": "video_prompt",
  "rerun_scope": "先修尾帧、视频 prompt、导演一致性契约或缺失 PNG，再重跑 video_preflight；未过 gate 不出视频。",
  "affected_artifacts": ["脚本/第N集/storyboard.json", "出视频/第N集/prompt", "出视频/第N集/视频"]
}
```

后续自动化只读这些字段做最小重跑范围；人类报告仍读 `msg`。

## 6. 跨阶段契约字段

`storyboard.json` 是分镜设计后的机器契约源：

- `visual_contract` 必含：`色调基线 / 场景光位锚 / 场景轴线视线 / 角色状态演进 / 景别阶梯`
- `style_contract` 必含：`风格名 / 视觉基调 / 镜头与构图 / 光色策略 / 运动边界 / 风格禁忌`
- 旧项目 `cinematic_contract` 兼容通过：`摄影基调 / 镜头焦段 / 光源动机 / 色彩策略 / 运镜边界 / 真实感禁忌`
- 每个 `clips[]` 的 `continuity` 必含：`start_state / action / end_state / constraints / negative / transition`
- 每个非末镜 outgoing seam 必须显式写 `seam_mode + seam_evidence`。只有 `continuous_take_relay` 写 `need_endframe=true` 并要求同一边界帧；非 relay 的镜内尾锚写 `end_anchor_required=true`

出图、出视频、review 都只能继承这些字段并细化，不能各自另写一套真值。

`style_contract` 的目标是把用户选择的基础视觉风格从形容词变成生产约束。风格由 `_设置.md` 的 `基础视觉风格` 与 `设定库/global_style.md` 派生，不由 skill 正文写死：

```json
{
  "style_contract": {
    "风格名": "国漫写实",
    "视觉基调": "东方幻想国漫，角色比例略理想化，场景和服装材质写实，高细节但不照片化",
    "镜头与构图": "保留影视景别和轴线；可用更强剪影、广角压迫和法术特写，但不随机变透视",
    "光色策略": "青灰为主，烛火金只在情绪转折处强调；强光来自月光、烛火、符阵或兵器反光",
    "运动边界": "慢推、固定、跟摇为主；爽点可短促环绕或轻甩，禁止无理由飞行镜头",
    "风格禁忌": ["欧美脸漂移", "页游塑料盔甲", "随机霓虹", "过度磨皮", "背景像贴图", "低幼Q版"]
  }
}
```

markdown 层新产物继承标题固定为「本集基础视觉风格契约」。`gate.py --stage image_preflight|video_preflight|image|video` 会阻断 storyboard 缺 `style_contract`、出图总览缺「本集基础视觉风格契约」、出视频总览缺「本集基础视觉风格契约」。旧标题「本集真实电影感契约」只作兼容。

## 7. 契约治理：invariant vs contested（阶段0）

契约是双刃剑——它让管线稳，也会**把仍在争论的设计决策硬化成既成事实**，给它们虚假权威、抬高演进成本。治理原则（见 `docs/n2d-原则变更提案-契约治理与一致性占位.md` 提案一）：

- **每个契约项分两类**：`invariant`（已定不变量，可硬化进 BLOCK gate / "必须"措辞）vs `contested`（待决原则，**只能进 choice point，不得新增 BLOCK / "只能·不可选"措辞**）。
- **真值源**：`skills/n2d/_lib/n2d_contract.py` 的 `CONTESTED`（当前标注，**零消费·零行为变化**）+ `INVARIANT_NOTE`。
- **当前 contested 三项**：① 生图后端垄断（“图必须 Codex”）② 是否把某类镜头强制成统一音画顺序（默认已收敛为 `混合自动路由`，逐镜证据决定，不生成整集占位 WAV）③ 基础视觉风格（默认预选为 `冷灰写实3D国风漫剧`，但必须 derive from `基础视觉风格` + `global_style.md`）。其中③已落地为选择点 + `style_contract`；旧 `cinematic_contract` 兼容。

## 8. 版本治理：bump 必带迁移

`CONTRACT_VERSION` 现为 **2**。`style_contract` 是向后兼容新增字段：gate 仍接受旧 `cinematic_contract`，所以本次不 bump schema；下次触碰旧故事板/总览时顺手迁到 `style_contract`。

原则：`CONTRACT_VERSION` 每升一级须配 `migrate_v{N}_to_v{N+1}(work_root)`，路由/进度脚本检测 `schema_version` 落后即提示。维护入口：

```bash
python3 skills/n2d/_lib/n2d_contract.py check-version <作品根>
python3 skills/n2d/_lib/n2d_contract.py migrate-version <作品根> [--dry-run]
```

当前脚手架已提供 `v1 -> v2` 的安全迁移：刷新每集 `脚本/第N集/manifest.json` 到当前 schema，并生成 `生产数据/contract_migration_report.json`；故事板字段仍按向后兼容策略由下次阶段重跑时自然升级。**版本号不配迁移函数等于没版本号**。
