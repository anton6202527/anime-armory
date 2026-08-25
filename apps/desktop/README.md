# LabuTV Desktop (Electron)

LabuTV 桌面创作 IDE 的 **Electron 版**(自原 Tauri 版重构而来,
Tauri 版已于 2026-07 退役删除)。长期重度使用定位:类 VSCode 的多进程结构、类型化
IPC 契约、worker 化媒体解码、虚拟化文件树、按 chunk 拆分的懒加载面板。

## 运行

```bash
npm install          # postinstall 会自动 electron-rebuild node-pty
npm run dev          # electron-vite dev(HMR)
npm run build        # typecheck + 三进程打包到 out/
npx electron .       # 运行打包产物
npm run dist         # electron-builder 产出安装包(release/)
```

技能仓库解析顺序:显式 `VITE_ANIME_ARMORY_REPO` → `ANIME_ARMORY_REPO` 环境变量 →
从 cwd 向上查找含 `skills/README.md` 的目录 → 打包内置 `resources/`。
新作品工作区默认为 `~/LabuTV`（若机器上已有旧版 `~/AnimeArmory` 且尚无 `~/LabuTV`，会继续沿用旧目录，避免迁移时丢失作品）。可经菜单“切换工作区…”更换，与技能仓库互斥隔离。
自动化调试可用 `ANIME_ARMORY_WORKSPACE` 指向临时工作区。

### Web 本地模型桥接

Electron 启动后会在 `127.0.0.1:43117` 提供仅回环可见的 Web 桥接。浏览器第一次调用本机共享模型时，桌面端会显示原生确认弹窗；允许后签发 12 小时内存会话令牌。该配对会话只开放受控的模型发现与文本/图片生成接口，不开放本地 Agent、Shell、文件上传或调用方指定的文件系统路径。

本地开发默认只允许 Web 端的 `localhost:4174` 与 `127.0.0.1:4174`。正式 Web 域名需通过逗号分隔的 `ANIME_ARMORY_WEB_ORIGINS` 显式加入允许列表。Web 端 Agent 任务继续走云端 API 或演示模式，不复用这个持有模型密钥的本地桥接。

画布内的文本/图片即时生成也走同一个已配对桥接，浏览器不会直接访问模型服务。桌面主进程通过 OpenAI-compatible `cli-proxy-api` 调用 `/v1/models`、`/v1/responses` 与 `/v1/images/generations`，仅在上游明确不支持 Responses 时回退 `/v1/chat/completions`，并只向 Web 暴露发现到的 GPT / Gemini 文本与图片模型。运行桌面端前配置：

完整 Skill 任务使用独立的本地 Agent 授权。网页第一次提交时，桌面端会明确提示当前 Origin、作品目录读写范围和将调用的本机 Agent；同意后才开放素材上传、任务提交、状态查询及本次任务产物下载，授权与模型调用配对 token 相互隔离。网页不能提供 Shell 命令、工作目录或任意文件路径。任务完成后，桥接只扫描当前作品目录内本次新增/更新的文字、图片、音频和视频产物，并把受限产物清单返回画布。

仅自动化测试可在启动桌面端前设置 `ANIME_ARMORY_ALLOW_LOCAL_AGENT=1` 跳过原生授权弹窗；普通启动不得设置此变量。

```bash
export CLI_PROXY_API_URL=http://127.0.0.1:8317
export CLI_PROXY_API_KEY=your_local_proxy_key
npm run dev
```

也兼容 `CUSTOM_OPENAI_BASE_URL` / `CUSTOM_OPENAI_API_KEY`；`CLI_PROXY_*` 同时存在时优先。URL 可省略，默认值如上。仅在 macOS 非打包开发环境且未设置任一 API Key 时，桌面端会只读解析 `/opt/homebrew/etc/cliproxyapi.conf` 中 `api-keys` 的第一项；正式包不会读取该开发配置。密钥只存在桌面主进程内存中，不能放进 `VITE_*` 变量。

### 画布生产工作台

Electron 画布定位为可从脚本、素材和机器结果继续二次创作、选择性重生成、质检、返修并维护最终产物的生产工作台，不是中间产物查看器。它与仓库四个 `app-*` 独立 skill 遵守相同治理语义，但当前没有持久化 `app-script-workbench/v3`，也不应把 Web 合同字段写成 Electron 已实现字段。

Electron 当前权威实现是 `anime_armory_canvas_production_state` v2、`content_hash` 与 `canvas.final_product/v1`。每集 canvas workflow 实例只保留一个前沿和一个最终产物判词，当前素材/母版用内容哈希绑定；普通可逆编辑和机检可以连续推进，权利合规、不可逆发布/覆盖和最终验收仍是硬边界。当前最终回执的 reviewer 值是本地 `desktop_user` 占位身份，只能说明本机交互动作，不能认证具名真人；接入账户或可验证身份回执前，不得把它描述为强具名验收。

画布连线只表达可见节点之间的真实依赖：源与目标都必须是当前图中的可渲染节点。共享素材若只有生产元数据、没有对应的可见图片/文字源节点，不创建透明锚点或连线；帧到视频等两端都可见的直接依赖继续显示。这样边不会参与错误的 `fitView` 范围，也不会形成跨整张画布的无源线束。

### 后台作品任务

从作品工作台切到首页、系列列表或另一部作品时，当前工作台不会立即卸载，其 PTY / Agent 制作任务会继续在后台运行。应用在同一 renderer 会话中最多挂载 3 个作品工作台（当前作品计入上限），访问作品会把它移动到 MRU；打开第 4 个不同作品时，按 LRU 卸载最久未访问的工作台并结束其 PTY，同时在界面提示被淘汰的作品。切换整个作品工作区、删除作品、手动关闭终端会话或退出应用仍会结束对应任务。

从首页提交的 Prompt 会随新作品形成一个稳定的启动请求，并按当前首选 Agent 适配为对应 CLI 的首轮启动参数；中文、多行内容及附件路径作为一个安全转义后的参数提交。只有目标 CLI 通过启动稳定窗口，或单次模式以成功状态退出后，请求才会被消费；切换、参数解析或启动失败时保持待发送并做有限重试，避免固定延时导致漏发或作品改名后重复执行。

### 匿名 Demo 下载与本地作品

公开桌面端没有账号、登录或上传能力。官方 Demo 目录和 ZIP 从 Cloudflare
R2 匿名读取，下载完成后强制核对字节数与 SHA-256，再安全解压到作品工作区。
用户新建或修改的作品始终只保存在本地，不会自动或手动上传。

作品系列列表最多展示一个官方 Demo；n2d / 制漫剧系列固定优先展示《那妖魔是姜大人》。同系列的其他本地作品仍正常显示为用户作品，但不得再标为第二个 Demo。

维护者通过仓库根目录的 `npm run demos:publish` 独立发布 Demo；R2 凭证和
Cloudflare 登录态不会进入 Electron 包。完整边界见 `../../docs/cloud-architecture.md`。

## 架构

```
src/
├── shared/            ← 单一事实源:领域类型 + IPC 契约
│   ├── types.ts       所有线上(wire)类型,main/preload/renderer 三方共享
│   └── ipc.ts         IpcCommands 映射表:通道名→(参数)→返回值,编译期校验
├── main/              ← 主进程(对应 Tauri 的 6477 行 commands.rs,按域拆分)
│   ├── index.ts       窗口/生命周期/冒烟钩子(SMOKE_SHOT/SMOKE_DRIVE)
│   ├── menu.ts        原生菜单 + 语言/终端可见状态(AppUiState)
│   ├── ipc.ts         类型化 IPC 路由:一张 HandlerMap,通道名拼错=编译错误
│   ├── util/          paths(反穿越)/ text(BOM+GB18030 解码)/ hash(FNV-1a)/ docx
│   └── services/
│       ├── workspace  六条创作线扫描、作品增删、目录选择器
│       ├── skills     技能清单/文件树/文件读取(SKILL.md frontmatter 解析)
│       ├── workfs     作品文件树(分页)、读写(mtime 乐观锁)、搜索、导入、快照指纹
│       ├── baseline   "类 git"变更追踪:基线快照存 userData/baselines/,diff/归档/还原
│       ├── canvas     分镜画布聚合(review_ui→storyboard→panel_script 三级回退)
│       ├── quality    质量洞察聚合(novel 线 + 通用线 12 类 QA 报告)
│       ├── pty        node-pty 登录 shell,base64 流式 pty-data 事件
│       ├── watch      chokidar,限定生产子树,300ms 防抖 fs-changed
│       ├── media      localhost HTTP Range 媒体服务器(视频拖动必需)
│       ├── agents     登录 shell 探测 claude/codex/opencode/gemini/kimi
│       ├── localBridge 受控的 Web 配对与画布模型路由（不开放 Agent/Shell/文件）
│       ├── cliProxy   cli-proxy-api 模型发现、文本/图片生成与安全输出归一化
│       ├── pipeline   skills/n2d/run.py next --json 桥(30s 超时)
│       └── demos      演示包下载/sha256 校验/解压安装
├── preload/           contextBridge 暴露 window.armory(invoke/on/platform/getPathForFile)
└── renderer/          React UI(自 Tauri 版移植,平台层重写)
    └── src/platform/bridge.ts   唯一允许触碰 window.armory 的模块
```

### 与 Tauri 版的关键差异

- **类型化 IPC**:`shared/ipc.ts` 一张 `IpcCommands` 接口同时约束 main 的 HandlerMap 和
  renderer 的 `bridge.invoke`,取代字符串式 `invoke("cmd")`。新增命令只改一处。
- **`renderer/src/api.ts` 导出面与 Tauri 版完全一致**,组件层零改动移植;仅传输层替换。
- 对话框(目录/文件选择)走主进程 `dialog`(`workspace.pickDirectory` / `work.pickImportFiles`)。
- OS 文件拖入:HTML5 DnD + preload `webUtils.getPathForFile`(Electron 已移除 `File.path`)。
- 窗口拖拽:`.topbar { -webkit-app-region: drag }`(替代 `data-tauri-drag-region`)。
- 终端可选 WebGL 渲染器:`localStorage aa.terminal.webgl = "1"` 开启(默认 DOM,行为与 Tauri 版一致)。
- 变更基线存放 `app.getPath('userData')/baselines/<fnv16>.json`,与 Rust 版隔离互不影响。

### 保留的既有优化(移植自 Tauri 版)

自绘虚拟化文件树(22px 行窗口化)、worker 池图片解码(ImageBitmap + LRU 96MB/72 项)、
xyflow 画布 `__renderKey` 协调避免节点重渲、Monaco/xyflow/xterm 手动 chunk 拆分、
终端优先两段式就绪(termReady → secondaryReady)、LRU 5 标签页。

## 冒烟验证

`SMOKE_SHOT=<png路径>` 启动会在 8s 后截图并输出探针 JSON;再加 `SMOKE_DRIVE=1`
会自动点击 进入创作区 → 打开作品 → 切画布 tab,验证 PTY/文件树/画布/进度条全链路。
`SMOKE_DEMOS=1` 会在空工作区验证 R2 Demo 下载卡片存在且登录入口不存在。

```bash
npm run build
SMOKE_DRIVE=1 SMOKE_SHOT=/tmp/smoke.png npx electron .
```

## 打包发布

安装包发布走 `tools/e2a`(`bash tools/e2a/scripts/e2a_release.sh`,契约见其
SKILL.md)：把技能仓库、使用手册和 R2 清单回退快照放进 `resources/`，生成
DMG/EXE/VSIX，并按显式参数上传 GitHub Release。Demo ZIP 不进入安装包或
GitHub Release，单独使用 `npm run demos:publish` 发布到 R2。

## 已知边界

- `demos.seed` 为遗留 no-op（演示包统一走 R2 下载安装）。
- PDF 导入仅复制文件,不做文本抽取(与原 Tauri 版一致)。
