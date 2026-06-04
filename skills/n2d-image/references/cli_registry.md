# 图 AI CLI 注册表（Stage 2）

本机生图 CLI 的已知清单 + 探测命令 + 调用规范 + 安装审查 SOP。每加一家新 CLI 时往本文件追加一节。

---

## 通用探测

```bash
# 一次性探测所有已知图 AI CLI
for cli in dreamina gemini-cli openai imagen flux replicate fal; do
  command -v "$cli" >/dev/null 2>&1 && \
    echo "✅ $cli → $(command -v $cli)"
done
```

未找到任何 CLI → 进入"手动指导模式"（Stage 2 SKILL.md 阶段 C 分支 2）。

## 优先级（针对默认即梦视频流）

| 排名 | 组合 | 说明 |
|---|---|---|
| ① | `dreamina` CLI → 即梦视频 | 同 AI 闭环，无锚定句，最稳 |
| ② | `dreamina` CLI 不可用时切手动即梦 web | 同家闭环不打破 |
| ③ | `gemini-cli` → 即梦视频 + 锚定句 | 省钱混合，图阶段免费 |
| ❌ | DALL-E / Flux → 即梦视频 | 画风跨度大，不推荐 |

切换到目标视频 = 可灵 / Veo 时，同理优先选自家或最接近自家的图 CLI。

---

## 档案：dreamina（即梦官方）

- **来源**：字节跳动官方（剪映 / 即梦）
- **安装**：`curl -s https://jimeng.jianying.com/cli | bash`（**安装前必走"安装审查"5 步**）
- **二进制**：`~/.local/bin/dreamina`
- **配套 SKILL**：`~/.dreamina_cli/dreamina/SKILL.md`（可挂为另一个 skill 用）
- **登录**：QR 码 + 抖音 App 扫码（OAuth）
- **平台**：macOS / Linux / Windows（WSL）
- **计费**：高级会员积分（试用期 2026-04-01 → 2026-05-01 已结束）
- **后端模型**：Seedance 2.0

### 子命令（实测）

| 子命令 | 用途 | Stage 2 使用 |
|---|---|---|
| `text2image` | 文生图 | ✅ 定妆首图、无参考图分镜 |
| `image2image` | 图生图 | ✅ 形态变体、参考图分镜 |
| `image_upscale` | 超分 | 可选，封面 4K 化 |
| `text2video` | 文生视频 | Stage 3 用 |
| `image2video` | 图生视频 | Stage 3 用 |

### 调用模板

```bash
# 定妆首图（无参考图）
dreamina text2image \
  --prompt "$(cat <出图/common/prompt/角色定妆.md  内某 prompt 块>)" \
  --negative "$(cat <统一负面词文件>)" \
  --aspect 9:16 \
  --model 图片3.0 \
  --quality high \
  --n 4 \
  --out /tmp/dreamina_<角色名>_v1/

# 形态变体（图生图）
dreamina image2image \
  --ref <出图/common/定妆_<角色>_<常态>.png> \
  --ref-strength 0.8 \
  --prompt "..." \
  --negative "..." \
  --aspect 9:16 \
  --out /tmp/dreamina_<角色>_<变体>/

# 分镜出图（图生图 + 参考图）
dreamina image2image \
  --ref <出图/common/定妆_<角色>.png> \
  --ref-strength 0.75 \
  --prompt "$(cat <出图/第N集/prompt/01_分镜出图.md 镜头N 块>)" \
  --negative "..." \
  --aspect 9:16 \
  --out <第N集/出图/镜头N_xxx.png>
```

> ⚠️ 上面参数名是惯例形式，实际名以官方 SKILL（`~/.dreamina_cli/dreamina/SKILL.md`）为准。**首次调用前必读该文档**核对 flag 名。

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

## 档案：DALL-E 3 / gpt-image-1（OpenAI）

- **CLI**：`openai` 官方 CLI（`pip install openai-cli` 或 `npm install -g openai`）
- **登录**：`OPENAI_API_KEY`
- **强项**：构图艺术感
- **弱项**：亚洲脸卡通化
- **跨即梦/可灵视频时**：必拼锚定句

```bash
openai images create \
  --model gpt-image-1 \
  --prompt "..." \
  --size 1024x1792 \
  --n 4 \
  --out /tmp/openai_<name>/
```

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

**Dreamina 审查结论**（参考案例，详见 `novel2drama/Q&A.md Q14/Q17`）：
- ✅ 域名干净（jimeng.jianying.com + bytednsdoc.com 均字节系）
- ✅ 用户级安装、无 sudo
- ✅ 只动 `~/.local/bin` + `~/.dreamina_cli` + `~/.zshrc` 追加 PATH
- ✅ 可装

**禁止**：装第三方逆向版即梦 CLI（违 ToS + 封号风险）。

---

## 如何加新 CLI

1. 本文件追加一节"档案：xxx"，含：来源 / 安装命令 / 登录方式 / 计费 / 强项弱项 / prompt 语言 / 子命令表 / 调用模板
2. 更新顶部"优先级"表
3. 必要时在 `platforms.md` 加对应图 AI 档案 + 锚定句兼容性说明

## 何时 spawn sub-agent 并发

本集分镜 ≥10 张 或 共享层新增 ≥6 张 时，可 spawn 2-4 个 sub-agent 并发跑 CLI，主线程收集 PNG 落档。**注意**：
- 每个 sub-agent 拿独立的 prompt 子集
- 避免对同一 CLI 账号并发过 4 个（API 限速 / 积分扣得快不易回滚）
- 子 agent 完成后回传"成功路径 + 失败列表"，主线程串行做最终筛选
