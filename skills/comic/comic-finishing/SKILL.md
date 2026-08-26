---
name: comic-finishing
description: 漫画传统原稿收尾计划阶段。Use when planning manga lineart, ink, blacks, screentone, grayscale/value hierarchy, action/focus/speed lines, manga symbols, drawn SFX treatment, finish layers, or traditional manuscript aesthetics before comic-image. Triggers 原稿收尾, 传统收尾, 墨线, 黑场, 网点, 效果线, 集中线, 速度线, 漫符, drawn SFX, screentone, comic-finishing.
---

# comic-finishing — 原稿收尾计划

把传统漫画的完成稿手法结构化：草稿 → 铅笔 → 清线 → 墨线/黑场 → 网点/灰阶 → 效果线/漫符 → 拟声词融入画面 → 最终检查。它发生在 `comic-layout` 之后、`comic-image` 出图包之前，让逐格 prompt 能继承传统原稿审美，而不是只写“漫画风”。

## 输入

- `_设置.md`：基础视觉风格、出图稿层、网点策略、效果线策略。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/name_board.json`：必需且已签收的 schema v2。
- `排版/第N话/layout.json`：必需、validator 通过且已签收的 schema v2；其中 panel 覆盖必须与脚本/name 完全同序。

## 输出

- `出图/第N话/finishing/finishing_plan.json`：schema 见 `references/finishing_schema.md`。
- `出图/第N话/finishing/finishing_plan.md`：人工可读收尾计划。
- `_进度.md`：只有所有输入存在、SHA 当前、panel/page coverage 完整且 finishing validator 通过后，才把 `原稿收尾` 标为 `✅`。

## 怎么跑

```bash
python3 skills/comic/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话
```

出图或恢复批跑前只读检查现有计划是否仍新鲜：

```bash
python3 skills/comic/comic-finishing/scripts/build_finishing_plan.py "创作区/画漫画/作品名" --chapter 第1话 --check
```

脚本不再对缺输入返回空计划：缺 panel script/name/layout、空 panels、覆盖或顺序不同、审批无效、任一上游 SHA 改变都会返回非零；失败不会写 `✅`。

## 工作流

1. 验证分格、已签收 name/layout 及其内容 SHA；先证明输入完整和当前，再生成计划。
2. 确定项目 `delivery_mode`、有序 `layer_contract`，并为每个 page/segment 建 `page_value_plans`。
3. 逐格生成 `layer_items`、墨线/黑场、`tone_items`、价值、效果线和 `sfx_items`；每个 SFX 都绑定源内容引用。
4. 动作/冲击/揭示格加 `effects_plan`，但必须保留脸、手、道具和接触点可读。
5. 黑白/页漫优先显式 `tone_plan`；彩色条漫也要有 `value_plan`，避免只靠色相堆信息。
6. 拟声词只在需要时作为画面节奏元素处理；正文对白仍后期嵌字。
7. validator 确认 plan 唯一、同序覆盖所有 panel/page 后写产物和 `✅`；`comic-image` 再把计划注入逐格 job。
8. 优先保存真实可编辑母版（ORA/PSD/KRA 或后端等价容器）。只有扁平输出时才走 flat fallback，并让 `comic-image` 保存不可变 raw、原子 active master、色彩/位深/ICC/alpha 和 derivative chain。

局部修手、改表情、修道具或服装时，不整格覆盖也不手改 master。先准备 SHA-bound 修复事务，把外部编辑器/任意 provider 的全尺寸候选写到脚本给出的 staging 路径，再提交：

```bash
python3 skills/comic/comic-finishing/scripts/local_repair_transaction.py "$ROOT" prepare \
  --chapter 第1话 --panel P003 --mask repair_mask.png --bbox 420,180,360,420 \
  --edit-prompt "只修复右手握刀关系，保持脸、服装、背景与光位不变"

python3 skills/comic/comic-finishing/scripts/local_repair_transaction.py "$ROOT" commit \
  生产数据/repair_staging/第1话/P003/<transaction_id>/repair_transaction.json
```

commit 只允许 mask 内像素改变；当前 master/panel、mask、执行合同任一 SHA 变化都会失效。成功后仍回到当前像素 post-QC 与结构化逐轴 B14 签收，不能沿用旧验收。
命令行里的 `--mask`、repair receipt 与 `--candidate`：绝对路径原样使用，非绝对路径统一相对作品根 `$ROOT` 解析，不受启动脚本时的 shell cwd 影响。

## 原则

- “墨线/黑场/网点/效果线”是叙事工具，不是装饰滤镜。
- 黑场先决定视觉重心，网点再服务材质、空间深度和情绪。
- 速度线、集中线、冲击闪、漫符必须指向动作路径、视线焦点或情绪读点。
- 传统手法不能破坏一致性底线：脸、眼神目标、身体完整性、场景轴线和关键道具仍是硬约束。

## 不做什么

- 不直接改最终面板图。
- 不替代 `comic-image` 的真实出图。
- 不把对白正文烘焙进画面。
