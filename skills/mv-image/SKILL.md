---
name: mv-image
description: 制MV 出图 — 按 视觉蓝图 + 分镜/clip_plan.json + identity/asset/reference 注册表，为 MV 生成两层图（共享定妆库[主角/场景] + Clip 首帧/尾帧 PNG）。图片生成拆成具体生图模型 + 访问渠道（默认 GPT Image 2 + Codex），每张正式图记录 model/channel/prompt/reference/asset hash；MV一致性增强支持指定参考图 / 后端主体库 / +LoRA，并拦项目内模型渠道混用与未授权路径. Use when asked to MV出图 / 生成MV画面 / MV分镜图 / MV定妆 / clip首帧. Triggers MV出图, MV画面, MV分镜图, MV定妆, clip首帧, mv-image.
---

# mv-image — 制MV 出图（mv 系列自建）

按 `创作区/制MV/<曲名>/视觉蓝图.md` + `分镜/clip_plan.json`，生成 MV 的画面。**两层架构**：共享层（主角/场景定妆，全曲复用锁一致性）+ Clip 层（每个 clip 的首帧/按需尾帧 PNG）。`生图模型` 与 `生图渠道` 分列（默认 GPT Image 2 + Codex；旧 `生图AI` 只兼容），`MV一致性增强` 在组图前提示指定参考图 / 后端主体库 / +LoRA。正式图必须通过 `record_generation.py` 留 model/channel/prompt/reference/asset SHA-256；image_qc 会拦收据缺失、项目内混用和资产被替换。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`生图模型`、`生图渠道`（旧 `生图AI` 兼容）、`MV一致性增强`、`MV视觉风格`、`重抽预算策略`。

## 作品根
```
创作区/制MV/<曲名>/
├── 视觉蓝图.md         主角/场景/画风 + 段落↔画面映射
├── 分镜/clip_plan.json Clip 首帧/尾帧/prompt 真值源（来自 mv-plan）
├── 分镜/reference_plan.json  每个 clip 的参考输入计划（来自 mv-craft identity_registry.py）
├── 设定/identity_registry.json, asset_registry.json  主角/道具/场景/VFX ID
├── 设定/characters,locations  角色/场景卡（含锚点句）
├── 节拍/beatgrid.json  段落+卡点（来自 mv-beat）
└── 出图/
    ├── common/
    │   ├── prompt/
    │   └── 图片/             共享 PNG 产物（与 prompt/ 平级）
    └── 段落/
        ├── prompt/
        └── 图片/             分段 PNG 产物（与 prompt/ 平级）
```

## 核心原则
- **导演视角八维（分镜图）**：每张分镜 prompt 按导演视角八维装配（**镜头·机位·人物·动作·场景·光影·情绪·画质**），不是画师视角的"好看主角图"——必读 `mv/references/导演视角prompt.md`。MV 最易漏也最关键三维：**②机位**（副歌用大胆机位/荷兰角，别全程正面平视）、**⑥光影**（演出光/色胶/逆光剪影——MV 就活在戏剧光里，别均匀打亮）、**⑦张力**（对齐 beatgrid 段落）。**定妆图是中性档案**（正面/均匀光/无戏），戏剧光只上分镜图。
- **两层 + 锚点一致性**：先出主角/场景**定妆**（共享层），每张分镜 prompt 末尾拼角色卡**锚点句**锁脸锁画风（跨段不漂）。
- **MV 单曲视觉一致性包**：只锁本曲内部的 `lead_identity_anchor / global_style / palette_anchor / section_look / motif_ledger / forbidden_drift`。主角/主唱最严；段落场景可随段落换，但同段落继承光色和场景定妆；特效/转场只锁颜色和形状方向。详细做法见 `references/visual_consistency.md`。
- **身份/资产注册优先**：若存在 `设定/identity_registry.json`、`asset_registry.json`、`分镜/reference_plan.json`，每张图必须按其中的 `lead_id / asset_ids / reference_inputs` 组装 prompt；缺 registry 时先跑 `python3 skills/mv-craft/scripts/identity_registry.py <作品根>`。
- **出图前一致性增强提示**：进入共享定妆或分段组图前，必须提示用户可选 `MV一致性增强=共享定妆+锚点 / 指定参考图 / 后端主体库 / +LoRA`。默认轻量；若用户已有主角/服装/场景参考图或已授权 LoRA，应先登记再生成，不要先批量出图再返工。
- **clip_plan 驱动画面**：按 `分镜/clip_plan.json` 的 `image_prompt_path` / `image_path` / `need_end_frame` 出图；`视觉蓝图` 只提供风格和段落映射，不再让出图阶段临时猜 clip。
- **动作首帧服务 video**：读取 `action_family/action_peak/visual_motif/transition_motif`，首帧要抓动作起幅或关键姿态，不要只做静态美图；副歌高光镜可用更强机位/演出光，但身份锚点不变。
- **卡点意识**：分镜数量/节奏参考 `beatgrid`（副歌密、verse 疏），为 mv-video 的卡点 clip 备料。
- **尾帧接力（仅同段落连续硬切·按需）**：MV 默认卡点硬切，接点靠"视觉身份一致 + 卡点准"。但凡 `clip_plan.json` 标 `need_end_frame=true` 的接缝（同段落·非卡点切·人物姿态连续，如副歌内一段连续动作分两 clip），**除首帧外再出一张尾帧 PNG `出图/段落/图片/Clip_XXX_end.png`，其构图/姿态 = 下一 clip 首帧**——用上一镜 end_state 派生、喂同一套定妆组锁人，供 mv-video 首尾双帧引导焊接点。换段/卡点切不出尾帧（省 credit）。尾帧也按导演视角八维出，只是构图对齐下一首帧。
- **画风统一**：依视觉蓝图 global_style；跨段不跳风。
- **筛选宽容铁律**：候选图**能用就用，尽量不重抽**。轻微偏差（构图小动、表情微差、目光朝向略偏、环境细节小出入）→ 直接通过落档，**不要拖节奏**。只有命中硬伤之一才重抽：① 核心人/物/场景错位 ② 主角脸/画风漂移到识别不出 ③ 违反硬性禁忌（错景别 / 出字幕 logo / 该用演出光却均匀打亮到无戏）。
- **逐图即时 QC（mv 线自维护）**：每生成并落档 1 张共享定妆、Clip 首帧或尾帧 PNG，立刻跑 mv 自己的 `scripts/image_qc.py` 最小可用入口；当前脚本以作品根全量扫描为主，就全量跑一次并重点处理新 PNG 的 finding。`block` 先重抽/修 prompt/换参考，不继续下一张；`review/warn` 必须在 mv 线报告或人工签收中留痕。不得抽成公共实现，也不得复用其它系列的 QC 脚本。
- **重抽预算铁律（两档全局统一）**：`重抽预算策略` 只保留两档，按 `../skills/mv-craft/references/选择点与偏好.md` 读 `_设置.md`→全局默认→首次问一次，**默认=预算充足**。旧值 `预算不足` / `预算不够` 一律归并为 `预算一般`。这里的“满意”以本张图的落档自检 + 用户/制作判断为准，每次重抽都必须记录事件、保留候选或废料，不设固定次数上限：

  | 策略 | 主角 / 副歌高光镜（爽点·副歌·反转·封面候选）| 配角 / 普通段镜 | 终止 |
  |---|---|---|---|
  | **预算充足**（默认）| 严格自检，主角脸/画风零漂移容忍；不满意就继续重抽/改 prompt/换参考，直到满意落档 | 同样严格自检；普通段镜也不将就，直到满意落档 | 满意为止 |
  | **预算一般** | **只关键图片严格自检**；主角/副歌高光/封面候选不满意就继续重抽/改 prompt/换参考，直到满意落档 | 普通段镜走筛选宽容：无核心错位、无主角身份漂移、无硬性禁忌即可落档，不追小瑕疵 | 关键图满意；普通图可用 |

  **关键图片判定**：主角/主唱 CU/ECU/情绪特写、副歌高光、卡点爽点、反转、封面候选、首尾镜、需要尾帧接力的连续动作镜、会被 mv-video 强引用的关键帧。`预算一般` 下非关键普通段镜仍要过硬伤自检，但不因为轻微构图、表情、环境细节偏差反复消耗。
- **生图模型/渠道规则（mv 线自持于 `mv-craft/scripts/contract.py`）**：生成者必须写具体模型版本，访问入口另写渠道；默认 `GPT Image 2 + Codex`。候选包括经官方核验的 `Seedream 5.0 Lite`、`Nano Banana Pro (Gemini 3 Pro Image)`，其它模型走 `自定义` 并先核验。正式一支 MV 默认统一 model+channel；每张图靠收据证明，不靠菜单文案猜。渠道不可用时停下报告，不偷偷切换；逆向、未授权网页自动化仍禁止。

## 一致性增强菜单（出图前提示）

进入共享定妆或分段组图前，必须给用户一句明确提示：**“本次 MV 默认用共享定妆+锚点；如果你有主角/服装/场景参考图、后端主体 ID，或已授权 LoRA，也可以先接入再出图。”** 若用户已有 `_设置.md`，按 `MV一致性增强` 沉默沿用；缺字段则补默认并提示一次。

| 模式 | 何时用 | 必填资料 |
|---|---|---|
| `共享定妆+锚点`（默认） | 一支歌内轻量一致，MV 大多数场景足够 | 角色/场景定妆图、锚点句、global_style |
| `指定参考图` | 用户已有主唱、服装、道具、场景参考图 | 参考图路径、用途标签、授权/来源说明；落 `设定/reference_images/` 或 `出图/共享/图片/` |
| `后端主体库` | Seedream/可灵/Sora 等支持官方主体/角色 ID | 主体/角色 ID、绑定后端、注册素材路径；仍统一一个生图后端 |
| `+LoRA` | 参考图和主体库仍不稳，且用户已有或明确授权 LoRA | `.safetensors` 路径、trigger、base model、许可说明、适用角色/形态 |

`+LoRA` 不是默认项，也不在 mv-image 里自动训练。若用户只说“更稳”，优先建议 `指定参考图` 或 `后端主体库`；只有明确有 LoRA 资产或授权训练结果时才进入 `+LoRA`。

## 工作流
1. 读 `视觉蓝图.md` + `分镜/clip_plan.json`。缺 `clip_plan.json` 时先跑 `mv-plan`，不要在出图阶段临时拆时间线。若项目是 `歌曲输入时序=后配歌曲` 且还没最终 `歌/song.*` / `节拍/beatgrid.json`，只能停在 rough 蓝图，不能正式出图。
2. 跑/读取 `mv-craft/scripts/identity_registry.py` 产物：`设定/identity_registry.json`、`设定/asset_registry.json`、`分镜/reference_plan.json`。prompt 里的身份/道具/场景/参考输入以 registry 为准。
3. 出共享定妆（主角/场景）→ `出图/共享/图片/`，建/复用 `设定/characters|locations` 卡 + 锚点句。若 `MV一致性增强=指定参考图/后端主体库/+LoRA`，先登记参考图、主体 ID 或 LoRA 卡，再生成第一组图。
4. 按 `clip_plan.json` 出首帧 → `出图/段落/图片/Clip_XXX.png`，每张拼锚点句与 `image_prompt_path`。**接力补尾帧**：`need_end_frame=true` 的 clip，额外出 `图片/Clip_XXX_end.png`（=下一 clip 首帧构图）。
5. 筛选（脸/画风一致优先）：每张按 `references/prompt_format.md` 自检栏过——轻微偏差放行，命中硬伤才按 `重抽预算策略` 档位重抽，废图归 `common/废料/`。
6. **逐图生成收据 + 机检**：每张 PNG 落档后先跑 `python3 skills/mv-image/scripts/record_generation.py <作品根> --asset <PNG> --model "<具体模型>" --channel "<访问渠道>" --prompt <prompt.md> [--reference <图> ...] [--subject-id <后端主体ID> ...]`，再跑 `image_qc.py`。正式项目缺 model/channel/prompt/reference/subject/asset 收据、计划要求的真实参考未提交，或图片/prompt/参考图后来被替换，或项目内混用模型渠道，都会被 gate 阻断。
7. **批次/全曲收尾机检**：一批或全曲图出完后再跑一次同命令，确认报告时间晚于所有 PNG，按 `verdict` 决定是否要重抽（见下节）。
8. 回写 `_进度.md` 出图行。下一步先由 `mv-craft` 渲真实 animatic、导出 V1+A1 OTIO 并完成具名 picture lock，再进入 mv-video。

## 作品封面（竖版 key visual · 作品列表卡片用）

作品列表卡片要一张**竖版封面**（约 9:16 / 5:7）+ 一段简介。简介 `synopsis` 在立项时已写进 `_meta.json`；封面走本线独立步骤，产物落 `出图/封面/`（与段落图同规约：`prompt/` 与 `图片/` 分列）。

- **优雅降级（C4/B4）**：纯净机（断网 / 无重依赖 / 无付费凭证）上，封面步骤**只产出稳定的封面 prompt + job 包 + 合规留痕**，`_meta.cover` 保持 `null`，不硬阻断主流程、不伪装云端自动化。
- **生成者到具体模型（C5）**：job 包里「由什么生成这张封面」写**具体生图模型（含版本，默认 GPT Image 2）**；访问渠道（默认 Codex）作为 access path 分列，不当生成者。
- **确定性回填**：真正渲染出竖版 PNG（`出图/封面/图片/cover.png`）并用 `record_generation.py` 留生成收据后，用 `cover_pack.py set-cover` 把 `_meta.cover` 回填为**作品根相对路径**，并回写 `_进度.md` 封面行。`set-cover` 不覆盖用户已设的封面（除非 `--force`）。
- 封面继承共享定妆同源身份锚点与 global_style，不换脸换画风；它属于 `重抽预算策略` 里的**关键图片（封面候选）**，严格自检到满意再落档。

```bash
# 1) 产出封面 prompt/job 包（不调用后端；纯净机也能跑）
python3 skills/mv-image/scripts/cover_pack.py pack <作品根>
# 2) 渲染竖版 PNG → 出图/封面/图片/cover.png，然后留生成收据
python3 skills/mv-image/scripts/record_generation.py <作品根> --asset 出图/封面/图片/cover.png \
  --model "GPT Image 2" --channel "Codex" --prompt 出图/封面/prompt/cover_prompt.md
# 3) 回填 _meta.cover（作品根相对路径）+ _进度.md
python3 skills/mv-image/scripts/cover_pack.py set-cover <作品根>
```

测试：`cd skills/mv-image/scripts && python3 -m pytest test_cover_pack.py`。

## 出图落档机检（image_qc · MV 版）

单主角跨 16-64 个 clip 是脸一致性重灾区——光靠散文规则不够。`scripts/image_qc.py` 把一致性机检**前移到出图落档**（刚出完一批、还没继续的最便宜的点），省下等 `mv-review` 审片才发现的返工。**mv 线自包含**：脸 embedding QC 使用本线独立实现的 insightface/buffalo_l 自标定余弦 flag-band。

**六类检查（确定性 vs 脸栈的边界）**：
| 检查 | 类型 | 依赖 | 严重度 | 做法 |
|---|---|---|---|---|
| 主角脸漂移 `G1` | **脸栈** | insightface/cv2/onnxruntime + buffalo_l | **hard（block=崩脸必重抽）** | 主角共享定妆组内部互相余弦自标定「同人下限」floor，每个 clip 首/尾帧脸 vs 主角主参考落 ok/warn/block。风格化 MV 脸跨图余弦偏低，**不写死阈值**，用本曲定妆组做地板 |
| 主色漂移 `palette` | **确定性** | 仅 Pillow（无需脸栈） | advisory（warn） | 从 `视觉蓝图.md` 抽 `palette_anchor`（`#rrggbb`/`rgb()`/中文色名），每个 clip 首帧主色 vs anchor 取最近距离，超阈值→warn。MV 段落允许加亮/变暗，故只人判不硬拦 |
| 帧级视觉多样性 `dHash` | **确定性** | 仅 Pillow | advisory（warn） | 感知哈希跨 clip 首帧比对：两 clip 首帧 dHash≤10=构图重复（画面撞脸）；某 clip 首↔尾帧 dHash≤10 且时长≥6s=静态长镜（画面不动却拖）。补 `shot_variety_audit` 计划期机检的盲区——计划换了景别但图实际出得一样，只有像素能看出来。MV 筛选宽容+recurring hook 可能刻意，故只 warn 不硬拦 |
| 锚点句落地 lint | **确定性** | 无（纯文本） | demo advisory；**正式项目身份/禁漂块缺失＝hard** | 按 `clip_plan.json` 逐 clip 读其 `image_prompt_path` 指向的 prompt，校验 `visual_consistency` 规定的『身份锚点 / 参考输入 / 视觉锚点 / 禁止漂移』锚点块是否真抄进了 prompt。身份锚点/禁止漂移块是身份合同进入 prompt 的唯一通道：正式项目缺这两块（或 prompt 文件不存在）＝下游未消费身份合同（B12 确定性交接缺口）→ hard；参考/视觉块与 demo 保持 advisory |
| 禁本地贴脸修复 | **确定性** | `生产数据/production_events.jsonl`（存在时） | **hard** | 最新 image 落档事件若记录 `local_face_patch` / facefix / faceswap / alpha_blend / pasteback 等本地身份像素贴回操作，该 PNG 不得进入 mv-video；必须回 mv-image 用真实参考输入重抽 |
| 生成来源链 | **确定性** | `record_generation.py` 事件 | 正式 **hard** | 每个计划首/尾帧绑定具体 model、channel、source prompt/asset SHA-256、真实参考图/后端主体 ID；计划要求的参考未实际提交、换文件、设置不符或 model+channel 混用即回出图 |

> **出图前先跑计划期视觉多样性机检**（最便宜的点，无需出图）：`python3 skills/mv-review/scripts/shot_variety_audit.py <作品根> --write`。它读 `分镜/clip_plan.json` 的 `shot_design`，在花积分前就拦「同构图反复 / 景别单调 / 副歌静镜 / 场景滞留 / 大变化镜头缺参考锚」。gate（image 阶段）会把它的 warn 抬进报告（advisory·不硬拦）。出图后 image_qc 的 `dHash` 再做像素级现实核对。

> **出图前再跑漂移风险预测**：`python3 skills/mv-image/scripts/drift_risk.py <作品根> --write`。不读像素、不花钱：用 clip_plan + identity_registry 的高危信号（近景占比/大表情/极端角度/逆光暗部/换装/长间隔复现/多主体同框/缺参考锚 + 主角定妆组基础分）逐 clip 打 high/medium/low，high 风险镜**出图前**挂定妆/表情/场景参考、优先进 `mv-plan/scripts/pilot_matrix.py` 打样。image_qc 已实测出脸警的 clip 自动回灌升 high（既成事实非预测；脸检降级模式下不臆造回灌）。写 `生产数据/drift_risk/drift_risk.{json,md}`，report-only（最高 warn），被 gate（image/video_jobs）与 `consistency_findings` 消费。

**优雅降级（绝不静默报通过）**：缺 insightface → 脸检降级 Pillow（只验 图损坏/分辨率/清晰度，不臆造相似度）；更缺 Pillow → 整项跳过交人判；缺 `palette_anchor` / `clip_plan.json` → 对应检查跳过并记 note。报告写 `qc_environment.precision_level=full|degraded|none`，degraded/none 时提示先补依赖再进 mv-video。

**CLI**：
```bash
python3 skills/mv-image/scripts/image_qc.py <作品根>              # 跑全部，打印报告路径
python3 skills/mv-image/scripts/image_qc.py <作品根> --json       # 机器可读 payload
python3 skills/mv-image/scripts/image_qc.py <作品根> --findings   # mv-review/gate 同形 findings
python3 skills/mv-image/scripts/image_qc.py <作品根> --regen-list # 「要重抽」的 clip（只脸 block，主色/锚点 warn 不进）
python3 skills/mv-image/scripts/image_qc.py <作品根> --strict     # 严审刷新：block/warn/降级都进候选重出清单
python3 skills/mv-image/scripts/image_qc.py <作品根> --no-pixel   # 只跑锚点 lint（无 Pillow/insightface 时）
# 可调：--margin 0.08（脸 flag-band 缓冲）、--palette-threshold 110（主色最近距离阈值）
```

**JSON schema**（落 `生产数据/image_qc/image_qc.json`(+`.md`)）：在原 face/palette/lint/local-patch 字段外，含 `generation_provenance:{expected_model,expected_channel,uniform,complete,rows[]}`（正式 gate 要求 `complete=true`）和 `assets_sha256:{<图片相对路径>: <内容 SHA-256>}`——gate 用后者做 **hash 级新鲜度核对**（图片重生成 → hash 变 → 报告过期），取代按 mtime 判过期（mtime 会被恢复旧图/跨机复制骗过）。

**seed/参数留痕**：`record_generation.py` 支持 `--seed <种子>`、`--param K=V`（可重复）、`--provider-job-id`——登记时已知则必记（复现/微调/审计用）；网页入口拿不到时可缺省，不阻断。

**落档判定（MV 筛选宽容铁律）**：`verdict=block`（主角脸崩/图损坏/禁用本地贴脸产物）→ 必须重抽后重跑；`verdict=review`（只有主色/锚点初筛或视觉降级）→ 先处理报告建议；`verdict=ok` → 放行。`mv-craft gate --stage video_jobs` 会强制读取本报告：缺报告、hard block、`precision_level!=full`、图片晚于 QC 报告都会挡住正式出视频。若确需降级/人审放行，用 `image_qc.py <作品根> --accept-degraded --reviewer <name> --notes <复核说明>` 写**具名 + 绑定报告 hash** 的 `manual_review` 留痕（报告一重跑绑定即失效，需重新放行；旧式裸布尔 `manual_review_accepted` 不再被 gate 接受——无法证明复核对应当前报告）。脚本退出码恒 0，是否阻断由 gate 消费报告决定。

**定妆组离群自检（G1 地基保护 · advisory）**：脸检 floor 由主角定妆组自标定（取组内最小相似度），一张漂了的定妆图会悄悄拉低地板、放松整套脸检。`run_face_check` 现在把每个定妆变体 vs 主参考的相似度落 `intra_by_variant`，显著低于组内最高值（差距 > 0.20）的变体报 `costume_outliers`（advisory warn）——人工确认后若真漂了，重抽该定妆再重跑，floor 随之回升。

测试：`cd skills/mv-image/scripts && python3 -m pytest test_image_qc.py`（CI-safe，走纯函数/降级路径/fixtures，不需要实跑脸栈）。

## 详细参考
- 导演视角八维 prompt 装配（画师→导演升级·MV版）：`mv/references/导演视角prompt.md`
- prompt 两层格式 + 锚点句 + 段落映射：`references/prompt_format.md`
- MV 单曲视觉一致性包（身份锚点/主色/母题/段落 look）：`references/visual_consistency.md`

## 常见错误
| 错误 | 纠正 |
|---|---|
| 分镜写成"好看主角图"（画师视角）| 按导演视角八维装配，补齐机位/光影/张力，见 `导演视角prompt.md` |
| 全程正面平视 + 均匀打亮 | 机位即能量（副歌大胆机位）、光影是 MV 灵魂（演出光/色胶/逆光） |
| 给定妆图也打浓光/色胶 | 定妆=中性档案，戏剧光只上分镜图，否则污染下游参考 |
| 不出定妆直接分镜 | 先共享定妆 + 锚点句，跨段才不漂 |
| 有参考图/LoRA 却没在组图前提示用户接入 | 进入共享定妆或分段组图前提示 `MV一致性增强` 四档；用户选择后先登记资产，再批量出图 |
| 副歌为了炫直接换脸/换服装轮廓/换画风 | 违 MV 单曲一致性包；副歌只增强光效、机位、动作和特效，不换身份锚点 |
| 跨段画风跳变 | 统一 global_style + 同一生图工具(同一集不换) |
| 分镜不看段落/卡点 | 按视觉蓝图段落 + beatgrid 疏密出图 |
| 跳过 mv-plan 直接按感觉出图 | 先跑 mv-plan，按 `clip_plan.json` 的 prompt/path 出首帧 |
| 跳过逐图 image_qc 就进 mv-video | `mv-craft gate --stage video_jobs` 会挡住；每张首/尾帧落档后先跑 `mv-image/scripts/image_qc.py`，批后再收尾跑一次，并处理 hard/degraded |
| 用本地贴脸/换脸修复让 embedding 过关 | 禁用。应回 mv-image 用共享定妆/参考输入/后端主体库真实重抽，不能把身份像素贴回最终帧 |
| 后配歌曲未补最终歌就出图 | 先补成品歌、跑 mv-beat 和正式 mv-plan；rough 蓝图不生成正式图 |
| clip_plan 标了 `need_end_frame` 却只出首帧 | 同段落连续硬切接缝补尾帧 PNG `Clip_XXX_end.png`（=下一首帧构图），供 mv-video 首尾双帧锁接点 |
| 候选图轻微偏差就喊重抽 | 违筛选宽容铁律——只对核心错位/脸·画风漂移/硬性禁忌才重抽 |
| 一张图反复重抽烧 credit | 先确认 `重抽预算策略`：预算充足允许出到满意；预算一般只对关键图片严格抽到满意，普通图无硬伤就收 |
| 把"预算一般"当成所有图都随便过 | 预算一般不是不审图；关键图严格自检直到满意，普通图也必须无核心错位、无主角身份漂移、无硬性禁忌 |
| 看到 `dreamina` 就直接用即梦逆向出图 | 违反安全 invariant——禁即梦/Dreamina 逆向 CLI/web 出图（官方 Seedream API 可用，≠ 即梦逆向）；即梦可用于出视频 |
| 这个 clip 用 Codex、那个用 Seedream | 后端混用是跨 clip 漂移真凶——一支 MV 统一一个官方后端 |
