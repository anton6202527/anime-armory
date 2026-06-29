#!/usr/bin/env bash
# 仓库级回归闸门（repo-level regression gate）—— 一处跑齐所有"改动时必须仍绿"的检查。
#
# 为什么需要它：本仓库是 254+ 脚本、契约强耦合的 skill 工厂，约 50 个脚本 import 本线
# `_lib` 契约，改一处契约能静默废掉一打下游消费者。提交直推 main，且后台 factory 进程
# 会自动 commit WIP——没有任何东西在改动时挡这一下时，"静默失效边"是反复出现的 bug 类。
# 这个脚本把散落的治理/测试入口收成一个退出码，供 CI、pre-commit 钩子和人工自检共用。
#
# 检查项（任一非零 → 整体非零）：
#   1) pytest skills/         全量纯逻辑测试（**逐目录隔离进程**，避免跨线同名 vendored 模块在
#                             单进程全树收集时互相遮蔽；重 conda 依赖的测试自身优雅跳过）
#   2) pytest tools/          元工具自身的测试
#   3) validate_skills.py     设计law机检（E1 VCS-free / B* / F1 README 索引同步 / F3 入口文档同步）
#   4) check_independence.py  系列独立性（无 skills/common、无跨线 import）
#   5) novel self-audit       novel 专项 registry/README/路由/队列/市场基准治理
#
# 用法：
#   bash tools/run_all_checks.sh            # 全量（CI / 发布前）
#   bash tools/run_all_checks.sh --fast     # 跳过全量 pytest，只跑治理 + 元工具测试（pre-commit 用）
#   bash tools/run_all_checks.sh --changed  # 只跑改动目录的 pytest（pre-commit 快子集）
#
# 退出码：0=全绿；非0=有检查未过（哪一项失败会在末尾汇总）。
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3}"
MODE="full"
for arg in "$@"; do
  case "$arg" in
    --fast) MODE="fast" ;;
    --changed) MODE="changed" ;;
    *) echo "未知参数: $arg" >&2; exit 2 ;;
  esac
done

declare -a FAILED=()
run_step() {
  local name="$1"; shift
  echo ""
  echo "──────────────────────────────────────────────"
  echo "▶ $name"
  echo "──────────────────────────────────────────────"
  if "$@"; then
    echo "✅ $name"
  else
    echo "❌ $name (exit $?)"
    FAILED+=("$name")
  fi
}

# 逐目录隔离跑 pytest：每个含 test_ 的目录单独一个进程。
# 为什么：各创作线**有意 vendored 同名模块**（init_project.py×9 / gate.py×3 / consistency_audit.py×2…，
# 这是「完全独立、零公共层」的设计，不是 bug）。单进程全树收集时，test 文件的 `sys.path.insert(0,本目录)
# + import gate` 会让先导入者占据 sys.modules[gate]，后续别的线拿到错的模块——失败点随收集顺序漂移、
# 时绿时红（conftest 的同名驱逐只在 import 时机覆盖直接兄弟，盖不住传递/运行期导入）。进程隔离从根上消除：
# 每目录全新解释器，sys.modules 不跨目录共享。决策语义不变，只是收集边界改对。
pytest_isolated() {                       # args: 已解析的测试目录列表
  local failed=() rc=0 d out
  out="$(mktemp)"
  for d in "$@"; do
    if ! "$PYTHON" -m pytest "$d" -q -p no:cacheprovider >"$out" 2>&1; then
      rc=1; failed+=("$d")
      echo "  ✗ $d"
      tail -4 "$out" | sed 's/^/    /'
    fi
  done
  rm -f "$out"
  if [ "$rc" -eq 0 ]; then
    echo "  $# 个测试目录逐一隔离运行，全过"
  else
    echo "  失败目录(${#failed[@]})：${failed[*]}"
  fi
  return $rc
}

# 改动目录的 pytest 子集（pre-commit 用）：从 git 暂存/工作区改动里挑出含 test_ 的 skill 目录。
changed_test_dirs() {
  {
    git diff --name-only --cached 2>/dev/null
    git diff --name-only 2>/dev/null
  } | grep -E '\.py$' | xargs -I{} dirname {} 2>/dev/null \
    | sort -u \
    | while read -r d; do
        if ls "$d"/test_*.py >/dev/null 2>&1; then echo "$d"; fi
      done
}

case "$MODE" in
  full)
    SKILL_DIRS=()  # 兼容 macOS bash 3.2（无 mapfile）：while-read 填数组
    while IFS= read -r d; do SKILL_DIRS+=("$d"); done \
      < <(find skills -name 'test_*.py' -not -path '*__pycache__*' -exec dirname {} \; | sort -u)
    run_step "pytest skills/（逐目录隔离）" pytest_isolated "${SKILL_DIRS[@]}"
    run_step "pytest tools/"  "$PYTHON" -m pytest tools/ -q -p no:cacheprovider
    ;;
  fast)
    run_step "pytest tools/"  "$PYTHON" -m pytest tools/ -q -p no:cacheprovider
    ;;
  changed)
    DIRS=()  # 兼容 macOS bash 3.2（无 mapfile）
    while IFS= read -r d; do DIRS+=("$d"); done < <(changed_test_dirs)
    if [ "${#DIRS[@]}" -gt 0 ]; then
      run_step "pytest（改动目录·逐目录隔离）" pytest_isolated "${DIRS[@]}"
    else
      echo "ℹ 无改动的测试目录，跳过 pytest 子集"
    fi
    ;;
esac

run_step "validate_skills" "$PYTHON" tools/validate_skills.py
run_step "novel-self-audit" "$PYTHON" skills/novel-review/scripts/self_audit.py --fail-on-block
run_step "independence-audit" "$PYTHON" tools/independence-audit/scripts/check_independence.py
run_step "state-files-lint" "$PYTHON" tools/validate_state_files.py

echo ""
echo "=============================================="
if [ "${#FAILED[@]}" -eq 0 ]; then
  echo "✅ 全部检查通过"
  exit 0
else
  echo "❌ 未通过：${FAILED[*]}"
  exit 1
fi
