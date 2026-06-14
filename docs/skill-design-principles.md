# Skill 设计原则（设计宪法）

> **这是本仓库唯一的「怎么*建造* skill」权威法条**（authoring-time constitution）。
> 跨工具、随仓库交付、对所有五条线（novel / n2d / song / mv / ad）生效。
>
> **三层分工，别放错层：**
> | 层 | 管什么 | 住在哪 |
> |---|---|---|
> | **设计宪法**（本文件）| 怎么*建造*一个 skill：独立性、选择点、合规、交付约束 | **本文件，单一副本** |
> | **运行期契约** | skill *执行*时的 manifest 字段、阶段表、候选清单 | 各线 `*-craft/` / 本线 `_lib/` / 本线 `references/选择点与偏好.md` |
> | **机器/会话事实** | 这台机器、此刻为真（env 缺失、后端宕机）| 各 AI 的私有 memory / 本机配置（不随交付）|
>
> 入口文档（`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`）只放 ~5 行摘要 + 指回本文件，**不复述**。
> 各线 `*-craft/SKILL.md` 的 `## 设计原则` 只留**本线特有**原则 + 一行指针，通用条文不再各抄一份。
> 标 ✅ 的条文已有机器检查覆盖（`tools/validate_skills.py` 或对应专项审计）；标 ◑ 的部分机检；其余靠 review。

---

## A. 仓库形态与独立性

- **A1 五线自包含、可单独分发** ✅ — 每条线本线脚本只 import 本线 `_lib`/craft 工具，**不依赖 `skills/common/`**（已删），**不 import 别线实现**。跨线只允许**可选文件/数据交接**（novel 导出 n2d 源书、song 交成品歌给 mv、n2d-feedback 写题材战绩 JSONL 供 novel-score）；交接缺失必须**优雅降级**，不能让本线主流程跑不起来。机检：`tools/independence-audit/scripts/check_independence.py`。
- **A2 仓库级 meta 工具放 `tools/`，不放 `skills/`** — 不是某条创作线能力的单副本维护工具（independence-audit、shared-cleanup、validate_skills、打包/发布脚本等）留 `tools/` 或独立单副本，不混进 `skills/` 的创作线命名空间。**例外**：属于某条线用户工作流的一线能力（如 `n2d-progress`、`novel-progress`）仍是该线 skill，可以留在 `skills/`。
- **A3 `skills/` 扁平、按名字前缀分组** — `n2d-*` / `novel-*` 等。SKILL.md frontmatter `description` + 正文 `Triggers`/`Use when` **就是路由依据**，匹配用户意图，不另建路由表逻辑。

## B. Skill 编写法

- **B1 脚本通用、无专有 API** — 纯 Python / bash，只调通用工具（`ffmpeg`/`librosa`/`whisper`/`yt-dlp`/生图生视频 CLI）；不绑定任何一家 AI 的专有 SDK；引用路径用中立的 `skills/...`。
- **B2 推荐 skill 一律写裸名** ✅ — 输出「下一步」或推荐调用时写 `n2d-image`，**不写** `/n2d-image`（有些 agent 把 `/...` 当内置斜杠命令报错）。
- **B3 prompt / 产物分离** — prompt 包与生成产物分目录、分文件，不混写。
- **B4 脚本不伪装云端自动化** — 没有凭证/后端 SDK 时，只产稳定 prompt/job 包 + 合规留痕；真正调用 Suno/即梦/Kling 等交对应后端工具，外部生成后再登记。
- **B5 阶段完成即回写 `_进度.md`** — 用确定性脚本（`progress_set.py` / `update_progress_stage()`）回写，不只在文档里说「更新进度」。正式产物阶段默认先过 `gate.py`。

## C. 选择点与适配层

- **C1 通用 skill、私有选择** — skill **不得硬编码**唯一平台/后端/分辨率/音色。凡「让用户选」的点：读 `<作品根>/_设置.md` → 否则读用户私有全局默认（如 `创作偏好-默认.md`、`.agents/创作偏好-默认.md`、`.codex/创作偏好-默认.md`，`.claude/` 仅作 legacy 兼容）并预填 + 告知一次 → 否则问一次，然后持久化沉默沿用。**例外**：合规 / 不可逆 / 花钱的点每次都复确认。
- **C2 选择菜单 = 带日期候选快照，不是真理** ◑ — 模型/平台/法规/价格/规格等会变的信息：执行前按需用专业知识/项目 references/官方文档/实时搜索核验刷新；用户永远可手输 `自定义`/`manual`（逃生口常驻）；每份易变候选清单带 `采集日期：YYYY-MM-DD` 戳。skill **不直接依赖菜单文案**，而经本线适配层（本线 `_lib` / craft contract / backend registry / model router 等）把选择归一到能力、参数、CLI/API、降级方案和合规闸门；**适配不了就停下报缺口，不偷偷换路**。各线策略差异是故意的（如 ad 禁即梦 ≠ n2d 放行即梦官方），**分别刷新、绝不合并候选清单**。新易变清单注册到对应线 `_lib/freshness.py:CANDIDATE_SOURCES`（若该线有候选源；目前 n2d/ad 有），用同目录 `refresh.py` 刷新。

## D. 合规硬闸门（非协商）

- **D1 授权与来源** — 声音克隆只在本人 / 已授权嗓音上做；克隆真人嗓需授权（2026 opt-in），未授权拒做。源小说/词曲默认公版 / 自有 / 已授权。合规 / 不可逆 / 高成本的选择点即使已记录也每次复确认（见 C1 例外）。
- **D2 各线合规策略不强行对齐** — 例如 AI 标识/水印义务在 n2d 线于 2026-06 退出管道（移到管道外处理），其他线按各自法规要求；改一条线的合规闸门不自动套到别线。

## E. 交付约束

- **E1 交付端 VCS-free** ✅ — 交付到用户端**不能假设有 git 仓库或 git 命令**。任何 skill 不得依赖 / 探测 / 描述 git 做本仓状态、基线或变更检测（无 `git status/diff/log/rev-parse` 等）；需要变更检测时改用**内容快照**（SHA over 文件内容），不依赖 git 基线。安装类 references 可以给第三方依赖的 `git clone` 作为获取方式，但不得把本仓 workflow 的正确性建立在 git 上，并应尽量提供 release 包 / 手动下载等替代路径。
  > **历史违例已销账（2026-06）**：`skills/n2d-update` 曾用 git 基线比对，现已重构为纯内容 SHA256 快照（`build_baseline_snapshot`），并主动拒绝 legacy git 基线。`validate_skills.py` 的 `KNOWN_GIT_EXCEPTIONS` 已清空，全仓 `git` 自省调用一律 fail。
- **E2 私有配置与重资产在 git 外** — 各 AI 私有配置（`.claude/`、`.cursor/`）、大模型权重、conda 环境（`~/CosyVoice`、`~/ACE-Step` 等）不进共享 skill，按各 `references/` 安装说明本地准备。

## F. 维护与同步

- **F1 改了 skill 集合（增/删/改职责）→ 必须同步 `skills/README.md` 索引** ✅。
- **F2 改了跨线引用 / `_lib` / 调度入口 → 跑 independence audit** — `python3 tools/independence-audit/scripts/check_independence.py`，确保没误引公共层或别线代码。
- **F3 改了路由表 / 入口文档 → 三份入口保持同步** ✅ — `AGENTS.md`（工具中立）、`GEMINI.md`（per-tool 镜像）、`CLAUDE.md`（Claude Code）的关键路由入口、机检命令与约定摘要必须一致；`CLAUDE.md` 可指向 `AGENTS.md` 作为路由真值源，但不得保留过期命令或旧路径。

---

## 不属于本宪法的（别往这塞）

- **本线特有工艺原则**留在各线 `*-craft/SKILL.md` 的 `## 设计原则`：n2d 配音先行 + 两层出图、ad 不拆集 + cutdown 轴、novel 不抢写作权、song/mv 多版是默认工程事实。
- **n2d 契约层治理**（invariant vs contested、版本迁移）是运行期契约层的演进，见 `docs/n2d-原则变更提案-契约治理与一致性占位.md`，不在本跨线宪法内。
- **机器/会话事实**（哪台机器装了什么、哪个后端宕了）进 memory，不进本文件。
