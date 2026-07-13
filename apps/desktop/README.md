# AnimeArmory Desktop (Electron)

Creation Armory(创作兵工厂)桌面 IDE 的 **Electron 版**(自原 Tauri 版重构而来,
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
作品工作区固定为 `~/AnimeArmory`(可经菜单"切换工作区…"更换,与技能仓库互斥隔离)。

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

```bash
npm run build
SMOKE_DRIVE=1 SMOKE_SHOT=/tmp/smoke.png npx electron .
```

## 打包发布

发布走 `tools/e2a`(`bash tools/e2a/scripts/e2a_release.sh`,契约见其 SKILL.md):
自动把技能仓库 + demo 目录经 `tools/e2a/scripts/sync_bundle.cjs` 内置进
`resources/`(electron-builder `extraResources`),出 DMG 并连同各线 demo zip
上传 Release。

## 已知边界

- `demos.seed` 为遗留 no-op(演示包统一走 Release 下载安装)。
- PDF 导入仅复制文件,不做文本抽取(与原 Tauri 版一致)。
