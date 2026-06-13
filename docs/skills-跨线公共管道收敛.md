> ⚠️ **已作废（2026-06-13）**：本文档记录的是把跨线重复管道**收敛进 `skills/common/`** 的方案，
> 已被「五条线全独立化」重构**整体推翻**——`skills/common/` 已删除，所有管道模块改为 **vendored 进各线
> `skills/<line>/_lib/`**，五条线零公共层、可单独打包分发。当前架构见 `docs/重构-各线全独立化计划.md`
> 与 `CLAUDE.md` 架构段。本文仅作历史留档，**不要据此恢复 `common/`**。

---

# Skills 跨线公共库收敛 + common 正名（四项）〔历史·已作废〕

> 状态：**已实施** · 日期：2026-06-12 · 适用：novel / song / mv / ad 的 `*-craft` + `skills/common/` + `skills/n2d/_lib/`
> 性质：一次架构审查的落地记录，分两类。**② 收敛**：把跨线**重复的管道代码**提到 `skills/common/` 单一真值源（disclosure / progress_md / io_utils 三项 + 前置的 settings 修复）。**③ 正名**：把 n2d 私有契约层从 `common/` 迁出，让 `common/` 名实相符。两类都**不动任何内容逻辑**、行为零变化。供团队 review。

---

## 0. 一句话

五条生产线"自包含、不互相 import"这条铁律约束的是**内容逻辑**（阶段表、分镜算法、披露字段集、gate 规则），不约束**管道**（文件 IO、披露写盘、进度表解析）。审查发现 `common/` 当时是"n2d 私有库 + 跨线公共"混装、且跨线管道被各线各抄一份并在漂移。两步治理：**②** 把真·跨线管道收敛进 `common/`；**③** 把 n2d 私有契约迁出 `common/`。

**判据（写进了 `skills/README.md`）**：一段代码删掉后各线表现一致、且不含本线业务语义 → 进 `common/`；否则留各线 `*-craft`（内容契约）或 `n2d/_lib/`（n2d 私有契约）。

## 1. 背景：漂移已发生，不是假想

审查时实测到的真实分叉（不是洁癖）：

- **设置解析**：`shared-settings` 按 `common/settings.py` 格式写 `_设置.md`，但 song/mv 用自己手写的 `parse_settings` 读——对 `**加粗**` key、`## 记录` 区处理不一致 → 写得进读不出的**静默 bug**（前置修复，已先行收敛到 `common/settings.py`）。
- **AI 披露**：`ai_usage.py` 四份近拷贝，ad vs mv 的非注释行已差 43 行。
- **进度表解析**：`parse_stage_rows` 三份，列序还不一样（ad 2 列 `阶段|状态`，song/mv 3 列 `阶段|skill|状态`）。
- **IO 小工具**：`load_json` 在 27 个文件各定义一份，`write_json` 12 份，且错误语义分叉（strict 抛错 / resilient 返默认 / 登记 QA BLOCK）。
- **common 名不副实**：`common/` 一半是 `n2d_*` 私有契约（n2d_contract 1682 行等），一半是真公共；讽刺的是 `disclosure`/`progress_md` 这类是**除 n2d 外全线在用**。

## 2. ② 收敛：3 个新公共模块（+ 前置 settings）

| 模块 | 职责（纯管道） | 消费方 | 各线保留（内容） |
|---|---|---|---|
| `common/settings.py`（前置） | `_设置.md` 读写/选择点 | n2d/novel/song/mv/ad + `shared-settings` | 选择点取值 |
| `common/disclosure.py` | AI 使用+授权披露的 IO、7 个通用 payload 字段、markdown 骨架 | novel/song/mv/ad 的 `*-craft/scripts/ai_usage.py` | 本线专属字段、markdown 标签、说明文案、`choices` |
| `common/progress_md.py` | `_进度.md` 阶段表解析（段名匹配 + 列提取 + 表头/分隔跳过），列序/段名按线传参 | song/mv/ad 的 `*-craft/scripts/progress.py` | `state_of`/`is_optional`/frontier 循环/打印/hint |
| `common/io_utils.py` | `load_json`/`write_json`/`read_text`/`write_text`/`load_meta`；`load_json(..., resilient=)` 兼容 strict/容错两种历史语义 | mv_utils / compose_song / disclosure（已迁），余 ~24 处 touch-on-edit | —（把坏 JSON 变成领域发现的加载器不算通用 IO，留本地） |

每个新模块均带 pytest（`common/test_disclosure.py` / `test_progress_md.py` / `test_io_utils.py`）。

## 3. ③ 正名：n2d 私有契约迁出 common

7 个重 `n2d_*` 模块（**2581 行**：n2d_contract / n2d_route / n2d_thresholds / n2d_telemetry / n2d_platform_profiles / n2d_visual_styles / n2d_contract_diff）`git mv` 到 `skills/n2d/_lib/`；`common/` 留 **6–12 行 compat shim** + 新增 `common/_relocated.py` 加载器。

- **0 个 importer 改动**：约 50 个 `import n2d_contract`（common 在 sys.path 上）的 n2d 脚本、`python3 skills/common/n2d_contract.py …` CLI **路径全不变**。
- **机制 = importlib-by-path**：`_relocated` 按**显式文件路径**加载 `_lib/` 真身，**不往 sys.path 加任何目录** → `skills/n2d/` 不会遮蔽裸 `import progress`/`import manifest`（特意没选"`_lib` 上 path"的包方案）。
- **shim 自举**：每个 shim 先把自身目录（common）插到 path 再 `import _relocated`，所以即便被 `spec_from_file_location` 之类**文件路径加载**（如 `n2d-review/self_audit.py`）也成立。
- **CLI 委托**：`n2d_contract` 的 `migrate-version/check-version` 经 shim 的 `__main__` 分支 `runpy` 委托给真身，invocation 路径保持有效。
- **要改契约去 `skills/n2d/_lib/`**，不是 `common/`。`n2d_settings.py`/`n2d_text_utils.py` 仍是转发 `settings`/`text_utils`（common 真模块）的 shim，留 common。

迁移中抓到并修掉 3 类真问题：① 3 个 `__file__`-相对路径（移深一层后指错 `n2d-dashboard`/common，改上溯层数）；② **self_audit 回归**——它用不带 common-on-path 的文件路径加载 shim，导致 `from _relocated import` 失败、报伪 block（测试套件没抓到，因为 self_audit 把失败 import **降级成 finding** 而非崩溃；靠**直接运行该工具**才发现），用 shim 自举修掉；③ `n2d_contract_diff` 原本插自身目录找 `n2d_contract`，改成插 common 走 shim 避免双载。

## 4. 行为保持的证据

两类都要求"零行为变化"，逐项验证：

- **disclosure**：4 条线用相同 `_meta.json`+参数跑新版 vs 改前 HEAD —— **markdown 逐字节一致**，JSON 键值一致（仅键顺序变化，机读无关）。
- **progress_md**：3 条线 `progress.py` 新版 vs 会话起点基线 `2db8194`，跑**真实 demo `_进度.md`**（制MV/写歌·仗剑下山）+ ad 合成文件 —— **stdout 逐字节一致**。
- **io_utils**：委托方各自保留 `resilient` 旗标匹配原错误语义（mv_utils=resilient、compose_song=strict、disclosure.load_meta=strict）。
- **③ 正名**：全量 n2d 测试 **~700 项**（common 115 / n2d-review 242 / n2d-batch 42 / n2d-image 39 / model-router 35 / identity 28 …）+ 非 n2d 线（settings 经 shim 取 n2d_platform_profiles）+ CLI 委托 + 跨 cwd import smoke + `validate_skills`(70 skills) + self_audit 直跑 **全绿**；迁后 `_lib/` 的 `__file__`-相对落点逐一 smoke 校验。

## 5. 刻意不做（及理由）

- **`gate.py` 不并**：mv/ad gate 唯一同构的是 ~15 行 argparse+退出码 CLI 壳；`check()` 里 100% 是线特定规则（"缺 beatgrid"/"brief 缺必填项"），搬不动也不该搬。等出现第 3 条需要 gate 的线再抽。
- **`song_check.load_json` 不迁**：撞坏 JSON 时它 `add(BLOCK, …)` 登记阻断级 QA 发现——是质检语义不是通用 IO。
- **io_utils 不做大爆炸**：只迁本次工作集内的文件，余 ~24 处本地 `load_json` 留待 touch-on-edit。
- **n2d 的 `progress.py`(逐集矩阵)/`gate.py`(2886 行) 不并**：另一量级的有状态机器，不属"管道"。

## 6. 维护须知

- 改 `settings.py`/`disclosure.py`/`progress_md.py`/`io_utils.py` 这类跨线模块 → 回归要跑**所有消费线**的 craft+相关脚本测试，不能只跑一条。消费方清单见各模块 docstring 与 `skills/README.md`「§ common/ 跨线公共库」注。
- 改 n2d 契约/路由/阈值等 → 改 `skills/n2d/_lib/` 的真身，不是 `common/` 的 shim。文档里凡说"真值源在 `common/n2d_*.py`"按此重定向（`import`/CLI 路径仍走 common shim 不变）。
- 新增跨线管道时按 §0 判据登记进 README 注。
