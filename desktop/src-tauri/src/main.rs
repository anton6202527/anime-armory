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
            commands::list_skills,
            commands::skill_tree,
            commands::read_skill_file,
            commands::work_dir,
            commands::work_tree,
            commands::work_snapshot,
            commands::work_is_empty,
            commands::work_change_summary,
            commands::work_changes,
            commands::read_work_change,
            commands::archive_work_changes,
            commands::archive_work_change,
            commands::work_deleted,
            commands::read_work_file,
            commands::write_work_file,
            commands::create_work_entry,
            commands::import_work_sources,
            commands::import_n2d_novel_sources,
            commands::rename_work_entry,
            commands::delete_work_entry,
            commands::reveal_work_entry,
            commands::open_work_entry,
            commands::open_source_repo,
            commands::detect_agents,
            commands::default_workspace,
            commands::resolve_repo,
            commands::seed_demos,
            commands::create_work,
            commands::delete_work,
            commands::read_canvas,
            commands::read_episode_workspace,
            commands::read_canvas_layout,
            commands::write_canvas_layout,
            commands::read_clip_edit,
            commands::write_clip_edit,
            commands::read_next_action,
            watch::watch_root,
            watch::unwatch_root,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
