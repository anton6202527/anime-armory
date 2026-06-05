---
name: n2d-video
description: Stage 5 of novel2drama pipeline — for a 作品 episode whose 出图(PNG) is done, generate the per-Clip video prompts from 故事板.md and either invoke a local video-gen CLI (即梦 dreamina image2video / kling / veo / seedance) or step-by-step guide the user to generate manually on their default platform (default 即梦). Writes progress to `_进度.md` (视频 column). Use when asked to 出视频, 视频 prompt, 生成视频, 跑视频, image2video, or anything video-generation-related for a novel2drama project. Triggers 出视频, 视频prompt, 图生视频, image2video, 即梦视频, 可灵视频, Veo, Seedance, 运镜.
---

# n2d-video — Stage 5：视频 prompt + 生视频

你是 **AI 漫剧出视频制作**。本 skill 只关心一件事：把 出图齐（分镜设计→出图后）的一集，先生成"开箱即用"的视频 prompt（按 Clip 维度），然后调本机生视频 CLI（或一步步指导用户在即梦/可灵/Veo 上手动跑），最后把 MP4 落档 + 更新进度。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`生视频AI`、`视频分辨率`、`画幅`、`对口型`。

## 核心原则

- **图生视频为主，文生视频为辅**：每个 Clip 以出图阶段的 PNG 为首帧（可灵/部分平台支持首尾帧），视频 AI 只控制"动作 + 运镜"。纯空镜/转场/氛围镜头可文生视频。
- **原生音频静音铁律（2026 新坑）**：Veo 3.1 / Seedance 2.0 等会**原生生成同步音频**（环境音甚至台词）。本产线是**配音先行 + 合成阶段统一加音轨**，所以图生视频出的 clip **默认要静音原生台词**——否则与 n2d-voice 的配音轨**双人声打架**。调用时若平台有"静音/无音频/仅画面"开关就开；不能关的，在 prompt 里写"无对白、无旁白"，并在 `00_总览.md` 标记该 clip 含原生音轨，交 n2d-compose 处理（compose 默认丢弃 clip 原生人声，可选保留环境音垫底）。
- **多镜连拍（可选·opt-in）**：后端支持多镜叙事（Seedance 2.0 self-storyboard / 可灵多图参考）时，**同场景连续 3-6 镜可一条 prompt 连拍**一段，跨镜潜变量共享、更稳更省（详见 `references/platforms.md` 多镜字段、与 n2d-image 的「多镜一次性故事板」同源）。产出仍按 Clip 拆开落 `视频/`，进度按 Clip 计。不支持则自动回退一 Clip 一调。
- **共享视频库（空镜/转场跨集复用）**：反复出现的纯空镜/转场/氛围 clip（宫门推、烛火空镜、妖气扩散转场）= 共享资产，出一次落 `出视频/common/视频/`，跨集直接复用，别每集重生成（与出图的场景库同理，省视频积分）。带角色的镜头不进共享库（各集表演不同）。
- **产物归集铁律**：所有 prompt md 进 `出视频/第N集/prompt/`；**生成的 clip MP4 全部落 `出视频/第N集/视频/`**（供 /n2d-compose 归集合成）。废片去 `废料/出视频/第N集/`。
- **运动 + 运镜 + 动态细节三件套必写**：只写画面不写运动 → AI 会随机推断，常翻车。
- **导演视角八维（视频版）**：视频 prompt 是导演视角八维的"运动落地"——①镜头/③人物外貌/⑤场景/⑥光影/⑧画风**已由首帧 PNG 锁死**（出图阶段做完），视频阶段**只升级 ④动作→人物运动+表情变化、②机位→运镜、⑦情绪→张力词**，其余维度严禁重定（改了=与首帧打架=闪烁漂移）。详见 `novel2drama/references/导演视角prompt.md §三`。
- **锚点句复用 + 跨AI锚定句不重拼**：含角色的 clip，prompt 里**复用角色卡『锚点句』**（来自 `n2d-script/references/formats.md §1`）稳住跨镜脸/妆造；但**跨 AI 锚定句只在出图阶段拼**（已由首帧 PNG 承载），**视频 prompt 不再追加任何风格锚定句**——视频 prompt 针对的是已锚定的首帧。
- **运镜服务情绪/节奏，不是炫技**（`novel2drama/references/导演节奏.md §四/§五`）：从 `故事板.md` 的节奏注记派生运镜——逼近/聚焦=推近、释放/孤独=拉远、代入=跟、**高光/爽点=环绕或轻甩**、克制/压迫=固定。铺垫段运镜缓慢，爽点 Clip 运镜短促有冲击。每条视频 prompt 带一个**张力词**（克制/紧张/爆发/释放）锚定这条镜头的情绪强度。
- **平台差异在档案里**：单 Clip 时长 / 运镜词偏好 / 首尾帧机制 / 提示词语言 见 `references/platforms.md`。默认即梦 5~8s。
- **分辨率默认 720p，首次确认后沉默沿用**：调即梦（dreamina）或任何生视频 AI（可灵/Veo/Seedance…）出视频，**默认用 720p**（写在 `_设置.md`）。**首次出视频时**告知/确认一次：`默认 720p（省积分/快），也可选 1080p（更清晰/更贵），要改请打断` → 记入 `_设置.md` → 同项目之后**沉默沿用**，不再每条重复问；用户随时可改。
- **生视频调用优先级**：本机已装的官方 CLI → Bash 直调；没装 → 一步步指导手动；大批量可 spawn sub-agent。
- **废料归档**：所有废视频片段 → `制漫剧/<剧名>/废料/出视频/第N集/`，**不留在 Downloads**。
- **视频生成贵**：单条 5-10s 视频从几毛到几块不等，**比图贵 1-2 个数量级**。提示词写不好就废一条——所以**先在图阶段把所有视觉变量锁死**，视频阶段只调动作/运镜。

## 可选增强：对口型 lip-sync（opt-in · 说话特写才值得）

说话近景/特写（CU/MCU）若口型与配音对不上会很跳。**默认不做**（远景/侧脸/背身/旁白镜头看不出，不值这成本）。仅当**人脸正面说话的特写**且预算允许时启用：

- **平台原生**：可灵 3.0 等支持「对口型/唇形同步」——把该 Clip 的配音 `line_NN.wav` 喂给视频 AI 的 lip-sync 入口，让口型贴配音。
- **后期对口型 pass**：clip 出好后用通用对口型工具（如 LatentSync/Wav2Lip 类，本地）把口型对到配音轨；属合成前的可选层。
- 启用与否记入 `_设置.md`（选择点 `对口型`）；不启用时在分镜阶段就**少给正面大特写说话镜**（用侧脸/背身/空镜配旁白规避），是零成本的替代。

## 输入前置条件

- `_进度.md` 该集 `配音` ✅ + `分镜设计` ✅ + `出图` 列分子=分母。**Clip 时长读定稿 `故事板.md`（来自配音时长 `镜头时长.json`），不再用平台默认估**；平台档案只约束单 Clip 上限（如即梦 ≤8s，超限拆 Clip）。
- **占位闸门（出视频最贵，必查）**：读 `出视频/第N集/配音/时长清单.json`，若有 `占位:true` → **拒绝出视频**并提示先 `/n2d-voice` 换真实配音重跑 + 回跑 `/n2d-script 阶段2` 重定时。占位时长出的 clip 长度全错，是返工成本最高的坑。
- 否则报错并建议用户先调 `/n2d-script` 或 `/n2d-image`

## 工作流

### 阶段 A — 视频 prompt 生成

源数据：`脚本/第N集/故事板.md`（阶段2·分镜设计 写的 Clip 表，时长配音驱动）+ `出图/第N集/镜头N_*.png`（出图阶段的定稿首帧）。

输出：`出视频/第N集/prompt/00_总览.md` + `出视频/第N集/prompt/01_clips.md`（按 Clip 一段一块）。

**单 Clip prompt 块标准格式**（详见 `references/prompt_format.md §1`）：

```markdown
## Clip K（时长 7s · 镜头 N1+N2）

**首帧**：`出图/第N集/镜头N1_<描述>.png`
**尾帧**（可选，可灵/部分平台支持）：`出图/第N集/镜头N2_<描述>.png`
**场景**：{场景名}（夜晚/内）

### 视频 prompt（中文，目标=即梦/可灵/Seedance）
\`\`\`
人物运动：{角色 A 动作} → {角色 A 表情变化}；
镜头运动：{推/拉/跟/环绕/固定 + 速度词}；
动态细节：{烛火摇曳 / 晨雾流动 / 衣袂飘动 / 妖气扩散 ...};
（末尾视情况追加平台风格词，详见 platforms.md）
\`\`\`

### 视频 prompt（英文，目标=Veo/海外）
\`\`\`
character motion: ...; camera motion: dolly in slowly; dynamic detail: ...
\`\`\`

### 平台参数
- 模型 / 时长 / 帧率 / 画幅 / image2video 强度

### 检查清单
1. ✅ 首帧 PNG 已落档
2. ✅ 人物动作明确可推断
3. ✅ 镜头运动词明确（不只是"运镜"这种模糊词）
4. ✅ 动态细节 ≥1 条
5. ✅ 复杂度可控（无超复杂打斗/多人混战）

### 降级方案
（若 image2video 推不动该动作，怎么改 prompt 或拆 Clip）
```

完成后：`_进度.md` 该集 `视频prompt` 列填 ✅。旧项目若表头缺 `视频prompt`，先迁移一次：
```bash
python3 <novel2drama skill>/progress.py ensure-col <作品根> 视频prompt ⬜
python3 <novel2drama skill>/progress.py set <作品根> 第N集 视频prompt ✅
```

### 阶段 B — 扫描本机生视频 CLI

```bash
# 已知视频 AI CLI 一次性探测
for cli in dreamina kling veo seedance; do
  command -v "$cli" >/dev/null 2>&1 && echo "found: $cli ($(command -v $cli))"
done
```

按 `references/cli_registry.md` 优先级选与目标视频 AI 同家的 CLI（默认即梦 → dreamina）。

### 阶段 C — 分支决策

**分支 1：找到匹配 CLI**
- 选定后告知用户："找到 X，将用它出视频，**分辨率默认 720p（也可 1080p）**。如不同意请打断。"
- 按 Clip 一段一条调用（详见"调用规范"）
- **批量加速可选**：>6 个 Clip 时，可 spawn 2-3 个 sub-agent 并发调用 CLI
- 中间筛选 → 废视频 `废料/出视频/第N集/`，定稿 MP4 → `出视频/第N集/视频/Clip<K>_<描述>.mp4`

**分支 2：本机无合适 CLI**
- 告知用户："本机未检测到合适的视频 AI CLI（已扫 dreamina/kling/veo/seedance）。可由我一步步指导你在 [默认即梦 web] 上跑 image2video，每跑一段回传，我帮你筛选 + 落档。"
- 进入"手动指导模式"：
  - 一次一 Clip，列出 prompt + 首帧路径 + 平台参数
  - 用户上传首帧 + 粘贴 prompt → 平台跑 → MP4 下载
  - 用户回传 MP4（或路径）→ Claude 评判 → 通过则用户 mv 到 `出视频/第N集/视频/`，不通过则建议调整 prompt（多数情况是动作过复杂，需简化）

### 阶段 D — 进度回写 + 推进

每出一条定稿 MP4：
1. MP4 落档到 `出视频/第N集/视频/Clip<K>_<描述>.mp4`
2. `出视频/第N集/prompt/00_总览.md` 对应 Clip 行状态改 ✅
3. 回写 `视频` 列：`python3 <novel2drama skill>/progress.py set <作品根> 第N集 视频 X/Y`

本集 `视频` 列 = 分母时：
```
第K集 视频完成（X/X）
- 总时长：~Y 秒
- Clip 数：X
下一步：
- 合成：/n2d-compose <作品根> 第K集  → 视频/ + 配音轨 + BGM + 烧字幕 → 成片
- 或继续 /n2d-video <作品根> 第K+1集
```

## 调用规范（找到 CLI 时）

**通用流程**（每个 Clip）：

1. 从 `出视频/第N集/prompt/01_clips.md` 读出本段 prompt + 首帧路径 + 平台参数
2. 走 CLI：
   ```bash
   <cli> image2video \
       --image <出图/第N集/镜头N1_xxx.png> \
       --prompt "$(cat <prompt 块>)" \
       --duration 7 \
       --aspect 9:16 \
       --resolution 720p \
       --out <出视频/第N集/视频/ClipK_<描述>.mp4>
   ```
   （各 CLI 具体子命令/参数见 `references/cli_registry.md`）
3. 检查产出：人脸不抖 / 动作合理 / 运镜与 prompt 一致 → 通过；否则进 `废料/出视频/第N集/`
4. **首尾帧机制**（可灵专属）：若目标 = 可灵且 Clip 含尾帧 PNG → 用 `--first <PNG> --last <PNG>` 双图引导

**关于"为什么大多数视频跑两遍才稳"**：image2video 的运动估计有随机性，同 prompt 不同 seed 出来差异可观。预算允许时**每个 Clip 默认跑 2 条**，挑视觉一致性更好的那条。

## 详细参考

- **导演视角八维（视频版·只调动作/运镜/张力，其余继承首帧）**：`novel2drama/references/导演视角prompt.md §三`
- **视频 prompt 单块格式 + 故事板 Clip 表 → prompt 派生规则**：`references/prompt_format.md`
- **平台档案 + 运镜词偏好 + 首尾帧机制**：`references/platforms.md`
- **已知视频 CLI 清单 + 调用模板**：`references/cli_registry.md`
- **翻车 + 修正案例**：`novel2drama/Q&A.md` 的 Q1（先图后视频）、Q14-Q17（CLI 安全）、Q18（图 AI vs 视频 AI 关系）

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视频 prompt 只写画面不写运动 | 必含人物运动 + 镜头运动 + 动态细节 |
| 设计超复杂打斗/人群 | 改为 AI 易生成的单人/双人动作、固定或简单运镜；过复杂的拆 Clip |
| 跨集首帧画风跳变 | 出图阶段的定妆/分镜 PNG 都基于共享层定妆图复用，本 skill 直接用即可 |
| 用文生视频做有角色的镜头 | 改用 image2video，首帧用出图阶段 PNG |
| 让 Veo/Seedance 原生台词进 clip | 默认静音原生人声（开静音/写"无对白"），避免与配音轨双人声打架 |
| 反复空镜/转场每集重生成 | 进 `出视频/common/视频/` 共享库跨集复用 |
| 正面大特写说话镜口型对不上 | 启用对口型 lip-sync，或分镜阶段改用侧脸/背身/空镜配旁白规避 |
| 单 Clip 时长超平台上限（即梦 >8s / Veo >8s） | 拆成两个 Clip，尾帧 = 下一首帧 |
| 废视频留在 Downloads | 全部归档 `废料/出视频/第N集/`，Downloads 清空 |
| 装第三方逆向 CLI | 违 ToS、封号风险，仅装官方 |
| 全部串行生 12 条 Clip | 可 spawn 子 agent 并发，但每账号 ≤4 并发避免限速 |
