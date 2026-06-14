# 生视频模型/渠道 + 模型路由（ad-video · 本线自持）

`生视频模型` + `生视频渠道` 读项目 `_设置.md`；新广告立项首跑必须给菜单选一次。模型只作默认/普通镜兜底建议，渠道决定实际调用入口。`视频模型路由=自动按镜头路由` 时按镜头**能力**选 primary/fallback；否则固定 `生视频模型`。旧 `生视频AI` 兼容读取。模型/渠道能力随版本变，正文写能力不绑版本。

## 路由是工程化产物（不是 prose 表）

`scripts/route.py` 读 `脚本/storyboard.json` 的镜型，**按能力分类**（不对后端品牌字串分支），落
`出视频/分镜/prompt/video_model_routes.json`，逐镜 `{primary, fallback, reason, capability, max_clip_seconds, findings}`。换厂只改 `route.py` 的 `BACKEND_PROFILES` 能力档，不改判型逻辑。下表是能力档的人读镜像，与 `BACKEND_PROFILES` 同步。

## 镜头类型 → 能力 → 路由

| 镜头类型 | 需要的能力 | primary（能力优先） | fallback | 为什么 |
|---|---|---|---|---|
| 产品展示 / hero 环绕 / 绑定 `PROD_*` | 主体一致性强 | Seedance / 可灵主体库 | 即梦 | 包装/logo 不能抖花，要稳 |
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
| 可灵 Kling | ≈ 10s |
| Veo | ≈ 8s |

广告镜短，一般够；能一镜到底就别切碎。超 primary 上限就换更长后端（Seedance）或拆镜/缩时长。

## 上游视觉契约单一真值源（契约继承用）

`scripts/inherit_contract.py` 比对的上游契约（品牌色 HEX / 光位锚 / 轴线）真值源：

1. **首选** `出图/分镜/prompt/00_总览.md` 的「视觉一致性契约」节（出图细化后烤进首帧的最终值）；
2. **回退** `脚本/storyboard.json`.visual_contract（出图总览尚未生成时的脚本种子）。

与 `ad-video/SKILL.md` 同口径，亦同 n2d 的 image→video diff。品牌色按 HEX 归一比对（`#E60012` 与 `rgb(230,0,18)` 视为同色，不误判漂移）。

## 出视频规格（`出视频规格`）

- 预算充足：1080p30fps，关键镜多跑挑稳。
- 预算一般：720p24–30fps（默认）。
- 预算不够：720p24fps 一条过。

## 三条硬约束

1. **契约继承**：品牌色/光位/轴线必须从出图继承（`inherit_contract.py` block，上游真值源见上节）。
2. **产品形态继承**：绑定 `PROD_*` 的产品镜，视频 prompt 必须重携产品身份锁定句/资产引用（`inherit_contract.py` block）。
3. **不混后端当默认**：路由按能力选 primary/fallback 并落 `video_model_routes.json`，不是随意混用。
