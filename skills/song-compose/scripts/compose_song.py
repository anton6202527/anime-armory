#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create and maintain song composition task packets and take manifests.

This script deliberately does not pretend to call every music backend. It creates
backend-ready prompt packets, records multiple generated takes, and selects one
take into 歌/song.wav once the user has listened and chosen.

Usage:
    python3 compose_song.py <写歌作品根> --backend ACE-Step --takes 4 --duration 120
    python3 compose_song.py <写歌作品根> --register /tmp/song.wav --take 1
    python3 compose_song.py <写歌作品根> --score take_01 --hook-score 5 --vocal-score 4 --notes "副歌最好"
    python3 compose_song.py <写歌作品根> --select take_01
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "song-craft", "scripts", "contract.py")


def load_contract():
    spec = importlib.util.spec_from_file_location("song_contract", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_song_utils():
    utils_path = os.path.join(REPO, "skills", "song-craft", "scripts", "song_utils.py")
    spec = importlib.util.spec_from_file_location("song_utils", utils_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()
try:
    song_utils = load_song_utils()
except Exception:
    song_utils = None

SETTING_RE = re.compile(r"^\s*-\s*([^:：]+)\s*[:：]\s*(.*?)\s*(?:#.*)?$")


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def parse_settings(root):
    settings = {}
    for line in read_text(os.path.join(root, "_设置.md")).splitlines():
        m = SETTING_RE.match(line)
        if m:
            settings[m.group(1).strip()] = m.group(2).strip()
    return settings


def parse_seconds(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"(\d+)", str(value))
    return int(m.group(1)) if m else None


def parse_int(value, default):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def title_for(root, meta):
    return meta.get("title") or os.path.basename(os.path.abspath(root))


def normalize_take_id(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    m = re.fullmatch(r"(?:take_?)?(\d+)", text, flags=re.I)
    if m:
        return f"take_{int(m.group(1)):02d}"
    if re.fullmatch(r"take_\d{2,}", text, flags=re.I):
        return text.lower()
    raise SystemExit(f"[err] take id 无效：{value}（用 1 / take_01）")


def make_style(meta, settings, args):
    if args.style:
        return args.style
    parts = [
        meta.get("genre"),
        meta.get("mood"),
        meta.get("target_platform") or settings.get("发行目标平台"),
        settings.get("语言") or args.language,
        settings.get("BPM/速度") or args.bpm,
        settings.get("调性") or args.key,
        meta.get("theme"),
    ]
    seen = set()
    clean = []
    for part in parts:
        if not part:
            continue
        text = str(part).strip()
        if text and text not in seen and text != "未定":
            seen.add(text)
            clean.append(text)
    return ", ".join(clean) or "根据歌词情绪生成完整流行歌曲"


def backend_hint(backend):
    hints = {
        "Suno": "Custom 模式：lyrics 框贴歌词，style 框贴 Style Prompt。生成后下载音频，再用 --register 登记。",
        "Udio": "Create / Extend：粘贴歌词与 Style Prompt。生成后下载音频，再用 --register 登记。",
        "ACE-Step": "本地 headless：将 Style Prompt 作为 prompt，将歌词作为 lyrics，按目标时长生成 wav。",
        "DiffRhythm": "本地扩散后端：按歌词、style、目标时长生成整首 wav，再用 --register 登记。",
        "manual": "手工外部后端：按任务包生成或录制音频，再用 --register 登记。",
    }
    return hints.get(backend, hints["manual"])


def build_prompt(title, take_id, backend, style, lyrics, duration, settings, meta):
    duration_line = f"{duration}s" if duration else settings.get("目标时长", "未定")
    lines = [
        f"# 作曲任务 — 《{title}》 {take_id}",
        "",
        "## 后端",
        f"- 作曲后端：{backend}",
        f"- 目标时长：{duration_line}",
        f"- 歌曲用途：{settings.get('歌曲用途', meta.get('use_case', '未定'))}",
        f"- 语言：{settings.get('语言', meta.get('language', '未定'))}",
        f"- BPM/速度：{settings.get('BPM/速度', meta.get('bpm', '未定'))}",
        f"- 调性：{settings.get('调性', meta.get('key', '未定'))}",
        "",
        "## Style Prompt",
        style,
        "",
        "## 操作提示",
        backend_hint(backend),
        "",
        "## 挑版重点",
        f"- 挑版策略：{settings.get('挑版策略', meta.get('take_selection_strategy', '人工挑版'))}",
        "- 优先判断：副歌 hook、旋律记忆点、人声清晰度、咬字、与蓝图情绪贴合、是否适合 MV 卡点。",
        "",
        "## Lyrics",
        "```lyrics",
        lyrics.strip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def prompt_plan(root, args):
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {})
    settings = parse_settings(root)
    title = title_for(root, meta)
    lyrics_path = os.path.join(root, "词", "lyrics.md")
    lyrics = read_text(lyrics_path)
    if not lyrics.strip():
        raise SystemExit("[err] 缺 词/lyrics.md，先完成 song-lyrics")

    backend = args.backend or settings.get("作曲后端") or meta.get("song_backend") or meta.get("compose_backend") or "Suno"
    if backend not in contract.COMPOSE_BACKENDS:
        raise SystemExit(f"[err] 不支持的作曲后端：{backend}")
    takes = args.takes or parse_int(settings.get("生成版数"), 4)
    if takes < 1:
        raise SystemExit("[err] --takes 必须 >= 1")
    duration = args.duration or parse_seconds(meta.get("target_duration_seconds")) or parse_seconds(settings.get("目标时长"))
    style = make_style(meta, settings, args)

    song_dir = os.path.join(root, "歌")
    prompt_dir = os.path.join(song_dir, "compose_prompts")
    takes_dir = os.path.join(song_dir, "takes")
    os.makedirs(prompt_dir, exist_ok=True)
    os.makedirs(takes_dir, exist_ok=True)

    manifest_path = os.path.join(song_dir, "takes_manifest.json")
    old = load_json(manifest_path, {})
    old_takes = {t.get("take_id"): t for t in old.get("takes", []) if t.get("take_id")}
    take_rows = []
    for i in range(1, takes + 1):
        take_id = f"take_{i:02d}"
        prompt_path = os.path.join(prompt_dir, f"{take_id}.md")
        write_text(prompt_path, build_prompt(title, take_id, backend, style, lyrics, duration, settings, meta))
        previous = old_takes.get(take_id, {})
        take_rows.append({
            "take_id": take_id,
            "backend": previous.get("backend", backend),
            "status": previous.get("status", "planned"),
            "audio_path": previous.get("audio_path", rel(root, os.path.join(takes_dir, f"{take_id}.wav"))),
            "prompt_path": rel(root, prompt_path),
            "score": previous.get("score", {}),
            "notes": previous.get("notes", ""),
            "registered_at": previous.get("registered_at"),
        })

    manifest = {
        "schema_version": 1,
        "kind": "song_take_manifest",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": title,
        "backend": backend,
        "requested_takes": takes,
        "target_duration_seconds": duration,
        "style_prompt": style,
        "lyrics_path": "词/lyrics.md",
        "selected_take": old.get("selected_take"),
        "takes": take_rows,
    }
    write_json(manifest_path, manifest)
    write_json(os.path.join(song_dir, "compose_task.json"), {
        "schema_version": 1,
        "kind": "song_compose_task",
        "title": title,
        "backend": backend,
        "requested_takes": takes,
        "target_duration_seconds": duration,
        "style_prompt": style,
        "prompt_dir": "歌/compose_prompts",
        "manifest_path": "歌/takes_manifest.json",
    })
    write_text(os.path.join(song_dir, "compose_task.md"), build_task_markdown(manifest))
    return manifest


def build_task_markdown(manifest):
    lines = [
        f"# 作曲任务包 — 《{manifest['title']}》",
        "",
        f"- 作曲后端：{manifest['backend']}",
        f"- 生成版数：{manifest['requested_takes']}",
        f"- 目标时长：{manifest.get('target_duration_seconds') or '未定'}s",
        f"- take manifest：`歌/takes_manifest.json`",
        "",
        "## Style Prompt",
        manifest["style_prompt"],
        "",
        "## Takes",
    ]
    for take in manifest["takes"]:
        lines.append(f"- {take['take_id']}: {take['status']} · prompt `{take['prompt_path']}` · audio `{take['audio_path']}`")
    lines.extend([
        "",
        "## 下一步",
        "1. 按每个 prompt 在所选后端生成音频。",
        "2. 用 `compose_song.py <作品根> --register <音频文件> --take N` 登记每一版。",
        "3. 试听后用 `--score take_NN ...` 评分，用 `--select take_NN` 定稿到 `歌/song.wav`。",
    ])
    return "\n".join(lines) + "\n"


def load_manifest(root):
    path = os.path.join(root, "歌", "takes_manifest.json")
    if not os.path.exists(path):
        raise SystemExit("[err] 缺 歌/takes_manifest.json，先运行一次 compose_song.py 生成任务包")
    return path, load_json(path, {})


def get_take(manifest, take_id):
    for take in manifest.get("takes", []):
        if take.get("take_id") == take_id:
            return take
    raise SystemExit(f"[err] manifest 里没有 {take_id}")


def copy_audio(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if src.lower().endswith(".wav"):
        shutil.copy(src, dst)
        return dst
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", src, "-ar", "44100", "-ac", "2", dst], check=True)
        return dst
    ext = os.path.splitext(src)[1] or ".audio"
    fallback = os.path.splitext(dst)[0] + ext
    shutil.copy(src, fallback)
    return fallback


def register_take(root, src, take_id):
    if not os.path.exists(src):
        raise SystemExit(f"[err] 找不到音频文件：{src}")
    manifest_path, manifest = load_manifest(root)
    take = get_take(manifest, take_id)
    target = os.path.join(root, "歌", "takes", f"{take_id}.wav")
    copied = copy_audio(src, target)
    take["status"] = "registered"
    take["audio_path"] = rel(root, copied)
    take["registered_at"] = date.today().isoformat()
    write_json(manifest_path, manifest)
    
    # Proactive linting
    if song_utils and copied.endswith(".wav"):
        try:
            dur, rate, ch, sw, peak, clip, rms, head, tail = song_utils._wav_peak_clip(copied)
            if clip is not None and clip > 0.005:
                print(f"[warn] {take_id} 检测到削波 (clipping: {clip*100:.1f}%)，建议在评分时注意音质或重新生成。")
            if peak is not None and peak < 1e-6:
                print(f"[warn] {take_id} 几乎全静音，可能生成失败！")
            elif peak is not None:
                import math
                dbfs = 20 * math.log10(peak)
                if dbfs < -40.0:
                    print(f"[warn] {take_id} 近静音 (峰值 {dbfs:.1f}dBFS)，请检查是否生成成功。")
            if dur and dur < 30:
                print(f"[warn] {take_id} 时长仅 {dur:.1f}s，可能是截断的片段。")
        except Exception as e:
            pass # ignore parse errors during proactive linting
            
    return copied


def score_take(root, take_id, args):
    manifest_path, manifest = load_manifest(root)
    take = get_take(manifest, take_id)
    score = dict(take.get("score") or {})
    for key, attr in (
        ("hook", "hook_score"),
        ("vocal", "vocal_score"),
        ("blueprint_fit", "fit_score"),
        ("clarity", "clarity_score"),
        ("mv_fit", "mv_score"),
    ):
        value = getattr(args, attr)
        if value is not None:
            score[key] = value
    numeric = [v for v in score.values() if isinstance(v, (int, float))]
    if numeric:
        score["average"] = round(sum(numeric) / len(numeric), 2)
    if args.notes is not None:
        take["notes"] = args.notes
    take["score"] = score
    if take.get("status") == "planned":
        take["status"] = "scored"
    write_json(manifest_path, manifest)


def select_take(root, take_id, args=None):
    manifest_path, manifest = load_manifest(root)
    take = get_take(manifest, take_id)
    audio_rel = take.get("audio_path")
    if not audio_rel:
        raise SystemExit(f"[err] {take_id} 尚未登记音频")
    src = os.path.join(root, audio_rel)
    if not os.path.exists(src):
        raise SystemExit(f"[err] {take_id} 音频不存在：{audio_rel}")
    dst = os.path.join(root, "歌", "song.wav")
    copy_audio(src, dst)
    for row in manifest.get("takes", []):
        if row.get("take_id") == take_id:
            row["status"] = "selected"
        elif row.get("status") == "selected":
            row["status"] = "registered"
    manifest["selected_take"] = take_id
    manifest["selected_at"] = date.today().isoformat()
    write_json(manifest_path, manifest)
    
    if args and getattr(args, "split", False):
        try:
            print("[info] 正在使用 demucs 分离人声和伴奏，请稍候...")
            subprocess.run(["python3", "-m", "demucs", "--two-stems", "vocals", 
                            "-o", os.path.join(root, "歌", "_demucs"), dst], check=True)
            print("[ok] demucs 分离完成 → 歌/_demucs/ (vocals/no_vocals)")
        except Exception as e:
            print(f"[warn] demucs 运行失败，请确认是否已安装 (pip install demucs)：{e}")


def main():
    ap = argparse.ArgumentParser(description="生成/维护 song-compose 多版任务包与挑版 manifest")
    ap.add_argument("project_root")
    ap.add_argument("--backend", choices=contract.COMPOSE_BACKENDS)
    ap.add_argument("--takes", type=int)
    ap.add_argument("--duration", type=int, help="目标时长秒数")
    ap.add_argument("--style", default="")
    ap.add_argument("--language", default="")
    ap.add_argument("--bpm", default="")
    ap.add_argument("--key", default="")
    ap.add_argument("--register", help="登记一个外部生成的音频文件")
    ap.add_argument("--take", help="配合 --register 使用，1/take_01 均可")
    ap.add_argument("--score", help="给某个 take 评分，1/take_01 均可")
    ap.add_argument("--hook-score", type=int, choices=range(1, 6))
    ap.add_argument("--vocal-score", type=int, choices=range(1, 6))
    ap.add_argument("--fit-score", type=int, choices=range(1, 6))
    ap.add_argument("--clarity-score", type=int, choices=range(1, 6))
    ap.add_argument("--mv-score", type=int, choices=range(1, 6))
    ap.add_argument("--notes")
    ap.add_argument("--select", help="选择某个 take 作为 歌/song.wav")
    ap.add_argument("--split", action="store_true", help="配合 --select 使用，调用 demucs 分离人声和伴奏")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    if not any((args.register, args.score, args.select)):
        manifest = prompt_plan(root, args)
        print(f"[ok] 作曲任务包 → {os.path.join(root, '歌', 'compose_task.md')}")
        print(f"[ok] take manifest → {os.path.join(root, '歌', 'takes_manifest.json')}（{manifest['requested_takes']} 版）")
        return

    if args.register:
        take_id = normalize_take_id(args.take)
        if not take_id:
            raise SystemExit("[err] --register 需要配合 --take 1/take_01")
        copied = register_take(root, args.register, take_id)
        print(f"[ok] {take_id} 登记 → {copied}")

    if args.score:
        take_id = normalize_take_id(args.score)
        score_take(root, take_id, args)
        print(f"[ok] {take_id} 评分已写入 takes_manifest.json")

    if args.select:
        take_id = normalize_take_id(args.select)
        select_take(root, take_id, args)
        print(f"[ok] {take_id} 已定稿 → {os.path.join(root, '歌', 'song.wav')}")


if __name__ == "__main__":
    main()
