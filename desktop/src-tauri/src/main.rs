// Prevents an extra console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod media;
mod pty;
mod watch;

use tauri::{
    menu::{AboutMetadata, Menu, MenuItem, PredefinedMenuItem, Submenu},
    Emitter, Wry,
};

const MENU_SET_LANGUAGE_ZH: &str = "anime-armory:set-language-zh";
const MENU_SET_LANGUAGE_EN: &str = "anime-armory:set-language-en";
const MENU_DOWNLOAD_LATEST: &str = "anime-armory:download-latest";
const EVENT_SET_LANGUAGE: &str = "anime-armory:set-language";

#[cfg(target_os = "macos")]
fn build_app_menu(app_handle: &tauri::AppHandle) -> tauri::Result<Menu<Wry>> {
    let pkg_info = app_handle.package_info();
    let config = app_handle.config();
    let about_metadata = AboutMetadata {
        name: Some(pkg_info.name.clone()),
        version: Some(pkg_info.version.to_string()),
        copyright: config.bundle.copyright.clone(),
        authors: config.bundle.publisher.clone().map(|p| vec![p]),
        ..Default::default()
    };

    let language_menu = Submenu::with_items(
        app_handle,
        "语言 / Language",
        true,
        &[
            &MenuItem::with_id(app_handle, MENU_SET_LANGUAGE_ZH, "中文", true, None::<&str>)?,
            &MenuItem::with_id(app_handle, MENU_SET_LANGUAGE_EN, "English", true, None::<&str>)?,
        ],
    )?;
    let window_menu = Submenu::with_id_and_items(
        app_handle,
        "Window",
        "Window",
        true,
        &[
            &PredefinedMenuItem::minimize(app_handle, None)?,
            &PredefinedMenuItem::maximize(app_handle, None)?,
            &PredefinedMenuItem::separator(app_handle)?,
            &PredefinedMenuItem::close_window(app_handle, None)?,
        ],
    )?;
    let help_menu = Submenu::with_id_and_items(app_handle, "Help", "Help", true, &[])?;

    Menu::with_items(
        app_handle,
        &[
            &Submenu::with_items(
                app_handle,
                pkg_info.name.clone(),
                true,
                &[
                    &PredefinedMenuItem::about(app_handle, None, Some(about_metadata))?,
                    &PredefinedMenuItem::separator(app_handle)?,
                    &language_menu,
                    &MenuItem::with_id(
                        app_handle,
                        MENU_DOWNLOAD_LATEST,
                        "下载最新 app / Download Latest App",
                        true,
                        None::<&str>,
                    )?,
                    &PredefinedMenuItem::separator(app_handle)?,
                    &PredefinedMenuItem::services(app_handle, None)?,
                    &PredefinedMenuItem::separator(app_handle)?,
                    &PredefinedMenuItem::hide(app_handle, None)?,
                    &PredefinedMenuItem::hide_others(app_handle, None)?,
                    &PredefinedMenuItem::separator(app_handle)?,
                    &PredefinedMenuItem::quit(app_handle, None)?,
                ],
            )?,
            &Submenu::with_items(
                app_handle,
                "File",
                true,
                &[&PredefinedMenuItem::close_window(app_handle, None)?],
            )?,
            &Submenu::with_items(
                app_handle,
                "Edit",
                true,
                &[
                    &PredefinedMenuItem::undo(app_handle, None)?,
                    &PredefinedMenuItem::redo(app_handle, None)?,
                    &PredefinedMenuItem::separator(app_handle)?,
                    &PredefinedMenuItem::cut(app_handle, None)?,
                    &PredefinedMenuItem::copy(app_handle, None)?,
                    &PredefinedMenuItem::paste(app_handle, None)?,
                    &PredefinedMenuItem::select_all(app_handle, None)?,
                ],
            )?,
            &Submenu::with_items(
                app_handle,
                "View",
                true,
                &[&PredefinedMenuItem::fullscreen(app_handle, None)?],
            )?,
            &window_menu,
            &help_menu,
        ],
    )
}

#[cfg(not(target_os = "macos"))]
fn build_app_menu(app_handle: &tauri::AppHandle) -> tauri::Result<Menu<Wry>> {
    Menu::default(app_handle)
}

fn main() {
    tauri::Builder::default()
        .menu(build_app_menu)
        .on_menu_event(|app, event| {
            if event.id() == MENU_SET_LANGUAGE_ZH {
                let _ = app.emit(EVENT_SET_LANGUAGE, "zh");
            } else if event.id() == MENU_SET_LANGUAGE_EN {
                let _ = app.emit(EVENT_SET_LANGUAGE, "en");
            } else if event.id() == MENU_DOWNLOAD_LATEST {
                let _ = commands::open_source_repo();
            }
        })
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
            commands::open_external_url,
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
