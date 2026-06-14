# 产品定妆一致性 checklist（ad-image · 广告线最严一致性）

广告里**产品是主角**，包装/logo/品牌色一漂，整片报废。产品定妆当最严格的"角色"管。

## 产品定妆库（`出图/共享/`）必产

- `定妆_<产品>.png`：包装**正/侧/背**三视图 + 关键细节特写（logo、材质、按钮、瓶口…）。
- ≥1024px、清晰、正打光、纯净背景，作为下游所有产品镜的参考图组。
- 产品卡 `设定库/产品卡_<产品>.md` 写死**禁改清单**（见下）。

## 禁改清单（写进产品卡 + 逐镜 prompt 负向）

| 维度 | 锁什么 |
|---|---|
| 品牌色 | 主色 HEX（如 `#E60012`）+ 辅色；环境光不得染偏主色 |
| logo | 字形/比例/方向/位置/最小留白；不得变形、镜像、遮挡、改色 |
| 包装文字 | 品名/规格/关键文案不得错字、乱码、缺笔（AI 生图常崩文字→关键文字镜建议后期合成真 logo/包装贴图）|
| 形态比例 | 瓶身/盒体长宽比、材质（哑光/高光/透明）、质感 |
| 数量/角度 | 同一镜产品数量、朝向符合分镜；hero shot 用定妆正面角度 |

## 资产引用注册（逐镜绑定）

产品镜的 `storyboard.json` 必带 `assets.PROD_xx: true`，逐镜 prompt 写：
- `资产引用：PROD_main`（绑定产品定妆参考组）
- **身份锁定句**：「与产品参考图①同一款包装、同一 logo、同一品牌色」（多参考/编辑类后端最敏感）
- **负向**：「不要改包装文字、不要变形 logo、不要偏色」

## logo / 文字的现实约束

AI 生图对**小文字 / logo 字形**仍不稳。策略：
- 产品 hero / logo 特写镜：出图先占位，**关键 logo/包装文字镜在 `ad-compose` 用真 logo/包装贴图合成或后期叠加**（最稳）。
- 中远景产品镜：靠产品定妆参考 + 身份锁定句锁形态与色。

## 机检（已落地 · `scripts/product_qc.py`）

二期设想的产品一致性机检**已实现并前移到出图落档**，是 gate spend 的硬闸（不再只是散文/人审）。出完图、还没继续出视频时跑：

```bash
python3 skills/ad-image/scripts/product_qc.py "<作品根>/出图/分镜" [--strict]
```

落档 `出图/分镜/product_qc.json`（`summary.block>0` → 退出非零，`ad-craft/gate.py` 据此挡 spend）。四项检：

| 检项 | severity 语义 | 实现 |
|---|---|---|
| **prompt-lint**（绝不文生图产品） | 产品镜缺 参考图块 / 身份锁定句 / 负向(不要改包装文字·不要变形logo) → **block**（无 Pillow 也跑） | 解析 `prompt/镜头N.md` |
| **品牌色 ΔE** | 产品区域主色 vs `品牌色` HEX，CIE76 ΔE 超阈 → **block**，临界 → warn；无区域取整图主色降级 warn | Pillow+numpy；缺则 info 降级 |
| **product dHash 离群** | 产品镜组内最近邻 Hamming 距离离群 → 漂移 warn/block（组 <3 张降 info） | Pillow |
| **logo 模板匹配** | 注册 `出图/共享/定妆库/产品/logo.png` 时 NCC 粗匹配；缺失/形变 → flag；无模板干净跳过 | Pillow+numpy |

缺 Pillow/numpy 时优雅降级（只跑 prompt-lint，报告标 `degraded`，不臆造通过）。测试：`cd skills/ad-image/scripts && python3 -m pytest test_product_qc.py`。logo/小文字仍建议关键镜用真 logo 贴图后期合成（见上节）——机检兜底，不替代该铁律。
