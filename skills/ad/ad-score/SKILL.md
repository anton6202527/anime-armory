---
name: ad-score
description: 拍广告 投放前 pre-spend 创意诊断——按 campaign_objective 使用不同权重检查钩子、品牌/产品、卖点、CTA、时长和广告法。分数仅作 revise/reject 建议与回流，不把启发式总分伪装成 ROI 硬闸；广告法 block 仍是唯一机器硬地板。Use when asked 广告评分, 投放前评分, 广告分镜打分, 出图前体检, ad-score. Triggers 广告评分, 投放前评分, 广告体检, 钩子评分, CTA评分, ad-score.
---

# ad-score — 拍广告 投放前 pre-spend 创意诊断

`ad-score` 是出图前的**诊断与返工建议**。启发式分数不能证明 ROI，也不应仅凭阈值阻断付费生产；广告法 block 才是机器硬地板。品牌认知、考虑种草、转化行动、全链路分别使用目标化权重。

`ad-score` 纯标准库实现，评分口径只面向广告片。

## 偏好（私有 · 用户选择，不写死在本 skill）

可选项不写死在源码。按 `../skills/ad/ad-craft/references/选择点与偏好.md` 读项目值、全局默认，再对普通可逆项采用推荐值写回并继续；合规/权利口径仍确认，付费动作绑定一次阶段预算包。评分阈值默认 `--threshold 80`（不传则建议性不阻断）。

## 混合模型：确定性 prescore + LLM 语义分 → 阈值三档 + 回流

**先机检（确定性），后 LLM。** 在任何出图/出视频烧积分前跑：

```bash
python3 skills/ad/ad-score/scripts/score_pre.py <作品根> --master 30s --threshold 80 \
    --dim 钩子吸引力=72 --dim 卖点清晰度=80 --dim CTA说服力=68 --enqueue
```

### 1) 确定性 prescore（脚本算，不要 LLM）

读 `需求/brief.json`、`脚本/广告法机检报告.json`、`脚本/storyboard.json`、`脚本/镜头时长.json`：

| 维度 | 权重 | 判据 |
|---|---|---|
| `adlaw` 广告法风险 | 0.25 | 机检报告 block/warn 数。**任一 block = 硬地板，强制 reject**（违禁词不可投放，与总分无关）；warn 按条扣分 |
| `brand_exposure` 品牌露出充分度 | 0.20 | 带产品(`PROD_*`)/logo/品牌/CTA 的镜数占比；甜点 25%~70%（太少记不住、太多像产品说明书） |
| `first_3s_brand_product` 前3秒品牌/产品 | 0.15 | 信息流前三秒是否已经出现产品、品牌、logo 或 CTA；不能把产品藏到后半段 |
| `duration_fit` 时长贴合 | 0.15 | 实测总时长 vs 主片目标偏差（广告总时长是硬约束，超 25% 记 0） |
| `cta_present` CTA 落镜 | 0.15 | 有无 end card/CTA 镜；brief 强制 CTA 却没落镜 = 0 |
| `hook` 钩子前 3s | 0.10 | 首镜是否钩子镜（痛点/悬念/数字/对比）vs 缓起势空镜（信息流前 3s 易被划走）——半确定性初筛，LLM 维度再细判 |

### 2) LLM 语义分（`--dim 名=分` 传入，由调用方 LLM 判）

确定性维度覆盖不了的语义判断由 LLM 打分后用 `--dim` 喂进来：钩子吸引力、卖点清晰度、CTA 说服力、品牌调性等。总分 = 确定性分 ×0.6 + LLM 维度均分 ×0.4（无 `--dim` 时总分=确定性分）。

### 3) 目标化三档 + 回流（成因映射）

`--threshold` 后：≥阈值=**go**；`[阈值-20, 阈值)`=**revise**；其下=**reject**。revise/reject 都是建议档，只有广告法硬地板 `blocked=true`。低分维度产 `affected_items`：

| 低分维度 | 回流 stage |
|---|---|
| 钩子弱 / CTA 缺失 | `ad-concept`（创意层重设开场/补行动号召） |
| 卖点不清 / 广告法 block / 总时长超标 / 露出分配 / 前3秒未露产品品牌 | `ad-script`（脚本/分镜/finalize 重切） |
| 无任何产品/品牌露出镜 | `ad-image`（补 hero/品牌镜）+ `ad-script` 落镜 |

`--enqueue` 落 `评分/回流清单.json`。退出码：0=评分建议（含 revise/reject）；1=广告法硬地板；2=输入缺失。

## 产物

- `评分/ad_score.json`：总分 + 档位 + 各维度分 + facts + `affected_items`。
- `评分/回流清单.json`（`--enqueue` 时）：按上游 stage 分组的返工清单。

## 何时跑

- **出图前**（`ad-image` 烧积分前）：这是主用途；revise/reject 建议回上游改，但不冒充效果保证。
- 脚本/分镜定稿后想体检一遍「这广告值不值得做下去」时。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 出完片才发现钩子塌/卖点糊 | 出图前先跑 ad-score，pre-spend 拦截 |
| 广告法有 block 还想靠高分放行 | block=硬地板，永远 reject，必须回 ad-script 改写违禁词 |
| 把评分维度阈值写死在脚本 | 阈值是 `--threshold` 参数 / `_设置.md` 选择点，不 hardcode |
| 想复用其它评分脚本 | ad-score 自包含，逻辑按广告口径维护 |
