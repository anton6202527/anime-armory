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
            let abs = Path::new(&repo_root).join(dir);
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
