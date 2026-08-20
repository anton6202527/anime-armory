# MV 生产标准与签收矩阵

> 版本：2026-08-20。机器字段以 `mv-craft/scripts/contract.py`、`gate.py` 与 `completion.py` 为准；本文件解释为什么这样分工、每一阶段凭什么签收。

## 总原则：导演视角合理，但不能让“导演”独占所有终判

把 agent 设为“专业 MV 导演”适合处理视觉概念、表演、镜头、场面调度、色彩剧本和审片意见；它不等于完整后期团队。正式生产至少分五个责任视角：

1. 导演/创意：歌曲解释、视觉母题、表演、镜头意图。
2. 剪辑：段落结构、切点、动作相位、接缝、picture lock、OTIO。
3. 音乐/歌词：母带真值、拍号/小节首/段落边界、实唱歌词时间轴。
4. 美术/连续性：身份、服化道、场景拓扑、道具状态、色彩脚本。
5. 调色/交付 QC：色彩管理、编码、音画时长、响度/真峰值、母版和 provenance。

同一个人可以兼任，但签收维度不能合并成一句“导演觉得可以”。

## 阶段签收矩阵

| 阶段 | 输入真值 | 机器必须证明 | 人工必须签什么 | 失败回流 |
|---|---|---|---|---|
| 立项/权利 | 歌曲、歌词、视觉参考、真人/品牌/场地/编舞来源 | `_设置.md`、`_meta.json`、`rights_manifest.json` 字段完整 | 明确第三方素材的许可范围；同源原创按仓库默认作者自有 | setup/rights |
| 歌曲入库 | 唯一正式 `歌/song.*`；歌词按需 | 文件可读、SHA-256 稳定；需要字幕/唱演时歌词存在 | 这是要发布的母带，不是试听/占位版；纯器乐且无字幕/口型可无歌词 | song_ingest |
| 节拍与结构 | 当前正式歌曲 + `_meta.section_timings` | `source_audio_sha256`；beats/downbeats 严格递增；sections 从 0 到歌尾连续覆盖；`timing_review` 具名 | 拍号、小节首相位、段落起止逐耳确认；自动 onset 只当候选 | mv-beat |
| 歌词时间轴 | 当前歌曲/人声 stem + 已知歌词 | 已知文本强制对齐，ASR 不得改动歌词；歌曲/歌词 hash；逐行时间单调；文字覆盖率只叫 coverage，不得冒充 alignment confidence；WhisperX 原始分数明确未校准、非歌声专用、不可单独验收；stem→master offset/drift 有可复算证据 | 正式接受严格二选一：经声明校准且适用于歌声的声学/逐音素证据，或具名逐行听审+非空依据；两者均绑定当前输入 hash | mv-lyric-sync |
| 视觉蓝图 | 歌曲结构、按需歌词、用途、画幅 | 非 rough；含核心视觉概念、身份/场景锚、palette/section look、母题 | “这首歌为什么要这样看”成立；段落变化有因果，不是套模板 | mv-script |
| Clip/时间线 | 已签收 beatgrid、歌词、蓝图、设置 | `inputs_sha256` 全输入收据；clip/timeline 顺序与时长一致；段落边界不被成本上限吞掉；动作峰值实际落在镜内确认拍；每个出缝有分类合同 | 景别/运镜/动作/表演层次、歌词意象、轴线和视觉覆盖 | mv-plan |
| 节奏预检 | 当前 plan + beatgrid + song | 新鲜 `pacing_prescore`；等长嫌疑、总时长、重拍对齐、副歌/主歌密度均可复算 | 指标只是证据；是否采用主歌长镜/副歌碎切由歌曲和概念决定。未显式设阈值时不做主观硬挡 | mv-plan / mv-script |
| 两层出图 | identity/asset/reference 注册表 + clip prompt | 所属图片可解码；主角定妆包 ready（≥3 张多角度参考）；每张图有具体 model + channel + prompt/reference + asset SHA-256 收据；B14 pre/post gate、完整机器 QC 均通过；权威 `image_acceptance.json` 逐资产绑定当前 generation/QC/hash 与具名视觉签收。旧 `--accept-degraded` 只能记录仍未接受，不能把 block 变 pass | 身份、服化道、道具、构图、手部、色彩；`match_action` 镜的尾帧确实能交给下一镜；签收人真实具名、理由具体 | mv-image |
| Animatic/Picture Lock | 当前首/尾帧、正式歌、clip/timeline、OTIO | animatic 输出 hash；OTIO 有 V1+A1、段落/接缝 markers，所有 RationalTime 为整数帧，并由正式 OpenTimelineIO adapter round-trip；picture lock 绑定规范化编辑 hash、上游文件和全部帧/prompt | 叙事覆盖、切奏、动作峰值、接缝意图、空间方向、身份、色彩、字幕安全区具名签收 | mv-plan / mv-image |
| 视频任务/挑版 | 已锁画时间线、图片、版本化 model×channel capability | jobs schema v4 绑定 plan/settings/capability freshness；无法解析路线 fail-closed；提交收据记录实际 refs+角色+SHA、controls 双 hash、provider request/job 或具名 manual adapter；多镜头母片按真实媒体生成具名 cut map；每 take 具名评分且全部 selected；inherit/QC/视频 SHA 当前 | 基础四维：motion/identity/beat_fit/clarity；连续镜另评 seam_fit；演唱镜另评 lip_sync；人工渠道核实“实际提交”而非计划描述 | mv-video / mv-image |
| 视频接缝签收 | 逐镜首/中/尾帧 + seam contract | 逐缝风险信号；签收绑定 selected video hashes 和 seam-contract hash | 按接缝类别验收，不能用同一标准：卡点切允许有意跳变；动作匹配切必须接姿态相位、运动方向、视线、道具和光位 | mv-video / mv-plan |
| 合成/交付 | timeline、全部 selected clips、A1 正式歌曲、字幕 | 正式模式不可绕 gate；逐输入 schema v2 色彩清单精确绑定当前视频，full→limited 显式变换，HDR/未知色域硬拦；clip 默认 trim/尾帧 hold；音画差 ≤ max(100ms, 2帧)；ProRes/PCM + BT.709 H.264/AAC；最终 PCM 对原歌首/中/尾互相关并检查 offset/drift | 字幕可读、调色连贯、歌曲母带未被无意改变 | mv-compose / mv-video |
| 披露/来源链 | 已稳定 final/master + 当前设置/模型/渠道/平台/法域 | 先写具名 `ai_usage.json`，再生成完整 provenance；请求 C2PA 时使用 2.4 `ai-disclosure`/ingredients，并把 embedded/structural/signature/trust/timestamp 分开。测试证书永不当 trusted | 人工贡献、真人/写实分类、音乐模式、目标法域准确；生产签名与 TSA 例外有责任人 | mv-craft |
| 总审 | 母版、交付版、delivery QC、披露与 provenance | 全量机检 0 block；具名 review receipt 精确绑定 final/master/delivery/provenance/ai_usage 当前 SHA | 完整观看首/中/尾，移动端/大屏抽检，接受结论与备注具名 | mv-review / 对应责任阶段 |
| 发布/交平台 | review receipt + 当前合规与交付资产 | 带版本平台/法域规则决策；平台声明、可见标识、机器标签、音乐元数据、政策复核分别记录；schema v3 上传回执绑定实际上传资产的 path+SHA（C2PA 路线必须是当前 signed output），API JSON 用 JSON Pointer 重取 remote id/time/URL，UI 截图/PDF 只作为具名观察；真实作品 URL；具名 handoff receipt | 操作人确认平台 UI 实际完成并说明所见；UI 观察是人证而非机器证明，C2PA 也不替代平台声明、可见标签或上传字节证明 | mv-craft / 平台操作人 |

## 接缝分类（不是一个“转场”字符串）

- `beat_cut`：确认重拍上的有意硬切。允许景别、姿态和色块跳变；仍须守身份、画风和切点。
- `section_break`：音乐段落边界。允许 setup/palette 有根据地变化；要读得出新段落而不是随机换景。
- `match_action`：同段落连续动作。必须守姿态相位、motion vector、screen direction、eyeline、prop state、lighting；默认要求尾帧目标。模型不支持首尾帧时，走多镜头一次生成或剪辑匹配复核，不能伪装已提交尾帧。
- `terminal`：歌尾收束。检查稳定落幅和歌曲尾音，不靠 `-shortest` 意外截歌。

颜色直方图、pHash、脸 embedding 只提供证据：卡点切的大色差不是自动错误；动作匹配切的大结构跳变才进入接缝复核。

## 重定时与声音政策

- 默认 `trim_hold`：素材长则裁，素材短则用稳定尾帧补足；保留动作原速度。
- `retime` 是逐镜显式决定，需记录原因。不得因为生成时长不合就批量 setpts，把舞蹈、嘴型和物理运动一起拉坏。
- 正式歌曲是唯一 A1。生成视频的原生音轨一律不混入 MV 母带；需要环境声/拟音时应另建可审计独立轨，而不是把模型随机生成的歌曲叠进来。
- 不自动把音乐母带归一到某个流媒体 LUFS。QC 比较输入歌与输出的 integrated loudness；真峰值 >0 dBTP 阻断，>-1 dBTP 提醒复核。

## 多镜头模型的使用边界

支持多镜头的模型可把同一 section、同一 setup、总时长在模型能力内的相邻 clips 组成 `sequence_units`，用生成侧连续性减少接缝漂移。一次生成不等于一次签收：结果仍按锁定切点拆回逐 clip，分别登记、评分、挑版和 QC。跨段落、跨 setup 或超过能力时长不得为了省调用强并。

## 官方依据（实时核验快照）

- OpenTimelineIO 是剪辑决定交换格式，支持多轨、外部媒体、transition、marker；不把媒体嵌在 `.otio` 内：<https://opentimelineio.readthedocs.io/en/latest/>
- YouTube 官方推荐 SDR 为 BT.709、H.264 High、4:2:0、AAC/48kHz、Fast Start，并建议沿用源帧率：<https://support.google.com/youtube/answer/1722171>
- EBU R128 定义节目响度和 true-peak 测量；本线只借其测量方法/真峰值安全线，不把广播 -23 LUFS 套到音乐母带：<https://tech.ebu.ch/files/live/sites/tech/files/shared/r/r128v5_0.pdf>
- WhisperX 用强制音素对齐提供词级时间戳；MV 使用“已知歌词强制对齐”，不让转写结果改词：<https://arxiv.org/abs/2303.00747>
- Seedance 2.5 官方说明 30 秒 one-take，并支持最多 30 图、10 视频、10 音频灵活参考；当前产品渠道与 API 状态仍需分别核验：<https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5>
- Gemini 视频总览当前推荐 Omni Flash 作为 Gemini API 默认视频入口；Omni 仍是 preview，公开页没有足以固化全局时长/fps/分辨率的稳定矩阵，故本线只作 adapter-required 候选：<https://ai.google.dev/gemini-api/docs/video>、<https://ai.google.dev/gemini-api/docs/omni>
- Kling VIDEO 3.0 官方指南说明原生音频、Elements 和多镜头叙事：<https://app.klingai.com/cn/quickstart/klingai-video-3-model-user-guide>
- Veo Gemini API 官方文档列出 reference images、首尾帧、4/6/8 秒、分辨率、24fps 与音频等组合约束：<https://ai.google.dev/gemini-api/docs/video>
- Runway 当前高质量模型为 Gen-4.5，公开工作流以 T2V/I2V 为主；Act-Two 则是基础视频后再用真实表演驱动嘴型/表情的独立表演通道：<https://help.runwayml.com/hc/en-us/articles/46974685288467-Creating-with-Gen-4-5>、<https://help.runwayml.com/hc/en-us/articles/42311337895827-Performance-Capture-with-Act-Two>
- Luma Ray3.2 官方说明最多 16 个 keyframes、20 秒 1080p 与官方 API/HDR 路线：<https://lumalabs.ai/news/introducing-ray-3-2>
- C2PA 2.4 定义 `c2pa.ai-disclosure`、ingredient 与 human oversight 等结构；可信发布还需验证签名、信任链与时间戳：<https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html>
- 中国《人工智能生成合成内容标识办法》自 2025-09-01 施行，发布用户有主动声明等义务；具体平台 UI 操作必须留真实证据：<https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm>
