#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE_MODE="${R2A_SOURCE_MODE:-local}"
SOURCE_REPO_URL="${R2A_SOURCE_REPO_URL:-https://github.com/anton6202527/anime-armory.git}"
SOURCE_REF="${R2A_SOURCE_REF:-main}"
TARGET_REPO="${R2A_TARGET_REPO:-anton6202527/anime-armory}"
TARGET_REPO_URL="${R2A_TARGET_REPO_URL:-https://github.com/${TARGET_REPO}.git}"
ARTIFACT_DIR="${R2A_OUTPUT_DIR:-}"
README_LINK_MODE="${R2A_README_LINK_MODE:-auto}"
SIGNING_IDENTITY="${R2A_SIGNING_IDENTITY:-${APPLE_SIGNING_IDENTITY:--}}"
NOTARY_PROFILE="${R2A_NOTARY_KEYCHAIN_PROFILE:-${APPLE_NOTARY_KEYCHAIN_PROFILE:-}}"
REQUIRE_GATEKEEPER="${R2A_REQUIRE_GATEKEEPER:-0}"
R2A_GH_HTTP_TIMEOUT_VALUE="${R2A_GH_HTTP_TIMEOUT:-}"
if [[ "$R2A_GH_HTTP_TIMEOUT_VALUE" =~ ^[0-9]+$ ]]; then
  R2A_GH_HTTP_TIMEOUT_VALUE="${R2A_GH_HTTP_TIMEOUT_VALUE}s"
fi

RELEASE_ALL=0
BUILD_APP_ASSETS=1
BUILD_DEMO_ASSETS=0
UPLOAD=1
UPDATE_README=1
WORK=""
SOURCE_DIR=""
SOURCE_SHA=""
SOURCE_DIRTY="unknown"
OUT_DIR=""
TAG=""
ASSETS=()
DEMO_WORKS=()
CREATIVE_LINES=("写小说" "制漫剧" "画漫画" "写歌" "制MV" "拍广告")
FULL_REFERENCE_LINES=()
CREATION_MANUALS=("创作区/使用手册.md")
for line in "${CREATIVE_LINES[@]}"; do
  CREATION_MANUALS+=("创作区/$line/使用手册.md")
done

full_reference_lines() {
  local line
  for line in ${FULL_REFERENCE_LINES+"${FULL_REFERENCE_LINES[@]}"}; do
    [[ -n "$line" ]] || continue
    printf '%s\n' "$line"
  done
}

usage() {
  cat <<'EOF'
Usage:
  r2a [--all]
  r2a --demo-assets

Equivalent script entry:
  bash scripts/r2a_release.sh [--all] [--demo-assets] [--with-demo-assets] [--no-upload] [--no-readme] [--readme-link-mode auto|latest|tag] [--remote-source --source-ref ref]

Semantics:
  r2a
    Snapshot this local checkout, build only the macOS Apple Silicon DMG,
    upload it to anime-armory Releases as a release asset, and update only
    that DMG README link.
    Does not rebuild demo zip assets. The desktop app downloads existing demo
    zips from the latest Release on demand.
    Excludes private agent files, git metadata, dist/, build targets, and
    dependency caches. Does NOT commit release artifacts into git history and
    is not marked as latest.

  r2a --all
    Snapshot this local checkout, build the public all-release package set,
    upload it to anime-armory Releases as release assets, update corresponding
    README download links, and mark the release as latest. Does not rebuild
    demo zip assets. Desktop packages keep no full demo payloads; the app
    downloads existing demo zips from the latest Release on demand. The VSIX
    keeps only vscode-extension's own lightweight bundled seed work root.

  r2a --demo-assets
    Build and upload configured desktop demo works as separate Release zip
    assets only. Does not build app installers, does not update README download
    links, does not overwrite existing release notes, and does not mark the
    release latest. Missing series are skipped.

  r2a --all --with-demo-assets
    Legacy combined path: build all app installers and demo zip assets in one
    run. This is slower because large demo zips are packaged and uploaded too.

Release artifact names:
  AnimeArmory_macos_arm64.dmg
  AnimeArmory_windows.exe
  anime-armory.vsix
  AnimeArmory_demo_novel.zip
  AnimeArmory_demo_n2d.zip
  AnimeArmory_demo_comic.zip
  AnimeArmory_demo_song.zip
  AnimeArmory_demo_mv.zip
  AnimeArmory_demo_ad.zip

VSIX packaging intentionally does not copy selected desktop demo payloads.

Options:
  --demo-assets, --demos, --demo
                         Build/upload only demo zip assets.
  --with-demo-assets     Also build/upload demo zip assets in an app release.
  --apps-only, --no-demo-assets
                         Build/upload app installers only. This is the default.
  --remote-source        Build from a remote clone instead of this local checkout.
  --source-ref REF       Remote branch/tag to clone when --remote-source is used. Default: main.
  --source-repo URL      Remote source git URL when --remote-source is used. Default: anime-armory.
  --repo owner/name      Target GitHub repo. Default: anton6202527/anime-armory.
  --target-repo-url URL  Target git URL. Default derived from --repo.
  --readme-link-mode MODE
                         README download URLs: auto, latest, or tag. Default: auto
                         (latest for --all, fixed tag for single-asset r2a).
  --no-upload           Build locally only; do not upload release assets.
  --no-readme           Do not update README download links after upload.
  -h, --help            Show this help.

Environment:
  R2A_OUTPUT_DIR                 Optional local artifact output directory. Default: dist/r2a-release-<tag>.
  R2A_SOURCE_MODE=remote         Same as --remote-source.
  R2A_README_LINK_MODE           auto, latest, or tag.
  R2A_SIGNING_IDENTITY           macOS codesign identity. Default: ad-hoc "-".
  R2A_NOTARY_KEYCHAIN_PROFILE    Optional notarytool keychain profile.
  R2A_REQUIRE_GATEKEEPER=1       Fail if spctl rejects the macOS app.
  R2A_GH_HTTP_TIMEOUT            Optional GitHub CLI HTTP timeout. Unset by default.
  R2A_GH_RETRIES                 Retry count for GitHub metadata commands. Default: 10.
  R2A_UPLOAD_RETRIES             Retry count per uploaded asset. Default: 10.
  R2A_ASSUME_RELEASE_EXISTS=1    Recovery mode: skip the initial release existence lookup.
  R2A_SKIP_REMOTE_DIGEST_PRECHECK=1
                                  Recovery mode: upload without the pre-upload digest skip check.

Download URL policy:
  Fixed, reproducible tag URL:
    https://github.com/OWNER/REPO/releases/download/v0.1.0/AnimeArmory_macos_arm64.dmg
  Always-latest README URL:
    https://github.com/OWNER/REPO/releases/latest/download/AnimeArmory_macos_arm64.dmg
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release)
      shift
      ;;
    --demo-assets|--demos|--demo)
      BUILD_APP_ASSETS=0
      BUILD_DEMO_ASSETS=1
      shift
      ;;
    --with-demo-assets)
      BUILD_APP_ASSETS=1
      BUILD_DEMO_ASSETS=1
      shift
      ;;
    --apps-only|--no-demo-assets)
      BUILD_APP_ASSETS=1
      BUILD_DEMO_ASSETS=0
      shift
      ;;
    all|--all)
      RELEASE_ALL=1
      shift
      ;;
    --remote-source)
      SOURCE_MODE="remote"
      shift
      ;;
    --source-ref)
      SOURCE_REF="${2:?missing ref after --source-ref}"
      SOURCE_MODE="remote"
      shift 2
      ;;
    --source-repo)
      SOURCE_REPO_URL="${2:?missing URL after --source-repo}"
      SOURCE_MODE="remote"
      shift 2
      ;;
    --repo)
      TARGET_REPO="${2:?missing owner/name after --repo}"
      TARGET_REPO_URL="https://github.com/${TARGET_REPO}.git"
      shift 2
      ;;
    --target-repo-url)
      TARGET_REPO_URL="${2:?missing URL after --target-repo-url}"
      shift 2
      ;;
    --readme-link-mode)
      README_LINK_MODE="${2:?missing mode after --readme-link-mode}"
      shift 2
      ;;
    --no-upload)
      UPLOAD=0
      shift
      ;;
    --no-readme)
      UPDATE_README=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$SOURCE_MODE" in
  local|remote) ;;
  *)
    echo "Invalid R2A_SOURCE_MODE: $SOURCE_MODE (expected local or remote)" >&2
    exit 2
    ;;
esac

if [[ "$BUILD_APP_ASSETS" != "1" && "$RELEASE_ALL" == "1" ]]; then
  echo "r2a: --all only applies to app installer builds." >&2
  echo "r2a: use --demo-assets alone for demo zips, or --all --with-demo-assets for the legacy combined path." >&2
  exit 2
fi

case "$README_LINK_MODE" in
  auto|latest|tag) ;;
  *)
    echo "Invalid R2A_README_LINK_MODE: $README_LINK_MODE (expected auto, latest, or tag)" >&2
    exit 2
    ;;
esac

cleanup() {
  local status=$?
  if [[ -n "$WORK" && -d "$WORK" ]]; then
    if [[ "$status" -ne 0 && "${R2A_KEEP_WORKDIR_ON_FAILURE:-0}" == "1" ]]; then
      echo "[r2a] preserving failed workdir for debugging: $WORK" >&2
    else
      rm -rf "$WORK"
    fi
  fi
}
trap cleanup EXIT

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

make_workdir() {
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/r2a.XXXXXX")"
}

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
  --exclude='desktop/dist/'
  --exclude='desktop/src-tauri/target/'
  --exclude='vscode-extension/node_modules/'
)

copy_work_reference() {
  local src_root="$1"
  local dst_root="$2"
  local rel="$3"
  local src="$src_root/$rel"
  local dst="$dst_root/$rel"
  mkdir -p "$dst"
  if [[ -f "$src/_进度.md" ]]; then
    cp "$src/_进度.md" "$dst/_进度.md"
  fi
}

copy_work_payload() {
  local src_root="$1"
  local dst_root="$2"
  local rel="$3"
  local src="$src_root/$rel"
  local dst="$dst_root/$rel"
  mkdir -p "$(dirname "$dst")"
  node "$ROOT/tools/release-safety/demo_safety.cjs" copy "$src" "$dst"
}

copy_selected_demo_payloads() {
  local src_root="$1"
  local dst_root="$2"
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    copy_work_payload "$src_root" "$dst_root" "$demo"
  done
}

copy_selected_demo_references() {
  local src_root="$1"
  local dst_root="$2"
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    copy_work_reference "$src_root" "$dst_root" "$demo"
  done
}

copy_selected_demo_source() {
  local src_root="$1"
  local dst_root="$2"
  if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
    copy_selected_demo_payloads "$src_root" "$dst_root"
  else
    copy_selected_demo_references "$src_root" "$dst_root"
  fi
}

copy_full_reference_lines() {
  local src_root="$1"
  local dst_root="$2"
  local line work_path work rel
  while IFS= read -r line; do
    [[ -d "$src_root/创作区/$line" ]] || continue
    for work_path in "$src_root/创作区/$line"/*; do
      [[ -d "$work_path" ]] || continue
      work="$(basename "$work_path")"
      rel="创作区/$line/$work"
      copy_work_reference "$src_root" "$dst_root" "$rel"
    done
  done < <(full_reference_lines)
}

copy_creation_manuals() {
  local src_root="$1"
  local dst_root="$2"
  local rel
  for rel in "${CREATION_MANUALS[@]}"; do
    if [[ ! -f "$src_root/$rel" ]]; then
      echo "[r2a] missing creation manual: $rel" >&2
      exit 1
    fi
    mkdir -p "$dst_root/$(dirname "$rel")"
    cp -p "$src_root/$rel" "$dst_root/$rel"
  done
  echo "[r2a] copied ${#CREATION_MANUALS[@]} creation manuals into source snapshot"
}

snapshot_local_source() {
  require_cmd git
  require_cmd rsync
  require_cmd node
  make_workdir
  SOURCE_DIR="$WORK/source"
  mkdir -p "$SOURCE_DIR"

  select_demo_works "$ROOT"

  echo "[r2a] snapshotting local checkout: $ROOT"
  rsync -a --delete "${rsync_common_excludes[@]}" --exclude='创作区/' "$ROOT/" "$SOURCE_DIR/"
  copy_creation_manuals "$ROOT" "$SOURCE_DIR"
  copy_selected_demo_source "$ROOT" "$SOURCE_DIR"
  copy_full_reference_lines "$ROOT" "$SOURCE_DIR"

  SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")"
  if [[ -n "$(git -C "$ROOT" status --short 2>/dev/null || true)" ]]; then
    SOURCE_DIRTY="yes"
    echo "[r2a] local source has uncommitted or untracked changes; snapshot includes non-excluded working tree files"
  else
    SOURCE_DIRTY="no"
  fi
  echo "[r2a] source commit: ${SOURCE_SHA}"
}

clone_source() {
  require_cmd git
  make_workdir
  SOURCE_DIR="$WORK/source"
  echo "[r2a] cloning source: ${SOURCE_REPO_URL} (${SOURCE_REF})"
  if ! GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch "$SOURCE_REF" "$SOURCE_REPO_URL" "$SOURCE_DIR"; then
    echo "[r2a] shallow branch/tag clone failed; retrying full clone then checkout"
    GIT_LFS_SKIP_SMUDGE=1 git clone "$SOURCE_REPO_URL" "$SOURCE_DIR"
    git -C "$SOURCE_DIR" checkout "$SOURCE_REF"
  fi
  SOURCE_SHA="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
  SOURCE_DIRTY="no"
  pull_source_lfs
  echo "[r2a] source commit: ${SOURCE_SHA}"
}

pull_source_lfs() {
  if ! git -C "$SOURCE_DIR" lfs version >/dev/null 2>&1; then
    echo "[r2a] git-lfs not available; LFS pointer files remain unresolved"
    return
  fi
  local exclude="创作区/**,dist/**,desktop/dist/**,desktop/node_modules/**,desktop/src-tauri/target/**,vscode-extension/node_modules/**"
  echo "[r2a] pulling LFS files outside excluded paths"
  git -C "$SOURCE_DIR" lfs pull --exclude="$exclude"
}

clone_target() {
  local target_dir="$1"
  require_cmd git
  if GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none --sparse --branch main "$TARGET_REPO_URL" "$target_dir"; then
    git -C "$target_dir" sparse-checkout set README.md >/dev/null 2>&1 || true
  else
    echo "[r2a] target main clone failed; creating a fresh target checkout"
    rm -rf "$target_dir"
    mkdir -p "$target_dir"
    git -C "$target_dir" init -b main
    git -C "$target_dir" remote add origin "$TARGET_REPO_URL"
  fi
}

sanitize_private_agent_files() {
  local dir="$1"
  rm -rf \
    "$dir/.agents" \
    "$dir/.claude" \
    "$dir/.cline" \
    "$dir/.codex" \
    "$dir/.continue" \
    "$dir/.cursor" \
    "$dir/.gemini" \
    "$dir/.opencode" \
    "$dir/.roo" \
    "$dir/.windsurf" \
    "$dir/.aider.conf.yml" \
    "$dir/.aiderignore" \
    "$dir/.clinerules" \
    "$dir/.cursorrules" \
    "$dir/.windsurfrules" \
    "$dir/.github/copilot-instructions.md" \
    "$dir/.github/instructions" \
    "$dir/.github/prompts" \
    "$dir/CLAUDE.md" \
    "$dir/GEMINI.md" \
    "$dir/OPENCODE.md" \
    "$dir/QWEN.md"
  find "$dir" \
    \( -name '.agents' \
    -o -name '.claude' \
    -o -name '.cline' \
    -o -name '.codex' \
    -o -name '.continue' \
    -o -name '.cursor' \
    -o -name '.gemini' \
    -o -name '.opencode' \
    -o -name '.roo' \
    -o -name '.windsurf' \
    -o -name 'CLAUDE.md' \
    -o -name 'GEMINI.md' \
    -o -name 'OPENCODE.md' \
    -o -name 'QWEN.md' \) \
    -prune -exec rm -rf {} + 2>/dev/null || true
}

select_demo_works() {
  require_cmd node
  local source_root="${1:-$SOURCE_DIR}"
  local demo
  DEMO_WORKS=()
  while IFS= read -r demo; do
    [[ -n "$demo" ]] || continue
    case "$demo" in
      创作区/*/*) ;;
      *)
        echo "Invalid demo path selected: $demo" >&2
        exit 1
        ;;
    esac
    if [[ "$demo" == *".."* || ! -d "$source_root/$demo" ]]; then
      echo "Demo work is missing or unsafe: $demo" >&2
      exit 1
    fi
    DEMO_WORKS+=("$demo")
  done < <(node "$ROOT/scripts/r2a_select_demo.cjs" "$source_root")

  echo "[r2a] demo works:"
  if [[ "${#DEMO_WORKS[@]}" -eq 0 ]]; then
    echo "[r2a]   - none from 创作区 (outer skill demos may still be bundled)"
  else
    for demo in "${DEMO_WORKS[@]}"; do
      echo "[r2a]   - $demo"
    done
  fi
}

prepare_source_snapshot() {
  if [[ "$SOURCE_MODE" == "remote" ]]; then
    clone_source
    select_demo_works "$SOURCE_DIR"
    if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
      pull_selected_demo_lfs
    fi
  else
    snapshot_local_source
  fi
}

pull_selected_demo_lfs() {
  if ! git -C "$SOURCE_DIR" lfs version >/dev/null 2>&1; then
    echo "[r2a] git-lfs not available; selected demo LFS files remain unresolved"
    return
  fi
  local include=""
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    include+="${demo}/**,${demo},"
  done
  include="${include%,}"
  [[ -n "$include" ]] || return
  echo "[r2a] pulling selected demo LFS files"
  git -C "$SOURCE_DIR" lfs pull --include="$include"
}

demo_line_selected() {
  local line="$1"
  local demo rel_no_root demo_line
  for demo in "${DEMO_WORKS[@]}"; do
    rel_no_root="${demo#创作区/}"
    demo_line="${rel_no_root%%/*}"
    [[ "$demo_line" == "$line" ]] && return 0
  done
  return 1
}

demo_work_selected() {
  local rel="$1"
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    [[ "$demo" == "$rel" ]] && return 0
  done
  return 1
}

line_kept_as_reference() {
  local line="$1"
  local full_line
  while IFS= read -r full_line; do
    [[ "$full_line" == "$line" ]] && return 0
  done < <(full_reference_lines)
  return 1
}

prune_creation_to_demo_works() {
  local dir="$1"
  local line_path line work_path work rel
  [[ -d "$dir/创作区" ]] || return

  for line_path in "$dir/创作区"/*; do
    [[ -e "$line_path" ]] || continue
    line="$(basename "$line_path")"
    if [[ ! -d "$line_path" ]] || ! demo_line_selected "$line"; then
      if [[ -d "$line_path" ]] && line_kept_as_reference "$line"; then
        continue
      fi
      rm -rf "$line_path"
      continue
    fi
    if line_kept_as_reference "$line"; then
      continue
    fi
    for work_path in "$line_path"/*; do
      [[ -e "$work_path" ]] || continue
      work="$(basename "$work_path")"
      rel="创作区/$line/$work"
      demo_work_selected "$rel" || rm -rf "$work_path"
    done
  done
}

sanitize_tree_with_demos() {
  local dir="$1"
  sanitize_generated_artifacts "$dir"
  prune_creation_to_demo_works "$dir"
}

sanitize_generated_artifacts() {
  local dir="$1"
  sanitize_private_agent_files "$dir"
  rm -rf \
    "$dir/dist" \
    "$dir/desktop/dist" \
    "$dir/desktop/node_modules" \
    "$dir/desktop/src-tauri/target" \
    "$dir/vscode-extension/node_modules"
  find "$dir" \
    \( -name 'dist' \
    -o -name '.DS_Store' \
    -o -name '__pycache__' \
    -o -name '.pytest_cache' \
    -o -name '.mypy_cache' \
    -o -name '.ruff_cache' \
    -o -name '*.dmg' \
    -o -name '*.pkg' \
    -o -name '*.msi' \
    -o -name '*.exe' \
    -o -name '*.vsix' \) \
    -prune -exec rm -rf {} + 2>/dev/null || true
}

json_value() {
  node -p "JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'))${2}" "$1"
}

prepare_release_source() {
  prepare_source_snapshot
  sanitize_tree_with_demos "$SOURCE_DIR"

  local desktop_version
  local tauri_version
  desktop_version="$(json_value "$SOURCE_DIR/desktop/package.json" ".version")"
  tauri_version="$(json_value "$SOURCE_DIR/desktop/src-tauri/tauri.conf.json" ".version")"
  if [[ "$desktop_version" != "$tauri_version" ]]; then
    echo "Version mismatch: desktop/package.json=$desktop_version tauri.conf.json=$tauri_version" >&2
    exit 1
  fi

  TAG="${R2A_RELEASE_TAG:-v${desktop_version}}"
  OUT_DIR="$ROOT/dist/r2a-release-${TAG}"
  if [[ -z "$ARTIFACT_DIR" ]]; then
    ARTIFACT_DIR="$OUT_DIR"
  fi
  rm -rf "$OUT_DIR"
  mkdir -p "$OUT_DIR" "$ARTIFACT_DIR"

  echo "[r2a] release tag: $TAG"
  echo "[r2a] release repo: $TARGET_REPO"
  if [[ "$SOURCE_MODE" == "remote" ]]; then
    echo "[r2a] release source is remote clone: ${SOURCE_REPO_URL} (${SOURCE_REF})"
  else
    echo "[r2a] release source is local checkout snapshot; release artifacts are uploaded to GitHub Release assets"
  fi
  if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
    echo "[r2a] source tree sanitized before build: selected demo payloads kept for demo zip assets"
  else
    echo "[r2a] source tree sanitized before build: selected demo references kept for app catalog; full payloads are not copied"
  fi
}

install_node_deps() {
  local dir="$1"
  if [[ -f "$dir/package-lock.json" ]]; then
    (cd "$dir" && npm ci)
  else
    (cd "$dir" && npm install)
  fi
}

latest_file() {
  local dir="$1"
  local glob="$2"
  if [[ ! -d "$dir" ]]; then
    return 0
  fi
  find "$dir" -maxdepth 1 -type f -name "$glob" -exec sh -c '
    for f do
      mt="$(stat -f "%m" "$f" 2>/dev/null || stat -c "%Y" "$f" 2>/dev/null || echo 0)"
      printf "%s\t%s\n" "$mt" "$f"
    done
  ' sh {} + 2>/dev/null | sort -nr | head -1 | cut -f2-
}

sign_macos_app() {
  local app_path="$1"
  if [[ ! -d "$app_path" ]]; then
    echo "Missing macOS app bundle: $app_path" >&2
    exit 1
  fi
  echo "[r2a] signing macOS app with identity: $SIGNING_IDENTITY"
  codesign --force --deep --options runtime --sign "$SIGNING_IDENTITY" "$app_path"
  codesign --verify --deep --strict --verbose=4 "$app_path"
}

make_macos_dmg() {
  local app_path="$1"
  local dmg_out="$2"
  local stage
  stage="$(mktemp -d "${TMPDIR:-/tmp}/r2a-dmg-stage.XXXXXX")"
  ditto "$app_path" "$stage/AnimeArmory.app"
  ln -s /Applications "$stage/Applications"
  rm -f "$dmg_out"
  hdiutil create -volname "AnimeArmory" -srcfolder "$stage" -format UDZO -ov "$dmg_out"
  rm -rf "$stage"
}

notarize_dmg_if_configured() {
  local dmg="$1"
  if [[ -z "$NOTARY_PROFILE" ]]; then
    echo "[r2a] notarization skipped (R2A_NOTARY_KEYCHAIN_PROFILE not set)"
    return
  fi
  echo "[r2a] submitting DMG to Apple notarization profile: $NOTARY_PROFILE"
  xcrun notarytool submit "$dmg" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$dmg"
  xcrun stapler validate "$dmg"
}

validate_macos_dmg() {
  local dmg="$1"
  local stem
  stem="$(basename "$dmg" | tr -c '[:alnum:]_.-' '_')"
  local mount_dir="$OUT_DIR/mount-check-$stem"
  rm -rf "$mount_dir"
  mkdir -p "$mount_dir"
  echo "[r2a] validating DMG: $(basename "$dmg")"
  hdiutil verify "$dmg"
  hdiutil attach "$dmg" -mountpoint "$mount_dir" -nobrowse -readonly >/dev/null
  local app_path="$mount_dir/AnimeArmory.app"
  if [[ ! -d "$app_path" ]]; then
    echo "DMG validation failed: AnimeArmory.app not found" >&2
    hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
    exit 1
  fi
  if ! codesign --verify --deep --strict --verbose=4 "$app_path"; then
    hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
    exit 1
  fi
  if spctl -a -vv -t exec "$app_path" > "$OUT_DIR/spctl-macos.txt" 2>&1; then
    echo "[r2a] Gatekeeper check accepted"
  else
    cat "$OUT_DIR/spctl-macos.txt" >&2
    if [[ "$REQUIRE_GATEKEEPER" == "1" ]]; then
      echo "Gatekeeper rejected the app. Configure Developer ID signing + notarization, or unset R2A_REQUIRE_GATEKEEPER." >&2
      hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
      exit 1
    fi
    echo "[r2a] Gatekeeper rejected this non-notarized build; continuing because R2A_REQUIRE_GATEKEEPER!=1" >&2
  fi
  hdiutil detach "$mount_dir" >/dev/null
}

validate_zip() {
  local path="$1"
  echo "[r2a] validating zip container: $(basename "$path")"
  unzip -tqq "$path"
}

validate_nonempty() {
  local path="$1"
  if [[ ! -s "$path" ]]; then
    echo "Built artifact is missing or empty: $path" >&2
    exit 1
  fi
}

demo_line_key() {
  case "$1" in
    "写小说") echo "novel" ;;
    "制漫剧") echo "n2d" ;;
    "画漫画") echo "comic" ;;
    "写歌") echo "song" ;;
    "制MV") echo "mv" ;;
    "拍广告") echo "ad" ;;
    *)
      echo "Unknown creative line for demo asset: $1" >&2
      exit 1
      ;;
  esac
}

build_demo_zip_assets() {
  require_cmd zip
  local demo rest line key asset stage
  for demo in "${DEMO_WORKS[@]}"; do
    rest="${demo#创作区/}"
    line="${rest%%/*}"
    key="$(demo_line_key "$line")"
    asset="$ARTIFACT_DIR/AnimeArmory_demo_${key}.zip"
    stage="$(mktemp -d "${TMPDIR:-/tmp}/r2a-demo-${key}.XXXXXX")"
    copy_work_payload "$SOURCE_DIR" "$stage" "$demo"
    prune_demo_asset_stage "$stage/$demo" "$line" "$key"
    rm -f "$asset"
    (
      cd "$stage"
      find "创作区" -exec touch -h -t 202001010000 {} + 2>/dev/null || find "创作区" -exec touch -t 202001010000 {} +
      COPYFILE_DISABLE=1 zip -X -qr "$asset" "创作区"
    )
    rm -rf "$stage"
    validate_zip "$asset"
    ASSETS+=("$asset")
  done
}

prune_demo_asset_stage() {
  local work_dir="$1"
  local line="$2"
  local key="$3"
  [[ -d "$work_dir" ]] || return
  case "$key" in
    n2d)
      echo "[r2a] slimming n2d demo asset to first-episode media payload"
      keep_only_named_child_dirs "$work_dir/出图" "第1集"
      keep_only_named_child_dirs "$work_dir/合成" "第1集"
      find "$work_dir/合成/第1集/配音" -maxdepth 1 -type f -name 'line_*.wav' -delete 2>/dev/null || true
      ;;
    *)
      ;;
  esac
  : "$line"
}

keep_only_named_child_dirs() {
  local dir="$1"
  shift
  [[ -d "$dir" ]] || return
  local child name keep wanted
  for child in "$dir"/*; do
    [[ -e "$child" ]] || continue
    [[ -d "$child" ]] || continue
    name="$(basename "$child")"
    keep=0
    for wanted in "$@"; do
      if [[ "$name" == "$wanted" ]]; then
        keep=1
        break
      fi
    done
    if [[ "$keep" != "1" ]]; then
      rm -rf "$child"
    fi
  done
}

require_assets() {
  if [[ "${#ASSETS[@]}" -eq 0 ]]; then
    echo "No release assets were built; aborting release steps" >&2
    exit 1
  fi
}

format_asset_lines() {
  require_assets
  local asset
  for asset in "${ASSETS[@]}"; do
    printf -- "- %s\n" "$(basename "$asset")"
  done
}

format_demo_lines() {
  if [[ "${#DEMO_WORKS[@]}" -eq 0 ]]; then
    printf -- "- none from 创作区\n"
    return
  fi
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    printf -- "- %s\n" "$demo"
  done
}

format_full_reference_lines() {
  local line line_path work_path work rel found
  found=0
  while IFS= read -r line; do
    line_path="$SOURCE_DIR/创作区/$line"
    [[ -d "$line_path" ]] || continue
    for work_path in "$line_path"/*; do
      [[ -d "$work_path" ]] || continue
      work="$(basename "$work_path")"
      rel="创作区/$line/$work"
      demo_work_selected "$rel" && continue
      printf -- "- %s\n" "$rel"
      found=1
    done
  done < <(full_reference_lines)
  [[ "$found" == "1" ]] || printf -- "- none\n"
}

format_source_lines() {
  if [[ "$SOURCE_MODE" == "remote" ]]; then
    printf -- "- Source mode: remote clone\n"
    printf -- "- Source repo: %s\n" "$SOURCE_REPO_URL"
    printf -- "- Source ref: %s\n" "$SOURCE_REF"
    printf -- "- Source commit: %s\n" "$SOURCE_SHA"
    return
  fi
  printf -- "- Source mode: local checkout snapshot\n"
  printf -- "- Source path: %s\n" "$ROOT"
  printf -- "- Source commit: %s\n" "$SOURCE_SHA"
  printf -- "- Working tree dirty: %s\n" "$SOURCE_DIRTY"
}

format_asset_download_lines() {
  require_assets
  local asset
  for asset in "${ASSETS[@]}"; do
    local base
    base="$(basename "$asset")"
    printf -- "- https://github.com/%s/releases/download/%s/%s\n" "$TARGET_REPO" "$TAG" "$base"
  done
}

package_set_label() {
  if [[ "$BUILD_APP_ASSETS" == "1" && "$BUILD_DEMO_ASSETS" == "1" ]]; then
    if [[ "$RELEASE_ALL" == "1" ]]; then
      echo "macOS Apple Silicon DMG + Windows EXE + VSIX + demo zip assets"
    else
      echo "macOS Apple Silicon DMG + demo zip assets"
    fi
    return
  fi
  if [[ "$BUILD_APP_ASSETS" == "1" ]]; then
    if [[ "$RELEASE_ALL" == "1" ]]; then
      echo "macOS Apple Silicon DMG + Windows EXE + VSIX"
    else
      echo "macOS Apple Silicon DMG only"
    fi
    return
  fi
  echo "demo zip assets only"
}

demo_asset_mode_line() {
  if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
    echo "Demo zip assets: built and uploaded in this run."
  else
    echo "Demo zip assets: not rebuilt in this run; existing Release demo assets are retained."
  fi
}

vsix_note_line() {
  if [[ "$BUILD_APP_ASSETS" == "1" && "$RELEASE_ALL" == "1" ]]; then
    echo "VSIX seed work root: existing vscode-extension/创作区 only; selected desktop demo payloads not copied."
  elif [[ "$BUILD_APP_ASSETS" == "1" ]]; then
    echo "VSIX: not built in this release."
  else
    echo "VSIX: not built in demo-assets release."
  fi
}

build_macos_assets() {
  local target="$1"
  local dmg_name="$2"
  local app_src="$SOURCE_DIR/desktop/src-tauri/target/$target/release/bundle/macos/AnimeArmory.app"
  local featured_works
  featured_works="$(printf '%s\n' "${DEMO_WORKS[@]}")"

  (
    cd "$SOURCE_DIR/desktop"
    R2A_INCLUDE_DEMOS=0 \
    R2A_FEATURED_WORKS="$featured_works" \
      npm run tauri -- build --target "$target" --bundles app --ci
  )

  local artifact_dmg="$ARTIFACT_DIR/$dmg_name"
  sign_macos_app "$app_src"
  make_macos_dmg "$app_src" "$artifact_dmg"
  notarize_dmg_if_configured "$artifact_dmg"
  validate_macos_dmg "$artifact_dmg"
  ASSETS+=("$artifact_dmg")
}

build_windows_exe() {
  require_cmd makensis
  local featured_works
  featured_works="$(printf '%s\n' "${DEMO_WORKS[@]}")"
  (
    cd "$SOURCE_DIR/desktop"
    R2A_INCLUDE_DEMOS=0 \
    R2A_FEATURED_WORKS="$featured_works" \
      npm run tauri -- build --target x86_64-pc-windows-gnu --bundles nsis --ci
  )
  local exe_src
  exe_src="$(latest_file "$SOURCE_DIR/desktop/src-tauri/target/x86_64-pc-windows-gnu/release/bundle/nsis" '*.exe')"
  if [[ -z "$exe_src" || ! -f "$exe_src" ]]; then
    echo "Could not locate built Windows installer" >&2
    exit 1
  fi
  local artifact_exe="$ARTIFACT_DIR/AnimeArmory_windows.exe"
  mv "$exe_src" "$artifact_exe"
  validate_nonempty "$artifact_exe"
  ASSETS+=("$artifact_exe")
}

prepare_vsix_seed_work_root() {
  local extension_dir="$SOURCE_DIR/vscode-extension"
  local safety="$SOURCE_DIR/tools/release-safety/demo_safety.cjs"
  local line
  local seed_root="$extension_dir/创作区"

  for line in "${CREATIVE_LINES[@]}"; do
    mkdir -p "$seed_root/$line"
  done
  node "$safety" scan "$seed_root"
  echo "[r2a] VSIX keeps vscode-extension/创作区 only; selected desktop demo payloads are not copied"
}

build_vsix() {
  prepare_vsix_seed_work_root
  (
    cd "$SOURCE_DIR/vscode-extension"
    rm -f *.vsix
    install_node_deps "$SOURCE_DIR/vscode-extension"
    npm run sync-assets
    npx --yes @vscode/vsce package --allow-missing-repository --out anime-armory.vsix
  )
  local vsix_src="$SOURCE_DIR/vscode-extension/anime-armory.vsix"
  if [[ ! -f "$vsix_src" ]]; then
    echo "Could not locate built VSIX" >&2
    exit 1
  fi
  local artifact_vsix="$ARTIFACT_DIR/anime-armory.vsix"
  mv "$vsix_src" "$artifact_vsix"
  validate_zip "$artifact_vsix"
  ASSETS+=("$artifact_vsix")
}

write_checksums() {
  require_assets
  : > "$OUT_DIR/SHA256SUMS.txt"
  local asset
  for asset in "${ASSETS[@]}"; do
    local base
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
  cat > "$notes" <<EOF
# AnimeArmory ${TAG}

$([[ "$UPLOAD" == "1" ]] && echo "Built locally and uploaded as GitHub Release assets." || echo "Built locally; upload disabled.")

$(format_source_lines)
- Release repo: https://github.com/${TARGET_REPO}
- Release artifacts committed to git history: no
- Package set: $(package_set_label)
- $(demo_asset_mode_line)

Configured demo works for release download:
$(format_demo_lines)

Desktop non-demo work references:
$(format_full_reference_lines)

$(vsix_note_line)

Assets:
$(format_asset_lines)

Fixed tag download URLs:
$(format_asset_download_lines)
EOF
  echo "$notes"
}

upload_release() {
  if [[ "$UPLOAD" != "1" ]]; then
    return
  fi
  require_assets
  require_cmd gh
  local notes="$1"
  local latest_args=(--latest=false)
  if [[ "$BUILD_APP_ASSETS" == "1" && "$RELEASE_ALL" == "1" ]]; then
    latest_args=(--latest)
  fi
  if release_exists; then
    if [[ "$BUILD_APP_ASSETS" == "1" && "$RELEASE_ALL" == "1" ]]; then
      gh_retry "edit release ${TAG}" gh release edit "$TAG" \
        --repo "$TARGET_REPO" \
        --title "AnimeArmory ${TAG}" \
        --notes-file "$notes" \
        --latest
    elif [[ "$BUILD_APP_ASSETS" == "1" ]]; then
      gh_retry "edit release ${TAG}" gh release edit "$TAG" \
        --repo "$TARGET_REPO" \
        --title "AnimeArmory ${TAG}" \
        --notes-file "$notes"
    else
      echo "[r2a] demo-assets release: keeping existing release notes for ${TAG}"
    fi
  else
    gh_retry "create release ${TAG}" gh release create "$TAG" \
      --repo "$TARGET_REPO" \
      --title "AnimeArmory ${TAG}" \
      --notes-file "$notes" \
      "${latest_args[@]}"
  fi

  upload_assets_sequentially
  write_remote_checksums
  upload_asset_with_retry "$OUT_DIR/SHA256SUMS.txt"
}

run_gh() {
  if [[ -n "$R2A_GH_HTTP_TIMEOUT_VALUE" ]]; then
    GH_HTTP_TIMEOUT="$R2A_GH_HTTP_TIMEOUT_VALUE" "$@"
  else
    "$@"
  fi
}

gh_retry() {
  local description="$1"
  shift
  local max_attempts="${R2A_GH_RETRIES:-10}"
  local attempt=1
  local status=1
  while (( attempt <= max_attempts )); do
    if run_gh "$@"; then
      return 0
    fi
    status=$?
    [[ "$status" -ne 0 ]] || status=1
    echo "[r2a] GitHub command failed: ${description} (attempt ${attempt}/${max_attempts})" >&2
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      sleep $((attempt * 5))
    fi
  done
  return "$status"
}

release_exists() {
  local output max_attempts attempt status
  if [[ "${R2A_ASSUME_RELEASE_EXISTS:-0}" == "1" ]]; then
    echo "[r2a] assuming GitHub release exists for ${TAG} (R2A_ASSUME_RELEASE_EXISTS=1)"
    return 0
  fi
  max_attempts="${R2A_GH_RETRIES:-10}"
  attempt=1
  status=1
  while (( attempt <= max_attempts )); do
    if output="$(run_gh gh release view "$TAG" --repo "$TARGET_REPO" 2>&1 >/dev/null)"; then
      return 0
    fi
    status=$?
    [[ "$status" -ne 0 ]] || status=1
    if printf '%s' "$output" | grep -Eiq 'not found|could not resolve to a Release'; then
      return 1
    fi
    echo "[r2a] GitHub release lookup failed for ${TAG} (attempt ${attempt}/${max_attempts}): ${output}" >&2
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      sleep $((attempt * 5))
    fi
  done
  echo "Failed to check GitHub release ${TAG}: ${output}" >&2
  exit "$status"
}

upload_assets_sequentially() {
  require_assets
  local asset
  for asset in "${ASSETS[@]}"; do
    upload_asset_with_retry "$asset"
  done
}

asset_sha256() {
  local path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    sha256sum "$path" | awk '{print $1}'
  fi
}

remote_asset_sha256() {
  require_cmd python3
  local name="$1"
  local assets_json="$OUT_DIR/release-assets-upload.json"
  gh_retry "read release assets for ${name}" gh release view "$TAG" --repo "$TARGET_REPO" --json assets > "$assets_json"
  python3 - "$assets_json" "$name" <<'PY'
import json
import sys
from pathlib import Path

assets_path = Path(sys.argv[1])
name = sys.argv[2]
data = json.loads(assets_path.read_text(encoding="utf-8"))
for asset in data.get("assets", []):
    if asset.get("name") != name:
        continue
    if asset.get("state") and asset.get("state") != "uploaded":
        continue
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        print(digest.removeprefix("sha256:"))
    break
PY
}

upload_asset_with_retry() {
  local asset="$1"
  local base local_digest remote_digest attempt max_attempts wait_seconds
  base="$(basename "$asset")"
  local_digest="$(asset_sha256 "$asset")"
  if [[ "${R2A_SKIP_REMOTE_DIGEST_PRECHECK:-0}" == "1" ]]; then
    remote_digest=""
  else
    remote_digest="$(remote_asset_sha256 "$base" || true)"
  fi
  if [[ -n "$remote_digest" && "$remote_digest" == "$local_digest" ]]; then
    echo "[r2a] asset already up to date: $base"
    return
  fi

  max_attempts="${R2A_UPLOAD_RETRIES:-10}"
  attempt=1
  while (( attempt <= max_attempts )); do
    echo "[r2a] uploading asset: $base (attempt ${attempt}/${max_attempts})"
    if run_gh gh release upload "$TAG" "$asset" \
      --repo "$TARGET_REPO" \
      --clobber; then
      wait_seconds=3
      for _ in 1 2 3; do
        remote_digest="$(remote_asset_sha256 "$base" || true)"
        if [[ "$remote_digest" == "$local_digest" ]]; then
          return
        fi
        sleep "$wait_seconds"
      done
      echo "[r2a] uploaded $base but remote digest did not match yet; retrying" >&2
    else
      echo "[r2a] upload failed for $base; retrying if attempts remain" >&2
    fi
    attempt=$((attempt + 1))
    if (( attempt <= max_attempts )); then
      sleep $((attempt * 10))
    fi
  done

  echo "Failed to upload verified release asset after ${max_attempts} attempts: $base" >&2
  exit 1
}

write_remote_checksums() {
  require_cmd gh
  require_cmd python3
  local assets_json="$OUT_DIR/release-assets.json"
  gh_retry "read release assets for checksums" gh release view "$TAG" --repo "$TARGET_REPO" --json assets > "$assets_json"
  python3 - "$assets_json" "$OUT_DIR/SHA256SUMS.txt" <<'PY'
import json
import sys
from pathlib import Path

assets_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
data = json.loads(assets_path.read_text(encoding="utf-8"))
rows = []
missing = []
for asset in data.get("assets", []):
    name = asset.get("name") or ""
    if not name or name == "SHA256SUMS.txt":
        continue
    if asset.get("state") and asset.get("state") != "uploaded":
        continue
    digest = asset.get("digest") or ""
    if not digest.startswith("sha256:"):
        missing.append(name)
        continue
    rows.append((name, digest.removeprefix("sha256:")))
if missing:
    raise SystemExit("missing sha256 digest for release asset(s): " + ", ".join(sorted(missing)))
rows.sort(key=lambda item: item[0])
out_path.write_text("".join(f"{digest}  {name}\n" for name, digest in rows), encoding="utf-8")
PY
}

effective_readme_link_mode() {
  if [[ "$README_LINK_MODE" == "auto" ]]; then
    if [[ "$BUILD_APP_ASSETS" == "1" && "$RELEASE_ALL" == "1" ]]; then
      echo "latest"
    else
      echo "tag"
    fi
    return
  fi
  echo "$README_LINK_MODE"
}

update_target_readme_links() {
  if [[ "$UPLOAD" != "1" || "$UPDATE_README" != "1" ]]; then
    return
  fi
  if [[ "$BUILD_APP_ASSETS" != "1" ]]; then
    return
  fi
  require_assets
  require_cmd python3

  local readme_dir="$WORK/readme-target"
  clone_target "$readme_dir"
  if [[ ! -f "$readme_dir/README.md" ]]; then
    echo "[r2a] target README.md not found; skip README link update"
    return
  fi

  local link_mode
  link_mode="$(effective_readme_link_mode)"
  if [[ "$link_mode" == "latest" && "$RELEASE_ALL" != "1" ]]; then
    echo "[r2a] README latest links requested for a single-asset release; ensure this tag is the latest release and has every linked asset" >&2
  fi

  python3 - "$readme_dir/README.md" "$TARGET_REPO" "$TAG" "$link_mode" "${ASSETS[@]}" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
repo = sys.argv[2]
tag = sys.argv[3]
mode = sys.argv[4]
assets = [Path(x).name for x in sys.argv[5:]]
text = path.read_text(encoding="utf-8")
for name in assets:
    if mode == "latest":
        target = f"https://github.com/{repo}/releases/latest/download/{name}"
    else:
        target = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    pattern = re.compile(
        r"https://github\.com/[^)\s]+/releases/(?:latest/download|download/[^/\s)]+)/"
        + re.escape(name)
    )
    text = pattern.sub(target, text)
path.write_text(text, encoding="utf-8")
PY

  git -C "$readme_dir" config user.name "${GIT_AUTHOR_NAME:-r2a}"
  git -C "$readme_dir" config user.email "${GIT_AUTHOR_EMAIL:-r2a@local}"
  git -C "$readme_dir" add README.md
  if git -C "$readme_dir" diff --cached --quiet; then
    echo "[r2a] README download links already up to date"
    return
  fi
  git -C "$readme_dir" commit -m "docs: update release download links"
  git -C "$readme_dir" push origin HEAD:main
  echo "[r2a] README download links updated in ${TARGET_REPO} using ${link_mode} URLs"
}

run_release() {
  require_cmd node
  require_cmd unzip
  if [[ "$BUILD_APP_ASSETS" == "1" ]]; then
    require_cmd npm
    require_cmd hdiutil
    require_cmd codesign
    require_cmd ditto
  fi
  if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
    require_cmd zip
  fi

  prepare_release_source
  if [[ "$BUILD_APP_ASSETS" == "1" ]]; then
    install_node_deps "$SOURCE_DIR/desktop"
  fi

  rm -f \
    "$ARTIFACT_DIR/AnimeArmory_macos_arm64.dmg" \
    "$ARTIFACT_DIR/AnimeArmory_windows.exe" \
    "$ARTIFACT_DIR/anime-armory.vsix" \
    "$ARTIFACT_DIR"/AnimeArmory_demo_*.zip

  if [[ "$BUILD_APP_ASSETS" == "1" ]]; then
    build_macos_assets "aarch64-apple-darwin" "AnimeArmory_macos_arm64.dmg"
    if [[ "$RELEASE_ALL" == "1" ]]; then
      build_windows_exe
      build_vsix
    fi
  fi

  if [[ "$BUILD_DEMO_ASSETS" == "1" ]]; then
    build_demo_zip_assets
  fi

  write_checksums
  local notes
  notes="$(release_notes)"
  upload_release "$notes"
  update_target_readme_links

  for asset in "${ASSETS[@]}"; do
    echo "[r2a] artifact: $asset"
  done
  if [[ "$UPLOAD" == "1" ]]; then
    echo "[r2a] release: https://github.com/${TARGET_REPO}/releases/tag/${TAG}"
  else
    echo "[r2a] upload disabled; local artifacts only"
  fi
}

cd "$ROOT"
run_release
