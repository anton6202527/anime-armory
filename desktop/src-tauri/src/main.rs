// Prevents an extra console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod media;
mod pty;
mod watch;

use std::sync::Mutex;

use tauri::{
    menu::{AboutMetadata, CheckMenuItem, Menu, MenuItem, PredefinedMenuItem, Submenu},
    Emitter, Manager, Wry,
};

const MENU_SET_LANGUAGE_ZH: &str = "anime-armory:set-language-zh";
const MENU_SET_LANGUAGE_EN: &str = "anime-armory:set-language-en";
const MENU_DOWNLOAD_LATEST: &str = "anime-armory:download-latest";
const MENU_TOGGLE_TERMINAL: &str = "anime-armory:toggle-terminal";
const EVENT_SET_LANGUAGE: &str = "anime-armory:set-language";
const EVENT_TOGGLE_TERMINAL: &str = "anime-armory:toggle-terminal";

#[cfg(target_os = "macos")]
struct AppMenuLabels {
    language: &'static str,
    download_latest: &'static str,
    show_terminal: &'static str,
    hide_terminal: &'static str,
}

#[cfg(target_os = "macos")]
fn app_menu_labels(language: &str) -> AppMenuLabels {
    if language == "en" {
        AppMenuLabels {
            language: "Language",
            download_latest: "Download Latest App",
            show_terminal: "Show Terminal",
            hide_terminal: "Hide Terminal",
        }
    } else {
        AppMenuLabels {
            language: "语言",
            download_latest: "下载最新App",
            show_terminal: "显示Terminal",
            hide_terminal: "隐藏Terminal",
        }
    }
}

#[cfg(target_os = "macos")]
fn build_app_menu(
    app_handle: &tauri::AppHandle,
    language: &str,
    terminal_visible: bool,
) -> tauri::Result<Menu<Wry>> {
    let pkg_info = app_handle.package_info();
    let config = app_handle.config();
    let labels = app_menu_labels(language);
    let about_metadata = AboutMetadata {
        name: Some(pkg_info.name.clone()),
        version: Some(pkg_info.version.to_string()),
        copyright: config.bundle.copyright.clone(),
        authors: config.bundle.publisher.clone().map(|p| vec![p]),
        ..Default::default()
    };

    let language_menu = Submenu::with_items(
        app_handle,
        labels.language,
        true,
        &[
            &CheckMenuItem::with_id(
                app_handle,
                MENU_SET_LANGUAGE_ZH,
                "中文",
                true,
                language != "en",
                None::<&str>,
            )?,
            &CheckMenuItem::with_id(
                app_handle,
                MENU_SET_LANGUAGE_EN,
                "English",
                true,
                language == "en",
                None::<&str>,
            )?,
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
                        labels.download_latest,
                        true,
                        None::<&str>,
                    )?,
                    &MenuItem::with_id(
                        app_handle,
                        MENU_TOGGLE_TERMINAL,
                        if terminal_visible {
                            labels.hide_terminal
                        } else {
                            labels.show_terminal
                        },
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

#[cfg(target_os = "macos")]
fn build_default_app_menu(app_handle: &tauri::AppHandle) -> tauri::Result<Menu<Wry>> {
    build_app_menu(app_handle, "zh", true)
}

#[cfg(target_os = "macos")]
fn set_app_menu(
    app: &tauri::AppHandle,
    language: &str,
    terminal_visible: bool,
) -> Result<(), String> {
    let menu = build_app_menu(app, language, terminal_visible).map_err(|e| e.to_string())?;
    app.set_menu(menu).map(|_| ()).map_err(|e| e.to_string())
}

#[cfg(not(target_os = "macos"))]
fn set_app_menu(
    _app: &tauri::AppHandle,
    _language: &str,
    _terminal_visible: bool,
) -> Result<(), String> {
    Ok(())
}

#[derive(Debug)]
struct AppUiState {
    language: Mutex<String>,
    terminal_visible: Mutex<bool>,
}

impl Default for AppUiState {
    fn default() -> Self {
        Self {
            language: Mutex::new("zh".to_string()),
            terminal_visible: Mutex::new(true),
        }
    }
}

fn update_app_language(app: &tauri::AppHandle, language: String) -> Result<(), String> {
    let state = app.state::<AppUiState>();
    let terminal_visible = *state
        .terminal_visible
        .lock()
        .map_err(|_| "terminal state lock poisoned".to_string())?;
    *state
        .language
        .lock()
        .map_err(|_| "language state lock poisoned".to_string())? = language.clone();
    set_app_menu(app, &language, terminal_visible)
}

fn update_app_terminal_visible(app: &tauri::AppHandle, visible: bool) -> Result<(), String> {
    let state = app.state::<AppUiState>();
    let language = state
        .language
        .lock()
        .map_err(|_| "language state lock poisoned".to_string())?
        .clone();
    *state
        .terminal_visible
        .lock()
        .map_err(|_| "terminal state lock poisoned".to_string())? = visible;
    set_app_menu(app, &language, visible)
}

fn toggle_app_terminal_visible(app: &tauri::AppHandle) -> Result<bool, String> {
    let state = app.state::<AppUiState>();
    let language = state
        .language
        .lock()
        .map_err(|_| "language state lock poisoned".to_string())?
        .clone();
    let next_visible = {
        let mut terminal_visible = state
            .terminal_visible
            .lock()
            .map_err(|_| "terminal state lock poisoned".to_string())?;
        *terminal_visible = !*terminal_visible;
        *terminal_visible
    };
    set_app_menu(app, &language, next_visible)?;
    Ok(next_visible)
}

#[tauri::command]
fn set_app_language(app: tauri::AppHandle, language: String) -> Result<(), String> {
    update_app_language(&app, language)
}

#[tauri::command]
fn set_app_terminal_visible(app: tauri::AppHandle, visible: bool) -> Result<(), String> {
    update_app_terminal_visible(&app, visible)
}

#[cfg(not(target_os = "macos"))]
fn build_default_app_menu(app_handle: &tauri::AppHandle) -> tauri::Result<Menu<Wry>> {
    Menu::default(app_handle)
}

fn main() {
    tauri::Builder::default()
        .menu(build_default_app_menu)
        .on_menu_event(|app, event| {
            if event.id() == MENU_SET_LANGUAGE_ZH {
                let _ = update_app_language(app, "zh".to_string());
                let _ = app.emit(EVENT_SET_LANGUAGE, "zh");
            } else if event.id() == MENU_SET_LANGUAGE_EN {
                let _ = update_app_language(app, "en".to_string());
                let _ = app.emit(EVENT_SET_LANGUAGE, "en");
            } else if event.id() == MENU_DOWNLOAD_LATEST {
                let _ = commands::open_source_repo();
            } else if event.id() == MENU_TOGGLE_TERMINAL {
                if let Ok(visible) = toggle_app_terminal_visible(app) {
                    let _ = app.emit(EVENT_TOGGLE_TERMINAL, visible);
                }
            }
        })
        .plugin(tauri_plugin_dialog::init())
        .manage(AppUiState::default())
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
            commands::search_work_files,
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
            commands::list_demo_downloads,
            commands::install_demo,
            commands::create_work,
            commands::delete_work,
            commands::read_canvas,
            commands::read_episode_workspace,
            commands::read_quality_insights,
            commands::read_canvas_layout,
            commands::write_canvas_layout,
            commands::read_clip_edit,
            commands::write_clip_edit,
            commands::read_next_action,
            set_app_language,
            set_app_terminal_visible,
            watch::watch_root,
            watch::unwatch_root,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
