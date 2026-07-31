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
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "song", "song-craft", "scripts", "contract.py")
QUALITY_GATE_PATH = os.path.join(REPO, "skills", "song", "song-craft", "scripts", "quality_gate.py")


def load_contract():
    spec = importlib.util.spec_from_file_location("song_contract", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_song_utils():
    utils_path = os.path.join(REPO, "skills", "song", "song-craft", "scripts", "song_utils.py")
    spec = importlib.util.spec_from_file_location("song_utils", utils_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()


def load_quality_gate():
    spec = importlib.util.spec_from_file_location("song_quality_gate", QUALITY_GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


quality_gate = load_quality_gate()
try:
    song_utils = load_song_utils()
except Exception:
    song_utils = None

# 设置解析统一走本线 song/_lib/settings.py（vendored，本线自包含）；别在本线另写一份 parser。
_COMMON_DIR = os.path.join(REPO, "skills", "song", "_lib")
if _COMMON_DIR not in sys.path:
    sys.path.insert(0, _COMMON_DIR)
from settings import load_settings as _load_settings  # noqa: E402
import io_utils  # noqa: E402
from song_prompt_compiler import (  # noqa: E402
    KIND as SONG_PROMPT_KIND,
    VERSION as SONG_PROMPT_VERSION,
    compile_prompt,
    lint as lint_song_prompt,
    normalize_backend as normalize_song_backend,
    render_markdown,
)


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


# IO 小工具走本线 _lib/io_utils.py（vendored，本线自包含）；本线 load_json 历史是 strict。
def load_json(path, default):
    return io_utils.load_json(path, default)


def write_json(path, payload):
    io_utils.write_json(path, payload)


def read_text(path, default=""):
    return io_utils.read_text(path, default)


def write_text(path, text):
    io_utils.write_text(path, text)


def parse_settings(root):
    # 委托给本线 _lib/settings.load_settings：正确处理 **加粗** key、跳过 `## 记录` 区，
    # 与本线 _lib/settings.py 写回格式同源（vendored，本线自包含）。
    return _load_settings(root)


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
        meta.get("instrumentation") or settings.get("乐器编制"),  # 2026 配方：明确器乐编制（piano and strings…）显著提升可控性
        meta.get("vocal_type") or settings.get("人声类型"),      # 人声类型（female/male/duet/合成…），缺则跳过
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


def read_context_blocks(root):
    blocks = []
    for heading, relpath in (
        ("Song Brief", os.path.join("创作", "song_brief.md")),
        ("Reference Boundaries", os.path.join("素材", "reference_pack.md")),
        ("Chord Sheet", os.path.join("歌", "chord_sheet.md")),
        ("Topline Notes", os.path.join("歌", "topline_notes.md")),
    ):
        text = read_text(os.path.join(root, relpath), "").strip()
        if text:
            blocks.append((heading, text))
    return blocks


def build_prompt(title, take_id, backend, style, lyrics, duration, settings, meta, context_blocks=None, compiled=None):
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
        "## Style Prompt Seed（完整合同字段，不直接复制）",
        style,
        "",
    ]
    for heading, text in context_blocks or []:
        lines.extend([
            f"## {heading}",
            text,
            "",
        ])
    lines.extend([
        "## 操作提示",
        backend_hint(backend),
        "",
        "## 挑版重点",
        f"- 挑版策略：{settings.get('挑版策略', meta.get('take_selection_strategy', '人工挑版'))}",
        "- 优先判断：副歌 hook、旋律记忆点、人声清晰度、咬字、与蓝图情绪贴合、是否适合 MV 卡点。",
        "",
        "## Lyrics Contract（歌词原文必须完整，后端字段见下）",
        "```lyrics",
        lyrics.strip(),
        "```",
        "",
    ])
    if compiled:
        lines.extend([
            "## 提交边界",
            "以上 A&R、参考边界、和声/topline、挑版说明和操作提示是完整生产合同；不得整份粘进音乐后端。只提交下方 compiler 映射出的 style/prompt、lyrics 与结构化参数。歌词不做摘要或压缩。",
            "",
            render_markdown(compiled),
            "",
        ])
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
    gate = quality_gate.evaluate(root, "compose", waiver_reason=args.waiver_reason)
    quality_gate.write_report(root, gate)
    if not gate["passed"]:
        details = "; ".join(item["message"] for item in gate["findings"])
        raise SystemExit(f"[err] 作曲前质量闸门未通过：{details}")

    backend = args.backend or settings.get("作曲后端") or meta.get("song_backend") or meta.get("compose_backend") or "Suno"
    if backend not in contract.COMPOSE_BACKENDS:
        raise SystemExit(f"[err] 不支持的作曲后端：{backend}")
    takes = args.takes or parse_int(settings.get("生成版数"), 4)
    if takes < 1:
        raise SystemExit("[err] --takes 必须 >= 1")
    duration = args.duration or parse_seconds(meta.get("target_duration_seconds")) or parse_seconds(settings.get("目标时长"))
    style = make_style(meta, settings, args)
    context_blocks = read_context_blocks(root)
    brief = load_json(os.path.join(root, "创作", "song_brief.json"), {}) or {}
    source_files = [
        "_meta.json", "_设置.md", "词/lyrics.md", "创作/song_brief.json",
        "素材/reference_pack.json", "歌/song_form.json", "歌/chord_sheet.md", "歌/topline_notes.md",
    ]
    source_hashes = {
        relpath: quality_gate.sha256_file(os.path.join(root, relpath))
        for relpath in source_files if os.path.isfile(os.path.join(root, relpath))
    }

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
        compiled = compile_prompt({
            "take_id": take_id,
            "backend": backend,
            "title": title,
            "style_seed": style,
            "sonic_identity": brief.get("sonic_identity") or meta.get("sonic_identity"),
            "emotional_arc": brief.get("emotional_arc") or meta.get("emotional_arc") or meta.get("dynamic_arc"),
            "hook_intent": (
                f"在前 {brief.get('hook_deadline_seconds')} 秒建立可复唱 hook"
                if brief.get("hook_deadline_seconds") else ""
            ),
            "lyrics": lyrics,
            "duration_seconds": duration,
            "contract_context": {
                "settings": settings,
                "meta": meta,
                "song_brief": brief,
                "context_blocks": {heading: text for heading, text in context_blocks},
            },
        })
        if compiled["lint"]["errors"]:
            raise SystemExit(f"[err] {take_id} song prompt compiler blocked: {compiled['lint']['errors']}")
        write_text(
            prompt_path,
            build_prompt(title, take_id, backend, style, lyrics, duration, settings, meta, context_blocks, compiled),
        )
        previous = old_takes.get(take_id, {})
        contract_unchanged = previous.get("source_contract_sha256") == compiled["source_contract_sha256"]
        submit_fields_raw = json.dumps(compiled["submit_fields"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        take_rows.append({
            "take_id": take_id,
            "backend": previous.get("backend", backend),
            "status": previous.get("status", "planned") if contract_unchanged else "planned",
            "audio_path": previous.get("audio_path", rel(root, os.path.join(takes_dir, f"{take_id}.wav"))),
            "prompt_path": rel(root, prompt_path),
            "prompt_source_kind": "compiled_submit_fields",
            "prompt_compiler": {
                key: compiled[key]
                for key in ("kind", "version", "profile_version", "profile", "backend", "field_map")
            },
            "style_prompt": compiled["style_prompt"],
            "lyrics": compiled["lyrics"],
            "submit_fields": compiled["submit_fields"],
            "source_contract_sha256": compiled["source_contract_sha256"],
            "lyrics_sha256": compiled["lyrics_sha256"],
            "submit_fields_sha256": hashlib.sha256(submit_fields_raw.encode("utf-8")).hexdigest(),
            "score": previous.get("score", {}) if contract_unchanged else {},
            "notes": previous.get("notes", "") if contract_unchanged else "",
            "registered_at": previous.get("registered_at") if contract_unchanged else None,
            "previous_contract_invalidated": bool(previous) and not contract_unchanged,
        })

    old_selected = old.get("selected_take")
    selection_valid = bool(old_selected) and any(
        row.get("take_id") == old_selected and not row.get("previous_contract_invalidated") for row in take_rows
    )
    manifest = {
        "schema_version": 3,
        "kind": "song_take_manifest",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": title,
        "backend": backend,
        "requested_takes": takes,
        "target_duration_seconds": duration,
        "style_prompt": take_rows[0]["style_prompt"] if take_rows else style,
        "context_sources": [heading for heading, _ in context_blocks],
        "lyrics_path": "词/lyrics.md",
        "source_hashes": source_hashes,
        "compose_gate": gate,
        "selected_take": old_selected if selection_valid else None,
        "selection_receipt": old.get("selection_receipt") if selection_valid else None,
        "takes": take_rows,
    }
    write_json(manifest_path, manifest)
    write_json(os.path.join(song_dir, "compose_task.json"), {
        "schema_version": 3,
        "kind": "song_compose_task",
        "title": title,
        "backend": backend,
        "requested_takes": takes,
        "target_duration_seconds": duration,
        "style_prompt": take_rows[0]["style_prompt"] if take_rows else style,
        "prompt_compiler": take_rows[0].get("prompt_compiler", {}) if take_rows else {},
        "context_sources": [heading for heading, _ in context_blocks],
        "prompt_dir": "歌/compose_prompts",
        "manifest_path": "歌/takes_manifest.json",
        "source_hashes": source_hashes,
        "compose_gate_receipt": "评审/quality_gate_compose.json",
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
        f"- 上下文证据：{', '.join(manifest.get('context_sources') or []) or '无'}",
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


def validate_compiled_take(take, expected_backend):
    compiler = take.get("prompt_compiler") if isinstance(take.get("prompt_compiler"), dict) else {}
    payload = {
        **compiler,
        "style_prompt": str(take.get("style_prompt") or ""),
        "lyrics": str(take.get("lyrics") or ""),
        "submit_fields": take.get("submit_fields"),
        "lyrics_sha256": str(take.get("lyrics_sha256") or ""),
    }
    errors = []
    if take.get("prompt_source_kind") != "compiled_submit_fields":
        errors.append("prompt_source_kind_invalid")
    if compiler.get("kind") != SONG_PROMPT_KIND or compiler.get("version") != SONG_PROMPT_VERSION:
        errors.append("prompt_compiler_incompatible")
    if normalize_song_backend(compiler.get("backend")) != normalize_song_backend(expected_backend):
        errors.append("prompt_backend_mismatch")
    source_hash = str(take.get("source_contract_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        errors.append("source_contract_hash_invalid")
    fields_raw = json.dumps(take.get("submit_fields"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if str(take.get("submit_fields_sha256") or "") != hashlib.sha256(fields_raw.encode("utf-8")).hexdigest():
        errors.append("submit_fields_hash_mismatch")
    errors.extend(lint_song_prompt(payload)["errors"])
    return errors


def validate_manifest_sources(root, manifest):
    errors = []
    for relpath, expected in (manifest.get("source_hashes") or {}).items():
        path = os.path.join(root, relpath)
        if not os.path.isfile(path):
            errors.append(f"missing:{relpath}")
        elif quality_gate.sha256_file(path) != expected:
            errors.append(f"changed:{relpath}")
    return errors


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
    source_errors = validate_manifest_sources(root, manifest)
    if source_errors:
        raise SystemExit(f"[err] 作曲任务上游已变化：{source_errors}；先重跑 compose_song.py")
    compiler_errors = validate_compiled_take(take, manifest.get("backend"))
    if compiler_errors:
        raise SystemExit(f"[err] {take_id} 作曲提交字段无效：{compiler_errors}；先重跑 compose_song.py 重建任务包")
    target = os.path.join(root, "歌", "takes", f"{take_id}.wav")
    copied = copy_audio(src, target)
    take["status"] = "registered"
    take["audio_path"] = rel(root, copied)
    take["registered_at"] = date.today().isoformat()
    take["audio_sha256"] = quality_gate.sha256_file(copied)
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
            target = manifest.get("target_duration_seconds")
            if target and dur and (dur < float(target) * 0.75 or dur > float(target) * 1.25):
                print(f"[warn] {take_id} 时长 {dur:.1f}s 偏离目标 {target}s 超过 25%。")
        except Exception as e:
            pass # ignore parse errors during proactive linting
            
    return copied


def score_take(root, take_id, args):
    manifest_path, manifest = load_manifest(root)
    take = get_take(manifest, take_id)
    score = dict(take.get("score") or {})
    for key, attr in (
        ("hook", "hook_score"),
        ("melody", "melody_score"),
        ("vocal", "vocal_score"),
        ("arrangement", "arrangement_score"),
        ("mix", "mix_score"),
        ("brief_fit", "fit_score"),
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
    source_errors = validate_manifest_sources(root, manifest)
    if source_errors:
        raise SystemExit(f"[err] 作曲任务上游已变化：{source_errors}；先重跑 compose_song.py 并重新生成/评审")
    audio_rel = take.get("audio_path")
    if not audio_rel:
        raise SystemExit(f"[err] {take_id} 尚未登记音频")
    src = os.path.join(root, audio_rel)
    if not os.path.exists(src):
        raise SystemExit(f"[err] {take_id} 音频不存在：{audio_rel}")
    gate = quality_gate.evaluate(
        root, "select", take_id=take_id,
        waiver_reason=getattr(args, "waiver_reason", "") if args else "",
    )
    quality_gate.write_report(root, gate)
    if not gate["passed"]:
        details = "; ".join(item["message"] for item in gate["findings"])
        raise SystemExit(f"[err] 挑版质量闸门未通过：{details}")
    dst = os.path.join(root, "歌", "song.wav")
    copy_audio(src, dst)
    pre_master = os.path.join(root, "混音", "pre_master.wav")
    copy_audio(src, pre_master)
    for row in manifest.get("takes", []):
        if row.get("take_id") == take_id:
            row["status"] = "selected"
        elif row.get("status") == "selected":
            row["status"] = "registered"
    manifest["selected_take"] = take_id
    manifest["selected_at"] = date.today().isoformat()
    manifest["selection_receipt"] = {
        "take_id": take_id,
        "source_audio_sha256": quality_gate.sha256_file(src),
        "song_audio_sha256": quality_gate.sha256_file(dst),
        "pre_master_sha256": quality_gate.sha256_file(pre_master),
        "gate_receipt": "评审/quality_gate_select.json",
        "status": "selected_pre_master_not_release_master",
    }
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
    ap.add_argument("--melody-score", type=int, choices=range(1, 6))
    ap.add_argument("--vocal-score", type=int, choices=range(1, 6))
    ap.add_argument("--arrangement-score", type=int, choices=range(1, 6))
    ap.add_argument("--mix-score", type=int, choices=range(1, 6))
    ap.add_argument("--fit-score", type=int, choices=range(1, 6))
    ap.add_argument("--notes")
    ap.add_argument("--select", help="选择某个 take 作为 歌/song.wav")
    ap.add_argument("--split", action="store_true", help="配合 --select 使用，调用 demucs 分离人声和伴奏")
    ap.add_argument("--waiver-reason", default="", help="质量闸门例外理由（至少 10 字，会写入 receipt）")
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
