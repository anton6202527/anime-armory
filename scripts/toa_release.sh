#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE_REPO_URL="${TOA_SOURCE_REPO_URL:-https://github.com/anton6202527/anime-arsenal.git}"
SOURCE_REF="${TOA_SOURCE_REF:-main}"
TARGET_REPO="${TOA_TARGET_REPO:-anton6202527/anime-armory}"
TARGET_REPO_URL="${TOA_TARGET_REPO_URL:-https://github.com/${TARGET_REPO}.git}"
ARTIFACT_DIR="${TOA_OUTPUT_DIR:-}"
SIGNING_IDENTITY="${TOA_SIGNING_IDENTITY:-${APPLE_SIGNING_IDENTITY:--}}"
NOTARY_PROFILE="${TOA_NOTARY_KEYCHAIN_PROFILE:-${APPLE_NOTARY_KEYCHAIN_PROFILE:-}}"
REQUIRE_GATEKEEPER="${TOA_REQUIRE_GATEKEEPER:-0}"

MODE="mirror"
RELEASE_ALL=0
INCLUDE_DEMOS=0
UPLOAD=1
UPDATE_README=1
WORK=""
SOURCE_DIR=""
SOURCE_SHA=""
OUT_DIR=""
TAG=""
ASSETS=()
DEMO_WORKS=()
CREATIVE_LINES=("写小说" "制漫剧" "写歌" "制MV" "拍广告")

usage() {
  cat <<'EOF'
Usage:
  toa [--demo]
  toa --release
  toa --release all

Equivalent script entry:
  bash scripts/toa_release.sh [--demo] [--release [all]] [--no-upload] [--no-readme]

Semantics:
  toa
    Clone https://github.com/anton6202527/anime-arsenal remote code and sync it
    to https://github.com/anton6202527/anime-armory main. Excludes 创作区/,
    private agent files, dist/, build outputs, node_modules, and
    installer/release artifacts.

  toa --demo
    Same source mirror as toa, but keeps each creative line's most-complete
    demo from 创作区/ and excludes private agent files plus the rest of 创作区/.

  toa --release
    Clone anime-arsenal remote code, build only the macOS Apple Silicon DMG,
    upload it to anime-armory Releases, and update only that DMG README link.
    Keeps each creative line's most-complete demo from 创作区/, excludes the
    rest plus private agent files and dist/.
    Does NOT sync source code to anime-armory and is not marked as latest.

  toa --release all
    Clone anime-arsenal remote code, build the public all-release package set,
    upload it to anime-armory Releases, update corresponding README download
    links, and mark the release as latest. Keeps each creative line's
    most-complete demo from 创作区/, excludes the rest plus private agent files
    and dist/. Does NOT sync source code to anime-armory.

Release artifact names:
  AnimeArsenal_macos_arm64.dmg
  AnimeArsenal_windows.exe
  anime-armory.vsix

Options:
  --demo                 Include selected demo works when mirroring source code.
  --source-ref REF       Source branch/tag to clone from anime-arsenal. Default: main.
  --source-repo URL      Source git URL. Default: anime-arsenal.
  --repo owner/name      Target GitHub repo. Default: anton6202527/anime-armory.
  --target-repo-url URL  Target git URL. Default derived from --repo.
  --no-upload           Build locally only; do not upload release assets.
  --no-readme           Do not update README download links after upload.
  -h, --help            Show this help.

Environment:
  TOA_OUTPUT_DIR                 Optional local artifact output directory. Default: dist/toa-release-<tag>.
  TOA_SIGNING_IDENTITY           macOS codesign identity. Default: ad-hoc "-".
  TOA_NOTARY_KEYCHAIN_PROFILE    Optional notarytool keychain profile.
  TOA_REQUIRE_GATEKEEPER=1       Fail if spctl rejects the macOS app.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release)
      MODE="release"
      shift
      if [[ "${1:-}" == "all" ]]; then
        RELEASE_ALL=1
        shift
      fi
      ;;
    all)
      if [[ "$MODE" == "release" ]]; then
        RELEASE_ALL=1
        shift
      else
        echo "Unexpected argument: all (use: toa --release all)" >&2
        usage >&2
        exit 2
      fi
      ;;
    --demo)
      INCLUDE_DEMOS=1
      shift
      ;;
    --source-ref)
      SOURCE_REF="${2:?missing ref after --source-ref}"
      shift 2
      ;;
    --source-repo)
      SOURCE_REPO_URL="${2:?missing URL after --source-repo}"
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

cleanup() {
  if [[ -n "$WORK" && -d "$WORK" ]]; then
    rm -rf "$WORK"
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
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/toa.XXXXXX")"
}

clone_source() {
  require_cmd git
  make_workdir
  SOURCE_DIR="$WORK/anime-arsenal"
  echo "[toa] cloning source: ${SOURCE_REPO_URL} (${SOURCE_REF})"
  if ! GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch "$SOURCE_REF" "$SOURCE_REPO_URL" "$SOURCE_DIR"; then
    echo "[toa] shallow branch/tag clone failed; retrying full clone then checkout"
    GIT_LFS_SKIP_SMUDGE=1 git clone "$SOURCE_REPO_URL" "$SOURCE_DIR"
    git -C "$SOURCE_DIR" checkout "$SOURCE_REF"
  fi
  SOURCE_SHA="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
  pull_source_lfs
  echo "[toa] source commit: ${SOURCE_SHA}"
}

pull_source_lfs() {
  if ! git -C "$SOURCE_DIR" lfs version >/dev/null 2>&1; then
    echo "[toa] git-lfs not available; LFS pointer files remain unresolved"
    return
  fi
  local exclude="创作区/**,dist/**,desktop/dist/**,desktop/node_modules/**,desktop/src-tauri/target/**,vscode-extension/node_modules/**"
  echo "[toa] pulling LFS files outside excluded paths"
  git -C "$SOURCE_DIR" lfs pull --exclude="$exclude"
}

clone_target() {
  local target_dir="$1"
  require_cmd git
  if ! git clone --depth 1 --branch main "$TARGET_REPO_URL" "$target_dir"; then
    echo "[toa] target main clone failed; creating a fresh target checkout"
    mkdir -p "$target_dir"
    git -C "$target_dir" init -b main
    git -C "$target_dir" remote add origin "$TARGET_REPO_URL"
  fi
}

sanitize_tree() {
  local dir="$1"
  rm -rf "$dir/创作区"
  sanitize_generated_artifacts "$dir"
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
    if [[ "$demo" == *".."* || ! -d "$SOURCE_DIR/$demo" ]]; then
      echo "Demo work is missing or unsafe: $demo" >&2
      exit 1
    fi
    DEMO_WORKS+=("$demo")
  done < <(node "$ROOT/scripts/toa_select_demo.cjs" "$SOURCE_DIR")

  if [[ "${#DEMO_WORKS[@]}" -eq 0 ]]; then
    echo "No demo works found under $SOURCE_DIR/创作区" >&2
    exit 1
  fi

  echo "[toa] demo works:"
  for demo in "${DEMO_WORKS[@]}"; do
    echo "[toa]   - $demo"
  done
}

pull_demo_lfs() {
  if ! git -C "$SOURCE_DIR" lfs version >/dev/null 2>&1; then
    echo "[toa] git-lfs not available; demo LFS pointer files may remain unresolved"
    return
  fi
  local includes=()
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    includes+=("${demo}/**")
  done
  local include_arg
  include_arg="$(IFS=,; echo "${includes[*]}")"
  echo "[toa] pulling LFS files for demo works"
  git -C "$SOURCE_DIR" lfs pull --include="$include_arg"
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

prune_creation_to_demo_works() {
  local dir="$1"
  local line_path line work_path work rel
  [[ -d "$dir/创作区" ]] || return

  for line_path in "$dir/创作区"/*; do
    [[ -e "$line_path" ]] || continue
    line="$(basename "$line_path")"
    if [[ ! -d "$line_path" ]] || ! demo_line_selected "$line"; then
      rm -rf "$line_path"
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

sync_remote_code_to_target() {
  require_cmd rsync
  clone_source
  if [[ "$INCLUDE_DEMOS" == "1" ]]; then
    select_demo_works
    pull_demo_lfs
    sanitize_tree_with_demos "$SOURCE_DIR"
  else
    sanitize_tree "$SOURCE_DIR"
  fi

  local target_dir="$WORK/anime-armory"
  clone_target "$target_dir"

  echo "[toa] syncing remote source code to ${TARGET_REPO_URL}"
  if [[ "$INCLUDE_DEMOS" == "1" ]]; then
    echo "[toa] included demos: ${DEMO_WORKS[*]}"
    echo "[toa] excluded: private agent files, non-demo 创作区/, dist/, build outputs, node_modules, installer artifacts"
  else
    echo "[toa] excluded: private agent files, 创作区/, dist/, build outputs, node_modules, installer artifacts"
  fi
  find "$target_dir" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  rsync -a --exclude='.git/' "$SOURCE_DIR/" "$target_dir/"
  if [[ "$INCLUDE_DEMOS" == "1" ]]; then
    sanitize_tree_with_demos "$target_dir"
  else
    sanitize_tree "$target_dir"
  fi

  git -C "$target_dir" config user.name "${GIT_AUTHOR_NAME:-toa}"
  git -C "$target_dir" config user.email "${GIT_AUTHOR_EMAIL:-toa@local}"
  git -C "$target_dir" add -A
  if git -C "$target_dir" diff --cached --quiet; then
    echo "[toa] target source mirror already up to date"
    return
  fi

  git -C "$target_dir" commit -m "sync: mirror anime-arsenal ${SOURCE_SHA:0:12}"
  git -C "$target_dir" push origin HEAD:main
  echo "[toa] synced source mirror: ${TARGET_REPO_URL} main"
}

json_value() {
  node -p "JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'))${2}" "$1"
}

prepare_release_source() {
  clone_source
  select_demo_works
  pull_demo_lfs
  sanitize_tree_with_demos "$SOURCE_DIR"

  local desktop_version
  local tauri_version
  desktop_version="$(json_value "$SOURCE_DIR/desktop/package.json" ".version")"
  tauri_version="$(json_value "$SOURCE_DIR/desktop/src-tauri/tauri.conf.json" ".version")"
  if [[ "$desktop_version" != "$tauri_version" ]]; then
    echo "Version mismatch: desktop/package.json=$desktop_version tauri.conf.json=$tauri_version" >&2
    exit 1
  fi

  TAG="${TOA_RELEASE_TAG:-v${desktop_version}}"
  OUT_DIR="$ROOT/dist/toa-release-${TAG}"
  if [[ -z "$ARTIFACT_DIR" ]]; then
    ARTIFACT_DIR="$OUT_DIR"
  fi
  rm -rf "$OUT_DIR"
  mkdir -p "$OUT_DIR" "$ARTIFACT_DIR"

  echo "[toa] release tag: $TAG"
  echo "[toa] release repo: $TARGET_REPO"
  echo "[toa] release source is remote-only; local working tree is ignored"
  echo "[toa] source tree sanitized before build: only selected demo works kept from 创作区/; dist/ removed"
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
  echo "[toa] signing macOS app with identity: $SIGNING_IDENTITY"
  codesign --force --deep --options runtime --sign "$SIGNING_IDENTITY" "$app_path"
  codesign --verify --deep --strict --verbose=4 "$app_path"
}

make_macos_dmg() {
  local app_path="$1"
  local dmg_out="$2"
  local stage
  stage="$(mktemp -d "${TMPDIR:-/tmp}/toa-dmg-stage.XXXXXX")"
  ditto "$app_path" "$stage/AnimeArmory.app"
  ln -s /Applications "$stage/Applications"
  rm -f "$dmg_out"
  hdiutil create -volname "AnimeArmory" -srcfolder "$stage" -format UDZO -ov "$dmg_out"
  rm -rf "$stage"
}

notarize_dmg_if_configured() {
  local dmg="$1"
  if [[ -z "$NOTARY_PROFILE" ]]; then
    echo "[toa] notarization skipped (TOA_NOTARY_KEYCHAIN_PROFILE not set)"
    return
  fi
  echo "[toa] submitting DMG to Apple notarization profile: $NOTARY_PROFILE"
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
  echo "[toa] validating DMG: $(basename "$dmg")"
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
    echo "[toa] Gatekeeper check accepted"
  else
    cat "$OUT_DIR/spctl-macos.txt" >&2
    if [[ "$REQUIRE_GATEKEEPER" == "1" ]]; then
      echo "Gatekeeper rejected the app. Configure Developer ID signing + notarization, or unset TOA_REQUIRE_GATEKEEPER." >&2
      hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
      exit 1
    fi
    echo "[toa] Gatekeeper rejected this non-notarized build; continuing because TOA_REQUIRE_GATEKEEPER!=1" >&2
  fi
  hdiutil detach "$mount_dir" >/dev/null
}

validate_zip() {
  local path="$1"
  echo "[toa] validating zip container: $(basename "$path")"
  unzip -tqq "$path"
}

validate_nonempty() {
  local path="$1"
  if [[ ! -s "$path" ]]; then
    echo "Built artifact is missing or empty: $path" >&2
    exit 1
  fi
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
  local demo
  for demo in "${DEMO_WORKS[@]}"; do
    printf -- "- %s\n" "$demo"
  done
}

build_macos_assets() {
  local target="$1"
  local dmg_name="$2"
  local app_src="$SOURCE_DIR/desktop/src-tauri/target/$target/release/bundle/macos/AnimeArmory.app"

  (
    cd "$SOURCE_DIR/desktop"
    TOA_INCLUDE_DEMOS=1 \
    TOA_FEATURED_WORK="${DEMO_WORKS[0]}" \
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
  (
    cd "$SOURCE_DIR/desktop"
    TOA_INCLUDE_DEMOS=1 \
    TOA_FEATURED_WORK="${DEMO_WORKS[0]}" \
      npm run tauri -- build --target x86_64-pc-windows-gnu --bundles nsis --ci
  )
  local exe_src
  exe_src="$(latest_file "$SOURCE_DIR/desktop/src-tauri/target/x86_64-pc-windows-gnu/release/bundle/nsis" '*.exe')"
  if [[ -z "$exe_src" || ! -f "$exe_src" ]]; then
    echo "Could not locate built Windows installer" >&2
    exit 1
  fi
  local artifact_exe="$ARTIFACT_DIR/AnimeArsenal_windows.exe"
  mv "$exe_src" "$artifact_exe"
  validate_nonempty "$artifact_exe"
  ASSETS+=("$artifact_exe")
}

sync_vsix_demo_works() {
  local extension_dir="$SOURCE_DIR/vscode-extension"
  local safety="$SOURCE_DIR/tools/release-safety/demo_safety.cjs"
  local demo line

  rm -rf "$extension_dir/创作区"
  for line in "${CREATIVE_LINES[@]}"; do
    mkdir -p "$extension_dir/创作区/$line"
  done
  for demo in "${DEMO_WORKS[@]}"; do
    node "$safety" copy "$SOURCE_DIR/$demo" "$extension_dir/$demo"
  done
}

build_vsix() {
  sync_vsix_demo_works
  (
    cd "$SOURCE_DIR/vscode-extension"
    rm -f *.vsix
    install_node_deps "$SOURCE_DIR/vscode-extension"
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

Built from remote anime-arsenal source.

- Source repo: ${SOURCE_REPO_URL}
- Source ref: ${SOURCE_REF}
- Source commit: ${SOURCE_SHA}
- Release repo: https://github.com/${TARGET_REPO}
- Code sync to anime-armory: not performed in release mode
- Package set: $([[ "$RELEASE_ALL" == "1" ]] && echo "macOS Apple Silicon DMG + Windows EXE + VSIX" || echo "macOS Apple Silicon DMG only")

Bundled demos:
$(format_demo_lines)

Assets:
$(format_asset_lines)
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
  if [[ "$RELEASE_ALL" == "1" ]]; then
    latest_args=(--latest)
  fi
  if GH_HTTP_TIMEOUT="${GH_HTTP_TIMEOUT:-600}" gh release view "$TAG" --repo "$TARGET_REPO" >/dev/null 2>&1; then
    GH_HTTP_TIMEOUT="${GH_HTTP_TIMEOUT:-600}" gh release upload "$TAG" "${ASSETS[@]}" "$OUT_DIR/SHA256SUMS.txt" \
      --repo "$TARGET_REPO" \
      --clobber
    if [[ "$RELEASE_ALL" == "1" ]]; then
      GH_HTTP_TIMEOUT="${GH_HTTP_TIMEOUT:-600}" gh release edit "$TAG" \
        --repo "$TARGET_REPO" \
        --title "AnimeArmory ${TAG}" \
        --notes-file "$notes" \
        --latest
    else
      GH_HTTP_TIMEOUT="${GH_HTTP_TIMEOUT:-600}" gh release edit "$TAG" \
        --repo "$TARGET_REPO" \
        --title "AnimeArmory ${TAG}" \
        --notes-file "$notes"
    fi
  else
    GH_HTTP_TIMEOUT="${GH_HTTP_TIMEOUT:-600}" gh release create "$TAG" "${ASSETS[@]}" "$OUT_DIR/SHA256SUMS.txt" \
      --repo "$TARGET_REPO" \
      --title "AnimeArmory ${TAG}" \
      --notes-file "$notes" \
      "${latest_args[@]}"
  fi
}

update_target_readme_links() {
  if [[ "$UPLOAD" != "1" || "$UPDATE_README" != "1" ]]; then
    return
  fi
  require_assets
  require_cmd python3

  local readme_dir="$WORK/anime-armory-readme"
  clone_target "$readme_dir"
  if [[ ! -f "$readme_dir/README.md" ]]; then
    echo "[toa] target README.md not found; skip README link update"
    return
  fi

  python3 - "$readme_dir/README.md" "$TARGET_REPO" "$TAG" "${ASSETS[@]}" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
repo = sys.argv[2]
tag = sys.argv[3]
assets = [Path(x).name for x in sys.argv[4:]]
text = path.read_text(encoding="utf-8")
for name in assets:
    target = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    pattern = re.compile(
        r"https://github\.com/[^)\s]+/releases/(?:latest/download|download/[^/\s)]+)/"
        + re.escape(name)
    )
    text = pattern.sub(target, text)
path.write_text(text, encoding="utf-8")
PY

  git -C "$readme_dir" config user.name "${GIT_AUTHOR_NAME:-toa}"
  git -C "$readme_dir" config user.email "${GIT_AUTHOR_EMAIL:-toa@local}"
  git -C "$readme_dir" add README.md
  if git -C "$readme_dir" diff --cached --quiet; then
    echo "[toa] README download links already up to date"
    return
  fi
  git -C "$readme_dir" commit -m "docs: update release download links"
  git -C "$readme_dir" push origin HEAD:main
  echo "[toa] README download links updated in ${TARGET_REPO}"
}

run_release() {
  require_cmd node
  require_cmd npm
  require_cmd hdiutil
  require_cmd codesign
  require_cmd ditto
  require_cmd unzip

  prepare_release_source
  install_node_deps "$SOURCE_DIR/desktop"

  rm -f \
    "$ARTIFACT_DIR/AnimeArsenal_macos_arm64.dmg" \
    "$ARTIFACT_DIR/AnimeArsenal_windows.exe" \
    "$ARTIFACT_DIR/anime-armory.vsix"

  build_macos_assets "aarch64-apple-darwin" "AnimeArsenal_macos_arm64.dmg"

  if [[ "$RELEASE_ALL" == "1" ]]; then
    build_windows_exe
    build_vsix
  fi

  write_checksums
  local notes
  notes="$(release_notes)"
  upload_release "$notes"
  update_target_readme_links

  for asset in "${ASSETS[@]}"; do
    echo "[toa] artifact: $asset"
  done
  if [[ "$UPLOAD" == "1" ]]; then
    echo "[toa] release: https://github.com/${TARGET_REPO}/releases/tag/${TAG}"
  else
    echo "[toa] upload disabled; local artifacts only"
  fi
}

cd "$ROOT"
if [[ "$MODE" == "mirror" ]]; then
  sync_remote_code_to_target
else
  run_release
fi
