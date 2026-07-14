#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-$(date +%Y-%m-%d)}"
PACKAGE="anime-armory-starter-${VERSION}"
DIST="${ROOT}/dist"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/anime-armory-package.XXXXXX")"
PKG="${WORK}/${PACKAGE}"
CREATIVE_LINES=("制漫剧" "画漫画" "写小说" "写歌" "制MV" "拍广告")

trap 'rm -rf "$WORK"' EXIT

copy_file() {
  local src="$1"
  if [ -f "${ROOT}/${src}" ]; then
    mkdir -p "${PKG}/$(dirname "$src")"
    cp -p "${ROOT}/${src}" "${PKG}/${src}"
  fi
}

copy_dir() {
  local src="$1"
  if [ -d "${ROOT}/${src}" ]; then
    mkdir -p "${PKG}"
    (
      cd "$ROOT"
      tar \
        --exclude='*/__pycache__' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        --exclude='.env' \
        --exclude='.env.*' \
        --exclude='.branches' \
        --exclude='.temp' \
        --exclude='node_modules' \
        --exclude='out' \
        --exclude='release' \
        --exclude='resources' \
        --exclude='dist' \
        -cf - "$src"
    ) | (
      cd "$PKG"
      tar -xf -
    )
  fi
}

copy_creation_manuals() {
  local rel
  local manuals=("创作区/使用手册.md")
  local dir
  for dir in "${CREATIVE_LINES[@]}"; do
    manuals+=("创作区/${dir}/使用手册.md")
  done
  for rel in "${manuals[@]}"; do
    if [ ! -f "${ROOT}/${rel}" ]; then
      echo "Missing creation manual: ${rel}" >&2
      exit 1
    fi
    mkdir -p "${PKG}/$(dirname "$rel")"
    cp -p "${ROOT}/${rel}" "${PKG}/${rel}"
  done
}

mkdir -p "$DIST" "$PKG"

copy_file README.md
copy_file AGENTS.md
copy_file pytest.ini
copy_file conftest.py
copy_file .env.example
copy_file package.json
copy_file package-lock.json
copy_file tsconfig.base.json

copy_dir skills
copy_dir tools
copy_dir docs
copy_dir packages
copy_dir infrastructure
copy_dir apps/backend
copy_dir apps/web
copy_dir apps/desktop/src
copy_dir apps/desktop/scripts
copy_dir apps/desktop/assets
copy_file apps/desktop/README.md
copy_file apps/desktop/.gitignore
copy_file apps/desktop/package.json
copy_file apps/desktop/electron-builder.yml
copy_file apps/desktop/electron.vite.config.ts
copy_file apps/desktop/tsconfig.node.json
copy_file apps/desktop/tsconfig.web.json

copy_file scripts/package_release.sh

for dir in "${CREATIVE_LINES[@]}"; do
  mkdir -p "${PKG}/创作区/${dir}/_资产库"
  cat > "${PKG}/创作区/${dir}/README.md" <<EOF
# 创作区/${dir}

这里放新项目产物。starter 包默认不带仓库里的 demo 媒体和工程产物，避免下载包过大。

需要参考 demo 时，请回到完整仓库查看同名创作区目录。
EOF
  if [ ! -f "${ROOT}/创作区/${dir}/_资产库/README.md" ]; then
    echo "Missing series asset library manual: 创作区/${dir}/_资产库/README.md" >&2
    exit 1
  fi
  cp -p "${ROOT}/创作区/${dir}/_资产库/README.md" "${PKG}/创作区/${dir}/_资产库/README.md"
done
copy_creation_manuals

cat > "${PKG}/版本说明.md" <<EOF
# ${PACKAGE}

这是 anime-armory 的轻量 starter 包，生成时间：$(date '+%Y-%m-%d %H:%M:%S %Z')。

包含：
- README.md / AGENTS.md
- skills/ 全部 workflow skill
- tools/ 仓库级维护工具
- docs/ 文档与截图
- packages/ Supabase/R2 共享契约、对象存储和客户端基础层
- apps/backend/ Supabase 数据库迁移与私有资产 Edge Function
- apps/web/ 未来 Web 客户端的工作区边界（当前不含页面实现）
- infrastructure/ R2 CORS 等云资源配置样例
- apps/desktop/ 桌面端(Electron)源码，不含 node_modules 和构建产物
- 创作区/ 六条空作品线目录、各系列使用手册与各自的 _资产库/ 说明

不包含：
- 仓库内现有 demo 媒体、小说工程和视频工程产物
- 各系列 _资产库/ 中的实际资产包（starter 只带规则说明）
- .git、.claude、.codex、.cursor 等私有 agent 配置
- .venv、node_modules、__pycache__、dist 等本地依赖和缓存

使用方式：
1. 解压本包。
2. 用本地 AI agent 打开目录。
3. 先读 AGENTS.md，再按 README.md 的入口 skill 开始新项目。
EOF

find "$PKG" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$PKG" -name '.DS_Store' -type f -delete
find "$PKG" -name '*.pyc' -type f -delete

ZIP="${DIST}/${PACKAGE}.zip"
TARGZ="${DIST}/${PACKAGE}.tar.gz"
rm -f "$ZIP" "$ZIP.sha256" "$TARGZ" "$TARGZ.sha256"

if command -v ditto >/dev/null 2>&1; then
  (cd "$WORK" && ditto -c -k --norsrc --keepParent "$PACKAGE" "$ZIP")
  shasum -a 256 "$ZIP" > "$ZIP.sha256"
  echo "$ZIP"
  echo "$ZIP.sha256"
elif command -v zip >/dev/null 2>&1; then
  (cd "$WORK" && zip -qr "$ZIP" "$PACKAGE")
  shasum -a 256 "$ZIP" > "$ZIP.sha256"
  echo "$ZIP"
  echo "$ZIP.sha256"
else
  (cd "$WORK" && tar -czf "$TARGZ" "$PACKAGE")
  shasum -a 256 "$TARGZ" > "$TARGZ.sha256"
  echo "$TARGZ"
  echo "$TARGZ.sha256"
fi
