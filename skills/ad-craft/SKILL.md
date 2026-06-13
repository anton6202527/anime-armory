---
name: ad-craft
description: Shared machine contracts and deterministic helpers for the ad-* (拍广告/广告片) skill family — ad project _meta/_设置/_进度 fields, user choice points, the unsplit stage table, the cutdown/多比例 deliverable axis, and AI usage + 授权 disclosure. Other ad-* skills reference these by file path; users can also invoke directly for 拍广告 pipeline contract, manifest, cutdown, 交付规格, or AI usage disclosure questions. Triggers ad contract, ad-craft, 广告合约, 广告契约, 交付版本, cutdown, 多比例交付, 交付规格, AI使用披露, 广告合规留痕.
---

# ad-craft — 拍广告线共享契约

`ad-craft` 是 `ad-*`（拍广告）家族的机器单一真值源，不写文案、不出图、不剪辑。它只沉淀字段、选择点、阶段表、交付件（cutdown/多比例）约定和合规留痕脚本，避免 `ad-script` / `ad-image` / `ad-video` / `ad-compose` 各自解释同一件事。

**自包含铁律**：`ad-*` 不复用 n2d-* / mv-* / novel-* / song-* 任何家族 skill。可借鉴 n2d 的配音先行、两层定妆、契约继承、接缝逻辑等成熟思路，但代码与文档各写各的。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/ad-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**。合规/不可逆/花钱多的点（`水印-AI合规标识`、`广告法地区`、`音乐来源`）每次仍确认。

本 skill 涉及的选择点：`广告类型`、`创意路线`、`基础视觉风格`、`主片时长`、`交付比例`、`cutdown版本`、`生图AI`、`一致性增强`、`生视频模型`、`生视频渠道`、`出视频规格`、`配音后端`、`音乐来源`、`品牌包装模板`、`字幕语言`、`广告法地区`、`交付规格` 等。

## 包含内容

| 主题 | 参考 / 脚本 | 何时用 |
|---|---|---|
| 机器契约 | `references/contract.md` + `scripts/contract.py` | 初始化项目、写 `_设置.md`/`_进度.md`/`_meta.json`、派生 cutdown 交付件、查阶段表/选择点/交付规格时；含 **brief 必填分层** `brief_check()`（必问最小集 brand/product/usp/audience；claims/rights/legal_lines 可标「待补」延后到花钱 gate 前） |
| 只读进度 | `scripts/progress.py` | 查项目当前前沿 + 下一步该跑哪个 ad-* skill（公共 `progress` 分发路由到此，与 novel/song/mv 各 craft 同构） |
| 状态回写 | `scripts/progress_set.py` | 阶段完成后回写 `_进度.md` 阶段进度；交付件存在后回写交付版本矩阵状态/路径 |
| 花钱 gate | `scripts/gate.py` | image/video/compose 正式生产入口统一阻断：brief 合规项、广告法报告、分镜时长、占位 VO、上游产物 |
| AI 使用 + 授权披露 | `scripts/ai_usage.py` | 投放、交平台前记录 AI 生图/视频、配音、音乐授权、代言人肖像、字体素材、水印/AI 标识 |

## 共享脚本

```bash
# 初始化项目 _设置.md / _进度.md（一般由 ad 调度自动调用 contract.py 的函数生成）
cd skills/ad-craft/scripts && python3 -c "import contract; print(contract.progress_markdown('某品牌618'))"

# 只读进度：当前前沿 + 下一步建议（公共 progress 分发也走这里）
python3 skills/ad-craft/scripts/progress.py "<拍广告作品根>"

# 花钱/不可逆阶段 gate
python3 skills/ad-craft/scripts/gate.py "<拍广告作品根>" --stage image
python3 skills/ad-craft/scripts/gate.py "<拍广告作品根>" --stage video
python3 skills/ad-craft/scripts/gate.py "<拍广告作品根>" --stage compose

# 阶段/交付回写
python3 skills/ad-craft/scripts/progress_set.py set-stage "<拍广告作品根>" image --status ✅ --artifact 出图/分镜
python3 skills/ad-craft/scripts/progress_set.py set-deliverable "<拍广告作品根>" master --status ✅ --path 合成/成片_主片.mp4

# 投放前 AI 使用 + 授权披露
python3 skills/ad-craft/scripts/ai_usage.py "<拍广告作品根>" \
  --visual-mode AI-generated --video-mode AI-generated \
  --music-status 授权曲库:已购 --talent-status 未使用真人 --publish-target 抖音
```

输出：`合规/ai_usage.json` + `合规/AI使用说明.md`。

## 设计原则

- **不拆集 + cutdown 轴**：一条主片是整体；多时长/多比例/A·B 是「交付件 deliverable」，登记在 `_进度.md` 交付版本矩阵，由 `default_deliverables()` 按 `主片时长`/`交付比例`/`cutdown版本` 派生。
- **音频先行**：VO 实测时长驱动镜头时长，`ad-script` 跑两遍（脚本 → 配音后分镜），与 n2d 同构。
- **选择点不写死**：广告类型、创意路线、视觉风格、生图后端、视频后端、配音后端、音乐来源、交付规格都读 `<作品根>/_设置.md`。
- **不伪装云端自动化**：没有后端 SDK/凭证时只生成稳定 job 包；外部生成后再登记。

## 测试

```bash
cd skills/ad-craft/scripts && python -m pytest test_contract.py test_progress_set_gate.py
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 把广告拆成「集」 | 拍广告不拆集；多时长/多比例走 cutdown 交付件矩阵，不是 `第N集` |
| 手工改 manifest/交付矩阵字段 | 经对应阶段脚本重新生成，别手改机器契约字段规范 |
| 偏好硬编码（写死即梦/720p/30s） | 一律读 `_设置.md`；新增选择点先进 `skills/ad-craft/references/选择点与偏好.md` 目录 |
| 投放前漏 AI/授权留痕 | 脱离管线投放前必须在 `合规/` 调用 `ai_usage.py` 并填具体授权模式 |
