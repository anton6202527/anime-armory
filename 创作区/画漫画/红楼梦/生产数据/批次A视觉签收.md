# 批次 A 视觉签收 — 《红楼梦》第1话

> 执行时间：2026-07-12。模型/渠道：GPT Image 2 / Codex CLI。范围：1 张风格锚 + 6 张角色 front。自动技术验收已完成；创意选角仍待用户签收。

## 执行摘要

- 目标：7；成功：7；失败：0。
- 每项实际尝试：1；技术重试：0。
- 全部为有效 PNG；均无对白、空白气泡、标题、水印或可读乱码。
- 六名角色均为单人正面全身，头顶、双手、鞋/脚完整入画；角色之间可辨。
- 六名角色生成时均把 `STYLE_HLM_GONGBI_DREAM_V1` 作为真实 `style_only` 图片附件，并记录同一 SHA-256：`690e5722e92f6e0b8524c5ac52388e49b945434dbe17a52894abb782db805f34`。
- [六人 casting contact sheet](comic_identity_views_第1话_contact_sheet.jpg)

## 逐项检查

| 资产 | 尺寸 | 自动/视觉判定 | 观察 |
|---|---:|---|---|
| `STYLE_HLM_GONGBI_DREAM_V1` | 1024×1536 | PASS | 工笔细线、低饱和矿物淡彩、木石绢材质及现实→墨境边缘清楚；无影视仿图。 |
| `CHAR_JIANGZHU front` | 916×1717 | PASS_WITH_NOTE | 月白/灰紫/淡青成立，脸手脚完整；与风格锚匿名女性存在审美家族相似，进入后续多视图前需留意风格参考是否越界成脸型参考。 |
| `CHAR_SHENYING front` | 864×1821 | REVIEW | 朱砂/暖玉体系与少年全身完整；秀润感较强、男性可读性偏中性，是否保留由选角签收决定。 |
| `CHAR_YINGLIAN_CHILD front` | 1024×1536 | PASS | 幼儿比例、双发束、小痣、藕荷/嫩绿明确，不是成人缩小版。 |
| `CHAR_ZHEN_SHIYIN front` | 864×1821 | PASS | 中年清癯、短须、竹青家居色成立，完整清楚。 |
| `CHAR_MONK front` | 864×1821 | REVIEW | 宽额、剃发、旧赭宽袖成立；图中托玉属于剧情临时物，不应固化为身份。registry 与 Skill 已拆分 `transient_props/staging_defaults`，后续视图会明确移除；若需要“无玉纯净 front”，应另行批准一次创意修订，不冒充技术重试。 |
| `CHAR_DAOIST front` | 864×1821 | PASS | 瘦长、道髻、青灰墨黑、清醒目光成立，完整清楚。 |

## 当前闸门

- identity report：`missing_ref_count=15`，即场景、道具、特效锚尚未生产。
- 六名角色各缺 `three_quarter / side / back / face`，合计 24 张。
- 六名角色 registry 均为 `status=partial`，每个角色 `view_readiness=1 ready / 4 missing`；资产库不会把 front、计划路径和 style-only 依赖合并虚报为六张现成参考。
- `image_preflight` 仍为 `block=2 / warn=0`，这是正确状态：批次 A 不能被误认为已经允许正式剧情格出图。
- 本批只允许技术失败重试；没有把审美意见伪装成技术失败自动多抽，因此实际只消耗 7 次成功生成。
