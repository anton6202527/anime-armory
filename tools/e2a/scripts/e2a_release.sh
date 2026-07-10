#!/usr/bin/env bash
# e2a — build the Electron desktop app (desktop-electron/) as release installers
# plus the per-line demo zip assets, and upload them to GitHub Release assets.
# Successor of the retired Tauri /r2a flow. Self-contained: demo selection
# (scripts/select_demo.cjs), skills bundler (scripts/sync_bundle.cjs) and the
# demo-works config live in tools/e2a/; the safe payload copier is the shared
# tools/release-safety/demo_safety.cjs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

TARGET_REPO="${E2A_TARGET_REPO:-anton6202527/anime-armory}"
ARTIFACT_DIR="${E2A_OUTPUT_DIR:-}"
SIGNING_IDENTITY="${E2A_SIGNING_IDENTITY:-}"
NOTARY_PROFILE="${E2A_NOTARY_KEYCHAIN_PROFILE:-}"
UPLOAD_RETRIES="${E2A_UPLOAD_RETRIES:-6}"

BUILD_APP_ASSETS=1
BUILD_DEMO_ASSETS=1
UPLOAD=1
TAG="${E2A_RELEASE_TAG:-}"
WORK=""
SOURCE_DIR=""
SOURCE_SHA="unknown"
SOURCE_DIRTY="unknown"
OUT_DIR=""
ASSETS=()
DEMO_WORKS=()
CREATIVE_LINES=("写小说" "制漫剧" "画漫画" "写歌" "制MV" "拍广告")
CREATION_MANUALS=("创作区/使用手册.md")
for line in "${CREATIVE_LINES[@]}"; do
  CREATION_MANUALS+=("创作区/$line/使用手册.md")
done

usage() {
  cat <<'EOF'
Usage:
  bash tools/e2a/scripts/e2a_release.sh [options]

Default behaviour (no flags):
  Snapshot the local checkout, build the Electron macOS Apple Silicon DMG
  (AnimeArmory_electron_macos_arm64.dmg) WITH the bundled skills repo + demo
  catalog, build the per-line demo zip assets, upload everything to the
  anime-armory GitHub Release for the tag, and write SHA256SUMS.txt.
  README download links are NOT touched and the release is NOT marked latest
  (the Tauri /r2a flow owns those).

Options:
  --apps-only, --no-demo-assets   Build/upload only the Electron DMG.
  --demo-assets, --demos, --demo  Build/upload only demo zip assets.
  --no-upload                     Build locally only (artifacts in dist/e2a-release-<tag>).
  --repo owner/name               Target GitHub repo. Default: anton6202527/anime-armory.
  --tag TAG                       Release tag. Default: electron-v<desktop-electron version>.
  -h, --help                      Show this help.

Release artifact names:
  AnimeArmory_electron_macos_arm64.dmg
  AnimeArmory_demo_novel.zip / _n2d / _comic / _song / _mv / _ad (selected works only)

Environment:
  E2A_OUTPUT_DIR                Artifact output dir. Default: dist/e2a-release-<tag>.
  E2A_RELEASE_TAG               Override the release tag.
  E2A_TARGET_REPO               Target repo (owner/name).
  E2A_SIGNING_IDENTITY          macOS codesign identity for electron-builder (CSC_NAME).
                                Unset = unsigned local build (right-click open to run).
  E2A_NOTARY_KEYCHAIN_PROFILE   Optional notarytool profile; staples the DMG when set.
  E2A_UPLOAD_RETRIES            Retry count per uploaded asset. Default: 6.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apps-only|--no-demo-assets) BUILD_APP_ASSETS=1; BUILD_DEMO_ASSETS=0; shift ;;
    --demo-assets|--demos|--demo) BUILD_APP_ASSETS=0; BUILD_DEMO_ASSETS=1; shift ;;
    --with-demo-assets) BUILD_APP_ASSETS=1; BUILD_DEMO_ASSETS=1; shift ;;
    --no-upload) UPLOAD=0; shift ;;
    --repo) TARGET_REPO="${2:?missing owner/name after --repo}"; shift 2 ;;
    --tag) TAG="${2:?missing tag after --tag}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

cleanup() {
  [[ -n "$WORK" && -d "$WORK" ]] && rm -rf "$WORK"
}
trap cleanup EXIT

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

json_value() {
  node -p "JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'))${2}" "$1"
}

# --- source snapshot (same exclusion policy as r2a) -------------------------

rsync_common_excludes=(
  --exclude='.git/'
  --exclude='.agents/'
  --exclude='.claude/'
  --exclude='.cline/'
  --exclude='.codex/'
  --exclude='.continue/'
  --exclude='.cursor/'
  --exclude='.gemini/'
  --exclude='.opencode/'
  --exclude='.roo/'
  --exclude='.windsurf/'
  --exclude='.aider.conf.yml'
  --exclude='.aiderignore'
  --exclude='.clinerules'
  --exclude='.cursorrules'
  --exclude='.windsurfrules'
  --exclude='CLAUDE.md'
  --exclude='GEMINI.md'
  --exclude='OPENCODE.md'
  --exclude='QWEN.md'
  --exclude='.github/copilot-instructions.md'
  --exclude='.github/instructions/'
  --exclude='.github/prompts/'
  --exclude='.DS_Store'
  --exclude='__pycache__/'
  --exclude='.pytest_cache/'
  --exclude='.mypy_cache/'
  --exclude='.ruff_cache/'
  --exclude='node_modules/'
  --exclude='dist/'
  --exclude='desktop-electron/out/'
  --exclude='desktop-electron/release/'
  --exclude='desktop-electron/resources/'
  --exclude='vscode-extension/node_modules/'
)

select_demo_works() {
  local source_root="$1"
  local demo
  DEMO_WORKS=()
  while IFS= read -r demo; do
    [[ -n "$demo" ]] || continue
    case "$demo" in
      创作区/*/*) ;;
      *) echo "Invalid demo path selected: $demo" >&2; exit 1 ;;
    esac
    if [[ "$demo" == *".."* || ! -d "$source_root/$demo" ]]; then
      echo "Demo work is missing or unsafe: $demo" >&2
      exit 1
    fi
    DEMO_WORKS+=("$demo")
  done < <(node "$ROOT/tools/e2a/scripts/select_demo.cjs" "$source_root")

  echo "[e2a] demo works:"
  for demo in ${DEMO_WORKS+"${DEMO_WORKS[@]}"}; do
    echo "[e2a]   - $demo"
  done
}

copy_work_reference() {
  local rel="$1"
  mkdir -p "$SOURCE_DIR/$rel"
  if [[ -f "$ROOT/$rel/_进度.md" ]]; then
    cp "$ROOT/$rel/_进度.md" "$SOURCE_DIR/$rel/_进度.md"
  fi
}

snapshot_local_source() {
  require_cmd git
  require_cmd rsync
  require_cmd node
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/e2a.XXXXXX")"
  SOURCE_DIR="$WORK/source"
  mkdir -p "$SOURCE_DIR"

  select_demo_works "$ROOT"

  echo "[e2a] snapshotting local checkout: $ROOT"
  rsync -a --delete "${rsync_common_excludes[@]}" --exclude='创作区/' "$ROOT/" "$SOURCE_DIR/"

  local rel
  for rel in "${CREATION_MANUALS[@]}"; do
    if [[ ! -f "$ROOT/$rel" ]]; then
      echo "[e2a] missing creation manual: $rel" >&2
      exit 1
    fi
    mkdir -p "$SOURCE_DIR/$(dirname "$rel")"
    cp -p "$ROOT/$rel" "$SOURCE_DIR/$rel"
  done

  # the snapshot only ever carries _进度.md references — keeping full payloads
  # out of the snapshot keeps sync-skills' bundled seeds (and thus the app
  # resources) slim; demo zips copy payloads straight from the checkout.
  local demo
  for demo in ${DEMO_WORKS+"${DEMO_WORKS[@]}"}; do
    copy_work_reference "$demo"
  done

  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")"
  if [[ -n "$(git -C "$ROOT" status --short 2>/dev/null || true)" ]]; then
    SOURCE_DIRTY="yes"
    echo "[e2a] local source has uncommitted changes; snapshot includes non-excluded working tree files"
  else
    SOURCE_DIRTY="no"
  fi
  echo "[e2a] source commit: ${SOURCE_SHA}"
}

# --- electron app build ------------------------------------------------------

stage_bundled_resources() {
  # sync_bundle.cjs bundles skills/tools/manuals + demo_catalog.json into
  # desktop-electron/resources; the packaged app reads the same layout from
  # process.resourcesPath/resources (electron-builder extraResources).
  local featured_works
  featured_works="$(printf '%s\n' ${DEMO_WORKS+"${DEMO_WORKS[@]}"})"
  echo "[e2a] bundling skills repo + demo catalog"
  rm -rf "$SOURCE_DIR/desktop-electron/resources"
  E2A_INCLUDE_DEMOS=0 \
  E2A_FEATURED_WORKS="$featured_works" \
  E2A_TARGET_REPO="$TARGET_REPO" \
  E2A_BUNDLE_DIR="$SOURCE_DIR/desktop-electron/resources" \
    node "$SOURCE_DIR/tools/e2a/scripts/sync_bundle.cjs"
  if [[ ! -f "$SOURCE_DIR/desktop-electron/resources/demo_catalog.json" ]]; then
    echo "Bundled resources are missing demo_catalog.json" >&2
    exit 1
  fi
}

validate_macos_dmg() {
  local dmg="$1"
  local mount_dir="$OUT_DIR/mount-check"
  rm -rf "$mount_dir"
  mkdir -p "$mount_dir"
  echo "[e2a] validating DMG: $(basename "$dmg")"
  hdiutil verify "$dmg"
  hdiutil attach "$dmg" -mountpoint "$mount_dir" -nobrowse -readonly >/dev/null
  local ok=1
  if [[ ! -d "$mount_dir/AnimeArmory.app" ]]; then
    echo "DMG validation failed: AnimeArmory.app not found" >&2
    ok=0
  elif [[ ! -f "$mount_dir/AnimeArmory.app/Contents/Resources/resources/demo_catalog.json" ]]; then
    echo "DMG validation failed: bundled resources/demo_catalog.json not found" >&2
    ok=0
  fi
  hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
  rm -rf "$mount_dir"
  [[ "$ok" == "1" ]] || exit 1
}

notarize_dmg_if_configured() {
  local dmg="$1"
  if [[ -z "$NOTARY_PROFILE" ]]; then
    echo "[e2a] notarization skipped (E2A_NOTARY_KEYCHAIN_PROFILE not set)"
    return
  fi
  echo "[e2a] submitting DMG to Apple notarization profile: $NOTARY_PROFILE"
  xcrun notarytool submit "$dmg" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$dmg"
  xcrun stapler validate "$dmg"
}

sign_macos_app() {
  # ad-hoc by default, same as /r2a; a real identity makes the app distributable
  local app_path="$1"
  local identity="${SIGNING_IDENTITY:--}"
  echo "[e2a] signing macOS app with identity: $identity"
  codesign --force --deep --options runtime --sign "$identity" "$app_path"
  codesign --verify --deep --strict "$app_path"
}

make_macos_dmg() {
  # hdiutil instead of electron-builder's dmg target: the latter downloads a
  # dmgbuild bundle at build time, which is flaky on restricted networks.
  local app_path="$1" dmg_out="$2" stage
  stage="$(mktemp -d "${TMPDIR:-/tmp}/e2a-dmg-stage.XXXXXX")"
  ditto "$app_path" "$stage/AnimeArmory.app"
  ln -s /Applications "$stage/Applications"
  rm -f "$dmg_out"
  hdiutil create -volname "AnimeArmory" -srcfolder "$stage" -format UDZO -ov "$dmg_out"
  rm -rf "$stage"
}

build_electron_macos() {
  require_cmd npm
  require_cmd hdiutil
  require_cmd codesign
  require_cmd ditto
  stage_bundled_resources

  echo "[e2a] building Electron app (npm ci + typecheck + electron-vite + electron-builder --dir)"
  (
    cd "$SOURCE_DIR/desktop-electron"
    if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
    npm run build
    CSC_IDENTITY_AUTO_DISCOVERY=false npx electron-builder --mac --arm64 --dir
  )

  local app_src="$SOURCE_DIR/desktop-electron/release/mac-arm64/AnimeArmory.app"
  if [[ ! -d "$app_src" ]]; then
    echo "Could not locate built Electron app bundle: $app_src" >&2
    exit 1
  fi
  local artifact_dmg="$ARTIFACT_DIR/AnimeArmory_electron_macos_arm64.dmg"
  sign_macos_app "$app_src"
  make_macos_dmg "$app_src" "$artifact_dmg"
  notarize_dmg_if_configured "$artifact_dmg"
  validate_macos_dmg "$artifact_dmg"
  ASSETS+=("$artifact_dmg")
}

# --- demo zip assets (same layout + slimming as r2a) -------------------------

demo_line_key() {
  case "$1" in
    "写小说") echo "novel" ;;
    "制漫剧") echo "n2d" ;;
    "画漫画") echo "comic" ;;
    "写歌") echo "song" ;;
    "制MV") echo "mv" ;;
    "拍广告") echo "ad" ;;
    *) echo "Unknown creative line for demo asset: $1" >&2; exit 1 ;;
  esac
}

keep_only_named_child_dirs() {
  local dir="$1"; shift
  [[ -d "$dir" ]] || return 0
  local child name keep wanted
  for child in "$dir"/*; do
    [[ -d "$child" ]] || continue
    name="$(basename "$child")"
    keep=0
    for wanted in "$@"; do
      [[ "$name" == "$wanted" ]] && keep=1 && break
    done
    [[ "$keep" == "1" ]] || rm -rf "$child"
  done
}

prune_demo_asset_stage() {
  local work_dir="$1" key="$2"
  [[ -d "$work_dir" ]] || return 0
  case "$key" in
    n2d)
      echo "[e2a] slimming n2d demo asset to first-episode media payload"
      keep_only_named_child_dirs "$work_dir/出图" "第1集"
      keep_only_named_child_dirs "$work_dir/合成" "第1集"
      find "$work_dir/合成/第1集/配音" -maxdepth 1 -type f -name 'line_*.wav' -delete 2>/dev/null || true
      ;;
  esac
}

build_demo_zip_assets() {
  require_cmd zip
  local demo rest line key asset stage
  for demo in ${DEMO_WORKS+"${DEMO_WORKS[@]}"}; do
    rest="${demo#创作区/}"
    line="${rest%%/*}"
    key="$(demo_line_key "$line")"
    asset="$ARTIFACT_DIR/AnimeArmory_demo_${key}.zip"
    stage="$(mktemp -d "${TMPDIR:-/tmp}/e2a-demo-${key}.XXXXXX")"
    mkdir -p "$stage/$(dirname "$demo")"
    # payload comes straight from the checkout through the release-safety
    # copier (secret/cache filtering) — the snapshot holds references only
    node "$ROOT/tools/release-safety/demo_safety.cjs" copy "$ROOT/$demo" "$stage/$demo"
    prune_demo_asset_stage "$stage/$demo" "$key"
    rm -f "$asset"
    (
      cd "$stage"
      find "创作区" -exec touch -h -t 202001010000 {} + 2>/dev/null || find "创作区" -exec touch -t 202001010000 {} +
      COPYFILE_DISABLE=1 zip -X -qr "$asset" "创作区"
    )
    rm -rf "$stage"
    echo "[e2a] validating zip container: $(basename "$asset")"
    unzip -tqq "$asset"
    ASSETS+=("$asset")
  done
}

# --- checksums / release notes / upload --------------------------------------

write_checksums() {
  : > "$OUT_DIR/SHA256SUMS.txt"
  local asset base
  for asset in "${ASSETS[@]}"; do
    base="$(basename "$asset")"
    if command -v shasum >/dev/null 2>&1; then
      (cd "$(dirname "$asset")" && shasum -a 256 "$base") >> "$OUT_DIR/SHA256SUMS.txt"
    else
      (cd "$(dirname "$asset")" && sha256sum "$base") >> "$OUT_DIR/SHA256SUMS.txt"
    fi
  done
}

release_notes() {
  local notes="$OUT_DIR/RELEASE_NOTES.md"
  {
    echo "# AnimeArmory (Electron) ${TAG}"
    echo
    if [[ "$UPLOAD" == "1" ]]; then
      echo "Built locally with tools/e2a and uploaded as GitHub Release assets."
    else
      echo "Built locally with tools/e2a; upload disabled."
    fi
    echo
    echo "- Source commit: ${SOURCE_SHA} (dirty: ${SOURCE_DIRTY})"
    echo "- Desktop shell: Electron (desktop-electron/)"
    echo "- Bundled: skills repo + creation manuals + demo catalog (payloads download on demand)"
    echo "- Release artifacts committed to git history: no"
    echo
    echo "Configured demo works:"
    local demo
    for demo in ${DEMO_WORKS+"${DEMO_WORKS[@]}"}; do
      echo "- ${demo}"
    done
    echo
    echo "Assets:"
    local asset
    for asset in "${ASSETS[@]}"; do
      echo "- $(basename "$asset")"
    done
    echo
    echo "Fixed tag download URLs:"
    for asset in "${ASSETS[@]}"; do
      echo "- https://github.com/${TARGET_REPO}/releases/download/${TAG}/$(basename "$asset")"
    done
  } > "$notes"
  echo "$notes"
}

upload_asset_with_retry() {
  local asset="$1" attempt=1
  while (( attempt <= UPLOAD_RETRIES )); do
    if gh release upload "$TAG" "$asset" --repo "$TARGET_REPO" --clobber; then
      return 0
    fi
    echo "[e2a] upload failed for $(basename "$asset") (attempt ${attempt}/${UPLOAD_RETRIES}); retrying" >&2
    attempt=$((attempt + 1))
    sleep $((attempt * 3))
  done
  echo "Failed to upload $(basename "$asset") after ${UPLOAD_RETRIES} attempts" >&2
  exit 1
}

upload_release() {
  [[ "$UPLOAD" == "1" ]] || return 0
  require_cmd gh
  local notes="$1"
  if gh release view "$TAG" --repo "$TARGET_REPO" >/dev/null 2>&1; then
    if [[ "$BUILD_APP_ASSETS" == "1" ]]; then
      gh release edit "$TAG" --repo "$TARGET_REPO" \
        --title "AnimeArmory (Electron) ${TAG}" --notes-file "$notes"
    else
      echo "[e2a] demo-assets upload: keeping existing release notes for ${TAG}"
    fi
  else
    gh release create "$TAG" --repo "$TARGET_REPO" \
      --title "AnimeArmory (Electron) ${TAG}" --notes-file "$notes" --latest=false
  fi
  local asset
  for asset in "${ASSETS[@]}"; do
    upload_asset_with_retry "$asset"
  done
  upload_asset_with_retry "$OUT_DIR/SHA256SUMS.txt"
  echo "[e2a] uploaded ${#ASSETS[@]} assets + SHA256SUMS.txt to https://github.com/${TARGET_REPO}/releases/tag/${TAG}"
}

# --- main --------------------------------------------------------------------

require_cmd node
snapshot_local_source

if [[ -z "$TAG" ]]; then
  TAG="electron-v$(json_value "$SOURCE_DIR/desktop-electron/package.json" ".version")"
fi
OUT_DIR="$ROOT/dist/e2a-release-${TAG}"
[[ -n "$ARTIFACT_DIR" ]] || ARTIFACT_DIR="$OUT_DIR"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" "$ARTIFACT_DIR"

echo "[e2a] release tag: $TAG"
echo "[e2a] release repo: $TARGET_REPO"

if [[ "$BUILD_APP_ASSETS" == "1" ]]; then
  build_electron_macos
fi
if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
  build_demo_zip_assets
fi

if [[ "${#ASSETS[@]}" -eq 0 ]]; then
  echo "No release assets were built; aborting" >&2
  exit 1
fi

write_checksums
notes="$(release_notes)"
upload_release "$notes"

echo "[e2a] done. artifacts:"
for asset in "${ASSETS[@]}"; do
  echo "[e2a]   - $asset"
done
echo "[e2a]   - $OUT_DIR/SHA256SUMS.txt"
