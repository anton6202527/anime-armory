# 生视频模型/渠道 + 模型路由（ad-video · 本线自持）

> 候选与关键能力最后核验：2026-08-20。当前一手来源包括 [BytePlus Seedance 2.0 API](https://docs.byteplus.com/en/docs/modelark/1520757)、[Google Veo 3.1](https://ai.google.dev/gemini-api/docs/video)、[Kling VIDEO 3.0 指南](https://app.klingai.com/cn/quickstart/klingai-video-3-model-user-guide)、[MiniMax video API](https://platform.minimax.io/docs/api-reference/api-overview)、[Runway 模型列表](https://docs.dev.runwayml.com/guides/models/)、[Luma Ray3.2](https://lumalabs.ai/news/introducing-ray-3-2) 与 [Pika 2.5 API](https://dev.pika.art/models/pika/pika-2.5/image-to-video)。菜单只表示候选存在；执行仍以项目账号、地区、模型 ID 和 CLI/API probe 为准。

`生视频模型` + `生视频渠道` 读项目 `_设置.md`，但新广告立项不再强制首跑选择具体后端。模型只作默认/普通镜兜底建议，渠道只作调用入口偏好。`视频模型路由=自动按镜头路由` 时按镜头**能力**、CLI/API 探测和账号约束选 primary/fallback；否则固定 `生视频模型`。只有客户/投放/账号要求固定后端、用户明确指定或 router/probe 找不到可执行后端时才问具体模型/渠道。旧 `生视频AI` 兼容读取。模型/渠道能力随版本变，正文写能力不绑版本。

## 路由是工程化产物（不是 prose 表）

`scripts/route.py` 读 `脚本/storyboard.json` 的镜型，**按能力分类**（不对后端品牌字串分支），落
`出视频/分镜/prompt/video_model_routes.json`，逐镜 `{primary, fallback, reason, capability, max_clip_seconds, findings}`。换厂只改 `route.py` 的 `BACKEND_PROFILES` 能力档，不改判型逻辑。下表是能力档的人读镜像，与 `BACKEND_PROFILES` 同步。

## 镜头类型 → 能力 → 路由

| 镜头类型 | 需要的能力 | primary（能力优先） | fallback | 为什么 |
|---|---|---|---|---|
| 产品展示 / hero 环绕 / 绑定 `PROD_*` | 主体一致性强 | Seedance / Kling 3.0 Element | 即梦 | 包装/logo 不能抖花，要稳 |
| 情绪 / 人物特写 | 电影感 | 可灵 / Veo | 即梦 | 表演与质感 |
| demo 实拍质感 / 手持 | 真实运动 | Seedance / 即梦 | 即梦 | 拟真手持、自然动态 |
| 痛点情境 / 叙事镜 | 通用 | 即梦 / `生视频模型` | 通用 | 普通叙事 |
| 空镜 / 转场 | 通用 | 即梦 / 通用 | 通用 | 低风险 |
| end card / 包装定格 | 静帧 | 静帧或极慢运镜 | — | 文字/logo 要稳，必要时 ad-compose 合成 |

## 单 Clip 时长上限按后端（路由 block 依据）

`route.py` 用这组上限做时长上限校验：镜头时长超 primary 上限 → block；≥90% 上限 → warn。

| 后端 | 单 Clip 上限 |
|---|---|
| 即梦 image2video | ≤ 8s |
| Seedance | ≤ 15s |
| 可灵 Kling 3.0 | ≤ 15s |
| Veo | ≈ 8s |

广告镜短，一般够；能一镜到底就别切碎。超 primary 上限就换支持更长时长的后端（Seedance/Kling 3.0）或拆镜/缩时长。

## 上游视觉契约单一真值源（契约继承用）

`scripts/inherit_contract.py` 比对的上游契约（品牌色 HEX / 光位锚 / 轴线）真值源：

1. **首选** `出图/分镜/prompt/00_总览.md` 的「视觉一致性契约」节（出图细化后烤进首帧的最终值）；
2. **回退** `脚本/storyboard.json`.visual_contract（出图总览尚未生成时的脚本种子）。

与 `ad-video/SKILL.md` 同口径。品牌色按 HEX 归一比对（`#E60012` 与 `rgb(230,0,18)` 视为同色，不误判漂移）。

## 后端感知 prompt compiler

广告使用“完整生产合同 → 本线 compiler → 模型提交 prompt”的单向边界：

- 完整合同保留品牌资产、产品锁、精确文案、平台安全区、广告合规、路由和 provenance；这些字段继续由 `inherit_contract.py` / gate 严格检查。
- `skills/ad/_lib/ad_video_prompt_compiler.py` 只抽取可见产品动作、单一主运镜、明确环境响应、结尾落幅、产品保持、文字策略和少量负向，按 primary 后端选 profile。
- Runway profile 使用肯定式主 prompt，不提交负向字段；支持独立负向字段的 profile 把负向与主 prompt 分离；仅能内联负向的中文后端使用一条精简“避免”约束。
- `render_dreamina.py` 只读取编译块。旧 Markdown 仅保留迁移期 fallback；新 prompt 缺编译块会被 `inherit_contract.py` block，不能进入付费生成。
- 精确 CTA、slogan、价格、法律声明和 UI 文案不由视频模型重绘，在 `ad-compose` 以可控文字层完成。

## 统一渲染规格（`render_profile.json`）

`ad-craft/scripts/render_profile.py` 是比例、源生成分辨率、母版容器分辨率和 FPS 的唯一解释层。`出视频规格` 仍表达预算/质量意图，但不能在 route、runner、compose 各自推导一套参数：

- `source_generation` 记录模型实际请求与能力上限；`master_render` 记录合成/交付编码尺寸。
- 源小于母版时明确标 `master_render.requires_upscale=true` 与 `quality_claim=container_upscale_only`；delivery QC 不得把大容器写成“原生 1080p/4K”。
- 后端只支持固定 FPS/时长/比例时，以当前官方能力为准并在 profile 中留证；不允许静默改参。
- 多版位先跑 `placement_adaptation.py`，原生重剪/重做与机械裁切是不同的审计路径。

## 三条硬约束

1. **契约继承**：品牌色/光位/轴线必须从出图继承（`inherit_contract.py` block，上游真值源见上节）。
2. **产品形态继承**：绑定 `PROD_*` 的产品镜，视频 prompt 必须重携产品身份锁定句/资产引用（`inherit_contract.py` block）。
3. **不混后端当默认**：路由按能力选 primary/fallback 并落 `video_model_routes.json`，不是随意混用。
