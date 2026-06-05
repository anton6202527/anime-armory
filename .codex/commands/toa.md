---
description: 同步本仓库(anime-arsenal)与 anime-armory：工具文件双向取最新；可选 demos 单向把每类进度最多的1个作品推到 armory 当示例
argument-hint: "[demos] [force]"
---

把本仓库（`origin` = anime-arsenal）与 **anime-armory** 同步，分两层：

1. **工具文件（除创作区外的一切）= 双向**：两边互相吸收对方最新改动，综合取最新，**有冲突你自己判断解决**。
2. **创作区（demo 产物）= 单向（仅 `demos` 参数时）**：把当前项目每类**进度最多的 1 个作品**单向推到 armory 当公开示例，给其他 AI agent 参考。**只 arsenal→armory，绝不反向**：armory 里的创作区**永远不回流改 arsenal**，未入选的作品**永远只留在 arsenal**。

**创作区 = 4 个目录**：`制MV/`　`制漫剧/`　`写小说/`　`写歌/`

**参数（可组合，任意顺序）**：
- `demos` = 开启第 3 步的「单向推精选 demo」。不带 `demos` 时只同步工具，且**保留** armory 已有的 demo（不动它们）。
- `force` = 第 3 步推送 armory 被拒（历史分叉）时允许 `--force`。留空则只做快进/带 lease。

> 命令与 skills 一样共享给其他 agent：本命令存于 `.claude/commands/toa.md`（Claude）与 `.codex/commands/toa.md`（Codex），都随本命令的工具同步进 armory，所以 Claude / Codex 等 agent 都能用 `/toa`。新增任何共享命令，放进这两个目录即可被 /toa 带走。

---

执行前：在仓库根、分支 `main`。**工作树若有未提交改动 → 先 `git stash -u`，全部做完再 `git stash pop`**（pop 若冲突，提示我手动处理）。git 身份应为 `wesley <anton6202527@users.noreply.github.com>`。

**先按本次调用置参数标志**（含 demos→DEMOS=1；含 force→FORCE=1）：
```bash
DEMOS=0 ; FORCE=0   # ← 按本次 /toa 调用的参数手动置位
```

### 1. 取两边最新
```bash
git fetch origin
git remote get-url armory >/dev/null 2>&1 || git remote add armory https://github.com/anton6202527/anime-armory
GIT_TERMINAL_PROMPT=0 git fetch armory
```
（缺凭证导致 fetch 卡住/失败 → 停下提示我先 `! gh auth login`，**不要探测凭证库**。）

### 2. 吸收 armory 侧的工具改动到本地 main（双向的「拉」）
```bash
git merge --no-ff --no-commit armory/main
```
- **保护创作区（单向闸门）**：armory 即使带了 demo，也**一律恢复本仓库自己的创作区**，绝不让 armory 影响 arsenal：
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

### 3. 构建 armory 提交（用 plumbing 不碰工作树），以 `armory/main` 为父保证可快进

先选 demo（仅 DEMOS=1 时）：枚举每类作品，**按实际完成度选每类 1 部**：
```bash
for top in 制MV 制漫剧 写小说 写歌; do
  echo "=== $top ==="
  for d in "$top"/*/; do
    [ -d "$d" ] || continue
    n=$(grep -o "✅" "$d/_进度.md" 2>/dev/null | wc -l | tr -d ' ')
    echo "  $d  _进度✅=$n"
  done
done
```
**选法（你判断）**：`_进度.md` 的 ✅ 数只是**起点信号**，真正比的是**实际成品完整度**——成片(`成片*.mp4`)、全本导出(`*.docx`/`原作.txt`+审稿)、`歌/song.wav`、出图/clip 齐不齐。
> 反例：写小说里 `本宫…`(✅=1) 数字高，但 `仙界闭关小能手-王敦外传`(✅=0) 才是全本完成+审稿+导出的成品——按成品完整度该选王敦外传。每类挑完成度最高那部，记下完整路径（无作品的类跳过）。

把选中的路径填进 `SEL`（DEMOS=1），然后构建树：
```bash
# DEMOS=1 时填：每类选中作品的完整路径（无则留空/删行）
SEL=( "制漫剧/本宫才是这皇宫最大的妖" "制MV/仗剑下山" "写歌/仗剑下山" "写小说/仙界闭关小能手-王敦外传" )

export GIT_INDEX_FILE=.git/_armory_index
git read-tree main
git rm -r --cached --ignore-unmatch 制MV 制漫剧 写小说 写歌 >/dev/null   # 先清掉全部创作区
if [ "$DEMOS" = 1 ]; then
  # 单向推精选：把选中的作品按原生路径接回 armory 树
  for w in "${SEL[@]}"; do
    [ -n "$w" ] && git read-tree --prefix="$w/" "main:$w"
  done
else
  # 不带 demos：保留 armory 已有的 demo（从 armory/main 接回，不从 arsenal 推新）
  for top in 制MV 制漫剧 写小说 写歌; do
    for w in $(git ls-tree --name-only "armory/main" "$top/" 2>/dev/null); do
      git read-tree --prefix="$w/" "armory/main:$w"
    done
  done
fi
NEWTREE=$(git write-tree)
unset GIT_INDEX_FILE; rm -f .git/_armory_index
ARM=$(git rev-parse armory/main)
```

推送（父=armory/main，正常即快进）：
```bash
if [ "$(git rev-parse "$ARM^{tree}")" = "$NEWTREE" ]; then
  echo "armory 已是目标镜像，无需推送"
else
  MSG="sync(armory): 工具镜像"; [ "$DEMOS" = 1 ] && MSG="sync(armory): 工具镜像 + 精选 demo（每类进度最多1部）"
  COMMIT=$(git commit-tree "$NEWTREE" -p "$ARM" -m "$MSG")
  GIT_TERMINAL_PROMPT=0 git push armory "${COMMIT}:refs/heads/main" \
    || { [ "$FORCE" = 1 ] && GIT_TERMINAL_PROMPT=0 git push --force armory "${COMMIT}:refs/heads/main"; } \
    || echo "armory 推送被拒（可能历史分叉）→ 重跑 /toa force（或 /toa demos force）"
fi
```
> 普通推送是父=armory/main 的快进，**不需要 force**；只有 armory 历史被外部改写才需要 `force`。

### 4. 校验并汇报
```bash
git fetch armory 2>/dev/null
echo "arsenal main = $(git rev-parse --short main) ; origin = $(git rev-parse --short origin/main)"
echo "armory  main = $(git rev-parse --short armory/main)"
echo "--- 工具文件两边应一致（非创作区差异应为空）---"
git -c core.quotepath=false diff --name-only main armory/main | grep -vE '^(制MV|制漫剧|写小说|写歌)/' && echo '⚠️ 有工具区差异!' || echo '✅ 工具文件一致'
echo "--- armory 创作区现状 ---"
for top in 制MV 制漫剧 写小说 写歌; do
  echo "  $top/: $(git ls-tree --name-only armory/main "$top/" 2>/dev/null | sed "s#^$top/##" | paste -sd', ' -)"
done
```
- **DEMOS=1**：armory 每类应**只有选中的那 1 部**（无其它作品）。
- **DEMOS=0**：armory 创作区维持原样（之前 demos 推过的保留；没推过则为空）。

向我报告：本地/origin/armory 三方 sha、工具文件一致性、armory 各类 demo 现状、本次选了哪几部 demo（DEMOS=1 时）+ 解决了哪些工具冲突（若有）。

约束：认证用 `GIT_TERMINAL_PROMPT=0` 快速失败；只动 `main` 与 `armory` remote；创作区**只单向 arsenal→armory（仅 demos 时）**，**绝不**反向回流改/删本仓库创作区，**绝不**把未入选的作品推出去。
