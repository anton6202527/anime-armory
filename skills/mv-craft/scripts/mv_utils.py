import array
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import wave

# 设置解析统一走本线 mv/_lib/settings.py（vendored，本线自包含）；别在本线另写一份 parser。
_COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mv", "_lib"))
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
from settings import load_settings as _load_settings  # noqa: E402
import io_utils  # noqa: E402

PLACEHOLDER = re.compile(r"待精修|待填|待定|占位|歌词…|歌词\.\.\.|placeholder|TODO|（待|\(待")
SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
SONG_EXTS = (".wav", ".mp3", ".m4a", ".flac")

# IO 小工具走本线 _lib/io_utils.py（vendored，本线自包含）；本线 load_json 历史是 resilient。
def read_text(path, default=""):
    return io_utils.read_text(path, default)

def write_text(path, text):
    io_utils.write_text(path, text)

def load_json(path, default=None):
    return io_utils.load_json(path, default, resilient=True)

def write_json(path, payload):
    io_utils.write_json(path, payload)

def parse_settings(root):
    # 委托给本线 _lib/settings.load_settings：正确处理 **加粗** key、跳过 `## 记录` 区，
    # 与本线 _lib/settings.py 写回格式同源（vendored，本线自包含）。
    return _load_settings(root)

def find_song(root):
    for ext in SONG_EXTS:
        path = os.path.join(root, "歌", f"song{ext}")
        if os.path.exists(path):
            return path
    return None

def relpath(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")

def wav_duration(path):
    if not os.path.exists(path):
        return None
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / w.getframerate() if w.getframerate() else None
    except Exception:
        return None

def audio_duration(path):
    if not path or not os.path.exists(path):
        return None
    if path.lower().endswith(".wav"):
        dur = wav_duration(path)
        if dur:
            return dur
    probed = ffprobe_json(path, "-show_entries", "format=duration")
    try:
        return float(probed.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        return None

def ffprobe_json(path, *args):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-of", "json", *args, path],
            capture_output=True, text=True, timeout=30)
        return json.loads(out.stdout) if out.stdout.strip() else {}
    except Exception:
        return {}

def ts_lrc(t):
    m = int(t // 60)
    s = t - 60 * m
    return f"[{m:02d}:{s:05.2f}]"

def ts_ass(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"

def parse_ass_time(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def _load_contract():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract.py")
    spec = importlib.util.spec_from_file_location("mv_contract", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def clean_stage_label(label):
    return re.sub(r"[（(].*?[）)]", "", str(label or "")).strip()

def update_progress_stage(root, stage_key, status="[x]"):
    progress = os.path.join(root, "_进度.md")
    if not os.path.exists(progress):
        return False
    contract = _load_contract()
    stage = next((s for s in contract.stage_table() if s.get("key") == stage_key), None)
    if not stage:
        raise KeyError(f"unknown mv stage key: {stage_key}")
    label = stage["label"]
    changed = False
    lines = []
    for raw in read_text(progress).splitlines():
        line = raw
        stripped = raw.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 3 and clean_stage_label(cells[0]) == label:
                cells[2] = status
                line = "| " + " | ".join(cells) + " |"
                changed = True
        lines.append(line)
    if changed:
        write_text(progress, "\n".join(lines) + "\n")
    return changed

def update_meta_flags(root):
    path = os.path.join(root, "_meta.json")
    meta = load_json(path, {})
    if not isinstance(meta, dict):
        return False
    before = dict(meta)
    meta["has_song"] = find_song(root) is not None
    meta["has_lyrics"] = os.path.exists(os.path.join(root, "词", "lyrics.md"))
    if meta != before:
        write_json(path, meta)
        return True
    return False
