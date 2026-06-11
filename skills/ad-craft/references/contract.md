# ad-* 机器契约（人读版）

机器字段以 `scripts/contract.py` 为准。拍广告线**自包含**，不复用 n2d-*/mv-*。

## 作品根（不拆集）

```text
拍广告/<项目名>/
├── _设置.md / _meta.json / _进度.md
├── 需求/
│   ├── brief.md            客户需求（人读）
│   └── brief.json          客户需求（结构化：品牌/产品/USP/受众/调性/强制项/交付规格）
├── 创意/
│   ├── concept.md          big idea / 主张 / mood&reference / KV方向
│   └── 创意脚本.md          creative treatment（故事线/节奏）
├── 脚本/
│   ├── 广告脚本.md          画面+台词+VO+秒级时间轴（0-3s/3-8s…）
│   ├── voiceover.txt        VO/台词逐句（驱动配音）
│   ├── 时间轴.json          段落级时间分配
│   ├── storyboard.json      分镜（实测时长驱动）+ visual_contract 种子
│   ├── 镜头时长.json
│   ├── 字幕_zh.srt / 字幕_en.srt
│   └── 广告法机检报告.json   ad_law_check.py 产物（命中=block）
├── 设定库/                  global_style + 角色卡 + 场景卡 + 产品卡 + voicemap.json
├── 配音/                    line_NN.wav + vo.wav + 时长清单.json + _voicecache/
├── 出图/共享/ 出图/分镜/     prompt/ + 图片/（三层定妆库 + 逐镜首尾帧）
├── 出视频/分镜/             prompt/ + 视频/（每 Clip MP4 + video_model_routes.json）
├── 合成/                    _work/ + 成片_主片.mp4 + cutdown/ + 多比例/ + 水印/
├── 合规/                    ai_usage.json + AI使用说明.md（二期补 compliance_manifest.json）
└── 成片_主片.mp4
```

## 阶段表

| key | 阶段 | owner | gate |
|---|---|---|---|
| `brief` | 客户需求立项 | `ad` | brief.json |
| `concept` | 创意策划 | `ad-concept` | concept.md + 创意脚本 |
| `script` | 广告脚本+VO+时间轴 | `ad-script` | 广告法机检 + voiceover.txt |
| `voice` | VO配音 | `ad-voice` | 时长清单.json |
| `storyboard` | 分镜（实测时长驱动） | `ad-script` | storyboard.json + 镜头时长 |
| `image` | 定妆库+出图 | `ad-image` | visual identity + 首尾帧（高风险闸门）|
| `video` | 图生视频 | `ad-video` | 契约继承 + clip videos（高风险闸门）|
| `compose` | 剪辑包装+交付 | `ad-compose` | 成片 + cutdown + 交付规格（高风险闸门）|
| `review` | 质检自审 | `ad-review` | machine + human review（**二期**）|
| `handoff` | AI披露/交付 | `ad-craft/scripts/ai_usage.py` | AI usage disclosure |

> **不拆集**：一条主片是整体；`_进度.md` 用「阶段进度表」而非逐集矩阵。
> **音频先行**：VO 实测时长驱动镜头时长，`script` 跑两遍（脚本 pass → 配音后 `storyboard` pass），与 n2d「配音先行」同构。广告常是「音乐床 + VO」混合驱动，音乐床作为节奏锚一并记录。

## cutdown / 多版本轴（不拆集的并行轴）

一条主片派生多个**交付件 deliverable**，登记在 `_进度.md` 的「交付版本矩阵」：
- `kind`：`master`（主片）/ `cutdown`（多时长 30→15→6s）/ `reframe`（多比例 16:9/9:16/1:1）/ `ab_variant`（A/B）。
- 字段：`deliverable_id / label / duration / aspect / kind / spec / status / path`。
- `ad-compose` 据此重剪 cutdown、reframe 比例、按 `交付规格` 归一响度（LUFS）和安全框。

## 关键选择点（详见 `_偏好约定.md` 拍广告节）

`广告类型` `创意路线` `基础视觉风格` `主片时长` `交付比例` `cutdown版本` `生图AI` `一致性增强` `生视频AI` `视频模型路由` `出视频规格` `视频分辨率` `配音后端` `音乐来源` `品牌包装模板` `字幕语言` `AI视觉使用披露` `水印-AI合规标识` `水印-品牌账号` `广告法地区` `交付规格` `生成粒度` `目标平台` `发行地区`。

合规/不可逆/花钱多的点（`水印-AI合规标识`、`广告法地区`、`音乐来源`）即便记录过每次仍确认。
