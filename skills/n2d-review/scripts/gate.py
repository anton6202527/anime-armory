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

from n2d_route import is_done, manifest_path, parse_progress, voice_is_placeholder  # noqa: E402
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
    # 时长清单可能在 合成/ 或 出视频/（先出视频后配音）下，两处都探
    p = manifest_path(root, ep) or os.path.join(root, "合成", ep, "配音", "时长清单.json")
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


def check_storyboard_contract(root: str, ep: str, require_frame_assets: bool = True) -> Optional[dict]:
    data = load_storyboard(root, ep)
    if not data:
        return None
    clips = data["clips"]
    policy = data.get("policy")
    if not isinstance(policy, dict) or policy.get("tailframe_default") is not True:
        add(BLOCK, "故事板", storyboard_path(root, ep), "storyboard.json 缺 policy.tailframe_default=true；首尾双帧接力必须作为默认契约")
    prev_end = None
    for i, clip in enumerate(clips, 1):
        loc = f"{storyboard_path(root, ep)} clip#{i}"
        first_png = clip.get("firstframe_png")
        if not first_png:
            add(BLOCK, "首帧", loc, "缺 firstframe_png")
        elif require_frame_assets:
            first_full = first_png if os.path.isabs(first_png) else os.path.join(root, first_png)
            if not os.path.exists(first_full):
                add(BLOCK, "首帧", first_full, "firstframe_png 不存在")
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
        if i < len(clips) and cont.get("need_endframe") is not True:
            if not cont.get("endframe_exempt_reason"):
                add(BLOCK, "尾帧", loc, "非最终 Clip 默认必须 need_endframe=true；若豁免需填写 endframe_exempt_reason")
        if cont.get("need_endframe") is True:
            end_png = cont.get("endframe_png")
            if not end_png:
                add(BLOCK, "尾帧", loc, "need_endframe=true 但未填写 endframe_png")
            elif require_frame_assets:
                full = end_png if os.path.isabs(end_png) else os.path.join(root, end_png)
                if not os.path.exists(full):
                    add(BLOCK, "尾帧", full, "need_endframe=true 但尾帧 PNG 不存在")
    return data


def check_prompt_checklists(root: str, ep: str, kind: str) -> None:
    if kind == "image":
        p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
        if not os.path.isfile(p):
            add(BLOCK, "prompt", p, "缺本集分镜出图 prompt")
            return
        text = open(p, encoding="utf-8").read()
        if "生成后自检流程" not in text and "自检（生成后逐张过" not in text:
            add(WARN, "prompt", p, "缺全局生成后自检流程")
        sections = re.findall(r"(?ms)^##\s+(?:镜头\s+\d+|Clip\s+\d+[A-Z]?).*?(?=^##\s+(?:镜头\s+\d+|Clip\s+\d+[A-Z]?)|\Z)", text)
        if not sections:
            add(BLOCK, "prompt", p, "未识别到逐镜 prompt 块")
            return
        for idx, sec in enumerate(sections, 1):
            check_image_shot_prompt_section(p, idx, sec)
        check_common_image_prompts(root)
        return
    else:
        p = os.path.join(root, "出视频", ep, "prompt", "01_clips.md")
        if not os.path.isfile(p):
            add(BLOCK, "prompt", p, "缺本集视频 Clip prompt")
            return
        text = open(p, encoding="utf-8").read()
        sections = re.findall(r"(?ms)^##\s+Clip\s+\d+[A-Z]?（.*?(?=^##\s+Clip\s+\d+[A-Z]?（|\Z)", text)
        if not sections:
            add(BLOCK, "prompt", p, "未识别到 Clip prompt 块")
            return
        for sec in sections:
            name = sec.splitlines()[0].strip()
            if "检查清单（视频三件套自查" not in sec:
                add(BLOCK, "prompt", p, f"{name} 缺提交前检查清单")
            if "自检（生成后逐条过" not in sec:
                add(BLOCK, "prompt", p, f"{name} 缺生成后自检段")
        return


def _has_any(text: str, needles: Iterable[str]) -> bool:
    return any(n in text for n in needles)


def _headline(section: str, fallback: str) -> str:
    first = next((ln.strip() for ln in section.splitlines() if ln.strip()), "")
    return first or fallback


def _reference_block(section: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^\*\*导演视角八维\*\*|^##\s+|\Z)", section)
    return m.group(0) if m else ""


def _section_has_character_refs(section: str) -> bool:
    refs = _reference_block(section)
    if "清空人物参考" in refs or "无需人物参考" in refs or "无人物" in section or "空镜" in section:
        return False
    # 场景/道具/VFX 纯空镜可没有角色锚点；含角色语义或人物定妆引用才按角色镜头卡。
    if _has_any(section, ("角色", "人物", "脸", "脸型", "发型", "服装", "妆造", "锚点句", "同一少女", "同一少年")):
        return True
    asset_names = re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
    non_character_words = (
        "场景", "道具", "寝殿", "宫", "殿", "庭", "院", "山", "洞", "门", "廊",
        "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉",
        "雷", "火", "云", "光效", "地标",
    )
    return any(not _has_any(name, non_character_words) for name in asset_names)


def check_image_shot_prompt_section(path: str, idx: int, section: str) -> None:
    name = _headline(section, f"镜头 {idx}")
    loc = f"{path} {name}"

    if "检查清单（八维自查" not in section:
        add(BLOCK, "prompt", loc, "缺提交前检查清单（八维自查·最易漏②机位/⑥光影/⑦张力）")
    if "**自检**" not in section and "逐镜自检" not in section and "自检（生成后逐张过" not in section:
        add(BLOCK, "prompt", loc, "缺生成后逐张自检段")
    if "重抽预算" not in section:
        add(BLOCK, "prompt", loc, "缺重抽预算字段；无法按主要人物/关键镜策略收口")
    if "正向 prompt（中文）" not in section:
        add(BLOCK, "prompt", loc, "缺正向 prompt（中文）")
    if "正向 prompt（英文）" not in section:
        add(BLOCK, "prompt", loc, "缺正向 prompt（英文）兜底")
    if "负向 prompt" not in section:
        add(BLOCK, "prompt", loc, "缺负向 prompt；人物/场景堵漏不可控")
    if "导演视角八维" not in section:
        add(BLOCK, "prompt", loc, "缺导演视角八维表；分镜图不能只写画师式描述")

    refs = _reference_block(section)
    if not refs:
        add(BLOCK, "prompt", loc, "缺参考图块；分镜图必须多图参考派生，禁止纯文生图")
    else:
        if "定妆_" not in refs:
            add(BLOCK, "prompt", loc, "参考图块未引用共享定妆资产；会导致跨镜人物/场景漂移")
        if "强度" not in refs and "strength" not in refs.lower():
            add(WARN, "prompt", loc, "参考图块未标参考强度；多图参考派生稳定性不可复现")

    for key in ("①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"):
        if key not in section:
            add(BLOCK, "prompt", loc, f"导演八维缺 {key} 维标记")

    if _section_has_character_refs(section):
        if not re.search(r"(锚点句|anchor phrase)\s*[:：]", section, re.IGNORECASE):
            add(BLOCK, "角色一致性", loc, "含角色镜头缺锚点句；每镜必须拼角色卡锚点")
        if not _has_any(section, ("脸型与定妆一致", "角色脸/妆造未漂移", "脸/妆造未漂移", "妆造未漂移")):
            add(BLOCK, "角色一致性", loc, "含角色镜头自检未显式检查脸/妆造漂移")
        if not _has_any(section, ("服装配色一致", "服装", "配色")):
            add(BLOCK, "角色一致性", loc, "含角色镜头未显式锁服装/配色")
        if "_侧" not in refs and "_半身" not in refs and "_全身" not in refs and "主体库" not in section and "角色ID" not in section:
            add(WARN, "角色一致性", loc, "含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂")


def check_common_image_prompts(root: str) -> None:
    prompt_dir = os.path.join(root, "出图", "common", "prompt")
    if not os.path.isdir(prompt_dir):
        add(BLOCK, "共享定妆", prompt_dir, "缺共享定妆 prompt 目录")
        return
    for filename in ("角色定妆.md", "场景定妆.md", "道具定妆.md", "法宝定妆.md", "特效定妆.md"):
        p = os.path.join(prompt_dir, filename)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        sections = re.findall(r"(?ms)^##\s+.*?(?=^##\s+|\Z)", text)
        for i, sec in enumerate(sections, 1):
            name = _headline(sec, f"{filename} block#{i}")
            loc = f"{p} {name}"
            if "目标存档" not in sec:
                add(BLOCK, "共享定妆", loc, "缺目标存档；共享资产无法归档追踪")
            if "正向 prompt（中文）" not in sec:
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（中文）")
            if "正向 prompt（英文）" not in sec:
                add(BLOCK, "共享定妆", loc, "缺正向 prompt（英文）")
            if "负向 prompt" not in sec:
                add(BLOCK, "共享定妆", loc, "缺负向 prompt")
            if "检查清单（定妆自查" not in sec:
                add(BLOCK, "共享定妆", loc, "缺定妆提交前检查清单")
            if "自检（生成后逐张过" not in sec and "**自检**" not in sec:
                add(BLOCK, "共享定妆", loc, "缺生成后落档自检段")
            if filename == "角色定妆.md":
                if "角色定妆组" not in sec:
                    add(BLOCK, "角色一致性", loc, "角色定妆缺定妆组说明；核心角色不能只靠单张正脸")
                if "锚点" not in sec:
                    add(BLOCK, "角色一致性", loc, "角色定妆缺锚点字段；下游每镜无锚可拼")


def check_shared_image_index(root: str, ep: str) -> None:
    overview = os.path.join(root, "出图", ep, "prompt", "00_总览.md")
    index = os.path.join(root, "出图", "common", "prompt", "00_索引.md")
    if not os.path.isfile(overview):
        add(BLOCK, "出图", overview, "缺本集出图总览")
        return
    if not os.path.isfile(index):
        add(BLOCK, "出图", index, "缺共享定妆索引")
        return
    index_text = open(index, encoding="utf-8").read()
    for ln in index_text.splitlines():
        if not ln.strip().startswith("|") or "✅" not in ln:
            continue
        paths = re.findall(r"`([^`]+\.png)`", ln)
        for rel in paths:
            full = rel if os.path.isabs(rel) else os.path.join(root, rel)
            if not os.path.exists(full):
                add(BLOCK, "共享定妆", index, f"索引标 ✅ 但 PNG 不存在：{rel}")
    overview_text = open(overview, encoding="utf-8").read()
    missing = []
    in_table = False
    for ln in overview_text.splitlines():
        if ln.startswith("## 共享定妆就绪状态"):
            in_table = True
            continue
        if in_table and ln.startswith("## "):
            break
        if in_table and ln.strip().startswith("|") and "⬜" in ln:
            missing.append(ln.strip())
    if missing:
        add(BLOCK, "共享定妆", overview, f"本集引用的共享定妆仍有未完成项：{missing[0][:120]}")


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
        check_storyboard_contract(root, ep, require_frame_assets=False)
        check_prompt_checklists(root, ep, "image")
        check_shared_image_index(root, ep)
    elif stage == "video":
        require_progress(root, ep, ("配音", "分镜设计", "出图prompt"))
        check_placeholder_policy(root, ep, "video")
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_image_assets(root, ep)
        check_prompt_checklists(root, ep, "video")
    elif stage == "compose":
        require_progress(root, ep, ("视频",))
        check_storyboard_contract(root, ep, require_frame_assets=True)
        check_compose_inputs(root, ep)
    elif stage == "review":
        check_storyboard_contract(root, ep, require_frame_assets=True)
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
