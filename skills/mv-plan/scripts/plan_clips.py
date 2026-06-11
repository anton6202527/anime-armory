#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate MV clip plan and timeline manifest from beatgrid + lyrics + blueprint."""
import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "contract.py")
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")


def load_contract():
    spec = importlib.util.spec_from_file_location("mv_contract", CONTRACT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()
mv_utils = load_mv_utils()

def parse_lyrics(root):
    path = os.path.join(root, "词", "lyrics.md")
    sections = []
    cur = None
    rows = []
    for raw in mv_utils.read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        m = mv_utils.SECTION_RE.match(line)
        if m:
            if cur:
                sections.append({"section": cur, "lines": rows})
            cur, rows = m.group(1).strip(), []
            continue
        line = mv_utils.PLACEHOLDER.sub("", line).strip()
        if line:
            rows.append(line)
    if cur:
        sections.append({"section": cur, "lines": rows})
    return sections


def normalize_sections(bg, meta, lyric_sections):
    duration = float(bg.get("duration") or 0)
    raw = bg.get("sections") or []
    sections = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        name = row.get("section") or row.get("name") or row.get("label") or f"section{i+1}"
        start = float(row.get("start", row.get("start_sec", 0)))
        end = row.get("end", row.get("end_sec"))
        sections.append({"section": str(name), "start": start, "end": float(end) if end is not None else None})
    if sections:
        sections = sorted(sections, key=lambda x: x["start"])
        for i, sec in enumerate(sections):
            if sec["end"] is None:
                sec["end"] = sections[i + 1]["start"] if i + 1 < len(sections) else duration
        return [s for s in sections if s["end"] > s["start"]]

    names = []
    if lyric_sections:
        names = [s["section"] for s in lyric_sections]
    elif isinstance(meta.get("structure"), list) and meta["structure"]:
        names = [str(s) for s in meta["structure"]]
    else:
        names = ["intro", "verse", "chorus", "outro"]
    if not duration:
        duration = 60.0
    step = duration / len(names)
    return [
        {"section": name, "start": round(i * step, 3), "end": round((i + 1) * step if i + 1 < len(names) else duration, 3)}
        for i, name in enumerate(names)
    ]


def is_chorus(name):
    low = name.lower()
    return any(k in low for k in ("chorus", "副歌", "drop", "hook", "refrain"))


def is_bridge(name):
    low = name.lower()
    return any(k in low for k in ("bridge", "pre", "间奏", "桥", "drop"))


def cut_points_for_section(sec, downbeats, profile, strategy):
    start, end = sec["start"], sec["end"]
    in_range = [t for t in downbeats if start < t < end]
    if not in_range:
        span = 3.0 if is_chorus(sec["section"]) or strategy == "全程强卡点" else 6.0
        pts = [start]
        cur = start + span
        while cur < end:
            pts.append(round(cur, 3))
            cur += span
        pts.append(end)
        return pts
    bars = profile["chorus_bars"] if is_chorus(sec["section"]) or strategy == "全程强卡点" else profile["verse_bars"]
    pts = [start]
    for idx, t in enumerate(in_range):
        if idx % max(1, bars) == 0:
            pts.append(float(t))
    pts.append(end)
    # 去重并丢掉太短切点
    clean = []
    for p in sorted(set(round(x, 3) for x in pts)):
        if not clean or p - clean[-1] >= 0.6:
            clean.append(p)
    if clean[-1] != round(end, 3):
        clean.append(round(end, 3))
    return clean


def merge_to_limit(clips, max_clips):
    if len(clips) <= max_clips:
        return clips
    merged = []
    i = 0
    while i < len(clips):
        cur = dict(clips[i])
        if len(clips) - i + len(merged) > max_clips and i + 1 < len(clips):
            nxt = clips[i + 1]
            cur["end"] = nxt["end"]
            cur["duration"] = round(cur["end"] - cur["start"], 3)
            cur["lyric_hint"] = " / ".join(x for x in (cur.get("lyric_hint"), nxt.get("lyric_hint")) if x)
            i += 2
        else:
            i += 1
        merged.append(cur)
    return merge_to_limit(merged, max_clips)


def lyric_hint_for(section_name, lyric_sections, index):
    candidates = [s for s in lyric_sections if s["section"] == section_name]
    lines = candidates[0]["lines"] if candidates else []
    if not lines:
        return ""
    return lines[index % len(lines)]


def build_clips(root, bg, sections, lyric_sections, granularity, strategy, visual_style):
    profile = contract.plan_granularity_profile(granularity)
    downbeats = [float(x) for x in (bg.get("downbeats") or bg.get("beats") or [])]
    raw_clips = []
    lyric_index_by_section = {}
    for sec in sections:
        pts = cut_points_for_section(sec, downbeats, profile, strategy)
        for i in range(len(pts) - 1):
            start, end = pts[i], pts[i + 1]
            if end <= start:
                continue
            idx = lyric_index_by_section.get(sec["section"], 0)
            lyric_index_by_section[sec["section"]] = idx + 1
            raw_clips.append({
                "section": sec["section"],
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "lyric_hint": lyric_hint_for(sec["section"], lyric_sections, idx),
            })
    raw_clips = merge_to_limit(raw_clips, profile["max_clips"])
    clips = []
    previous_end_state = ""
    for idx, clip in enumerate(raw_clips, 1):
        clip_id = f"Clip_{idx:03d}"
        section = clip["section"]
        key = is_chorus(section) or is_bridge(section)
        transition = "卡点硬切" if key else "动作切"
        beat_role = "key" if key else "normal"
        speed_mode = "trim" if key else "warp"
        action_family = "dance_hit/vfx_burst" if key else "performance_pose/expressive_walk"
        action = "副歌高光动作/光效爆点对齐 downbeat" if key else "叙事动作完整推进，镜头缓推"
        action_peak = round(end - min(0.2, max(0.05, (end - start) * 0.2)), 3)
        transition_motif = "光效切/whip pan" if key else "动作切/视线切"
        visual_motif = "继承视觉蓝图的主角身份锚点、段落主色和本段反复母题"
        end_state = f"{section} 段 {clip_id} 结束姿态，画面重心留给下一刀"
        start_state = previous_end_state or f"{section} 段首帧，继承视觉蓝图和定妆锚点"
        previous_end_state = end_state
        image_prompt = f"出图/段落/prompt/{clip_id}.md"
        video_prompt = f"出视频/prompt/{clip_id}.md"
        clips.append({
            "clip_id": clip_id,
            "section": section,
            "start": clip["start"],
            "end": clip["end"],
            "duration": clip["duration"],
            "beat_role": beat_role,
            "speed_mode": speed_mode,
            "action_family": action_family,
            "action_peak": action_peak,
            "transition_motif": transition_motif,
            "visual_motif": visual_motif,
            "lyric_hint": clip.get("lyric_hint", ""),
            "image_prompt_path": image_prompt,
            "video_prompt_path": video_prompt,
            "image_path": f"出图/段落/图片/{clip_id}.png",
            "end_frame_path": f"出图/段落/图片/{clip_id}_end.png",
            "need_end_frame": False,
            "selected_video_path": f"出视频/视频/{clip_id}.mp4",
            "transition": transition,
            "visual_style": visual_style,
            "continuity": {
                "start_state": start_state,
                "action": action,
                "end_state": end_state,
                "constraints": "同一段落保持角色定妆、服装发型、主色调、光线、道具、背景布局一致",
                "negative": "不要换脸、不要换衣、不要新增人物、不要改变场景、不要生成文字/logo/水印、不要生成原生人声",
            },
        })
    return clips


def write_prompt_files(root, clips, blueprint):
    for clip in clips:
        image_lines = [
            f"# {clip['clip_id']} 首帧出图任务",
            "",
            f"- 段落：{clip['section']}",
            f"- 时间：{clip['start']:.2f}s - {clip['end']:.2f}s",
            f"- 视觉风格：{clip['visual_style']}",
            f"- 歌词/情绪钩子：{clip['lyric_hint'] or '无'}",
            "",
            "## 首帧要求",
            f"用导演视角八维生成本 clip 首帧。画面必须服务：{clip['continuity']['action']}。",
            f"动作家族：{clip.get('action_family', '')}；动作峰值：{clip.get('action_peak', clip['end']):.2f}s。",
            f"视觉母题：{clip.get('visual_motif', '')}。",
            "",
            "## 继承",
            clip["continuity"]["constraints"],
            "",
            "## 负向",
            clip["continuity"]["negative"],
        ]
        mv_utils.write_text(os.path.join(root, clip["image_prompt_path"]), "\n".join(image_lines) + "\n")
        video_lines = [
            f"# {clip['clip_id']} 视频任务",
            "",
            f"- 首帧：`{clip['image_path']}`",
            f"- 时长：{clip['duration']:.2f}s",
            f"- 卡点：{clip['start']:.2f}s → {clip['end']:.2f}s",
            f"- 转场：{clip['transition']}",
            f"- 动作家族：{clip.get('action_family', '')}",
            f"- 动作峰值：{clip.get('action_peak', clip['end']):.2f}s",
            f"- 转场母题：{clip.get('transition_motif', '')}",
            "",
            "## continuity",
            f"- start_state：{clip['continuity']['start_state']}",
            f"- action：{clip['continuity']['action']}",
            f"- end_state：{clip['continuity']['end_state']}",
            f"- constraints：{clip['continuity']['constraints']}",
            f"- negative：{clip['continuity']['negative']}",
            "",
            "## 视频 prompt",
            f"人物运动：{clip['continuity']['action']}；动作家族：{clip.get('action_family', '')}；镜头运动：按段落张力执行；动态细节：发丝、衣摆、光斑或环境粒子随节拍变化；卡点约束：动作峰值对齐 {clip.get('action_peak', clip['end']):.2f}s；转场母题：{clip.get('transition_motif', '')}；声音约束：无对白、无旁白、不要生成原生人声，音乐由 mv-compose 使用原歌轨统一处理。",
        ]
        mv_utils.write_text(os.path.join(root, clip["video_prompt_path"]), "\n".join(video_lines) + "\n")


def build_markdown(title, clips):
    lines = [f"# MV clip plan — {title}", "", "| Clip | 段落 | 时间 | 时长 | 转场 | 歌词钩子 |", "|---|---|---:|---:|---|---|"]
    for c in clips:
        lines.append(f"| {c['clip_id']} | {c['section']} | {c['start']:.2f}-{c['end']:.2f}s | {c['duration']:.2f}s | {c['transition']} | {c.get('lyric_hint','')} |")
    lines.extend(["", "## 下一步", "1. mv-image 按 image_prompt_path 出首帧。", "2. mv-video/scripts/video_jobs.py 生成视频任务包。", "3. mv-compose 按 timeline_manifest.json 合成。"])
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="生成 MV clip_plan/timeline_manifest")
    ap.add_argument("project_root")
    ap.add_argument("--granularity", choices=contract.MV_PLAN_GRANULARITY)
    ap.add_argument("--strategy", choices=contract.MV_BEAT_STRATEGIES)
    ap.add_argument("--visual-style", choices=contract.MV_VISUAL_STYLES)
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    bg_path = os.path.join(root, "节拍", "beatgrid.json")
    if not os.path.exists(bg_path):
        print("[err] 缺 节拍/beatgrid.json，先跑 mv-beat", file=sys.stderr)
        sys.exit(2)
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {})
    bg = mv_utils.load_json(bg_path, {})
    settings = mv_utils.parse_settings(root)
    title = meta.get("title") or os.path.basename(root)
    granularity = args.granularity or settings.get("MV规划粒度") or "标准"
    strategy = args.strategy or settings.get("卡点策略") or "副歌强卡点"
    visual_style = args.visual_style or settings.get("MV视觉风格") or "电影叙事"
    lyric_sections = parse_lyrics(root)
    sections = normalize_sections(bg, meta, lyric_sections)
    clips = build_clips(root, bg, sections, lyric_sections, granularity, strategy, visual_style)
    if not clips:
        print("[err] 未生成任何 clip，请检查 beatgrid duration/sections", file=sys.stderr)
        sys.exit(1)
    write_prompt_files(root, clips, mv_utils.read_text(os.path.join(root, "视觉蓝图.md")))
    plan = {
        "schema_version": 1,
        "kind": "mv_clip_plan",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": title,
        "granularity": granularity,
        "strategy": strategy,
        "visual_style": visual_style,
        "beatgrid_path": "节拍/beatgrid.json",
        "clips": clips,
    }
    timeline = {
        "schema_version": 1,
        "kind": "mv_timeline_manifest",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": title,
        "song_path": "歌/song.wav",
        "beatgrid_path": "节拍/beatgrid.json",
        "clips": [
            {
                "clip_id": c["clip_id"],
                "section": c["section"],
                "start": c["start"],
                "end": c["end"],
                "duration": c["duration"],
                "video_path": c["selected_video_path"],
                "transition": c["transition"],
                "speed_mode": c["speed_mode"],
            }
            for c in clips
        ],
    }
    plan_dir = os.path.join(root, "分镜")
    mv_utils.write_json(os.path.join(plan_dir, "clip_plan.json"), plan)
    mv_utils.write_json(os.path.join(plan_dir, "timeline_manifest.json"), timeline)
    mv_utils.write_text(os.path.join(plan_dir, "clip_plan.md"), build_markdown(title, clips))
    print(f"[ok] clip plan → {os.path.join(plan_dir, 'clip_plan.json')}（{len(clips)} clips）")
    print(f"[ok] timeline → {os.path.join(plan_dir, 'timeline_manifest.json')}")
    print("\n[推荐下一步] 你可以运行语义分镜引擎，根据歌词和蓝图自动补全画面提示词：")
    print(f"             python3 skills/mv-plan/scripts/compose_prompts.py {root}")


if __name__ == "__main__":
    main()
