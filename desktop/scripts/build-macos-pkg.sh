#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="AnimeArmory"
APP_PATH="src-tauri/target/release/bundle/macos/${APP_NAME}.app"
OUT_DIR="${1:-src-tauri/target/release/bundle/pkg}"
VERSION="$(node -p "JSON.parse(require('fs').readFileSync('package.json', 'utf8')).version")"
HOST_ARCH="$(uname -m)"

case "${HOST_ARCH}" in
  arm64) PKG_ARCH="aarch64" ;;
  x86_64) PKG_ARCH="x64" ;;
  *) PKG_ARCH="${HOST_ARCH}" ;;
esac

mkdir -p "${OUT_DIR}"

COMPONENT_PKG="${OUT_DIR}/${APP_NAME}_${VERSION}_${PKG_ARCH}_component.pkg"
FINAL_PKG="${OUT_DIR}/${APP_NAME}_${VERSION}_${PKG_ARCH}.pkg"

npm run tauri -- build --bundles app

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle: ${APP_PATH}" >&2
  exit 1
fi

rm -f "${COMPONENT_PKG}" "${FINAL_PKG}"

pkgbuild \
  --component "${APP_PATH}" \
  --install-location "/Applications" \
  --identifier "com.animearmory.desktop.pkg" \
  --version "${VERSION}" \
  "${COMPONENT_PKG}"

productbuild \
  --package "${COMPONENT_PKG}" \
  "${FINAL_PKG}"

rm -f "${COMPONENT_PKG}"

echo "${FINAL_PKG}"
