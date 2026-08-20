# 生图模型/渠道 / 本地生图能力注册表（Stage 4：出图）

本机生图能力的已知清单 + 探测命令 + 调用规范 + 安装审查 SOP。这里的"能力"包含 Codex 会话内置生图、Codex 插件、官方 CLI、以及可自动落 PNG 的本地服务。每加一家新入口时往本文件追加一节。

---

## 通用探测

```bash
# 每次进入 n2d-image 生图阶段都重新探测
for cli in codex openai dreamina gemini-cli seedream kling sora; do
  command -v "$cli" >/dev/null 2>&1 && \
    echo "$cli -> $(command -v $cli)"
done
codex features list 2>/dev/null | rg 'image_generation|artifact' || true
codex plugin list 2>/dev/null | rg -i 'image|openai|fal|replicate|browser|computer-use' || true
python3 skills/n2d/_lib/image_backend_adapter.py scan --json
```

`scan --json` 的 `usable_backends` 是“当前可自动确认能落 PNG”的列表。若 **0 个可用**，停止并提示“当前无可用生图渠道，请准备好可以生图的官方/已登录渠道”；`needs_confirmation_backends` 只能列为检测到但需人工确认，不当作可用。若 **≥2 个可用**，producer-owned router 按项目需求只推荐一组 `生图模型 + 生图AI/生图渠道`（长篇/多集/核心角色/多人同框优先主体库或多参考强模型/渠道；单集 demo/快速迭代优先 Codex；文字/编辑/透明背景等能力按当天官方文档和 CLI/API help 核验），将该推荐并入同一次付费确认，不再额外暂停；用户可在花钱前覆盖。确认后写 `<作品根>/_设置.md`，整集统一一组模型+渠道。

所选渠道未找到可自动落 PNG 的入口 → **停下报告**（见 SKILL「生图后端规则」），不偷偷换后端兜底（换后端=混用）。**生成轴=具体模型（C5）**：`生图模型` 默认 **GPT Image 2 / OpenAI GPT Image 系列归一名**，访问入口 `生图AI`(渠道) 默认 **Codex CLI**；执行前必须以官方 docs/CLI/API 刷新实际 model id。全项目生图优先 Codex/OpenAI；Seedream、可灵主体库、Nano Banana、Dreamina/即梦官方图像模型等非 Codex/OpenAI 后端只能作为用户签核例外，签核写入 `<作品根>/合规/image_backend_override.json`。上面的通用探测覆盖白名单常见 CLI 名；具体是否可用仍以本文件各后端档案和官方帮助为准。禁止第三方逆向 CLI、`同视频AI` / `同视频模型` 含糊口径和 web 自动化出图；`<作品根>/_设置.md` 写 `同视频AI` 或 `同视频模型` 时改成显式后端名。

## 优先级（生视频后端未固定时）

| 排名 | 组合 | 说明 |
|---|---|---|
| ① | Codex 会话内置 `image_gen` / Codex image_generation feature → 通用视频兼容锚定；若已固定生视频模型则拼对应锚定句 | 当前 Codex 能力优先；生成后必须把图从 `$CODEX_HOME/generated_images/...` 移入作品目录 |
| ② | 官方 OpenAI Images 入口（`openai` CLI 或 Codex/OpenAI 插件）→ 通用视频兼容锚定；若已固定生视频模型则拼对应锚定句 | 可自动批量落 PNG 时优先于国内兜底；注意统一视频兼容视觉锚点 |
| 签核例外 | Seedream / 可灵主体库 / Nano Banana(Gemini) / Dreamina/即梦官方 CLI | 仅在用户明确签核并写 `<作品根>/合规/image_backend_override.json` 后可用；选定后整集统一、不与 Codex 混用。Sora Cameo 仅旧项目/manual |
| 禁止 | 第三方逆向 CLI / `同视频AI` 或 `同视频模型` 含糊口径 / 即梦 web 自动化出图 / 未签核 Dreamina 图片跑法 | 安全 invariant：未授权路径禁用；官方 Dreamina CLI 也不能无签核用于图片阶段 |

切换/固定目标生视频模型/渠道时，图片阶段仍保持所选生图模型/渠道；需要风格兼容时拼目标生视频模型的图像风格锚定句。未固定时不回到开局强问视频后端，先拼通用视频兼容锚定并由 n2d-video 后续路由。

---

## 档案：Codex 内置生图 / Codex CLI

- **来源**：Codex 会话能力 + `codex` CLI。
- **定位**：优先生图入口，但要分清"会话内置工具"和"命令行子命令"。
- **本机探测**：
  - `command -v codex`
  - `codex features list | rg 'image_generation|artifact'`
  - `codex plugin list | rg -i 'image|openai|fal|replicate|browser|computer-use'`
  - `codex --help` / `codex exec --help`
- **当前实测注意**：`codex` / `codex exec` 的 help 只有 agent、review、plugin、mcp 等子命令，`-i/--image` 是"附图输入"，不是"生成图片"。所以不能仅凭 `codex` 在 PATH 中就写 `codex images generate`。
- **可用判定**：
  1. 当前 agent 有内置 `image_gen` 工具，或
  2. Codex 插件/配置明确暴露可生成并保存 PNG 的图像工具，或
  3. 用户提供了可由 `codex exec` 稳定调用且会把 PNG 写入指定路径的本地命令/工作流。
- **落档规则**：内置 `image_gen` 生成图默认在 `$CODEX_HOME/generated_images/...`；项目资产必须复制/移动到 `创作区/制漫剧/<剧名>/出图/共享/图片/` 或 `创作区/制漫剧/<剧名>/出图/第N集/图片/`，不能只引用 `$CODEX_HOME` 路径。
- **批量策略**：多个不同镜头用多次内置生图调用或已验证的批量入口；不要用一个泛 prompt 代替逐镜 prompt。

---

## 档案：OpenAI Images（官方）

- **来源**：OpenAI 官方 Images API / 官方 CLI / Codex OpenAI 插件（如已安装）。
- **探测**：`command -v openai`、`OPENAI_API_KEY`、`codex plugin list`。
- **强项**：构图、审美、文字理解。
- **弱项**：古装东方脸和跨镜一致性要显式锚点；固定 Seedance/Kling/Veo 等生视频模型时必须拼目标生视频模型的图像风格锚定句，未固定时拼通用视频兼容锚定。
- **调用模板**（仅在官方 CLI 可用且参数确认后使用）：

```bash
openai images create \
  --model gpt-image-2 \
  --prompt "..." \
  --size "<官方支持的竖版尺寸；必要时生成后按 9:16 安全裁切>" \
  --n 1 \
  --out /tmp/openai_<name>/
```

实际模型名、尺寸枚举和 CLI 参数随版本变化，首次使用前跑 `openai images --help` 或官方文档核对；不要把旧模板里的 `gpt-image-1` 当固定真值。

---

## 档案：dreamina（即梦官方 CLI）

- **来源**：字节跳动官方（剪映 / 即梦）
- **安装**：`curl -s https://jimeng.jianying.com/cli | bash`（**安装前必走"安装审查"5 步**）
- **二进制**：`~/.local/bin/dreamina`
- **配套 SKILL**：`~/.dreamina_cli/dreamina/SKILL.md`（可挂为另一个 skill 用）
- **登录**：QR 码 + 抖音 App 扫码（OAuth）
- **平台**：macOS / Linux / Windows（WSL）
- **计费**：高级会员积分（按官方实时档位为准；早期试用期已结束，不再列具体日期）
- **后端模型**：Seedance 2.0
> 注：Dreamina/即梦官方 CLI 不再作为图片阶段默认备选；只有用户明确签核并写 `<作品根>/合规/image_backend_override.json` 后才能跑本 runner。第三方逆向版、`同视频AI` / `同视频模型` 含糊口径和 web 自动化始终禁用。

### 子命令（实测）

| 子命令 | 用途 | Stage 4 使用 |
|---|---|---|
| `text2image` | 文生图 | ✅ 可用于共享定妆首图、场景、道具、空镜 |
| `image2image` | 图生图 / 参考图派生 | ✅ 可用于角色定妆组派生、本集分镜首尾帧 |
| `image_upscale` | 超分 | 可选，封面 4K 化 |
| `text2video` | 文生视频 | Stage 5 用 |
| `image2video` | 图生视频 | Stage 5 用 |

### 图片阶段调用原则

- 签核例外且 `生图AI=Dreamina` 时，优先用 `image2image` / 多参考能力生成含角色镜头，避免纯文生图导致脸漂；共享角色第一张定妆可用 `text2image` 起稿，再用 `image2image` 按 `library_tier` 派生多视图/半身/turnaround（`core_full` 为正/前3/4/侧/后3/4/背五角）。
- 输出必须落到 `出图/共享/图片/` 或 `出图/第N集/图片/`，废图进 `废料/出图/...`。
- 不使用即梦 web 自动化；不安装第三方逆向版 CLI。

---

## 档案：gemini-cli（Google Imagen）

- **来源**：Google 官方 `npm install -g @google/gemini-cli`（或对应渠道）
- **登录**：Google OAuth
- **计费**：订阅制 / 免费额度
- **强项**：质感、光感细腻
- **弱项**：东方面孔默认偏西方 → 跨即梦/可灵视频时**必拼锚定句**
- **prompt 语言**：英文最稳

### 调用模板

```bash
gemini-cli images generate \
  --prompt "<full English prompt + Eastern Asian face anchor sentence>" \
  --aspect 9:16 \
  --n 4 \
  --out /tmp/gemini_<name>/
```

参考图机制各版本差异较大，使用前查最新 doc。

---

## 档案：可灵 Kling

- **API**：官方 https://kling.kuaishou.com/dev
- **CLI**：暂无官方独立 CLI，通过 API 包装。本仓库可未来加一个 `kling-wrap.sh` 薄封装。
- **使用场景**：目标视频 = 可灵时 推荐自家闭环

---

## 档案：Flux Pro

- **后端**：Black Forest Labs（通过 Replicate / fal.ai 调用）
- **CLI**：`replicate` / `fal`
- **强项**：照片级写实
- **弱项**：默认好莱坞审美，亚洲脸需 LoRA

---

## 档案：Stability SDXL / SD3

- **可控性最高**（开源 + LoRA + ControlNet）
- **门槛**：自托管 + 调参
- 不推荐作为本 skill 的默认 CLI；进阶用户做"风格统一返工"时启用

---

## 安装审查（任何 `curl xxx | bash` 类必走）

1. **域名核对** — 安装命令域名 + 脚本里下载二进制的 URL 域名 必须落在该厂商**官方主域名**下。第三方域名、缩短链接、不知名 CDN → 拒绝。
2. **WebFetch 读脚本** — 不直接 pipe 到 bash，先用 WebFetch 把脚本内容拉出来读。
3. **是否 sudo / root** — 合规用户级工具**不应**要 sudo。
4. **是否往敏感位置写** — 安全：`~/.local/bin`、`~/.dreamina_cli`、`~/.zshrc` 追加 PATH。危险：`/usr/local/bin`、`/etc/`、`/var/`、sudoers。
5. **是否有可疑行为** — 上传本地文件 / `eval $(curl ...)` / base64 解码执行 / 创建 systemd cron / 改其他工具配置 → 警惕。

**Dreamina 审查结论**（参考案例，详见 `n2d/Q&A.md Q14/Q17`）：
- ✅ 域名干净（jimeng.jianying.com + bytednsdoc.com 均字节系）
- ✅ 用户级安装、无 sudo
- ✅ 只动 `~/.local/bin` + `~/.dreamina_cli` + `~/.zshrc` 追加 PATH
- ✅ 可装

**禁止**：装第三方逆向版即梦 CLI；只用已登录的官方 CLI。

---

## 如何加新 CLI

1. 本文件追加一节"档案：xxx"，含：来源 / 安装命令 / 登录方式 / 计费 / 强项弱项 / prompt 语言 / 子命令表 / 调用模板
2. 更新顶部"优先级"表
3. 必要时在 `platforms.md` 加对应生图模型/渠道档案 + 锚定句兼容性说明

## 何时并发

本集分镜 ≥10 张 或 共享层新增 ≥6 张 时，可并行 2-4 个独立任务跑 CLI，主流程收集 PNG 落档。**注意**：
- 每个任务拿独立的 prompt 子集
- 避免对同一 CLI 账号并发过 4 个（API 限速 / 积分扣得快不易回滚）
- 任务完成后回传"成功路径 + 失败列表"，主流程串行做最终筛选
