#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-$(date +%Y-%m-%d)}"
PACKAGE="anime-armory-starter-${VERSION}"
DIST="${ROOT}/dist"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/anime-armory-package.XXXXXX")"
PKG="${WORK}/${PACKAGE}"

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
        --exclude='node_modules' \
        --exclude='dist' \
        -cf - "$src"
    ) | (
      cd "$PKG"
      tar -xf -
    )
  fi
}

mkdir -p "$DIST" "$PKG"

copy_file README.md
copy_file AGENTS.md
copy_file pytest.ini
copy_file conftest.py

copy_dir skills
copy_dir docs
copy_dir desktop/src
copy_file desktop/README.md
copy_file desktop/.gitignore
copy_file desktop/package.json
copy_file desktop/package-lock.json

copy_file 资产库/README.md
copy_file scripts/package_release.sh

for dir in 写小说 制漫剧 写歌 制MV; do
  mkdir -p "${PKG}/${dir}"
  cat > "${PKG}/${dir}/README.md" <<EOF
# ${dir}

这里放新项目产物。starter 包默认不带仓库里的 demo 媒体和工程产物，避免下载包过大。

需要参考 demo 时，请回到完整仓库查看同名顶层目录。
EOF
done

cat > "${PKG}/版本说明.md" <<EOF
# ${PACKAGE}

这是 anime-armory 的轻量 starter 包，生成时间：$(date '+%Y-%m-%d %H:%M:%S %Z')。

包含：
- README.md / AGENTS.md
- skills/ 全部 workflow skill
- docs/ 文档与截图
- desktop/ 桌面端源码，不含 node_modules 和构建产物
- 写小说/、制漫剧/、写歌/、制MV/ 空作品目录
- 资产库/README.md

不包含：
- 仓库内现有 demo 媒体、小说工程和视频工程产物
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
