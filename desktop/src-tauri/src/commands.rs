// Bridge commands: scan the workspace, read the canvas (review_ui or
// storyboard fallback), and shell out to the repo's `--json` tools.
use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::hash::{Hash, Hasher};
use std::io::Read;
use std::path::{Component, Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tauri::Manager;

// ---- workspace scan ----

#[derive(Serialize)]
pub struct WorkRoot {
    name: String,
    path: String,
    has_progress: bool,
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
const BASELINE_FILE_LIMIT: usize = 50_000;
const CHANGE_SUMMARY_FILE_LIMIT: usize = 30_000;
const HASH_COMPARE_LIMIT: u64 = 1024 * 1024;
const TEXT_SNAPSHOT_LIMIT: u64 = 2 * 1024 * 1024;
const TEXT_EDIT_LIMIT: u64 = 20 * 1024 * 1024;

const LINES: &[(&str, &str, &str, &str)] = &[
    // (key, label, product dir, view)
    ("n2d", "制漫剧 (n2d)", "制漫剧", "canvas"),
    ("ad", "拍广告 (ad)", "拍广告", "canvas"),
    ("mv", "制MV (mv)", "制MV", "canvas"),
    ("song", "写歌 (song)", "写歌", "audio"),
    ("novel", "写小说 (novel)", "写小说", "files"),
];

#[tauri::command]
pub fn scan_workspace(repo_root: String) -> Vec<LineInfo> {
    LINES
        .iter()
        .map(|(key, label, dir, view)| {
            let abs = Path::new(&repo_root).join(CREATION_ROOT).join(dir);
            let mut roots = Vec::new();
            if let Ok(entries) = fs::read_dir(&abs) {
                for e in entries.flatten() {
                    let p = e.path();
                    if p.is_dir() {
                        let name = e.file_name().to_string_lossy().to_string();
                        if name.starts_with('.') || name.starts_with('_') {
                            continue;
                        }
                        let has_progress = p.join("_进度.md").exists();
                        roots.push(WorkRoot {
                            name,
                            path: p.to_string_lossy().to_string(),
                            has_progress,
                        });
                    }
                }
            }
            roots.sort_by(|a, b| a.name.cmp(&b.name));
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
    let mut entries: Vec<_> = match fs::read_dir(dir) {
        Ok(rd) => rd.flatten().collect(),
        Err(_) => return false,
    };
    entries.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    for e in entries {
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
fn baseline_path(root: &str) -> Option<PathBuf> {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    root.hash(&mut hasher);
    let h = hasher.finish();
    Some(
        dirs::config_dir()?
            .join("anime-arsenal")
            .join("baselines")
            .join(format!("{h:016x}.json")),
    )
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
    if bytes.contains(&0) {
        return Err("二进制文件，不预览".into());
    }
    Ok(String::from_utf8_lossy(&bytes).into_owned())
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
    let url = "https://github.com/anton6202527/anime-armory";

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
/// npm globals, ~/.local/bin). Codex's image capability is refined with a cheap,
/// bounded `codex features list` probe — mirroring skills/n2d-image cli_registry.
#[tauri::command]
pub fn detect_agents() -> Vec<AgentInfo> {
    let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".to_string());

    // resolve every candidate command in ONE login-shell call (PATH parity)
    let probe = r#"for c in claude codex opencode; do p=$(command -v "$c" 2>/dev/null) && printf '%s\t%s\n' "$c" "$p"; done"#;
    let mut found: std::collections::HashMap<String, String> = std::collections::HashMap::new();
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

/// Resolve which directory the app uses as its **skills repo** (drives the skill
/// roster + `run.py`). Priority:
///   1. the live `dev_repo` checkout if it actually has a `skills/` dir — so on a
///      dev machine skill edits are always picked up (the bundle is ignored);
///   2. else the `/tod`-bundled copy shipped inside the app
///      (`<resourceDir>/resources`, written by sync-skills.js) — the
///      self-contained path for an installed app with no source checkout.
/// Falls back to `dev_repo` as a last resort so the frontend always has a value.
#[tauri::command]
pub fn resolve_repo(app: tauri::AppHandle, dev_repo: String) -> String {
    if Path::new(&dev_repo).join("skills").is_dir() {
        return dev_repo;
    }
    if let Ok(res) = app.path().resource_dir() {
        let bundled = res.join("resources");
        if bundled.join("skills").is_dir() {
            return bundled.to_string_lossy().to_string();
        }
    }
    dev_repo
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

/// Seed each line's most-complete work (the bundled samples) into the app's works
/// workspace so a fresh app is never empty. For each bundled
/// `resources/demos/创作区/<产品目录>/<作品>`, if the same path is MISSING under
/// `workspace_root`, copy it in (existing user work is never clobbered). Runs on
/// every launch and re-adds any champion the user is missing — these samples are
/// a default, not a one-shot seed. Returns the number of works (re)seeded.
#[tauri::command]
pub fn seed_demos(app: tauri::AppHandle, workspace_root: String) -> Result<usize, String> {
    let ws = Path::new(&workspace_root);
    let res = match app.path().resource_dir() {
        Ok(r) => r,
        Err(e) => return Err(e.to_string()),
    };
    let demos = res.join("resources").join("demos").join(CREATION_ROOT);
    if !demos.is_dir() {
        return Ok(0); // app was built with --no-demos
    }
    let mut seeded = 0usize;
    // demos/创作区/<产品目录>/<作品>/
    for line in fs::read_dir(&demos).map_err(|e| e.to_string())?.flatten() {
        let line_dir = line.path();
        if !line_dir.is_dir() {
            continue;
        }
        let product = line.file_name();
        for work in fs::read_dir(&line_dir)
            .map_err(|e| e.to_string())?
            .flatten()
        {
            let from = work.path();
            if !from.is_dir() {
                continue;
            }
            let dst = ws.join(CREATION_ROOT).join(&product).join(work.file_name());
            if dst.exists() {
                continue; // never clobber existing user work
            }
            copy_dir_all(&from, &dst).map_err(|e| e.to_string())?;
            seeded += 1;
        }
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
    qa: Vec<QaFlag>,
}

#[derive(Serialize, Default)]
pub struct CanvasSeam {
    from: String,
    to: String,
    transition: Option<String>,
}

#[derive(Serialize, Default)]
pub struct CanvasData {
    source: String, // review_ui | storyboard | none
    episode: String,
    title: Option<String>,
    total_duration: Option<f64>,
    episodes: Vec<String>,
    clips: Vec<CanvasClip>,
    seams: Vec<CanvasSeam>,
}

fn ep_num(name: &str) -> i64 {
    // "第12集" / "第7a集" -> 12 / 7 ; fallback large.
    let digits: String = name.chars().filter(|c| c.is_ascii_digit()).collect();
    digits.parse().unwrap_or(1_000_000)
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

fn s(v: &Value, k: &str) -> Option<String> {
    v.get(k).and_then(|x| x.as_str()).map(|x| x.to_string())
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
            let ff_rel = s(c, "firstframe_png");
            let (ff_abs, ff_exists) = match &ff_rel {
                Some(r) => {
                    let abs = root.join(r);
                    (Some(abs.to_string_lossy().to_string()), abs.exists())
                }
                None => (None, false),
            };
            let vid_rel = s(c, "video_out");
            let (vid_abs, vid_exists) = match &vid_rel {
                Some(r) => {
                    let abs = root.join(r);
                    (Some(abs.to_string_lossy().to_string()), abs.exists())
                }
                None => (None, false),
            };
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
                qa: vec![],
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

fn from_review_ui(root: &Path, data: &Value) -> (Vec<CanvasClip>, Vec<CanvasSeam>) {
    let empty = vec![];
    let clips = data
        .get("clips")
        .and_then(|c| c.as_array())
        .unwrap_or(&empty);
    let out_clips: Vec<CanvasClip> = clips
        .iter()
        .map(|c| {
            let ff = c.get("first_frame").cloned().unwrap_or(Value::Null);
            let ff_path = s(&ff, "path");
            let ff_abs = ff_path.as_ref().map(|p| {
                let pb = PathBuf::from(p);
                if pb.is_absolute() { pb } else { root.join(p) }
                    .to_string_lossy()
                    .to_string()
            });
            let qa = c
                .get("qa_flags")
                .and_then(|q| q.as_array())
                .map(|arr| {
                    arr.iter()
                        .map(|f| QaFlag {
                            severity: s(f, "severity").unwrap_or_else(|| "info".into()),
                            status: s(f, "status"),
                            dimension: s(f, "dimension"),
                            message: s(f, "message"),
                        })
                        .collect()
                })
                .unwrap_or_default();
            CanvasClip {
                id: s(c, "id").unwrap_or_default(),
                number: c.get("number").and_then(|n| n.as_i64()),
                label: s(c, "label").unwrap_or_default(),
                duration: c.get("duration").and_then(|d| d.as_f64()),
                scene: s(c, "scene"),
                rhythm: s(c, "rhythm"),
                template: s(c, "template"),
                first_frame_exists: ff.get("exists").and_then(|e| e.as_bool()).unwrap_or(false),
                first_frame_abs: ff_abs,
                video_abs: None,
                video_exists: false,
                qa,
            }
        })
        .collect();
    let seams = data
        .get("seams")
        .and_then(|x| x.as_array())
        .map(|arr| {
            arr.iter()
                .map(|sm| CanvasSeam {
                    from: s(sm, "from").unwrap_or_default(),
                    to: s(sm, "to").unwrap_or_default(),
                    transition: s(sm, "transition"),
                })
                .collect()
        })
        .unwrap_or_default();
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
            return out;
        }
    }

    out
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
