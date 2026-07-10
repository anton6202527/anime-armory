// Tiny localhost media server: serves PNG/JPG/MP4 under the workspace by
// absolute path, with HTTP range support so MP4 scrubbing works in the webview.
//   GET /media?path=<absolute file path>
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::thread;

use tauri::State;
use tiny_http::{Header, Response, Server, StatusCode};

#[derive(Default)]
pub struct MediaState {
    port: Mutex<Option<u16>>,
    // files are only served if they canonicalize under one of these roots
    roots: Arc<Mutex<Vec<PathBuf>>>,
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
    } else if p.ends_with(".bmp") {
        "image/bmp"
    } else if p.ends_with(".svg") {
        "image/svg+xml"
    } else if p.ends_with(".mp4") || p.ends_with(".m4v") {
        "video/mp4"
    } else if p.ends_with(".mov") {
        "video/quicktime"
    } else if p.ends_with(".webm") {
        "video/webm"
    } else if p.ends_with(".wav") {
        "audio/wav"
    } else if p.ends_with(".mp3") {
        "audio/mpeg"
    } else if p.ends_with(".m4a") {
        "audio/mp4"
    } else if p.ends_with(".aac") {
        "audio/aac"
    } else if p.ends_with(".flac") {
        "audio/flac"
    } else if p.ends_with(".ogg") {
        "audio/ogg"
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
    if len == 0 {
        return None;
    }
    for h in headers {
        if h.field.equiv("Range") {
            let v = h.value.as_str();
            if let Some(r) = v.strip_prefix("bytes=") {
                let (a, b) = r.split_once('-')?;
                let start: u64 = a.parse().ok()?;
                let end: u64 = if b.is_empty() {
                    len - 1
                } else {
                    b.parse().ok()?
                };
                if start <= end && end < len {
                    return Some((start, end));
                }
            }
        }
    }
    None
}

fn media_headers(path: &str) -> Vec<Header> {
    vec![
        Header::from_bytes("Content-Type", content_type(path)).unwrap(),
        Header::from_bytes("Accept-Ranges", "bytes").unwrap(),
        Header::from_bytes("Access-Control-Allow-Origin", "*").unwrap(),
        Header::from_bytes("Access-Control-Allow-Headers", "Range").unwrap(),
        Header::from_bytes("X-Content-Type-Options", "nosniff").unwrap(),
    ]
}

fn handle(req: tiny_http::Request, roots: Arc<Mutex<Vec<PathBuf>>>) {
    let abs = match query_path(req.url()) {
        Some(p) => p,
        None => {
            let _ = req.respond(Response::from_string("missing path").with_status_code(400));
            return;
        }
    };
    // Resolve symlinks/.. and confine to an allowed root before opening anything.
    let canon = match std::fs::canonicalize(&abs) {
        Ok(c) => c,
        Err(_) => {
            let _ = req.respond(Response::from_string("not found").with_status_code(404));
            return;
        }
    };
    let allowed = roots.lock().unwrap().iter().any(|r| canon.starts_with(r));
    if !allowed {
        let _ = req.respond(Response::from_string("forbidden").with_status_code(403));
        return;
    }
    let path_str = canon.to_string_lossy().to_string();
    let mut file = match File::open(&canon) {
        Ok(f) => f,
        Err(_) => {
            let _ = req.respond(Response::from_string("not found").with_status_code(404));
            return;
        }
    };
    let len = file.metadata().map(|m| m.len()).unwrap_or(0);

    match parse_range(req.headers(), len) {
        Some((start, end)) => {
            let chunk = end - start + 1;
            if file.seek(SeekFrom::Start(start)).is_err() {
                let _ = req.respond(Response::from_string("seek error").with_status_code(500));
                return;
            }
            let reader = file.take(chunk);
            let cr =
                Header::from_bytes("Content-Range", format!("bytes {start}-{end}/{len}")).unwrap();
            let mut headers = media_headers(&path_str);
            headers.push(cr);
            let resp = Response::new(StatusCode(206), headers, reader, Some(chunk as usize), None);
            let _ = req.respond(resp);
        }
        None => {
            let resp = Response::new(
                StatusCode(200),
                media_headers(&path_str),
                file,
                Some(len as usize),
                None,
            );
            let _ = req.respond(resp);
        }
    }
}

impl MediaState {
    fn start(&self) -> Result<u16, String> {
        let mut port_guard = self
            .port
            .lock()
            .map_err(|_| "media port lock poisoned".to_string())?;
        if let Some(p) = *port_guard {
            return Ok(p);
        }
        let server = Arc::new(Server::http("127.0.0.1:0").map_err(|e| e.to_string())?);
        let port = server
            .server_addr()
            .to_ip()
            .map(|a| a.port())
            .ok_or("no port")?;
        // Four bounded workers keep image grids and one range-streaming video
        // from serializing behind a single large WebP/MP4 response.
        for _ in 0..4 {
            let server = server.clone();
            let roots = self.roots.clone();
            thread::spawn(move || {
                for req in server.incoming_requests() {
                    handle(req, roots.clone());
                }
            });
        }
        *port_guard = Some(port);
        Ok(port)
    }

    fn allow_root(&self, root: String) {
        let canon = std::fs::canonicalize(&root).unwrap_or_else(|_| PathBuf::from(&root));
        let mut g = self.roots.lock().unwrap();
        if !g.contains(&canon) {
            g.push(canon);
        }
    }
}

#[tauri::command]
pub fn start_media(state: State<MediaState>) -> Result<u16, String> {
    state.start()
}

#[tauri::command]
pub fn media_allow_root(state: State<MediaState>, root: String) {
    state.allow_root(root);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decodes_media_path_and_ignores_revision_query() {
        assert_eq!(
            query_path("/media?path=%2Ftmp%2F%E9%95%9C%E5%A4%B4.webp&v=abc"),
            Some("/tmp/镜头.webp".to_string())
        );
    }

    #[test]
    fn parses_bounded_and_open_ended_ranges() {
        let bounded = Header::from_bytes("Range", "bytes=5-9").unwrap();
        let open = Header::from_bytes("Range", "bytes=7-").unwrap();
        assert_eq!(parse_range(&[bounded], 20), Some((5, 9)));
        assert_eq!(parse_range(&[open], 20), Some((7, 19)));
        assert_eq!(parse_range(&[], 0), None);
    }

    #[test]
    fn reports_webp_content_type() {
        assert_eq!(content_type("/tmp/a.WEBP"), "image/webp");
    }
}
