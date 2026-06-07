#!/usr/bin/env python3
"""Deterministic stage gates for novel2drama/n2d.

This script turns the high-risk SKILL.md rules into repeatable checks.  It does
not create assets; it only reports whether a stage may proceed.

Usage:
  python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage image|video|compose|review
  python3 skills/n2d-review/scripts/gate.py <作品根> 第N集 --stage video --json

Exit codes:
  0 = no blockers
  1 = at least one blocker
  2 = bad invocation / missing project
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
COMMON = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_route import is_done, parse_progress, voice_is_placeholder  # noqa: E402
from n2d_settings import is_video_first, watermark_setting  # noqa: E402

BLOCK, WARN, INFO = "block", "warn", "info"
findings: List[Dict[str, str]] = []


def add(sev: str, dim: str, loc: str, msg: str) -> None:
    findings.append({"sev": sev, "dim": dim, "loc": loc, "msg": msg})


def exists(path: str) -> bool:
    return os.path.exists(path)


def load_json(path: str):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def row_for(root: str, ep: str) -> Tuple[List[str], Optional[Dict[str, str]]]:
    try:
        header, rows = parse_progress(root)
    except Exception as e:
        add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"进度表不可解析：{e}")
        return [], None
    row = next((r for r in rows if r.get("_ep") == ep), None)
    if row is None:
        add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"{ep} 不在进度表")
    return header, row


def require_progress(root: str, ep: str, cols: Iterable[str]) -> None:
    header, row = row_for(root, ep)
    if row is None:
        return
    for col in cols:
        if col not in header:
            add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"缺进度列：{col}")
        elif not is_done(row.get(col, "")):
            add(BLOCK, "进度", os.path.join(root, "_进度.md"), f"{ep}「{col}」未完成（当前 {row.get(col, '⬜')}）")


def progress_fraction_done(root: str, ep: str, col: str) -> bool:
    _, row = row_for(root, ep)
    if not row:
        return False
    return is_done(row.get(col, ""))


def voice_manifest(root: str, ep: str) -> Optional[List[dict]]:
    p = os.path.join(root, "合成", ep, "配音", "时长清单.json")
    data = load_json(p)
    if not isinstance(data, list):
        add(BLOCK, "配音", p, "缺少或无法解析时长清单.json")
        return None
    return data


def check_placeholder_policy(root: str, ep: str, stage: str) -> None:
    ph = voice_is_placeholder(root, ep)
    if ph is None:
        add(WARN, "配音", ep, "未找到可判定的占位字段；若尚未配音，下游应先补齐")
        return
    if not ph:
        return
    if stage == "image":
        add(WARN, "配音", ep, "当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时")
    elif stage == "video" and is_video_first(root):
        add(WARN, "配音", ep, "先出视频后配音模式已放行占位时长；后期补真音可能需要重出视频")
    else:
        add(BLOCK, "配音", ep, "配音仍为占位音色；该阶段不应继续")


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def load_storyboard(root: str, ep: str) -> Optional[dict]:
    p = storyboard_path(root, ep)
    data = load_json(p)
    if not isinstance(data, dict):
        add(BLOCK, "故事板", p, "缺少机器可读 storyboard.json；下游无法确定 continuity/need_endframe")
        return None
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        add(BLOCK, "故事板", p, "storyboard.json 缺 clips[]")
        return None
    return data


def check_storyboard_contract(root: str, ep: str) -> Optional[dict]:
    data = load_storyboard(root, ep)
    if not data:
        return None
    clips = data["clips"]
    prev_end = None
    for i, clip in enumerate(clips, 1):
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        cont = clip.get("continuity")
        if not isinstance(cont, dict):
            add(BLOCK, "故事板", loc, "缺 continuity 块")
            continue
        for key in ("start_state", "end_state", "transition", "need_endframe"):
            if key not in cont:
                add(BLOCK, "故事板", loc, f"continuity 缺字段：{key}")
        if prev_end and cont.get("start_state") != prev_end:
            add(BLOCK, "故事板", loc, "start_state 未原样继承上一 Clip 的 end_state")
        prev_end = cont.get("end_state")
        if cont.get("need_endframe") is True:
            end_png = cont.get("endframe_png")
            if not end_png:
                add(BLOCK, "尾帧", loc, "need_endframe=true 但未填写 endframe_png")
            else:
                full = end_png if os.path.isabs(end_png) else os.path.join(root, end_png)
                if not os.path.exists(full):
                    add(BLOCK, "尾帧", full, "need_endframe=true 但尾帧 PNG 不存在")
    return data


def prompt_blocks(paths: Iterable[str]) -> Iterable[Tuple[str, str]]:
    for p in paths:
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        chunks = re.split(r"(?m)^##\s+", text)
        for idx, chunk in enumerate(chunks):
            if idx == 0 and not chunk.strip():
                continue
            yield p, chunk


def check_prompt_checklists(root: str, ep: str, kind: str) -> None:
    if kind == "image":
        paths = glob.glob(os.path.join(root, "出图", "common", "prompt", "*.md"))
        paths += glob.glob(os.path.join(root, "出图", ep, "prompt", "*.md"))
        required = ("检查清单（", "自检（生成后逐张过")
    else:
        paths = glob.glob(os.path.join(root, "出视频", ep, "prompt", "*.md"))
        required = ("检查清单（视频三件套自查", "自检（生成后逐条过")
    if not paths:
        add(BLOCK, "prompt", root, f"缺 {kind} prompt 文件")
        return
    checked = 0
    for p, chunk in prompt_blocks(paths):
        if "prompt" not in chunk.lower() and "Prompt" not in chunk and "视频 prompt" not in chunk:
            continue
        checked += 1
        for marker in required:
            if marker not in chunk:
                add(BLOCK, "prompt", p, f"prompt 块缺必需检查段：{marker}")
    if checked == 0:
        add(WARN, "prompt", root, f"未识别到 {kind} prompt 块，检查清单闸门可能未覆盖")


def check_shared_image_index(root: str, ep: str) -> None:
    overview = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    index = os.path.join(root, "出图", "common", "prompt", "00_索引.md")
    if not os.path.isfile(overview):
        add(BLOCK, "出图", overview, "缺本集出图总览")
        return
    if not os.path.isfile(index):
        add(BLOCK, "出图", index, "缺共享定妆索引")
        return
    idx_text = open(index, encoding="utf-8").read()
    bad = []
    for ln in idx_text.splitlines():
        if ln.strip().startswith("|") and "⬜" in ln:
            bad.append(ln.strip())
    if bad:
        add(BLOCK, "共享定妆", index, f"共享索引仍有未完成项：{bad[0][:120]}")


def check_image_assets(root: str, ep: str) -> None:
    if not progress_fraction_done(root, ep, "出图"):
        add(BLOCK, "出图", os.path.join(root, "_进度.md"), "出图列未满，不能进入出视频")
    pngs = glob.glob(os.path.join(root, "出图", ep, "*.png"))
    if not pngs:
        add(BLOCK, "出图", os.path.join(root, "出图", ep), "本集没有分镜 PNG")


def ffprobe_json(path: str) -> Optional[dict]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
            text=True,
        )
        return json.loads(out)
    except Exception:
        return None


def duration(path: str) -> Optional[float]:
    data = ffprobe_json(path)
    if not data:
        return None
    try:
        return float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        return None


def has_audio(path: str) -> Optional[bool]:
    data = ffprobe_json(path)
    if not data:
        return None
    return any(s.get("codec_type") == "audio" for s in data.get("streams", []))


def clip_files(root: str, ep: str) -> List[str]:
    return sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))


def check_video_assets(root: str, ep: str) -> None:
    clips = clip_files(root, ep)
    if not clips:
        add(BLOCK, "视频", os.path.join(root, "出视频", ep, "视频"), "缺 clip MP4")
        return
    sb = load_storyboard(root, ep)
    if sb and len(clips) != len(sb.get("clips", [])):
        add(WARN, "视频", os.path.join(root, "出视频", ep, "视频"), f"clip 数 {len(clips)} 与 storyboard clips {len(sb.get('clips', []))} 不一致")
    audio_hits = [c for c in clips if has_audio(c)]
    if audio_hits:
        add(WARN, "原生音轨", audio_hits[0], "clip 含原生音轨；compose 默认丢弃，若要保留环境声需确认无原生人声")
    shots = load_json(os.path.join(root, "脚本", ep, "镜头时长.json"))
    if isinstance(shots, dict):
        target = sum(float(v) for v in shots.values())
        actuals = [duration(c) for c in clips]
        if all(d is not None for d in actuals):
            total = sum(d for d in actuals if d is not None)
            if abs(total - target) > 1.0:
                add(WARN, "时长", ep, f"clip 总长 {total:.2f}s 与镜头时长累计 {target:.2f}s 差 {abs(total-target):.2f}s")


def check_compose_inputs(root: str, ep: str) -> None:
    check_video_assets(root, ep)
    check_placeholder_policy(root, ep, "compose")
    zh = os.path.join(root, "脚本", ep, "字幕_中文.srt")
    if not os.path.isfile(zh):
        add(BLOCK, "字幕", zh, "缺中文字幕")


def check_final_watermark(root: str, ep: str) -> None:
    wm = watermark_setting(root)
    if wm == "不打":
        add(WARN, "水印", os.path.join(root, "_设置.md"), "水印设置为不打；正式投放 AI 合成内容建议保留 AI 合规标识")
        return
    finals = glob.glob(os.path.join(root, "合成", ep, f"成片_{ep}_*_水印.mp4"))
    if not finals:
        add(BLOCK, "水印", os.path.join(root, "合成", ep), f"水印设置为「{wm}」，但未找到 *_水印.mp4")


def run(root: str, ep: str, stage: str) -> None:
    if not os.path.isdir(root):
        add(BLOCK, "路径", root, "作品根不存在")
        return
    if stage == "image":
        require_progress(root, ep, ("配音", "分镜设计"))
        check_placeholder_policy(root, ep, "image")
        check_storyboard_contract(root, ep)
        check_prompt_checklists(root, ep, "image")
        check_shared_image_index(root, ep)
    elif stage == "video":
        require_progress(root, ep, ("配音", "分镜设计", "出图prompt"))
        check_placeholder_policy(root, ep, "video")
        check_storyboard_contract(root, ep)
        check_image_assets(root, ep)
        check_prompt_checklists(root, ep, "video")
    elif stage == "compose":
        require_progress(root, ep, ("视频",))
        check_storyboard_contract(root, ep)
        check_compose_inputs(root, ep)
    elif stage == "review":
        check_storyboard_contract(root, ep)
        check_video_assets(root, ep)
        check_final_watermark(root, ep)
    else:
        add(BLOCK, "参数", stage, "未知 stage")


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--stage", required=True, choices=("image", "video", "compose", "review"))
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    run(ns.root.rstrip("/"), ns.episode, ns.stage)
    if ns.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        blocks = sum(1 for f in findings if f["sev"] == BLOCK)
        warns = sum(1 for f in findings if f["sev"] == WARN)
        infos = sum(1 for f in findings if f["sev"] == INFO)
        print(f"=== n2d gate: {ns.root} {ns.episode} stage={ns.stage} ===")
        print(f"block {blocks} · warn {warns} · info {infos}\n")
        order = {BLOCK: 0, WARN: 1, INFO: 2}
        for f in sorted(findings, key=lambda x: order[x["sev"]]):
            icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}[f["sev"]]
            print(f"{icon} [{f['dim']}] {f['loc']}: {f['msg']}")
    return 1 if any(f["sev"] == BLOCK for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

