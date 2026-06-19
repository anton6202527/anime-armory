---
name: ad-score
description: 拍广告 投放前 pre-spend 评分闸门——正式出图/出视频烧积分前，对广告脚本+分镜按「钩子前3秒 / 卖点清晰度 / CTA 强度 / 品牌露出充分度 / 广告法风险 / 时长贴合」打分体检，拦平庸 ROI。混合模型：确定性 prescore（读 ad-script 已有产物，广告法 block=硬地板）+ LLM 语义分 → 阈值三档（go/revise/reject）+ 低分维度按成因回流 ad-concept、ad-script、ad-image。ad 线自包含，不复用 n2d-* 与 mv-*。Use when asked 广告评分, 投放前评分, 广告分镜打分, 这广告行不行, 出图前体检, ad-score for a 拍广告 project. Triggers 广告评分, 投放前评分, 广告体检, 广告分镜打分, 钩子评分, 卖点评分, CTA评分, 广告能不能行, ad-score.
---

# ad-score — 拍广告 投放前 pre-spend 评分闸门

广告**一条主片就是全部产出**，正式出图/出视频一旦开跑即烧积分。`ad-score` 是出图前的**质量闸门**：用 `ad-script`/`ad-voice` 已产出的确定性产物先拦平庸 ROI（钩子塌、卖点糊、CTA 弱、品牌露出不足、广告法 block、总时长超标），比出完片再靠 `ad-review` 发现省得多。

与 n2d-score、mv-score、novel-score、song-score 同构（每条线都有 pre-spend 评分），但 **ad 线自包含**：纯标准库，不 import 任何别线脚本。

## 偏好（私有 · 用户选择，不写死在本 skill）

可选项不写死在源码。按 `../skills/ad-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`，缺则全局默认预填并告知一句，再缺则首次问一次→写回→之后沉默沿用（合规/不可逆/花钱多的点每次仍确认）。评分阈值默认 `--threshold 80`（不传则建议性不阻断）。

## 混合模型：确定性 prescore + LLM 语义分 → 阈值三档 + 回流

**先机检（确定性），后 LLM。** 在任何出图/出视频烧积分前跑：

```bash
python3 skills/ad-score/scripts/score_pre.py <作品根> --master 30s --threshold 80 \
    --dim 钩子吸引力=72 --dim 卖点清晰度=80 --dim CTA说服力=68 --enqueue
```

### 1) 确定性 prescore（脚本算，不要 LLM）

读 `需求/brief.json`、`脚本/广告法机检报告.json`、`脚本/storyboard.json`、`脚本/镜头时长.json`：

| 维度 | 权重 | 判据 |
|---|---|---|
| `adlaw` 广告法风险 | 0.30 | 机检报告 block/warn 数。**任一 block = 硬地板，强制 reject**（违禁词不可投放，与总分无关）；warn 按条扣分 |
| `brand_exposure` 品牌露出充分度 | 0.25 | 带产品(`PROD_*`)/logo/品牌/CTA 的镜数占比；甜点 25%~70%（太少记不住、太多像产品说明书） |
| `duration_fit` 时长贴合 | 0.20 | 实测总时长 vs 主片目标偏差（广告总时长是硬约束，超 25% 记 0） |
| `cta_present` CTA 落镜 | 0.15 | 有无 end card/CTA 镜；brief 强制 CTA 却没落镜 = 0 |
| `hook` 钩子前 3s | 0.10 | 首镜是否钩子镜（痛点/悬念/数字/对比）vs 缓起势空镜（信息流前 3s 易被划走）——半确定性初筛，LLM 维度再细判 |

### 2) LLM 语义分（`--dim 名=分` 传入，由调用方 LLM 判）

确定性维度覆盖不了的语义判断由 LLM 打分后用 `--dim` 喂进来：钩子吸引力、卖点清晰度、CTA 说服力、品牌调性等。总分 = 确定性分 ×0.6 + LLM 维度均分 ×0.4（无 `--dim` 时总分=确定性分）。

### 3) 阈值三档 + 回流（成因映射）

`--threshold` 后：≥阈值=**go**（可出图）；`[阈值-20, 阈值)`=**revise**（局部改后重评）；其下 或 **硬地板**=**reject**（退回上游）。低分维度按成因映射回上游 stage 产 `affected_items`：

| 低分维度 | 回流 stage |
|---|---|
| 钩子弱 / CTA 缺失 | `ad-concept`（创意层重设开场/补行动号召） |
| 卖点不清 / 广告法 block / 总时长超标 / 露出分配 | `ad-script`（脚本/分镜/finalize 重切） |
| 无任何产品/品牌露出镜 | `ad-image`（补 hero/品牌镜）+ `ad-script` 落镜 |

`--enqueue` 落 `评分/回流清单.json`（`kind=ad_score_rework_queue`，按 `return_to_stage` 分组，ad 自有格式，不引用别线 batch）。退出码：0=go/建议性；1=reject/低于阈值（pre-spend 拦截）；2=输入缺失。

## 产物

- `评分/ad_score.json`：总分 + 档位 + 各维度分 + facts + `affected_items`。
- `评分/回流清单.json`（`--enqueue` 时）：按上游 stage 分组的返工清单。

## 何时跑

- **出图前**（`ad-image` 烧积分前）：这是主用途，reject 就别出图，回上游改。
- 脚本/分镜定稿后想体检一遍「这广告值不值得做下去」时。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 出完片才发现钩子塌/卖点糊 | 出图前先跑 ad-score，pre-spend 拦截 |
| 广告法有 block 还想靠高分放行 | block=硬地板，永远 reject，必须回 ad-script 改写违禁词 |
| 把评分维度阈值写死在脚本 | 阈值是 `--threshold` 参数 / `_设置.md` 选择点，不 hardcode |
| import n2d-score、mv-score 复用 | ad 线自包含，逻辑在 ad 内重写 |
