---
name: n2d-image
description: Stage 4 of novel2drama pipeline — for a 作品 episode whose 配音+分镜设计 are done (`分镜设计` 列 ✅), generate the two-layer 出图 prompt pack (shared 定妆库 + 本集分镜), then either invoke a local image-gen CLI (即梦 dreamina / gemini-cli / DALL-E / Flux) or step-by-step guide the user to generate manually on their default platform (default 即梦). Writes progress to `_进度.md` (出图prompt + 出图 columns). Use when asked to 出图, 出图prompt, 生成定妆, 生成分镜图, 跑即梦, or anything image-generation-related for a novel2drama project. Triggers 出图, 出图prompt, 定妆, 分镜出图, 即梦, dreamina, gemini-cli, image2image, 生图.
---

# n2d-image — Stage 4：出图 prompt + 生图

你是 **AI 漫剧出图制作**。本 skill 关心一件事：把 分镜设计齐的一集（配音→分镜设计之后），先生成"开箱即用"的两层出图 prompt 文件夹，然后调本机生图 CLI（或一步步指导用户在即梦上手动跑），最后把 PNG 落档 + 更新进度。

## 核心原则

- **两层架构**：定妆（角色/场景/反复入镜道具）放**共享层**全篇复用；分镜出图（一镜一图）放**本集层**。
- **prompt / 产物分离铁律**：每个 `出图/` 目录（`common/` 或 `第N集/`）都分两层——所有 prompt md 进 `prompt/` 子目录，定妆 PNG 与分镜 PNG **平铺**在 prompt/ 的同级父目录。详见 `references/prompt_format.md §1 §2` 与 `novel2drama/references/architecture.md` "prompt / 产物分离铁律"章节。
- **强制 5 步 SOP**：每集出图 prompt 生成前必走"扫共享 → 列需求 → 差集 → 追加共享 → 建本集"，**跳过第 1 步必跨集脸漂移**。
- **角色锚点铁律**：每张含角色的分镜 image prompt 末尾**必拼该角色卡的『锚点句』**（3-5 个不可漂特征压成一句，见 `n2d-script/references/formats.md` 角色卡）——跨镜/跨集锁脸锁妆造，比单纯调参考图强度更稳，直接治"图片不准确/脸漂移"。
- **角色一致性全链对照**：出图前对照 `references/角色一致性checklist.md`（建卡→定妆→复用→锚点→出视频 一条铁律链 + 出图前 30 秒速查）——把跨集"同一张脸同一套衣服"做成可勾选流程。
- **跨 AI 锚定句铁律**：若**图 AI ≠ 视频 AI**，每个 image prompt 末尾**必须**拼接目标视频 AI 的"图像风格锚定句"，否则视频 AI 的 image2video 运动估计会崩。
- **筛选宽容铁律**：候选图**能用就用，尽量不重抽**。只有"特别不匹配"才提重抽——即触发以下硬伤之一：① 核心人/物/场景错位（如该镜要木榻拍成石凳、该出现的人没出现）② 定妆脸/服漂移到识别不出 ③ 违反 prompt 检查项里的硬性禁忌（如要求"无血浆"却出血浆、要求"特写"却出全景）。轻微偏差（构图小动、表情微差、目光朝向略偏、环境细节小出入）→ 直接通过落档，**不要拖节奏**。
- **重抽预算铁律**：触发硬伤需重抽时也要卡上限——**非常重要的剧情图**（核心爽点/反转/觉醒/封面候选等关键叙事镜）**最多重抽 2 次**；**其余所有图最多重抽 1 次**。到上限仍不完美 → 从已抽版本里挑**定妆一致性最优**的那张落档（定妆漂移优先级高于构图/道具/动作的小偏差），别无止境刷图烧 credit。
- **生图调用优先级**：本机已装的官方 CLI → Bash 直调；没装的 → **先问用户有没有其他自动生图 AI**，没有再默认走即梦 web 手动指导；批量并发可 spawn sub-agent。**不装第三方逆向 CLI**（违 ToS + 封号风险）。
- **废料归档**：所有筛选拼图 / 废图 → `制漫剧/<剧名>/common/废料/出图/{common,第N集}/`，**绝不留在 Downloads 或散落作品根**。

## 可选增强：LoRA 角色一致性（opt-in · 引导式）

默认一致性方案 = **锚点句 + 定妆参考图 + 平台建角色**（见 `references/角色一致性checklist.md`），绝大多数角色已够。**LoRA 是其上的可选增强层，默认不启用。**

- **何时把它作为选项提出来**：某个**贯穿几十集的核心角色**（如女主）拼了锚点句、调高参考图强度后**脸/妆造仍反复漂移**，或用户主动问"要不要训练/LoRA/提高一致性"。提的时候说清三点：① 这是可选增强，不启用也能继续出图；② 只对核心长线角色划算，一次性角色不值；③ LoRA 是开源支线（Flux/ComfyUI），即梦/可灵不接受自训 LoRA，是**混合产线非替换**。
- **用户选择启用后**：严格按 `references/lora_consistency.md` **一步步问答引导**——先过 Stage 0 三个决策门（商用许可/本次范围/云算力），再逐阶段推进（建数据集→云训练→ComfyUI验证→接产线→固化），**一次只推进一个阶段，别一次性把全套丢给用户**。
- **用户不选**：继续默认参考图 + 锚点句出图，不要强推。

## 输入前置条件

- 作品根存在，`_进度.md` 该集 `分镜设计` 列 ✅（= 配音 + 阶段2分镜设计 已完成）
- 否则报错并建议用户先调 `/n2d-script <作品根> 第N集`

## 工作流

### 阶段 A — 出图 prompt 生成（5 步强制 SOP）

**① 扫描共享库**
- 读 `出图/common/prompt/00_索引.md`（若不存在则首次创建——格式见 `references/prompt_format.md §1`）
- 盘清楚：已有哪些角色（含形态变体）/场景/道具，及状态（✅/⏳/⬜）

**② 列出本集需求**
- 读 `脚本/第N集/分镜剧本.md` + `素材清单.md`
- 提取本集需要的所有角色/场景/道具/特殊视觉

**③ 差集 = 新增项**
- 本集需求 − 共享已有 = 必须新加入共享库的项
- 包括"首次出现的全新项" + "已有角色的新形态变体"

**④ 追加共享库**（仅新增项才做）
- 共享 `00_索引.md` 追加 ⬜ 行（含 ID / 首现集 / 复用范围）
- 对应 `角色|场景|道具定妆.md` 追加完整 prompt 块（格式见 `references/prompt_format.md §2`）

**⑤ 建本集 prompt 文件夹**
- `出图/第N集/prompt/00_总览.md`（本集图清单 + 引用共享 + 进度）
- `出图/第N集/prompt/01_分镜出图.md`（本集 N 张分镜，一镜一图，复杂镜拆 NA/NB）

**完成后**：
- `_进度.md` 该集 **`出图prompt` 列填 ✅**（共享层新增 + 本集总览 + 本集分镜 三处都写完算 ✅）
- `_进度.md` 该集 **`出图` 列填 已完成张数/总张数**（如 `2/16`；分子含共享复用，分母 = 共享需要 + 本集分镜）

### 阶段 B — 扫描本机生图 CLI

```bash
# 已知图 AI CLI 一次性探测（详细清单见 references/cli_registry.md）
for cli in dreamina gemini-cli openai imagen flux-cli; do
  command -v "$cli" >/dev/null 2>&1 && echo "found: $cli ($(command -v $cli))"
done
```

按 `references/cli_registry.md` 的优先级选最匹配目标视频 AI 的那个（同 AI 闭环最稳）。

### 阶段 C — 分支决策

**分支 1：找到匹配的 CLI**
- 优先级：**与目标视频 AI 同家 CLI** > 与目标视频 AI 兼容（带锚定句拼接）的图 CLI > 不推荐组合
- 选定后告知用户："找到 X，将用它出图。如不同意请打断。"
- 按 SOP 一镜一图调用（详见"调用规范"）
- **批量加速可选**：>10 张时，可 spawn 多个 sub-agent 并发调用 CLI（每个负责一段镜头），主线程收集结果
- 中间筛选废料 → `common/废料/出图/{common,第N集}/`，定稿 PNG → `出图/common/` 或 `出图/第N集/`

**分支 2：本机无合适 CLI**
- **必须先问一句**（不要直接跳进即梦 web 手动模式）：
  > "本机未检测到合适的图 AI CLI（已扫 dreamina/gemini-cli/...）。**默认我会一步步指导你在即梦 web 上生图**。但如果你本地或账号上有其他能自动接 prompt 跑图的 AI（如 SD WebUI / ComfyUI / Midjourney bot / 自建 API / 其它图生图服务），告诉我接入方式，我可以把 prompt 喂给它自动跑。否则就走即梦 web 手动模式。"
- 用户回答后再分流：
  - **有自动 AI** → 让用户提供调用方式（CLI 命令 / API endpoint / webhook），按 `references/cli_registry.md` 临时登记一项并走分支 1 流程
  - **没有 / 用户直接说"走即梦"** → 进入"手动指导模式"
- **手动指导模式**：
  - 一次一张（或一批），把 prompt + 即梦参数列出来
  - 让用户截图回传 → Claude 按**筛选宽容铁律**评判 → 通过则落档（用户从 Downloads 挪 PNG 进 `出图/common/` 或 `出图/第N集/`），只有触发硬伤才建议调整 prompt 或重抽
- 用户也可主动切换：换用 可灵 web / DALL-E web 等，本 skill 按 `references/platforms.md` 给对应平台的 prompt 适配

### 阶段 D — 进度回写 + 推进

每出一张定稿 PNG：
1. PNG 落档到正确位置（共享定妆 → `出图/common/`；本集分镜 → `出图/第N集/`）
2. 共享 `00_索引.md` 该项状态改 ✅，填 PNG 路径
3. 回写 `出图` 列：`python3 <novel2drama skill>/progress.py set <作品根> 第N集 出图 X/Y`（X=已出张数）

本集 `出图` 列 = 分母时：
```
第K集 出图完成（X/X）
- 共享层新增定妆：<列项目>
- 本集分镜：<张数>
下一步建议：
- 调 /n2d-video <作品根> 第K集  生成视频 prompt + MP4
- 或继续 /n2d-image <作品根> 第K+1集
```

## 调用规范（找到 CLI 时）

**通用流程**（每张图）：

1. 从对应 prompt 文件读出本张的正向 + 负向 prompt + 参考图（如有）
2. 走 CLI：
   ```bash
   <cli> <subcommand> --prompt "$(cat <prompt_file_or_inline>)" \
                     --negative "..." \
                     --ref-image <出图/common/定妆_xxx.png> \
                     --ref-strength 0.8 \
                     --aspect 9:16 \
                     --out <目标 PNG 路径>
   ```
   （各 CLI 具体子命令/参数见 `references/cli_registry.md` 单家档案）
3. 检查产出 → 通过则原位 PNG 已落档；废图 → `mv` 到 `common/废料/出图/{common,第N集}/`
4. **跨 AI 锚定句**：组装 prompt 时若 `global_style.md` 标的 图AI ≠ 视频AI，自动在 prompt 末尾追加视频AI 的锚定句（详见 `references/platforms.md`）

**安装新 CLI 时**（用户同意才做）：
- 走 `references/cli_registry.md §安装审查` 的 5 步流程（域名核对 / WebFetch 读脚本 / 不 sudo / 不写敏感位置 / 无可疑行为）
- 绝不 `curl xxx | bash` 不审

## 详细参考

- **角色一致性 checklist（跨集锁脸全链对照）**：`references/角色一致性checklist.md`
- **LoRA 增强一致性（可选 · 引导式五阶段）**：`references/lora_consistency.md`
- **prompt 两层架构 + 单张 prompt 块标准格式**：`references/prompt_format.md`
- **平台档案 + 锚定句速查**：`references/platforms.md`
- **已知 CLI 清单 + 安装/调用规范**：`references/cli_registry.md`
- **翻车 + 修正案例**（实战沉淀）：`novel2drama/Q&A.md` 的 Q3-Q12（定妆/场景细节）、Q14-Q18（CLI 安全 + 跨 AI）、Q19-Q20（共享层 + 跨集复用 SOP）

## 常见错误

| 错误 | 纠正 |
|---|---|
| 跳过 SOP 第 ① 步（不扫共享） | 必然重复劳动 + 跨集脸漂移 |
| 把定妆图当本集分镜放到 `出图/第N集/` | 共享资产去 `出图/common/` |
| 角色切换时不清空参考图 | 即梦参考图框是粘性的，新角色前必须清空（见 Q&A Q8） |
| 场景图带角色参考图 | 场景定妆**必须**清空人物参考图（见 Q&A Q12） |
| 图 AI ≠ 视频 AI 时漏拼锚定句 | image prompt 末尾必须拼视频 AI 锚定句 |
| 装第三方逆向 CLI | 违 ToS、封号风险，仅装官方 |
| 废图留在 Downloads | 全部归档 `common/废料/出图/{common,第N集}/`，Downloads 清空 |
| 全部串行生 100 张 | 大量分镜可 spawn 子 agent 并发调 CLI |
| 候选图轻微偏差就喊重抽 | 违反**筛选宽容铁律**——只对核心错位/定妆漂移/硬性禁忌违反 才重抽，小动小偏直接放行 |
| 一张图反复重抽烧 credit | 违反**重抽预算铁律**——重要剧情图≤2次、其余≤1次，到顶挑定妆最一致的版本落档 |
| 无 CLI 就直接进即梦 web 手动模式 | 必须先问用户有无自建 / 第三方自动生图 AI 可接 prompt，没有再走默认 |
