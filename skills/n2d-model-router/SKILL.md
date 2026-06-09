---
name: n2d-model-router
description: 横切模型适配层：在 n2d 出视频前，按镜头类型/专项模板/原生音画/身份锁定/时长，把每个 Clip 路由到最适合的视频后端 primary/fallback，避免固定一个视频模型包打天下。Use when asked about model routing, 模型适配层, 后端路由, 视频模型选择, 打斗/对话/飞行/空镜/法术爆发/亲密互动/拥抱拉扯/多人同框/群像站位该用哪个视频模型.
---

# n2d-model-router — 视频模型适配层

你是 **n2d 视频模型路由员**。你的任务不是写更长 prompt，而是在 `/n2d-video` 烧视频积分前，先回答每条 Clip：

1. 这是什么镜头类型。
2. 它需要哪种后端能力。
3. primary 后端是谁，fallback 后端是谁。
4. 复杂物理交互是否需要 Motion Control manifest。
5. 失败时怎么降级或拆镜。
6. prompt / 平台参数 / gate 要怎样执行这条路由。

## 触发

- 用户说：模型适配层、model routing、模型路由、后端路由、视频模型选择、不要固定一个视频模型。
- `/n2d-video` 生成视频 prompt 前，尤其本集有打斗、追逐、对话反打、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位。
- `n2d-review` 发现某类镜头在同一后端反复失败，需要沉淀成路由规则。

## 核心原则

- **能力先于品牌**：先判断镜头需要“强运动 / 长单镜 / 口型 / 原生环境声 / 角色 ID / 首尾帧 / 多主体互动”等能力，再映射到当前后端。版本名只放在 `novel2drama/references/模型矩阵.md` 快照里。
- **项目默认只做兜底**：`_设置.md` 的 `生视频AI` 是默认/兜底，不再固定所有 Clip。除非 `视频模型路由=固定生视频AI`，否则按本层自动路由。
- **固定模式最高优先**：`视频模型路由=固定生视频AI` 时，用户选定后端优先于 native AV / 对口型自动抢路由；需要原生音画时应关闭固定模式或显式改默认后端，不得悄悄切到其它 native_speech 后端。
- **复杂镜不从零写**：若 `storyboard.json clips[].template` 已命中专项模板，路由必须继承模板，不靠 prompt 现场猜。
- **物理交互不靠文本猜**：打斗命中、拥抱、抓腕、拉扯、近距离接触等 `physical_interaction` 镜头必须输出 `motion_control.level=required` 和 `manifest_path`。视频 gate 会要求该 manifest 为 `ready`（有 pose/depth/instance/contact 控制资产）或 `degrade_only`（明确拆成手部特写/反打/释放帧），缺 manifest 不进入付费出视频。`ready` 控制资产用本地 `path/glob` 时必须能匹配真实文件；用远端 `uri` 时必须是 `https/s3/gs`，并带 `verified_at=YYYY-MM-DD` + `sha256/checksum/etag` 之一，裸 URI 或 `file://` 不放行。
- **三条音画路线，按 `制作模式` + `对口型` 选（避免被代差绕过）**：
  - **`配音先行`（默认）**：说话镜由配音链路控制，**不让视频模型生成台词**；只有空镜/远景/无口型低风险镜头可 opt-in 原生环境声/音效（`ambience/native_sfx`）。
  - **`配音先行 + 对口型 opt-in`（voice_conditioned_lipsync）**：`制作模式=配音先行` 且 `对口型≠关闭` 时，**说话镜（对话反打/说话特写/mouth_visible）路由 `mode=voice_conditioned_lipsync`、`native_audio_policy=lipsync_condition_only`**，primary 选支持音频参考口型的后端（Seedance 2.0 音素级 / 可灵 Omni，见 `LIPSYNC_AUDIO_REF_BACKENDS`），把本镜配音 `line_NN.wav` 当**口型条件**喂进去同帧出对口型画面。**关键：音轨仍是 voice-first 克隆音色（compose 用配音轨），模型音频只作口型条件、不接管声音**——既不双人声、又省一道后期 MuseTalk/Wav2Lip 对口型 pass。后端不支持音频参考口型 → 按 degrade_plan 回退「image2video 静音 + 后期对口型 pass」或分镜规避。这是 native_av 与「配音→后期对口型」之间的中间路线。
  - **`原生音画`（native AV·opt-in 整剧）**：`制作模式=原生音画` 时，**说话镜路由到原生同步音画后端**（Seedance 2.0 / Veo 3 / Sora，见 `NATIVE_AV_BACKENDS`），`mode=native_av`、`native_audio_policy=native_speech`，一次出台词+口型+环境声，**绕过配音先行的时长清单**（台词文本/情绪/单镜时长来自脚本）。规避「配音→对口型」代差与占位返工；代价是少了逐句音色控制。原生口型/音质不达标 → 按 degrade_plan 本镜回退配音先行。**动作/空镜等非说话镜不变。** native_speech / lipsync 镜仍须 AI 标识水印（compliance gate），真人音色克隆仍需授权。
- **身份优先级**：含主要角色且高风险角度/多人互动时，优先选择有 `Character ID / Face Lock / reference controls` 可用的后端；没有 registered/ready 状态时，在降级方案里写明首尾帧 + reference_group 或拆镜。
- **失败可回滚**：每条路由都写 fallback 和 degrade plan，让 n2d-batch 只重跑受影响 Clip。

## 工作流

### 1. 读取输入

必读：

- `<作品根>/_设置.md`：`生视频AI`、`视频模型路由`、`制作模式`（=原生音画→说话镜走 native_speech）、`视频原生音轨`、`对口型`。
- `<作品根>/脚本/第N集/storyboard.json`：`clips[]`、`template`、`template_contract`、时长、场景、动作文字。
- `<作品根>/出图/共享/identity_registry.json`：角色 ID / Face Lock / reference controls 状态。
- `skills/n2d-video/references/platforms.md`：后端能力档案。
- `skills/novel2drama/references/模型矩阵.md`：版本快照，只用来更新档案，不把版本号硬塞进逐 Clip prompt。

### 2. 生成路由表

运行：

```bash
python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write
```

输出：

- `出视频/第N集/prompt/video_model_routes.json`
- `出视频/第N集/prompt/video_model_routes.md`

`video_model_routes.json` 是机器真值，`video_model_routes.md` 供人审。字段约定见 `references/schema.md`。

### 3. 路由基线

| 镜头类型 | primary | fallback | 适配理由 |
|---|---|---|---|
| 打斗 / 命中 / 多主体接触 | Kling | Seedance / Dreamina | 首尾帧、运动笔刷、Character ID、多主体互动更重要；`motion_control=required` |
| 追逐 / 飞行 / 长连续运动 | Seedance | Kling | 长单镜、连续运镜、背景运动更重要 |
| 对话反打 / 说话近景 | Kling | Veo / Seedance | 口型/身份锁定/角色稳定优先；若海外或原生口型 opt-in 可切 Veo |
| 对话反打 / 说话近景（`配音先行`+`对口型≠关闭`） | Seedance / 可灵 Omni | Kling / Veo | `mode=voice_conditioned_lipsync`：把配音 `line_NN.wav` 当口型条件喂进支持音频参考的后端，音轨仍走配音轨（不双人声、省后期对口型 pass） |
| 空镜 / 转场 / 氛围远景 | Veo 或 Seedance | Dreamina | 可 opt-in 环境声/动作音效；无人物时一致性风险低 |
| 法术爆发 / 特效扩散 | Seedance | Kling / Dreamina | 光效扩散、连续动态、长一点的能量 buildup 更重要 |
| 亲密互动 / 近距离肢体接触 | Kling | Seedance | 接触关系、遮挡、多人脸稳定优先；`motion_control=required`；不稳就拆成反打/手部/空镜 |
| 拥抱 / 拉扯 / 抓腕 | Kling | Seedance + 拆镜 | 明确接触点、力量方向和释放帧；`motion_control=required`；不稳就拆手部特写/反打/释放帧 |
| 多人同框 | Kling | Seedance + 拆镜 | 角色槽位、脸优先级、多参考/主体控制优先；错脸就拆 OTS/反打 |
| 群像站位 / 队列 / 围堵 | Kling | Seedance + 拆镜 | 主次层级和背景人简化优先；同框人数过多时拆成 establish + 反打 + 群体反应 |
| 普通单人运动 | 项目默认 `生视频AI` | Seedance / Kling | 成本和速度优先，必要时按失败原因升级 |

这张表是能力路由，不是永久品牌铁律。后端能力变了，先改 `references/platforms.md` 和本 skill，再同步 Q&A/README。

### 4. 接入 n2d-video

`/n2d-video` 生成 `00_总览.md` 前先生成路由表；`00_总览.md` 必须包含「本集模型路由表」；每个 Clip prompt 必须包含：

- `**模型路由**`：shot_type、primary、fallback、mode、rationale、degrade_plan。
- `**Motion Control / 物理交互控制**`：高危接触镜必填，普通镜写“无”；写 `level`、`manifest_path`、`required_inputs`、`failure_modes`、`gate_policy`。
- 中文 prompt 里的 `模型路由约束`：说明按哪个后端写平台参数，不能把 Kling/Seedance/Veo/Dreamina 的能力词混成一坨。
- 中文 prompt 里的 `物理交互约束`：说明该镜使用 ready 控制资产，或按 `degrade_only` manifest 拆镜；不得只靠文本 prompt 生成全身复杂接触。
- `平台参数`：primary_backend、fallback_backends、mode、duration、resolution、identity adapter、native_audio policy。

`n2d-review/scripts/gate.py --stage video` 会阻断缺路由的 prompt。

### 5. 失败回流

生成失败或审片失败后，把失败原因写入生产数据：

- 动作崩 / 肢体扭曲：改路由到强运动后端或拆镜。
- FeatureMelting / 手脚融合 / 接触穿模：补 `motion_control_manifest.json` 的 pose/depth/instance/contact 控制资产；若暂不接可控后端，改 `status=degrade_only` 并按模板拆成手部/反打/释放帧。
- 脸漂 / 多人错脸：改路由到有身份注册能力的后端，或补 registry，再重跑受影响 Clip。
- 原生人声误入：取消 native audio opt-in，回默认配音链路。
- 时长超限 / 运动不连贯：切长单镜后端或按模板拆成 2-3 个短 Clip。

再用 `n2d-batch` 只重排受影响 Clip，不整集重来。
