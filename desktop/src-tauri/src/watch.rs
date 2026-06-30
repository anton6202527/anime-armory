// Filesystem watcher: watch a work root recursively and emit a `fs-changed`
// event whenever skills write outputs (出图/出视频/脚本/_进度.md/生产数据).
// The frontend debounces and re-pulls the canvas + next-action.
use std::collections::HashMap;
use std::path::Path;
use std::sync::Mutex;

use notify::{EventKind, RecommendedWatcher, RecursiveMode, Watcher};
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
    let mut watcher = notify::recommended_watcher(move |res: notify::Result<notify::Event>| {
        if let Ok(ev) = res {
            // Ignore pure access/metadata noise; only react to content changes.
            if matches!(ev.kind, EventKind::Access(_)) {
                return;
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

    watcher
        .watch(Path::new(&root), RecursiveMode::Recursive)
        .map_err(|e| e.to_string())?;

    map.insert(root, watcher);
    Ok(())
}

#[tauri::command]
pub fn unwatch_root(state: State<WatchState>, root: String) -> Result<(), String> {
    state.watchers.lock().unwrap().remove(&root);
    Ok(())
}
