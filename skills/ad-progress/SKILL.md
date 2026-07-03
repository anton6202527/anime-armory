---
name: ad-progress
description: 拍广告(ad)「当前进度仪表盘 + 下一步建议」（只读 QA，不生产内容）。扫描 `创作区/拍广告/` 下广告项目的 `_进度.md` 阶段进度表和交付版本矩阵，汇总每条广告的完成度、当前前沿、brief 缺口、交付件状态，并给出下一步该跑哪个 ad skill。不改任何文件。Use when the user wants an ad project status overview or asks "what's next" for a 拍广告 project. Triggers ad-progress, 广告进度, 拍广告进度, TVC进度, 交付进度, 下一步, 下一步做什么, 查进度, 看进度.
---

# ad-progress — 拍广告进度仪表盘 + 下一步建议

你是广告线的**只读进度向导**。扫描广告项目 `_进度.md`，报告阶段完成度、brief 缺口、交付版本矩阵和下一步建议。**不修改任何文件，不出图、不出视频、不合成**。

**范围**：只管 `创作区/拍广告/`（ad）。

## 输入 / 输出 / 读写边界

- **输入**：`创作区/拍广告/<项目>/_进度.md` 和可选 `需求/brief.json`。
- **输出**：终端摘要：阶段完成度、交付件完成度、brief gate 提示、当前前沿、后续待办。
- **读写边界**：严格只读；不写 `_进度.md`、不写生产数据、不启动花钱或不可逆阶段。
- **契约关系**：解析只引用广告线自己的 `ad-craft/scripts/contract.py` 和 `ad/_lib/progress_md.py`；不引用其它系列实现。

## 怎么跑

```bash
python3 skills/ad-progress/scan.py                    # 扫描 创作区/拍广告/ 下所有广告项目
python3 skills/ad-progress/scan.py <广告项目根>          # 只看指定广告
python3 skills/ad-progress/scan.py --root <仓库根>      # 从其它目录调用时指定仓库根
```

- 用户没指定某个广告项目 → 扫全部。
- 用户给了 `创作区/拍广告/<项目>/` 但没说动作 → 跑本 skill。

## 输出怎么转述

优先转述当前前沿和阻断。若下一步是 `ad-image`、`ad-video`、`ad-compose`，提醒这是高风险阶段：会花钱/不可逆，进入前要确认后端、交付规格，并先过广告线 gate；brief 的必填项缺失时，先回 `ad-concept` 访谈补齐。

## 不做什么

- 不改 `_进度.md`。
- 不替用户决定花钱出图/出视频/合成。
- 不碰其它生产线项目。
