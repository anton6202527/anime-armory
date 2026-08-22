# mv-video jobs manifest + 卡点定时长 + 运镜映射

## 真值源
- `分镜/clip_plan.json`：clip 时长、首帧路径、尾帧需求、转场、continuity 的源头，由 `mv-plan` 生成。
- `出视频/jobs_manifest.json`：每个 clip 跑几版、prompt 文件、已登记 take、评分、selected_take 的源头，由 `scripts/video_jobs.py` 生成/维护。
- `分镜/timeline_manifest.json`：最终合成顺序和 selected video 路径，由 `mv-plan` 创建、`video_jobs.py --select` 同步。
- `mv-video/references/action_knowledge.md`：动作家族、动作峰值、转场母题的知识库。`clip_plan.json` 中的 `action_family/action_peak/visual_motif/transition_motif` 应从这里选，不临场泛写“炫酷”。
- `mv/references/运镜/manifest.json`：运镜机器真值源。`clip_plan.json.shot_design.camera_movement` 和视频 prompt 的 `镜头运动` 应从这里选结构化词，并补速度、方向、起幅、落幅；视觉校准优先看本地五帧 contact sheet，需要完整动态节奏时才用 `skills/mv/scripts/camera_reference.py fetch` 按需下载。

## clip 任务格式（按 clip_plan + beatgrid 规划）
```markdown
## Clip_001（段落 chorus · 时长 1.6s · @0:48-0:49.6）
**首帧**：出图/段落/图片/Clip_001.png
**尾帧**（`need_end_frame=true` 时必用，平台支持双帧走 frames2video）：出图/段落/图片/Clip_001_end.png（mv-image 出的尾帧=下一 clip 首帧构图）
**卡点**：起 0:48(downbeat) → 止 0:49.6(下一downbeat)
**歌词/情绪钩子**：{本 clip 对应歌词词组 / 情绪点 / 爽点}
**转场**：{动作切 / 视线切 / 闪白 / 遮挡擦镜 / 光效切 / 硬切 / 空镜缓冲}
**动作家族**：{performance_pose / expressive_walk / dance_hit / dance_sharp / dance_fluid / dance_street / performance_vocal / camera_whip / orbit_reveal / prop_sync / vfx_burst / environment_motion / mirror_split / silhouette_action}
**力量等级**：{Level 1-10}
**动作峰值**：{对齐 beat/downbeat 的秒点，或相对于 clip 开始的秒点，如 0.8s (relative)}
**空间/轴线锁**：{视线看向镜头 / 运动方向画左至画右 / 保持双脚接触地面}
**视觉母题**：{主角身份锚点 / 主色 / 本段反复符号}
**转场母题**：{闪白 / 遮挡擦镜 / whip pan / match action / match color / particle bridge / mirror fracture / shadow cut}
**need_end_frame**：true/false。
**continuity**：
- start_state：直接抄上一 clip 的 `end_state`
- action：{人物动作 + 力量等级}
- end_state：{给下一 clip 承接的结尾姿态}
- constraints：{角色定妆、服装发型、主色调、空间轴线锁}
- negative：{不要换脸、不要换衣、不要瞬移、不要生成文字/logo、不要生成原生人声}
### 完整生产合同（供 gate / 人工复核，不可整段提交）
continuity:
  start_state: {start_state}
  action: {action}
  end_state: {end_state}
  constraints: {constraints}
  negative: {negative}
人物运动：{动作链}；动作家族：{action_family}；力量等级：{energy_level}；表情；
镜头运动：{从 mv/references/运镜/manifest.json 选结构化词，如快速推镜头/环绕/甩镜/冲击变焦 + 速度/方向/起止}；
空间/轴线锁：{eyeline_lock / movement_vector}；
动态细节：发丝、衣摆、光斑或环境粒子随动作幅度产生物理惯性偏移；
卡点约束：动作峰值/击中点对齐 {action_peak_relative}；
转场母题：{transition_motif}；
衔接约束：开头承接 continuity.start_state，只执行 continuity.action，保持 continuity.constraints，避开 continuity.negative；
声音约束：clip 只生成画面；成片歌曲在合成阶段铺设；演唱口型音频只作条件，不替换歌曲；

### 后端编译提交 prompt
**编译元数据**：kind=mv_compiled_video_prompt; version=2; profile_version=...; profile=...; backend=...; mode=...; language=...; native_audio_policy=external_song_track; planned_request_controls_sha256=...; compiled_request_controls_sha256=...; source_contract_sha256=...
```text
{由 skills/mv/_lib/mv_video_prompt_compiler.py 生成的唯一提交文本：人物主动作 + 运镜 + 明确环境响应 + 卡点 + 落幅 + 最短身份保持；不得含身份注册表、歌词、资产路径、渠道/规格说明或审计文字}
```

### 后端负向字段（profile 支持时单独提交）
```text
{换脸、换衣、新增人物、文字/水印等；Runway profile 不提交负向命令}
```

### 平台参数：模型/时长/帧率/画幅/**分辨率·帧率·质量档(由 出视频规格 档定)**/image2video 强度
```

> **分辨率/帧率/质量档/跑几版由 `出视频规格` 三档预算统一决定**（见 SKILL「出视频规格」节）：预算充足=1080p·30fps·高质量档·多跑挑稳，预算一般（默认）=720p·24-30fps·标准档·关键镜2版/普通镜1版，预算不够=720p·24fps·省积分档·全1版。缺失时自动写回推荐档；当前档记录进任务包，不逐调用询问。实际 submit 由调用层核对精确绑定且有效的阶段预算包。CLI 调用据此加 `--resolution`/`--fps`（flag 名以平台为准）。

`video_jobs.py` 写 schema v4 manifest：每个 take 除 `prompt_path` 外还持有具体 model×channel/provider route、`prompt_source_kind=compiled_submit_prompt`、compiler/profile 元数据、`submit_prompt`、独立负向字段、完整 `planned_request_controls` / `compiled_request_controls`、双 controls SHA、`source_contract_sha256` 与 `submit_prompt_sha256`。manifest 的 freshness snapshot 同时绑定 `_设置.md`、plan、image QC、compiler/capability graph、逐 take prompt 和真实参考文件 SHA。提交端只读 compiled 结构化字段；人工网页操作也必须按 receipt 逐 role 确认实际所用控制和参考。

provider 仅支持离散/最短生成时长时，`planned_request_controls.duration_seconds` 仍是 picture lock，`compiled_request_controls.duration_seconds` 可按能力图上调，并以 `adaptations.kind=provider_duration_then_trim_to_picture_lock` 明示；生成后先静音、裁到计划时长再登记，不改 timeline、不用变速掩盖。

## Gemini Omni Flash Preview 候选边界（采集 2026-08-20）

- 官方模型 ID：`gemini-omni-flash-preview`；官方状态：`preview`；已知入口：Gemini `v1beta/interactions`。依据：[Omni 官方文档](https://ai.google.dev/gemini-api/docs/omni)（页面更新 2026-07-30）、[Gemini 视频总览](https://ai.google.dev/gemini-api/docs/video)（页面更新 2026-06-30）。
- 官方已展示 text-to-video、image-to-video、多张 subject reference、`reference_to_video`/`edit` task、16:9/9:16 与默认生成音轨；同时明确当前不支持上传音频参考、首尾帧插值/视频延展，视频参考处理也有限制。
- 官方页面没有给出足以固定全局 `duration_seconds` / `fps` / `resolutions` 的稳定执行矩阵，也没有声明原生音轨的 API 关闭参数。因此它不进入可直接执行的 `MODEL_CAPABILITIES`，只进入 `MODEL_CANDIDATES`；`Google Gemini API.models` 对该模型固定为 `adapter_required`。
- adapter 必须具名绑定确切 model/channel/provider，并完整提供 `input_roles`、`allowed_input_combinations`、`duration_seconds`、`fps`、`resolutions`、`native_audio`。缺一即拒绝；adapter 中的账号实测值只属于该项目收据，不能反向冒充官方全局能力。

## 多镜头 sequence unit（生成侧连续性，不改剪辑真值）

- 只合并**相邻、同 section、同 setup、总时长不超过 capability profile 上限**的 clips。
- sequence prompt 写明锁定切点和各子镜的 start/end/action；跨段落、跨 setup 不得为了省调用强并。
- 一次生成结果仍须按 picture lock 切点拆回每个 clip，分别 `--register / --score / --select`。sequence 不是新的交付单元，也不能替代逐缝 QC。
- 实际母片不能按计划累计 duration 盲切。具名复核者先逐帧/NLE 标出真实镜头边界，写 `mv_video_sequence_cut_map`（母片 SHA、`actual_boundaries_seconds`、`review_method`、`reviewer`、`notes`），再用 `video_jobs.py --register-sequence <file> --unit Sequence_XXX --take N --cut-map <json> --submit-receipt <json>` 拆回。脚本验证总时长、母片 SHA、边界数、单段时长容差后按 observed boundaries 切分、丢弃原生音轨并派生逐镜收据。
- `need_end_frame=true` 只有在模型 profile 明确 `start_end_frames=true` 时才提交尾帧；否则 manifest 必须记录 `multi_shot_sequence_or_editorial_match_review` 回退，不得伪称双帧已生效。

## 卡点定 clip 时长（核心）
- 由 `mv-plan` 读取 `节拍/beatgrid.json` 的 `downbeats[]`（小节首秒）并写入 `clip_plan.json`；mv-video 只消费，不重新拆时间线。
- **副歌**：每个 downbeat（或半小节）切一刀 → clip 短（碎切，强节奏）。
- **verse**：2-4 拍一切 → clip 长（缓）。
- clip 时长 = 该段相邻卡点之差；**全曲 clip 时长之和 ≈ 歌长**（mv-compose 会校验）。

## 段落/张力 → 运镜
| 段落 | 张力 | 运镜 | clip 时长 |
|---|---|---|---|
| intro | 克制 | 固定机位/极缓推镜头 | 长 |
| verse | 叙事 | 缓慢推镜头/稳定器跟拍/移镜头 | 中长 |
| pre-chorus | 蓄力 | 渐快推镜头/焦点转移 | 中→短 |
| chorus | 爆发 | 快推/甩镜/环绕/冲击变焦 | 短(碎切) |
| bridge | 反转 | 柯克变焦/前景遮挡揭示/摇臂揭示 | 中 |
| outro | 释放 | 缓慢拉镜头/固定机位/顶视俯拍 | 长 |

## continuity 派生规则（MV 版）
- `start_state`：**抄上一 clip 的 `end_state`**（同一句，不重写）；若是段落第一条，取本 clip 首帧描述 + 段落视觉锚点。
- `action`：取本 clip 的主动作链，并把动作峰值、眼神落点、拔剑/转身/抬手/光效爆点对齐 `beatgrid` 的 beat/downbeat；副歌动作短促，verse 动作完整。
- `end_state`：服务下一 clip 的首帧、歌词钩子和转场方式。接不住时停在手部道具、衣摆、背影、光效、门帘、山影等可切画面重心。**`need_end_frame=true` 时，end_state 必须与 mv-image 出的尾帧 `_end.png` 一致，并把它设为本 clip 尾帧做双帧引导。**
- `constraints`：同一段落继承角色定妆、服装发型、主色调、光线、天气、道具、背景布局、轴线/屏幕方向；跨段落可换场景，但角色定妆和核心道具保持。
- `negative`：默认写入"不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声"；人脸/手部/多人镜按风险追加"不要脸部抖动/不要手指变形/不要多人脸错乱"。

## 常用衔接做法
- **动作切**：上一 clip 结尾停在动作完成前后一拍，下一 clip 从同方向继续或切道具特写。
- **视线切**：上一 clip 让人物看向画外，下一 clip 承接被看的物体/风景/敌人/远山。
- **光效切/闪白**：副歌 or 强 downbeat 可用光效爆点遮掩场景切换，但不要每条都用。
- **遮挡擦镜**：衣袖、剑光、前景树枝、烟雾横过画面，用于接不上时补缝。
- **空镜缓冲**：verse/outro 用云、山、灯、雨、脚步、手部等 0.5-2s 镜头缓冲。

## 生视频 / 登记 / 挑版
- 同一 MV 全程同一生视频模型/渠道策略（防风格跳）。首帧=mv-image PNG（图生视频锁一致性）。
- 每 clip 跑几版挑脸/运动稳由 `出视频规格` 档统一定（充足=关键镜2-3版·普通镜2版；一般=关键镜2版·普通镜1版；不够=全1版）；废片归 `common/废料/出视频/`。
- 爽点 clip 的关键帧对齐某个 downbeat，供 mv-compose 卡点。
- 外部/网页生成视频后必须登记：先从 `出视频/receipts/Clip_001_take_01.submit.json` 模板生成实际收据，精确填写 provider job id、model/channel/provider_id、完整 compiled controls、按 role 的真实 refs+SHA 与确认；再运行 `video_jobs.py --register <file> --clip Clip_001 --take 1 --submit-receipt <json>`。模板本身不是证据，`manual` 还须具名 attestation。
- 正式 route 使用 submit receipt v2 + provider evidence schema v2，且 `provider_status` 必须归一为成功态。schema v2 对 transport、顶层及嵌套字段采用白名单，未知字段 fail closed。证据文件必须落在作品根的 `出视频/provider_evidence/**`（provenance 会从这里收集）、不能位于 `出视频/receipts/`，并记录当前 SHA-256；待登记视频的当前 SHA 写入 `selected_asset.sha256`，登记入口会与实际源文件逐字节核对。
  - `provider_api_response_json`：只允许 `provider_evidence.py` 内代码审过的 provider×model adapter；adapter 固定 capture 类型与 job/time/model/status 字段路径，JSON 严格解析并拒绝重复键。项目里的 capability adapter 不能声明新 Pointer。响应若出现 request/input/prompt/parameters 等请求材料而当前 adapter 没有固定绑定逻辑，fail closed。
    截至 2026-08-20，Veo 官方 operation 响应不承诺 model+提交时间，Runway task detail 不含 model，因此当前受信 API adapter 清单为空；这些 API route 会明确阻断并要求改 manual，而不是补写自证字段。只有 provider-owned capture 同时暴露四字段且能固定映射 controls/refs 后，才可在代码里新增 adapter。
  - `provider_ui_capture`：文件只能是具备正确 magic bytes 的 PNG/JPEG/PDF，另填 reviewer/notes/observed_at/submitted_at/provider/job/model/status/capture_method 的 `ui_observation`；`observed_at` 是人工观察时刻，`submitted_at` 是界面显示并与 receipt 对齐的提交时刻，不得混用。它会标记为 `named_human_observation`，不得表述成机器证明。若填 source URL，HTTPS origin 必须匹配该 provider。当前无代码审过的 HAR adapter 时，自制 HAR 或结构化 UI JSON 一律不收。
  - `local_runner_receipt_json`：固定 `mv_video_local_runner_receipt` v1，必须记录 provider、runner 名称/版本/操作者/命令 SHA、exit_code=0、job/time/model/status、compiled controls SHA、submitted refs SHA 与 output SHA。
  - `api_or_web` 必须显式写真实 `execution_transport=api|web`；未知 provider/model adapter、自由 `bindings`、证据漂移、job/time/model/status/output 不一致都会阻断登记和后续继承检查。旧正式 v1 仅可读，不能进入完成态；manual v1/v2 继续要求具名 attestation。
- 旧正式 v1 收据保持可读取，但不能作为 video 完成凭据，也不会自动从自填字段迁移出 evidence；必须用真实 export 重新登记。`manual` v1 仍可凭具名 reviewer+notes 兼容。
- 多版评分后挑版：`video_jobs.py --score ...`，再 `--select Clip_001 --take 1`；挑版会复制到 `出视频/视频/Clip_001.mp4` 并同步 timeline。

## 自查
- [ ] clip 时长来自 `clip_plan.json`（非等长）？
- [ ] 副歌碎切、verse 缓？
- [ ] 运镜服务段落/张力？
- [ ] continuity 五字段齐，且读取了上一/下一 clip 与 beatgrid 落点？
- [ ] 接力：start_state 抄了上一 clip 的 end_state（没自己重写）？标 `need_end_frame=true` 的接缝已让 mv-image 出 `_end.png` 并用首尾双帧？
- [ ] 每个外部 take 都已登记，最终 selected_take 已同步 timeline？
- [ ] register receipt 精确绑定 job/model/channel/provider/controls/逐 role 实际 refs+SHA，而不是把计划首尾帧 SHA 当提交证据？
- [ ] sequence 母片使用了绑定母片 SHA 的具名真实边界 cut map，而不是照抄计划累计时长？
- [ ] 三件套齐？总时长≈歌长？
