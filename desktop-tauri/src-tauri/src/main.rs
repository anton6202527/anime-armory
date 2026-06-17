// Prevents an extra console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod media;
mod pty;
mod watch;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(pty::PtyManager::default())
        .manage(media::MediaState::default())
        .manage(watch::WatchState::default())
        .invoke_handler(tauri::generate_handler![
            pty::pty_spawn,
            pty::pty_write,
            pty::pty_resize,
            pty::pty_kill,
            media::start_media,
            media::media_allow_root,
            commands::scan_workspace,
            commands::read_canvas,
            commands::read_next_action,
            watch::watch_root,
            watch::unwatch_root,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
