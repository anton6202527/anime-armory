---
name: song-progress
description: 写歌(song)「当前进度仪表盘 + 下一步建议」（只读 QA，不生产内容）。扫描 `创作区/写歌/` 下歌曲项目的 `_进度.md` 阶段表，汇总每首歌的完成度、当前前沿、后续待办，并给出下一步该跑哪个 song skill。不改任何文件。Use when the user wants a song project status overview or asks "what's next" for a 写歌 project. Triggers song-progress, 写歌进度, 歌曲进度, 作曲进度, 到哪了, 下一步, 下一步做什么, 查进度, 看进度.
---

# song-progress — 写歌进度仪表盘 + 下一步建议

你是写歌线的**只读进度向导**。只做三件事：扫描歌曲项目 `_进度.md`，报告阶段完成度和生产前沿，给出下一步该跑哪个 `song-*` skill。**不修改任何文件，不生成歌词/音频，不启动付费或合规敏感步骤**。

**范围**：只管 `创作区/写歌/`（song）。

## 输入 / 输出 / 读写边界

- **输入**：`创作区/写歌/<曲名>/_进度.md`。
- **输出**：终端摘要：阶段状态、当前前沿、后续待办、下一步建议。
- **读写边界**：严格只读；不写 `_进度.md`、不写生产数据、不登记 take。
- **契约关系**：单项目解析复用 song 线自己的 `song-craft/scripts/progress.py` 和 `song/_lib/progress_md.py`；不引用其它系列实现。

## 怎么跑

```bash
python3 skills/song/song-progress/scan.py                    # 扫描 创作区/写歌/ 下所有歌曲项目
python3 skills/song/song-progress/scan.py <歌曲项目根>         # 只看指定歌曲
python3 skills/song/song-progress/scan.py --root <仓库根>      # 从其它目录调用时指定仓库根
```

- 用户没指定某首歌 → 扫全部。
- 用户给了 `创作区/写歌/<曲名>/` 但没说动作 → 跑本 skill。

## 输出怎么转述

简洁转述“现在卡在哪”和“下一步跑谁”。免费确定性下一步可由外层编排直接 chain；如果下一步是 `song-compose`、`song-cover` 或 `song-review`，带上脚本输出里的费用/授权/质检状态。克隆真人歌手嗓音未授权时必须拒做；实际调用层已有精确绑定且有效的阶段预算包时，不要逐 take 重复询问。

示例：

> 下一步：**仗剑下山 多版生成 / 注册** → `song-compose`。先核对权利/音色授权和当前预算绑定；若阶段预算包仍有效且范围未变可连续执行，否则返回结构化预算停止。

## 不做什么

- 不改 `_进度.md`。
- 不替用户创建、扩大或续期付费授权；已有有效授权的包内调用由实际 runner 按合同执行。
- 不碰其它生产线项目。
