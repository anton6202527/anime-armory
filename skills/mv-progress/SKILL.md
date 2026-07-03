---
name: mv-progress
description: 制MV(mv)「当前进度仪表盘 + 下一步建议」（只读 QA，不生产内容）。扫描 `创作区/制MV/` 下 MV 项目的 `_进度.md` 阶段表，汇总每支 MV 的完成度、当前前沿、后续待办，并给出下一步该跑哪个 mv skill。不改任何文件。Use when the user wants an MV project status overview or asks "what's next" for a 制MV project. Triggers mv-progress, MV进度, 制MV进度, 卡点进度, 下一步, 下一步做什么, 查进度, 看进度.
---

# mv-progress — 制MV进度仪表盘 + 下一步建议

你是 MV 线的**只读进度向导**。扫描 MV 项目 `_进度.md`，报告阶段完成度、当前前沿和下一步建议。**不修改任何文件，不出图、不出视频、不合成**。

**范围**：只管 `创作区/制MV/`（mv）。

## 输入 / 输出 / 读写边界

- **输入**：`创作区/制MV/<曲名>/_进度.md`。
- **输出**：终端摘要：阶段状态、当前前沿、后续待办、下一步建议。
- **读写边界**：严格只读；不写 `_进度.md`、不写生产数据、不启动付费视觉阶段。
- **契约关系**：单项目解析复用 mv 线自己的 `mv-craft/scripts/progress.py` 和 `mv/_lib/progress_md.py`；不引用其它系列实现。

## 怎么跑

```bash
python3 skills/mv-progress/scan.py                    # 扫描 创作区/制MV/ 下所有 MV 项目
python3 skills/mv-progress/scan.py <MV项目根>           # 只看指定 MV
python3 skills/mv-progress/scan.py --root <仓库根>      # 从其它目录调用时指定仓库根
```

- 用户没指定某支 MV → 扫全部。
- 用户给了 `创作区/制MV/<曲名>/` 但没说动作 → 跑本 skill。

## 输出怎么转述

按脚本输出给一个明确前沿。若下一步是 `mv-image`、`mv-video`、`mv-compose`，提醒这是花钱/不可逆/耗时步骤，开跑前必须确认后端、规格和画幅；后配歌曲路线若还没有最终音频，不得推进正式卡点之后的产物。

## 不做什么

- 不改 `_进度.md`。
- 不替用户决定花钱出图/出视频。
- 不碰其它生产线项目。
