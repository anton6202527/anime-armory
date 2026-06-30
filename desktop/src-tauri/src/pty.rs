// Native terminal: real PTY sessions via portable-pty, streamed to the
// frontend (xterm.js) over Tauri events. base64-encoded so non-UTF8 bytes
// survive the IPC boundary.
use std::collections::HashMap;
use std::io::{Read, Write};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::thread;

use base64::Engine;
use portable_pty::{native_pty_system, CommandBuilder, MasterPty, PtySize};
use serde::Serialize;
use tauri::{AppHandle, Emitter, State};

struct PtySession {
    master: Box<dyn MasterPty + Send>,
    writer: Box<dyn Write + Send>,
    child: Box<dyn portable_pty::Child + Send + Sync>,
}

#[derive(Default)]
pub struct PtyManager {
    sessions: Mutex<HashMap<u64, PtySession>>,
    counter: AtomicU64,
}

#[derive(Clone, Serialize)]
struct PtyData {
    id: u64,
    data: String, // base64 of raw bytes
}

#[derive(Clone, Serialize)]
struct PtyExit {
    id: u64,
}

impl PtyManager {
    fn spawn(&self, app: AppHandle, cwd: String, rows: u16, cols: u16) -> Result<u64, String> {
        let pty_system = native_pty_system();
        let pair = pty_system
            .openpty(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| e.to_string())?;

        let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".to_string());
        let mut cmd = CommandBuilder::new(shell);
        cmd.arg("-l"); // login shell so PATH (python3, claude, conda) is set up
        cmd.cwd(&cwd);
        cmd.env("TERM", "xterm-256color");

        let child = pair.slave.spawn_command(cmd).map_err(|e| e.to_string())?;
        drop(pair.slave);

        let mut reader = pair.master.try_clone_reader().map_err(|e| e.to_string())?;
        let writer = pair.master.take_writer().map_err(|e| e.to_string())?;

        let id = self.counter.fetch_add(1, Ordering::SeqCst) + 1;

        // Reader thread: pump PTY output → frontend.
        let app2 = app.clone();
        thread::spawn(move || {
            let mut buf = [0u8; 8192];
            loop {
                match reader.read(&mut buf) {
                    Ok(0) => break,
                    Ok(n) => {
                        let data = base64::engine::general_purpose::STANDARD.encode(&buf[..n]);
                        if app2.emit("pty-data", PtyData { id, data }).is_err() {
                            break;
                        }
                    }
                    Err(_) => break,
                }
            }
            let _ = app2.emit("pty-exit", PtyExit { id });
        });

        self.sessions.lock().unwrap().insert(
            id,
            PtySession {
                master: pair.master,
                writer,
                child,
            },
        );
        Ok(id)
    }

    fn write(&self, id: u64, bytes: &[u8]) -> Result<(), String> {
        let mut map = self.sessions.lock().unwrap();
        let s = map.get_mut(&id).ok_or("no such pty session")?;
        s.writer.write_all(bytes).map_err(|e| e.to_string())?;
        s.writer.flush().map_err(|e| e.to_string())
    }

    fn resize(&self, id: u64, rows: u16, cols: u16) -> Result<(), String> {
        let map = self.sessions.lock().unwrap();
        let s = map.get(&id).ok_or("no such pty session")?;
        s.master
            .resize(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| e.to_string())
    }

    fn kill(&self, id: u64) {
        if let Some(mut s) = self.sessions.lock().unwrap().remove(&id) {
            let _ = s.child.kill();
        }
    }
}

#[tauri::command]
pub fn pty_spawn(
    app: AppHandle,
    state: State<PtyManager>,
    cwd: String,
    rows: u16,
    cols: u16,
) -> Result<u64, String> {
    state.spawn(app, cwd, rows.max(1), cols.max(1))
}

#[tauri::command]
pub fn pty_write(state: State<PtyManager>, id: u64, data: String) -> Result<(), String> {
    state.write(id, data.as_bytes())
}

#[tauri::command]
pub fn pty_resize(state: State<PtyManager>, id: u64, rows: u16, cols: u16) -> Result<(), String> {
    state.resize(id, rows.max(1), cols.max(1))
}

#[tauri::command]
pub fn pty_kill(state: State<PtyManager>, id: u64) -> Result<(), String> {
    state.kill(id);
    Ok(())
}
