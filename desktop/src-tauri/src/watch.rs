// Filesystem watcher: watch a work root recursively and emit a `fs-changed`
// event whenever skills write outputs (出图/出视频/脚本/_进度.md/生产数据).
// The frontend debounces and re-pulls the canvas + next-action.
use std::collections::HashMap;
use std::path::Path;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use notify::{event::ModifyKind, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use serde::Serialize;
use tauri::{AppHandle, Emitter, State};

#[derive(Default)]
pub struct WatchState {
    // keyed by root path; keeps the watcher alive while watched
    watchers: Mutex<HashMap<String, RecommendedWatcher>>,
}

#[derive(Clone, Serialize)]
struct FsChanged {
    root: String,
}

#[tauri::command]
pub fn watch_root(app: AppHandle, state: State<WatchState>, root: String) -> Result<(), String> {
    let mut map = state.watchers.lock().unwrap();
    if map.contains_key(&root) {
        return Ok(()); // already watching
    }

    let app2 = app.clone();
    let root_for_event = root.clone();
    let last_emit: Arc<Mutex<Option<Instant>>> = Arc::new(Mutex::new(None));
    let last_emit_for_cb = last_emit.clone();
    let mut watcher = notify::recommended_watcher(move |res: notify::Result<notify::Event>| {
        if let Ok(ev) = res {
            // Ignore pure access/metadata noise; only react to content changes.
            if matches!(
                ev.kind,
                EventKind::Access(_) | EventKind::Modify(ModifyKind::Metadata(_))
            ) {
                return;
            }
            {
                let mut last = last_emit_for_cb.lock().unwrap();
                if last
                    .map(|instant| instant.elapsed() < Duration::from_millis(300))
                    .unwrap_or(false)
                {
                    return;
                }
                *last = Some(Instant::now());
            }
            let _ = app2.emit(
                "fs-changed",
                FsChanged {
                    root: root_for_event.clone(),
                },
            );
        }
    })
    .map_err(|e| e.to_string())?;

    watch_path(&mut watcher, Path::new(&root), RecursiveMode::NonRecursive)?;
    for (rel, mode) in [
        ("脚本", RecursiveMode::Recursive),
        ("设定库", RecursiveMode::Recursive),
        ("生产数据", RecursiveMode::NonRecursive),
        ("生产数据/episodes", RecursiveMode::NonRecursive),
        ("生产数据/visuals", RecursiveMode::NonRecursive),
        ("出图", RecursiveMode::NonRecursive),
        ("出视频", RecursiveMode::NonRecursive),
        ("配音", RecursiveMode::NonRecursive),
    ] {
        let path = Path::new(&root).join(rel);
        if path.exists() {
            let _ = watch_path(&mut watcher, &path, mode);
        }
    }

    map.insert(root, watcher);
    Ok(())
}

fn watch_path(watcher: &mut RecommendedWatcher, path: &Path, mode: RecursiveMode) -> Result<(), String> {
    watcher.watch(path, mode).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn unwatch_root(state: State<WatchState>, root: String) -> Result<(), String> {
    state.watchers.lock().unwrap().remove(&root);
    Ok(())
}
