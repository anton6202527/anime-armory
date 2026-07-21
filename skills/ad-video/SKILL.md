---
name: ad-video
description: 拍广告 第6阶段·图生视频 — 把 ad-image 首帧按 storyboard 逐镜图生视频；保留品牌/产品/合规完整合同，并用本线 prompt compiler 编译后端感知的精简提交 prompt；按镜头类型路由、机检契约继承、首尾双帧接力。Use when asked 广告出视频/图生视频/视频prompt/prompt compiler/运镜/模型路由/契约继承 for a 拍广告 project. Triggers 广告出视频, 图生视频, 视频prompt, prompt compiler, 运镜, 模型路由, 契约继承, image2video, ad-video.
---

# ad-video — 拍广告 · 图生视频

把 `ad-image` 的首帧 PNG 按 `storyboard.json` 逐镜**图生视频**：写 Clip 视频 prompt（运镜+表演+节奏），机检视觉契约继承，按镜头类型、`asset_registry.json` 和平台规格路由后端，首尾双帧接力；Clip 生成后跑 `video_qc.py` 做出视频落档 QC，未过不得进入 `ad-compose`。

用通用生视频模型/渠道（Seedance/Veo/Kling/即梦/可灵/manual 等）。

## 偏好（私有）

按 `../skills/ad-craft/references/选择点与偏好.md` 读 `<作品根>/_设置.md`。涉及：`生视频模型`（固定/兜底）、`生视频渠道`（固定/调用入口偏好）、`视频模型路由`、`出视频规格`、`视频分辨率`、`交付比例`。出视频是**花钱/高风险**阶段，正式跑前确认规格；若未显式固定后端，先按模型路由、CLI/API 探测与账号约束决定入口，探测不到可执行后端时再问用户选渠道或 `manual`。写完视频 prompt 并跑完契约继承机检后、正式生成前跑 `gate.py --stage video`；正式 runner 同时自动跑 `stage_acceptance.py --stage image`，只有全部 image job、真实输出/参考输入 provenance 与 full product_qc 通过才花视频额度。

## 上游契约单一真值源

品牌色 HEX / 光位锚 / 轴线在**出图阶段**烤进首帧像素，所以契约继承的上游真值源是：

1. **首选** `出图/分镜/prompt/00_总览.md` 的「视觉一致性契约」节（出图细化后的最终值）；
2. **回退** `脚本/storyboard.json`.visual_contract（出图总览尚未生成时的脚本种子）。

`inherit_contract.py` 与 `references/platforms.md` 都以此口径为准。

## 工作流

1. **模型路由**（先于写 prompt）：
   ```bash
   python3 skills/ad-video/scripts/route.py "<作品根>"   # 写 出视频/分镜/prompt/video_model_routes.json
   ```
   按镜型**能力**（不是后端品牌字串）路由 primary/fallback + 单 Clip 时长上限校验（见 `references/platforms.md`）：
   - 产品展示/环绕 hero、绑定 `PROD_*` → 主体一致性强（Seedance/可灵主体库）
   - 情绪/人物特写 → 电影感后端（Veo/可灵）
   - demo 实拍质感/手持 → 真实运动后端
   - 空镜/痛点/普通镜 → 通用后端（`_设置.md` 的 `生视频模型`/`生视频渠道`，旧 `生视频AI` 兼容）
   - end card/包装定格 → 静帧或极慢运镜
   - 镜头时长超 primary 后端单 Clip 上限 = 🔴 block（改用更长后端或拆镜）。
   - 语义产品/App/UI/片尾镜缺 `PROD_*` = 🔴 block；引用的 `PROD_*`/`BRAND_*` 若不在 `设定库/asset_registry.json` 或 `出图/共享/asset_registry.json` = warn。
   - 只消费 `ad-craft/platform_pack.py` 的单一规格源（不在 route 内复制清单），优先落 `placement_specs` + 来源/采集日期/安全区证据；只有平台名时可做母版但不能发布，未知或无出处自定义 placement 直接 block。
   - **三轴增量字段**，逐镜写进 `video_model_routes.json`：
     - **`quality_tier` 质量档（成本×质量）**：产品 hero/代言人特写/end card 品牌定格 → `high`（值后端 pro 档把脸·包装·logo·品牌色钉稳）；空镜/痛点/普通镜 → `fast`（量产省成本）；后端无 fast/pro 档 → `n/a`。只表达意图，落档侧把 `high→pro`、`fast→fast` 解析成实际档位，不写死 model_version。
     - **`motion_reference` 视频运动参考**：产品环绕 hero/demo 连续动作镜 + primary 支持 `reference_video_motion`（Seedance/可灵）时 `applicable=true`，提示把同段前一条已通过 clip 作运动/风格参考喂进去锁运镜节奏（与图身份锁正交）。
     - **`summary.multishot_groups` 多镜单次生成候选（advisory）**：连续 demo 步骤/产品多角度 + 支持多镜的后端 → 标候选组，可一次 co-generate 消缝；**只提示不合并**，逐镜仍是独立可重跑交付单元，组大小受单次输出时长上限封顶。
2. **逐 Clip 完整合同 + 编译提交 prompt**：运行 `python3 skills/ad-video/scripts/plan_prompts.py "<作品根>"` 写 `出视频/分镜/prompt/镜头N.md` 与 `video_jobs_manifest.json`。同一 Markdown 分两层：
   - **完整生产合同**：输入帧、路由理由、品牌色/光位/轴线、产品资产 ID、精确 CTA/slogan/法律声明、安全区、负向和合规信息；供 gate、人工复核和溯源，必须严格完整。
   - **后端编译提交 prompt**：`skills/ad/_lib/ad_video_prompt_compiler.py` 按 primary 后端只编译产品主动作、运镜、明确的环境响应、结尾落幅、产品保持与文字处理；renderer 只提交此块。每条主运镜补速度、方向与落幅，禁止把整份合同、路由理由、资产路径或法规说明拼给模型。
   - 精确 CTA、slogan、价格、法律声明和 UI 文案由 `ad-compose` 可控叠加；视频模型只保持首帧已有文字像素，不负责重新拼写。绑定 `PROD_*` 的产品镜仍须在**完整合同**重写身份锁定句/资产引用。
   - runner 拒绝旧版完整合同回退提交；提交前重算 compiler source hash、submit prompt hash 和输入帧 hash，并核对 route primary 与实际模型家族。
3. **契约继承机检（硬闸门）**：
   ```bash
   python3 skills/ad-video/scripts/inherit_contract.py "<作品根>" --json "<作品根>/出视频/分镜/contract_inheritance.json"
   ```
   品牌色/光位锚/轴线未继承、产品镜丢产品身份锁定、缺编译块、编译后端与路由不一致或 compiler lint error = 🔴 block。0 block 才生成。
4. **animatic 预演（传统 PPM 纪律·花钱前最后一道免费签核）**：
   ```bash
   python3 skills/ad-video/scripts/animatic.py "<作品根>"
   ```
   用首帧 PNG × 实测镜头时长 + VO 拼 `合成/animatic.mp4`（+ `生产数据/ad_animatic_manifest.json`，逐帧 SHA + VO 时长对账）。节奏塌/镜序错/VO 不贴，在预演里改是免费的，生完视频再改是重烧。缺首帧/缺实测时长直接 block（预演不能拿空画面凑）；gate video 以 advisory 侧车提示，首帧或时长变更后预演过期。
5. **图生视频**：调生视频 CLI，标 `need_end_frame` 的用首+尾双帧引导焊接点。**付费渲染资金安全**（签核例外走 `scripts/render_dreamina.py` 时）：提交成功即**先落盘** `submit_id` 再下载，下载失败重跑凭已登记 `submit_id` 免费收集（`--submit-only`/`--collect-only` 两段式或默认同步路径均如此），绝不二次付费；job 账本原子写；下载/查询有限重试+退避、付费提交永不自动重试；`--max-credits N` 预算封顶到顶即停。
6. **出视频落档 QC（post-video gate）**：
   ```bash
   python3 skills/ad-video/scripts/video_qc.py "<作品根>"
   ```
   用 ffprobe 实测视频流/分辨率/时长，用 ffmpeg 抽 start/mid/end 三帧并生成 contact sheet；对输入首帧、镜内产品漂移、相邻镜头真实尾/首帧做启发式比较。抽帧失败会 block“无法验收”，视觉 dHash 只 WARN 交人工。报告须晚于 clips 且 full precision 才能进 compose（或显式人工签收）。
7. 回写 `_进度.md` 视频 ✅：`python3 skills/ad-craft/scripts/progress_set.py set-stage "<作品根>" video --status ✅ --artifact 出视频/分镜/视频`，提示 `ad-compose`。

## 广告专有强化

- **品牌色 + 产品形态继承是硬闸门**：`inherit_contract.py` 把品牌色/光位/轴线漂移、产品镜丢产品身份锁定句拦在生成前。
- **产品镜稳定优先**：产品 hero 镜路由到主体一致性最强的后端，避免 image2video 把包装/logo 抖花。
- **资产注册表驱动**：`route.py` 消费 `asset_registry.json`，让 App/UI/end card 的 `PROD_*`、`BRAND_*` 和平台安全区一起进入视频路由产物。
- **生成后也要验收**：`inherit_contract.py` 只管生成前 prompt 继承；`video_qc.py` 负责生成后的 Clip 文件、产品锁、文字可读、安全区、接缝声明，外加**批内混帧率/混分辨率**（`batch_fps_mix`/`batch_resolution_mix`·warn——合成强制统一参数会静默掩盖来源差异）与**同场景相邻镜色跳**（`seam_color_jump`·平均色距>0.12 warn，已声明转场降 info——dHash 只抓灰度结构，调色/白平衡跳变靠色距抓），不允许坏 Clip 进入剪辑。
- **运镜服务节奏**：广告节奏紧，一镜一个主运镜，动作峰值对 VO/音乐床节奏点（`ad-script` 时间轴标）。产品 hero/demo/end card 的可用运镜见 `skills/ad/references/运镜/manifest.json`，默认读本地五帧 contact sheet；只有需要检查运动节奏/轨迹时才运行 `python3 skills/ad/scripts/camera_reference.py fetch <运镜ID或名称>` 按 SHA-256 下载远端动画。断网只退回 manifest + contact sheet，不阻断广告 prompt。
- **多比例**：按主比例出视频，其它比例 `ad-compose` reframe；运镜别让主体/产品冲出 action-safe。

## 测试

```bash
cd skills/ad-video/scripts && python3 -m pytest
```

## 常见错误

| 错误 | 纠正 |
|---|---|
| 视频 prompt 丢了品牌色/光位 | `inherit_contract.py` block；逐镜继承上游契约（出图 00_总览 → storyboard 回退） |
| 品牌色 HEX 与 rgb()/别名写法不同被误判漂移 | `inherit_contract.py` 归一化 HEX 比对，同色不同写法不 block |
| 产品镜 prompt 丢了产品身份锁定句 | `inherit_contract.py` 产品形态 block；重写 `PROD_xx`/「同一包装/同一 logo/同一品牌色」 |
| 把完整广告合同直接提交给模型 | 只提交 `后端编译提交 prompt` 代码块；完整合同留给 gate/复核/溯源 |
| 让视频模型重新生成 CTA/价格/法律声明 | 首帧已有文字只做像素保持；精确文字在 `ad-compose` 可控叠加 |
| 产品镜用普通后端抖花包装 | `route.py` 按能力把产品镜路由主体一致后端 + 首尾双帧 |
| 生成了 MP4 就直接合成 | 先跑 `video_qc.py`；compose gate 缺 `出视频/分镜/video_qc.json` 或 block 会拦 |
| 镜头比后端单 Clip 上限还长 | `route.py` 时长上限 block；换更长后端（Seedance≤15s）或拆镜 |
| 项目内混用视频后端当默认 | 路由按能力选 primary/fallback 落 `video_model_routes.json`，不是随意混 |
| 运镜让产品/主体冲出安全框 | 留 action-safe 余量，多比例 reframe 才不裁掉主体 |
