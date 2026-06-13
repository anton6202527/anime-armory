# 图 AI / 本地生图能力注册表（Stage 4：出图）

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
```

所选后端未找到可自动落 PNG 的入口 → **停下报告**（见 SKILL「生图后端规则」），不偷偷换后端兜底（换后端=混用）。`生图AI` 默认 Codex，当前也可选 Dreamina/即梦官方 CLI、Seedream/可灵主体库/Nano Banana/Sora Cameo 等官方/已登录后端（全集统一一个、不混用）。上面的通用探测覆盖白名单常见 CLI 名；具体是否可用仍以本文件各后端档案和官方帮助为准。禁止第三方逆向 CLI、`同视频AI` / `同视频模型` 含糊口径和 web 自动化出图；`<作品根>/_设置.md` 写 `同视频AI` 或 `同视频模型` 时改成显式后端名。

## 优先级（以 `生视频模型=Seedance 2.0` + `生视频渠道=即梦/Dreamina` 为例）

| 排名 | 组合 | 说明 |
|---|---|---|
| ① | Codex 会话内置 `image_gen` / Codex image_generation feature → 所选生视频模型 + 对应锚定句 | 当前 Codex 能力优先；生成后必须把图从 `$CODEX_HOME/generated_images/...` 移入作品目录 |
| ② | 官方 OpenAI Images 入口（`openai` CLI 或 Codex/OpenAI 插件）→ 所选生视频模型 + 对应锚定句 | 可自动批量落 PNG 时优先于国内兜底；注意统一目标生视频模型的视觉锚点 |
| 官方备选 | Dreamina/即梦官方 CLI / Seedream / 可灵主体库 / Nano Banana(Gemini) / Sora Cameo 官方 API | 当前可选；选定后整集统一、不与 Codex 混用；多角色同框/跨集锁人更稳 |
| 禁止 | 第三方逆向 CLI / `同视频AI` 或 `同视频模型` 含糊口径 / 即梦 web 自动化出图 | 安全 invariant：未授权路径禁用；官方 Dreamina CLI 和官方 Seedream API 不在此列 |

切换目标生视频模型/渠道时，图片阶段仍保持 Codex/OpenAI；需要风格兼容时拼目标生视频模型的图像风格锚定句。

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
- **落档规则**：内置 `image_gen` 生成图默认在 `$CODEX_HOME/generated_images/...`；项目资产必须复制/移动到 `制漫剧/<剧名>/出图/共享/图片/` 或 `制漫剧/<剧名>/出图/第N集/图片/`，不能只引用 `$CODEX_HOME` 路径。
- **批量策略**：多个不同镜头用多次内置生图调用或已验证的批量入口；不要用一个泛 prompt 代替逐镜 prompt。

---

## 档案：OpenAI Images（官方）

- **来源**：OpenAI 官方 Images API / 官方 CLI / Codex OpenAI 插件（如已安装）。
- **探测**：`command -v openai`、`OPENAI_API_KEY`、`codex plugin list`。
- **强项**：构图、审美、文字理解。
- **弱项**：古装东方脸和跨镜一致性要显式锚点；跨 Seedance/Kling/Veo 等生视频模型时必须拼目标生视频模型的图像风格锚定句。
- **调用模板**（仅在官方 CLI 可用且参数确认后使用）：

```bash
openai images create \
  --model gpt-image-1 \
  --prompt "..." \
  --size 1024x1792 \
  --n 1 \
  --out /tmp/openai_<name>/
```

实际 CLI 参数随版本变化，首次使用前跑 `openai images --help` 或官方文档核对。

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
> 注：Dreamina/即梦官方 CLI 图片生成已放行；仅禁第三方逆向版、`同视频AI` / `同视频模型` 含糊口径和 web 自动化。

### 子命令（实测）

| 子命令 | 用途 | Stage 4 使用 |
|---|---|---|
| `text2image` | 文生图 | ✅ 可用于共享定妆首图、场景、道具、空镜 |
| `image2image` | 图生图 / 参考图派生 | ✅ 可用于角色定妆组派生、本集分镜首尾帧 |
| `image_upscale` | 超分 | 可选，封面 4K 化 |
| `text2video` | 文生视频 | Stage 5 用 |
| `image2video` | 图生视频 | Stage 5 用 |

### 图片阶段调用原则

- `生图AI=Dreamina` 时，优先用 `image2image` / 多参考能力生成含角色镜头，避免纯文生图导致脸漂；共享角色第一张定妆可用 `text2image` 起稿，再用 `image2image` 派生侧/背/半身/三视图。
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
3. 必要时在 `platforms.md` 加对应图 AI 档案 + 锚定句兼容性说明

## 何时并发

本集分镜 ≥10 张 或 共享层新增 ≥6 张 时，可并行 2-4 个独立任务跑 CLI，主流程收集 PNG 落档。**注意**：
- 每个任务拿独立的 prompt 子集
- 避免对同一 CLI 账号并发过 4 个（API 限速 / 积分扣得快不易回滚）
- 任务完成后回传"成功路径 + 失败列表"，主流程串行做最终筛选
