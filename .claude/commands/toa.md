---
description: 把当前分支同步推送到 anime-armory 仓库（toa = to armory）
argument-hint: "[force]"
allowed-tools: Bash(git remote:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git push:*), Bash(git fetch:*), Bash(git config:*)
---

把**当前分支**的代码同步推送到 GitHub 仓库 `https://github.com/anton6202527/anime-armory`（与 `origin` = anime-arsenal 不同的另一个仓库）。

参数 `$1`：留空 = 普通推送；传 `force` = 用 `--force-with-lease` 强推（两仓库历史分叉时用，会覆盖 armory 上的同名分支）。

按以下步骤执行，并把每一步结果讲给我：

1. **确保 `armory` remote 存在且 URL 正确**（幂等）：
   ```bash
   TARGET=https://github.com/anton6202527/anime-armory
   if git remote get-url armory >/dev/null 2>&1; then
     git remote set-url armory "$TARGET"
   else
     git remote add armory "$TARGET"
   fi
   git remote get-url armory
   ```

2. **取当前分支名**：`BR=$(git branch --show-current)`，并报告将推送的 commit：`git log -1 --format='%h %s'`。

3. **推送当前分支到 armory 的同名分支**（`GIT_TERMINAL_PROMPT=0` 让缺凭证时快速失败而非卡死）：
   - 普通：`GIT_TERMINAL_PROMPT=0 git push armory "$BR"`
   - `$1` == `force`：`GIT_TERMINAL_PROMPT=0 git push --force-with-lease armory "$BR"`

4. **结果分流**：
   - 成功 → 报告 “已同步 `<分支>` → anime-armory（`<commit>`）”。
   - 因 **non-fast-forward / 历史分叉** 被拒 → **不要**自动强推；告诉我被拒原因，并提示可重跑 `/toa force` 覆盖。
   - 因 **认证失败 / 卡在凭证**（GitHub HTTPS 需 token）→ 停下，告诉我需要先认证（如 `! gh auth login`），认证后再重跑本命令。**不要**去探测我的凭证库。

约束：只动 `armory` 这个 remote 与一次 push，**不要**改 `origin`、不要改本地分支/提交、不要新建提交。
