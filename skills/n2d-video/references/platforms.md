# 平台档案（Platform Profiles）

> **机器真值源**：视频后端别名、`max_clip_seconds`、原生音画后端集合等可执行字段集中在 `skills/n2d/_lib/n2d_platform_profiles.py`。本文件负责人读解释；若两者不一致，以 `_lib` 模块为准，并同步修本文。

本 skill 的核心产物——分镜剧本、角色/场景卡、爽剧节拍、双语字幕——**平台无关**。
各 AI 生成平台的差异，由下面的「平台档案」描述。

---

## 三项架构：内容轴(剧情) × 平台皮 × 调用渠道（2026-06 起）

skill 改为**图 AI + 生视频模型 + 生视频渠道**：
- **生视频模型**：决定最终成片风格基线 + image2video 运动估计分布 → "主"
- **生视频渠道**：决定实际通过哪个产品/API/CLI 调用模型（如即梦/Dreamina、豆包、海螺AI、Google Gemini API、Runway API）
- **图 AI**：出图工具，可以与生视频模型同厂，也可以独立（Gemini / DALL-E / Flux 等）

```
image prompt = [图AI 的 prompt 写法] + [生视频模型的图像风格锚定句]
```

**默认结构 = 图 AI(`生图AI` 所选官方/已登录后端，默认 Codex，可选 Dreamina/即梦官方 CLI) + 生视频模型(`_设置.md 生视频模型`，新作品首跑菜单选择，默认 Seedance 2.0) + 生视频渠道(`_设置.md 生视频渠道`，默认 即梦/Dreamina)**。第三方逆向 CLI、`同视频AI` / `同视频模型` 含糊口径和 web 自动化出图仍禁。

### 图 AI ≠ 生视频模型时的强制规则

1. image prompt **必须**在末尾追加目标生视频模型的"图像风格锚定句"（见各档案）
2. 锚定句作用：强制图 AI 输出**生视频模型训练分布里的视觉特征**（面孔/风格/光感）→ 让视频模型的 image2video 运动估计稳定
3. 图 AI 按 `生图AI` 选择点统一到一个官方后端；视频模型读 `_设置.md` 的 `生视频模型`，调用渠道读 `生视频渠道`，新作品首跑选择一次
4. 锚定句语言：按目标生视频模型/渠道的消化风格选；即梦/可灵渠道通常用中文版，Veo 等海外渠道用英文版

### 推荐组合速查

> 与 `n2d-image/references/platforms.md` 同一张表，保持一致：**图阶段按 `生图AI` 统一官方/已登录后端；Dreamina/即梦官方 CLI 可用于出图；视频阶段按 `_设置.md 生视频模型` + `生视频渠道` 执行，首跑菜单选择一次**。

| 场景 | 组合 | 备注 |
|---|---|---|
| 国风短剧（Seedance via 即梦） | `生图AI` 所选官方/已登录图后端 + Seedance 锚定句 → `生视频模型=Seedance 2.0` + `生视频渠道=即梦/Dreamina` | 图默认 Codex；视频模型与渠道分开记录；全项目统一图后端 |
| 国风短剧（即梦闭环） | Dreamina/即梦官方 CLI 出图 → `Seedance 2.0` via 即梦/Dreamina | 已登录会员可直调；全项目统一图后端 |
| 国风短剧（Kling） | `生图AI` 所选官方图后端 + Kling 锚定句 → `生视频模型=Kling 3.0` + `生视频渠道=可灵/Kling` | 只换视频模型/渠道时不重写图后端；换图后端需整集统一 |
| 海外英文短剧 | `生图AI` 所选官方图后端 + Veo 锚定句 → `生视频模型=Veo 3.1` + `生视频渠道=Google Gemini API` | 全英文 prompt 优先 |
| 禁止 | 第三方逆向 CLI / `同视频AI` 或 `同视频模型` 含糊口径 / web 自动化出图 | 未授权路径禁用 |

---

## 通用 prompt 结构（所有平台共用）

```
主体 + 外貌/妆造锚定 + 动作表情 + 环境/光线 + 景别构图 + 画风词 [+ 生视频模型风格锚定句]
                                                                  ↑
                                                              跨AI 时必拼
```

画风词与统一负面词以项目 `global_style.md` 为准。角色一致性一律：**先出定妆照 → 设为该平台的角色参考/首帧 → 后续复用**（见 formats.md §1）。

> **角色一致性·用后端原生能力（2026-06，治 image2video 脸漂）**：image2video 每帧独立推理会**累积漂移**，尤其 极端角度/大暗部/人物过小 时。除首帧锁脸外，**有原生「角色ID/Face-Lock」的后端要把定妆图喂进去当持久角色参考，不只当首帧**——Kling 3.0 **Character ID**（注册定妆为角色 ID，跨 clip ~90% 稳）、Seedance 2.0 **Face Lock**（单主参考 + 几何约束锁五官比例，正脸/3⁄4 最稳）、Veo 3.1 **reference controls**（角色/风格参考）。短 clip + 强参考是减漂主路；缺原生 ID 的后端退回「首帧 + 首尾双帧 + 强 end_state 文字」。所有后端 ID / Face Lock / LoRA 状态以 `出图/共享/identity_registry.json` 为准，不写在临时 prompt 备注里。

### `identity_registry.json` adapter key 对照

| 平台 | registry 位置 | 生产用法 |
|---|---|---|
| 即梦 / Dreamina | `identity_adapters.video.dreamina` | 通常 `fallback_reference_group`：首帧 + 尾帧 + reference_group + 强 continuity |
| 可灵 Kling | `identity_adapters.video.kling` | `registered/ready` 时把 Character ID 写入平台参数；未注册则 fallback |
| Seedance | `identity_adapters.video.seedance` | `registered/ready` 时启用 Face Lock / reference；正脸、3/4 侧最稳 |
| Veo | `identity_adapters.video.veo` | `registered/ready` 时启用 reference controls；英文 prompt 同步写身份锁定约束 |

## 档案字段（每个平台都按这几项描述）

提示词语言 · 画幅 · **分辨率** · 单 Clip 时长 · 角色一致性机制 · **身份注册层字段** · **原生音画策略** · 运镜/动态词偏好 · **图像风格锚定句** · 负面词机制 · 特殊语法/注意

> **分辨率铁律**：所有平台**默认 720p**（省积分/出片快），1080p 仅在用户明确要时用。开跑前把选项给用户确认一次，用户指定后按用户的来。

> **单 Clip 上限铁律（2026-06）**：单 Clip 时长上限**按所选后端档案，不是一刀切 8s**。**能一镜到底就别切碎**——更长单镜 = 更少拼接缝 = **跨镜一致性更稳 + 更省**。只在 Clip 时长（=所含镜头时长之和，配音驱动）**超该后端上限**时才拆 Clip，拆点尾帧=下一首帧。各后端当前上限见下方档案；n2d-script 阶段2 拆 Clip 时**读该后端上限值**，不要写死 8s。后端能力会变，以 `n2d/references/模型矩阵.md` 最新快照为准。

## 关键帧/多帧能力口径（2026-06-13）

机器真值源在 `skills/n2d/_lib/n2d_platform_profiles.py::frame_control`；gate 和 runner 读机器档案，本文只解释给人看。**主流后端并不都支持首/中/尾三帧同一次请求**。至少首帧图生视频普遍可用；首尾两帧在 Dreamina、Luma/Ray、Veo 3.1、Kling 路径可用或按档案保守放行；任意中段时间轴锚帧目前只在本仓库核验过 Dreamina `multiframe2video` 原生路径。

| 后端/渠道 | 时间轴帧能力 | n2d 落地 | fallback |
|---|---:|---|---|
| Dreamina / 即梦 `multiframe2video` | 2-20 张，段长 0.5-8s | 原生吃 `[首, 中锚..., 尾]`，一条连续 Clip，无 concat | 若帧数/段长不合法，退 first+last `frames2video` 或单首帧 |
| Dreamina / 即梦 `frames2video` | 首尾 2 张 | 常规接缝锁定；近景大表情起止表情插值 | 中段需要改 `multiframe2video` 或拆段 |
| Kling / 可灵 | 首尾 2 张（保守档） | 打斗/接触/释放帧适合 first+last；Character ID 另管身份 | `_mid` 不能假定原生生效，拆 A→M、M→B 或 reroute |
| Seedance 直连 | 按首帧/参考图保守处理 | 只有执行渠道是 Dreamina 时，帧能力改按 Dreamina | 直连要先复核当前 API，再付费批量 |
| Veo 3.1 / Gemini API | first+last + 最多 3 张 reference images | 首尾锁接点，reference 管角色/风格 | 中段时间轴锚不是 arbitrary keyframe，需 extend/split 或 reroute |
| Luma / Ray | `frame0` + `frame1` | 首尾锁起止画面 | 中段锚需拆段/interpolate |
| Runway / Pika / Sora | 未在本仓库核验任意多帧 | 按首帧/参考媒体保守处理 | 当前官方 API 明确支持前不得吞 `_mid`；gate 应 WARN |

用户问“每个 Clip 分几张帧”时，先回答能力边界：**首尾两帧是较稳的通用 fallback，但不是所有 API 都无条件支持；首/中/尾三帧不是主流统一能力，只有 Dreamina 原生多帧已在本仓库打通。** 因此 n2d 默认仍可以规划三帧契约来保证审查和可升级，但执行前必须让 `video_preflight` 核验：后端不能吃中锚时，明示用户改首尾帧、拆段接力或换原生多帧后端。

---

## 模型路由能力速查（n2d-model-router）

`生视频模型` 是项目默认/兜底，不是每个 Clip 的固定模型；`生视频渠道` 是执行调用入口。`视频模型路由=自动按镜头路由` 时，`n2d-model-router` 按下表生成 `video_model_routes.json`，`n2d-video` 再按逐 Clip primary/fallback 写 prompt 和平台参数。

| 镜头类型 | primary | fallback | 关键能力 | prompt / gate 要求 |
|---|---|---|---|---|
| 打斗 / 命中 / 双人接触 | 可灵 Kling | Seedance / 即梦 | 首尾帧、运动笔刷、多主体互动、Character ID；后续可接 ComfyUI/LTX pose/depth/instance 控制 | `mode=frames2video`；`motion_control=required`；一 Clip 只做一个命中动作；必须有 ready/degrade_only manifest |
| 追逐 | Seedance | 可灵 / 即梦 | 长连续运动、背景层速度、单镜上限更长 | 锁人物姿态，速度来自背景/前景遮挡/镜头跟拍；多人追逐拆正反打 |
| 飞行 / 御剑 / 掠空 | Seedance | 可灵 | 长单镜、连续运镜、动背景 | 人物姿态保持，云层/山河/衣袂向后运动；大转向必须有尾帧或拆镜 |
| 对话反打 / 说话近景 | 可灵 Kling | Veo / Seedance | 身份稳定、口型/唇形能力、参考控制 | 默认仍 `no_native_speech`；若口型关闭，优先侧脸/背身/反应镜规避 |
| 空镜 / 转场 / 氛围远景 | Veo 或 Seedance | 即梦 | 原生环境声/动作音效、低身份风险、文生视频 | 仅低风险 opt-in：mouth_visible=no、speech_policy=no_native_speech；否则生成静音画面交 compose 配声 |
| 法术爆发 / 符阵 / 雷劫 | Seedance | 可灵 / 即梦 | 光效连续扩散、蓄力→释放→余波、较长单镜 | 锁特效颜色/形状/方向；可 opt-in 动作音效但禁止人声；失败拆蓄力/爆发/余波 |
| 亲密互动 / 搀扶 / 牵手 | 可灵 Kling | Seedance | 接触点、遮挡、近距离身份保持；必要时 pose/depth/instance 控制 | `motion_control=required`；必须写 contact point、occlusion_order、body_part_ownership；不稳就拆手部/反应/过肩 |
| 拥抱 / 拉扯 / 抓腕 | 可灵 Kling | Seedance + 拆镜 | 首尾帧、接触点、力量方向、近距离身份保持；高危时需要 pose/depth/instance/contact_map | `motion_control=required`；必须写 force_direction 和 release_frame；无 ready manifest 就 degrade_only 拆手部/反打/释放帧 |
| 多人同框（2-3 具名） | 可灵 Kling | Seedance + 拆镜 | 多参考/主体控制、角色槽位、脸优先级 | 写 character_slots / face_priority / overlap_rules；**2-3 具名走 Kling，≥5 具名走 Sora**，错脸就拆 OTS/反打 |
| 多人同框（5+ 具名）/ 群像站位 / 队列 / 围堵 | **Sora** | 可灵 Kling / Seedance + 拆镜 | 5+ 角色一致性、主次层级、背景人简化 | 2026：Sora 2 对 5+/群像同框最稳，超 Kling 2-3 张脸上限；写 character_slots/screen_positions/focus_hierarchy，仍不稳按 degrade_plan 拆组 |
| 普通单人运动 | `_设置.md 生视频模型` | Seedance / 可灵 | 成本、速度、普通 image2video | 若同类失败两次，改最近的专项镜头类型重新路由 |

路由表只写能力层判断；具体版本名、SOTA 快照和升级触发在 `n2d/references/模型矩阵.md`。若新后端在某类镜头上明显更稳，先更新本表和 `n2d-model-router`，再同步 README/Q&A。

## 档案：即梦 AI（默认）

- **提示词语言**：中文优先（英文备用）
- **画幅**：竖版 9:16（短剧）
- **分辨率**：**默认 720p**（也支持 1080p；开跑前把选择给用户）
- **单 Clip 时长**：image2video 5~8 秒；其 **文生视频后端 = Seedance 2.0，长单镜可达 ~15s**（需长镜时走该路径，见 Seedance 档案）
- **角色一致性**：定妆照 → 设为「角色参考图 / 图生图」→ 分镜出图与视频首帧复用
- **身份注册层字段**：`identity_adapters.video.dreamina`（默认 `fallback_reference_group`）
- **原生音画策略**：默认 `audio_intent=none`；若使用 Seedance 后端产生原生音轨，只对空镜/无口型环境声 opt-in，禁止原生台词
- **运镜/动态**：必写 人物运动 + 镜头运动 + 动态细节（推/拉/跟/环绕/固定）
- **图像风格锚定句**（图AI ≠ 即梦时拼入图prompt）：
  - 中文：`中国古代东方面孔，国风写实漫剧风格，电影级光影，暗黑宫廷氛围，皮肤通透感，竖版9:16`
  - English：`cinematic Chinese ancient-fantasy webcomic aesthetic, Eastern Asian face, dramatic chiaroscuro, dark palace atmosphere, vertical 9:16`
- **负面词**：可写进 prompt 或负面框
- **CLI**：`dreamina`（`curl -s https://jimeng.jianying.com/cli | bash` 安装；需高级会员）
- **注意**：中文语义理解好；避免超复杂打斗/多人混战/高频切换

## 档案：可灵 Kling

- **提示词语言**：中文友好（中/英皆可）
- **画幅**：9:16（也支持 16:9）
- **分辨率**：**默认 720p**（也支持 1080p；开跑前把选择给用户）
- **单 Clip 时长**：5~10 秒；**单 clip 可含多镜（Kling 3.0 最多约 6 镜）**，能在一条 clip 里承载更长连续叙事/多景别
- **角色一致性**：**首尾帧控制**（首帧图 + 尾帧图）；图生视频；4 参考图可建 360° 主体；**Kling 3.0 Character ID**——把定妆注册成角色 ID 跨 clip 引用（~90% 稳，优于纯首帧，多角色/换景尤其用）
- **身份注册层字段**：`identity_adapters.video.kling`（`mode=character_id`；`registered/ready` 必填 `id` 或 `handle`）
- **原生音画策略**：支持音画/口型能力时也不默认接管 n2d 配音；仅低风险环境声/动作音效 opt-in，正面说话镜走配音或 lip-sync
- **运镜/动态**：可用「运动笔刷」框定主体运动轨迹；镜头语言（推拉摇移）写清。故事板可对关键 Clip 标注**首帧/尾帧两张关键图**
- **图像风格锚定句**：
  - 中文：`中国古代东方面孔，影视级国风写实，自然电影光感，皮肤通透真实质感，竖版9:16`
  - English：`cinematic Chinese realistic webdrama, photoreal Eastern Asian face, natural film lighting, vertical 9:16`
- **负面词**：写进 prompt 描述
- **API**：官方 API（kling.kuaishou.com/dev）
- **注意**：首尾帧 + 运动笔刷是其强项，复杂运动可拆成"首帧静态→尾帧到位"两图引导

## 档案：Seedance（字节）

- **提示词语言**：中/英皆可，镜头语言强
- **画幅**：9:16 / 16:9
- **分辨率**：**默认 720p**（也支持 1080p；开跑前把选择给用户）
- **单 Clip 时长**：**单镜可达 ~15s（Seedance 2.0）**——长单镜 = 更少拼接缝、跨镜漂移更少，本可一镜到底的段落别切碎
- **角色一致性**：首帧图 → 图生视频；多镜头连续叙事能力较强；原生音视频联合生成；**Seedance 2.0 Face Lock**——单主参考 + 几何约束锁五官比例/位置（正脸、3⁄4 侧最稳；比多图嵌入更死守正脸）
- **身份注册层字段**：`identity_adapters.video.seedance`（`mode=face_lock`；`registered/ready` 必填 `reference` 或 `id`）
- **原生音画策略**：原生音视频联合是强项，但 n2d 默认仍禁原生人声；环境声/法术声/破空声可低风险 opt-in，compose 默认低音量混入
- **运镜/动态**：支持较复杂的连续运镜/多机位描述（可在一个 prompt 写"分镜A→分镜B"）
- **图像风格锚定句**：**同即梦**（字节自家，训练分布相同）
- **负面词**：prompt 内
- **注意**：适合一条 prompt 承载稍长的连续动作；即梦 CLI 的 `text2video` 后端就是 Seedance 2.0

## 档案：Veo / 海外（Google Veo 等）

- **提示词语言**：**英文优先**（可直接复用 `字幕_英文` 的语感写 prompt）
- **画幅**：9:16（竖版短剧）/ 16:9
- **分辨率**：**默认 720p**（也支持 1080p；开跑前把选择给用户）
- **单 Clip 时长**：约 8 秒（Veo 3.1 可 extend 接续更长；48kHz 原生同步对白）
- **角色一致性**：首帧图 → 图生视频；**Veo 3.1 reference controls**（角色/风格参考，3 张参考图控制）；英文角色锚定句须稳定复用（人名用统一音译）
- **身份注册层字段**：`identity_adapters.video.veo`（`mode=reference_controls`；`registered/ready` 必填 `id` / `handle` / `reference`）
- **原生音画策略**：原生同步音频强，但正式 n2d 漫剧默认不让 Veo 生成角色台词；海外/预览可对空镜环境声 opt-in，保留原片音轨需无 n2d-voice 配音轨
- **运镜/动态**：英文电影镜头术语（dolly in / pan / tracking shot / orbit）
- **图像风格锚定句**：`cinematic Chinese ancient-fantasy aesthetic, photoreal Eastern Asian face, dramatic film lighting, fine film grain, vertical 9:16`
- **负面词**：部分版本不支持独立负面框，写进 prompt 或改为正向描述
- **API**：Google Cloud Vertex AI
- **注意**：海外投放搭配 `字幕_英文.srt`；系统提示用游戏化英文

---

## 图 AI 档案（出图工具，不是生视频模型）

> 这里只列**作为图 AI 时**的写法特征。生视频模型看上面档案。

### 禁止：第三方逆向 / web 自动化出图
图片阶段按 `生图AI` 统一到一个官方/已登录后端；Dreamina/即梦官方 CLI 可出图。生视频模型/渠道另由 `生视频模型` + `生视频渠道` 选择，图阶段用所选后端生成首帧并按需拼生视频模型锚定句。

### Gemini-Imagen（Google）
- **提示词语言**：英文最稳，中文次之
- **prompt 长度**：偏好"描述性英文段落"，不要短关键词列表
- **参考图**：支持（图生图 / Multi-image input）
- **强项**：质感真实、光感细腻
- **弱项**：东方面孔需要显式描述（默认会偏西方），**所以生视频模型/渠道偏国风系（Seedance via 即梦、Kling/可灵）时锚定句必加**
- **CLI**：`gemini-cli`（订阅制）

### DALL-E 3 / gpt-image-1（OpenAI）
- **提示词语言**：英文为主
- **强项**：构图想象力强、艺术感
- **弱项**：写实人脸不如 Imagen / Flux；亚洲脸特征容易卡通化
- **API**：OpenAI Images API

### Flux Pro（Black Forest Labs / Replicate）
- **提示词语言**：英文为主
- **强项**：照片级写实、皮肤质感
- **弱项**：默认好莱坞审美，亚洲脸需要 LoRA 才稳
- **API**：Replicate / fal.ai

### Stability SDXL / SD3
- **可控性**：最高（开源，支持 LoRA / ControlNet）
- **门槛**：需自托管 + 调参，不适合直接用
- 适合进阶玩家做"风格统一返工"

---

## 如何新增一个平台（保持拓展性）

1. 在本文件复制一段「档案：XXX」，填上面 8 个字段（**必含**"图像风格锚定句"中英双版）
2. 若该平台 prompt 与即梦差异较大，可在该集 `素材清单.md` 里对该平台**另起一组 prompt 并标注平台名**（如 `【Kling·首帧】…` / `【Kling·尾帧】…`）
3. 在项目 `global_style.md` 的"目标视频模型 / 生视频渠道 / 目标图AI"三行记上即可。**核心分镜/角色卡/字幕无需改动**——只换 prompt 的平台适配层。
