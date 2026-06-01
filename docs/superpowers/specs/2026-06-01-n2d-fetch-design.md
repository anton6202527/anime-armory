# n2d-fetch — Stage 0.5 联网取书 skill 设计

- 日期:2026-06-01
- 状态:已确认,待实现
- 所属流水线:`novel2drama`(小说 → AI 漫剧/短剧)

## 1. 目标与定位

在 `novel2drama` 流水线最前端增加一道**取料工序**:

> 给定一个**书名**(或章节目录页 URL)→ 联网抓取小说全文 → 同时输出 `.txt` 和 `.docx` 两种格式 → 落到 `artifacts/<书名>/小说/`,可直接接 `/n2d-script` 拆集。

skill 名:`n2d-fetch`。放在 `.claude/skills/n2d-fetch/`,与 `novel2drama` 调度同级。

设计目标:**书名越确定越具体越好** —— 通过"搜索→候选→人工确认"流程锁定到唯一一本,避免抓错版本/译本/节选。

## 2. 职责分工

采用「脚本抓正文 + Claude 搜候选」分工:

- **Claude(找对书)**:用 WebSearch/WebFetch 在公版站检索书名 → 列出候选,每个候选强制带"区分维度":作者、来源站、字数/卷数、译本、全本 vs 节选 → 用户确认唯一一本并拿到目录页 URL。
- **Python 脚本(抓全 + 转格式)**:`scripts/fetch_novel.py` 接收目录页 URL,遍历抓取全部章节正文 → 合并 → 同时输出 `.txt` 与 `.docx`。

## 3. 抓取引擎(公版站优先 + 通用兜底)

`fetch_novel.py` 两条路径:

### 3.1 站点适配器(优先,最稳、合法)
- **Project Gutenberg**:走 gutendex API(`https://gutendex.com`)检索 + 下载,英文公版。章节边界清晰。
- **中文维基文库 Wikisource**:走 MediaWiki API,中文公版经典(已过版权期作品,如四大名著、鲁迅等)。

### 3.2 通用兜底
任意目录页 URL → `requests` 抓页 → `trafilatura` 提正文(失败回退 `readability-lxml`)→ 遍历章节链接。
- 成功率因站而异;脚本逐章报告抓取状态(成功/失败/疑似空)。

### 3.3 依赖
`requests beautifulsoup4 trafilatura python-docx`(以及 trafilatura 失败时的回退 `readability-lxml`,可选)。
脚本启动时自检依赖,缺失则打印一行 `pip install ...` 提示,**不自动安装**。

## 4. 锁定唯一一本

- 默认 **搜索 → 候选表 → 用户确认** 流程。候选表必须包含区分维度(作者 + 来源站 + 字数/卷数 + 译本 + 全本/节选)。
- 输入已是 URL 时**跳过搜索**,直接抓取。
- 抓完在输出文件头部写入 **provenance 元信息**:来源 URL、抓取日期、章节数、总字数、版权状态判定。

## 5. 输出格式

落点:`artifacts/<书名>/小说/`;参数 `--out <路径>` 可覆盖。

- **`<书名>.txt`**:UTF-8。章节间统一分隔:`\n\n第N章 标题\n\n`,与 `n2d-script/scripts/split_novel.py` 的输入约定对齐。文件头含 provenance 注释块。
- **`<书名>.docx`**:python-docx 生成。章节标题用 Heading 样式,正文段落化(便于人读 / 导入飞书云文档)。

两个文件内容一致,仅格式不同。

## 6. 合法性护栏(写进 SKILL.md 铁律)

- 默认只引导公版 / 开放授权(CC、作者自授权、已过版权期)来源。
- 脚本对已知付费墙站(起点、番茄、晋江等)维护一份**黑名单**,命中直接拒抓并提示。
- 通用兜底抓取**非公版** URL 时,抓取前**弹一次来源合法性确认**(用户声明有权使用才继续)。
- provenance 如实记录版权状态判定。
- 不实现绕过反爬 / 付费墙 / 登录墙的逻辑。

## 7. 与调度器集成

`novel2drama` 调度 SKILL.md 增加一条路由:当用户**只给书名、没给本地小说文件**时 → 推荐先跑 `/n2d-fetch`;抓完产出 `artifacts/<书名>/小说/<书名>.txt` 后再走 `/n2d-script`。

## 8. 目录结构

```
.claude/skills/n2d-fetch/
├── SKILL.md                      # SOP:搜候选 → 确认 → 跑脚本 → 落地 → 提示 /n2d-script;含合法性铁律
├── scripts/fetch_novel.py        # 站点适配器(Gutenberg/Wikisource)+ 通用兜底 + txt/docx 双输出 + provenance + 依赖自检 + 付费墙黑名单
└── references/
    ├── sources.md                # 公版站清单 + 各 adapter 用法 + 付费墙黑名单说明
    └── formats.md                # txt/docx 输出规范(对齐 n2d-script 输入)
```

## 9. 验收标准

1. 给一个中文维基文库或 Gutenberg 的公版作品 → 能完整抓取并产出 txt + docx,章节分隔符合 `split_novel.py` 约定。
2. 给一个任意目录页 URL → 通用兜底能抓取并逐章报告状态。
3. 命中付费墙黑名单 → 拒抓并给出清晰提示。
4. 缺依赖 → 打印明确的 `pip install` 提示而非崩溃。
5. 输出文件头部含完整 provenance。
6. `novel2drama` 调度能在"只给书名"场景下推荐 `/n2d-fetch`。
