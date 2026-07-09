// Bridge commands: scan the workspace, read the canvas (review_ui or
// storyboard fallback), and shell out to the repo's `--json` tools.
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs;
use std::hash::{Hash, Hasher};
use std::io::Read;
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use base64::Engine;
use encoding_rs::GB18030;
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use tauri::Manager;

// ---- workspace scan ----

#[derive(Serialize)]
pub struct WorkRoot {
    name: String,
    path: String,
    has_progress: bool,
    is_demo: bool,
}

#[derive(Serialize)]
pub struct LineInfo {
    line: String,
    label: String,
    dir: String,
    view: String, // canvas | files | audio
    roots: Vec<WorkRoot>,
}

const CREATION_ROOT: &str = "创作区";
const TREE_DEPTH_LIMIT: usize = 6;
const WORK_TREE_ENTRY_LIMIT: usize = 8_000;
const WORK_DIR_ENTRY_LIMIT: usize = 500;
const WORK_SNAPSHOT_ENTRY_LIMIT: usize = 20_000;
const BASELINE_FILE_LIMIT: usize = 50_000;
const CHANGE_SUMMARY_FILE_LIMIT: usize = 30_000;
const HASH_COMPARE_LIMIT: u64 = 1024 * 1024;
const TEXT_SNAPSHOT_LIMIT: u64 = 2 * 1024 * 1024;
const TEXT_EDIT_LIMIT: u64 = 20 * 1024 * 1024;
const DOCX_PREVIEW_LIMIT: u64 = 80 * 1024 * 1024;
const DOCX_TEXT_PREVIEW_LIMIT: usize = 2 * 1024 * 1024;
const WORK_SEARCH_FILE_LIMIT: usize = 30_000;
const WORK_SEARCH_RESULT_LIMIT: usize = 300;
const WORK_SEARCH_MATCH_LIMIT_PER_FILE: usize = 12;
const WORK_SEARCH_TEXT_LIMIT: u64 = 1024 * 1024;
const WORK_SEARCH_DEPTH_LIMIT: usize = 10;
const CANVAS_PROMPT_PREVIEW_LIMIT: usize = 4096;
const APP_CONFIG_DIR: &str = "anime-armory";
const WORKSPACE_META_DIR: &str = ".anime-armory";
const DEMO_ORIGINS_FILE: &str = "demo_origins.json";
const DEMO_CATALOG_FILE: &str = "demo_catalog.json";
const DEFAULT_RELEASE_DOWNLOAD_BASE: &str =
    "https://github.com/anton6202527/anime-armory/releases/latest/download";

const LINES: &[(&str, &str, &str, &str)] = &[
    // (key, label, product dir, view)
    ("n2d", "制漫剧 (n2d)", "制漫剧", "canvas"),
    ("comic", "画漫画 (comic)", "画漫画", "canvas"),
    ("ad", "拍广告 (ad)", "拍广告", "canvas"),
    ("mv", "制MV (mv)", "制MV", "canvas"),
    ("song", "写歌 (song)", "写歌", "audio"),
    ("novel", "写小说 (novel)", "写小说", "files"),
];

fn demo_rel(product: &str, name: &str) -> String {
    format!("{CREATION_ROOT}/{product}/{name}")
}

#[derive(Clone, Deserialize)]
struct DemoCatalogEntry {
    line: String,
    line_key: Option<String>,
    name: String,
    rel: Option<String>,
    is_demo: Option<bool>,
    asset_name: Option<String>,
    download_url: Option<String>,
    sha256: Option<String>,
    size: Option<u64>,
    source: Option<String>,
}

impl DemoCatalogEntry {
    fn rel(&self) -> String {
        self.rel
            .clone()
            .unwrap_or_else(|| demo_rel(&self.line, &self.name))
    }
}

#[derive(Serialize)]
pub struct DemoDownloadInfo {
    line: String,
    line_key: String,
    name: String,
    rel: String,
    asset_name: String,
    download_url: String,
    sha256: Option<String>,
    size: Option<u64>,
    source: String,
    installed: bool,
    path: Option<String>,
}

#[derive(Serialize)]
pub struct DemoInstallResult {
    root: WorkRoot,
    already_installed: bool,
}

fn load_demo_catalog(app: &tauri::AppHandle) -> Vec<DemoCatalogEntry> {
    let mut candidates = Vec::new();
    if let Ok(res) = app.path().resource_dir() {
        candidates.push(res.join("resources").join(DEMO_CATALOG_FILE));
    }
    candidates.push(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("resources")
            .join(DEMO_CATALOG_FILE),
    );

    for path in candidates {
        let Ok(text) = fs::read_to_string(path) else {
            continue;
        };
        if let Ok(entries) = serde_json::from_str::<Vec<DemoCatalogEntry>>(&text) {
            return entries;
        }
    }
    Vec::new()
}

fn line_key_for_product(product: &str) -> Option<&'static str> {
    LINES
        .iter()
        .find(|(_, _, dir, _)| *dir == product)
        .map(|(key, _, _, _)| *key)
}

fn product_for_line_key(line_key: &str) -> Option<&'static str> {
    LINES
        .iter()
        .find(|(key, _, _, _)| *key == line_key)
        .map(|(_, _, dir, _)| *dir)
}

fn catalog_entry_line_key(entry: &DemoCatalogEntry) -> Option<String> {
    entry
        .line_key
        .clone()
        .or_else(|| line_key_for_product(&entry.line).map(|key| key.to_string()))
}

fn demo_asset_name_for_key(line_key: &str) -> String {
    format!("AnimeArmory_demo_{line_key}.zip")
}

fn demo_download_base() -> String {
    std::env::var("ANIME_ARMORY_DEMO_RELEASE_BASE")
        .ok()
        .map(|value| value.trim().trim_end_matches('/').to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| DEFAULT_RELEASE_DOWNLOAD_BASE.to_string())
}

fn catalog_entry_asset_name(entry: &DemoCatalogEntry, line_key: &str) -> String {
    entry
        .asset_name
        .clone()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| demo_asset_name_for_key(line_key))
}

fn catalog_entry_download_url(entry: &DemoCatalogEntry, asset_name: &str) -> String {
    entry
        .download_url
        .clone()
        .filter(|value| value.starts_with("https://") || value.starts_with("http://"))
        .unwrap_or_else(|| format!("{}/{}", demo_download_base(), asset_name))
}

fn demo_info_from_entry(workspace: &Path, entry: &DemoCatalogEntry) -> Option<DemoDownloadInfo> {
    let line_key = catalog_entry_line_key(entry)?;
    let asset_name = catalog_entry_asset_name(entry, &line_key);
    let rel = entry.rel();
    let path = workspace.join(&rel);
    let installed = path.join("_进度.md").is_file();
    Some(DemoDownloadInfo {
        line: entry.line.clone(),
        line_key,
        name: entry.name.clone(),
        rel,
        asset_name: asset_name.clone(),
        download_url: catalog_entry_download_url(entry, &asset_name),
        sha256: entry.sha256.clone(),
        size: entry.size,
        source: entry
            .source
            .clone()
            .unwrap_or_else(|| "release-demo".into()),
        installed,
        path: installed.then(|| path.to_string_lossy().to_string()),
    })
}

#[tauri::command]
pub fn list_demo_downloads(app: tauri::AppHandle, workspace_root: String) -> Vec<DemoDownloadInfo> {
    let workspace = Path::new(&workspace_root);
    load_demo_catalog(&app)
        .iter()
        .filter_map(|entry| demo_info_from_entry(workspace, entry))
        .collect()
}

fn demo_origins_path(workspace: &Path) -> PathBuf {
    workspace.join(WORKSPACE_META_DIR).join(DEMO_ORIGINS_FILE)
}

fn load_demo_origins(workspace: &Path) -> BTreeSet<String> {
    let path = demo_origins_path(workspace);
    fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str::<BTreeSet<String>>(&text).ok())
        .unwrap_or_default()
}

fn write_demo_origins(workspace: &Path, origins: &BTreeSet<String>) -> Result<(), String> {
    let path = demo_origins_path(workspace);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let text = serde_json::to_string_pretty(origins).map_err(|e| e.to_string())?;
    fs::write(path, text).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn scan_workspace(app: tauri::AppHandle, repo_root: String) -> Vec<LineInfo> {
    let workspace = Path::new(&repo_root);
    let demo_origins = load_demo_origins(workspace);
    let demo_catalog = load_demo_catalog(&app);
    let catalog_by_rel: BTreeMap<String, DemoCatalogEntry> = demo_catalog
        .iter()
        .map(|entry| (entry.rel(), entry.clone()))
        .collect();
    LINES
        .iter()
        .map(|(key, label, dir, view)| {
            let abs = workspace.join(CREATION_ROOT).join(dir);
            let mut roots = Vec::new();
            if let Ok(entries) = fs::read_dir(&abs) {
                for e in entries.flatten() {
                    let p = e.path();
                    if p.is_dir() {
                        let name = e.file_name().to_string_lossy().to_string();
                        if name.starts_with('.') || name.starts_with('_') {
                            continue;
                        }
                        let rel = demo_rel(dir, &name);
                        let catalog_entry = catalog_by_rel.get(&rel);
                        let has_progress = p.join("_进度.md").exists();
                        let is_demo = demo_origins.contains(&rel)
                            || catalog_entry
                                .and_then(|entry| entry.is_demo)
                                .unwrap_or(false);
                        roots.push(WorkRoot {
                            name,
                            path: p.to_string_lossy().to_string(),
                            has_progress,
                            is_demo,
                        });
                    }
                }
            }
            roots.sort_by(|a, b| {
                b.is_demo
                    .cmp(&a.is_demo)
                    .then_with(|| a.name.cmp(&b.name))
                    .then_with(|| a.path.cmp(&b.path))
            });
            LineInfo {
                line: key.to_string(),
                label: label.to_string(),
                dir: abs.to_string_lossy().to_string(),
                view: view.to_string(),
                roots,
            }
        })
        .collect()
}

// ---- skills (per-line SKILL.md roster) ----

#[derive(Serialize)]
pub struct SkillInfo {
    name: String,
    description: String,
    dir: String, // skill directory name under skills/ (for skill_tree)
}

#[derive(Serialize)]
pub struct SkillTreeEntry {
    name: String,
    path: String, // path relative to the skill dir, e.g. "scripts/market.py"
    depth: usize,
    is_dir: bool,
    // Change status vs the work's local baseline snapshot:
    // "u" = new since baseline, "m" = modified, "" = clean / not tracked.
    // Always "" for skill_tree (which has no baseline).
    status: String,
    size: u64,
    mtime: u64,
    truncated: bool,
}

#[derive(Serialize)]
pub struct WorkDirListing {
    entries: Vec<SkillTreeEntry>,
    total: usize,
    offset: usize,
    limit: usize,
    has_more: bool,
}

#[derive(Serialize)]
pub struct WorkSnapshot {
    signature: String,
    file_count: usize,
    dir_count: usize,
    capped: bool,
}

#[derive(Serialize, Default)]
pub struct WorkChangeSummary {
    changed: usize,
    deleted: usize,
    scanned: usize,
    capped: bool,
}

#[derive(Serialize)]
pub struct WorkFileWriteResult {
    size: u64,
    mtime: u64,
}

#[derive(Serialize)]
pub struct CanvasCaptureSaveResult {
    rel: String,
    path: String,
}

#[derive(Serialize)]
pub struct ImportWorkSourcesResult {
    root: String,
    name: String,
    imported: Vec<String>,
}

#[derive(Serialize)]
pub struct WorkChangeEntry {
    path: String,
    kind: String, // added | modified | deleted
    old_size: Option<u64>,
    new_size: Option<u64>,
    old_mtime: Option<u64>,
    new_mtime: Option<u64>,
    text_available: bool,
}

#[derive(Serialize, Default)]
pub struct WorkChanges {
    changes: Vec<WorkChangeEntry>,
    scanned: usize,
    capped: bool,
}

#[derive(Serialize)]
pub struct WorkChangeDetail {
    path: String,
    kind: String,
    old_text: String,
    new_text: String,
    text_available: bool,
    message: String,
}

#[derive(Serialize)]
pub struct WorkSearchMatch {
    line: usize,
    preview: String,
}

#[derive(Serialize)]
pub struct WorkSearchResult {
    path: String,
    name: String,
    size: u64,
    name_match: bool,
    matches: Vec<WorkSearchMatch>,
}

#[derive(Serialize, Default)]
pub struct WorkSearchResponse {
    query: String,
    results: Vec<WorkSearchResult>,
    scanned: usize,
    capped: bool,
}

/// The file/folder tree under `skills/<dir>/` for the skills-detail view.
/// `dir` is a single skill directory name (path traversal is rejected).
#[tauri::command]
pub fn skill_tree(repo_root: String, dir: String) -> Vec<SkillTreeEntry> {
    if dir.is_empty() || dir.contains('/') || dir.contains('\\') || dir.contains("..") {
        return Vec::new();
    }
    let base = Path::new(&repo_root).join("skills").join(&dir);
    let mut out = Vec::new();
    walk_tree(&base, "", 0, &mut out);
    out
}

fn walk_tree(dir: &Path, prefix: &str, depth: usize, out: &mut Vec<SkillTreeEntry>) {
    if depth > TREE_DEPTH_LIMIT {
        return;
    }
    let mut entries: Vec<_> = match fs::read_dir(dir) {
        Ok(rd) => rd.flatten().collect(),
        Err(_) => return,
    };
    // dirs first, then files; alphabetical within each group
    entries.sort_by(|a, b| {
        let (ad, bd) = (a.path().is_dir(), b.path().is_dir());
        bd.cmp(&ad).then(a.file_name().cmp(&b.file_name()))
    });
    for e in entries {
        let name = e.file_name().to_string_lossy().to_string();
        if should_skip_tree_entry(&name) {
            continue;
        }
        let meta = e.metadata().ok();
        let is_dir = meta
            .as_ref()
            .map(|m| m.is_dir())
            .unwrap_or_else(|| e.path().is_dir());
        let rel = if prefix.is_empty() {
            name.clone()
        } else {
            format!("{prefix}/{name}")
        };
        out.push(SkillTreeEntry {
            name: name.clone(),
            path: rel.clone(),
            depth,
            is_dir,
            status: String::new(),
            size: meta
                .as_ref()
                .filter(|m| m.is_file())
                .map(|m| m.len())
                .unwrap_or(0),
            mtime: meta.as_ref().and_then(metadata_mtime).unwrap_or(0),
            truncated: false,
        });
        if is_dir {
            walk_tree(&e.path(), &rel, depth + 1, out);
        }
    }
}

fn walk_tree_limited(
    dir: &Path,
    prefix: &str,
    depth: usize,
    out: &mut Vec<SkillTreeEntry>,
    limit: usize,
) -> bool {
    if depth > TREE_DEPTH_LIMIT {
        return false;
    }
    let mut entries: Vec<_> = match fs::read_dir(dir) {
        Ok(rd) => rd.flatten().collect(),
        Err(_) => return false,
    };
    entries.sort_by(|a, b| {
        let (ad, bd) = (a.path().is_dir(), b.path().is_dir());
        bd.cmp(&ad).then(a.file_name().cmp(&b.file_name()))
    });
    for e in entries {
        if out.len() >= limit {
            return true;
        }
        let name = e.file_name().to_string_lossy().to_string();
        if should_skip_tree_entry(&name) {
            continue;
        }
        let meta = e.metadata().ok();
        let is_dir = meta
            .as_ref()
            .map(|m| m.is_dir())
            .unwrap_or_else(|| e.path().is_dir());
        let rel = if prefix.is_empty() {
            name.clone()
        } else {
            format!("{prefix}/{name}")
        };
        out.push(SkillTreeEntry {
            name: name.clone(),
            path: rel.clone(),
            depth,
            is_dir,
            status: String::new(),
            size: meta
                .as_ref()
                .filter(|m| m.is_file())
                .map(|m| m.len())
                .unwrap_or(0),
            mtime: meta.as_ref().and_then(metadata_mtime).unwrap_or(0),
            truncated: false,
        });
        if is_dir && walk_tree_limited(&e.path(), &rel, depth + 1, out, limit) {
            return true;
        }
    }
    false
}

fn metadata_mtime(meta: &fs::Metadata) -> Option<u64> {
    Some(
        meta.modified()
            .ok()?
            .duration_since(UNIX_EPOCH)
            .ok()?
            .as_millis() as u64,
    )
}

fn should_skip_tree_entry(name: &str) -> bool {
    matches!(
        name,
        "__pycache__" | ".DS_Store" | "node_modules" | "_voicecache" | ".git"
    )
}

/// Read one text file inside a skill (`skills/<dir>/<rel>`) for the code pane.
/// Hard-guarded: `dir` must be a bare name, `rel` must stay inside the skill
/// dir (no `..` escape), binary/oversize files are refused.
#[tauri::command]
pub fn read_skill_file(repo_root: String, dir: String, rel: String) -> Result<String, String> {
    if dir.is_empty() || dir.contains('/') || dir.contains('\\') || dir.contains("..") {
        return Err("非法 skill 目录".into());
    }
    if rel.is_empty() || rel.contains("..") {
        return Err("非法文件路径".into());
    }
    let base = Path::new(&repo_root).join("skills").join(&dir);
    let base_canon = fs::canonicalize(&base).map_err(|e| e.to_string())?;
    let target_canon = fs::canonicalize(base.join(&rel)).map_err(|e| e.to_string())?;
    if !target_canon.starts_with(&base_canon) {
        return Err("路径越界，已拒绝".into());
    }
    let meta = fs::metadata(&target_canon).map_err(|e| e.to_string())?;
    if meta.is_dir() {
        return Err("这是一个目录".into());
    }
    const MAX: u64 = 512 * 1024; // 512 KB preview cap
    if meta.len() > MAX {
        return Err(format!("文件过大（{} KB），不在此预览", meta.len() / 1024));
    }
    let bytes = fs::read(&target_canon).map_err(|e| e.to_string())?;
    if bytes.contains(&0) {
        return Err("二进制文件，不预览".into());
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

// ---- work-folder file viewer (the default "文件" tab of every work) ----

/// The full file/folder tree under a work root (`创作区/<line>/<work>/`), for the
/// in-app 文件 viewer. Reuses `SkillTreeEntry`'s {name,path,depth,is_dir} shape and
/// fills `status` ("u"/"m"/"") against the work's local baseline snapshot.
/// `root` is an absolute work path produced by `scan_workspace`; read-only to the work.
#[tauri::command]
pub fn work_tree(root: String) -> Vec<SkillTreeEntry> {
    let base = Path::new(&root);
    let mut out = Vec::new();
    if !base.is_dir() {
        return out;
    }
    let capped = walk_tree_limited(base, "", 0, &mut out, WORK_TREE_ENTRY_LIMIT);

    // First-ever scan of a work: silently seed the baseline from the current
    // state so everything starts "clean" (no marker noise) — markers only show
    // for genuine changes made after this point.
    if !baseline_exists(&root) {
        let mut bl = Baseline::default();
        let mut scanned = 0usize;
        let _ = snapshot_files(
            base,
            "",
            0,
            &mut bl.files,
            BASELINE_FILE_LIMIT,
            &mut scanned,
        );
        let _ = save_baseline(&root, &bl);
        if capped {
            push_tree_limit_marker(&mut out);
        }
        return out;
    }

    let bl = load_baseline(&root);
    annotate_status(&root, &mut out, &bl);
    if capped {
        push_tree_limit_marker(&mut out);
    }
    out
}

fn rel_depth(rel: &str) -> usize {
    rel.split('/')
        .filter(|part| !part.is_empty())
        .count()
        .saturating_sub(1)
}

fn entry_status_for_listing(base: &Path, rel: &str, is_dir: bool, bl: Option<&Baseline>) -> String {
    let Some(bl) = bl else {
        return String::new();
    };
    if is_dir {
        let prefix = format!("{rel}/");
        return if bl.files.keys().any(|path| path.starts_with(&prefix)) {
            String::new()
        } else {
            "u".into()
        };
    }
    match bl.files.get(rel) {
        None => "u".into(),
        Some(prev) => file_meta(&base.join(rel))
            .filter(|cur| file_changed(base, rel, prev, cur))
            .map(|_| "m".into())
            .unwrap_or_default(),
    }
}

/// A single directory page for the in-app file tree. Unlike `work_tree`, this is
/// intentionally shallow and paged, so opening a media-heavy work never walks
/// thousands of generated images/videos just to render the sidebar.
#[tauri::command]
pub fn work_dir(
    root: String,
    rel: String,
    offset: Option<usize>,
    limit: Option<usize>,
) -> WorkDirListing {
    let mut listing = WorkDirListing {
        entries: Vec::new(),
        total: 0,
        offset: offset.unwrap_or(0),
        limit: limit.unwrap_or(WORK_DIR_ENTRY_LIMIT).clamp(50, 5_000),
        has_more: false,
    };
    let base = Path::new(&root);
    if !base.is_dir() || validate_rel_path(&rel, true).is_err() {
        return listing;
    }
    let dir = match existing_work_path(&root, &rel, true) {
        Ok(path) if path.is_dir() => path,
        _ => return listing,
    };
    let mut raw: Vec<_> = match fs::read_dir(&dir) {
        Ok(rd) => rd
            .flatten()
            .filter(|entry| {
                let name = entry.file_name().to_string_lossy().to_string();
                !should_skip_tree_entry(&name)
            })
            .collect(),
        Err(_) => return listing,
    };
    raw.sort_by(|a, b| {
        let (ad, bd) = (a.path().is_dir(), b.path().is_dir());
        bd.cmp(&ad).then(a.file_name().cmp(&b.file_name()))
    });
    listing.total = raw.len();
    let end = listing
        .total
        .min(listing.offset.saturating_add(listing.limit));
    listing.has_more = end < listing.total;
    let bl = if baseline_exists(&root) {
        Some(load_baseline(&root))
    } else {
        None
    };

    for e in raw.into_iter().skip(listing.offset).take(listing.limit) {
        let name = e.file_name().to_string_lossy().to_string();
        let child_rel = if rel.is_empty() {
            name.clone()
        } else {
            format!("{rel}/{name}")
        };
        let meta = e.metadata().ok();
        let is_dir = meta
            .as_ref()
            .map(|m| m.is_dir())
            .unwrap_or_else(|| e.path().is_dir());
        listing.entries.push(SkillTreeEntry {
            name,
            path: child_rel.clone(),
            depth: rel_depth(&child_rel),
            is_dir,
            status: entry_status_for_listing(base, &child_rel, is_dir, bl.as_ref()),
            size: meta
                .as_ref()
                .filter(|m| m.is_file())
                .map(|m| m.len())
                .unwrap_or(0),
            mtime: meta.as_ref().and_then(metadata_mtime).unwrap_or(0),
            truncated: false,
        });
    }
    listing
}

fn push_tree_limit_marker(out: &mut Vec<SkillTreeEntry>) {
    out.push(SkillTreeEntry {
        name: "tree-limit".into(),
        path: "__anime_armory_tree_limit__".into(),
        depth: 0,
        is_dir: false,
        status: String::new(),
        size: WORK_TREE_ENTRY_LIMIT as u64,
        mtime: 0,
        truncated: true,
    });
}

/// Cheap recursive fingerprint of the visible work tree. Used by the frontend
/// as a polling fallback when the OS watcher misses a burst of skill-generated
/// file writes. It has no baseline side effects; it only observes the directory.
#[tauri::command]
pub fn work_snapshot(root: String) -> WorkSnapshot {
    let base = Path::new(&root);
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    let mut file_count = 0usize;
    let mut dir_count = 0usize;
    let mut capped = false;
    if base.is_dir() {
        capped = snapshot_signature(base, "", 0, &mut hasher, &mut file_count, &mut dir_count);
    } else {
        "missing".hash(&mut hasher);
    }
    WorkSnapshot {
        signature: format!("{:016x}", hasher.finish()),
        file_count,
        dir_count,
        capped,
    }
}

/// Cheap root-level emptiness probe for first-open UX. This avoids building the
/// full work tree just to decide whether to show the empty n2d guidance.
#[tauri::command]
pub fn work_is_empty(root: String) -> bool {
    let base = Path::new(&root);
    work_is_empty_path(base)
}

fn work_is_empty_path(base: &Path) -> bool {
    if !base.is_dir() {
        return true;
    }
    let Ok(entries) = fs::read_dir(base) else {
        return true;
    };
    !entries.flatten().any(|e| {
        let name = e.file_name().to_string_lossy().to_string();
        !should_skip_tree_entry(&name)
    })
}

fn snapshot_signature(
    dir: &Path,
    prefix: &str,
    depth: usize,
    hasher: &mut std::collections::hash_map::DefaultHasher,
    file_count: &mut usize,
    dir_count: &mut usize,
) -> bool {
    if depth > TREE_DEPTH_LIMIT {
        return false;
    }
    if (*file_count).saturating_add(*dir_count) >= WORK_SNAPSHOT_ENTRY_LIMIT {
        return true;
    }
    let mut entries: Vec<_> = match fs::read_dir(dir) {
        Ok(rd) => rd.flatten().collect(),
        Err(_) => return false,
    };
    entries.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    for e in entries {
        if (*file_count).saturating_add(*dir_count) >= WORK_SNAPSHOT_ENTRY_LIMIT {
            return true;
        }
        let name = e.file_name().to_string_lossy().to_string();
        if should_skip_tree_entry(&name) {
            continue;
        }
        let rel = if prefix.is_empty() {
            name.clone()
        } else {
            format!("{prefix}/{name}")
        };
        let p = e.path();
        rel.hash(hasher);
        if p.is_dir() {
            *dir_count += 1;
            "dir".hash(hasher);
            if snapshot_signature(&p, &rel, depth + 1, hasher, file_count, dir_count) {
                return true;
            }
        } else if let Ok(meta) = fs::metadata(&p) {
            *file_count += 1;
            "file".hash(hasher);
            meta.len().hash(hasher);
            metadata_mtime(&meta).hash(hasher);
        }
    }
    false
}

// ---- local-baseline change counting ----

#[derive(Serialize, Deserialize, Clone)]
struct FileMeta {
    mtime: u64, // millis since UNIX epoch
    size: u64,
    #[serde(default)]
    hash: u64, // deterministic content hash; 0 means unavailable/legacy baseline
    #[serde(default, skip_serializing_if = "Option::is_none")]
    text: Option<String>, // text snapshot for diff; omitted for binary/large files
}

#[derive(Serialize, Deserialize, Default)]
struct Baseline {
    files: BTreeMap<String, FileMeta>, // rel path -> snapshot at baseline seed
}

/// Where a work's baseline snapshot lives — OS config dir, keyed by a hash of the
/// absolute work path. Kept OUT of the work folder so it never pollutes 创作区/
/// nor gets swept up by the repo's periodic auto-commit hook.
fn baseline_path_for_app(root: &str, app_dir: &str) -> Option<PathBuf> {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    root.hash(&mut hasher);
    let h = hasher.finish();
    Some(
        dirs::config_dir()?
            .join(app_dir)
            .join("baselines")
            .join(format!("{h:016x}.json")),
    )
}

fn baseline_path(root: &str) -> Option<PathBuf> {
    baseline_path_for_app(root, APP_CONFIG_DIR)
}

fn baseline_exists(root: &str) -> bool {
    baseline_path(root).map(|p| p.exists()).unwrap_or(false)
}

fn load_baseline(root: &str) -> Baseline {
    let Some(path) = baseline_path(root) else {
        return Baseline::default();
    };
    let Ok(bytes) = fs::read(path) else {
        return Baseline::default();
    };
    let Ok(bl) = serde_json::from_slice(&bytes) else {
        return Baseline::default();
    };
    bl
}

fn save_baseline(root: &str, bl: &Baseline) -> Result<(), String> {
    let p = baseline_path(root).ok_or("无法定位配置目录")?;
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let data = serde_json::to_vec_pretty(bl).map_err(|e| e.to_string())?;
    fs::write(p, data).map_err(|e| e.to_string())
}

fn file_meta(p: &Path) -> Option<FileMeta> {
    let m = fs::metadata(p).ok()?;
    let mtime = metadata_mtime(&m)?;
    Some(FileMeta {
        mtime,
        size: m.len(),
        hash: 0,
        text: None,
    })
}

fn snapshot_file_meta(p: &Path) -> Option<FileMeta> {
    let mut meta = file_meta(p)?;
    if meta.size <= HASH_COMPARE_LIMIT {
        meta.hash = content_hash(p).unwrap_or(0);
    }
    if meta.size <= TEXT_SNAPSHOT_LIMIT {
        if let Ok(bytes) = fs::read(p) {
            if !bytes.contains(&0) {
                meta.text = Some(String::from_utf8_lossy(&bytes).into_owned());
            }
        }
    }
    Some(meta)
}

fn safe_work_write_target(base: &Path, rel: &str) -> Result<PathBuf, String> {
    validate_rel_path(rel, false)?;
    let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
    let target = base.join(rel);
    let parent = target.parent().ok_or("非法文件路径")?;

    let mut ancestor = parent;
    while !ancestor.exists() {
        ancestor = ancestor.parent().ok_or("非法文件路径")?;
    }
    let ancestor_canon = fs::canonicalize(ancestor).map_err(|e| e.to_string())?;
    if ancestor_canon != base_canon && !ancestor_canon.starts_with(&base_canon) {
        return Err("路径越界，已拒绝".into());
    }

    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let parent_canon = fs::canonicalize(parent).map_err(|e| e.to_string())?;
    if parent_canon != base_canon && !parent_canon.starts_with(&base_canon) {
        return Err("路径越界，已拒绝".into());
    }
    Ok(target)
}

fn safe_work_existing_parent_target(base: &Path, rel: &str) -> Result<PathBuf, String> {
    validate_rel_path(rel, false)?;
    let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
    let target = base.join(rel);
    let Some(parent) = target.parent() else {
        return Err("非法文件路径".into());
    };
    if parent.exists() {
        let parent_canon = fs::canonicalize(parent).map_err(|e| e.to_string())?;
        if parent_canon != base_canon && !parent_canon.starts_with(&base_canon) {
            return Err("路径越界，已拒绝".into());
        }
    }
    Ok(target)
}

fn restore_one_work_change(base: &Path, rel: &str, bl: &mut Baseline) -> Result<(), String> {
    let old = bl.files.get(rel).cloned();

    if old.is_none() {
        let target = safe_work_existing_parent_target(base, rel)?;
        if target.exists() {
            let meta = fs::symlink_metadata(&target).map_err(|e| e.to_string())?;
            if meta.is_dir() {
                return Err(format!("{rel}: 无法撤销目录变动"));
            }
            fs::remove_file(&target).map_err(|e| format!("{rel}: {e}"))?;
        }
        bl.files.remove(rel);
        return Ok(());
    }

    let old = old.expect("checked old.is_none");
    let target = safe_work_write_target(base, rel)?;
    let text = old
        .text
        .ok_or_else(|| format!("{rel}: 基线没有文本快照，无法撤销"))?;
    if target.exists() {
        let meta = fs::symlink_metadata(&target).map_err(|e| e.to_string())?;
        if meta.is_dir() {
            return Err(format!("{rel}: 当前路径是目录，无法写回文件"));
        }
        if meta.file_type().is_symlink() {
            fs::remove_file(&target).map_err(|e| format!("{rel}: {e}"))?;
        }
    }
    fs::write(&target, text.as_bytes()).map_err(|e| format!("{rel}: {e}"))?;
    let restored =
        snapshot_file_meta(&target).ok_or_else(|| format!("{rel}: 无法读取恢复后的文件状态"))?;
    bl.files.insert(rel.to_string(), restored);
    Ok(())
}

fn content_hash(p: &Path) -> Option<u64> {
    const FNV_OFFSET: u64 = 0xcbf29ce484222325;
    const FNV_PRIME: u64 = 0x00000100000001b3;

    let mut file = fs::File::open(p).ok()?;
    let mut hash = FNV_OFFSET;
    let mut buf = [0u8; 16 * 1024];
    loop {
        let n = file.read(&mut buf).ok()?;
        if n == 0 {
            break;
        }
        for b in &buf[..n] {
            hash ^= u64::from(*b);
            hash = hash.wrapping_mul(FNV_PRIME);
        }
    }
    Some(hash)
}

fn file_changed(base: &Path, rel: &str, prev: &FileMeta, cur: &FileMeta) -> bool {
    if cur.size != prev.size {
        return true;
    }
    if cur.mtime == prev.mtime {
        return false;
    }
    if prev.hash == 0 {
        // Legacy baselines did not store content hashes. Fall back to the old
        // mtime+size behavior for those entries.
        return true;
    }
    if cur.size > HASH_COMPARE_LIMIT {
        return true;
    }
    match content_hash(&base.join(rel)) {
        Some(hash) => hash != prev.hash,
        None => true,
    }
}

/// Walk a directory the SAME way `walk_tree` does (same ignores + depth cap) but
/// collect only files with their {mtime,size}, so a snapshot matches the tree.
fn snapshot_files(
    dir: &Path,
    prefix: &str,
    depth: usize,
    out: &mut BTreeMap<String, FileMeta>,
    limit: usize,
    scanned: &mut usize,
) -> bool {
    if depth > TREE_DEPTH_LIMIT {
        return false;
    }
    let rd = match fs::read_dir(dir) {
        Ok(rd) => rd,
        Err(_) => return false,
    };
    for e in rd.flatten() {
        if *scanned >= limit {
            return true;
        }
        let name = e.file_name().to_string_lossy().to_string();
        if should_skip_tree_entry(&name) {
            continue;
        }
        let rel = if prefix.is_empty() {
            name.clone()
        } else {
            format!("{prefix}/{name}")
        };
        let p = e.path();
        if p.is_dir() {
            if snapshot_files(&p, &rel, depth + 1, out, limit, scanned) {
                return true;
            }
        } else if let Some(fm) = snapshot_file_meta(&p) {
            out.insert(rel, fm);
            *scanned += 1;
        }
    }
    false
}

fn snapshot_current_file_meta(
    dir: &Path,
    prefix: &str,
    depth: usize,
    out: &mut BTreeMap<String, FileMeta>,
    limit: usize,
    scanned: &mut usize,
) -> bool {
    if depth > TREE_DEPTH_LIMIT {
        return false;
    }
    let rd = match fs::read_dir(dir) {
        Ok(rd) => rd,
        Err(_) => return false,
    };
    for e in rd.flatten() {
        if *scanned >= limit {
            return true;
        }
        let name = e.file_name().to_string_lossy().to_string();
        if should_skip_tree_entry(&name) {
            continue;
        }
        let rel = if prefix.is_empty() {
            name.clone()
        } else {
            format!("{prefix}/{name}")
        };
        let p = e.path();
        if p.is_dir() {
            if snapshot_current_file_meta(&p, &rel, depth + 1, out, limit, scanned) {
                return true;
            }
        } else if let Some(fm) = file_meta(&p) {
            out.insert(rel, fm);
            *scanned += 1;
        }
    }
    false
}

fn add_parent_dirs(rel: &str, out: &mut HashSet<String>) {
    let mut cursor = rel;
    while let Some(idx) = cursor.rfind('/') {
        let parent = &cursor[..idx];
        if parent.is_empty() {
            break;
        }
        out.insert(parent.to_string());
        cursor = parent;
    }
}

/// Fill each entry's `status` from the baseline: files compare mtime+size; dirs
/// roll up to "u" (a brand-new folder) or "m" (a folder with edited descendants).
fn annotate_status(root: &str, entries: &mut [SkillTreeEntry], bl: &Baseline) {
    let base = Path::new(root);
    let mut changed_dirs = HashSet::new();
    for e in entries.iter_mut() {
        if e.is_dir {
            continue;
        }
        match bl.files.get(&e.path) {
            None => e.status = "u".into(),
            Some(prev) => {
                if let Some(cur) = file_meta(&base.join(&e.path)) {
                    if file_changed(base, &e.path, prev, &cur) {
                        e.status = "m".into();
                    }
                }
            }
        }
        if e.status == "u" || e.status == "m" {
            add_parent_dirs(&e.path, &mut changed_dirs);
        }
    }

    let mut tracked_dirs = HashSet::new();
    for rel in bl.files.keys() {
        add_parent_dirs(rel, &mut tracked_dirs);
    }

    for e in entries.iter_mut() {
        if !e.is_dir {
            continue;
        }
        if changed_dirs.contains(&e.path) {
            e.status = if tracked_dirs.contains(&e.path) {
                "m".into()
            } else {
                "u".into()
            };
        }
    }
}

/// Baseline files that no longer exist on disk.
/// Returned separately from `work_tree` because a deleted file has no tree row.
/// Empty when there's no baseline yet (first scan silently seeds it).
#[tauri::command]
pub fn work_deleted(root: String) -> Vec<String> {
    if !Path::new(&root).is_dir() || !baseline_exists(&root) {
        return Vec::new();
    }
    let base = Path::new(&root);
    let bl = load_baseline(&root);
    bl.files
        .keys()
        .filter(|k| !base.join(k).is_file())
        .cloned()
        .collect()
}

/// Count changed/deleted files without returning or rendering the full tree.
/// This keeps the desktop UI's "N files changed" signal cheap enough to load
/// after the terminal is already interactive.
#[tauri::command]
pub fn work_change_summary(root: String) -> WorkChangeSummary {
    let base = Path::new(&root);
    if !base.is_dir() {
        return WorkChangeSummary::default();
    }

    if !baseline_exists(&root) {
        let mut bl = Baseline::default();
        let mut scanned = 0usize;
        let capped = snapshot_files(
            base,
            "",
            0,
            &mut bl.files,
            BASELINE_FILE_LIMIT,
            &mut scanned,
        );
        let _ = save_baseline(&root, &bl);
        return WorkChangeSummary {
            scanned,
            capped,
            ..WorkChangeSummary::default()
        };
    }

    let bl = load_baseline(&root);
    let mut current = BTreeMap::new();
    let mut scanned = 0usize;
    let capped = snapshot_current_file_meta(
        base,
        "",
        0,
        &mut current,
        CHANGE_SUMMARY_FILE_LIMIT,
        &mut scanned,
    );

    let changed = current
        .iter()
        .filter(|(rel, cur)| match bl.files.get(*rel) {
            None => true,
            Some(prev) => file_changed(base, rel, prev, cur),
        })
        .count();
    let deleted = if capped {
        0
    } else {
        bl.files
            .keys()
            .filter(|rel| !current.contains_key(*rel))
            .count()
    };

    WorkChangeSummary {
        changed,
        deleted,
        scanned,
        capped,
    }
}

fn ensure_work_baseline(root: &str, base: &Path) -> Option<(Baseline, usize, bool)> {
    if !base.is_dir() {
        return None;
    }
    if baseline_exists(root) {
        return Some((load_baseline(root), 0, false));
    }
    let mut bl = Baseline::default();
    let mut scanned = 0usize;
    let capped = snapshot_files(
        base,
        "",
        0,
        &mut bl.files,
        BASELINE_FILE_LIMIT,
        &mut scanned,
    );
    let _ = save_baseline(root, &bl);
    Some((bl, scanned, capped))
}

#[tauri::command]
pub fn work_changes(root: String) -> WorkChanges {
    let base = Path::new(&root);
    let Some((bl, initial_scanned, initial_capped)) = ensure_work_baseline(&root, base) else {
        return WorkChanges::default();
    };
    if initial_scanned > 0 || initial_capped {
        return WorkChanges {
            scanned: initial_scanned,
            capped: initial_capped,
            ..WorkChanges::default()
        };
    }

    let mut current = BTreeMap::new();
    let mut scanned = 0usize;
    let capped = snapshot_current_file_meta(
        base,
        "",
        0,
        &mut current,
        CHANGE_SUMMARY_FILE_LIMIT,
        &mut scanned,
    );

    let mut changes = Vec::new();
    for (rel, cur) in current.iter() {
        match bl.files.get(rel) {
            None => changes.push(WorkChangeEntry {
                path: rel.clone(),
                kind: "added".into(),
                old_size: None,
                new_size: Some(cur.size),
                old_mtime: None,
                new_mtime: Some(cur.mtime),
                text_available: cur.size <= TEXT_SNAPSHOT_LIMIT,
            }),
            Some(prev) => {
                if file_changed(base, rel, prev, cur) {
                    changes.push(WorkChangeEntry {
                        path: rel.clone(),
                        kind: "modified".into(),
                        old_size: Some(prev.size),
                        new_size: Some(cur.size),
                        old_mtime: Some(prev.mtime),
                        new_mtime: Some(cur.mtime),
                        text_available: prev.text.is_some() && cur.size <= TEXT_SNAPSHOT_LIMIT,
                    });
                }
            }
        }
    }
    if !capped {
        for (rel, prev) in bl.files.iter() {
            if !current.contains_key(rel) {
                changes.push(WorkChangeEntry {
                    path: rel.clone(),
                    kind: "deleted".into(),
                    old_size: Some(prev.size),
                    new_size: None,
                    old_mtime: Some(prev.mtime),
                    new_mtime: None,
                    text_available: prev.text.is_some(),
                });
            }
        }
    }
    changes.sort_by(|a, b| a.path.cmp(&b.path));
    WorkChanges {
        changes,
        scanned,
        capped,
    }
}

fn joined_work_path(root: &str, rel: &str) -> Result<PathBuf, String> {
    validate_rel_path(rel, false)?;
    let base = fs::canonicalize(root).map_err(|e| e.to_string())?;
    Ok(base.join(rel))
}

fn read_diff_text(p: &Path) -> Result<String, String> {
    let meta = fs::metadata(p).map_err(|e| e.to_string())?;
    if meta.is_dir() {
        return Err("这是一个目录".into());
    }
    if meta.len() > TEXT_SNAPSHOT_LIMIT {
        return Err(format!(
            "文件过大（{} MB），不在变动对比中展开",
            meta.len() / 1024 / 1024
        ));
    }
    let bytes = fs::read(p).map_err(|e| e.to_string())?;
    if bytes.contains(&0) {
        return Err("二进制文件不做文本对比".into());
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

#[tauri::command]
pub fn read_work_change(root: String, rel: String) -> Result<WorkChangeDetail, String> {
    let base = Path::new(&root);
    if !base.is_dir() || !baseline_exists(&root) {
        return Err("还没有可对比的变动基线".into());
    }
    let loose_target = joined_work_path(&root, &rel)?;
    let existing_target = existing_work_path(&root, &rel, false).ok();
    let target = existing_target.as_deref().unwrap_or(&loose_target);
    let bl = load_baseline(&root);
    let old = bl.files.get(&rel);
    let current_meta = existing_target
        .as_ref()
        .and_then(|p| fs::metadata(p).ok())
        .filter(|m| m.is_file());
    let kind = match (old, current_meta.as_ref()) {
        (None, Some(_)) => "added",
        (Some(_), None) => "deleted",
        (Some(prev), Some(cur)) => {
            let cur_meta = FileMeta {
                mtime: metadata_mtime(cur).unwrap_or(0),
                size: cur.len(),
                hash: 0,
                text: None,
            };
            if file_changed(base, &rel, prev, &cur_meta) {
                "modified"
            } else {
                "unchanged"
            }
        }
        (None, None) => return Err("文件不存在，且基线中也没有记录".into()),
    };

    let old_has_text = old.and_then(|m| m.text.as_ref()).is_some();
    let old_text = match kind {
        "added" => String::new(),
        _ => old.and_then(|m| m.text.clone()).unwrap_or_default(),
    };
    let new_text_result = match kind {
        "deleted" => Ok(String::new()),
        _ => read_diff_text(target),
    };
    let new_text = match &new_text_result {
        Ok(value) => value.clone(),
        Err(_) => String::new(),
    };
    let mut message = String::new();
    let text_available = match kind {
        "added" => match &new_text_result {
            Err(err) => {
                message = err.clone();
                false
            }
            Ok(_) => true,
        },
        "deleted" => {
            if old_has_text {
                true
            } else {
                message = "基线没有旧文本快照，无法展开删除前内容。".into();
                false
            }
        }
        "modified" | "unchanged" => {
            if old_has_text && new_text_result.is_ok() {
                true
            } else {
                message = "基线缺少旧文本快照，或当前文件不是可展开文本。归档一次后，后续变动会保留可对比快照。".into();
                false
            }
        }
        _ => false,
    };
    Ok(WorkChangeDetail {
        path: rel,
        kind: kind.into(),
        old_text,
        new_text,
        text_available,
        message,
    })
}

#[tauri::command]
pub fn archive_work_changes(root: String) -> Result<WorkChangeSummary, String> {
    let base = Path::new(&root);
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    let mut bl = Baseline::default();
    let mut scanned = 0usize;
    let capped = snapshot_files(
        base,
        "",
        0,
        &mut bl.files,
        BASELINE_FILE_LIMIT,
        &mut scanned,
    );
    save_baseline(&root, &bl)?;
    Ok(WorkChangeSummary {
        changed: 0,
        deleted: 0,
        scanned,
        capped,
    })
}

#[tauri::command]
pub fn archive_work_change(root: String, rel: String) -> Result<WorkChangeSummary, String> {
    let base = Path::new(&root);
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    validate_rel_path(&rel, false)?;

    let mut bl = load_baseline(&root);
    let target = base.join(&rel);
    if target.exists() {
        let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
        let target_canon = fs::canonicalize(&target).map_err(|e| e.to_string())?;
        if !target_canon.starts_with(&base_canon) {
            return Err("路径越界，已拒绝".into());
        }
        let meta = fs::metadata(&target_canon).map_err(|e| e.to_string())?;
        if meta.is_dir() {
            return Err("只能归档单个文件变动".into());
        }
        let fm = snapshot_file_meta(&target_canon).ok_or("无法读取当前文件状态")?;
        bl.files.insert(rel, fm);
    } else {
        bl.files.remove(&rel);
    }
    save_baseline(&root, &bl)?;
    Ok(work_change_summary(root))
}

#[tauri::command]
pub fn restore_work_change(root: String, rel: String) -> Result<WorkChangeSummary, String> {
    let base = Path::new(&root);
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    if !baseline_exists(&root) {
        return Err("还没有可撤销的变动基线".into());
    }
    let mut bl = load_baseline(&root);
    restore_one_work_change(base, &rel, &mut bl)?;
    save_baseline(&root, &bl)?;
    Ok(work_change_summary(root))
}

#[tauri::command]
pub fn restore_work_changes(root: String) -> Result<WorkChangeSummary, String> {
    let base = Path::new(&root);
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    if !baseline_exists(&root) {
        return Err("还没有可撤销的变动基线".into());
    }
    let current = work_changes(root.clone()).changes;
    let mut bl = load_baseline(&root);
    let mut failures = Vec::new();
    for change in current {
        if let Err(err) = restore_one_work_change(base, &change.path, &mut bl) {
            failures.push(err);
        }
    }
    save_baseline(&root, &bl)?;
    if !failures.is_empty() {
        return Err(failures.join("\n"));
    }
    Ok(work_change_summary(root))
}

/// Read one text file inside a work root (`<root>/<rel>`) for the file preview.
/// Hard-guarded: `rel` must stay inside the work dir (no `..` escape);
/// binary/oversize files are refused (images/video go through the media server).
#[tauri::command]
pub fn read_work_file(root: String, rel: String) -> Result<String, String> {
    let target_canon = existing_work_path(&root, &rel, false)?;
    let meta = fs::metadata(&target_canon).map_err(|e| e.to_string())?;
    if meta.is_dir() {
        return Err("这是一个目录".into());
    }
    if meta.len() > TEXT_EDIT_LIMIT {
        return Err(format!(
            "文件过大（{} MB），不在内置编辑器打开",
            meta.len() / 1024 / 1024
        ));
    }
    let bytes = fs::read(&target_canon).map_err(|e| e.to_string())?;
    decode_text_bytes(&bytes)
}

fn decode_utf16(bytes: &[u8], little_endian: bool) -> Option<String> {
    if bytes.len() % 2 != 0 {
        return None;
    }
    let units: Vec<u16> = bytes
        .chunks_exact(2)
        .map(|chunk| {
            if little_endian {
                u16::from_le_bytes([chunk[0], chunk[1]])
            } else {
                u16::from_be_bytes([chunk[0], chunk[1]])
            }
        })
        .collect();
    String::from_utf16(&units).ok()
}

fn looks_like_utf16(bytes: &[u8], little_endian: bool) -> bool {
    if bytes.len() < 8 || bytes.len() % 2 != 0 {
        return false;
    }
    let sample_len = bytes.len().min(4096);
    let pairs = sample_len / 2;
    if pairs == 0 {
        return false;
    }
    let zeroes = bytes[..sample_len]
        .chunks_exact(2)
        .filter(|chunk| {
            if little_endian {
                chunk[1] == 0
            } else {
                chunk[0] == 0
            }
        })
        .count();
    zeroes * 100 / pairs >= 55
}

fn decode_text_bytes(bytes: &[u8]) -> Result<String, String> {
    if bytes.is_empty() {
        return Ok(String::new());
    }
    if bytes.starts_with(&[0xef, 0xbb, 0xbf]) {
        return Ok(String::from_utf8_lossy(&bytes[3..]).into_owned());
    }
    if bytes.starts_with(&[0xff, 0xfe]) {
        return decode_utf16(&bytes[2..], true).ok_or_else(|| "无法解码 UTF-16 LE 文本".into());
    }
    if bytes.starts_with(&[0xfe, 0xff]) {
        return decode_utf16(&bytes[2..], false).ok_or_else(|| "无法解码 UTF-16 BE 文本".into());
    }
    if let Ok(text) = std::str::from_utf8(bytes) {
        return Ok(text.to_string());
    }
    if looks_like_utf16(bytes, true) {
        if let Some(text) = decode_utf16(bytes, true) {
            return Ok(text);
        }
    }
    if looks_like_utf16(bytes, false) {
        if let Some(text) = decode_utf16(bytes, false) {
            return Ok(text);
        }
    }
    if bytes.contains(&0) {
        return Err("二进制文件，不预览".into());
    }
    let (text, _, _) = GB18030.decode(bytes);
    Ok(text.into_owned())
}

#[tauri::command]
pub async fn read_work_docx(root: String, rel: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || read_work_docx_blocking(root, rel))
        .await
        .map_err(|e| e.to_string())?
}

fn read_work_docx_blocking(root: String, rel: String) -> Result<String, String> {
    let target_canon = existing_work_path(&root, &rel, false)?;
    let meta = fs::metadata(&target_canon).map_err(|e| e.to_string())?;
    if meta.is_dir() {
        return Err("这是一个目录".into());
    }
    if meta.len() > DOCX_PREVIEW_LIMIT {
        return Err(format!(
            "docx 文件过大（{} MB），不在内置预览中解析",
            meta.len() / 1024 / 1024
        ));
    }
    let ext = target_canon
        .extension()
        .and_then(|s| s.to_str())
        .unwrap_or_default()
        .to_ascii_lowercase();
    if ext != "docx" {
        return Err("只支持预览 .docx 文件".into());
    }
    let file = fs::File::open(&target_canon).map_err(|e| e.to_string())?;
    let mut archive = zip::ZipArchive::new(file).map_err(|e| format!("无法读取 docx：{e}"))?;
    let mut names: Vec<String> = (0..archive.len())
        .filter_map(|i| archive.by_index(i).ok().map(|file| file.name().to_string()))
        .filter(|name| {
            name == "word/document.xml"
                || (name.starts_with("word/header") && name.ends_with(".xml"))
                || (name.starts_with("word/footer") && name.ends_with(".xml"))
                || name == "word/footnotes.xml"
                || name == "word/endnotes.xml"
        })
        .collect();
    names.sort_by_key(|name| if name == "word/document.xml" { 0 } else { 1 });

    let mut out = String::new();
    for name in names {
        let mut part = archive.by_name(&name).map_err(|e| e.to_string())?;
        let mut xml = String::new();
        part.read_to_string(&mut xml).map_err(|e| e.to_string())?;
        let extracted = extract_docx_xml_text(&xml);
        if extracted.trim().is_empty() {
            continue;
        }
        if !out.is_empty() && !out.ends_with("\n\n") {
            out.push('\n');
        }
        out.push_str(extracted.trim());
        out.push('\n');
        if out.len() > DOCX_TEXT_PREVIEW_LIMIT {
            out.truncate(DOCX_TEXT_PREVIEW_LIMIT);
            out.push_str("\n\n…");
            break;
        }
    }
    let text = out.trim().to_string();
    if text.is_empty() {
        Err("docx 没有可预览正文".into())
    } else {
        Ok(text)
    }
}

fn push_docx_break(out: &mut String) {
    while out.ends_with(' ') || out.ends_with('\t') {
        out.pop();
    }
    if !out.ends_with('\n') {
        out.push('\n');
    }
}

fn decode_xml_entities(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    let mut rest = input;
    while let Some(idx) = rest.find('&') {
        out.push_str(&rest[..idx]);
        rest = &rest[idx + 1..];
        let Some(end) = rest.find(';') else {
            out.push('&');
            out.push_str(rest);
            return out;
        };
        let entity = &rest[..end];
        match entity {
            "amp" => out.push('&'),
            "lt" => out.push('<'),
            "gt" => out.push('>'),
            "quot" => out.push('"'),
            "apos" => out.push('\''),
            _ if entity.starts_with("#x") => {
                if let Ok(value) = u32::from_str_radix(&entity[2..], 16) {
                    if let Some(ch) = char::from_u32(value) {
                        out.push(ch);
                    }
                }
            }
            _ if entity.starts_with('#') => {
                if let Ok(value) = entity[1..].parse::<u32>() {
                    if let Some(ch) = char::from_u32(value) {
                        out.push(ch);
                    }
                }
            }
            _ => {
                out.push('&');
                out.push_str(entity);
                out.push(';');
            }
        }
        rest = &rest[end + 1..];
    }
    out.push_str(rest);
    out
}

fn extract_docx_xml_text(xml: &str) -> String {
    let mut out = String::new();
    let mut pos = 0;
    while let Some(start_rel) = xml[pos..].find('<') {
        let start = pos + start_rel;
        let Some(end_rel) = xml[start..].find('>') else {
            break;
        };
        let end = start + end_rel;
        let tag = xml[start + 1..end].trim();
        let normalized = tag.trim_start_matches('/').trim_end_matches('/').trim();
        let name = normalized.split_whitespace().next().unwrap_or_default();
        if matches!(name, "w:t" | "a:t" | "m:t") && !tag.starts_with('/') {
            let close_tag = format!("</{name}>");
            let content_start = end + 1;
            if let Some(close_rel) = xml[content_start..].find(&close_tag) {
                let close = content_start + close_rel;
                out.push_str(&decode_xml_entities(&xml[content_start..close]));
                pos = close + close_tag.len();
                continue;
            }
        } else if name == "w:tab" && !tag.starts_with('/') {
            out.push('\t');
        } else if matches!(name, "w:br" | "w:cr") && !tag.starts_with('/') {
            push_docx_break(&mut out);
        } else if matches!(name, "w:p" | "w:tr") && tag.starts_with('/') {
            push_docx_break(&mut out);
        }
        pos = end + 1;
    }
    out.lines()
        .map(str::trim_end)
        .collect::<Vec<_>>()
        .join("\n")
        .replace("\n\n\n", "\n\n")
}

fn is_search_text_file(path: &Path) -> bool {
    matches!(
        path.extension()
            .and_then(|s| s.to_str())
            .unwrap_or_default()
            .to_ascii_lowercase()
            .as_str(),
        "txt"
            | "md"
            | "markdown"
            | "mdx"
            | "json"
            | "jsonl"
            | "yaml"
            | "yml"
            | "toml"
            | "py"
            | "sh"
            | "bash"
            | "zsh"
            | "rs"
            | "ts"
            | "tsx"
            | "js"
            | "jsx"
            | "cjs"
            | "mjs"
            | "css"
            | "html"
            | "xml"
            | "svg"
            | "srt"
            | "csv"
            | "log"
            | "sql"
    )
}

fn search_preview(line: &str) -> String {
    let compact = line.trim().replace('\t', "  ");
    compact.chars().take(240).collect()
}

fn text_matches(path: &Path, matcher: &Regex) -> Vec<WorkSearchMatch> {
    let Ok(meta) = fs::metadata(path) else {
        return Vec::new();
    };
    if !meta.is_file() || meta.len() > WORK_SEARCH_TEXT_LIMIT || !is_search_text_file(path) {
        return Vec::new();
    }
    let Ok(bytes) = fs::read(path) else {
        return Vec::new();
    };
    if bytes.contains(&0) {
        return Vec::new();
    }
    let text = String::from_utf8_lossy(&bytes);
    let mut matches = Vec::new();
    for (idx, line) in text.lines().enumerate() {
        if matcher.is_match(line) {
            matches.push(WorkSearchMatch {
                line: idx + 1,
                preview: search_preview(line),
            });
            if matches.len() >= WORK_SEARCH_MATCH_LIMIT_PER_FILE {
                break;
            }
        }
    }
    matches
}

struct SearchOptions<'a> {
    matcher: &'a Regex,
}

fn search_work_dir(
    dir: &Path,
    prefix: &str,
    depth: usize,
    opts: &SearchOptions<'_>,
    results: &mut Vec<WorkSearchResult>,
    scanned: &mut usize,
) -> bool {
    if depth > WORK_SEARCH_DEPTH_LIMIT {
        return false;
    }
    if *scanned >= WORK_SEARCH_FILE_LIMIT || results.len() >= WORK_SEARCH_RESULT_LIMIT {
        return true;
    }
    let mut entries: Vec<_> = match fs::read_dir(dir) {
        Ok(rd) => rd.flatten().collect(),
        Err(_) => return false,
    };
    entries.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    for e in entries {
        if *scanned >= WORK_SEARCH_FILE_LIMIT || results.len() >= WORK_SEARCH_RESULT_LIMIT {
            return true;
        }
        let name = e.file_name().to_string_lossy().to_string();
        if should_skip_tree_entry(&name) {
            continue;
        }
        let rel = if prefix.is_empty() {
            name.clone()
        } else {
            format!("{prefix}/{name}")
        };
        let path = e.path();
        if path.is_dir() {
            if search_work_dir(&path, &rel, depth + 1, opts, results, scanned) {
                return true;
            }
            continue;
        }
        *scanned += 1;
        let meta = match fs::metadata(&path) {
            Ok(meta) if meta.is_file() => meta,
            _ => continue,
        };
        let name_match = opts.matcher.is_match(&rel);
        let matches = text_matches(&path, opts.matcher);
        if name_match || !matches.is_empty() {
            results.push(WorkSearchResult {
                path: rel,
                name,
                size: meta.len(),
                name_match,
                matches,
            });
        }
    }
    false
}

#[tauri::command]
pub fn search_work_files(
    root: String,
    query: String,
    case_sensitive: Option<bool>,
    whole_word: Option<bool>,
    use_regex: Option<bool>,
) -> Result<WorkSearchResponse, String> {
    let query = query.trim().to_string();
    if query.is_empty() {
        return Ok(WorkSearchResponse::default());
    }
    let base = existing_work_path(&root, "", true)?;
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    let case_sensitive = case_sensitive.unwrap_or(false);
    let mut source = if use_regex.unwrap_or(false) {
        query.clone()
    } else {
        regex::escape(&query)
    };
    if whole_word.unwrap_or(false) {
        source = format!(r"\b(?:{source})\b");
    }
    let matcher = regex::RegexBuilder::new(&source)
        .case_insensitive(!case_sensitive)
        .build()
        .map_err(|e| format!("搜索表达式无效：{e}"))?;
    let opts = SearchOptions { matcher: &matcher };
    let mut results = Vec::new();
    let mut scanned = 0usize;
    let capped = search_work_dir(&base, "", 0, &opts, &mut results, &mut scanned);
    Ok(WorkSearchResponse {
        query,
        results,
        scanned,
        capped,
    })
}

#[tauri::command]
pub fn write_work_file(
    root: String,
    rel: String,
    text: String,
    expected_mtime: Option<u64>,
) -> Result<WorkFileWriteResult, String> {
    if text.as_bytes().len() as u64 > TEXT_EDIT_LIMIT {
        return Err(format!(
            "文件过大（{} MB），不在内置编辑器保存",
            text.as_bytes().len() / 1024 / 1024
        ));
    }
    if text.as_bytes().contains(&0) {
        return Err("拒绝保存含 NUL 字节的文本".into());
    }
    let target = existing_work_path(&root, &rel, false)?;
    let meta = fs::metadata(&target).map_err(|e| e.to_string())?;
    if meta.is_dir() {
        return Err("这是一个目录".into());
    }
    if let Some(expected) = expected_mtime {
        let current = metadata_mtime(&meta).unwrap_or(0);
        if expected > 0 && current > 0 && current != expected {
            return Err("文件已被外部修改，请重新载入后再保存".into());
        }
    }
    fs::write(&target, text.as_bytes()).map_err(|e| e.to_string())?;
    let next = fs::metadata(&target).map_err(|e| e.to_string())?;
    Ok(WorkFileWriteResult {
        size: next.len(),
        mtime: metadata_mtime(&next).unwrap_or(0),
    })
}

fn sanitize_capture_label(label: &str) -> String {
    let mut out = String::new();
    let mut last_was_sep = false;
    for ch in label.trim().chars() {
        let illegal = ch.is_control() || matches!(ch, '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|');
        if illegal || ch.is_whitespace() {
            if !last_was_sep && !out.is_empty() {
                out.push('_');
                last_was_sep = true;
            }
            continue;
        }
        out.push(ch);
        last_was_sep = false;
        if out.chars().count() >= 48 {
            break;
        }
    }
    let clean = out.trim_matches('_').to_string();
    if clean.is_empty() {
        "canvas_capture".into()
    } else {
        clean
    }
}

#[tauri::command]
pub fn save_canvas_capture(
    root: String,
    image_data: String,
    label: String,
) -> Result<CanvasCaptureSaveResult, String> {
    let base = existing_work_path(&root, "", true)?;
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    let encoded = image_data
        .strip_prefix("data:image/png;base64,")
        .ok_or("仅支持 PNG 截图")?;
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(encoded)
        .map_err(|e| format!("截图数据无效：{e}"))?;
    if bytes.is_empty() {
        return Err("截图数据为空".into());
    }
    if bytes.len() > 32 * 1024 * 1024 {
        return Err("截图过大，已拒绝保存".into());
    }
    let dir = base.join("画布");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let ms = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_millis();
    let filename = format!("{}_{}.png", sanitize_capture_label(&label), ms);
    let target = dir.join(&filename);
    fs::write(&target, bytes).map_err(|e| e.to_string())?;
    Ok(CanvasCaptureSaveResult {
        rel: format!("画布/{filename}"),
        path: target.to_string_lossy().to_string(),
    })
}

fn validate_rel_path(rel: &str, allow_empty: bool) -> Result<(), String> {
    if rel.is_empty() {
        return if allow_empty {
            Ok(())
        } else {
            Err("非法文件路径".into())
        };
    }
    if !allow_empty && rel == "." {
        return Err("非法文件路径".into());
    }
    let p = Path::new(rel);
    if p.is_absolute() {
        return Err("非法文件路径".into());
    }
    let mut has_normal = false;
    for c in p.components() {
        match c {
            Component::Normal(_) => has_normal = true,
            Component::CurDir => {}
            _ => return Err("非法文件路径".into()),
        }
    }
    if !allow_empty && !has_normal {
        return Err("非法文件路径".into());
    }
    Ok(())
}

fn validate_entry_name(name: &str) -> Result<String, String> {
    let trimmed = name.trim();
    if trimmed.is_empty()
        || trimmed == "."
        || trimmed == ".."
        || trimmed.contains('/')
        || trimmed.contains('\\')
        || trimmed.contains('\0')
    {
        return Err("名称含非法字符".into());
    }
    Ok(trimmed.to_string())
}

fn validate_work_name(name: &str) -> Result<String, String> {
    let clean = validate_entry_name(name)?;
    if clean.starts_with('.') {
        return Err("作品名含非法字符".into());
    }
    Ok(clean)
}

fn existing_work_path(root: &str, rel: &str, allow_empty: bool) -> Result<PathBuf, String> {
    validate_rel_path(rel, allow_empty)?;
    let base = Path::new(root);
    let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
    let target = if rel.is_empty() {
        base.to_path_buf()
    } else {
        base.join(rel)
    };
    let target_canon = fs::canonicalize(target).map_err(|e| e.to_string())?;
    if target_canon == base_canon || target_canon.starts_with(&base_canon) {
        Ok(target_canon)
    } else {
        Err("路径越界，已拒绝".into())
    }
}

#[tauri::command]
pub fn create_work_entry(
    root: String,
    parent_rel: String,
    name: String,
    kind: String,
) -> Result<String, String> {
    validate_rel_path(&parent_rel, true)?;
    let clean_name = validate_entry_name(&name)?;
    let parent = existing_work_path(&root, &parent_rel, true)?;
    if !parent.is_dir() {
        return Err("父路径不是文件夹".into());
    }
    let target = parent.join(&clean_name);
    if target.exists() {
        return Err("同名文件或文件夹已存在".into());
    }
    match kind.as_str() {
        "file" => {
            fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&target)
                .map_err(|e| e.to_string())?;
        }
        "folder" => fs::create_dir(&target).map_err(|e| e.to_string())?,
        _ => return Err("未知创建类型".into()),
    }
    let rel = if parent_rel.is_empty() {
        clean_name
    } else {
        format!("{parent_rel}/{clean_name}")
    };
    Ok(rel)
}

fn supported_import_ext(path: &Path) -> bool {
    matches!(
        path.extension()
            .and_then(|s| s.to_str())
            .unwrap_or_default()
            .to_ascii_lowercase()
            .as_str(),
        "txt" | "md" | "markdown" | "mdx" | "docx" | "pdf"
    )
}

fn unique_import_target(parent: &Path, file_name: &str) -> Result<(PathBuf, String), String> {
    let original = validate_entry_name(file_name)?;
    let candidate = parent.join(&original);
    if !candidate.exists() {
        return Ok((candidate, original));
    }

    let path = Path::new(&original);
    let stem = path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or(&original);
    let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
    for idx in 2..1000 {
        let name = if ext.is_empty() {
            format!("{stem} ({idx})")
        } else {
            format!("{stem} ({idx}).{ext}")
        };
        let target = parent.join(&name);
        if !target.exists() {
            return Ok((target, name));
        }
    }
    Err("同名文件过多，无法导入".into())
}

fn validated_import_source(source: &str) -> Result<PathBuf, String> {
    let src = PathBuf::from(source);
    let src_canon = fs::canonicalize(&src).map_err(|e| format!("无法读取源文件：{source}：{e}"))?;
    let meta = fs::metadata(&src_canon).map_err(|e| e.to_string())?;
    if !meta.is_file() {
        return Err(format!("只能导入文件：{source}"));
    }
    if !supported_import_ext(&src) {
        return Err(format!("暂不支持该格式：{source}"));
    }
    Ok(src_canon)
}

fn source_file_name(path: &Path, source: &str) -> Result<String, String> {
    path.file_name()
        .and_then(|s| s.to_str())
        .map(|s| s.to_string())
        .ok_or_else(|| format!("无法识别文件名：{source}"))
}

fn source_work_name(path: &Path, source: &str) -> Result<String, String> {
    let stem = path
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or_else(|| format!("无法识别小说名：{source}"))?;
    validate_work_name(stem)
}

#[tauri::command]
pub fn import_work_sources(root: String, sources: Vec<String>) -> Result<Vec<String>, String> {
    if sources.is_empty() {
        return Err("没有选择可导入的文件".into());
    }
    let base = Path::new(&root);
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
    let mut imported = Vec::new();

    for source in sources {
        let src_canon = validated_import_source(&source)?;
        let file_name = source_file_name(Path::new(&source), &source)?;
        let (target, rel) = unique_import_target(&base_canon, &file_name)?;
        fs::copy(&src_canon, &target).map_err(|e| format!("导入失败：{source}：{e}"))?;
        imported.push(rel);
    }

    Ok(imported)
}

#[tauri::command]
pub fn import_n2d_novel_sources(
    root: String,
    sources: Vec<String>,
) -> Result<ImportWorkSourcesResult, String> {
    if sources.is_empty() {
        return Err("没有选择可导入的小说".into());
    }
    if sources.len() != 1 {
        return Err("一次只能导入一本小说".into());
    }
    let base = Path::new(&root);
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    let base_canon = fs::canonicalize(base).map_err(|e| e.to_string())?;
    if !work_is_empty_path(&base_canon) {
        return Err("只有空作品可以直接按小说初始化".into());
    }

    let source = &sources[0];
    let src_canon = validated_import_source(source)?;
    let source_path = Path::new(source);
    let work_name = source_work_name(source_path, source)?;
    let file_name = source_file_name(source_path, source)?;
    let parent = base_canon
        .parent()
        .ok_or_else(|| "无法定位作品父目录".to_string())?;
    let current_name = base_canon
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or_default();
    let work_root = if current_name == work_name {
        base_canon
    } else {
        let target = parent.join(&work_name);
        if target.exists() {
            return Err(format!("已存在同名作品：{work_name}"));
        }
        fs::rename(&base_canon, &target).map_err(|e| format!("作品目录重命名失败：{e}"))?;
        target
    };

    let novel_dir = work_root.join("小说");
    fs::create_dir_all(&novel_dir).map_err(|e| format!("创建小说目录失败：{e}"))?;
    let (target, file_rel) = unique_import_target(&novel_dir, &file_name)?;
    fs::copy(&src_canon, &target).map_err(|e| format!("导入失败：{source}：{e}"))?;
    Ok(ImportWorkSourcesResult {
        root: work_root.to_string_lossy().to_string(),
        name: work_name,
        imported: vec![format!("小说/{file_rel}")],
    })
}

#[tauri::command]
pub fn rename_work_entry(root: String, rel: String, new_name: String) -> Result<String, String> {
    validate_rel_path(&rel, false)?;
    let clean_name = validate_entry_name(&new_name)?;
    let target = existing_work_path(&root, &rel, false)?;
    let parent = target
        .parent()
        .ok_or_else(|| "无法定位父目录".to_string())?;
    let next = parent.join(&clean_name);
    if next.exists() {
        return Err("同名文件或文件夹已存在".into());
    }
    fs::rename(&target, &next).map_err(|e| e.to_string())?;
    let parent_rel = Path::new(&rel)
        .parent()
        .and_then(|p| {
            let s = p.to_string_lossy().to_string();
            if s.is_empty() || s == "." {
                None
            } else {
                Some(s)
            }
        })
        .unwrap_or_default();
    Ok(if parent_rel.is_empty() {
        clean_name
    } else {
        format!("{parent_rel}/{clean_name}")
    })
}

#[tauri::command]
pub fn delete_work_entry(root: String, rel: String) -> Result<(), String> {
    validate_rel_path(&rel, false)?;
    let target = existing_work_path(&root, &rel, false)?;
    let base = fs::canonicalize(&root).map_err(|e| e.to_string())?;
    if target == base {
        return Err("拒绝删除作品根目录".into());
    }
    trash::delete(&target).map_err(|e| format!("移入垃圾桶失败：{e}"))
}

fn spawn_os_open(program: &str, args: &[&str]) -> Result<(), String> {
    Command::new(program)
        .args(args)
        .spawn()
        .map(|_| ())
        .map_err(|e| e.to_string())
}

fn open_url_in_os(url: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        return spawn_os_open("open", &[url]);
    }
    #[cfg(target_os = "windows")]
    {
        return Command::new("cmd")
            .args(["/C", "start", "", url])
            .spawn()
            .map(|_| ())
            .map_err(|e| e.to_string());
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        return spawn_os_open("xdg-open", &[url]);
    }
}

#[tauri::command]
pub fn reveal_work_entry(root: String, rel: String) -> Result<(), String> {
    let target = existing_work_path(&root, &rel, true)?;
    let target_s = target.to_string_lossy().to_string();

    #[cfg(target_os = "macos")]
    {
        return spawn_os_open("open", &["-R", &target_s]);
    }
    #[cfg(target_os = "windows")]
    {
        if target.is_dir() {
            return spawn_os_open("explorer", &[&target_s]);
        }
        let select_arg = format!("/select,{target_s}");
        return spawn_os_open("explorer", &[&select_arg]);
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let dir = if target.is_dir() {
            target
        } else {
            target
                .parent()
                .map(Path::to_path_buf)
                .ok_or("无法定位父目录")?
        };
        let dir_s = dir.to_string_lossy().to_string();
        return spawn_os_open("xdg-open", &[&dir_s]);
    }
}

#[tauri::command]
pub fn open_work_entry(root: String, rel: String) -> Result<(), String> {
    let target = existing_work_path(&root, &rel, true)?;
    let target_s = target.to_string_lossy().to_string();

    #[cfg(target_os = "macos")]
    {
        return spawn_os_open("open", &[&target_s]);
    }
    #[cfg(target_os = "windows")]
    {
        return Command::new("cmd")
            .args(["/C", "start", "", &target_s])
            .spawn()
            .map(|_| ())
            .map_err(|e| e.to_string());
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        return spawn_os_open("xdg-open", &[&target_s]);
    }
}

#[tauri::command]
pub fn open_source_repo() -> Result<(), String> {
    open_url_in_os("https://github.com/anton6202527/anime-armory/releases")
}

#[tauri::command]
pub fn open_external_url(url: String) -> Result<(), String> {
    let url = url.trim();
    if !(url.starts_with("https://") || url.starts_with("http://")) {
        return Err("只允许打开 http(s) 下载链接".into());
    }
    open_url_in_os(url)
}

// ---- AI agent CLI detection (for the operation-page terminal) ----

#[derive(Serialize)]
pub struct AgentInfo {
    id: String,
    name: String,
    command: String, // launch command to run in the terminal
    found: bool,
    path: String,
    image: String, // image-gen capability: "yes" | "maybe" | "no"
    note: String,
}

/// Run a command with a hard timeout. Returns stdout (lossy utf8) on a clean
/// exit, None on spawn error / timeout / non-zero. stdin is closed so the child
/// can't block on an interactive prompt.
fn run_capped(program: &str, args: &[&str], secs: u64) -> Option<String> {
    let mut child = Command::new(program)
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    let mut out_pipe = child.stdout.take()?;
    let oh = thread::spawn(move || {
        let mut b = Vec::new();
        let _ = out_pipe.read_to_end(&mut b);
        b
    });
    let deadline = Instant::now() + Duration::from_secs(secs);
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) => {
                if Instant::now() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return None;
                }
                thread::sleep(Duration::from_millis(60));
            }
            Err(_) => return None,
        }
    }
    let bytes = oh.join().ok()?;
    Some(String::from_utf8_lossy(&bytes).into_owned())
}

/// Detect locally-installed AI agent CLIs on the terminal's PATH and flag which
/// ones can generate images (生图). PATH is resolved through the user's LOGIN
/// shell so it matches exactly what the operation-page terminal sees (conda,
/// npm globals, ~/.local/bin). Missing mainstream CLIs are still returned so the
/// UI can list them disabled. Codex's image capability is refined with a cheap,
/// bounded `codex features list` probe — mirroring skills/n2d-image cli_registry.
#[tauri::command]
pub fn detect_agents() -> Vec<AgentInfo> {
    let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".to_string());

    // resolve every candidate command in ONE login-shell call (PATH parity)
    let probe = r#"for c in claude codex opencode gemini kimi kimi-cli; do p=$(command -v "$c" 2>/dev/null) && printf '%s\t%s\n' "$c" "$p"; done"#;
    let mut found: HashMap<String, String> = HashMap::new();
    if let Some(out) = run_capped(&shell, &["-lc", probe], 8) {
        for line in out.lines() {
            if let Some((c, p)) = line.split_once('\t') {
                if !p.trim().is_empty() {
                    found.insert(c.to_string(), p.trim().to_string());
                }
            }
        }
    }

    // Codex image capability: refine "maybe" via its own feature/plugin list.
    let codex_image = if found.contains_key("codex") {
        run_capped(
            &shell,
            &[
                "-lc",
                "codex features list 2>/dev/null; codex plugin list 2>/dev/null",
            ],
            8,
        )
        .map(|s| {
            // a line naming image_generation with a truthy/enabled token, or an
            // explicit image-gen plugin — avoids matching e.g. `resize_all_images`
            s.lines().any(|line| {
                let l = line.to_lowercase();
                (l.contains("image_generation")
                    && (l.contains("true")
                        || l.contains("stable")
                        || l.contains("enabled")
                        || l.contains("ok")))
                    || (l.contains("image") && l.contains("plugin"))
            })
        })
    } else {
        None
    };
    let (codex_img, codex_note) = match codex_image {
        Some(true) => ("yes", "codex 已暴露 image_generation/图像能力，可生图"),
        Some(false) => (
            "maybe",
            "codex 在 PATH，但 features/plugin 未列出 image_generation（可能需登录或启用图像插件）",
        ),
        None => ("maybe", "codex 生图需启用 image_generation 能力/插件"),
    };
    let kimi_cmd = if found.contains_key("kimi") {
        "kimi"
    } else {
        "kimi-cli"
    };
    let kimi_path = found
        .get("kimi")
        .or_else(|| found.get("kimi-cli"))
        .cloned()
        .unwrap_or_default();
    let kimi_found = !kimi_path.is_empty();

    vec![
        AgentInfo {
            id: "claude".into(),
            name: "Claude Code".into(),
            command: "claude".into(),
            found: found.contains_key("claude"),
            path: found.get("claude").cloned().unwrap_or_default(),
            image: "no".into(),
            note: "对话 / Agent CLI，无原生生图能力".into(),
        },
        AgentInfo {
            id: "codex".into(),
            name: "Codex CLI".into(),
            command: "codex".into(),
            found: found.contains_key("codex"),
            path: found.get("codex").cloned().unwrap_or_default(),
            image: codex_img.into(),
            note: codex_note.into(),
        },
        AgentInfo {
            id: "opencode".into(),
            name: "OpenCode".into(),
            command: "opencode".into(),
            found: found.contains_key("opencode"),
            path: found.get("opencode").cloned().unwrap_or_default(),
            image: "no".into(),
            note: "开源终端 Agent；模型可走其 provider 配置，适合无付费专属 agent 的兜底入口"
                .into(),
        },
        AgentInfo {
            id: "gemini".into(),
            name: "Gemini CLI".into(),
            command: "gemini".into(),
            found: found.contains_key("gemini"),
            path: found.get("gemini").cloned().unwrap_or_default(),
            image: "no".into(),
            note: "Google Gemini 终端 Agent；模型、配额和登录状态由其全局配置决定".into(),
        },
        AgentInfo {
            id: "kimi".into(),
            name: "Kimi CLI".into(),
            command: kimi_cmd.into(),
            found: kimi_found,
            path: kimi_path,
            image: "no".into(),
            note: "Kimi / Moonshot 终端 Agent；模型、配额和登录状态由其全局配置决定".into(),
        },
    ]
}

/// Pull `name:` / `description:` out of a SKILL.md YAML frontmatter block
/// (the single-line values between the leading `---` fences).
fn parse_frontmatter(md: &str) -> Option<(String, String)> {
    let mut lines = md.lines();
    if lines.next()?.trim() != "---" {
        return None;
    }
    let (mut name, mut desc) = (None, None);
    for line in lines {
        let t = line.trim_start();
        if t == "---" {
            break;
        }
        if let Some(v) = t.strip_prefix("name:") {
            name = Some(unquote(v.trim()));
        } else if let Some(v) = t.strip_prefix("description:") {
            desc = Some(unquote(v.trim()));
        }
    }
    Some((name?, desc.unwrap_or_default()))
}

fn unquote(s: &str) -> String {
    let s = s.trim();
    if s.len() >= 2
        && ((s.starts_with('"') && s.ends_with('"')) || (s.starts_with('\'') && s.ends_with('\'')))
    {
        s[1..s.len() - 1].to_string()
    } else {
        s.to_string()
    }
}

/// List the skills belonging to one creative line: the dispatcher `<line>`
/// plus every `<line>-*` member, dispatcher first then alphabetical.
#[tauri::command]
pub fn list_skills(repo_root: String, line: String) -> Vec<SkillInfo> {
    let skills_dir = Path::new(&repo_root).join("skills");
    let prefix = format!("{line}-");
    let mut members: Vec<(String, SkillInfo)> = Vec::new();
    if let Ok(entries) = fs::read_dir(&skills_dir) {
        for e in entries.flatten() {
            let p = e.path();
            if !p.is_dir() {
                continue;
            }
            let dir_name = e.file_name().to_string_lossy().to_string();
            if dir_name != line && !dir_name.starts_with(&prefix) {
                continue;
            }
            let md = match fs::read_to_string(p.join("SKILL.md")) {
                Ok(t) => t,
                Err(_) => continue,
            };
            let (name, description) =
                parse_frontmatter(&md).unwrap_or_else(|| (dir_name.clone(), String::new()));
            members.push((
                dir_name.clone(),
                SkillInfo {
                    name,
                    description,
                    dir: dir_name,
                },
            ));
        }
    }
    // dispatcher (exact line name) first, then the rest alphabetically by dir name
    members.sort_by(|a, b| {
        let rank = |n: &str| if n == line { 0 } else { 1 };
        rank(&a.0).cmp(&rank(&b.0)).then(a.0.cmp(&b.0))
    });
    members.into_iter().map(|(_, s)| s).collect()
}

/// Resolve (and create) the app's dedicated works workspace `<home>/AnimeArmory/`.
/// This is kept SEPARATE from the skills repo so app works never touch the
/// repo's demo product dirs (创作区/制漫剧/ etc.). Cross-platform (HOME / USERPROFILE).
#[tauri::command]
pub fn default_workspace() -> Result<String, String> {
    let home = dirs::home_dir().ok_or("无法定位用户主目录")?;
    let ws = home.join("AnimeArmory");
    fs::create_dir_all(&ws).map_err(|e| e.to_string())?;
    Ok(ws.to_string_lossy().to_string())
}

fn has_skills_repo(path: &Path) -> bool {
    path.join("skills").join("README.md").is_file()
}

fn find_skills_repo_from(start: &Path) -> Option<PathBuf> {
    let mut cur = if start.is_dir() {
        start.to_path_buf()
    } else {
        start.parent()?.to_path_buf()
    };
    loop {
        if has_skills_repo(&cur) {
            return Some(cur);
        }
        if !cur.pop() {
            return None;
        }
    }
}

/// Resolve which directory the app uses as its **skills repo** (drives the skill
/// roster + `run.py`). Priority:
///   1. an explicit frontend/env override if it actually has `skills/`;
///   2. the live checkout inferred from cwd / Cargo manifest dir in dev;
///   3. the bundled copy shipped inside the app
///      (`<resourceDir>/resources`, written by sync-skills.cjs) — the
///      self-contained path for an installed app with no source checkout.
/// Falls back to the explicit override as a last resort so the frontend always
/// has a value when one was provided.
#[tauri::command]
pub fn resolve_repo(app: tauri::AppHandle, dev_repo: String) -> String {
    let explicit = dev_repo.trim();
    if !explicit.is_empty() && has_skills_repo(Path::new(explicit)) {
        return explicit.to_string();
    }
    if let Ok(env_repo) = std::env::var("ANIME_ARMORY_REPO") {
        let env_repo = env_repo.trim();
        if !env_repo.is_empty() && has_skills_repo(Path::new(env_repo)) {
            return env_repo.to_string();
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        if let Some(repo) = find_skills_repo_from(&cwd) {
            return repo.to_string_lossy().to_string();
        }
    }
    if let Some(repo) = find_skills_repo_from(Path::new(env!("CARGO_MANIFEST_DIR"))) {
        return repo.to_string_lossy().to_string();
    }
    if let Ok(res) = app.path().resource_dir() {
        let bundled = res.join("resources");
        if has_skills_repo(&bundled) {
            return bundled.to_string_lossy().to_string();
        }
    }
    if !explicit.is_empty() {
        return explicit.to_string();
    }
    std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .to_string_lossy()
        .to_string()
}

fn copy_dir_all(src: &Path, dst: &Path) -> std::io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let from = entry.path();
        let to = dst.join(entry.file_name());
        if from.is_dir() {
            copy_dir_all(&from, &to)?;
        } else {
            fs::copy(&from, &to)?;
        }
    }
    Ok(())
}

fn seed_resource_works(
    resource_root: &Path,
    workspace: &Path,
    demo_origins: &mut BTreeSet<String>,
    mark_demo: bool,
) -> Result<(usize, bool), String> {
    if !resource_root.is_dir() {
        return Ok((0, false));
    }

    let mut seeded = 0usize;
    let mut origins_changed = false;
    for line in fs::read_dir(resource_root)
        .map_err(|e| e.to_string())?
        .flatten()
    {
        let line_dir = line.path();
        if !line_dir.is_dir() {
            continue;
        }
        let product = line.file_name();
        let product_name = product.to_string_lossy().to_string();
        for work in fs::read_dir(&line_dir)
            .map_err(|e| e.to_string())?
            .flatten()
        {
            let from = work.path();
            if !from.is_dir() {
                continue;
            }
            let work_name = work.file_name().to_string_lossy().to_string();
            let rel = demo_rel(&product_name, &work_name);
            if mark_demo {
                if demo_origins.insert(rel) {
                    origins_changed = true;
                }
            } else if demo_origins.remove(&rel) {
                origins_changed = true;
            }
            let dst = workspace
                .join(CREATION_ROOT)
                .join(&product)
                .join(work.file_name());
            if dst.exists() {
                continue; // never clobber existing user work
            }
            copy_dir_all(&from, &dst).map_err(|e| e.to_string())?;
            seeded += 1;
        }
    }
    Ok((seeded, origins_changed))
}

fn demo_cache_dir() -> Result<PathBuf, String> {
    let base = dirs::cache_dir()
        .or_else(dirs::data_local_dir)
        .ok_or("无法定位下载缓存目录")?;
    let dir = base.join(APP_CONFIG_DIR).join("demo-downloads");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

fn unique_demo_temp_dir(line_key: &str) -> Result<PathBuf, String> {
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_millis();
    let dir = demo_cache_dir()?.join(format!("{line_key}-{millis}"));
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 64 * 1024];
    loop {
        let n = file.read(&mut buf).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    let digest = hasher.finalize();
    Ok(digest.iter().map(|b| format!("{b:02x}")).collect())
}

fn download_file(url: &str, dst: &Path) -> Result<(), String> {
    let mut response = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(600))
        .user_agent("AnimeArmory Desktop")
        .build()
        .map_err(|e| e.to_string())?
        .get(url)
        .send()
        .map_err(|e| format!("下载失败：{e}"))?
        .error_for_status()
        .map_err(|e| format!("下载失败：{e}"))?;
    let mut out = fs::File::create(dst).map_err(|e| e.to_string())?;
    std::io::copy(&mut response, &mut out).map_err(|e| e.to_string())?;
    Ok(())
}

fn extract_zip_safe(zip_path: &Path, dst: &Path) -> Result<(), String> {
    let file = fs::File::open(zip_path).map_err(|e| e.to_string())?;
    let mut archive = zip::ZipArchive::new(file).map_err(|e| format!("zip 无效：{e}"))?;
    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| e.to_string())?;
        let Some(rel) = entry.enclosed_name().map(|p| p.to_owned()) else {
            return Err(format!("zip 内含非法路径：{}", entry.name()));
        };
        let out_path = dst.join(rel);
        if entry.is_dir() {
            fs::create_dir_all(&out_path).map_err(|e| e.to_string())?;
            continue;
        }
        if let Some(parent) = out_path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let mut out = fs::File::create(&out_path).map_err(|e| e.to_string())?;
        std::io::copy(&mut entry, &mut out).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn find_extracted_demo_root(
    extract_dir: &Path,
    info: &DemoDownloadInfo,
) -> Result<PathBuf, String> {
    let expected = extract_dir.join(&info.rel);
    if expected.join("_进度.md").is_file() {
        return Ok(expected);
    }
    let named = extract_dir.join(&info.name);
    if named.join("_进度.md").is_file() {
        return Ok(named);
    }
    if extract_dir.join("_进度.md").is_file() {
        return Ok(extract_dir.to_path_buf());
    }
    Err(format!("示例包结构不匹配，未找到 {} 或 _进度.md", info.rel))
}

fn select_demo_info_for_line(
    app: &tauri::AppHandle,
    workspace: &Path,
    line_key: &str,
) -> Result<DemoDownloadInfo, String> {
    if product_for_line_key(line_key).is_none() {
        return Err("未知系列".into());
    }
    load_demo_catalog(app)
        .iter()
        .filter_map(|entry| demo_info_from_entry(workspace, entry))
        .find(|info| info.line_key == line_key)
        .ok_or_else(|| "该系列没有配置可下载示例".into())
}

/// Download one line's demo zip from GitHub Releases, extract it into the app
/// workspace, and tag it as a demo. Existing works are never overwritten.
#[tauri::command]
pub fn install_demo(
    app: tauri::AppHandle,
    workspace_root: String,
    line: String,
) -> Result<DemoInstallResult, String> {
    let line_key = line.trim();
    let workspace = Path::new(&workspace_root);
    fs::create_dir_all(workspace).map_err(|e| e.to_string())?;
    let info = select_demo_info_for_line(&app, workspace, line_key)?;
    validate_rel_path(&info.rel, false)?;

    let target = workspace.join(&info.rel);
    if target.exists() {
        let mut demo_origins = load_demo_origins(workspace);
        if demo_origins.insert(info.rel.clone()) {
            write_demo_origins(workspace, &demo_origins)?;
        }
        return Ok(DemoInstallResult {
            root: WorkRoot {
                name: info.name,
                path: target.to_string_lossy().to_string(),
                has_progress: target.join("_进度.md").is_file(),
                is_demo: true,
            },
            already_installed: true,
        });
    }

    let temp_dir = unique_demo_temp_dir(line_key)?;
    let zip_path = temp_dir.join(&info.asset_name);
    let extract_dir = temp_dir.join("extract");
    fs::create_dir_all(&extract_dir).map_err(|e| e.to_string())?;

    download_file(&info.download_url, &zip_path)?;
    if let Some(expected) = info.sha256.as_ref().filter(|s| !s.trim().is_empty()) {
        let actual = sha256_file(&zip_path)?;
        if actual.to_ascii_lowercase() != expected.trim().to_ascii_lowercase() {
            let _ = fs::remove_dir_all(&temp_dir);
            return Err("示例包校验失败，已拒绝安装".into());
        }
    }

    extract_zip_safe(&zip_path, &extract_dir)?;
    let extracted = find_extracted_demo_root(&extract_dir, &info)?;
    if let Some(parent) = target.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    copy_dir_all(&extracted, &target).map_err(|e| e.to_string())?;
    let _ = fs::remove_dir_all(&temp_dir);

    let mut demo_origins = load_demo_origins(workspace);
    demo_origins.insert(info.rel.clone());
    write_demo_origins(workspace, &demo_origins)?;

    Ok(DemoInstallResult {
        root: WorkRoot {
            name: info.name,
            path: target.to_string_lossy().to_string(),
            has_progress: target.join("_进度.md").is_file(),
            is_demo: true,
        },
        already_installed: false,
    })
}

/// Legacy bundled-work seeding. Current builds keep full demos in GitHub
/// Release assets, so this is normally a no-op; retained for older packages.
#[tauri::command]
pub fn seed_demos(app: tauri::AppHandle, workspace_root: String) -> Result<usize, String> {
    let ws = Path::new(&workspace_root);
    let res = match app.path().resource_dir() {
        Ok(r) => r,
        Err(e) => return Err(e.to_string()),
    };
    let seed = res.join("resources").join("seed").join(CREATION_ROOT);
    let demos = res.join("resources").join("demos").join(CREATION_ROOT);
    let mut seeded = 0usize;
    let mut demo_origins = load_demo_origins(ws);
    let mut origins_changed = false;

    let (seeded_normal, seed_origins_changed) =
        seed_resource_works(&seed, ws, &mut demo_origins, false)?;
    seeded += seeded_normal;
    origins_changed |= seed_origins_changed;

    let (seeded_demos, demo_origins_changed) =
        seed_resource_works(&demos, ws, &mut demo_origins, true)?;
    seeded += seeded_demos;
    origins_changed |= demo_origins_changed;

    if !seed.is_dir() && !demos.is_dir() {
        return Ok(0); // app was built with no bundled works
    }
    if origins_changed {
        write_demo_origins(ws, &demo_origins)?;
    }
    Ok(seeded)
}

/// Canonicalize `p`; if it doesn't exist yet, canonicalize its nearest existing
/// ancestor and re-append the missing tail (so symlinks on the existing part are
/// resolved). Used to vet a not-yet-created work path against the repo.
fn canon_lenient(p: &Path) -> Option<PathBuf> {
    if let Ok(c) = fs::canonicalize(p) {
        return Some(c);
    }
    let mut cur = p.parent();
    while let Some(dir) = cur {
        if let Ok(c) = fs::canonicalize(dir) {
            let rel = p.strip_prefix(dir).ok()?;
            return Some(c.join(rel));
        }
        cur = dir.parent();
    }
    None
}

/// True if `target` is the project/skills repo root or lives inside it. The app
/// must NEVER create or delete anything here — the repo's demos are not app works.
fn inside_repo(target: &Path, repo_root: &str) -> bool {
    if repo_root.is_empty() {
        return false;
    }
    match fs::canonicalize(repo_root) {
        Ok(repo) => target == repo || target.starts_with(&repo),
        Err(_) => false,
    }
}

/// Move a work folder to the OS Trash / Recycle Bin (recoverable). Guarded twice:
/// the target must live INSIDE the app's own workspace, and must NOT live inside
/// the project/skills repo — so it can never touch the repo's demos, even if the
/// workspace was (mis)pointed at the repo.
#[tauri::command]
pub fn delete_work(workspace_root: String, repo_root: String, path: String) -> Result<(), String> {
    let ws = fs::canonicalize(&workspace_root).map_err(|e| e.to_string())?;
    let target = fs::canonicalize(&path).map_err(|e| e.to_string())?;
    if target == ws || !target.starts_with(&ws) {
        return Err("拒绝删除：该作品不在 app 工作区内".into());
    }
    if inside_repo(&target, &repo_root) {
        return Err(
            "拒绝删除：该路径位于项目仓库内，已被隔离保护（仓库 demo 不是 app 作品）".into(),
        );
    }
    trash::delete(&target).map_err(|e| format!("移入垃圾桶失败：{e}"))?;
    Ok(())
}

/// Create an empty work folder `<line product dir>/<name>/` and return its
/// absolute path. The actual content pipeline is then driven by the line's
/// skill / terminal inside the Operation page.
#[tauri::command]
pub fn create_work(dir: String, repo_root: String, name: String) -> Result<String, String> {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return Err("作品名不能为空".into());
    }
    if trimmed.contains('/') || trimmed.contains('\\') || trimmed.starts_with('.') {
        return Err("作品名含非法字符".into());
    }
    // Hard isolation: never create works inside the project/skills repo.
    if let Some(resolved) = canon_lenient(Path::new(&dir)) {
        if inside_repo(&resolved, &repo_root) {
            return Err("拒绝创建：工作区位于项目仓库内，已被隔离保护".into());
        }
    }
    let path = Path::new(&dir).join(trimmed);
    if path.exists() {
        return Err(format!("作品已存在：{trimmed}"));
    }
    fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    Ok(path.to_string_lossy().to_string())
}

// ---- canvas ----

#[derive(Serialize, Default)]
pub struct QaFlag {
    severity: String,
    status: Option<String>,
    dimension: Option<String>,
    message: Option<String>,
    score: Option<f64>,
}

#[derive(Serialize, Default, Clone)]
pub struct CanvasFrame {
    role: String,
    label: String,
    abs: Option<String>,
    exists: bool,
    at_sec: Option<f64>,
    prompt: Option<String>,
}

#[derive(Serialize, Default)]
pub struct CanvasClip {
    id: String,
    number: Option<i64>,
    label: String,
    duration: Option<f64>,
    scene: Option<String>,
    rhythm: Option<String>,
    template: Option<String>,
    first_frame_abs: Option<String>,
    first_frame_exists: bool,
    video_abs: Option<String>,
    video_exists: bool,
    frames: Vec<CanvasFrame>,
    prompt: Option<String>,
    qa: Vec<QaFlag>,
    score: Option<f64>,
    qa_blocks: i64,
    qa_warnings: i64,
    qa_infos: i64,
}

#[derive(Serialize, Default)]
pub struct CanvasSeam {
    from: String,
    to: String,
    transition: Option<String>,
}

#[derive(Serialize, Default)]
pub struct CanvasMetric {
    label: String,
    value: String,
}

#[derive(Serialize, Default)]
pub struct CanvasScoreDimension {
    key: Option<String>,
    label: String,
    status: Option<String>,
    score: Option<f64>,
    blocks: i64,
    warnings: i64,
    infos: i64,
    return_to_stage: Option<String>,
    rerun_scope: Option<String>,
    evidence: Vec<String>,
}

#[derive(Serialize, Default)]
pub struct CanvasReturnTask {
    return_to_stage: Option<String>,
    scope: Option<String>,
    affected_shots: Vec<String>,
    dimensions: Vec<String>,
}

#[derive(Serialize, Default)]
pub struct CanvasQualitySummary {
    source: Option<String>,
    score: Option<f64>,
    verdict: Option<String>,
    status: Option<String>,
    blocks: i64,
    warnings: i64,
    infos: i64,
    dimensions: Vec<CanvasScoreDimension>,
    tasks: Vec<CanvasReturnTask>,
    metrics: Vec<CanvasMetric>,
}

#[derive(Serialize, Default)]
pub struct QualityInsightMetric {
    label: String,
    value: String,
    tone: Option<String>,
}

#[derive(Serialize, Default)]
pub struct QualityInsightDimension {
    key: Option<String>,
    label: String,
    score: Option<f64>,
    value: Option<String>,
    max: Option<f64>,
    status: Option<String>,
    blocks: i64,
    warnings: i64,
    infos: i64,
    detail: Option<String>,
    evidence: Vec<String>,
}

#[derive(Serialize, Default)]
pub struct QualityInsightIssue {
    severity: String,
    dimension: Option<String>,
    title: String,
    message: Option<String>,
    stage: Option<String>,
    path: Option<String>,
    source: Option<String>,
}

#[derive(Serialize, Default)]
pub struct QualityInsightTask {
    priority: Option<String>,
    title: String,
    skill: Option<String>,
    stage: Option<String>,
    detail: Option<String>,
}

#[derive(Serialize, Default)]
pub struct QualityInsightArtifact {
    label: String,
    path: String,
    exists: bool,
    kind: Option<String>,
}

#[derive(Serialize, Default)]
pub struct QualityInsights {
    line: String,
    episode: Option<String>,
    status: Option<String>,
    score: Option<f64>,
    verdict: Option<String>,
    blocks: i64,
    warnings: i64,
    infos: i64,
    metrics: Vec<QualityInsightMetric>,
    dimensions: Vec<QualityInsightDimension>,
    issues: Vec<QualityInsightIssue>,
    tasks: Vec<QualityInsightTask>,
    artifacts: Vec<QualityInsightArtifact>,
    source_files: Vec<String>,
}

#[derive(Serialize, Default)]
pub struct CanvasData {
    source: String, // review_ui | storyboard | none
    episode: String,
    title: Option<String>,
    total_duration: Option<f64>,
    episodes: Vec<String>,
    shared_assets: Vec<CanvasFrame>,
    clips: Vec<CanvasClip>,
    seams: Vec<CanvasSeam>,
    quality: Option<CanvasQualitySummary>,
}

#[derive(Serialize, Deserialize, Clone, Default)]
pub struct CanvasNodePosition {
    id: String,
    x: f64,
    y: f64,
}

#[derive(Serialize, Deserialize, Default)]
pub struct CanvasLayout {
    version: u32,
    episode: String,
    updated_at_epoch_ms: u128,
    nodes: Vec<CanvasNodePosition>,
}

#[derive(Serialize, Default)]
pub struct ClipEditData {
    source_rel: String,
    id: String,
    number: Option<i64>,
    label: String,
    duration: Option<f64>,
    scene: String,
    rhythm: String,
    template: String,
    prompt: String,
    image_prompt: String,
    video_prompt: String,
    positive_prompt: String,
    negative_prompt: String,
}

#[derive(Deserialize, Default)]
pub struct ClipEditPatch {
    label: String,
    duration: Option<f64>,
    scene: String,
    rhythm: String,
    template: String,
    prompt: String,
    image_prompt: String,
    video_prompt: String,
    positive_prompt: String,
    negative_prompt: String,
}

fn ep_num(name: &str) -> i64 {
    // "第12集" / "第7a集" -> 12 / 7 ; fallback large.
    let digits: String = name.chars().filter(|c| c.is_ascii_digit()).collect();
    digits.parse().unwrap_or(1_000_000)
}

fn number_from_id(id: &str) -> Option<i64> {
    let digits: String = id.chars().filter(|c| c.is_ascii_digit()).collect();
    digits.parse().ok()
}

fn list_episodes(root: &Path) -> Vec<String> {
    let mut eps = Vec::new();
    if let Ok(entries) = fs::read_dir(root.join("脚本")) {
        for e in entries.flatten() {
            if e.path().is_dir() {
                let n = e.file_name().to_string_lossy().to_string();
                if n.starts_with('第') {
                    eps.push(n);
                }
            }
        }
    }
    eps.sort_by_key(|n| (ep_num(n), n.clone()));
    eps
}

fn production_dir_for_write(root: &str) -> Result<PathBuf, String> {
    let base = fs::canonicalize(root).map_err(|e| e.to_string())?;
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    let dir = base.join("生产数据");
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

fn validate_episode_name(ep: &str) -> Result<(), String> {
    if ep.trim().is_empty() || ep.contains('/') || ep.contains('\\') || ep.contains('\0') {
        return Err("非法集名".into());
    }
    Ok(())
}

fn canvas_layout_read_path(root: &str, ep: &str) -> Result<PathBuf, String> {
    validate_episode_name(ep)?;
    let base = fs::canonicalize(root).map_err(|e| e.to_string())?;
    if !base.is_dir() {
        return Err("作品目录不存在".into());
    }
    Ok(base
        .join("生产数据")
        .join(format!("canvas_layout_{ep}.json")))
}

fn canvas_layout_path(root: &str, ep: &str) -> Result<PathBuf, String> {
    validate_episode_name(ep)?;
    Ok(production_dir_for_write(root)?.join(format!("canvas_layout_{ep}.json")))
}

fn now_epoch_ms() -> u128 {
    UNIX_EPOCH
        .elapsed()
        .map(|d| d.as_millis())
        .unwrap_or_default()
}

fn storyboard_path(root: &str, ep: &str) -> Result<PathBuf, String> {
    let rel = format!("脚本/{ep}/storyboard.json");
    existing_work_path(root, &rel, false)
}

fn panel_script_path(root: &str, ep: &str) -> Result<PathBuf, String> {
    let rel = format!("脚本/{ep}/panel_script.json");
    existing_work_path(root, &rel, false)
}

fn find_clip_index(clips: &[Value], clip_id: &str, number: Option<i64>) -> Option<usize> {
    let id_keys = ["id", "panel_id"];
    for key in id_keys {
        if let Some(idx) = clips
            .iter()
            .position(|c| c.get(key).and_then(|v| v.as_str()) == Some(clip_id))
        {
            return Some(idx);
        }
    }
    if let Some(n) = number {
        if let Some(idx) = clips
            .iter()
            .position(|c| c.get("number").and_then(|v| v.as_i64()) == Some(n))
        {
            return Some(idx);
        }
        let needle = format!("{n:02}");
        return clips.iter().position(|c| {
            c.get("id")
                .and_then(|v| v.as_str())
                .map(|id| id.ends_with(&needle) || id.contains(&format!("CLIP{needle}")))
                .unwrap_or(false)
                || c.get("panel_id")
                    .and_then(|v| v.as_str())
                    .map(|id| {
                        id.ends_with(&needle)
                            || id == format!("P{n:03}")
                            || id == format!("P{n:02}")
                    })
                    .unwrap_or(false)
        });
    }
    None
}

fn value_string(v: &Value, key: &str) -> String {
    v.get(key)
        .and_then(|x| x.as_str())
        .unwrap_or("")
        .to_string()
}

fn nonempty_value_string(v: &Value, key: &str) -> Option<String> {
    let value = value_string(v, key);
    if value.trim().is_empty() {
        None
    } else {
        Some(value)
    }
}

fn value_string_or(v: &Value, key: &str, fallback: Option<String>) -> String {
    nonempty_value_string(v, key)
        .or(fallback)
        .unwrap_or_default()
}

fn storyboard_shot_text(clip: &Value) -> Option<String> {
    let mut parts: Vec<String> = Vec::new();
    if let Some(shots) = clip.get("shots").and_then(|x| x.as_array()) {
        for (idx, shot) in shots.iter().enumerate() {
            let mut bits = Vec::new();
            if let Some(t) = s(shot, "t") {
                bits.push(t);
            }
            if let Some(lens) = s(shot, "lens") {
                bits.push(lens);
            }
            if let Some(desc) = s(shot, "desc") {
                bits.push(desc);
            }
            if !bits.is_empty() {
                parts.push(format!("shot {}: {}", idx + 1, bits.join(" · ")));
            }
        }
    }
    if parts.is_empty() {
        None
    } else {
        Some(parts.join("\n"))
    }
}

fn storyboard_shot_video_prompt(clip: &Value) -> Option<String> {
    let mut parts: Vec<String> = Vec::new();
    if let Some(shots) = clip.get("shots").and_then(|x| x.as_array()) {
        for (idx, shot) in shots.iter().enumerate() {
            if let Some(prompt) = s(shot, "video_prompt") {
                let prompt = prompt.trim();
                if prompt.is_empty() {
                    continue;
                }
                let mut label = format!("shot {}", idx + 1);
                if let Some(t) = s(shot, "t") {
                    label.push_str(&format!(" · {t}"));
                }
                if let Some(lens) = s(shot, "lens") {
                    label.push_str(&format!(" · {lens}"));
                }
                parts.push(format!("{label}: {prompt}"));
            }
        }
    }
    if parts.is_empty() {
        None
    } else {
        Some(parts.join("\n"))
    }
}

fn set_string_field(
    obj: &mut serde_json::Map<String, Value>,
    key: &str,
    value: &str,
    remove_empty: bool,
) {
    if remove_empty && value.trim().is_empty() {
        obj.remove(key);
    } else {
        obj.insert(key.to_string(), Value::String(value.to_string()));
    }
}

fn split_list_text(input: &str) -> Vec<String> {
    input
        .split(|c| matches!(c, '\n' | ',' | '，' | '、' | ';' | '；'))
        .map(|part| part.trim())
        .filter(|part| !part.is_empty())
        .map(|part| part.to_string())
        .collect()
}

fn set_string_array_field(obj: &mut serde_json::Map<String, Value>, key: &str, input: &str) {
    let values = split_list_text(input);
    if values.is_empty() {
        obj.remove(key);
    } else {
        obj.insert(
            key.to_string(),
            Value::Array(values.into_iter().map(Value::String).collect()),
        );
    }
}

fn s(v: &Value, k: &str) -> Option<String> {
    v.get(k).and_then(|x| x.as_str()).map(|x| x.to_string())
}

fn heading_matches_clip(line: &str, clip_id: &str, number: Option<i64>) -> bool {
    if !clip_id.trim().is_empty() && line.contains(clip_id) {
        return true;
    }
    if let Some(n) = number {
        let n2 = format!("{n:02}");
        let n3 = format!("{n:03}");
        let candidates = [
            format!("镜头 {n}"),
            format!("镜头{n}"),
            format!("Clip {n}"),
            format!("Clip {n2}"),
            format!("Clip{n2}"),
            format!("Clip_{n2}"),
            format!("CLIP{n2}"),
            format!("P{n2}"),
            format!("P{n3}"),
        ];
        return candidates.iter().any(|candidate| line.contains(candidate));
    }
    false
}

fn markdown_clip_section<'a>(text: &'a str, clip_id: &str, number: Option<i64>) -> Option<&'a str> {
    let mut headings: Vec<(usize, &str)> = Vec::new();
    let mut pos = 0usize;
    for line in text.split_inclusive('\n') {
        if line.starts_with("## ") && !line.starts_with("### ") {
            headings.push((pos, line.trim_end()));
        }
        pos += line.len();
    }
    for (idx, (start, heading)) in headings.iter().enumerate() {
        if heading_matches_clip(heading, clip_id, number) {
            let end = headings
                .get(idx + 1)
                .map(|(next_start, _)| *next_start)
                .unwrap_or(text.len());
            return text.get(*start..end);
        }
    }
    None
}

fn fenced_or_plain_after_heading(section: &str, prefixes: &[&str]) -> Option<String> {
    let lines: Vec<&str> = section.lines().collect();
    for idx in 0..lines.len() {
        let heading = lines[idx].trim();
        if !heading.starts_with("### ") || !prefixes.iter().any(|prefix| heading.contains(prefix)) {
            continue;
        }

        let mut plain = Vec::new();
        let mut fenced = Vec::new();
        let mut in_fence = false;
        let mut saw_fence = false;
        for line in lines.iter().skip(idx + 1) {
            let trimmed = line.trim();
            if trimmed.starts_with("```") {
                if in_fence {
                    let value = fenced.join("\n").trim().to_string();
                    if !value.is_empty() {
                        return Some(value);
                    }
                    break;
                }
                in_fence = true;
                saw_fence = true;
                continue;
            }
            if in_fence {
                fenced.push((*line).to_string());
                continue;
            }
            if trimmed.starts_with("### ") || trimmed.starts_with("## ") {
                break;
            }
            if !saw_fence {
                plain.push((*line).to_string());
            }
        }
        let value = plain.join("\n").trim().to_string();
        if !value.is_empty() {
            return Some(value);
        }
    }
    None
}

fn read_clip_prompt_pack(
    root: &Path,
    rel: &[&str],
    clip_id: &str,
    number: Option<i64>,
    subheading_prefixes: &[&str],
) -> Option<String> {
    let mut path = root.to_path_buf();
    for part in rel {
        path.push(part);
    }
    let text = fs::read_to_string(path).ok()?;
    let section = markdown_clip_section(&text, clip_id, number)?;
    fenced_or_plain_after_heading(section, subheading_prefixes)
}

fn n_f64(v: &Value, k: &str) -> Option<f64> {
    v.get(k).and_then(|x| x.as_f64())
}

fn n_i64(v: &Value, k: &str) -> i64 {
    v.get(k).and_then(|x| x.as_i64()).unwrap_or(0)
}

fn read_json(path: &Path) -> Option<Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|txt| serde_json::from_str::<Value>(&txt).ok())
}

fn short_text(value: &str, limit: usize) -> String {
    if value.chars().count() <= limit {
        value.to_string()
    } else {
        format!("{}…", value.chars().take(limit).collect::<String>())
    }
}

fn value_label(value: &Value) -> Option<String> {
    if let Some(s) = value.as_str() {
        let s = s.trim();
        if !s.is_empty() {
            return Some(s.to_string());
        }
    }
    if let Some(n) = value.as_f64() {
        return Some(if (n.fract()).abs() < f64::EPSILON {
            format!("{}", n as i64)
        } else {
            format!("{n:.2}")
        });
    }
    if let Some(b) = value.as_bool() {
        return Some(if b { "是" } else { "否" }.to_string());
    }
    None
}

fn string_array(v: &Value, k: &str, limit: usize) -> Vec<String> {
    v.get(k)
        .and_then(|x| x.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|x| x.as_str())
                .take(limit)
                .map(|x| short_text(x, 180))
                .collect()
        })
        .unwrap_or_default()
}

fn rel_abs(root: &Path, rel: Option<String>) -> (Option<String>, bool) {
    match rel {
        Some(r) if !r.trim().is_empty() => {
            let pb = PathBuf::from(&r);
            let abs = if pb.is_absolute() { pb } else { root.join(&r) };
            let exists = abs.exists();
            (Some(abs.to_string_lossy().to_string()), exists)
        }
        _ => (None, false),
    }
}

fn clip_prompt(c: &Value) -> Option<String> {
    let mut parts: Vec<String> = Vec::new();
    for key in [
        "video_prompt",
        "image_prompt",
        "prompt",
        "positive_prompt",
        "negative_prompt",
    ] {
        if let Some(v) = s(c, key) {
            let v = v.trim();
            if !v.is_empty() {
                parts.push(format!("{key}: {v}"));
            }
        }
    }
    if let Some(shots) = c.get("shots").and_then(|x| x.as_array()) {
        for (idx, shot) in shots.iter().enumerate() {
            let mut bits = Vec::new();
            if let Some(t) = s(shot, "t") {
                bits.push(t);
            }
            if let Some(lens) = s(shot, "lens") {
                bits.push(lens);
            }
            if let Some(desc) = s(shot, "desc") {
                bits.push(desc);
            }
            if let Some(prompt) = s(shot, "video_prompt") {
                bits.push(format!("video_prompt: {prompt}"));
            }
            if !bits.is_empty() {
                parts.push(format!("shot {}: {}", idx + 1, bits.join(" · ")));
            }
        }
    }
    if parts.is_empty() {
        None
    } else {
        let joined = parts.join("\n");
        if joined.chars().count() > CANVAS_PROMPT_PREVIEW_LIMIT {
            let clipped: String = joined.chars().take(CANVAS_PROMPT_PREVIEW_LIMIT).collect();
            Some(format!("{clipped}\n…"))
        } else {
            Some(joined)
        }
    }
}

fn score_dimension(raw: &Value) -> CanvasScoreDimension {
    let evidence = raw
        .get("evidence")
        .and_then(|x| x.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|x| x.as_str())
                .take(4)
                .map(|x| short_text(x, 180))
                .collect()
        })
        .unwrap_or_default();
    CanvasScoreDimension {
        key: s(raw, "key").or_else(|| s(raw, "dim_key")),
        label: s(raw, "label")
            .or_else(|| s(raw, "dim"))
            .unwrap_or_else(|| "未命名维度".into()),
        status: s(raw, "status"),
        score: n_f64(raw, "score"),
        blocks: n_i64(raw, "blocks").max(n_i64(raw, "block")),
        warnings: n_i64(raw, "warnings").max(n_i64(raw, "warn")),
        infos: n_i64(raw, "infos").max(n_i64(raw, "info")),
        return_to_stage: s(raw, "return_to_stage"),
        rerun_scope: s(raw, "rerun_scope").map(|x| short_text(&x, 260)),
        evidence,
    }
}

fn score_dimensions(score_data: Option<&Value>) -> Vec<CanvasScoreDimension> {
    score_data
        .and_then(|v| v.get("dimensions"))
        .and_then(|x| x.as_array())
        .map(|arr| {
            let mut dims: Vec<CanvasScoreDimension> = arr.iter().map(score_dimension).collect();
            dims.sort_by(|a, b| {
                b.blocks
                    .cmp(&a.blocks)
                    .then(b.warnings.cmp(&a.warnings))
                    .then_with(|| {
                        a.score
                            .unwrap_or(999.0)
                            .partial_cmp(&b.score.unwrap_or(999.0))
                            .unwrap_or(std::cmp::Ordering::Equal)
                    })
            });
            dims
        })
        .unwrap_or_default()
}

fn return_tasks(score_data: Option<&Value>) -> Vec<CanvasReturnTask> {
    score_data
        .and_then(|v| v.get("auto_return_tasks"))
        .and_then(|x| x.as_array())
        .map(|arr| {
            arr.iter()
                .take(8)
                .map(|raw| CanvasReturnTask {
                    return_to_stage: s(raw, "return_to_stage"),
                    scope: s(raw, "scope").map(|x| short_text(&x, 360)),
                    affected_shots: string_array(raw, "affected_shots", 12),
                    dimensions: string_array(raw, "dimensions", 8),
                })
                .collect()
        })
        .unwrap_or_default()
}

fn push_metric(
    metrics: &mut Vec<CanvasMetric>,
    alerts: &Value,
    label: &str,
    key: &str,
    suffix: &str,
) {
    if let Some(value) = alerts.get(key).and_then(value_label) {
        metrics.push(CanvasMetric {
            label: label.into(),
            value: format!("{value}{suffix}"),
        });
    }
}

fn push_rate_metric(metrics: &mut Vec<CanvasMetric>, alerts: &Value, label: &str, key: &str) {
    if let Some(value) = alerts.get(key).and_then(|v| v.as_f64()) {
        metrics.push(CanvasMetric {
            label: label.into(),
            value: format!("{:.1}%", value * 100.0),
        });
    }
}

fn dashboard_metrics(root: &Path, ep: &str) -> Vec<CanvasMetric> {
    let dash = read_json(&root.join("生产数据").join("dashboard.json"));
    let Some(alerts) = dash
        .as_ref()
        .and_then(|v| v.get("alert_counts"))
        .filter(|v| s(v, "episode").as_deref() == Some(ep) || s(v, "episode").is_none())
    else {
        return vec![];
    };
    let mut metrics = Vec::new();
    push_rate_metric(&mut metrics, alerts, "成品通过率", "final_pass_rate");
    push_rate_metric(&mut metrics, alerts, "生成通过率", "generation_pass_rate");
    push_metric(&mut metrics, alerts, "QA阻断", "qa_blockers", "");
    push_metric(&mut metrics, alerts, "QA警告", "qa_warnings", "");
    push_metric(
        &mut metrics,
        alerts,
        "一致性阻断",
        "consistency_blockers",
        "",
    );
    push_metric(
        &mut metrics,
        alerts,
        "一致性警告",
        "consistency_warnings",
        "",
    );
    push_metric(&mut metrics, alerts, "重抽次数", "redraw_count", "");
    if let Some(costs) = alerts.get("cost_totals").and_then(|v| v.as_object()) {
        for (unit, value) in costs.iter().take(2) {
            if let Some(v) = value_label(value) {
                metrics.push(CanvasMetric {
                    label: format!("成本 {unit}"),
                    value: v,
                });
            }
        }
    }
    if let Some(stage) = s(alerts, "progress_next_stage") {
        metrics.push(CanvasMetric {
            label: "下一阶段".into(),
            value: stage,
        });
    }
    metrics
}

fn quality_summary(
    root: &Path,
    ep: &str,
    review_data: Option<&Value>,
) -> Option<CanvasQualitySummary> {
    let score_from_review = review_data
        .and_then(|v| v.get("score"))
        .filter(|v| v.is_object())
        .cloned();
    let score_file = root.join("生产数据").join(format!("score_{ep}.json"));
    let score_from_file = read_json(&score_file);
    let score_data = score_from_review.as_ref().or(score_from_file.as_ref());
    let findings = read_json(
        &root
            .join("生产数据")
            .join(format!("review_ui_findings_{ep}.json")),
    );
    let dimensions = score_dimensions(score_data);
    let findings_sev = findings
        .as_ref()
        .and_then(|v| v.get("summary"))
        .and_then(|v| v.get("severity"));
    let blocks = findings_sev
        .map(|v| n_i64(v, "block"))
        .unwrap_or_else(|| dimensions.iter().map(|d| d.blocks).sum());
    let warnings = findings_sev
        .map(|v| n_i64(v, "warn"))
        .unwrap_or_else(|| dimensions.iter().map(|d| d.warnings).sum());
    let infos = findings_sev
        .map(|v| n_i64(v, "info"))
        .unwrap_or_else(|| dimensions.iter().map(|d| d.infos).sum());
    let score = score_data.and_then(|v| {
        n_f64(v, "total_score")
            .or_else(|| n_f64(v, "overall_score"))
            .or_else(|| n_f64(v, "score"))
    });
    let mut metrics = dashboard_metrics(root, ep);
    if let Some(source) = score_data.and_then(|v| s(v, "source")) {
        metrics.push(CanvasMetric {
            label: "评分来源".into(),
            value: source,
        });
    }
    let status = score_data.and_then(|v| s(v, "status")).or_else(|| {
        if blocks > 0 {
            Some("block".into())
        } else if warnings > 0 {
            Some("warn".into())
        } else if score_data.is_some() || findings.is_some() {
            Some("pass".into())
        } else {
            None
        }
    });
    if score_data.is_none() && findings.is_none() && metrics.is_empty() {
        return None;
    }
    Some(CanvasQualitySummary {
        source: if score_from_review.is_some() {
            Some("review_ui.score".into())
        } else if score_from_file.is_some() {
            Some(format!("生产数据/score_{ep}.json"))
        } else {
            findings
                .as_ref()
                .map(|_| format!("生产数据/review_ui_findings_{ep}.json"))
        },
        score,
        verdict: score_data.and_then(|v| s(v, "verdict")),
        status,
        blocks,
        warnings,
        infos,
        dimensions,
        tasks: return_tasks(score_data),
        metrics,
    })
}

fn summary_count(data: Option<&Value>, key: &str) -> i64 {
    data.and_then(|v| v.get("summary"))
        .map(|summary| {
            n_i64(summary, key)
                .max(n_i64(summary, &key.replace("_count", "")))
                .max(n_i64(summary, &key.replace("block_count", "block")))
                .max(n_i64(summary, &key.replace("warn_count", "warn")))
                .max(n_i64(summary, &key.replace("info_count", "info")))
        })
        .unwrap_or(0)
}

fn score_from_status(blocks: i64, warnings: i64, complete: bool) -> Option<f64> {
    if blocks > 0 {
        Some(50.0)
    } else if warnings > 0 {
        Some(75.0)
    } else if complete {
        Some(100.0)
    } else {
        None
    }
}

fn comic_return_tasks_from_findings(findings: Option<&Value>) -> Vec<CanvasReturnTask> {
    findings
        .and_then(|v| v.get("findings"))
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .take(12)
                .map(|item| CanvasReturnTask {
                    return_to_stage: s(item, "return_to_stage").or_else(|| Some("image".into())),
                    scope: s(item, "suggested_fix")
                        .or_else(|| s(item, "reason"))
                        .map(|value| short_text(&value, 360)),
                    affected_shots: s(item, "panel_id").map(|id| vec![id]).unwrap_or_default(),
                    dimensions: s(item, "dimension")
                        .or_else(|| s(item, "code"))
                        .map(|value| vec![value])
                        .unwrap_or_default(),
                })
                .collect()
        })
        .unwrap_or_default()
}

fn comic_quality_summary(
    root: &Path,
    ep: &str,
    clips: &[CanvasClip],
) -> Option<CanvasQualitySummary> {
    if clips.is_empty() {
        return None;
    }
    let style = read_json(
        &root
            .join("生产数据")
            .join(format!("comic_style_consistency_{ep}.json")),
    );
    let findings = read_json(
        &root
            .join("生产数据")
            .join(format!("consistency_findings_style_{ep}.json")),
    );
    let identity = read_json(
        &root
            .join("生产数据")
            .join(format!("comic_identity_report_{ep}.json")),
    );
    let jobs = read_json(
        &root
            .join("出图")
            .join(ep)
            .join("prompt")
            .join("panel_jobs.json"),
    );

    let panel_count = clips.len() as i64;
    let image_count = clips.iter().filter(|clip| clip.first_frame_exists).count() as i64;
    let clip_blocks: i64 = clips.iter().map(|clip| clip.qa_blocks).sum();
    let clip_warnings: i64 = clips.iter().map(|clip| clip.qa_warnings).sum();
    let clip_infos: i64 = clips.iter().map(|clip| clip.qa_infos).sum();
    let style_blocks = summary_count(style.as_ref(), "block_count")
        .max(summary_count(findings.as_ref(), "block_count"));
    let style_warnings = summary_count(style.as_ref(), "warn_count")
        .max(summary_count(findings.as_ref(), "warn_count"));
    let style_infos = summary_count(style.as_ref(), "info_count")
        .max(summary_count(findings.as_ref(), "info_count"));
    let missing_refs = identity
        .as_ref()
        .and_then(|v| v.get("summary"))
        .map(|summary| n_i64(summary, "missing_ref_count"))
        .unwrap_or(0);
    let rerun_targets = identity
        .as_ref()
        .and_then(|v| v.get("summary"))
        .map(|summary| n_i64(summary, "rerun_target_count"))
        .unwrap_or(0);

    let blocks = clip_blocks.max(style_blocks).max(missing_refs);
    let warnings = clip_warnings.max(style_warnings).max(rerun_targets);
    let infos = clip_infos.max(style_infos);
    let complete = image_count == panel_count && panel_count > 0 && blocks == 0 && warnings == 0;
    let status = if blocks > 0 {
        "block"
    } else if warnings > 0 {
        "warn"
    } else if complete {
        "pass"
    } else {
        "draft"
    };

    let mut dimensions = Vec::new();
    dimensions.push(CanvasScoreDimension {
        key: Some("panel_qc".into()),
        label: "单格后检".into(),
        status: Some(status.into()),
        score: score_from_status(clip_blocks, clip_warnings, image_count > 0),
        blocks: clip_blocks,
        warnings: clip_warnings,
        infos: clip_infos,
        return_to_stage: if clip_blocks > 0 || clip_warnings > 0 {
            Some("image".into())
        } else {
            None
        },
        rerun_scope: None,
        evidence: vec![
            format!("生产数据/panel_qc/{ep}/"),
            format!("出图/{ep}/prompt/panel_jobs.json"),
        ],
    });
    if style.is_some() || findings.is_some() {
        dimensions.push(CanvasScoreDimension {
            key: Some("style_consistency".into()),
            label: "风格一致性".into(),
            status: style
                .as_ref()
                .and_then(|v| s(v, "verdict"))
                .or_else(|| findings.as_ref().and_then(|v| s(v, "verdict"))),
            score: score_from_status(style_blocks, style_warnings, true),
            blocks: style_blocks,
            warnings: style_warnings,
            infos: style_infos,
            return_to_stage: if style_blocks > 0 || style_warnings > 0 {
                Some("image".into())
            } else {
                None
            },
            rerun_scope: findings
                .as_ref()
                .and_then(|v| v.get("findings"))
                .and_then(|v| v.as_array())
                .and_then(|items| items.first())
                .and_then(|item| s(item, "suggested_fix").or_else(|| s(item, "reason")))
                .map(|value| short_text(&value, 260)),
            evidence: vec![
                format!("生产数据/comic_style_consistency_{ep}.json"),
                format!("生产数据/consistency_findings_style_{ep}.json"),
            ],
        });
    }
    if identity.is_some() {
        dimensions.push(CanvasScoreDimension {
            key: Some("identity_references".into()),
            label: "角色参考完整性".into(),
            status: if missing_refs > 0 {
                Some("block".into())
            } else if rerun_targets > 0 {
                Some("warn".into())
            } else {
                Some("pass".into())
            },
            score: score_from_status(missing_refs, rerun_targets, true),
            blocks: missing_refs,
            warnings: rerun_targets,
            infos: 0,
            return_to_stage: if missing_refs > 0 || rerun_targets > 0 {
                Some("image".into())
            } else {
                None
            },
            rerun_scope: None,
            evidence: vec![format!("生产数据/comic_identity_report_{ep}.json")],
        });
    }

    let mut metrics = vec![
        CanvasMetric {
            label: "分格".into(),
            value: panel_count.to_string(),
        },
        CanvasMetric {
            label: "已出图".into(),
            value: image_count.to_string(),
        },
        CanvasMetric {
            label: "待出图".into(),
            value: (panel_count - image_count).max(0).to_string(),
        },
    ];
    if let Some(model) = jobs.as_ref().and_then(|v| s(v, "model")) {
        metrics.push(CanvasMetric {
            label: "出图模型".into(),
            value: model,
        });
    }
    if root
        .join("生产数据")
        .join(format!("panel_contact_sheet_{ep}.jpg"))
        .exists()
    {
        metrics.push(CanvasMetric {
            label: "联络图".into(),
            value: "已生成".into(),
        });
    }

    Some(CanvasQualitySummary {
        source: Some(format!("脚本/{ep}/panel_script.json")),
        score: score_from_status(blocks, warnings, complete),
        verdict: Some(status.into()),
        status: Some(status.into()),
        blocks,
        warnings,
        infos,
        dimensions,
        tasks: comic_return_tasks_from_findings(findings.as_ref()),
        metrics,
    })
}

fn severity_tone(raw: Option<String>) -> String {
    let value = raw.unwrap_or_else(|| "info".into()).to_ascii_lowercase();
    if value.contains("block")
        || value.contains("blocking")
        || value == "critical"
        || value == "error"
        || value == "fail"
        || value == "failed"
    {
        "block".into()
    } else if value.contains("warn")
        || value == "action_required"
        || value == "needs_revision"
        || value == "suggestion"
        || value == "should"
    {
        "warn".into()
    } else if value == "pass" || value == "ok" || value == "done" || value == "accepted" {
        "pass".into()
    } else {
        "info".into()
    }
}

fn status_from_counts(blocks: i64, warnings: i64, score: Option<f64>) -> Option<String> {
    if blocks > 0 {
        Some("block".into())
    } else if warnings > 0 {
        Some("warn".into())
    } else if score.is_some() {
        Some("pass".into())
    } else {
        None
    }
}

fn push_insight_metric(
    out: &mut QualityInsights,
    label: &str,
    value: Option<String>,
    tone: Option<&str>,
) {
    let Some(value) = value else {
        return;
    };
    if value.trim().is_empty() {
        return;
    }
    out.metrics.push(QualityInsightMetric {
        label: label.into(),
        value,
        tone: tone.map(|v| v.to_string()),
    });
}

fn push_insight_artifact(
    out: &mut QualityInsights,
    root: &Path,
    label: &str,
    rel: &str,
    kind: &str,
) {
    if rel.trim().is_empty() {
        return;
    }
    let exists = root.join(rel).exists();
    out.artifacts.push(QualityInsightArtifact {
        label: label.into(),
        path: rel.into(),
        exists,
        kind: Some(kind.into()),
    });
}

fn push_source_file(out: &mut QualityInsights, root: &Path, rel: &str, label: &str) -> bool {
    if root.join(rel).is_file() {
        if !out.source_files.iter().any(|item| item == rel) {
            out.source_files.push(rel.into());
        }
        push_insight_artifact(out, root, label, rel, "evidence");
        true
    } else {
        false
    }
}

fn ratio_metric(value: Option<f64>) -> Option<String> {
    value.map(|v| format!("{:.1}%", v * 100.0))
}

fn score_label(value: Option<f64>) -> Option<String> {
    value.map(|v| {
        if (v.fract()).abs() < f64::EPSILON {
            format!("{}", v as i64)
        } else {
            format!("{v:.1}")
        }
    })
}

fn insight_counts_from_summary(summary: Option<&Value>) -> (i64, i64, i64) {
    let Some(summary) = summary else {
        return (0, 0, 0);
    };
    let sev = summary.get("severity");
    let blocks = sev
        .map(|v| n_i64(v, "block"))
        .unwrap_or(0)
        .max(n_i64(summary, "block"))
        .max(n_i64(summary, "blocks"))
        .max(n_i64(summary, "block_count"))
        .max(n_i64(summary, "blocking_count"))
        .max(n_i64(summary, "qa_blockers"))
        .max(n_i64(summary, "consistency_blockers"));
    let warnings = sev
        .map(|v| n_i64(v, "warn"))
        .unwrap_or(0)
        .max(n_i64(summary, "warn"))
        .max(n_i64(summary, "warnings"))
        .max(n_i64(summary, "warn_count"))
        .max(n_i64(summary, "warning_count"))
        .max(n_i64(summary, "suggestion_count"))
        .max(n_i64(summary, "qa_warnings"))
        .max(n_i64(summary, "consistency_warnings"));
    let infos = sev
        .map(|v| n_i64(v, "info"))
        .unwrap_or(0)
        .max(n_i64(summary, "infos"))
        .max(n_i64(summary, "info_count"))
        .max(n_i64(summary, "polish_count"));
    (blocks, warnings, infos)
}

fn push_task_from_value(out: &mut QualityInsights, raw: &Value) {
    let title = s(raw, "action")
        .or_else(|| s(raw, "title"))
        .or_else(|| s(raw, "scope"))
        .or_else(|| s(raw, "fix_hint"))
        .or_else(|| s(raw, "suggested_fix"))
        .unwrap_or_else(|| "未命名返工任务".into());
    out.tasks.push(QualityInsightTask {
        priority: s(raw, "priority"),
        title: short_text(&title, 180),
        skill: s(raw, "recommended_skill").or_else(|| s(raw, "skill")),
        stage: s(raw, "return_to_stage").or_else(|| s(raw, "stage")),
        detail: s(raw, "dimension")
            .or_else(|| s(raw, "reason"))
            .or_else(|| s(raw, "message"))
            .map(|v| short_text(&v, 260)),
    });
}

fn push_issue_from_value(out: &mut QualityInsights, raw: &Value) {
    let severity = if raw
        .get("blocking")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
    {
        "block".into()
    } else {
        severity_tone(
            s(raw, "severity")
                .or_else(|| s(raw, "sev"))
                .or_else(|| s(raw, "status")),
        )
    };
    let title = s(raw, "problem")
        .or_else(|| s(raw, "reason"))
        .or_else(|| s(raw, "message"))
        .or_else(|| s(raw, "msg"))
        .or_else(|| s(raw, "code"))
        .or_else(|| s(raw, "id"))
        .unwrap_or_else(|| "未命名问题".into());
    let path = s(raw, "loc")
        .or_else(|| s(raw, "path"))
        .or_else(|| s(raw, "artifact"))
        .or_else(|| {
            raw.get("affected_files")
                .and_then(|v| v.as_array())
                .and_then(|items| items.first())
                .and_then(|v| v.as_str())
                .map(|v| v.to_string())
        });
    out.issues.push(QualityInsightIssue {
        severity,
        dimension: s(raw, "dimension")
            .or_else(|| s(raw, "dim"))
            .or_else(|| s(raw, "category")),
        title: short_text(&title, 160),
        message: s(raw, "fix_hint")
            .or_else(|| s(raw, "suggested_fix"))
            .or_else(|| s(raw, "evidence"))
            .or_else(|| s(raw, "rerun_scope"))
            .map(|v| short_text(&v, 280)),
        stage: s(raw, "return_to_stage").or_else(|| s(raw, "gate_stage")),
        path,
        source: s(raw, "source"),
    });
}

fn push_dimensions_from_by_dim(
    out: &mut QualityInsights,
    source_label: &str,
    by_dim: Option<&Value>,
) {
    let Some(obj) = by_dim.and_then(|v| v.as_object()) else {
        return;
    };
    let mut dims: Vec<QualityInsightDimension> = obj
        .iter()
        .map(|(key, raw)| {
            let blocks = n_i64(raw, "block").max(n_i64(raw, "blocks"));
            let warnings = n_i64(raw, "warn")
                .max(n_i64(raw, "warning"))
                .max(n_i64(raw, "warnings"));
            let infos = n_i64(raw, "info").max(n_i64(raw, "infos"));
            QualityInsightDimension {
                key: Some(key.clone()),
                label: key.clone(),
                score: score_from_status(blocks, warnings, true),
                value: Some(format!("{blocks}/{warnings}/{infos}")),
                max: Some(100.0),
                status: status_from_counts(blocks, warnings, Some(100.0)),
                blocks,
                warnings,
                infos,
                detail: Some("block / warn / info".into()),
                evidence: vec![source_label.into()],
            }
        })
        .collect();
    dims.sort_by(|a, b| {
        b.blocks
            .cmp(&a.blocks)
            .then(b.warnings.cmp(&a.warnings))
            .then(b.infos.cmp(&a.infos))
    });
    out.dimensions.extend(dims.into_iter().take(14));
}

fn collect_tasks_from_array(out: &mut QualityInsights, data: &Value, key: &str, limit: usize) {
    if let Some(items) = data.get(key).and_then(|v| v.as_array()) {
        for item in items.iter().take(limit) {
            push_task_from_value(out, item);
        }
    }
}

fn collect_issues_from_array(out: &mut QualityInsights, data: &Value, key: &str, limit: usize) {
    if let Some(items) = data.get(key).and_then(|v| v.as_array()) {
        for item in items.iter().take(limit) {
            push_issue_from_value(out, item);
        }
    }
}

fn collect_novel_score(root: &Path, out: &mut QualityInsights) {
    let rel = "评分/score_report.json";
    let Some(score_data) = read_json(&root.join(rel)) else {
        return;
    };
    push_source_file(out, root, rel, "小说评分");
    out.score = n_f64(&score_data, "total_score")
        .or_else(|| n_f64(&score_data, "overall_score"))
        .or(out.score);
    out.verdict = s(&score_data, "verdict").or(out.verdict.take());
    out.status = s(&score_data, "production_decision").or(out.status.take());
    push_insight_metric(out, "评分档", s(&score_data, "target_platform"), None);
    push_insight_metric(out, "评分", score_label(out.score), Some("pass"));
    push_insight_metric(out, "判定", s(&score_data, "verdict"), None);
    if let Some(scope) = score_data.get("scope") {
        push_insight_metric(
            out,
            "章节数",
            scope.get("chapter_count").and_then(value_label),
            None,
        );
    }
    if let Some(arr) = score_data.get("scores").and_then(|v| v.as_array()) {
        for item in arr.iter().take(12) {
            let label = s(item, "dimension_label")
                .or_else(|| s(item, "dimension"))
                .unwrap_or_else(|| "评分维度".into());
            let score = n_f64(item, "raw_score").or_else(|| n_f64(item, "score"));
            let mut evidence = Vec::new();
            if let Some(v) = s(item, "evidence") {
                evidence.push(short_text(&v, 180));
            }
            if let Some(v) = s(item, "improve_by") {
                evidence.push(short_text(&v, 180));
            }
            out.dimensions.push(QualityInsightDimension {
                key: s(item, "dimension"),
                label,
                score,
                value: n_f64(item, "weighted_score").map(|v| format!("加权 {v:.1}")),
                max: Some(10.0),
                status: status_from_counts(
                    0,
                    if score.unwrap_or(10.0) < 7.0 { 1 } else { 0 },
                    score,
                ),
                blocks: 0,
                warnings: if score.unwrap_or(10.0) < 7.0 { 1 } else { 0 },
                infos: 0,
                detail: s(item, "comment").map(|v| short_text(&v, 260)),
                evidence,
            });
        }
    }
    for (key, label) in [("title_check", "标题侧"), ("adaptation_check", "转制潜力")] {
        if let Some(check) = score_data.get(key).filter(|v| v.is_object()) {
            let score = n_f64(check, "total");
            let max = n_f64(check, "max_total");
            let risky = check
                .get("needs_rename")
                .or_else(|| check.get("low_potential"))
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            out.dimensions.push(QualityInsightDimension {
                key: Some(key.into()),
                label: label.into(),
                score,
                value: max.map(|m| format!("/ {m:.0}")),
                max,
                status: Some(if risky { "warn" } else { "pass" }.into()),
                blocks: 0,
                warnings: if risky { 1 } else { 0 },
                infos: 0,
                detail: s(check, "comment").map(|v| short_text(&v, 280)),
                evidence: vec![rel.into()],
            });
        }
    }
    if let Some(prior) = score_data.get("repetition_prior") {
        let level = prior
            .get("prior")
            .and_then(|v| s(v, "level"))
            .or_else(|| prior.get("summary").and_then(|v| s(v, "prior_level")));
        push_insight_metric(out, "重复/机械先验", level, None);
        if let Some(summary) = prior.get("summary") {
            push_insight_metric(
                out,
                "相邻最高重复",
                summary
                    .get("adjacent_max_jaccard")
                    .and_then(|v| v.as_f64())
                    .map(|v| format!("{:.2}%", v * 100.0)),
                None,
            );
            push_insight_metric(
                out,
                "低压缩章节",
                summary
                    .get("low_chapter_compression_count")
                    .and_then(value_label),
                None,
            );
        }
    }
    if let Some(deductions) = score_data.get("deductions").and_then(|v| v.as_array()) {
        for item in deductions.iter().take(6) {
            let title = s(item, "item").unwrap_or_else(|| "扣分项".into());
            out.issues.push(QualityInsightIssue {
                severity: "warn".into(),
                dimension: Some("score_deduction".into()),
                title,
                message: s(item, "reason").map(|v| short_text(&v, 260)),
                stage: Some("score".into()),
                path: Some(rel.into()),
                source: Some("novel-score".into()),
            });
        }
    }
    collect_tasks_from_array(out, &score_data, "next_actions", 8);
}

fn collect_novel_review(root: &Path, out: &mut QualityInsights) {
    let rel = "审稿/review_report.json";
    let Some(review_data) = read_json(&root.join(rel)) else {
        return;
    };
    push_source_file(out, root, rel, "小说审稿");
    if let Some(summary) = review_data.get("summary") {
        let blocks = n_i64(summary, "blocking_count").max(n_i64(summary, "block_count"));
        let warnings = n_i64(summary, "suggestion_count").max(n_i64(summary, "warning_count"));
        let infos = n_i64(summary, "polish_count").max(n_i64(summary, "info_count"));
        out.blocks += blocks;
        out.warnings += warnings;
        out.infos += infos;
        out.dimensions.push(QualityInsightDimension {
            key: Some("novel_review".into()),
            label: "审稿问题".into(),
            score: score_from_status(blocks, warnings, true),
            value: Some(format!("{} 项", blocks + warnings + infos)),
            max: Some(100.0),
            status: s(summary, "verdict")
                .or_else(|| status_from_counts(blocks, warnings, Some(100.0))),
            blocks,
            warnings,
            infos,
            detail: Some("blocking / suggestion / polish".into()),
            evidence: vec![rel.into()],
        });
    }
    collect_issues_from_array(out, &review_data, "findings", 12);
    collect_tasks_from_array(out, &review_data, "next_actions", 8);
}

fn collect_novel_compliance(root: &Path, out: &mut QualityInsights) {
    let rel = "合规/compliance_profile.json";
    let Some(data) = read_json(&root.join(rel)) else {
        push_source_file(out, root, "合规/compliance_profile.md", "合规 Profile");
        return;
    };
    push_source_file(out, root, rel, "合规 Profile");
    push_insight_metric(
        out,
        "合规阻断",
        data.get("blocking").and_then(value_label),
        None,
    );
    push_insight_metric(
        out,
        "合规提醒",
        data.get("warning").and_then(value_label),
        None,
    );
    if let Some(axes) = data.get("target_axes").and_then(|v| v.as_object()) {
        let enabled: Vec<String> = axes
            .iter()
            .filter_map(|(key, value)| {
                if value.as_bool().unwrap_or(false) {
                    Some(key.clone())
                } else {
                    None
                }
            })
            .collect();
        if !enabled.is_empty() {
            push_insight_metric(out, "发布轴", Some(enabled.join(" / ")), None);
        }
    }
    if let Some(reqs) = data.get("requirements").and_then(|v| v.as_array()) {
        for req in reqs.iter().take(12) {
            let status = s(req, "status");
            let severity = s(req, "severity");
            let ok = status
                .as_deref()
                .map(|v| matches!(v, "ok" | "pass" | "done" | "confirmed"))
                .unwrap_or(false);
            let tone = if ok {
                "pass".into()
            } else {
                severity_tone(severity.clone().or(status.clone()))
            };
            let blocks = if tone == "block" { 1 } else { 0 };
            let warnings = if tone == "warn" { 1 } else { 0 };
            out.blocks += blocks;
            out.warnings += warnings;
            out.dimensions.push(QualityInsightDimension {
                key: s(req, "id"),
                label: s(req, "title")
                    .or_else(|| s(req, "id"))
                    .unwrap_or_else(|| "合规项".into()),
                score: score_from_status(blocks, warnings, true),
                value: status.clone(),
                max: Some(100.0),
                status: Some(tone.clone()),
                blocks,
                warnings,
                infos: if tone == "info" { 1 } else { 0 },
                detail: s(req, "reason").map(|v| short_text(&v, 260)),
                evidence: string_array(req, "evidence_source_ids", 4),
            });
            if tone != "pass" {
                out.issues.push(QualityInsightIssue {
                    severity: tone,
                    dimension: Some("compliance".into()),
                    title: s(req, "title")
                        .or_else(|| s(req, "id"))
                        .unwrap_or_else(|| "合规待办".into()),
                    message: s(req, "reason").map(|v| short_text(&v, 280)),
                    stage: Some("release".into()),
                    path: Some(rel.into()),
                    source: Some("compliance_profile".into()),
                });
            }
        }
    }
}

fn collect_novel_dashboard(root: &Path, out: &mut QualityInsights) {
    let rel = "生产数据/novel_dashboard.json";
    let Some(data) = read_json(&root.join(rel)) else {
        return;
    };
    push_source_file(out, root, rel, "小说看板");
    if let Some(stage_counts) = data.get("stage_counts").and_then(|v| v.as_object()) {
        for (key, value) in stage_counts {
            push_insight_metric(out, &format!("阶段 {key}"), value_label(value), None);
        }
    }
    if let Some(release) = data.get("release") {
        let ready = release
            .get("release_ready")
            .and_then(|v| v.as_bool())
            .map(|v| if v { "ready" } else { "not ready" }.to_string());
        push_insight_metric(out, "导出状态", ready, None);
        let blockers = n_i64(release, "blocker_count");
        out.blocks += blockers;
        push_insight_metric(out, "导出阻断", Some(blockers.to_string()), None);
    }
    if let Some(revision) = data.get("revision") {
        push_insight_metric(
            out,
            "修订任务",
            revision.get("task_count").and_then(value_label),
            None,
        );
        push_insight_metric(
            out,
            "修订冲突",
            revision.get("conflicts").and_then(value_label),
            None,
        );
    }
    for rel in [
        "生产数据/novel_dashboard.html",
        "生产数据/visuals/novel_review_heatmap.html",
        "生产数据/visuals/novel_revision_kanban.html",
        "生产数据/visuals/novel_emotion_curve.html",
        "生产数据/visuals/novel_foreshadow_ledger.html",
        "生产数据/visuals/novel_relationship_timeline.html",
    ] {
        push_insight_artifact(
            out,
            root,
            rel.rsplit('/').next().unwrap_or(rel),
            rel,
            "visual",
        );
    }
}

fn select_dashboard_episode<'a>(data: &'a Value, ep: Option<&str>) -> Option<&'a Value> {
    let episodes = data.get("episodes").and_then(|v| v.as_array())?;
    if let Some(ep) = ep {
        if let Some(found) = episodes
            .iter()
            .find(|item| s(item, "episode").as_deref() == Some(ep))
        {
            return Some(found);
        }
    }
    episodes.last().or_else(|| episodes.first())
}

fn collect_dashboard_insights(root: &Path, out: &mut QualityInsights, ep: Option<&str>) {
    let rel = "生产数据/dashboard.json";
    let Some(data) = read_json(&root.join(rel)) else {
        return;
    };
    push_source_file(out, root, rel, "生产看板");
    if let Some(ep_data) = select_dashboard_episode(&data, ep) {
        out.episode = s(ep_data, "episode").or(out.episode.take());
        push_insight_metric(
            out,
            "成品通过率",
            ratio_metric(n_f64(ep_data, "final_pass_rate")),
            None,
        );
        push_insight_metric(
            out,
            "生成通过率",
            ratio_metric(n_f64(ep_data, "generation_pass_rate")),
            None,
        );
        push_insight_metric(
            out,
            "尝试",
            ep_data.get("generation_attempts").and_then(value_label),
            None,
        );
        push_insight_metric(
            out,
            "重抽",
            ep_data.get("redraw_count").and_then(value_label),
            None,
        );
        push_insight_metric(out, "耗时", s(ep_data, "duration_hms"), None);
        if let Some(costs) = ep_data.get("cost_totals").and_then(|v| v.as_object()) {
            for (unit, value) in costs.iter().take(3) {
                push_insight_metric(out, &format!("成本 {unit}"), value_label(value), None);
            }
        }
        let qa_blocks = n_i64(ep_data, "qa_blockers");
        let qa_warnings = n_i64(ep_data, "qa_warnings");
        let consistency_blocks = n_i64(ep_data, "consistency_blockers");
        let consistency_warnings = n_i64(ep_data, "consistency_warnings");
        out.blocks += qa_blocks + consistency_blocks;
        out.warnings += qa_warnings + consistency_warnings;
        out.dimensions.push(QualityInsightDimension {
            key: Some("final_pass_rate".into()),
            label: "成片通过率".into(),
            score: n_f64(ep_data, "final_pass_rate").map(|v| v * 100.0),
            value: ratio_metric(n_f64(ep_data, "final_pass_rate")),
            max: Some(100.0),
            status: status_from_counts(qa_blocks, qa_warnings, Some(100.0)),
            blocks: qa_blocks,
            warnings: qa_warnings,
            infos: 0,
            detail: Some("QA blockers / warnings".into()),
            evidence: vec![rel.into()],
        });
        out.dimensions.push(QualityInsightDimension {
            key: Some("generation_pass_rate".into()),
            label: "生成通过率".into(),
            score: n_f64(ep_data, "generation_pass_rate").map(|v| v * 100.0),
            value: ratio_metric(n_f64(ep_data, "generation_pass_rate")),
            max: Some(100.0),
            status: status_from_counts(0, n_i64(ep_data, "generation_fails"), Some(100.0)),
            blocks: 0,
            warnings: n_i64(ep_data, "generation_fails"),
            infos: 0,
            detail: Some("generation_passes / generation_attempts".into()),
            evidence: vec![rel.into()],
        });
        out.dimensions.push(QualityInsightDimension {
            key: Some("consistency".into()),
            label: "一致性".into(),
            score: score_from_status(consistency_blocks, consistency_warnings, true),
            value: Some(format!("{consistency_blocks}/{consistency_warnings}")),
            max: Some(100.0),
            status: status_from_counts(consistency_blocks, consistency_warnings, Some(100.0)),
            blocks: consistency_blocks,
            warnings: consistency_warnings,
            infos: 0,
            detail: Some("consistency blockers / warnings".into()),
            evidence: vec![rel.into()],
        });
    } else if let Some(alerts) = data.get("alert_counts") {
        let (blocks, warnings, infos) = insight_counts_from_summary(Some(alerts));
        out.blocks += blocks;
        out.warnings += warnings;
        out.infos += infos;
        push_insight_metric(
            out,
            "成品通过率",
            ratio_metric(n_f64(alerts, "final_pass_rate")),
            None,
        );
        push_insight_metric(
            out,
            "生成通过率",
            ratio_metric(n_f64(alerts, "generation_pass_rate")),
            None,
        );
        push_insight_metric(out, "下一阶段", s(alerts, "progress_next_stage"), None);
    }
}

fn collect_yield_insights(root: &Path, out: &mut QualityInsights) {
    let rel = "生产数据/yield_summary.json";
    let Some(data) = read_json(&root.join(rel)) else {
        return;
    };
    push_source_file(out, root, rel, "出图产能");
    push_insight_metric(
        out,
        "可用率",
        ratio_metric(n_f64(&data, "usable_yield")),
        None,
    );
    push_insight_metric(
        out,
        "重抽率",
        ratio_metric(n_f64(&data, "reroll_rate")),
        None,
    );
    push_insight_metric(
        out,
        "候选数",
        data.get("total_candidates").and_then(value_label),
        None,
    );
    out.dimensions.push(QualityInsightDimension {
        key: Some("usable_yield".into()),
        label: "候选可用率".into(),
        score: n_f64(&data, "usable_yield").map(|v| v * 100.0),
        value: ratio_metric(n_f64(&data, "usable_yield")),
        max: Some(100.0),
        status: status_from_counts(
            0,
            if n_f64(&data, "usable_yield").unwrap_or(1.0) < 0.8 {
                1
            } else {
                0
            },
            Some(100.0),
        ),
        blocks: 0,
        warnings: if n_f64(&data, "usable_yield").unwrap_or(1.0) < 0.8 {
            1
        } else {
            0
        },
        infos: 0,
        detail: Some("survivors / candidates".into()),
        evidence: vec![rel.into()],
    });
}

fn collect_finding_json(root: &Path, out: &mut QualityInsights, rel: &str, data: &Value) {
    push_source_file(out, root, rel, rel);
    let summary = data.get("summary");
    let (blocks, warnings, infos) = insight_counts_from_summary(summary);
    out.blocks += blocks;
    out.warnings += warnings;
    out.infos += infos;
    if blocks > 0 || warnings > 0 || infos > 0 {
        out.dimensions.push(QualityInsightDimension {
            key: Some(rel.into()),
            label: rel
                .rsplit('/')
                .next()
                .unwrap_or(rel)
                .trim_end_matches(".json")
                .into(),
            score: score_from_status(blocks, warnings, true),
            value: Some(format!("{blocks}/{warnings}/{infos}")),
            max: Some(100.0),
            status: status_from_counts(blocks, warnings, Some(100.0)),
            blocks,
            warnings,
            infos,
            detail: Some("block / warn / info".into()),
            evidence: vec![rel.into()],
        });
    }
    push_dimensions_from_by_dim(out, rel, summary.and_then(|v| v.get("by_dim")));
    collect_issues_from_array(out, data, "findings", 10);
    collect_issues_from_array(out, data, "issues", 10);
    collect_tasks_from_array(out, data, "auto_return_tasks", 6);
    collect_tasks_from_array(out, data, "return_tasks", 6);
    collect_tasks_from_array(out, data, "next_actions", 6);
}

fn should_collect_production_json(name: &str, ep: Option<&str>) -> bool {
    if !name.ends_with(".json") {
        return false;
    }
    let prefixes = [
        "gate_findings",
        "review_ui_findings",
        "release_verdict",
        "comic_review",
        "comic_style_consistency",
        "comic_identity_report",
        "consistency_findings",
        "raw_bubble_acceptance",
        "style_consistency_acceptance",
        "image_qc",
        "video_qc",
        "score_",
    ];
    if !prefixes.iter().any(|prefix| name.starts_with(prefix)) {
        return false;
    }
    match ep {
        Some(ep) if name.contains('第') => name.contains(ep),
        _ => true,
    }
}

fn collect_generic_production(root: &Path, out: &mut QualityInsights, ep: Option<&str>) {
    collect_dashboard_insights(root, out, ep);
    collect_yield_insights(root, out);
    let prod = root.join("生产数据");
    let Ok(entries) = fs::read_dir(&prod) else {
        return;
    };
    let mut files: Vec<PathBuf> = entries
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.is_file())
        .filter(|path| {
            path.file_name()
                .and_then(|v| v.to_str())
                .map(|name| should_collect_production_json(name, ep))
                .unwrap_or(false)
        })
        .collect();
    files.sort();
    for path in files.into_iter().take(24) {
        let Some(name) = path.file_name().and_then(|v| v.to_str()) else {
            continue;
        };
        let rel = format!("生产数据/{name}");
        if let Some(data) = read_json(&path) {
            collect_finding_json(root, out, &rel, &data);
        }
    }
    for rel in [
        "合规/compliance_manifest.json",
        "合规/AI使用说明.md",
        "生产数据/dashboard.html",
        "生产数据/board.html",
        "生产数据/dashboard.md",
    ] {
        push_insight_artifact(
            out,
            root,
            rel.rsplit('/').next().unwrap_or(rel),
            rel,
            "evidence",
        );
    }
}

fn finalize_quality_insights(out: &mut QualityInsights) {
    out.issues.truncate(28);
    out.tasks.truncate(18);
    out.metrics.truncate(28);
    out.dimensions.sort_by(|a, b| {
        b.blocks
            .cmp(&a.blocks)
            .then(b.warnings.cmp(&a.warnings))
            .then_with(|| {
                a.score
                    .unwrap_or(999.0)
                    .partial_cmp(&b.score.unwrap_or(999.0))
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
    });
    out.dimensions.truncate(24);
    let mut seen = HashSet::new();
    out.artifacts.retain(|item| seen.insert(item.path.clone()));
    out.artifacts.truncate(24);
    if out.status.is_none() {
        out.status = status_from_counts(out.blocks, out.warnings, out.score);
    }
}

#[tauri::command]
pub fn read_quality_insights(root: String, line: String, ep: Option<String>) -> QualityInsights {
    let root_p = Path::new(&root);
    let clean_ep = ep
        .filter(|value| validate_episode_name(value).is_ok())
        .filter(|value| !value.trim().is_empty());
    let mut out = QualityInsights {
        line: line.clone(),
        episode: clean_ep.clone(),
        ..Default::default()
    };
    if line == "novel" {
        collect_novel_score(root_p, &mut out);
        collect_novel_review(root_p, &mut out);
        collect_novel_compliance(root_p, &mut out);
        collect_novel_dashboard(root_p, &mut out);
    } else {
        collect_generic_production(root_p, &mut out, clean_ep.as_deref());
    }
    finalize_quality_insights(&mut out);
    out
}

fn push_frame(
    frames: &mut Vec<CanvasFrame>,
    root: &Path,
    role: &str,
    label: &str,
    rel: Option<String>,
    at_sec: Option<f64>,
    prompt: Option<String>,
) {
    let (abs, exists) = rel_abs(root, rel);
    frames.push(CanvasFrame {
        role: role.into(),
        label: label.into(),
        abs,
        exists,
        at_sec,
        prompt,
    });
}

fn storyboard_frames(root: &Path, c: &Value, _prompt: Option<String>) -> Vec<CanvasFrame> {
    let mut frames = Vec::new();
    push_frame(
        &mut frames,
        root,
        "first",
        "首帧",
        s(c, "firstframe_png"),
        Some(0.0),
        None,
    );
    let null = Value::Null;
    let continuity = c.get("continuity").unwrap_or(&null);
    if let Some(anchors) = continuity.get("anchors").and_then(|x| x.as_array()) {
        for (idx, raw) in anchors.iter().enumerate() {
            let rel = s(raw, "anchor_png")
                .or_else(|| s(raw, "png"))
                .or_else(|| s(raw, "path"))
                .or_else(|| s(raw, "image"))
                .or_else(|| s(raw, "image_path"));
            let at = raw.get("at_sec").and_then(|x| x.as_f64());
            let reason = s(raw, "reason");
            let frame_prompt = reason
                .filter(|r| !r.trim().is_empty())
                .map(|r| format!("reason: {r}"));
            push_frame(
                &mut frames,
                root,
                "anchor",
                &format!("中帧{}", idx + 1),
                rel,
                at,
                frame_prompt,
            );
        }
    } else if let Some(mid) = s(continuity, "midframe").or_else(|| s(c, "midframe")) {
        push_frame(&mut frames, root, "anchor", "中帧", Some(mid), None, None);
    }
    let end_rel = s(continuity, "endframe_png").or_else(|| s(c, "endframe_png"));
    push_frame(
        &mut frames,
        root,
        "end",
        "尾帧",
        end_rel,
        c.get("duration").and_then(|d| d.as_f64()),
        None,
    );

    let mut seen = HashSet::new();
    frames
        .into_iter()
        .filter(|f| {
            let key = format!("{}:{}", f.role, f.abs.clone().unwrap_or_default());
            seen.insert(key)
        })
        .collect()
}

fn review_asset_frame(
    root: &Path,
    raw: &Value,
    fallback_label: &str,
    prompt: Option<String>,
) -> CanvasFrame {
    let rel = s(raw, "path");
    let (abs, exists_by_path) = rel_abs(root, rel);
    CanvasFrame {
        role: s(raw, "role").unwrap_or_else(|| fallback_label.into()),
        label: s(raw, "label")
            .or_else(|| s(raw, "name"))
            .unwrap_or_else(|| fallback_label.into()),
        abs,
        exists: raw
            .get("exists")
            .and_then(|e| e.as_bool())
            .unwrap_or(exists_by_path),
        at_sec: raw.get("at_sec").and_then(|x| x.as_f64()),
        prompt,
    }
}

fn review_frames(root: &Path, c: &Value, _prompt: Option<String>) -> Vec<CanvasFrame> {
    let mut frames = Vec::new();
    if let Some(arr) = c.get("anchor_frames").and_then(|x| x.as_array()) {
        for raw in arr {
            frames.push(review_asset_frame(root, raw, "锚帧", None));
        }
    }
    if frames.is_empty() {
        if let Some(first) = c.get("first_frame") {
            frames.push(review_asset_frame(root, first, "首帧", None));
        }
        if let Some(end) = c.get("end_frame") {
            frames.push(review_asset_frame(root, end, "尾帧", None));
        }
    }
    if let Some(arr) = c.get("consumed_frames").and_then(|x| x.as_array()) {
        let mut seen_paths: HashSet<String> = frames.iter().filter_map(|f| f.abs.clone()).collect();
        for raw in arr {
            let frame = review_asset_frame(root, raw, "入参", None);
            if frame
                .abs
                .as_ref()
                .map(|p| seen_paths.insert(p.clone()))
                .unwrap_or(true)
            {
                frames.push(frame);
            }
        }
    }
    frames
}

fn from_storyboard(root: &Path, ep: &str, data: &Value) -> Vec<CanvasClip> {
    let empty = vec![];
    let clips = data
        .get("clips")
        .and_then(|c| c.as_array())
        .unwrap_or(&empty);
    clips
        .iter()
        .enumerate()
        .map(|(i, c)| {
            let prompt = clip_prompt(c);
            let frames = storyboard_frames(root, c, prompt.clone());
            let ff_rel = s(c, "firstframe_png");
            let (ff_abs, ff_exists) = rel_abs(root, ff_rel);
            let vid_rel = s(c, "video_out");
            let (vid_abs, vid_exists) = rel_abs(root, vid_rel);
            CanvasClip {
                id: s(c, "id").unwrap_or_else(|| format!("{ep}_CLIP{:02}", i + 1)),
                number: c
                    .get("number")
                    .and_then(|n| n.as_i64())
                    .or(Some((i + 1) as i64)),
                label: s(c, "label").unwrap_or_default(),
                duration: c.get("duration").and_then(|d| d.as_f64()),
                scene: s(c, "scene"),
                rhythm: s(c, "rhythm"),
                template: s(c, "template"),
                first_frame_abs: ff_abs,
                first_frame_exists: ff_exists,
                video_abs: vid_abs,
                video_exists: vid_exists,
                frames,
                prompt,
                qa: vec![],
                score: None,
                qa_blocks: 0,
                qa_warnings: 0,
                qa_infos: 0,
            }
        })
        .collect()
}

fn seams_from_clips(clips: &[CanvasClip], data: &Value) -> Vec<CanvasSeam> {
    let empty = vec![];
    let raw = data
        .get("clips")
        .and_then(|c| c.as_array())
        .unwrap_or(&empty);
    let mut seams = Vec::new();
    for i in 0..clips.len().saturating_sub(1) {
        let transition = raw
            .get(i)
            .and_then(|c| c.get("continuity"))
            .and_then(|c| c.get("transition"))
            .and_then(|t| t.as_str())
            .map(|t| t.to_string());
        seams.push(CanvasSeam {
            from: clips[i].id.clone(),
            to: clips[i + 1].id.clone(),
            transition,
        });
    }
    seams
}

fn sequential_seams(clips: &[CanvasClip], transition: Option<&str>) -> Vec<CanvasSeam> {
    let mut seams = Vec::new();
    for i in 0..clips.len().saturating_sub(1) {
        seams.push(CanvasSeam {
            from: clips[i].id.clone(),
            to: clips[i + 1].id.clone(),
            transition: transition.map(|value| value.to_string()),
        });
    }
    seams
}

fn is_shared_asset_rel(rel: &str) -> bool {
    let rel = rel.replace('\\', "/").to_lowercase();
    rel.contains("出图/共享/") || rel.contains("/shared/")
}

fn is_canvas_image_path(path: &Path) -> bool {
    matches!(
        path.extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext.to_ascii_lowercase())
            .as_deref(),
        Some("png" | "jpg" | "jpeg" | "webp" | "gif")
    )
}

fn push_shared_asset_files(root: &Path, dir: &Path, depth: usize, out: &mut Vec<CanvasFrame>) {
    if depth > 4 || out.len() >= 160 {
        return;
    }
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    let mut paths: Vec<PathBuf> = entries.flatten().map(|entry| entry.path()).collect();
    paths.sort();
    for path in paths {
        if out.len() >= 160 {
            break;
        }
        if path.is_dir() {
            push_shared_asset_files(root, &path, depth + 1, out);
            continue;
        }
        if !path.is_file() || !is_canvas_image_path(&path) {
            continue;
        }
        let rel = path
            .strip_prefix(root)
            .ok()
            .and_then(|p| p.to_str())
            .map(|p| p.replace('\\', "/"))
            .unwrap_or_else(|| path.to_string_lossy().replace('\\', "/"));
        if !is_shared_asset_rel(&rel) {
            continue;
        }
        let label = path
            .file_stem()
            .and_then(|v| v.to_str())
            .unwrap_or("共享资产")
            .to_string();
        out.push(CanvasFrame {
            role: "shared_asset".into(),
            label,
            abs: Some(path.to_string_lossy().to_string()),
            exists: true,
            at_sec: None,
            prompt: Some(rel),
        });
    }
}

fn shared_asset_frames(root: &Path) -> Vec<CanvasFrame> {
    let shared = root.join("出图").join("共享");
    let mut out = Vec::new();
    for dir in [shared.join("图片"), shared.join("用户参考"), shared.clone()] {
        push_shared_asset_files(root, &dir, 0, &mut out);
    }
    let mut seen = HashSet::new();
    out.retain(|frame| {
        frame
            .abs
            .as_ref()
            .map(|abs| seen.insert(abs.clone()))
            .unwrap_or(false)
    });
    out.sort_by(|a, b| a.label.cmp(&b.label));
    out
}

fn comic_reference_label(raw: &Value) -> String {
    let id = s(raw, "id").unwrap_or_else(|| "共享资产".into());
    let view = s(raw, "view")
        .map(|v| v.trim_end_matches("_path").to_string())
        .filter(|v| !v.trim().is_empty());
    match view {
        Some(view) => format!("{id} / {view}"),
        None => id,
    }
}

fn push_comic_shared_asset_frame(
    frames: &mut Vec<CanvasFrame>,
    seen: &mut HashSet<String>,
    root: &Path,
    id: &str,
    view: &str,
    rel: String,
) {
    if !is_shared_asset_rel(&rel) || !seen.insert(rel.clone()) {
        return;
    }
    let (abs, exists) = rel_abs(root, Some(rel.clone()));
    if !exists {
        return;
    }
    let view_label = view.trim_end_matches("_path");
    frames.push(CanvasFrame {
        role: "shared_asset".into(),
        label: if view_label.is_empty() {
            id.to_string()
        } else {
            format!("{id} / {view_label}")
        },
        abs,
        exists,
        at_sec: None,
        prompt: Some(format!("id: {id}\nview: {view}\n{rel}")),
    });
}

fn comic_reference_frames(root: &Path, panel: &Value, job: Option<&Value>) -> Vec<CanvasFrame> {
    let mut frames = Vec::new();
    let mut seen = HashSet::new();
    let refs = job
        .and_then(|j| j.get("references"))
        .and_then(|refs| refs.as_array());
    if let Some(refs) = refs {
        for raw in refs {
            let rel = match s(raw, "path") {
                Some(rel) if is_shared_asset_rel(&rel) => rel,
                _ => continue,
            };
            if !seen.insert(rel.clone()) {
                continue;
            }
            let label = comic_reference_label(raw);
            let (abs, exists) = rel_abs(root, Some(rel.clone()));
            let prompt = Some(
                [
                    s(raw, "id").map(|id| format!("id: {id}")),
                    s(raw, "view").map(|view| format!("view: {view}")),
                    Some(rel),
                ]
                .into_iter()
                .flatten()
                .collect::<Vec<_>>()
                .join("\n"),
            );
            frames.push(CanvasFrame {
                role: "shared_asset".into(),
                label,
                abs,
                exists,
                at_sec: None,
                prompt,
            });
        }
    }

    if let Some(scene_id) = s(panel, "scene_anchor_id").or_else(|| s(panel, "location")) {
        push_comic_shared_asset_frame(
            &mut frames,
            &mut seen,
            root,
            &scene_id,
            "anchor",
            format!("出图/共享/图片/{scene_id}__anchor.png"),
        );
    }
    if let Some(refs) = panel.get("references").and_then(|refs| refs.as_array()) {
        for raw in refs {
            if let Some(id) = raw.as_str().filter(|id| !id.trim().is_empty()) {
                push_comic_shared_asset_frame(
                    &mut frames,
                    &mut seen,
                    root,
                    id,
                    "anchor",
                    format!("出图/共享/图片/{id}__anchor.png"),
                );
            }
        }
    }
    frames
}

fn comic_panel_jobs(root: &Path, ep: &str) -> BTreeMap<String, Value> {
    read_json(
        &root
            .join("出图")
            .join(ep)
            .join("prompt")
            .join("panel_jobs.json"),
    )
    .and_then(|v| v.get("jobs").and_then(|jobs| jobs.as_array()).cloned())
    .map(|jobs| {
        jobs.into_iter()
            .filter_map(|job| s(&job, "panel_id").map(|id| (id, job)))
            .collect()
    })
    .unwrap_or_default()
}

fn comic_panel_qc(root: &Path, ep: &str, panel_id: &str, job: Option<&Value>) -> Option<Value> {
    job.and_then(|j| j.get("post_qc"))
        .filter(|v| v.is_object())
        .cloned()
        .or_else(|| {
            read_json(
                &root
                    .join("生产数据")
                    .join("panel_qc")
                    .join(ep)
                    .join(format!("{panel_id}.json")),
            )
        })
}

fn comic_findings_by_panel(root: &Path, ep: &str) -> BTreeMap<String, Vec<Value>> {
    let mut out: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    for file in [
        format!("consistency_findings_style_{ep}.json"),
        format!("comic_consistency_findings_{ep}.json"),
    ] {
        let Some(data) = read_json(&root.join("生产数据").join(file)) else {
            continue;
        };
        let Some(findings) = data.get("findings").and_then(|v| v.as_array()) else {
            continue;
        };
        for finding in findings {
            if let Some(panel_id) = s(finding, "panel_id") {
                out.entry(panel_id).or_default().push(finding.clone());
            }
        }
    }
    out
}

fn comic_dialogue_lines(panel: &Value) -> Vec<String> {
    panel
        .get("dialogue")
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|item| {
                    let text = s(item, "text")?;
                    let speaker = s(item, "speaker").unwrap_or_default();
                    if speaker.trim().is_empty() {
                        Some(text)
                    } else {
                        Some(format!("{speaker}: {text}"))
                    }
                })
                .collect()
        })
        .unwrap_or_default()
}

fn comic_dialogue_from_text(input: &str) -> Vec<Value> {
    input
        .lines()
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
        .map(|line| {
            let mut obj = serde_json::Map::new();
            let split_at = line.find('：').or_else(|| line.find(':'));
            if let Some(idx) = split_at {
                let speaker = line[..idx].trim();
                let text = line[idx + 1..].trim();
                if !speaker.is_empty() {
                    obj.insert("speaker".into(), Value::String(speaker.to_string()));
                }
                obj.insert("text".into(), Value::String(text.to_string()));
            } else {
                obj.insert("text".into(), Value::String(line.to_string()));
            }
            Value::Object(obj)
        })
        .collect()
}

fn set_dialogue_field(obj: &mut serde_json::Map<String, Value>, input: &str) {
    let values = comic_dialogue_from_text(input);
    if values.is_empty() {
        obj.remove("dialogue");
    } else {
        obj.insert("dialogue".into(), Value::Array(values));
    }
}

fn comic_panel_size_label(job: Option<&Value>) -> Option<String> {
    let size = job.and_then(|j| j.get("size"))?;
    let w = size.get("width").and_then(|v| v.as_i64())?;
    let h = size.get("height").and_then(|v| v.as_i64())?;
    Some(format!("{w}x{h}"))
}

fn comic_panel_prompt(panel: &Value, job: Option<&Value>) -> Option<String> {
    let mut parts = Vec::new();
    if let Some(desc) = s(panel, "description") {
        parts.push(format!("description: {desc}"));
    }
    if let Some(notes) = s(panel, "art_notes") {
        parts.push(format!("art_notes: {notes}"));
    }
    let dialogue = comic_dialogue_lines(panel);
    if !dialogue.is_empty() {
        parts.push(format!("dialogue: {}", dialogue.join(" / ")));
    }
    if let Some(narration) = s(panel, "narration").filter(|v| !v.trim().is_empty()) {
        parts.push(format!("narration: {narration}"));
    }
    let sfx = string_array(panel, "sfx", 12);
    if !sfx.is_empty() {
        parts.push(format!("sfx: {}", sfx.join(" / ")));
    }
    if let Some(job_prompt) = job.and_then(|j| s(j, "prompt")) {
        parts.push(format!("image_prompt: {}", short_text(&job_prompt, 1200)));
    }
    if let Some(negative) = job.and_then(|j| s(j, "negative_prompt")) {
        parts.push(format!("negative_prompt: {}", short_text(&negative, 600)));
    }
    if parts.is_empty() {
        None
    } else {
        Some(short_text(&parts.join("\n"), CANVAS_PROMPT_PREVIEW_LIMIT))
    }
}

fn accepted_manual_review(qc: &Value) -> bool {
    qc.get("manual_review")
        .and_then(|v| s(v, "status"))
        .map(|status| {
            status.eq_ignore_ascii_case("accepted") || status.eq_ignore_ascii_case("pass")
        })
        .unwrap_or(false)
}

fn push_comic_qc_flags(flags: &mut Vec<QaFlag>, qc: Option<&Value>) {
    let Some(qc) = qc else {
        return;
    };
    let accepted = accepted_manual_review(qc);
    let verdict = s(qc, "verdict").unwrap_or_else(|| "info".into());
    if let Some(issues) = qc.get("issues").and_then(|v| v.as_array()) {
        for issue in issues {
            flags.push(QaFlag {
                severity: if accepted {
                    "info".into()
                } else {
                    s(issue, "severity").unwrap_or_else(|| verdict.clone())
                },
                status: Some(if accepted {
                    "accepted".into()
                } else {
                    verdict.clone()
                }),
                dimension: s(issue, "category").or_else(|| Some("panel_qc".into())),
                message: s(issue, "reason").or_else(|| s(issue, "message")),
                score: None,
            });
        }
    }
    if verdict != "pass" && flags.is_empty() {
        flags.push(QaFlag {
            severity: if accepted { "info".into() } else { verdict },
            status: s(qc, "verdict"),
            dimension: Some("panel_qc".into()),
            message: Some("面板后检未通过或需要复核".into()),
            score: None,
        });
    }
    if qc
        .get("manual_review_required")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
        && !accepted
    {
        flags.push(QaFlag {
            severity: "warn".into(),
            status: Some("manual_review_required".into()),
            dimension: Some("panel_qc".into()),
            message: Some("需要人工复核".into()),
            score: None,
        });
    }
}

fn push_comic_finding_flags(flags: &mut Vec<QaFlag>, findings: Option<&Vec<Value>>) {
    let Some(findings) = findings else {
        return;
    };
    for finding in findings {
        flags.push(QaFlag {
            severity: s(finding, "severity").unwrap_or_else(|| "warn".into()),
            status: s(finding, "status"),
            dimension: s(finding, "dimension")
                .or_else(|| s(finding, "code"))
                .or_else(|| Some("consistency".into())),
            message: s(finding, "reason")
                .or_else(|| s(finding, "suggested_fix"))
                .or_else(|| s(finding, "message")),
            score: None,
        });
    }
}

fn qa_counts(qa: &[QaFlag]) -> (i64, i64, i64) {
    let blocks = qa
        .iter()
        .filter(|f| {
            f.severity.eq_ignore_ascii_case("block") || f.status.as_deref() == Some("block")
        })
        .count() as i64;
    let warnings = qa
        .iter()
        .filter(|f| f.severity.eq_ignore_ascii_case("warn") || f.status.as_deref() == Some("warn"))
        .count() as i64;
    let infos = qa
        .iter()
        .filter(|f| f.severity.eq_ignore_ascii_case("info") || f.status.as_deref() == Some("info"))
        .count() as i64;
    (blocks, warnings, infos)
}

fn from_comic_panel_script(root: &Path, ep: &str, data: &Value) -> Vec<CanvasClip> {
    let empty = vec![];
    let panels = data
        .get("panels")
        .and_then(|p| p.as_array())
        .unwrap_or(&empty);
    let jobs = comic_panel_jobs(root, ep);
    let findings = comic_findings_by_panel(root, ep);
    panels
        .iter()
        .enumerate()
        .map(|(i, panel)| {
            let panel_id = s(panel, "panel_id").unwrap_or_else(|| format!("P{:03}", i + 1));
            let job = jobs.get(&panel_id);
            let qc = comic_panel_qc(root, ep, &panel_id, job);
            let prompt = comic_panel_prompt(panel, job);
            let image_rel = job
                .and_then(|j| s(j, "result_path"))
                .or_else(|| qc.as_ref().and_then(|q| s(q, "path")))
                .or_else(|| Some(format!("出图/{ep}/panels/{panel_id}.png")));
            let (image_abs, image_exists) = rel_abs(root, image_rel);
            let mut frames = vec![CanvasFrame {
                role: "panel".into(),
                label: "成图".into(),
                abs: image_abs.clone(),
                exists: image_exists,
                at_sec: None,
                prompt: prompt.clone(),
            }];
            frames.extend(comic_reference_frames(root, panel, job));
            let mut qa = Vec::new();
            push_comic_qc_flags(&mut qa, qc.as_ref());
            push_comic_finding_flags(&mut qa, findings.get(&panel_id));
            if let Some(status) = job.and_then(|j| s(j, "status")) {
                if status != "ready" && status != "done" && status != "pass" {
                    qa.push(QaFlag {
                        severity: "warn".into(),
                        status: Some(status.clone()),
                        dimension: Some("image_job".into()),
                        message: Some(format!("出图任务状态：{status}")),
                        score: None,
                    });
                }
            }
            let (qa_blocks, qa_warnings, qa_infos) = qa_counts(&qa);
            let score = if qa_blocks > 0 {
                Some(50.0)
            } else if qa_warnings > 0 {
                Some(75.0)
            } else if image_exists || qc.is_some() {
                Some(100.0)
            } else {
                None
            };
            CanvasClip {
                id: panel_id.clone(),
                number: number_from_id(&panel_id).or(Some((i + 1) as i64)),
                label: s(panel, "story_function").unwrap_or_else(|| panel_id.clone()),
                duration: None,
                scene: s(panel, "location"),
                rhythm: s(panel, "story_function"),
                template: comic_panel_size_label(job),
                first_frame_abs: image_abs,
                first_frame_exists: image_exists,
                video_abs: None,
                video_exists: false,
                frames,
                prompt,
                qa,
                score,
                qa_blocks,
                qa_warnings,
                qa_infos,
            }
        })
        .collect()
}

fn insert_clip_key(lookup: &mut BTreeMap<String, String>, key: &str, id: &str) {
    let key = key.trim();
    if key.is_empty() || id.trim().is_empty() {
        return;
    }
    lookup
        .entry(key.to_string())
        .or_insert_with(|| id.to_string());
}

fn resolve_seam_endpoint(
    raw: Option<String>,
    fallback_idx: Option<usize>,
    clips: &[CanvasClip],
    lookup: &BTreeMap<String, String>,
) -> Option<String> {
    if let Some(raw) = raw {
        if let Some(id) = lookup.get(raw.trim()) {
            return Some(id.clone());
        }
    }
    fallback_idx
        .and_then(|idx| clips.get(idx))
        .map(|clip| clip.id.clone())
        .filter(|id| !id.trim().is_empty())
}

fn review_seams_from_clips(clips: &[CanvasClip], data: &Value) -> Vec<CanvasSeam> {
    let mut lookup = BTreeMap::new();
    for clip in clips {
        insert_clip_key(&mut lookup, &clip.id, &clip.id);
        insert_clip_key(&mut lookup, &clip.label, &clip.id);
        if let Some(n) = clip.number {
            insert_clip_key(&mut lookup, &n.to_string(), &clip.id);
            insert_clip_key(&mut lookup, &format!("Clip_{n:02}"), &clip.id);
            insert_clip_key(&mut lookup, &format!("Clip{n:02}"), &clip.id);
        }
    }

    let mut seams = Vec::new();
    let mut seen = HashSet::new();
    if let Some(arr) = data.get("seams").and_then(|x| x.as_array()) {
        for (idx, sm) in arr.iter().enumerate() {
            let base_idx = sm
                .get("index")
                .and_then(|x| x.as_i64())
                .and_then(|n| if n > 0 { Some((n - 1) as usize) } else { None })
                .unwrap_or(idx);
            let from = resolve_seam_endpoint(s(sm, "from"), Some(base_idx), clips, &lookup);
            let to = resolve_seam_endpoint(s(sm, "to"), Some(base_idx + 1), clips, &lookup);
            if let (Some(from), Some(to)) = (from, to) {
                if from != to && seen.insert(format!("{from}->{to}")) {
                    seams.push(CanvasSeam {
                        from,
                        to,
                        transition: s(sm, "transition"),
                    });
                }
            }
        }
    }

    if seams.is_empty() {
        for i in 0..clips.len().saturating_sub(1) {
            seams.push(CanvasSeam {
                from: clips[i].id.clone(),
                to: clips[i + 1].id.clone(),
                transition: None,
            });
        }
    }
    seams
}

fn from_review_ui(root: &Path, data: &Value) -> (Vec<CanvasClip>, Vec<CanvasSeam>) {
    let empty = vec![];
    let clips = data
        .get("clips")
        .and_then(|c| c.as_array())
        .unwrap_or(&empty);
    let out_clips: Vec<CanvasClip> = clips
        .iter()
        .map(|c| {
            let prompt = clip_prompt(c);
            let frames = review_frames(root, c, prompt.clone());
            let ff = c.get("first_frame").cloned().unwrap_or(Value::Null);
            let ff_path = s(&ff, "path");
            let (ff_abs, ff_exists_by_path) = rel_abs(root, ff_path);
            let video = c.get("video").cloned().unwrap_or(Value::Null);
            let (vid_abs, vid_exists_by_path) = rel_abs(root, s(&video, "path"));
            let qa: Vec<QaFlag> = c
                .get("qa_flags")
                .and_then(|q| q.as_array())
                .map(|arr| {
                    arr.iter()
                        .map(|f| QaFlag {
                            severity: s(f, "severity").unwrap_or_else(|| "info".into()),
                            status: s(f, "status"),
                            dimension: s(f, "dimension"),
                            message: s(f, "message"),
                            score: n_f64(f, "score"),
                        })
                        .collect()
                })
                .unwrap_or_default();
            let qa_blocks = qa
                .iter()
                .filter(|f| {
                    f.severity.eq_ignore_ascii_case("block") || f.status.as_deref() == Some("block")
                })
                .count() as i64;
            let qa_warnings = qa
                .iter()
                .filter(|f| {
                    f.severity.eq_ignore_ascii_case("warn") || f.status.as_deref() == Some("warn")
                })
                .count() as i64;
            let qa_infos = qa
                .iter()
                .filter(|f| {
                    f.severity.eq_ignore_ascii_case("info") || f.status.as_deref() == Some("info")
                })
                .count() as i64;
            let score = qa.iter().filter_map(|f| f.score).reduce(f64::min);
            CanvasClip {
                id: s(c, "id").unwrap_or_default(),
                number: c.get("number").and_then(|n| n.as_i64()),
                label: s(c, "label").unwrap_or_default(),
                duration: c.get("duration").and_then(|d| d.as_f64()),
                scene: s(c, "scene"),
                rhythm: s(c, "rhythm"),
                template: s(c, "template"),
                first_frame_exists: ff
                    .get("exists")
                    .and_then(|e| e.as_bool())
                    .unwrap_or(ff_exists_by_path),
                first_frame_abs: ff_abs,
                video_abs: vid_abs,
                video_exists: video
                    .get("exists")
                    .and_then(|e| e.as_bool())
                    .unwrap_or(vid_exists_by_path),
                frames,
                prompt,
                qa,
                score,
                qa_blocks,
                qa_warnings,
                qa_infos,
            }
        })
        .collect();
    let seams = review_seams_from_clips(&out_clips, data);
    (out_clips, seams)
}

#[tauri::command]
pub fn read_canvas(root: String, ep: String) -> CanvasData {
    let root_p = Path::new(&root);
    let episodes = list_episodes(root_p);
    let mut out = CanvasData {
        source: "none".into(),
        episode: ep.clone(),
        episodes,
        shared_assets: shared_asset_frames(root_p),
        ..Default::default()
    };

    // 1) review_ui_第N集.json (preferred — has QA + score)
    let review = root_p.join("生产数据").join(format!("review_ui_{ep}.json"));
    if let Ok(txt) = fs::read_to_string(&review) {
        if let Ok(v) = serde_json::from_str::<Value>(&txt) {
            let (clips, seams) = from_review_ui(root_p, &v);
            out.source = "review_ui".into();
            out.title = v
                .get("storyboard")
                .and_then(|s| s.get("title"))
                .and_then(|t| t.as_str())
                .map(|t| t.to_string());
            out.total_duration = v
                .get("storyboard")
                .and_then(|s| s.get("total_duration"))
                .and_then(|d| d.as_f64());
            out.quality = quality_summary(root_p, &ep, Some(&v));
            out.clips = clips;
            out.seams = seams;
            return out;
        }
    }

    // 2) storyboard.json fallback
    let sb = root_p.join("脚本").join(&ep).join("storyboard.json");
    if let Ok(txt) = fs::read_to_string(&sb) {
        if let Ok(v) = serde_json::from_str::<Value>(&txt) {
            let clips = from_storyboard(root_p, &ep, &v);
            out.seams = seams_from_clips(&clips, &v);
            out.title = s(&v, "title");
            out.total_duration = v.get("total_duration").and_then(|d| d.as_f64());
            out.source = "storyboard".into();
            out.clips = clips;
            out.quality = quality_summary(root_p, &ep, None);
            return out;
        }
    }

    // 3) comic panel_script.json fallback (画漫画: panels + optional panel jobs/QC)
    let panel_script = root_p.join("脚本").join(&ep).join("panel_script.json");
    if let Ok(txt) = fs::read_to_string(&panel_script) {
        if let Ok(v) = serde_json::from_str::<Value>(&txt) {
            let clips = from_comic_panel_script(root_p, &ep, &v);
            out.seams = sequential_seams(&clips, Some("下一格"));
            out.title = s(&v, "title");
            out.source = "panel_script".into();
            out.quality = comic_quality_summary(root_p, &ep, &clips);
            out.clips = clips;
            return out;
        }
    }

    out
}

#[tauri::command]
pub fn read_episode_workspace(root: String, ep: String) -> Option<Value> {
    if validate_episode_name(&ep).is_err() {
        return None;
    }
    read_json(
        &Path::new(&root)
            .join("生产数据")
            .join("episodes")
            .join(format!("{ep}.json")),
    )
}

#[tauri::command]
pub fn read_canvas_layout(root: String, ep: String) -> Result<CanvasLayout, String> {
    let path = canvas_layout_read_path(&root, &ep)?;
    if !path.is_file() {
        return Ok(CanvasLayout {
            version: 1,
            episode: ep,
            updated_at_epoch_ms: 0,
            nodes: vec![],
        });
    }
    let txt = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut layout: CanvasLayout = serde_json::from_str(&txt).map_err(|e| e.to_string())?;
    if layout.episode.is_empty() {
        layout.episode = ep;
    }
    Ok(layout)
}

#[tauri::command]
pub fn write_canvas_layout(
    root: String,
    ep: String,
    nodes: Vec<CanvasNodePosition>,
) -> Result<(), String> {
    let path = canvas_layout_path(&root, &ep)?;
    let mut seen = HashSet::new();
    let clean: Vec<CanvasNodePosition> = nodes
        .into_iter()
        .filter(|n| {
            !n.id.trim().is_empty()
                && n.x.is_finite()
                && n.y.is_finite()
                && seen.insert(n.id.clone())
        })
        .take(2_000)
        .collect();
    let layout = CanvasLayout {
        version: 1,
        episode: ep,
        updated_at_epoch_ms: now_epoch_ms(),
        nodes: clean,
    };
    let txt = serde_json::to_string_pretty(&layout).map_err(|e| e.to_string())?;
    fs::write(path, format!("{txt}\n")).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn read_clip_edit(
    root: String,
    ep: String,
    clip_id: String,
    number: Option<i64>,
) -> Result<ClipEditData, String> {
    let root_path = PathBuf::from(&root);
    if let Ok(path) = storyboard_path(&root, &ep) {
        return read_storyboard_clip_edit(&root_path, path, &ep, &clip_id, number);
    }
    if let Ok(path) = panel_script_path(&root, &ep) {
        return read_panel_clip_edit(path, &ep, &clip_id, number);
    }
    Err("找不到 storyboard.json 或 panel_script.json".into())
}

fn read_storyboard_clip_edit(
    root: &Path,
    path: PathBuf,
    ep: &str,
    clip_id: &str,
    number: Option<i64>,
) -> Result<ClipEditData, String> {
    let txt = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let data: Value = serde_json::from_str(&txt).map_err(|e| e.to_string())?;
    let clips = data
        .get("clips")
        .and_then(|v| v.as_array())
        .ok_or("storyboard.json 缺 clips 数组")?;
    let idx = find_clip_index(clips, clip_id, number).ok_or("找不到对应 Clip，未写入")?;
    let clip = clips.get(idx).ok_or("找不到对应 Clip，未写入")?;
    let clip_number = clip.get("number").and_then(|v| v.as_i64()).or(number);
    let clip_identifier = value_string(clip, "id");
    let image_pack_rel = ["出图", ep, "prompt", "01_分镜出图.md"];
    let video_pack_rel = ["出视频", ep, "prompt", "01_clips.md"];
    let image_positive = read_clip_prompt_pack(
        root,
        &image_pack_rel,
        &clip_identifier,
        clip_number,
        &["正向 prompt（中文", "正向 prompt (中文"],
    );
    let image_negative = read_clip_prompt_pack(
        root,
        &image_pack_rel,
        &clip_identifier,
        clip_number,
        &["负向 prompt"],
    );
    let video_prompt = read_clip_prompt_pack(
        root,
        &video_pack_rel,
        &clip_identifier,
        clip_number,
        &["视频 prompt（中文", "视频 prompt (中文"],
    )
    .or_else(|| storyboard_shot_video_prompt(clip));
    Ok(ClipEditData {
        source_rel: format!("脚本/{ep}/storyboard.json"),
        id: clip_identifier,
        number: clip_number,
        label: value_string(clip, "label"),
        duration: clip.get("duration").and_then(|v| v.as_f64()),
        scene: value_string(clip, "scene"),
        rhythm: value_string(clip, "rhythm"),
        template: value_string(clip, "template"),
        prompt: value_string_or(
            clip,
            "prompt",
            clip_prompt(clip).or_else(|| storyboard_shot_text(clip)),
        ),
        image_prompt: value_string_or(clip, "image_prompt", image_positive.clone()),
        video_prompt: value_string_or(clip, "video_prompt", video_prompt),
        positive_prompt: value_string_or(clip, "positive_prompt", image_positive),
        negative_prompt: value_string_or(clip, "negative_prompt", image_negative),
    })
}

fn read_panel_clip_edit(
    path: PathBuf,
    ep: &str,
    clip_id: &str,
    number: Option<i64>,
) -> Result<ClipEditData, String> {
    let txt = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let data: Value = serde_json::from_str(&txt).map_err(|e| e.to_string())?;
    let panels = data
        .get("panels")
        .and_then(|v| v.as_array())
        .ok_or("panel_script.json 缺 panels 数组")?;
    let idx = find_clip_index(panels, clip_id, number).ok_or("找不到对应分格，未写入")?;
    let panel = panels.get(idx).ok_or("找不到对应分格，未写入")?;
    let panel_id = value_string(panel, "panel_id");
    Ok(ClipEditData {
        source_rel: format!("脚本/{ep}/panel_script.json"),
        id: panel_id.clone(),
        number: number_from_id(&panel_id).or(number),
        label: value_string(panel, "story_function"),
        duration: None,
        scene: value_string(panel, "location"),
        rhythm: value_string(panel, "story_function"),
        template: string_array(panel, "characters", 20).join("、"),
        prompt: value_string(panel, "description"),
        image_prompt: value_string(panel, "art_notes"),
        video_prompt: value_string(panel, "narration"),
        positive_prompt: comic_dialogue_lines(panel).join("\n"),
        negative_prompt: string_array(panel, "sfx", 20).join("、"),
    })
}

#[tauri::command]
pub fn write_clip_edit(
    root: String,
    ep: String,
    clip_id: String,
    number: Option<i64>,
    patch: ClipEditPatch,
) -> Result<ClipEditData, String> {
    if let Ok(path) = storyboard_path(&root, &ep) {
        write_storyboard_clip_edit(path, root, ep, clip_id, number, patch)
    } else if let Ok(path) = panel_script_path(&root, &ep) {
        write_panel_clip_edit(path, root, ep, clip_id, number, patch)
    } else {
        Err("找不到 storyboard.json 或 panel_script.json".into())
    }
}

fn write_storyboard_clip_edit(
    path: PathBuf,
    root: String,
    ep: String,
    clip_id: String,
    number: Option<i64>,
    patch: ClipEditPatch,
) -> Result<ClipEditData, String> {
    let txt = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut data: Value = serde_json::from_str(&txt).map_err(|e| e.to_string())?;
    let clips = data
        .get_mut("clips")
        .and_then(|v| v.as_array_mut())
        .ok_or("storyboard.json 缺 clips 数组")?;
    let idx = find_clip_index(clips, &clip_id, number).ok_or("找不到对应 Clip，未写入")?;
    let clip = clips
        .get_mut(idx)
        .and_then(|v| v.as_object_mut())
        .ok_or("Clip 不是对象，未写入")?;

    if patch.label.trim().is_empty() {
        return Err("标题不能为空".into());
    }
    set_string_field(clip, "label", patch.label.trim(), false);
    match patch.duration {
        Some(v) if v.is_finite() && v > 0.0 => {
            let num = serde_json::Number::from_f64(v).ok_or("非法时长")?;
            clip.insert("duration".into(), Value::Number(num));
        }
        _ => {
            clip.remove("duration");
        }
    }
    set_string_field(clip, "scene", patch.scene.trim(), true);
    set_string_field(clip, "rhythm", patch.rhythm.trim(), true);
    set_string_field(clip, "template", patch.template.trim(), true);
    set_string_field(clip, "prompt", patch.prompt.trim(), true);
    set_string_field(clip, "image_prompt", patch.image_prompt.trim(), true);
    set_string_field(clip, "video_prompt", patch.video_prompt.trim(), true);
    set_string_field(clip, "positive_prompt", patch.positive_prompt.trim(), true);
    set_string_field(clip, "negative_prompt", patch.negative_prompt.trim(), true);

    let next = serde_json::to_string_pretty(&data).map_err(|e| e.to_string())?;
    fs::write(&path, format!("{next}\n")).map_err(|e| e.to_string())?;
    read_clip_edit(root, ep, clip_id, number)
}

fn write_panel_clip_edit(
    path: PathBuf,
    root: String,
    ep: String,
    clip_id: String,
    number: Option<i64>,
    patch: ClipEditPatch,
) -> Result<ClipEditData, String> {
    let txt = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut data: Value = serde_json::from_str(&txt).map_err(|e| e.to_string())?;
    let panels = data
        .get_mut("panels")
        .and_then(|v| v.as_array_mut())
        .ok_or("panel_script.json 缺 panels 数组")?;
    let idx = find_clip_index(panels, &clip_id, number).ok_or("找不到对应分格，未写入")?;
    let panel = panels
        .get_mut(idx)
        .and_then(|v| v.as_object_mut())
        .ok_or("分格不是对象，未写入")?;

    let story_function = if patch.label.trim().is_empty() {
        patch.rhythm.trim()
    } else {
        patch.label.trim()
    };
    if story_function.trim().is_empty() {
        return Err("分格功能不能为空".into());
    }
    set_string_field(panel, "story_function", story_function.trim(), false);
    set_string_field(panel, "location", patch.scene.trim(), true);
    set_string_array_field(panel, "characters", patch.template.trim());
    set_string_field(panel, "description", patch.prompt.trim(), true);
    set_string_field(panel, "art_notes", patch.image_prompt.trim(), true);
    set_string_field(panel, "narration", patch.video_prompt.trim(), true);
    set_dialogue_field(panel, patch.positive_prompt.trim());
    set_string_array_field(panel, "sfx", patch.negative_prompt.trim());

    let next = serde_json::to_string_pretty(&data).map_err(|e| e.to_string())?;
    fs::write(&path, format!("{next}\n")).map_err(|e| e.to_string())?;
    read_clip_edit(root, ep, clip_id, number)
}

// ---- run.py next --json bridge ----

// Async so the python shell-out runs off the main thread (no UI freeze), with a
// hard timeout so a hung run.py can't wedge the call.
#[tauri::command]
pub async fn read_next_action(
    repo_root: String,
    root: String,
    ep: String,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || run_next_blocking(&repo_root, &root, &ep))
        .await
        .map_err(|e| e.to_string())?
}

fn run_next_blocking(repo_root: &str, root: &str, ep: &str) -> Result<String, String> {
    let script = Path::new(repo_root).join("skills/n2d/run.py");
    let mut child = Command::new("python3")
        .arg(script)
        .arg("next")
        .arg(root)
        .arg(ep)
        .arg("--json")
        .arg("--preview")
        .current_dir(repo_root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| e.to_string())?;

    // Drain pipes on threads so a chatty child can't dead-lock on a full buffer.
    let mut out_pipe = child.stdout.take().ok_or("no stdout pipe")?;
    let mut err_pipe = child.stderr.take().ok_or("no stderr pipe")?;
    let oh = thread::spawn(move || {
        let mut b = Vec::new();
        let _ = out_pipe.read_to_end(&mut b);
        b
    });
    let eh = thread::spawn(move || {
        let mut b = Vec::new();
        let _ = err_pipe.read_to_end(&mut b);
        b
    });

    let deadline = Instant::now() + Duration::from_secs(30);
    loop {
        match child.try_wait().map_err(|e| e.to_string())? {
            Some(_) => break,
            None => {
                if Instant::now() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err("run.py 超时（>30s）".into());
                }
                thread::sleep(Duration::from_millis(50));
            }
        }
    }

    let stdout = oh.join().unwrap_or_default();
    let stderr = eh.join().unwrap_or_default();
    if !stdout.is_empty() {
        Ok(String::from_utf8_lossy(&stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&stderr).to_string())
    }
}
