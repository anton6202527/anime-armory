# anime-arsenal desktop（MVP）

VS Code 式的本地客户端 —— 给「重 AI」的创作工厂一个**能看文件 + 能随手敲命令 + 后续看画布**的工作台。

> **这是独立 app，不是 skill。** `anime-arsenal` 本身是 skills 库（不是应用），所以这个客户端放在单独的 `desktop/` 目录，以"消费这些 skills"的身份存在，不进 `skills/` 树。日后可整体拆成独立仓库。

## MVP 已有
- **打开文件夹** → 侧栏**文件树**（懒展开，略过隐藏目录、保留 `.claude`）
- **打开/关闭文件** → Monaco 编辑器 + 标签页（`_进度.md`/`storyboard.json`/`SKILL.md` 随手看改），`⌘S` 保存、未保存有 ● 标记
- **集成终端**（xterm.js + node-pty 真 shell）→ 继承你的 shell 环境，能 `conda activate`、跑 `python3 skills/.../*.py`、跑 Claude Code
- **终端面板可上下拖拽**改高度（VS Code 同款手感）
- **生产看板面板（命令行+画布同窗联动）** 🆕：活动栏 📊 → 编辑器右侧弹出 n2d 生产看板（内嵌 `board.py` 出的画布，可缩放/平移、点 Clip 跳深画布）。
  - 顶部选作品（自动扫打开目录里带 `_进度.md` 的剧）→「↻ 刷新」重生成；
  - 勾「自动刷新」后，**终端里跑 `score.py` / `n2d-*` 写了产物，看板自动重载**（文件监听，避开看板自身输出防死循环）；
  - 与编辑器之间有竖向 gutter 可拖拽分宽。
- **命令面板「一键跑下一步 skill」** 🆕（活动栏 ⌘ 或 `⌘⇧P`）：对当前作品列出可执行命令——
  - 🟢 **绿色=直接在集成终端跑**的确定性安全脚本（刷新看板 `board.py`、机器评分 `score.py --run-checks`、`gate.py` 闸门检查）；
  - 🔵 **蓝色=填入终端待你确认**的「下一步」：从 `_进度.md` 算出的前沿(`/n2d-* {root} {ep}`，多为 Claude Code 步或付费出图/出视频)——**只填不自动回车**，你在 Claude 会话里确认执行。
  - 输入框模糊过滤；↑↓ 选择、回车执行、Esc 关闭。诚实区分「脚本直接跑」与「LLM/付费步交给你/Claude」两种执行模型。
  - **执行落日志**：每次跑/填的命令追加进 `<userData>/command_log.jsonl`（`{ts,work,tier,cmd}`），面板里「📜 命令日志」项可在编辑器打开查看。
- **看板深链在 app 内打开** 🆕：看板里点 Clip → **不弹新窗口**，在 app 内开一个「第N集 深画布」标签（iframe 加载该集 `review_ui`），并自动**居中高亮**那个 Clip。两视图（全局看板 ↔ 单集深审）在同一窗口里打通。
- **启动即打开**：`npm start -- <文件夹>`（或 `INIT_FOLDER=<dir> npm start`）直接在该目录开 app（VS Code 的 `code <dir>` 体验）。
- **全局搜索 + git 面板** 🆕（活动栏 🔍 / ⑂，VS Code 式侧栏视图切换）：
  - 🔍 全局搜索：优先 ripgrep（快·尊重 .gitignore·跳过媒体），缺则 node 兜底；结果 `文件:行` 点击→打开文件并定位到行。`⌘⇧F` 切到搜索。
  - ⑂ git：显示分支 + 改动文件列表（M/A/D/?? 着色），点文件→打开；填提交信息「提交(终端)」= 在集成终端跑 `git add -A && git commit`（你看得见、可中断）。
- **状态栏环境探测** 🆕：右下角显示「环境 py✓ ffmpeg✓ conda N/4」——通过登录 shell 探测（与集成终端同 PATH），检查基础工具 + CLAUDE.md 点名的重 AI conda 环境（cosyvoice/acestep/fish-speech/facefusion）。缺核心工具=红，缺重 AI 环境=黄(提示"本机跑不起来,先用 say 应急")，全绿=无色。点开看每项 ✓/✗ + 路径/版本，附「重新探测 / 终端详细探测」。**不硬编码任何私有后端 IP**。
- 布局：活动栏 / 文件树侧栏 / 标签+编辑器(+看板) / 底部可拉伸终端 / 命令面板 / 状态栏

## 跑起来（macOS）
```bash
cd desktop
npm install
npm run rebuild     # 把原生模块 node-pty 重编到 Electron（需 Xcode Command Line Tools）
npm start
```
- `npm run rebuild` 失败时：`xcode-select --install` 装 CLT 后重试。
- 打开后点左上「打开」选一个创作根（如整个 `anime-arsenal`，或 `制漫剧/某剧`），终端 cwd 会切到它。

## 打包（electron-builder）
```bash
npm run pack    # 不签名·不出 dmg，产 dist/mac-arm64/anime-arsenal.app（验证构建，最快）
npm run dist    # 出 dmg（需 Apple Developer ID 签名/公证，否则只是未签名包）
```
- 已验证 `pack` 产出可用 `.app`（含 node-pty 原生模块正确 unpack 出 asar），**且打包版能用 n2d 看板/命令面板**（见下「skills 路径解析」，已实测打包版 `board:generate` 出图成功）。
- **node-pty `spawn-helper` 执行位**：node-pty 1.1.x 的 prebuild 自带一个 `spawn-helper` 可执行文件，npm 安装 / electron-rebuild 出来常丢执行位(0644)，导致终端一启动就 `posix_spawnp failed`。已修：`npm run rebuild` 末尾会 `chmod +x` 回来（dev 版），打包时 `build/afterPack.js` 钩子在产物里再补一次（打包版），两条路径都自愈，无需手动处理。

## skills 路径解析（让打包版也能用看板）
看板/命令面板要调 `skills/n2d-review-ui/scripts/board.py` 等脚本。skills 目录按以下优先级解析（main `resolveSkillsDir`），**不写死相对路径**：
1. 环境变量 `ARSENAL_SKILLS_DIR`；
2. 用户持久化设置 `<userData>/settings.json` 的 `skillsDir`（命令面板「⚙️ 设置 skills 目录…」写入）；
3. **从作品根/打开的文件夹向上找** `<dir>/skills/n2d-review-ui/scripts/board.py`——因为 n2d 作品(`制漫剧/<剧>`)本就在仓库内，这条让**打包版在任意位置都能从作品路径定位到 skills**（已实测）；
4. dev 相对路径 `<app>/../../skills`。

都没命中（如打包版开在一个仓库外的孤立文件夹）→ 命令面板出「⚙️ 设置 skills 目录…」兜底项，选一次即持久化。**编辑器/终端/搜索/git 与 skills 无关，任何情况都能用。**

## 技术选型（为什么）
- **Electron + Monaco + xterm.js + node-pty**：VS Code 同款编辑器内核 + 最成熟的真终端方案；**零打包**（Monaco 走 AMD loader、xterm 走 UMD），改完直接 `npm start`。
- 安全：`contextIsolation` 开、`nodeIntegration` 关，renderer 只能通过 `preload` 的白名单 API 碰文件/终端。MVP 期 `webSecurity:false`（本地工具加载本地文件，省去 Monaco 的 `file://` worker 坑）——**产品化前要收紧**。
- 单一真值源：客户端只读/写你磁盘上的真实文件，不建第二份状态。

## 路线图（下一步，未做）
1. ~~嵌入生产看板 + 终端联动~~ ✅ 已做（见上「生产看板面板」）。
2. ~~命令面板 / 一键「跑下一步 skill」~~ ✅ 已做（见上「命令面板」）。
3. ~~状态栏显示 conda/后端环境可用性~~ ✅ 已做（见上「状态栏环境探测」）。可选延伸：可配置的后端 URL 可达性探测（从 `_设置.md`/env 读，不硬编码）。
4. ~~命令面板执行落日志 + 看板深链 app 内标签~~ ✅ 已做。可选延伸：命令面板补更多 stage（配音/合成）的安全命令。
5. ~~全局搜索 + git 面板~~ ✅ 已做。剩 Monaco 完整 IntelliSense（接打包后开 worker）。
6. ~~打包分发（electron-builder）+ 打包版 skills 路径解析~~ ✅ 已做（`npm run pack` 产 .app；打包版从作品路径解析 skills，实测可用）。剩：dmg 签名/公证、app 图标。
