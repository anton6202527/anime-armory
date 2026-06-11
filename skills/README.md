# Skills 索引

本项目的自定义 skills 按 创作线×生产线 + 公共能力 组织（写小说→制漫剧、写歌→制MV、拍广告(ad)，外加公共 shared-video-faceswap / shared-image-faceswap 换脸、shared-watermark 水印、shared-cleanup 瘦身清理）。**目录保持扁平**（每个 skill 仍是 `skills/<name>/SKILL.md`）——
skill 之间用 `<skills>/<name>/...` 互相引用，故**不要**移进子目录，否则交叉引用与 skill 发现会失效。
本文件仅作分类说明。

> **工具中立 / 跨 AI 使用**：真身在仓库根 `skills/`，**不绑定任何特定 AI**。
> - **Claude Code** 经软链 `.claude/skills → ../skills` 自动发现并用 `Skill` 工具按触发词路由（无需改动）。
> - **其他 AI agent / 人**：直接读 `skills/<name>/SKILL.md`（= 这个 skill 干啥、何时用；frontmatter 的 `description` + 正文 `Triggers` 就是路由依据），照其说明做事，需要时跑 `skills/<name>/scripts/` 下的脚本。
> - **脚本是通用的**：纯 Python/bash，只调通用工具（ffmpeg / librosa / whisper / yt-dlp / 生图生视频 CLI 等），**无任何 Claude 专有 API**，谁都能执行。引用一律走中立路径 `skills/...`（旧 `.claude/skills/...` 经软链仍兼容）。

> **偏好约定（通用化原则）**：所有 skill 保持**通用**，不把平台/后端/分辨率写死成唯一路径。凡「让用户选」的点都是**选择点**，用户的实际选择是**私有的**，存在用户自己的空间——每作品 `<作品根>/_设置.md`（权威）+ 私有全局默认（memory 区 `创作偏好-默认.md`，开新项目预填），**不进共享 skill 代码 / 不进 git**。行为：选择点首次问一次→写 `_设置.md`→同项目沉默沿用；合规/不可逆/花钱多的点每次仍确认。机制与全部选择点目录见 [`_偏好约定.md`](_偏好约定.md)；每个 skill 有「## 偏好（私有）」段引用它。**新增选择点**→加进 `_偏好约定.md` 目录，别在正文写死。

> **AI 交互节点（Interactive Flow）约定**：凡遇到**「机器可自动计算，但需要结合文学/语义理解才能高质量完成」**的连贯流程（如算好卡点时间线后，需要给每个镜头写包含动作和运镜的 Prompt），**不要让用户手动去复制粘贴脚本命令**。应该在工作流 SKILL.md 中设置明确的**【AI 代理交互节点】**：让 AI 主动用人类语言向用户提问提供选项（如：“是否需要我启动语义引擎为你补全提示词？”），在用户做出「决定」后，由 AI 代理在后台全自动完成「跑脚本 → 读提示 → 调 LLM 生成 → JSON 落档并回写」的脏活累活。**原则：把枯燥的脚本命令藏在背后，让用户只做决策。**

---

## 一、n2d ——「小说 → AI 漫剧/短剧」生产管线

`novel2drama` 是总调度，按 `_进度.md` 把用户路由到对应阶段 skill。阶段顺序（**默认 `制作模式=配音先行`**）：

| 阶段 | Skill | 职责 |
|---|---|---|
| 调度 | `novel2drama` | 检查 作品 根目录，**入口先跑源新鲜度自检**（`source_check.py`：比对 `小说/<剧>.txt` 与 `小说/_源指纹.json`，写小说成品更新→列出变动章/受影响集/是否触及已生产集，提示同步+重切，重切每次确认不自动），读 `_进度.md`，按 `skills/common/n2d_contract.py` 的阶段契约路由到下面的阶段 |
| 1 剧本改编 | `n2d-script` | 拆集 + 精修前 5-10 集窗口复核边界 + 配音台词/BGM/封面/角色场景卡/global_style |
| 2 配音 | `n2d-voice` | voiceover.txt → 角色配音 + 拼接音轨 + 时长清单.json（驱动下游镜头时长；逐句记 `voice_key` 实际音色键，一角一色跨集对账数据源，`n2d-identity` 消费）；macOS say 中文空音频时自动降级静音占位并醒目告警 |
| 3 分镜设计 | `n2d-script` | 配音后回跑：按实测时长生成分镜剧本/故事板/素材清单/字幕/镜头时长 |
| 4 出图 | `n2d-image` | 两层出图 prompt（定妆库 + 本集分镜）→ 用 `生图AI` 所选后端出图（默认 Codex；**阶段2 起放行官方/已登录多参考后端** OpenAI/gpt-image、Dreamina/即梦官方 CLI、Seedream/可灵主体库/Nano Banana/Sora Cameo）。两条硬闸门：① 项目内**不混用后端** ② **禁第三方逆向/未授权出图** |
| 5 出视频 | `n2d-video` | 由故事板生成每 Clip 视频 prompt → 即梦/可灵/Veo/Seedance 图生视频；`scripts/inherit_contract.py` 机检出图→出视频视觉契约继承（光位锚/轴线漂移=block，报告落 `生产数据/contract_inheritance_第N集.json/md`） |
| 模型适配层（横切） | `n2d-model-router` | P1 视频后端路由层：按镜头类型/专项模板/身份注册层/原生音画/时长上限，为打斗、追逐、对话、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位选择 primary/fallback；`生视频AI` 只做默认/兜底。三条音画路线：默认配音先行；**`配音先行`+`对口型≠关闭`** 说话镜路由 `mode=voice_conditioned_lipsync`（把克隆配音当口型条件喂进 Seedance 2.0/可灵 Omni，音轨仍走配音轨·不双人声·省后期对口型 pass）；**`制作模式=原生音画`** 说话镜路由原生同步音画后端（`mode=native_av`、`native_speech`，绕过配音先行）。`scripts/motion_control.py scaffold/check/generate` 为 `level=required` 镜头生成 gate 兼容的控制资产骨架 manifest + 待补清单（补"只 gate 不生成"的摩擦），可选 DWPose/depth 种子帧；`scripts/mouth_detect.py` 按首帧 PNG（装 insightface 时）+ 分镜文本预填/复核每 Clip `mouth_visible`（决定原生音画 opt-in/口型），图↔文本/prompt 冲突标 warn |
| 角色身份闭环（横切） | `n2d-identity` | P0/P1 身份资产执行层：把 `identity_registry.json` 与 reference group、Face Lock、Character ID、reference controls、LoRA 打通，生成 `identity_adapter_matrix` 和跨集 `identity_drift_report`（含 LoRA 升档自动建议 `recommendations` + `characters_needing_lora_upgrade`）；`voice_consistency.py` 对账配音时长清单×voicemap，`voice_print_consistency.py` 量真实声纹漂移并外发 `voice_consistency` 一致性 findings |
| 跨项目资产库（横切） | `n2d-asset-market` | P1 成本摊薄层：把角色原型、定妆组、`identity_registry` 片段、视频模型路由经验导出成本地资产包，开新剧/新增角色场景前先查 `资产库/`；导入即 fork 新身份（写 `fork_history[]` 多级溯源链），默认重置 Character ID / Face Lock / LoRA ready 状态并把被重置后端记入 `preserve_review` 审计留痕，再跑 `n2d-identity` |
| LoRA 生命周期（横切） | `n2d-lora` | P2/P1 一致性重武器：只给核心长线角色管理 LoRA 数据集、训练任务、验证报告和 registry ready 回写；默认不联网训练，先把 `.safetensors` 从散文件变成可审计资产；`suggest` 子命令读 identity 漂移报表打印升档建议（升档触发已工程化） |
| 合规与版权前置（横切） | `n2d-compliance` | P0 合规包：生成/检查 `合规/compliance_manifest.json`，把源文本/改编权、角色肖像授权、声音克隆授权、AI 标识、可见/元数据/C2PA/平台水印、平台审核、出海本地化前置到 gate；`distribution_intent=internal_only` 时平台投放/出海域降 INFO 免检（授权/AI 标识照常 BLOCK） |
| 6 合成 | `n2d-compose` | 拼 视频 clips + 配音 + BGM + 烧双语字幕 → 成片；`tension_mix.py` 按 storyboard 每 Clip `rhythm` 出张力感知 BGM 增益包络（爽点抬/细节压，喂 `BGM_GAIN_EXPR`，不传则原固定行为） |
| 质检·自审（横切） | `n2d-review` | 双模 QA：①作品质检（崩脸/字幕错位/音画/节奏/合规，机检+人判，出定位报告）②流程自审（先 `scripts/self_audit.py` 做本地静态治理检查，再联网对标→审 skills+Q&A→出优化建议）。非必经阶段，任意闸门或成片后可跑 |
| 进度·下一步（横切·只读）| `n2d-progress` | 扫 `制漫剧/<剧名>/_进度.md` 逐集矩阵 → 压缩出每部剧完成度 + 生产前沿（下一步该跑哪个 n2d skill）+ 可并行事项 + 次要缺口，按 `制作模式` 解释 `配音=⏳rough` 与原生音画跳过配音硬依赖；出图/视频/成片/配音等花钱·不可逆·合规步骤先提醒确认。**只读·不改文件·不碰其它三条线**。脚本 `scan.py` 纯标准库。触发词：进度 / 当前进度 / 下一步 / 还差什么 / progress / check |
| skill 更新重制（横切·计划） | `n2d-update` | 检测 n2d 相关 `skills/` 文件相对上次快照是否变化，读 `_进度.md` 判断每集当前阶段，生成“从最早受影响阶段回放、最多只重制到当前阶段”的最小重制计划（`生产数据/skill_update_plan_第N集.{json,md}`）；用户说 更新/重制/update/rebuild 某作品某集时触发。只生成计划和建议命令，不直接烧图/视频/配音；确认后交 `n2d-batch` 或对应 stage skill 执行 |
| 生产数据仪表盘（横切） | `n2d-dashboard` | P0 工业化 + ROI 指标层：每集记录成本、耗时、生成次数、重抽原因、QA 阻断项、最终通过率，并派生每分钟成本、一次通过率、重抽率、投放净回收、回收/生产成本；重抽原因按契约 `REDRAW_REASON_CATEGORIES` 九类维度归类（显式传或按关键词自动归类，存量读时归类），`dashboard.md` 出分维度表 + **一致性小计**；生成 `production_events.jsonl`、`dashboard.json/md`。**实时监控 + 阈值告警(纯本地·跨AI通用)**：record/gate 每次写事件即评估阈值(预算上限/通过率下限/重抽率/QA阻断/回收比)写 `alerts.json/md`；内置 `watch` 轮询 + 本机 `http.server` 自刷新 `dashboard.html`；可选本机弹窗(osascript/notify-send)与 webhook(`N2D_ALERT_WEBHOOK`)；`build --fail-on-critical` 退出码停线。循环逻辑在脚本内，hook/cron/loop 仅可选外壳 |
| 批量任务队列（横切） | `n2d-batch` | P1 批量编排 + worker 层：按 `_进度.md` 自动排队，支持并发 claim、失败重试、预算上限、按受影响镜头/Clip/产物最小范围重跑，并可直接承接 `n2d_consistency_findings`（一致性审查 / 人审 UI 导出）生成返工队列；`runner.py` 可自动 claim、执行配置命令、写 dashboard telemetry、回写 pass/fail；生成 `生产数据/batch_queue.json`、`batch_queue.md`。**单机多 worker 安全（纯本地·零后端）**：`flock` 原子认领 + 原子写账本 + 任务租约(心跳续租) + 过期租约自动回收 + `--resume` 崩溃自愈；多机/私有算力池仍需真正的协调后端（flock 跨 NFS 不可靠） |
| 自动审片评分（横切） | `n2d-score` | P2 机器评分层：每集输出语义继承/状态百科/多模态漂移 + 角色/服装/场景/字幕/音画/节奏/风格维度分，并接入图像相似度、字幕 OCR、音画时长对账、口型风险/检测报告、成片节奏密度；脸 G1 无 insightface 时按 `pillow_fallback` 降权分消费（不再整维度缺数据）；低于阈值生成 `auto_return_tasks`，可写入 `n2d-batch` 定向返工队列 |
| 人审可视化 UI（横切） | `n2d-review-ui` | P2 可视化层（零构建 HTML/JSON，只读不改状态）：① `review_ui.py` 单集人审画布（首帧/尾帧/clip/接缝/定妆/QA flag/机器分），可 `--export-findings` 输出 `review_ui_findings_第N集.json` 供 `n2d-batch --from-consistency-findings` 回流；② `board.py` 整部生产看板（读 `_进度.md`→作品/集/阶段/Clip+接力链+进度色，`--serve` 本地 127.0.0.1）——PC端+无限画布愿景的 MVP（Q36） |
| 投放数据回灌（横切） | `n2d-feedback` | P2 增长反馈层：导入平台留存/追更/跳出数据（实时投放 API 经摄取适配器规范化成标准 `platform_metrics` 文件，支持中文列名别名），并从 `storyboard.json` 自动抽取导演标签；同集开场/封面/集尾断点/标题文案 A/B，按 paired lift 分析；生成 `platform_feedback.json/md`，可更新 `导演节奏.md` 快照；**`--emit-ledger` 把第一方战绩按题材写入跨项目「自有题材战绩库」(`生产战绩/genre_ledger.jsonl`)，供 `novel-score` 反哺选题——闭合 选题→生产→投放→反哺选题**；另读 `生产数据/consistency_findings_*.json` / `review_ui_findings_*.json` 出「一致性问题 Top」与留存/跳出并排（QA 线接进投放闭环） |

> **选择点 `制作模式`（出片顺序）**：默认 `配音先行`（真实配音时长驱动镜头，音画准·返工少）。另支持 `先出视频后配音`（**快速 demo·不推荐**：镜头时长靠估算锁死，后期补真音对不上 → 音画不同步/可能重切重出视频）；以及 `原生音画`（**native AV·按剧选**：Seedance 2.0/Veo 3/Sora 类后端对说话镜一次出同步音画[台词+口型+环境声]，绕过配音先行链路与对口型，规避代差与占位返工，代价是少了逐句音色控制；合规仍需 AI 标识、仿真人音色需授权）。三种流程图 + 完整理由见 `novel2drama/SKILL.md`「制作模式」节；选择点定义见 `_偏好约定.md`。
> **机器契约层**：n2d 的阶段图、`_进度.md` schema、gate stage、manifest 与结构化回滚字段集中在 `skills/common/n2d_contract.py`，人读版见 `novel2drama/references/contract.md`。`common/n2d_route.py`、`novel2drama/progress.py`、`n2d-progress/scan.py` 和 `n2d-review/scripts/gate.py` 复用同一契约；阶段职责变更时先改 contract，再同步本索引与各 SKILL.md。**横切口径分两层**：① 有作品级就绪标志的横切能力（合规/身份/LoRA/资产库/仪表盘/评分/审片UI/投放回灌/skill 更新重制）登记在 `n2d_contract.CROSS_CUTTING_READINESS`（旧别名 `CROSS_CUTTING` 兼容），`n2d-progress` 据此输出「横切就绪」；② 无稳定就绪标志或本身是调度/观察工具的横切工具（model-router/batch/progress/review）登记在 `n2d_contract.CROSS_CUTTING_TOOLS`，只供索引/调度说明感知，不污染 `_进度.md` 流程表。新增横切能力时按这两个边界登记 + 同步本索引。每次 `progress.py set` 会自动刷新 `脚本/第N集/manifest.json` 快照，也可用 `python3 skills/novel2drama/manifest.py <作品根> 第N集 [--stage stage_key]` 手动重建。

> **合规与版权前置（P0）**：新剧或投放前先跑 `python3 skills/n2d-compliance/scripts/compliance.py <作品根> --init`，人工补齐后用 `--check` 预检。`n2d-review/scripts/gate.py` 在 image/video/compose/review 四个阶段都会读取 `合规/compliance_manifest.json`：源文本/改编权、角色肖像授权、声音克隆授权、AI 标识、可见水印/元数据/C2PA 或平台隐式标识、平台审核、出海本地化缺任一项，先阻断，不能等成片后补救。
> **选题↔投放闭环（跨生产线 · 内卷市场的结构性优势）**：`novel-score`（选题/题材热度）→ 生产（n2d 全链）→ `n2d-feedback`（投放回灌）→ 反哺 `novel-score` 选题，形成闭环。连接点是**数据产物层**的一个跨项目「自有题材战绩库」（append-only JSONL，默认 `生产战绩/genre_ledger.jsonl`）：`n2d-feedback --emit-ledger --genre <题材>` 按题材写入第一方留存/追更/完播/ROI；`novel-score` 自动读它做题材热度的**第一方先验**（自有 ROI/留存权重高于公榜，本题材做不动就下调 topic_heat）。novel-* 与 n2d-* 仍是独立生产线，**只在这个文件层连接、不互相 import**。实时投放 API 经 `n2d-feedback` 的摄取适配器规范化成标准 `platform_metrics` 文件（支持中文列名别名）。
> **反同质化差异化引擎（闭环的反内卷延伸）**：`n2d-feedback/scripts/differentiate.py` 从战绩库点云（`题材×开场×结尾×密度`，每条记录带主导 `features`）+ 公榜基线反推**"未被做烂的组合"**——占用度(我们做过几次)×已验证轴(战绩里有效的开场/结尾节奏)×市场饱和(公榜避热门)，排序出差异化选题候选写 `生产战绩/差异化候选.{json,md}`，供 `novel-create/novel-title/novel-score` 当选题输入。爆款率仅 0.16% 的内卷市场里，这是把"反哺"从节奏层升到**选题层**的关键。样本/基线不足时诚实降级、不捏造题材。
> **仙侠武侠打斗专项工艺**：`n2d-script/references/打斗分镜.md`（五帧拆招/命中帧出图/首尾帧锁动作/后期补打击感），已挂接 script/image/video/compose/review 全链；总纲见 `novel2drama/Q&A.md` Q31。
> **仙侠非打斗奇观工艺**：`n2d-script/references/仙侠场面分镜.md`（御剑飞行/追逐/渡劫突破/炼丹炼器/大阵法阵/大场面 establish/斗法对轰/神魂(神识·元神出窍·夺舍)——飞行追逐锁姿态动背景、渡劫炼丹法阵对轰爆发帧出图+元素入库、神魂元神=肉身半透明派生治"二我"、大场面三镜由远及近），同样挂接全链；总纲见 `novel2drama/Q&A.md` Q33。
> **资产库题材自适应**：共享定妆库通用三类（角色/场景/道具）+ ⚙️仙侠玄幻可选两类（**法宝/特效**，本命法宝按形态多态、剑气/光效锁颜色拖尾）；**人物定妆固定标准三视图**——所有人物角色先出正面 / 侧面 / 背面生产拆图，并生成 `定妆_<角色>_三视图.png` 人审拼版；场景才按题材和复用程度补**场景多视图（四视图）**保跨镜背景自洽；见 `n2d-image/references/prompt_format.md §1`+`角色一致性checklist.md`、`Q&A.md` Q32。
> **模型矩阵 + 模型路由（防过期快照）**：各轴 SOTA vs n2d 默认 vs 升级触发（含图/视频/配音 + **口型 lip-sync**：后端音频参考口型（Seedance 2.0 音素级/可灵 Omni，由 router `voice_conditioned_lipsync` 喂克隆配音、不双人声）首选，后期 MuseTalk/Wav2Lip/LatentSync 兜底；配音情绪解耦 IndexTTS-2），见 `novel2drama/references/模型矩阵.md`，由 `n2d-review` 流程自审每次检查，默认只给刷新建议；用户确认落地后再刷新矩阵——版本名只活在带日期的快照里，正文写能力不绑版本。视频阶段新增 `n2d-model-router`：`视频模型路由=自动按镜头路由` 时，打斗/追逐/对话/飞行/空镜/法术爆发/亲密互动/拥抱拉扯/多人同框/群像站位按能力选择 primary/fallback；`生视频AI` 不再固定每个 Clip，只作为普通镜和兜底后端。
> **单 Clip 上限按后端（非一刀切 8s）**：机器真值源在 `skills/common/n2d_platform_profiles.py`（即梦 image2video≤8s / Seedance≤15s / 可灵≈10s / Veo≈8s / Sora≈20s），`n2d-video/references/platforms.md` 负责人读解释，`n2d-model-router` 与 gate 读 common 值——能一镜到底就别切碎（更少拼接缝·跨镜更稳）。
> **clip 衔接接力链（治"剪起来跳"·横切全链）**：clip 间顺滑是一条逐级继承的接力链，单一真值源在 `n2d-script`。① `n2d-script` 在 `故事板.md`/`storyboard.json` 把每个接缝写成契约：`上一 Clip 出点 = 下一 Clip 入点`（同一句）+ `转场类型` + `需要尾帧?`（见 `references/formats.md §4`）。② `n2d-image` 在标 `需要尾帧` 的接缝出**尾帧 PNG `镜头N_end.png`**（命名=首帧名+`_end`，亦兼容 `Clip_NN.png`→`Clip_NN_end.png`；=下一 Clip 首帧构图，最省做法复用下一 Clip 参考图组）。③ `n2d-video` **读取**契约不重写 start_state、有尾帧用首尾双帧引导焊接点。④ `n2d-compose` 按 `转场类型` 接 clip（有意硬切硬切/跳变微溶解/缺空镜报警），不盲拼。⑤ `n2d-review` 逐接缝并排读图查跳切/闪烁/接力断链。**MV 线同构但卡点优先**：契约源在 `mv-plan` 的 `分镜/clip_plan.json` 与 `timeline_manifest.json`（`出点=下一入点` + `转场` + `need_end_frame`，单一真值踩 `mv-beat` 的 beatgrid downbeats 定切点）；`mv-video/scripts/video_jobs.py --select` 只登记/挑版并同步 timeline，不另造时间线。默认**卡点硬切**、靠"视觉身份一致+卡点准"接缝，尾帧接力仅**同段落·非卡点切·连续镜**可选（`mv-image` 出 `_end.png`、`mv-video` 双帧引导）。`mv-compose` 按 timeline 顺序和 `转场` 接（卡点硬切硬切/跳变微溶解/缺空镜报警），`mv-review` 逐接缝查跳切——但**副歌卡点切的有意跳变不算问题**（容差比 n2d 宽）。
> **机器闸门**：n2d 高风险阶段正式生产入口统一跑 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image|video|compose|review`。它调用底层 `n2d-review/scripts/gate.py --json`，检查合规包、占位配音、`storyboard.json` continuity、尾帧、prompt 检查段、生图 AI 一致性、clip 音轨/时长、水印、**P0 语义谱系 / P1 状态百科** 等阻断项，并把 `block/warn/info`、`return_to_stage`、`rerun_scope`、`affected_artifacts` 写入 `生产数据/`；同时外发 `gate_findings_<stage>_第N集.json`（kind=`n2d_consistency_findings`），可直接交给 `n2d-batch --from-consistency-findings` 入队；退出码沿用 gate（有 block 即 1）。裸 `gate.py --json` 只作调试/机器消费入口。image/video/compose/review gate 都会阻断缺 `合规/compliance_manifest.json` 或角色授权/声音克隆授权/AI 标识/平台审核/出海本地化未就绪；image gate 放行官方/已登录多参考后端但阻断项目内后端混用；video gate 会阻断缺导演一致性契约或逐 Clip 缺导演调度五字段；review gate 另跑 **P2 多模态视觉语义/道具漂移** + **L1 双语字幕对齐**（中↔英短语边界/阅读速度/译文完整性，补 mechanical_check 条数对账盲区）。
> **资产引用闭环（P0）**：人物/形态归 `identity_registry.json`，关键场景、关键道具、独立服装/盔甲、法宝/VFX 归 `asset_registry.json`。逐镜 prompt 必须写 `资产身份注册层` 与 `资产引用注册层`，用 `CHAR_xx/形态`、`LOC_xx`、`PROP_xx`、`OUTFIT_xx`、`VFX_xx` 绑定参考组与漂移禁区；image gate 缺注册表、缺逐镜 ID 绑定、ID 类型前缀不匹配、关键道具结构约束不完整都会阻断。服装若是角色形态的一部分，放在 `identity_registry.json` 形态里；能跨角色/跨场单独复用或会独立漂移的服装才建 `OUTFIT_xx`。
> **生产数据仪表盘 + ROI（P0）**：每次 n2d 生成、审查或投放回收后，调用 `n2d-dashboard` 记录事件；成本、耗时、生成次数、重抽原因、QA 阻断、最终通过率、每分钟成本、一次通过率、重抽率、投放净回收、回收/生产成本统一落 `制漫剧/<剧名>/生产数据/`。`_进度.md` 只管阶段状态，`n2d-dashboard` 才是判断“工业级是否成立”的指标真值源。gate 结果用 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image|video|compose|review` 入账，生成事件用 `record` 入账；平台收入/投放成本放 `生产数据/platform_metrics.csv|jsonl|json` 或 `record --event release` 入账。**开跑前成本预检**用 `dashboard.py forecast <作品根> 第N集 [--budget N --unit CNY]`：历史 `cost_per_finished_min` × 本集计划时长给预测成本 + 预算够撑几集 + 重抽漏点 Top（事后记账之外补一个事前估算；无历史/无计划时长则不臆造）。`dashboard.md` 另出**行业基准对照**（默认读 `n2d-dashboard/references/industry_benchmark.json`，一次通过率/重抽率/每分钟成本/跨集一致性 并排行业宣传基准，只读·非闸门，可 `_设置.md` 或项目级 `生产数据/industry_benchmark.json` 覆盖，基准以 `n2d-review` 流程自审复核为准）。
> **工业化量产可行性分析**：详见 `docs/n2d-industrial-feasibility-study.md`，从原子化解耦、SSOT、ROI 导向等维度评估漫剧生产线的工业化成熟度与优化路线图。
> **批量任务队列（P1）**：多集推进时先用 `python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-10 --max-concurrency 2 --budget <N>` 生成队列；执行者用 `claim` 占并发槽，用 `mark` 记录 pass/fail，失败按 `max_retries` 自动回到 `retry_queued` 或落 `failed`。配置 `生产数据/batch_runner.json` 后，可用 `python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty` 自动 claim、执行、写 dashboard telemetry、回写状态。定妆变更、gate finding、审片问题用 `--rerun-from image|video|compose --affected-shot/--affected-artifact` 只重跑受影响范围，不整集重来。**单机多 worker**：各 worker `runner.py <作品根> --until-empty --worker w1 [--resume]`——`claim/mark` 全在 `batch_queue.lock` 的 `flock` 内重读最新队列+原子写，绝不双认领；任务带租约+心跳续租，worker 崩了租约过期自动被别的 worker 回收，`--resume` 立即自愈本 worker 残留 running。`queue.py reclaim <作品根>` 手动回收。**这是纯本地零后端方案；真·多机要换协调后端**。
> **自动审片评分（P2）**：成片或阶段审查后跑 `python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85`，生成 `生产数据/score_第N集.json/md`。它汇总 n2d-review 机检、一致性审查、n2d-dashboard 阻断，并新增 `visual_checks.py`：接缝图像相似度、字幕 OCR、成片/配音/SRT/storyboard 时长对账、口型检测报告/口型风险、成片节奏密度。语义继承/状态百科/多模态漂移和原有视觉/字幕/音画/节奏维度都会映射回 `script_stage2` / `image` / `compose`；加 `--enqueue-low` 可直接写入 `n2d-batch` 返工队列。
> **人审 UI / 无限画布（P2）**：机检和机器分之后跑 `python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --export-findings --markdown`，生成 `生产数据/review_ui_第N集.html/json` 与 `review_ui_findings_第N集.json`。HTML 静态可打开，集中看首帧、尾帧、clip、接缝、定妆参考、QA flag、机器分和缺素材；批量审片时先用筛选器看 block/warn，再逐接缝和高风险 clip 人判，红黄 flag 可直接交给 `n2d-batch --from-consistency-findings` 回流。
> **投放数据回灌（P2）**：上线一批后跑 `python3 skills/n2d-feedback/scripts/feedback.py <作品根> --metrics <平台指标.csv> --update-guide`，用平台留存/追更/跳出数据反哺 `novel2drama/references/导演节奏.md`。`creative_features` 默认从 `脚本/第N集/storyboard.json` 自动抽取 `opening_type/cliffhanger_type/shot_density_per_min/hook_interval_sec`，需要复核时加 `--write-features` 落 `creative_features.auto.json`，手工文件或 `--features` 仍可覆盖；同一集多投放版本时在 metrics/features 写 `ab_test_id + variant_id + opening_variant/cover_variant/cliffhanger_cut_variant/title_variant`，报告会额外算同集 paired lift，比较开场、封面、集尾断点、标题文案对留存/追更的影响；样本不足只写观察，不把偶然数据写成铁律。
> **视觉契约 + 基础视觉风格契约三层同源**：色调/光位/轴线·视线/人物状态/景别这些**视频改不动、要烤进首帧像素**的导演决策，源头在 `n2d-script` 分镜设计——`storyboard.json` 写 `visual_contract` 种子块 → `n2d-image` 的 `出图/第N集/prompt/00_总览.md`「本集视觉一致性契约」继承+细化、逐镜带 `视线方向/光位锚/起幅·运动余量`（首帧=起幅非动作顶点、为运镜留构图余量）→ `n2d-video` 的导演一致性契约再继承。基础视觉风格同理：用户先选 `基础视觉风格` → `global_style.md` 写风格源头 → `storyboard.json.style_contract` 写风格名/视觉基调/镜头与构图/光色策略/运动边界/风格禁忌 → 出图总览「本集基础视觉风格契约」把所选风格烤进首帧 → 出视频总览继承并只做相容运动。image gate 阻断 storyboard 缺 `visual_contract` / `style_contract` 或总览缺契约；compose gate 另查成片时长对账（amix 静默截断超长配音）+ 水印待打提醒（画幅按 `_设置.md` 不写死）。配音侧 `设定库/voicemap.json` 持久绑定角色→音色（跨集稳定，manifest 记 `音色键/voice_id` 供机检），零样本克隆喂参考音同 `voice_clone.py` 一样硬闸门要 `VOICE_CLONE_AUTHORIZED=1`。
> **崩脸机检（自标定 flag-band）**：装 `insightface` 后跑 `n2d-review/scripts/face_consistency.py <作品根> 第N集` —— **不写死阈值**，用本作定妆组内部互相余弦当"同一人下限"地板，每镜低于 地板−margin=🔴/地板带=🟡（治写死 0.45 对风格化脸误杀/放过）；缺库优雅跳过交人判，纯数学部分带 pytest。
> **一致性机检套件（都自标定·缺库优雅跳过·纯数学带 pytest）**：① **P0 `semantic_continuity.py` 语义谱系 Diff**：抽取 `voiceover.txt → storyboard.json → 出图 prompt → 出视频 prompt` 的角色/场景/状态/风格/模板/continuity 关键词，检查下游是否继承上游，匹配层含精确词/常见同义别名/中文 bigram 重叠，提前抓语义变形；② **P1 `state_continuity.py` n2d 动态百科/状态哨兵**：读取 `storyboard.json.visual_contract.角色状态演进` + `出图/共享/visual_state_ledger.json`，抓状态提前泄露、开始后漏继承、区间结束后泄露，`until/至 ClipN/本镜` 会被当作状态区间；`state_ledger_build.py <作品根> --episodes 1-10 --write` 可从 storyboard 确定性生成跨集 visual_state_ledger；③ **P2 `multimodal_consistency.py` 多模态视觉语义/道具漂移**：按非角色参考资产（场景/道具/法宝/特效）分组，用本地视觉 embedding（RGB 直方图 + dHash；可后续接 CLIP/DINO/SAM）找组内离群，角色优先由 `identity_registry.json` 判定，非角色资产优先由 `asset_registry.json` 判定；④ `face_consistency.py` 锁脸（含 `--audit-anchor`=**N3 定妆主参考质量门**：恰好 1 张清晰够大正脸才配当锚点，治"锚点一脏下游每镜继承"）；⑤ `outfit_consistency.py` 锁**服装/配色**（加权色相直方图，治"脸没崩但夹克色第4镜就漂"，需 Pillow）；⑥ `temporal_consistency.py` 锁**单 clip 内**身份漂移 + flicker/TCI（ffmpeg 抽帧，治"几秒后脸渐变/发际线闪"，对标行业 scene-stability 记分卡）；⑦ `quality_check.py`=**N4 糊/低质无参考质检**（Laplacian 方差·自标定本集中位数，关键镜更严）；⑧ `scene_consistency.py`=**O2 场景/环境一致性**（同场景多镜 dHash 结构离群 + **光位/色调离群**[明度+饱和加权色相指纹·光位锚的可机检代理]·自标定，治背景漂移与光打错向/色温跳，需 Pillow）；⑨ `style_consistency.py`=**S1 风格一致性**（每镜风格指纹[饱和+明度直方图+边缘密度]·median-中心自标定，治"某镜突然偏离所选风格"，补 `style_contract` 落地后零机检的盲区，需 Pillow）；⑩ `temporal_consistency.py --seam`=**接缝接力**（尾帧 vs 下一首帧 dHash，距大=出视频跳切，把"逐接缝人判"降成机检初筛）；⑪ `n2d-identity/voice_print_consistency.py`=**音色声纹一致性**（speaker embedding，自标定 flag-band，输出 `voice_consistency` findings）。**一键编排 `consistency_audit.py <作品根> 第N集`** 串跑视觉/语义类检测器出一张汇总分档表，并保留 `details/affected_shots/affected_artifacts/auto_return_tasks`（O1·检测器再多没被自动跑=没有）——`n2d-review` 模式①工作流第 1 步即调它。覆盖「语义继承→状态演进→视觉语义/道具→定妆(锚点门)→首帧→接缝→片内→场景(结构+光色)→风格→清晰度」全链。另：`n2d-identity/scripts/identity.py <作品根> --write` 汇总 Face Lock / Character ID / LoRA / reference group adapter matrix，并生成跨集 `identity_drift_report` 与声纹 findings；gate 还强制逐镜负向含风格禁忌、运镜越运动边界 WARN、风格名↔基础视觉风格软校验。
> **定妆变更影响扫描 + 连锁更新自动化**：改了共享定妆资产后，`n2d-image/scripts/asset_impact.py <作品根> <资产名>` 列出引用它的下游镜头（已出图的需重出），属 `n2d-review` 机检家族；兼容两种 prompt schema。加 `--rerun-plan` 直接出**连锁重跑计划**（受影响集 → 重出图 → 刷新身份 → 重出视频 → 重合成 → 每集一条最小范围 `n2d-batch --rerun-from image --affected-artifact/--affected-shot` 命令），把"改一个定妆要回头排查哪些集/镜头/clip"的人工活自动化。除文本「参考图」行外**同时读 registry 结构化绑定**（prompt 只写 `CHAR_xx` ID、靠 registry 自动取参考的镜头不再漏）；`--include-video` 加「已出视频需重生」清单、`--check-native-adapters` 列「后端身份注册基于旧定妆需重注册」、`--output-batch-tasks 计划.json` 输出 batch 直接可吃的任务 JSON（`queue.py plan <作品根> --from-asset-impact 计划.json` 自动排队，免手抄命令）。
> **接缝自动化（n2d-compose 已落地）**：`n2d-compose/seam_concat.py` 按 `storyboard.json` 每接缝 `continuity.transition` 自动接 clip——硬切裸拼 / 跳变·未焊→局部 `xfade` 微溶解 / 缺空镜→报警；硬切相连段先 `concat -c copy`、只在溶解接缝重编码，无溶解时等价旧行为，ffmpeg 失败自动回退裸拼。`compose.sh` 拼接步已接入（`SEAM_FALLBACK`/`SEAM_DISSOLVE_SEC` 可覆盖）。
> **角色身份闭环（P0/P1）**：`identity_registry.json` 是真值，`n2d-identity` 把它展开成 `identity_adapter_matrix.json/md` 和 `identity_drift_report.json/md`。reference group、Face Lock、Character ID、reference controls、LoRA 都必须进同一矩阵；`registered/ready` 空句柄、后端 mode 不匹配、LoRA ready 缺 `base_model/model_path/trigger` 都由 gate 阻断。跨集脸漂不再只靠人记，报表会给出角色级 `first_bad_episode`，供 `n2d-batch` 只重跑受影响集/镜头。
> **跨项目资产库提示（让用户不用记 CLI）**：开新剧、建角色卡、出图新增共享定妆、或某类路由经验值得沉淀时，agent 先提醒“我会查资产库，有可复用模板就问你是否导入”，再后台跑 `python3 skills/n2d-asset-market/scripts/market.py list`。导入角色模板后必须 fork 新 `character_id/name`，并跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --write`；用户只需说“查资产库 / 导入冷宫废妃模板为沈念 / 把这个角色导出成模板”，不要要求用户背命令。
> **LoRA 生命周期（第三档一致性）**：LoRA 不默认启用；只有核心长线角色在参考图派生 + 后端原生角色 ID/主体库仍不稳时，才调 `n2d-lora`。它管理 `设定库/lora/<CHAR_ID>/<形态>/` 下的 `lora_card`、`dataset_manifest`、`train_job`、`validation_report` 和 `.safetensors`；验证报告未 `pass` 不得写 `identity_registry` 的 `lora.status=ready`。用户只需说“给沈念启动 LoRA 生命周期 / 验证这个 safetensors / 写回 registry”，不要背命令。
> **一致性梯子（出图）**：①参考图派生（默认）→ **②后端原生角色ID/主体**（可灵主体库 / Seedream Universal Reference / Sora Cameo·注册一次按 ID 引用·opt-in·先于 LoRA 用尽）→ ③LoRA。能力对照见 `n2d-image/references/platforms.md`「后端原生角色ID / 主体库」，opt-in 流程见 `n2d-image/SKILL.md` 同名节；后端无持久 ID 自动回退第①档。**出图侧锚定双保险**：锚点句（锁特征词）+ **身份锁定句**（锁"与参考图①同一张脸"，多参考/编辑类模型最敏感）叠加用；定妆 ≥1024px·覆盖 3–6 角度。**多人同框/复杂站位可选增强（控制网双保险）**：站位易乱且后端支持 pose/depth 时，用骨架/深度图锁站位+景别（控制网锁"站位"、参考图锁"身份"·正交叠加），后端不暴露控制网则退回多参考后端/分别出图合成，不为上控制网而混后端（见 `n2d-image/SKILL.md` 多角色同框节 (c)）。
> **一致性梯子（出视频·治 image2video 脸漂）**：除首帧锁脸外，有原生角色一致能力的后端把定妆喂进去当**持久角色参考**——可灵 3.0 **Character ID** / Seedance 2.0 **Face Lock** / Veo 3.1 **reference controls**；**极端角度/大暗部/人物过小**是公认崩脸高危带，分镜阶段就规避（见 `n2d-script/references/分镜语法.md`「一致性高危镜」+ `角色一致性checklist §二`）。缺原生能力退回「首帧+首尾双帧+强 end_state 文字」。

## 二、novel ——「写小说」创作工坊

`novel-author` 是总调度（与 `novel2drama` 同构），按输入（几个字/想法/书名/URL/路径/配角名/扩缩/审稿/评分）路由到下面的子 skill；拖入本地小说文件/URL 且没指定动作时，先用 `scripts/import_novel.py` 自动推断书名并建 `写小说/<书名>/` 源书项目；指向已有 `写小说/<项目>/` 且有 `_进度.md` 时，先读它续跑未完成阶段。与 novel2drama(制漫剧·`制漫剧/`) 平行：这条线做**纯文本小说**，**产物统一落 `写小说/<项目>/`**，成稿后可交 novel2drama 改编漫剧。

| Skill | 职责 |
|---|---|
| `novel-author` | 顶层分派器：看输入 / 读 `写小说/<项目>/_进度.md`，路由到下面的子 skill；拖入小说路径/URL 时先建 `写小说/<书名>/` 源书项目，重名提示新建版本/覆盖/使用现有，**自身不写作** |
| `novel-create` | **原创从零·访谈引导**：只有几个字/想法/部分风格/碎片时，访谈→创作蓝图→设定圣经→章纲→Demo→任务包批量写章→状态增量/回扫→成书（家族里唯一从零生成，其余都需既有源） |
| `novel-title` | 头脑风暴 5–8 个书名候选，5 维打分排序 |
| `novel-fetch` | 按书名/章节目录 URL 联网抓公版小说全文 → txt + docx + `source_manifest.json` |
| `novel-craft` | 写作工艺共享库（章纲编织/单章守则/扩写/精简/**设定圣经统一 schema**/**批量写章闭环**）+ **机器契约层**（`references/contract.md` + `scripts/contract.py` 定义 `_meta/_进度` schema、scale 分档、输出格式、原创/派生阶段表；`scripts/registry.py` 定义 novel-* roster；`qa-report-schema.md` 定义 review/score JSON 回流报告）+ 共享脚本（`draft_queue.py` 批量写章认领队列、`draft_packets.py` 生成逐章任务包+状态账本、`progress.py` 加锁读写 `_进度.md`、`store.py` 原子写/锁、`ai_usage.py` 写 AI 使用披露、`export.py`/`derive_common.py`），被其他 novel-* 按路径引用 |
| `novel-expand` | 短篇 → 长篇：在保留事件骨架前提下加细节 |
| `novel-condense` | 长篇 → 短版：砍描写/支线/重复内心戏，并章 |
| `novel-continue` | 续编（完本后写续集）/ 接更（接未完本往后写） |
| `novel-rewrite` | 改写/魔改/翻拍：改主线、加原创设定的转化型重写 |
| `novel-spinoff` | 配角平行视角外传，锚点处锁定原作事件 |
| `novel-review` | 双模 QA（与 n2d/mv/song-review 同构）：①作品质检（串视角/人设崩/设定矛盾/锚点漂移/原文照搬，机检+人判，出 Markdown + `review_report.json` 回流报告，判"写得对不对"）②流程自审（先 `self_audit.py` 做本地静态治理检查，再联网对标→审 novel-* + novel-craft→出优化建议）。机检 `mechanical_check.py` 带 pytest |
| `novel-score` | 市场+品质评分体检：联网拉红果/抖音/番茄当下热榜对标 **+ 读 n2d-feedback 写的「自有题材战绩库」做第一方题材热度先验**（自有 ROI/留存权重高于公榜，闭环读端），多维打分→总分+档位+「过/小改/大改/弃稿重立」判定+改写ROI，出 Markdown + `score_report.json`（判"值不值得做、能不能火"）**+ 读 novel-simulate 的模拟读者留存信号做第一方留存先验** |
| `novel-style` | 文风指纹提取与漂移机检：`extract_style.py` 从标杆/锚点章确定性算出《风格指纹.json》(句长分布·短句比·对白占比·虚词密度·词频锚点)，`--compare` 算两份指纹的漂移分；供 `novel-create/continue` 写作时注入、`novel-review` 做"文风漂移"机检 |
| `novel-wiki` | 动态百科与逻辑哨兵：`wiki_builder.py` 从章节+角色卡增量建《动态百科.json》(角色生死/位置/道具/状态)，`logic_sentry.py` 确定性扫硬冲突(死人复活/弃置道具复用/位置跳变)出 `审稿/logic_alerts_*.json`；喂给 `novel-review` 当机检深度增强 |
| `novel-simulate` | 多代理人「模拟读者」试读：构建差异化人格读者(小白/逻辑党/嗑糖党/毒舌)，`simulate_panel.py` 算确定性信号(爽点/逻辑/情感/套路关键词密度)+LLM 定性反馈，识别弃书点·爽点捕获率·受众兼容度，产留存先验喂 `novel-score` |
| `novel-balance` | 情节热力图与节奏平衡仪：扫全书情绪起伏/信息密度，识别高潮密集度·平淡铺垫期·节奏断裂点，自动给"注水警告"/"节奏脱节"预警，与 `novel-review` 节奏维度互补 |
| `novel-promote` | 宣发一体化与爆点挖掘：挖小说高光时刻(战斗/情感爆发/神反转)，生成抖音/小红书短视频脚本·预告片文案·引流切片建议，对接 `novel2drama` 线把文字爆点接到视觉宣发 |

## 三、song ——「创作歌曲 / 写歌」创作线（词 + 曲 + 演唱 → 成品歌）

`song` 是总调度：既能从主题/几个字/曲风**直接创作**一首带人声的成品歌，也能对已有 `写歌/<曲名>/`、歌词、曲风或半成品音频做**可编辑迭代**（改词、改结构、改曲风、重生成、多版挑版、换声、质检）。与 novel-author(写小说) 平行的创作线；产物落 `写歌/<曲名>/`（`词/lyrics.md` + `歌/song.wav`），交给 制MV(mv) 做视频。创作过程中总调度可按需调用 `song-lyrics` / `song-score` / `song-compose` / `song-cover` / `song-review` / `song-craft`。

| Skill | 职责 | 状态 |
|---|---|---|
| `song` | 创作歌曲/写歌总调度：从零创作或编辑迭代，按进度和用户意图调用子 skill | ✅ |
| `song-lyrics` | 访谈式作词 + 作词工艺知识库（结构/押韵/字数贴旋律/hook），**零安装** | ✅ |
| `song-craft` | 写歌线共享机器契约：`_设置/_meta/_进度` 字段、选择点、多版 take manifest 约定、AI 音频使用披露脚本 | ✅ |
| `song-compose` | 词→带人声的歌：云 Suno/Udio / 本地 ACE-Step(Mac可跑) / DiffRhythm；生成作曲任务包 + 多版登记/评分/挑版定稿 | ✅ |
| `song-cover` | 翻唱/换声：RVC / so-vits-svc | ✅ |
| `song-review` | 双模 QA：①作品质检（词可唱性/押韵/hook/结构 + 曲演唱试听清单 + 音频削波/静音/采样率 + 音色合规，机检+人判，出定位报告）②流程自审（联网对标→审 song skills→出优化建议）。非必经阶段，作词/作曲后或交 mv 前可跑 | ✅ |

> 唱歌的声音要装东西：TTS（CosyVoice/FishSpeech）不能唱；唱歌走音乐生成模型(Suno/Udio/ACE-Step/DiffRhythm)或歌声转换(RVC)。**克隆真人嗓需授权（2026 opt-in）**。正式出歌走多版 `歌/takes_manifest.json` 挑版；发布/交平台/交 MV 前用 `song-craft/scripts/ai_usage.py` 留 AI 音频使用披露。

## 四、mv ——「制MV」生产线（成品歌 → AI 音乐 MV 视频）

`mv` 是总调度，**输入 = 一首已做好的歌**（来自 写歌/ 或用户给），产物落 `制MV/<曲名>/成片_MV.mp4`。与 novel2drama(制漫剧) 平行：**写歌→制MV**，正如 **写小说→制漫剧**。**完全独立、自包含——不复用 n2d-* 或任何家族 skill**。

| 阶段 | Skill | 职责 | 状态 |
|---|---|---|---|
| 共享契约 | `mv-craft` | `_设置/_meta/_进度` 字段、选择点、clip/timeline/video jobs manifest 约定、AI 视觉使用披露脚本 | ✅ |
| 调度+立项 | `mv` | 扫 制MV 根，拷入歌+词，初始化选择和视觉蓝图，路由 | ✅ |
| 卡点 | `mv-beat` | librosa 检测 BPM+候选 tempo+能量图+鼓点+初始段落 → beatgrid | ✅ |
| clip/timeline 规划 | `mv-plan` | 从 beatgrid/lyrics/视觉蓝图生成 `clip_plan.json`、`timeline_manifest.json`、出图/出视频 prompt 包；沉淀 `action_family/action_peak/visual_motif/transition_motif`，给出图和视频继承 | ✅ |
| 出图 | `mv-image` | mv 自建：共享定妆 + 分段分镜 PNG；出图前提示 `MV一致性增强`（共享定妆+锚点 / 指定参考图 / 后端主体库 / +LoRA）；MV 单曲视觉一致性包（身份锚点/主色/段落 look/母题）锁一支歌内部稳定，不做 n2d 跨集强状态账本 | ✅ |
| 出视频 | `mv-video` | mv 自建：按 jobs manifest 多版图生视频、登记/评分/挑版并同步 timeline；动作知识库按段落和 beat 选择动作家族、动作峰值、转场母题 | ✅ |
| 卡拉OK字幕 | `mv-lyric-sync` | whisperx 词级对齐 → karaoke.ass / lyrics.lrc / alignment_report.json | ✅ |
| 合成 | `mv-compose` | 读 timeline 顺序 + 歌轨 + 卡拉OK烧录 → 成片_MV.mp4（自带 mv_compose.sh + render_lyrics.py） | ✅ |
| 质检·自审（横切） | `mv-review` | 双模 QA：①作品质检（规划/timeline/jobs 对账、视觉一致性/卡点节奏[clip 对齐 beatgrid·不等长]/卡拉OK字幕越界·对账/音画合成[成片时长·画幅·音轨]/AI披露/换脸合规，机检[+ffprobe]+人判，出定位报告）②流程自审（联网对标→审 mv skills→出优化建议）。非必经阶段，任意闸门或成片后可跑 | ✅ |

> 独立铁律：mv-* 即便与 n2d 逻辑相似也各写各的；只用通用外部工具（非 skill）。可借鉴 n2d 的一致性前置和模板化动作方法，但落成 mv 自己的 references：`mv-image/references/visual_consistency.md` 与 `mv-video/references/action_knowledge.md`。
> 输入歌本身的音质/词体检属 `song-review`，mv-review 不重复——只审歌轨进没进、卡点对不对。

## 五、ad ——「拍广告」生产线（客户需求 → AI 广告片）

`ad` 是总调度：把**一份客户需求 / 品牌产品**做成一条 AI 广告片。与 novel2drama/mv 平行的第五条生产线；产物落 `拍广告/<项目名>/成片_主片.mp4` + 多时长 cutdown + 多比例。这条线几乎覆盖了 写小说(创意/脚本) + 制漫剧(分镜→出图→出视频→配音→合成) 合起来的全套，独有**前端创意策划**（策略层）和**后端品牌包装/交付**。**完全独立、自包含——不复用 n2d-*/mv-* 或任何家族 skill**（与 mv/song 同，自带 `ad-craft` 契约）。

| 阶段 | Skill | 职责 | 状态 |
|---|---|---|---|
| 共享契约 | `ad-craft` | `_设置/_meta/_进度` 字段、选择点、**不拆集阶段表**、cutdown/多比例交付件约定、AI 使用+授权披露 | ✅ |
| 调度+立项 | `ad` | 扫 `拍广告/` 根；把客户需求结构化进 `需求/brief.json`；读 `_进度.md` 路由到阶段 skill | ✅ |
| 创意策划 | `ad-concept` | brief → big idea / 一句话主张 / 创意路线 / mood&reference / KV方向 / 故事线 | ✅ |
| 脚本+分镜+广告法机检 | `ad-script` | 脚本 pass（广告脚本+VO+秒级时间轴）+ **《广告法》违禁词机检硬闸门**；配音后分镜 pass（实测时长驱动 storyboard，对账总时长≈主片目标） | ✅ |
| VO配音 | `ad-voice` | voiceover.txt → 逐句音频 + vo.wav + 时长清单.json（驱动镜头时长）；克隆真人嗓硬闸门 | ✅ |
| 三层定妆库+出图 | `ad-image` | 共享定妆库（角色/代言人 + 场景 + **产品定妆 hero product**：包装/logo/品牌色零漂移）+ 逐镜首尾帧；视觉契约烤进首帧 | ✅ |
| 图生视频 | `ad-video` | 逐 Clip 视频 prompt + 模型路由 + **契约继承机检（品牌色/光位/轴线漂移=block）** + 首尾双帧接力 | ✅ |
| 剪辑包装+交付 | `ad-compose` | 拼 clips + 混 VO/音乐床 + 字幕(PNG overlay) + **品牌包装 end card** + **多时长 cutdown** + **多比例 reframe** + **交付规格(LUFS/安全框)** + AI标识水印 | ✅ |
| 质检/自审(横切) | `ad-review` | 双模 QA：产品一致性/品牌色/logo/字幕/音画/违禁词 + 流程自审 | ⏳ 二期 |

> **不拆集铁律**：广告不切「集」。一条主片是一个整体（可以很长）；多时长（30/15/6s）、多比例（16:9/9:16/1:1）、A·B 是**交付件 deliverable**，登记在 `_进度.md` 的「交付版本矩阵」，由 `ad-compose` 从主片重剪/reframe。
> **广告专有强化（相对 n2d/mv）**：① 客户需求 brief 作 source；② 创意策划策略层（novel 无）；③ **《广告法》违禁词/极限词机检**（绝对化用语「最/第一/国家级」、医疗保健极限词，`ad-script/ad_law_check.py` 命中即 block，带 pytest）；④ **产品定妆**（hero product 包装/logo/品牌色零漂移=三层定妆库第三层）；⑤ **品牌包装 + 多版本交付**（end card / cutdown / 多比例 reframe / 响度归一）。
> **音频先行**：VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本→配音后分镜），与 n2d 同构；广告常是「音乐床 + VO」混合驱动。
> **机器契约层**：阶段表、`_进度.md`/`_设置.md` schema、选择点目录、cutdown 交付件约定集中在 `skills/ad-craft/scripts/contract.py`（人读版 `ad-craft/references/contract.md`）。

## 公共能力（不属任何家族，谁都能调）

| Skill | 职责 |
|---|---|
| `shared-video-faceswap` | 通用**视频**换脸（FaceFusion，Mac可跑）+ 强制 AI 标识（打标调公共 `shared-watermark`）；**仅本人/授权/合成脸**，带合规闸门。制MV/制漫剧/单独使用都可调 |
| `shared-image-faceswap` | 通用**图片**换脸（同 FaceFusion 底座，单图秒级）+ 强制 AI 标识（打标调公共 `shared-watermark`）；**仅本人/授权/合成脸**，带合规闸门。出图阶段/单独使用都可调 |
| `shared-watermark` | 通用**水印**（图/视频同一工具，按扩展名自动判定）：①合规 **AI 标识**（法律强制·可见提示+元数据·**只加不去**）②**品牌/logo/账号**水印（文字或 logo·位置/透明度/大小可选）。faceswap 打标 + n2d/mv 合成阶段 + 单独使用都可调；Pillow+ffmpeg，无 libass 走 overlay |
| `shared-cleanup` | 通用**skill 瘦身清理**：扫描/删除 `skills/` 下低风险生成垃圾（`__pycache__`、pytest/mypy/ruff 缓存、`.DS_Store`、临时/备份文件等），默认 dry-run；placeholder skill / 大目录只报告不自动删。n2d/mv/song/novel/公共 skill 都可调 |

> 换脸/克隆真人 = deepfake，2026 强监管：须**肖像同意 + AI 标识水印**（中国《标识办法》、US DEFIANCE/NO FAKES）；shared-video-faceswap / shared-image-faceswap 已内置合规闸门，仅本人/授权/合成脸，且强制打标。两者共用同一 FaceFusion 安装；**打标统一调公共 `shared-watermark` skill**（图/视频同工具，原 label_watermark*.py 已合并进去）。`shared-watermark` 还能打品牌/账号水印（`--mode brand`），但**绝不**提供去水印。

---

> 五条线**互不依赖、各自自包含**：**写小说→制漫剧**、**写歌→制MV**（创作线产成品 → 生产线做视频，衔接只在成品文件层面），外加 **拍广告(`ad`)** 这条自带创意+生产的独立生产线（输入=客户需求）。各线不互相 import（ad-* 不复用 n2d-*/mv-*）。换脸是公共 `shared-video-faceswap`（视频）/ `shared-image-faceswap`（图片），水印是 `shared-watermark`。
