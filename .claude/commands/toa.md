---
description: 双向同步本仓库(anime-arsenal)与 anime-armory 的「非创作区」文件，综合两边最新、冲突自行解决
argument-hint: "[force]"
allowed-tools: Bash(git:*), Read, Edit, Write
---

把本仓库（`origin` = anime-arsenal）与 **anime-armory** 的**除创作区外的所有文件**保持一致：两边互相吸收对方最新改动，综合取最新，**有冲突你自己判断解决**。创作区（demo 产物）只留在 anime-arsenal，**绝不推到 armory，也不被 armory 影响**。

**创作区 = 4 个目录（同步时排除）**：`制MV/`　`制漫剧/`　`写小说/`　`写歌/`

`$1` = `force`：第 4 步推送 armory 被拒（历史分叉）时允许 `--force`。留空则只做快进/带 lease。

---

执行前：在仓库根、分支 `main`。**工作树若有未提交改动 → 先 `git stash -u`，全部做完再 `git stash pop`**（pop 若冲突，提示我手动处理）。git 身份应为 `wesley <anton6202527@users.noreply.github.com>`。

### 1. 取两边最新
```bash
git fetch origin
git remote get-url armory >/dev/null 2>&1 || git remote add armory https://github.com/anton6202527/anime-armory
GIT_TERMINAL_PROMPT=0 git fetch armory
```
（缺凭证导致 fetch 卡住/失败 → 停下提示我先 `! gh auth login`，**不要探测凭证库**。）

### 2. 吸收 armory 侧的改动到本地 main（双向的「拉」）
```bash
git merge --no-ff --no-commit armory/main
```
- **保护创作区**：armory 没有这 4 个目录，合并会想删掉它们 → 一律恢复本仓库自己的版本：
  ```bash
  git checkout HEAD -- 制MV 制漫剧 写小说 写歌 2>/dev/null
  git add -A 制MV 制漫剧 写小说 写歌 2>/dev/null
  ```
- **其它文件有冲突（`<<<<<<<` 标记）** → 逐个打开，**按「综合两边最新、保留各自有意义的改动」的原则手动改**（不要无脑选一边），改完 `git add <文件>`。
- 收尾：
  ```bash
  git commit --no-edit 2>/dev/null || echo "已是最新，无需合并提交"
  ```
- 推 anime-arsenal：`GIT_TERMINAL_PROMPT=0 git push origin main`

### 3. 构建 armory 的「工具-only」提交（双向的「推」，用 plumbing 不碰工作树）
arsenal 当前树 **去掉 4 个创作区目录**，以 `armory/main` 为父提交，保证可快进：
```bash
export GIT_INDEX_FILE=.git/_armory_index
git read-tree main
git rm -r --cached --ignore-unmatch 制MV 制漫剧 写小说 写歌
NEWTREE=$(git write-tree)
unset GIT_INDEX_FILE; rm -f .git/_armory_index
ARM=$(git rev-parse armory/main)
if [ "$(git rev-parse "$ARM^{tree}")" = "$NEWTREE" ]; then
  echo "armory 已是最新工具镜像，无需推送"
else
  COMMIT=$(git commit-tree "$NEWTREE" -p "$ARM" -m "sync(armory): 工具文件镜像（排除创作区 制MV/制漫剧/写小说/写歌）")
  GIT_TERMINAL_PROMPT=0 git push armory "${COMMIT}:refs/heads/main" \
    || ([ "$1" = force ] && GIT_TERMINAL_PROMPT=0 git push --force armory "${COMMIT}:refs/heads/main") \
    || echo "armory 推送被拒（可能历史分叉）→ 重跑 /toa force"
fi
```

### 4. 校验并汇报
```bash
git fetch armory 2>/dev/null
echo "arsenal main = $(git rev-parse --short main) ; origin = $(git rev-parse --short origin/main)"
echo "armory  main = $(git rev-parse --short armory/main)"
echo "armory 顶层目录（应无创作区4目录）："; git ls-tree --name-only armory/main | grep -E '制MV|制漫剧|写小说|写歌' && echo '⚠️ 仍含创作区!' || echo 'OK: 不含创作区'
```
向我报告：本地/origin/armory 三方 sha、armory 确认不含创作区、本次解决了哪些工具文件冲突（若有）。

约束：认证用 `GIT_TERMINAL_PROMPT=0` 快速失败；只动 `main` 与 `armory` remote；**绝不**把创作区推到 armory，也**绝不**因 armory 而删/改本仓库创作区内容。
