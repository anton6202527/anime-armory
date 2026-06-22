// Bridge commands: scan the workspace, read the canvas (review_ui or
// storyboard fallback), and shell out to the repo's `--json` tools.
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use serde::Serialize;
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
    if depth > 4 {
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
        if matches!(
            name.as_str(),
            "__pycache__" | ".DS_Store" | "node_modules" | "_voicecache" | ".git"
        ) {
            continue;
        }
        let is_dir = e.path().is_dir();
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
        });
        if is_dir {
            walk_tree(&e.path(), &rel, depth + 1, out);
        }
    }
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
    let probe = r#"for c in claude codex gemini gemini-cli; do p=$(command -v "$c" 2>/dev/null) && printf '%s\t%s\n' "$c" "$p"; done"#;
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
            &["-lc", "codex features list 2>/dev/null; codex plugin list 2>/dev/null"],
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

    // gemini launch command: prefer `gemini`, fall back to `gemini-cli`
    let gemini_found = found.contains_key("gemini") || found.contains_key("gemini-cli");
    let gemini_cmd = if found.contains_key("gemini") {
        "gemini"
    } else {
        "gemini-cli"
    };
    let gemini_path = found
        .get("gemini")
        .or_else(|| found.get("gemini-cli"))
        .cloned()
        .unwrap_or_default();

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
            id: "gemini".into(),
            name: "Gemini CLI".into(),
            command: gemini_cmd.into(),
            found: gemini_found,
            path: gemini_path,
            image: "yes".into(),
            note: "原生生图（Imagen / Nano Banana）".into(),
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

/// Resolve (and create) the app's dedicated works workspace `<home>/AnimeArsenal/`.
/// This is kept SEPARATE from the skills repo so app works never touch the
/// repo's demo product dirs (创作区/制漫剧/ etc.). Cross-platform (HOME / USERPROFILE).
#[tauri::command]
pub fn default_workspace() -> Result<String, String> {
    let home = dirs::home_dir().ok_or("无法定位用户主目录")?;
    let ws = home.join("AnimeArsenal");
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

/// Seed the `/tod --demos` sample works into the app's works workspace, ONCE.
/// For each bundled `resources/demos/创作区/<产品目录>/<作品>`, if the same path is
/// missing under `workspace_root`, copy it in. A `.demos_seeded` sentinel in the
/// workspace makes this idempotent and means user-deleted demos stay deleted.
/// Returns the number of works seeded (0 if nothing bundled / already seeded).
#[tauri::command]
pub fn seed_demos(app: tauri::AppHandle, workspace_root: String) -> Result<usize, String> {
    let ws = Path::new(&workspace_root);
    let sentinel = ws.join(".demos_seeded");
    if sentinel.exists() {
        return Ok(0);
    }
    let res = match app.path().resource_dir() {
        Ok(r) => r,
        Err(e) => return Err(e.to_string()),
    };
    let demos = res.join("resources").join("demos").join(CREATION_ROOT);
    if !demos.is_dir() {
        return Ok(0); // app was built without --demos
    }
    let mut seeded = 0usize;
    // demos/创作区/<产品目录>/<作品>/
    for line in fs::read_dir(&demos).map_err(|e| e.to_string())?.flatten() {
        let line_dir = line.path();
        if !line_dir.is_dir() {
            continue;
        }
        let product = line.file_name();
        for work in fs::read_dir(&line_dir).map_err(|e| e.to_string())?.flatten() {
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
    let _ = fs::write(&sentinel, b"1");
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
        return Err("拒绝删除：该路径位于项目仓库内，已被隔离保护（仓库 demo 不是 app 作品）".into());
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
    let clips = data.get("clips").and_then(|c| c.as_array()).unwrap_or(&empty);
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
                number: c.get("number").and_then(|n| n.as_i64()).or(Some((i + 1) as i64)),
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
    let raw = data.get("clips").and_then(|c| c.as_array()).unwrap_or(&empty);
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
    let clips = data.get("clips").and_then(|c| c.as_array()).unwrap_or(&empty);
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
            out.title = v.get("storyboard").and_then(|s| s.get("title")).and_then(|t| t.as_str()).map(|t| t.to_string());
            out.total_duration = v.get("storyboard").and_then(|s| s.get("total_duration")).and_then(|d| d.as_f64());
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
pub async fn read_next_action(repo_root: String, root: String, ep: String) -> Result<String, String> {
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
