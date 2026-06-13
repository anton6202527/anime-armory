# 生视频渠道 CLI/API 注册表（Stage 5）

本机生视频渠道 CLI/API 的已知清单 + 探测命令 + 调用规范 + 安装审查 SOP。`生视频模型` 决定能力与 prompt 适配，`生视频渠道` 决定实际调用入口。

---

## 通用探测

```bash
# 一次性探测所有已知生视频渠道 CLI
for cli in dreamina kling veo seedance runway pika; do
  command -v "$cli" >/dev/null 2>&1 && \
    echo "✅ $cli → $(command -v $cli)"
done
```

未找到任何 CLI → 进入"手动指导模式"（Stage 5 SKILL.md 阶段 C 分支 2）。

## 优先级（按生视频渠道匹配 CLI/API）

| 生视频渠道 | 常用模型 | 首选 CLI/API | 次选 |
|---|---|---|---|
| 即梦/Dreamina | Seedance 2.0 | `dreamina` | 手动即梦 web |
| 可灵/Kling | Kling 3.0 | `kling` API 包装 | 手动可灵 web |
| Google Gemini API | Veo 3.1 | `gcloud ai vertex` / `veo-cli`（如有） | 手动 |
| Runway API | Runway Gen-4 | `runway` API 包装 | 手动 Runway web |
| manual | 用户指定 | 手动登记 | `video_jobs.py --register` 类登记脚本 |

跨家组合（图 AI ≠ 生视频模型）不在本表 — 那是 Stage 4 锚定句的事；Stage 5 同时看 `生视频模型`（prompt/能力）和 `生视频渠道`（执行入口）。

---

## 档案：dreamina（即梦官方）

- **来源**：字节跳动官方
- **安装**：见 `n2d-image/references/cli_registry.md` 同档案（同一 CLI，图视频共用）
- **二进制**：`~/.local/bin/dreamina`
- **配套 SKILL**：`~/.dreamina_cli/dreamina/SKILL.md`
- **登录**：QR + 抖音 App 扫码
- **计费**：高级会员积分（**视频每条扣分远高于图**）
- **后端模型**：Seedance 2.0

### 子命令（实测）

| 子命令 | Stage 5 使用 |
|---|---|
| `text2video` | 文生视频 — 用于空镜/氛围/转场 |
| `image2video` | 图生视频 — **主力**，每条 Clip 用 |
| `image_upscale` | 视频前置图超分（不直接出视频） |

### 调用模板

```bash
# 图生视频（默认）：推荐通过 n2d-video/scripts/video_runner.py 调用。
# Dreamina 实际返回 submit_id；下载需再 query_result，不要假设 image2video 支持 --out。
dreamina image2video \
  --image <出图/第N集/图片/镜头N1_xxx.png> \
  --prompt "$(cat <prompt 块文件或 here-doc>)" \
  --duration 7 \
  --video_resolution 720p \
  --model_version 3.0

dreamina query_result \
  --submit_id=<submit_id> \
  --download_dir=<作品根>/出视频/第N集/视频/_downloads

# 文生视频（空镜）
dreamina text2video \
  --prompt "空镜：残烛在风中摇曳，烛芯吐黑烟" \
  --duration 5 \
  --aspect 9:16 \
  --resolution 720p \
  --out <出视频/第N集/视频/ClipK_<描述>.mp4>
```

> ⚠️ 参数名以官方 SKILL 为准；首次调用前必读 `~/.dreamina_cli/dreamina/SKILL.md` 核对 flag（含分辨率/帧率/质量档 flag 的确切写法：分辨率可能是 `--resolution` / `--quality` / `-r`；帧率 `--fps`；质量档可能用模型名或 `--quality`）。
>
> **分辨率/帧率/质量档由 `出视频规格` 三档预算统一决定**（见 SKILL「出视频规格」节）：预算充足=1080p·30fps·高质量档，预算一般（默认）=720p·24-30fps·标准档，预算不够=720p·24fps·省积分档。**每次开跑前念一行告知当前规格档**（首次问一次记入 `_设置.md`，之后沉默沿用但仍告知，用户随时可改）。

---

## 档案：可灵 Kling

- **API**：https://kling.kuaishou.com/dev（官方 REST）
- **CLI**：目前无官方独立 CLI；可自封一个 `kling-wrap.sh`：

```bash
#!/usr/bin/env bash
# kling-wrap.sh — 极简包装，调官方 REST API
# 用法：kling-wrap image2video --first <png> --last <png> --prompt "..." --duration 8 --out clip.mp4
...
```

- **特色**：首尾帧机制 + 运动笔刷（复杂运动用首尾帧静态引导）
- **调用模板**：
  ```bash
  kling image2video \
    --first <出图/第N集/图片/镜头N1_xxx.png> \
    --last <出图/第N集/图片/镜头N2_xxx.png> \
    --prompt "..." \
    --duration 8 \
    --resolution 720p \
    --motion-brush <可选 motion mask> \
    --out <ClipK.mp4>
  ```

---

## 档案：Veo（Google）

- **API**：Google Cloud Vertex AI（`gcloud ai`）
- **CLI**：`gcloud ai models invoke veo-...`（参考 GCP 文档）
- **prompt 语言**：**英文优先**
- **时长**：约 8s/Clip
- **登录**：Google Cloud 凭证（`gcloud auth login`）
- **运镜术语**：英文电影镜头术语（dolly in / pan / tracking shot / orbit）

```bash
gcloud ai models invoke veo-XX \
  --project <PROJECT_ID> \
  --image <出图/第N集/图片/镜头N1_xxx.png> \
  --prompt "<English prompt>" \
  --duration 8 \
  --resolution 720p \
  --output <ClipK.mp4>
```

部分版本不支持独立负面框 → 写进 prompt 或改正向描述。

---

## 档案：Seedance（字节）

- **本质**：dreamina CLI 的 `text2video/image2video` 后端就是 Seedance 2.0
- 单独 CLI 通常不需要单装；如有独立官方 CLI，走相同审查流程

---

## 档案：Runway / Pika（备选）

- **Runway**：API 提供，CLI 需自封；英文 prompt；强项是镜头控制
- **Pika**：API 提供；强项是短动作
- 国风短剧不建议作为主力（画风与即梦/可灵差距大）

---

## 安装审查（同 Stage 4 标准）

详见 `n2d-image/references/cli_registry.md` 的"安装审查"章节。5 步：

1. 域名核对
2. WebFetch 读脚本
3. 不 sudo
4. 不写敏感位置
5. 无可疑行为

**禁止**：装第三方逆向视频 CLI（违 ToS + 封号风险）。

---

## 何时并发

本集 Clip 数 ≥6 时可并行 2-3 个独立任务跑 CLI。注意：
- **视频 API 限速比图更严**，单账号 ≤2-3 并发更安全
- 视频每条扣分多，**翻车成本高**——任务跑完后主流程认真筛选，不通过的废视频归档 `废料/出视频/第N集/`
- 并发任务不要自行重抽 —— 由主流程统一决定是否改 prompt + 重跑

---

## 关于"为什么大多数 Clip 跑两遍"

image2video 的运动估计有随机性。同 prompt 不同 seed 出来的人脸抖动幅度、镜头加速度都可能不同。**每个 Clip 跑几条挑稳由 `出视频规格` 三档预算统一决定**（见 SKILL「出视频规格」节）：预算充足=关键镜 2-3 条·普通镜 2 条；预算一般（默认）=关键镜（人脸特写/反转高光/钩子）2 条·普通镜（空镜等）1 条；预算不够=全部 1 条。挑视觉一致性更好的那条落档。
