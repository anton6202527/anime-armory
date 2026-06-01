---
name: n2d-video
description: Stage 3 of novel2drama pipeline — for a 作品 episode whose Stage 2 (PNG) is done, generate the per-Clip video prompts from 故事板.md and either invoke a local video-gen CLI (即梦 dreamina image2video / kling / veo / seedance) or step-by-step guide the user to generate manually on their default platform (default 即梦). Writes progress to `_进度.md` (视频 column). Use when asked to 出视频, 视频 prompt, 生成视频, 跑视频, image2video, or anything video-generation-related for a novel2drama project. Triggers 出视频, 视频prompt, 图生视频, image2video, 即梦视频, 可灵视频, Veo, Seedance, 运镜.
---

# n2d-video — Stage 3：视频 prompt + 生视频

你是 **AI 漫剧出视频制作**。本 skill 只关心一件事：把 Stage 2 PNG 齐的一集，先生成"开箱即用"的视频 prompt（按 Clip 维度），然后调本机生视频 CLI（或一步步指导用户在即梦/可灵/Veo 上手动跑），最后把 MP4 落档 + 更新进度。

## 核心原则

- **图生视频为主，文生视频为辅**：每个 Clip 以 Stage 2 出的 PNG 为首帧（可灵/部分平台支持首尾帧），视频 AI 只控制"动作 + 运镜"。纯空镜/转场/氛围镜头可文生视频。
- **prompt / 产物分离铁律**：每个 `出视频/` 目录（`common/` 跨集复用片段 或 `第N集/`）都分两层——所有 prompt md 进 `prompt/` 子目录，生成 MP4 **平铺**在 prompt/ 的同级父目录。详见 `novel2drama/references/architecture.md` "prompt / 产物分离铁律"章节。
- **运动 + 运镜 + 动态细节三件套必写**：只写画面不写运动 → AI 会随机推断，常翻车。
- **平台差异在档案里**：单 Clip 时长 / 运镜词偏好 / 首尾帧机制 / 提示词语言 见 `references/platforms.md`。默认即梦 5~8s。
- **生视频调用优先级**：本机已装的官方 CLI → Bash 直调；没装 → 一步步指导手动；大批量可 spawn sub-agent。
- **废料归档**：所有废视频片段 → `作品集/<剧名>/common/废料/出视频/第N集/`，**不留在 Downloads**。
- **视频生成贵**：单条 5-10s 视频从几毛到几块不等，**比图贵 1-2 个数量级**。提示词写不好就废一条——所以**先在图阶段把所有视觉变量锁死**，视频阶段只调动作/运镜。

## 输入前置条件

- 作品根存在，`_进度.md` 该集的 8 类素材 + `出图prompt` + `出图` 三组列均 ✅（出图列分子 = 分母）
- 否则报错并建议用户先调 `/n2d-script` 或 `/n2d-image`

## 工作流

### 阶段 A — 视频 prompt 生成

源数据：`脚本/第N集/故事板.md`（Stage 1 写的 Clip 表）+ `出图/第N集/镜头N_*.png`（Stage 2 出的定稿首帧）。

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

完成后：`_进度.md` 该集**新增 `视频prompt` 列填 ✅**（若进度表当前没这一列，本 skill 第一次跑时追加表头）。

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
- 选定后告知用户："找到 X，将用它出视频。如不同意请打断。"
- 按 Clip 一段一条调用（详见"调用规范"）
- **批量加速可选**：>6 个 Clip 时，可 spawn 2-3 个 sub-agent 并发调用 CLI
- 中间筛选 → 废视频 `common/废料/出视频/第N集/`，定稿 MP4 → `出视频/第N集/Clip<K>_<描述>.mp4`

**分支 2：本机无合适 CLI**
- 告知用户："本机未检测到合适的视频 AI CLI（已扫 dreamina/kling/veo/seedance）。可由我一步步指导你在 [默认即梦 web] 上跑 image2video，每跑一段回传，我帮你筛选 + 落档。"
- 进入"手动指导模式"：
  - 一次一 Clip，列出 prompt + 首帧路径 + 平台参数
  - 用户上传首帧 + 粘贴 prompt → 平台跑 → MP4 下载
  - 用户回传 MP4（或路径）→ Claude 评判 → 通过则用户 mv 到 `出视频/第N集/`，不通过则建议调整 prompt（多数情况是动作过复杂，需简化）

### 阶段 D — 进度回写 + 推进

每出一条定稿 MP4：
1. MP4 落档到 `出视频/第N集/Clip<K>_<描述>.mp4`
2. `出视频/第N集/prompt/00_总览.md` 对应 Clip 行状态改 ✅
3. `_进度.md` 该集 `视频` 列分子 +1

本集 `视频` 列 = 分母时：
```
第K集 视频完成（X/X）
- 总时长：~Y 秒
- Clip 数：X
下一步：
- 合成（Stage 4 当前不在 skill 范围）：在剪映/CapCut/FFmpeg 把 视频/ + voiceover.txt + bgm.txt + 字幕_{中/英}.srt 合成成片
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
       --out <出视频/第N集/ClipK_<描述>.mp4>
   ```
   （各 CLI 具体子命令/参数见 `references/cli_registry.md`）
3. 检查产出：人脸不抖 / 动作合理 / 运镜与 prompt 一致 → 通过；否则进 `common/废料/出视频/第N集/`
4. **首尾帧机制**（可灵专属）：若目标 = 可灵且 Clip 含尾帧 PNG → 用 `--first <PNG> --last <PNG>` 双图引导

**关于"为什么大多数视频跑两遍才稳"**：image2video 的运动估计有随机性，同 prompt 不同 seed 出来差异可观。预算允许时**每个 Clip 默认跑 2 条**，挑视觉一致性更好的那条。

## 详细参考

- **视频 prompt 单块格式 + 故事板 Clip 表 → prompt 派生规则**：`references/prompt_format.md`
- **平台档案 + 运镜词偏好 + 首尾帧机制**：`references/platforms.md`
- **已知视频 CLI 清单 + 调用模板**：`references/cli_registry.md`
- **翻车 + 修正案例**：`novel2drama/Q&A.md` 的 Q1（先图后视频）、Q14-Q17（CLI 安全）、Q18（图 AI vs 视频 AI 关系）

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视频 prompt 只写画面不写运动 | 必含人物运动 + 镜头运动 + 动态细节 |
| 设计超复杂打斗/人群 | 改为 AI 易生成的单人/双人动作、固定或简单运镜；过复杂的拆 Clip |
| 跨集首帧画风跳变 | Stage 2 的定妆/分镜 PNG 都基于共享层定妆图复用，本 skill 直接用即可 |
| 用文生视频做有角色的镜头 | 改用 image2video，首帧用 Stage 2 PNG |
| 单 Clip 时长超平台上限（即梦 >8s / Veo >8s） | 拆成两个 Clip，尾帧 = 下一首帧 |
| 废视频留在 Downloads | 全部归档 `common/废料/出视频/第N集/`，Downloads 清空 |
| 装第三方逆向 CLI | 违 ToS、封号风险，仅装官方 |
| 全部串行生 12 条 Clip | 可 spawn 子 agent 并发，但每账号 ≤4 并发避免限速 |
