// Tiny localhost media server: serves PNG/JPG/MP4 under the workspace by
// absolute path, with HTTP range support so MP4 scrubbing works in the webview.
//   GET /media?path=<absolute file path>
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::sync::Mutex;
use std::thread;

use tauri::State;
use tiny_http::{Header, Response, Server, StatusCode};

#[derive(Default)]
pub struct MediaState {
    port: Mutex<Option<u16>>,
}

fn content_type(path: &str) -> &'static str {
    let p = path.to_ascii_lowercase();
    if p.ends_with(".png") {
        "image/png"
    } else if p.ends_with(".jpg") || p.ends_with(".jpeg") {
        "image/jpeg"
    } else if p.ends_with(".webp") {
        "image/webp"
    } else if p.ends_with(".gif") {
        "image/gif"
    } else if p.ends_with(".mp4") || p.ends_with(".m4v") {
        "video/mp4"
    } else if p.ends_with(".webm") {
        "video/webm"
    } else if p.ends_with(".wav") {
        "audio/wav"
    } else if p.ends_with(".mp3") {
        "audio/mpeg"
    } else {
        "application/octet-stream"
    }
}

fn query_path(url: &str) -> Option<String> {
    // url like /media?path=<percent-encoded abs>
    let q = url.split_once('?')?.1;
    for kv in q.split('&') {
        if let Some(v) = kv.strip_prefix("path=") {
            return Some(percent_decode(v));
        }
    }
    None
}

fn percent_decode(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'%' if i + 2 < bytes.len() => {
                let hi = (bytes[i + 1] as char).to_digit(16);
                let lo = (bytes[i + 2] as char).to_digit(16);
                if let (Some(h), Some(l)) = (hi, lo) {
                    out.push((h * 16 + l) as u8);
                    i += 3;
                    continue;
                }
                out.push(bytes[i]);
                i += 1;
            }
            b'+' => {
                out.push(b' ');
                i += 1;
            }
            b => {
                out.push(b);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn parse_range(headers: &[Header], len: u64) -> Option<(u64, u64)> {
    for h in headers {
        if h.field.equiv("Range") {
            let v = h.value.as_str();
            if let Some(r) = v.strip_prefix("bytes=") {
                let (a, b) = r.split_once('-')?;
                let start: u64 = a.parse().ok()?;
                let end: u64 = if b.is_empty() { len - 1 } else { b.parse().ok()? };
                if start <= end && end < len {
                    return Some((start, end));
                }
            }
        }
    }
    None
}

fn handle(req: tiny_http::Request) {
    let abs = match query_path(req.url()) {
        Some(p) => p,
        None => {
            let _ = req.respond(Response::from_string("missing path").with_status_code(400));
            return;
        }
    };
    let mut file = match File::open(&abs) {
        Ok(f) => f,
        Err(_) => {
            let _ = req.respond(Response::from_string("not found").with_status_code(404));
            return;
        }
    };
    let len = file.metadata().map(|m| m.len()).unwrap_or(0);
    let ct = Header::from_bytes("Content-Type", content_type(&abs)).unwrap();
    let accept = Header::from_bytes("Accept-Ranges", "bytes").unwrap();

    match parse_range(req.headers(), len) {
        Some((start, end)) => {
            let chunk = end - start + 1;
            if file.seek(SeekFrom::Start(start)).is_err() {
                let _ = req.respond(Response::from_string("seek error").with_status_code(500));
                return;
            }
            let reader = file.take(chunk);
            let cr = Header::from_bytes("Content-Range", format!("bytes {start}-{end}/{len}")).unwrap();
            let resp = Response::new(StatusCode(206), vec![ct, accept, cr], reader, Some(chunk as usize), None);
            let _ = req.respond(resp);
        }
        None => {
            let resp = Response::new(StatusCode(200), vec![ct, accept], file, Some(len as usize), None);
            let _ = req.respond(resp);
        }
    }
}

impl MediaState {
    fn start(&self) -> Result<u16, String> {
        if let Some(p) = *self.port.lock().unwrap() {
            return Ok(p);
        }
        let server = Server::http("127.0.0.1:0").map_err(|e| e.to_string())?;
        let port = server.server_addr().to_ip().map(|a| a.port()).ok_or("no port")?;
        *self.port.lock().unwrap() = Some(port);
        thread::spawn(move || {
            for req in server.incoming_requests() {
                thread::spawn(move || handle(req));
            }
        });
        Ok(port)
    }
}

#[tauri::command]
pub fn start_media(state: State<MediaState>) -> Result<u16, String> {
    state.start()
}
