import array
import json
import math
import os
import re
import subprocess
import wave

PLACEHOLDER = re.compile(r"待精修|待填|待定|占位|歌词…|歌词\.\.\.|placeholder|TODO|（待|\(待")
SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
SETTING_RE = re.compile(r"^\s*-\s*([^:：]+)\s*[:：]\s*(.*?)\s*(?:#.*)?$")

def read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return f.read()

def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def parse_settings(root):
    settings = {}
    for line in read_text(os.path.join(root, "_设置.md")).splitlines():
        m = SETTING_RE.match(line)
        if m:
            settings[m.group(1).strip()] = m.group(2).strip()
    return settings

def wav_duration(path):
    if not os.path.exists(path):
        return None
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / w.getframerate() if w.getframerate() else None
    except Exception:
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
