#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="AnimeArmory"
DEFAULT_APP_PATH="src-tauri/target/release/bundle/macos/${APP_NAME}.app"
APP_PATH="${APP_PATH:-$DEFAULT_APP_PATH}"
OUT_DIR="${1:-src-tauri/target/release/bundle/pkg}"
VERSION="$(node -p "JSON.parse(require('fs').readFileSync('package.json', 'utf8')).version")"
IDENTIFIER="$(node -p "JSON.parse(require('fs').readFileSync('src-tauri/tauri.conf.json', 'utf8')).identifier")"

if [[ ! -d "${APP_PATH}" && "${SKIP_BUILD:-0}" != "1" ]]; then
  npm run tauri -- build --bundles app
fi

mkdir -p "${OUT_DIR}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle: ${APP_PATH}" >&2
  exit 1
fi

APP_BINARY="${APP_PATH}/Contents/MacOS/anime-armory-desktop"
if [[ ! -f "${APP_BINARY}" ]]; then
  APP_BINARY="$(find "${APP_PATH}/Contents/MacOS" -type f | head -1 || true)"
fi
if [[ -n "${APP_BINARY}" ]] && command -v lipo >/dev/null 2>&1; then
  ARCHS="$(lipo -archs "${APP_BINARY}" 2>/dev/null || true)"
else
  ARCHS="$(uname -m)"
fi

if [[ -n "${PKG_ARCH:-}" ]]; then
  PKG_ARCH="${PKG_ARCH}"
elif [[ " ${ARCHS} " == *" arm64 "* && " ${ARCHS} " == *" x86_64 "* ]]; then
  PKG_ARCH="universal"
elif [[ " ${ARCHS} " == *" arm64 "* ]]; then
  PKG_ARCH="arm64"
elif [[ " ${ARCHS} " == *" x86_64 "* ]]; then
  PKG_ARCH="x64"
else
  PKG_ARCH="$(printf '%s' "${ARCHS:-$(uname -m)}" | tr ' /' '__')"
fi

COMPONENT_PKG="${OUT_DIR}/${APP_NAME}_${VERSION}_${PKG_ARCH}_component.pkg"
FINAL_PKG="${OUT_DIR}/${APP_NAME}_${VERSION}_${PKG_ARCH}.pkg"

rm -f "${COMPONENT_PKG}" "${FINAL_PKG}"

pkgbuild \
  --component "${APP_PATH}" \
  --install-location "/Applications" \
  --identifier "${IDENTIFIER}.pkg" \
  --version "${VERSION}" \
  "${COMPONENT_PKG}" >/dev/null

productbuild \
  --package "${COMPONENT_PKG}" \
  "${FINAL_PKG}" >/dev/null

rm -f "${COMPONENT_PKG}"

echo "${FINAL_PKG}"
