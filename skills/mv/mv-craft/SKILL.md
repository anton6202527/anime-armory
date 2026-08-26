---
name: mv-craft
description: Shared machine contracts and deterministic helpers for the mv-* skill family — settings-first state, output-health receipts, clip/timeline/OTIO contracts, identity/asset registries, provider submission evidence, candidate freshness, AI disclosure, provenance, release decision, and named handoff. Other mv-* skills reference these by file path; users can also invoke directly for MV pipeline contract, manifest, registry, disclosure, provenance, or release questions. Triggers mv contract, mv-craft, MV合约, 歌曲输入时序, timeline_manifest, clip_plan, video_jobs, identity_registry, AI视觉使用披露, MV合规留痕, MV发布交付.
---

# mv-craft — 制MV线共享契约

`mv-craft` 是 `mv-*` 家族的机器单一真值源，不生成画面、不出视频。它只沉淀字段、选择点、阶段表、manifest 约定和合规留痕脚本，避免 `mv-image` / `mv-video` / `mv-compose` 各自解释同一件事。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `skills/mv/mv-craft/references/选择点与偏好.md` 读项目值、全局默认；仍缺失的普通、可逆项采用本线推荐值写回并继续。合规、当前像素/视频与最终验收、不可逆发布/覆盖及预算合同变化才停。

本 skill 涉及的选择点：`MV用途`、`歌曲输入时序`、`MV视觉风格`、`MV规划粒度`、`卡点策略`、`生图模型`、`生图渠道`、`MV一致性增强`、`生视频模型`、`生视频渠道`、`演唱口型`、`字幕语言` 等。

`mv-craft` 与 `mv/run.py next --json` 为**已初始化项目**提供合同、完成态和机器可消费前沿，不是完整 batch/provider runner。外层可自动 chain 免费确定性 helper；缺 `_进度.md` 时当前 setup card 只是不可执行 legacy 占位，须先用 `init_project.py --title ... --out ... --song-timing ...` 初始化。真实付费提交、当前像素/视频验收、picture lock 和发布仍由对应入口执行。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md` / `_meta.json`、按 `歌曲输入时序` 决定阶段顺序、生成 clip/timeline/video job manifest 时 |
| 单一状态与完成态 | `scripts/state_contract.py` + `scripts/completion.py` | 审计/显式同步 `_设置.md`、`_meta.json`、`_进度.md`；阶段 health 只作证据，最终 `verdict` 用一个 canonical release digest + 当前 handoff 真人收据判 `blocked\|ready_for_acceptance\|complete` |
| 阶段验收标准 | `references/production-standards.md` | 查看每阶段输入真值、机器证据、人工签收、阈值与回流责任；区分导演/剪辑/音乐/连续性/交付 QC |
| 身份/资产注册 | `scripts/identity_registry.py` | 从任意角色卡、状态变体、场景卡、视觉蓝图和 clip_plan 动态生成 registry；共享实现不含作品模板 |
| 参考资产需求 | `scripts/identity_registry.py` | 同步生成身份/状态、交互道具、复用场景和 VFX 的参考缺口 |
| 正式版 readiness | `scripts/formal_readiness.py` | 按实际歌长、计划覆盖、参考、picture lock、QC 与签收判断；不再用固定 90 秒/12 镜规则 |
| 制片与锁版 | `scripts/production_pack.py` + `render_animatic.py` + `picture_lock.py` + `export_otio.py` | 生成 V1+A1+markers 的 OTIO/receipt、真实 animatic，并把具名 picture lock 绑定到规范化编辑 hash、plan、prompt、首尾帧和歌曲 |
| 来源链 | `scripts/provenance.py` | 在披露完成后汇总输入、生成图/视频、母版、交付件 hash；可生成 C2PA 2.4 AI disclosure/ingredients 并分开核验结构、签名、信任与时间戳 |
| 候选新鲜度 | `skills/mv/_lib/freshness.py` + `skills/mv/_lib/refresh.py` | 模型/渠道/生图后端候选过期检查、刷新快照和 provenance；正式视频能力图 90 天后 fail-closed |
| 阶段 gate | `scripts/gate.py` | `mv-plan` / `mv-video` / `mv-lyric-sync` / `mv-compose` 等正式阶段开跑前做确定性前置检查 |
| 进度回写 | `scripts/progress_set.py` + `scripts/mv_utils.py` | 阶段脚本完成后回写 `_进度.md`，并同步 `_meta.has_song/has_lyrics` |
| AI 使用披露 | `scripts/ai_usage.py` | 发布前记录视觉/视频/音乐模式、模型+渠道、目标平台/法域、真人与写实分类、人工贡献，并由真实姓名签收 |
| 平台/法域发布决策 | `scripts/release_decision.py` + `references/release-evidence-schema.md` | review health 通过后，按带版本规则集复验 schema v3 上传资产、平台原始证据、声明/标识和真实发布 URL；不伪装自动上传 |
| 权利清单 | `scripts/rights_manifest.py` | 正式付费生成前记录歌曲、视觉参考、真人肖像、品牌、场地与编舞的权利断言；不是法律意见 |

## 共享脚本

```bash
python3 skills/mv/mv-craft/scripts/gate.py "<制MV作品根>" plan
python3 skills/mv/mv-craft/scripts/progress_set.py "<制MV作品根>" plan
python3 skills/mv/mv-craft/scripts/identity_registry.py "<制MV作品根>"
python3 skills/mv/mv-craft/scripts/formal_readiness.py "<制MV作品根>" --no-fail
python3 skills/mv/mv-craft/scripts/completion.py verdict "<制MV作品根>" --write --json
python3 skills/mv/mv-craft/scripts/production_pack.py "<制MV作品根>"
python3 skills/mv/mv-craft/scripts/render_animatic.py "<制MV作品根>"
python3 skills/mv/mv-craft/scripts/picture_lock.py "<制MV作品根>" --reviewer <name> --notes "逐镜确认当前 animatic 与剪辑决定"
python3 skills/mv/mv-craft/scripts/export_otio.py "<制MV作品根>"
python3 skills/mv/mv-craft/scripts/state_contract.py audit "<制MV作品根>" --json
python3 skills/mv/mv-craft/scripts/rights_manifest.py "<制MV作品根>" --song owned --visual-reference owned --likeness not_applicable --brand not_applicable --location not_applicable --choreography not_applicable --reviewer <name>
python3 skills/mv/_lib/freshness.py

python3 skills/mv/mv-craft/scripts/ai_usage.py "<制MV作品根>" \
  --visual-mode AI-generated \
  --video-mode AI-generated \
  --publish-target 抖音 --territory CN --realism stylized \
  --real-person none --music-mode human \
  --human-contribution "导演、剪辑与逐镜人工挑版" --reviewer <真实姓名>

python3 skills/mv/mv-craft/scripts/provenance.py "<制MV作品根>" \
  --final 成片_MV.mp4 --master 成片_MV_master.mov

python3 skills/mv/mv-craft/scripts/release_decision.py "<制MV作品根>" \
  --platform 抖音 --territory CN --operator <真实姓名> --notes "发布前复核" \
  --platform-declaration-status completed --visible-label-status completed \
  --music-metadata-status completed --platform-policy-review-status completed \
  --machine-label-method platform_metadata --platform-evidence <项目内证据路径> \
  --machine-evidence <项目内证据路径> --submission-status uploaded \
  --upload-receipt <项目内 schema-v3 回执JSON> --published-url <实际作品URL>

python3 skills/mv/mv-craft/scripts/completion.py complete "<制MV作品根>" handoff \
  --reviewer <真实姓名> --notes "已核验上传回执与发布页"
```

`ai_usage.py` 和 `provenance.py` 默认在写出证据后调用完成态控制器：若上游未满足，证据文件保留，但命令返回非 0 且不推进阶段。`--no-progress` 只用于明确的证据单写、迁移或测试，不得当作正式流程成功的替代路径。

输出：
- `合规/ai_usage.json`
- `合规/AI使用说明.md`
- `设定/identity_registry.json`
- `设定/asset_registry.json`
- `设定/reference_requirements.json`
- `分镜/reference_plan.json`
- `分镜/animatic_manifest.json`
- `分镜/animatic.mp4`
- `分镜/timeline.otio`
- `生产数据/otio/otio_receipt.json`
- `生产数据/image_acceptance/image_acceptance.json`
- `生产数据/color/color_input_manifest.json`
- `生产数据/review/review_receipt.json`
- `制片/shot_list.json`
- `制片/setup_schedule.md`
- `制片/take_log.csv`
- `制片/picture_lock_color_checklist.md`
- `制片/finishing_delivery_checklist.md`
- `制片/picture_lock.json`
- `合规/provenance.json` + `合规/c2pa_manifest.json`（请求 C2PA 时）
- `合规/release_decision.json`
- `合规/handoff_receipt.json`
- `合规/rights_manifest.json`
- `生产数据/formal_readiness/formal_readiness.json`
- `生产数据/formal_readiness/formal_upgrade_plan.md`
- `skills/mv/references/candidate_snapshots/*.json`

## 设计原则

> 跨线通用原则（选择点不写死 C1/C2、阶段回写 B5、脚本不伪装云端自动化 B4、合规闸门 D1…）见 [`docs/skill-design-principles.md`](../../../docs/skill-design-principles.md)，此处只列 mv 线特有原则。mv 的选择点目录：`skills/mv/mv-craft/references/选择点与偏好.md`。

- **manifest + receipt 是源头**：clip 时长、接缝分类、尾帧、prompt、已登记视频都落 manifest；歌曲/歌词/蓝图/设置、OTIO、animatic、QC 和签收用完整 SHA-256 绑定。`mv-compose` 不再凭文件名猜时间线。
- **设置是选择点真值，收据是完成态真值**：`_设置.md` 决定当前路线；`_meta.json` 与 `_进度.md` 不一致时先 audit，再显式 sync。写成 done 不能替代产物健康度；缺失或过期收据会返回 `stale_receipts`。
- **registry 锁一致性**：任意数量的角色、状态变体、道具、场景、VFX 用项目派生 ID、状态图和 reference plan 传递；共享代码不得硬编码某支 MV 的人物或资产。
- **脚本先过 gate（本线前置条件）**：正式产物阶段默认调用 `scripts/gate.py`，缺最终歌、beatgrid、正式视觉蓝图、首帧或已选视频时先停下；歌词只在字幕或唱演口型启用时必需，纯器乐无字幕路线合法跳过。

## 正式工具链边界

- 正式 OTIO 收据要求 Python 环境安装官方 `opentimelineio`，并成功 adapter round-trip；缺依赖会明确阻断，不把手写 JSON 当已验证交换件。
- C2PA 仅在选择 Content Credentials 时需要 `c2patool`。生产模式还必须提供外部 signer、trust anchors 与可信 TSA 时间戳；脚本按当前 `validation_results` 分开核 `claimSignature.validated`、credential trust、`timeStamp.validated`/trusted，不能把 `signature_info.time` 当 TSA。内置测试证书只供开发验证，永不记为 trusted。不要把私钥直接传给脚本。
- 上传回执 schema v3 要求显式 `uploaded_asset.path+sha256`；C2PA 路线必须精确上传当前 provenance 绑定的 signed output，其他路线绑定当前 `成片_MV.mp4`。API 路线保存原始 JSON 并用 JSON Pointer 重新提取 remote asset id、时间和 URL；UI 截图/PDF 只是具名人证。C2PA 也只证当前 claim/签名链的可验证状态，不证明声明事实本身为真，不替代平台声明或上传证据。完整 schema 与 API/UI JSON 示例见 `references/release-evidence-schema.md`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 直接手工改写 manifest.json 内容 | manifest 文件是各 stage 传递数据的机器契约，手动修改极易破坏其字段规范，应通过对应的阶段脚本重新生成 |
| 只靠 prompt 锁主角，不落 registry | 跑 `identity_registry.py` 生成身份/资产/参考计划，再让 mv-image/mv-video 消费这些 ID |
| demo 被误当正式版 | 跑 `formal_readiness.py`；有 blocker 时只能当 demo/reference，不能发布为正式 MV |
| 只有 clip_plan，没有制片组织 | 跑 `production_pack.py` 生成 shot list、setup schedule、take log 和 picture lock/color pass 清单 |
| 发布前遗漏披露或把 C2PA 当作全部披露 | 先写具名、设置绑定的 `ai_usage.json`，再生成 provenance；C2PA 只是机器可读信号，平台声明开关、可见标识、音乐元数据与上传回执仍由 `release_decision.py` 独立核验 |
| 手工把 `_进度.md` 写成完成 | 用 `completion.py health` 核验真实产物；所有产物阶段的 `[x]`、`✅`、`1/1` 都必须经过同一完成态控制器 |
| 偏好设定硬编码 | 管线中的卡点策略/粒度等不可写死，须经由此处统一定义的方式并从 `_设置.md` 读取 |
| 用 compose fallback 绕过正式 gate | `--allow-fallback` 只能写 `预览/fallback_preview.mp4`，不会写正式成片/母版、进度、delivery QC 或 provenance；正式交付必须回到 gate |
