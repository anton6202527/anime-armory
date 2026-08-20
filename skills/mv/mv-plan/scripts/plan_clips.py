#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate MV clip plan and timeline manifest from beatgrid + lyrics + blueprint."""
import argparse
import importlib.util
import json
import math
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONTRACT_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "contract.py")
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
GATE_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "gate.py")
REGISTRY_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "identity_registry.py")


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

def load_gate():
    spec = importlib.util.spec_from_file_location("mv_gate", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_registry():
    spec = importlib.util.spec_from_file_location("mv_identity_registry", REGISTRY_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load_contract()
mv_utils = load_mv_utils()
mv_gate = load_gate()
registry = load_registry()


def blueprint_value(blueprint, key, default=""):
    match = re.search(rf"^\s*[-*]\s*{re.escape(key)}\s*[:：]\s*(.+)$", blueprint, re.M | re.I)
    return match.group(1).strip() if match else default

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


def alignment_lines(root):
    report = mv_utils.load_json(os.path.join(root, "字幕", "alignment_report.json"), None)
    if not isinstance(report, dict):
        return [], None
    rows = []
    for row in report.get("lines") or []:
        if not isinstance(row, dict):
            continue
        try:
            start, end = float(row["start"]), float(row["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if end > start and str(row.get("line") or "").strip():
            rows.append({"line": str(row["line"]).strip(), "start": start, "end": end})
    return sorted(rows, key=lambda row: (row["start"], row["end"])), report


def lyric_hint_for_interval(start, end, rows):
    """Join true alignment intervals; never rotate lyrics by clip index."""
    matched = [row for row in rows if min(end, row["end"]) - max(start, row["start"]) > 0.0]
    return " / ".join(dict.fromkeys(row["line"] for row in matched))


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
        sections.append({
            "section": str(name),
            "start": start,
            "end": float(end) if end is not None else None,
            "source": row.get("source") or bg.get("section_source") or "beatgrid_sections",
        })
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
    lyric_counts = {row["section"]: max(1, len(row.get("lines") or [])) for row in lyric_sections}
    weights = [lyric_counts.get(name, 1) for name in names]
    total = float(sum(weights))
    cursor = 0.0
    rows = []
    for name, weight in zip(names, weights):
        end = duration if len(rows) == len(names) - 1 else cursor + duration * weight / total
        rows.append({"section": name, "start": round(cursor, 3), "end": round(end, 3),
                     "source": "unverified_lyric_weight_estimate"})
        cursor = end
    return rows


def is_chorus(name):
    low = name.lower()
    return any(k in low for k in ("chorus", "副歌", "drop", "hook", "refrain"))


def is_bridge(name):
    low = name.lower()
    return any(k in low for k in ("bridge", "pre", "间奏", "桥", "drop"))


def get_energy_at(t, energy_map):
    if not energy_map:
        return 0.5
    idx = int(t)
    if idx < 0: row = energy_map[0]
    elif idx >= len(energy_map): row = energy_map[-1]
    else: row = energy_map[idx]
    if isinstance(row, dict):
        values = [float(x.get("rms") or 0) for x in energy_map if isinstance(x, dict)]
        peak = max(values) if values else 0
        return min(1.0, float(row.get("rms") or 0) / peak) if peak else 0.5
    return float(row)


def nearest_downbeat(t, downbeats):
    if not downbeats:
        return None
    return min((float(x) for x in downbeats), key=lambda x: abs(x - t))


def section_location(section, lyric_hint, assets):
    locations = [a for a in assets.get("assets", []) if a.get("type") == "location"]
    if not locations:
        return "LOC_UNSPECIFIED", "场景待从语义分镜确认"
    blob = re.sub(r"\s+", "", f"{section} {lyric_hint}").lower()
    scored = []
    for asset in locations:
        tokens = re.split(r"[/·、，,\s]+", f"{asset.get('name', '')} {asset.get('anchor', '')}".lower())
        score = sum(1 for token in tokens if len(token) >= 2 and token in blob)
        scored.append((score, asset))
    best = max(scored, key=lambda row: row[0])[1]
    return best.get("id"), best.get("name")


def shot_design_for(section, clip_id, key, energy_level, transition, lyric_hint, assets, aspect):
    loc_id, loc_name = section_location(section, lyric_hint, assets)
    if key:
        shot_size = "中近景/特写交替"
        angle = "低角度、正面或三分之二机位，服务段落爆点"
        camera = "快速推进、甩镜或半环绕，动作峰值压在确认重拍"
        lens = "35mm-50mm 电影感，近景可用 70mm 压缩背景"
        lighting = "继承段落色彩脚本，提高反差或光效脉冲但不更换主画风"
        blocking = "主体占视觉重心，动作线形成清晰方向，留出转场遮挡物"
        setup_group = f"{section}/high_energy/{loc_id}"
    else:
        shot_size = "远景/中景/近景按叙事推进"
        angle = "平视或轻低角度，保持人物稳定可认"
        camera = "缓慢推镜头、移镜头或稳定器跟拍，避免无意义绕圈"
        lens = "35mm-50mm 自然透视"
        lighting = "段落主色的戏剧光，保留脸部可读性"
        blocking = "人物动线从画面一侧进入或离开，接下一镜视线/动作方向"
        setup_group = f"{section}/story/{loc_id}"
    return {
        "shot_size": shot_size,
        "angle": angle,
        "camera_movement": camera,
        "lens_feel": lens,
        "blocking": blocking,
        "lighting": lighting,
        "location_id": loc_id,
        "location_name": loc_name,
        "setup_group": setup_group,
        "floorplan_hint": f"目标画幅 {aspect}：主体、面部、手部和关键道具不贴边；下方字幕安全区至少留 18%",
        "production_design": "服装、发型、关键道具和场景陈设沿同段 setup_group 连续；同一场景保持空间拓扑与时代质感",
        "take_intent": "关键镜至少两版挑动作/脸；叙事镜优先稳定和可剪",
        "color_grade": "继承视觉蓝图 palette_anchor 和 section_look；相邻镜曝光、白平衡和饱和度有意连续",
        "qc_notes": "检查身份、服装、手部、关键道具、空间方向、字幕安全区、动作峰值与重拍",
    }


def identity_contract_for(section, identity_registry):
    identities = identity_registry.get("identities") or []
    lead_id = identity_registry.get("lead_id")
    identity = next((x for x in identities if x.get("id") == lead_id), identities[0] if identities else {})
    states = [x for x in identity_registry.get("identity_states", []) if x.get("identity_id") == identity.get("id")]
    section_low = str(section).lower()
    state = next((x for x in states if str(x.get("name", "")).lower() in section_low), states[0] if states else {})
    return {
        "lead_id": identity.get("id") or "CHAR_UNSPECIFIED",
        "identity_state_id": state.get("state_id"),
        "lead_identity_anchor": state.get("anchor") or identity.get("anchor") or "身份锚点待补",
        "reference_group": identity.get("reference_group"),
        "wardrobe_props": [],
        "forbidden_drift": identity.get("forbidden_drift") or ["换脸", "换发型", "无依据换服装", "新增无关人物", "文字/logo/水印"],
    }


def reference_inputs_for(identity_contract, location_id, identity_registry):
    lead = next((x for x in identity_registry.get("identities", []) if x.get("id") == identity_contract.get("lead_id")), {})
    refs = [{"path": path, "use": "lead_identity"} for path in lead.get("reference_images", [])]
    if location_id and location_id != "LOC_UNSPECIFIED":
        refs.append({"asset_id": location_id, "use": "scene_anchor"})
    return refs


def cut_points_for_section(sec, downbeats, beats, meter, energy_map, profile, strategy):
    start, end = sec["start"], sec["end"]
    
    # Calculate average energy for this section to drive ASL curve
    avg_energy = 0.5
    if energy_map:
        relevant = energy_map[int(start):int(end)+1]
        if relevant:
            samples = [get_energy_at(i, energy_map) for i in range(int(start), int(end) + 1)]
            avg_energy = sum(samples) / len(samples) if samples else 0.5

    # Base bars from profile
    base_bars = profile["chorus_bars"] if is_chorus(sec["section"]) or strategy == "全程强卡点" else profile["verse_bars"]
    
    # Dynamic ASL: Higher energy -> lower bars (more frequent cuts)
    if avg_energy > 0.8:
        bars = 1
    elif avg_energy > 0.5:
        bars = max(1, base_bars // 2)
    elif avg_energy < 0.2:
        bars = base_bars * 2
    else:
        bars = base_bars

    in_range = [t for t in downbeats if start < t < end]
    stride = max(1, int(bars))
    if not in_range:
        # A sparse/missing downbeat grid may still have confirmed beat times.
        # Never invent 2s/4s cuts: use musical beat anchors or preserve the
        # signed section as one shot when no anchor exists inside it.
        in_range = [t for t in beats if start < t < end]
        stride = max(1, int(bars) * max(1, int(meter or 4)))
    if not in_range:
        return [round(start, 3), round(end, 3)]

    pts = [start]
    for idx, t in enumerate(in_range):
        if idx % stride == 0:
            pts.append(float(t))
    pts.append(end)
    # 去重并丢掉太短切点
    clean = []
    for p in sorted(set(round(x, 3) for x in pts)):
        if not clean or p - clean[-1] >= 0.5:
            clean.append(p)
    if clean[-1] != round(end, 3):
        clean.append(round(end, 3))
    return clean


def merge_to_limit(clips, max_clips):
    """Reduce task count without ever erasing a musical section boundary.

    The old pairwise recursion could merge the last clip of a verse with the
    first clip of a chorus.  ``max_clips`` is now a cost target, not authority
    to corrupt the signed music structure.
    """
    if len(clips) <= max_clips:
        return clips
    rows = [dict(row) for row in clips]
    while len(rows) > max_clips:
        candidates = [
            (float(left.get("duration") or 0) + float(right.get("duration") or 0), idx)
            for idx, (left, right) in enumerate(zip(rows, rows[1:]))
            if left.get("section") == right.get("section")
        ]
        if not candidates:
            break
        _cost, idx = min(candidates)
        cur, nxt = dict(rows[idx]), rows[idx + 1]
        cur["end"] = nxt["end"]
        cur["duration"] = round(float(cur["end"]) - float(cur["start"]), 3)
        cur["lyric_hint"] = " / ".join(
            value for value in (cur.get("lyric_hint"), nxt.get("lyric_hint")) if value
        )
        cur["energy_level"] = max(cur.get("energy_level", 5), nxt.get("energy_level", 5))
        rows[idx:idx + 2] = [cur]
    return rows


def seam_contract_for(current, following, key_cut):
    """Classify the outgoing edit seam so generation and review share intent."""
    if not following:
        return {
            "kind": "terminal",
            "transition_type": "cut",
            "continuity_required": False,
            "need_end_frame": False,
            "review": ["final_hold", "song_end"],
        }
    if current.get("section") != following.get("section"):
        return {
            "kind": "section_break",
            "transition_type": "beat_cut",
            "continuity_required": False,
            "need_end_frame": False,
            "expected_discontinuity": ["setup_or_palette_may_change"],
            "review": ["musical_boundary", "new_section_readability", "intentional_contrast"],
        }
    if key_cut:
        return {
            "kind": "beat_cut",
            "transition_type": "hard_cut",
            "continuity_required": False,
            "need_end_frame": False,
            "expected_discontinuity": ["pose_or_scale_may_jump_on_confirmed_beat"],
            "review": ["beat_hit", "identity", "color_intent"],
        }
    return {
        "kind": "match_action",
        "transition_type": "hard_cut",
        "continuity_required": True,
        "need_end_frame": True,
        "expected_discontinuity": [],
        "review": ["pose_phase", "motion_vector", "screen_direction", "eyeline", "prop_state", "lighting"],
    }


def build_clips(root, bg, sections, lyric_sections, granularity, strategy, visual_style,
                blueprint, identities, assets, aspect, aligned_lyrics=None):
    profile = contract.plan_granularity_profile(granularity)
    beats = [float(x) for x in (bg.get("beats") or [])]
    downbeats = [float(x) for x in (bg.get("downbeats") or [])]
    if not downbeats:
        downbeats = list(beats)
    try:
        meter = int(bg.get("meter") or 4)
    except (TypeError, ValueError):
        meter = 4
    energy_map = bg.get("energy_map")
    raw_clips = []
    aligned_lyrics = aligned_lyrics or []
    for sec in sections:
        pts = cut_points_for_section(sec, downbeats, beats, meter, energy_map, profile, strategy)
        for i in range(len(pts) - 1):
            start, end = pts[i], pts[i + 1]
            if end <= start:
                continue
            energy = get_energy_at(start, energy_map)
            energy_level = int(energy * 10) + 1
            energy_level = max(1, min(10, energy_level))
            
            raw_clips.append({
                "section": sec["section"],
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "energy_level": energy_level,
                "lyric_hint": lyric_hint_for_interval(start, end, aligned_lyrics),
                "lyric_timing_source": "alignment_report" if aligned_lyrics else "none",
            })
    raw_clips = merge_to_limit(raw_clips, profile["max_clips"])
    clips = []
    previous_end_state = ""
    previous_section = None
    screen_direction = "left_to_right"
    for idx, clip in enumerate(raw_clips, 1):
        clip_id = f"Clip_{idx:03d}"
        section = clip["section"]
        start, end = clip["start"], clip["end"]
        energy_level = clip["energy_level"]
        key = is_chorus(section) or is_bridge(section) or energy_level >= 8
        following = raw_clips[idx] if idx < len(raw_clips) else None
        seam_contract = seam_contract_for(clip, following, key)
        seam_contract["from_clip"] = clip_id
        seam_contract["to_clip"] = f"Clip_{idx + 1:03d}" if following else None
        transition = {
            "section_break": "段落切",
            "beat_cut": "卡点硬切",
            "match_action": "动作匹配切",
            "terminal": "收束",
        }[seam_contract["kind"]]
        beat_role = "key" if key else "normal"
        # Preserve motion cadence by default.  Editorial fills a short source by
        # holding the final stable frames; retiming is an explicit exception.
        speed_mode = "trim_hold"
        
        # Action peak must bind to a musical anchor inside the locked clip.
        desired_peak = round(start + (end - start) * 0.8, 3)
        in_clip_downbeats = [value for value in downbeats if start <= value <= end]
        in_clip_beats = [value for value in beats if start <= value <= end]
        anchors = in_clip_downbeats or in_clip_beats
        anchor_kind = "downbeat" if in_clip_downbeats else ("beat" if in_clip_beats else "section_boundary")
        beat_anchor = nearest_downbeat(desired_peak, anchors)
        if beat_anchor is None:
            beat_anchor = nearest_downbeat(desired_peak, [start, end])
        action_peak_abs = round(beat_anchor, 3)
        action_peak_relative = round(action_peak_abs - start, 3)
        
        action_family = "performance_peak/visual_burst" if key else "performance_pose/narrative_action"
        action = f"力量等级 Level {energy_level}；段落高光动作/视觉爆点对齐确认重拍" if key else f"力量等级 Level {energy_level}；叙事或表演动作完整推进，镜头克制"
        transition_motif = "光效切/whip pan/动作匹配切" if key else "动作切/视线切/构图匹配切"
        visual_motif = blueprint_value(blueprint, "motif_ledger", "继承视觉蓝图的身份锚点、段落主色和反复视觉母题")
        end_state = f"{section} 段 {clip_id} 结束姿态，画面重心留给下一刀"
        start_state = previous_end_state or f"{section} 段首帧，继承视觉蓝图和定妆锚点"
        if previous_section != section:
            screen_direction = "left_to_right"
        previous_section = section
        previous_end_state = end_state
        shot_design = shot_design_for(section, clip_id, key, energy_level, transition, clip.get("lyric_hint", ""), assets, aspect)
        identity_contract = identity_contract_for(section, identities)
        reference_inputs = reference_inputs_for(identity_contract, shot_design["location_id"], identities)
        asset_ids = [x for x in (shot_design["location_id"],) if x and x != "LOC_UNSPECIFIED"]
        image_prompt = f"出图/段落/prompt/{clip_id}.md"
        video_prompt = f"出视频/prompt/{clip_id}.md"
        clips.append({
            "clip_id": clip_id,
            "section": section,
            "start": start,
            "end": end,
            "duration": clip["duration"],
            "energy_level": f"Level {energy_level}",
            "beat_role": beat_role,
            "speed_mode": speed_mode,
            "action_family": action_family,
            "action_peak": action_peak_abs,
            "action_peak_relative": action_peak_relative,
            "action_peak_anchor": beat_anchor,
            "action_peak_anchor_kind": anchor_kind,
            "action_peak_downbeat": beat_anchor if anchor_kind == "downbeat" else None,
            "transition_motif": transition_motif,
            "seam_contract": seam_contract,
            "visual_motif": visual_motif,
            "lyric_hint": clip.get("lyric_hint", ""),
            "vocal_lyrics": clip.get("lyric_hint", ""),
            "lyric_timing_source": clip.get("lyric_timing_source", "none"),
            "shot_design": shot_design,
            "identity_contract": identity_contract,
            "reference_inputs": reference_inputs,
            "identity_ids": [identity_contract["lead_id"]],
            "asset_ids": asset_ids,
            "image_prompt_path": image_prompt,
            "video_prompt_path": video_prompt,
            "image_path": f"出图/段落/图片/{clip_id}.png",
            "end_frame_path": f"出图/段落/图片/{clip_id}_end.png",
            "need_end_frame": seam_contract["need_end_frame"],
            "selected_video_path": f"出视频/视频/{clip_id}.mp4",
            "transition": transition,
            "visual_style": visual_style,
            "continuity": {
                "start_state": start_state,
                "action": action,
                "end_state": end_state,
                "identity_state": identity_contract.get("identity_state_id") or identity_contract.get("lead_id"),
                "wardrobe_state": "继承身份状态卡；变化需显式写入 clip 合同",
                "prop_state": "继承上一镜关键道具、持握手和开合/损伤状态",
                "scene_topology": f"继承 {shot_design['setup_group']} 的入口、主体、背景层次和关键陈设位置",
                "screen_direction": screen_direction,
                "eyeline": "承接上一镜视线目标；反打时显式标记轴线变化",
                "motion_vector": "动作速度和方向承接上一镜尾帧，峰值后保留稳定落幅",
                "lighting_state": shot_design["lighting"],
                "outgoing_seam": seam_contract,
                "end_frame_target": (
                    f"出图/段落/图片/Clip_{idx + 1:03d}.png"
                    if seam_contract["need_end_frame"] else ""
                ),
                "constraints": "同一段落保持身份状态、服装发型、主色调、光线、关键道具、空间拓扑和屏幕方向一致",
                "negative": "不要换脸、不要无依据换衣、不要新增人物、不要改变场景拓扑、不要生成文字/logo/水印、不要生成原生人声",
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
            f"动作家族：{clip.get('action_family', '')}；力量等级：{clip.get('energy_level', 'Level 5')}；动作峰值：{clip.get('action_peak_relative', 0.8):.2f}s (relative)。",
            f"视觉母题：{clip.get('visual_motif', '')}。",
            "",
            "## 导演合约",
            f"- 景别：{clip['shot_design']['shot_size']}",
            f"- 机位：{clip['shot_design']['angle']}",
            f"- 运镜：{clip['shot_design']['camera_movement']}",
            f"- 焦段感：{clip['shot_design']['lens_feel']}",
            f"- 走位/构图：{clip['shot_design']['blocking']}",
            f"- 光影：{clip['shot_design']['lighting']}",
            f"- 场景 setup：{clip['shot_design']['setup_group']}",
            f"- 字幕安全区：{clip['shot_design']['floorplan_hint']}",
            "",
            "## 一致性锚点",
            f"- 身份锚点(lead_identity_anchor)：{clip['identity_contract']['lead_identity_anchor']}",
            f"- 参考输入(reference_inputs)：{', '.join(str(x.get('path') or x.get('asset_id')) for x in clip.get('reference_inputs', []))}",
            f"- 视觉锚点(global_style/palette_anchor)：{clip['visual_style']}；按视觉蓝图 palette_anchor/section_look 变化",
            f"- 禁止漂移(forbidden_drift)：{', '.join(clip['identity_contract']['forbidden_drift'])}",
            "",
            "## 继承",
            clip["continuity"]["constraints"],
            "",
            "## 负向",
            clip["continuity"]["negative"],
        ]
        if clip.get("need_end_frame"):
            image_lines.extend([
                "",
                "## 尾帧接力（必做）",
                f"- 输出：`{clip['end_frame_path']}`",
                f"- 对齐下一镜首帧：`{clip['continuity'].get('end_frame_target', '')}`",
                "- 尾帧必须保持同一身份/服化道/道具/场景拓扑，并把姿态相位、运动方向、视线和光线交给下一镜；不得只复制首帧。",
            ])
        mv_utils.write_text(os.path.join(root, clip["image_prompt_path"]), "\n".join(image_lines) + "\n")
        video_lines = [
            f"# {clip['clip_id']} 视频任务",
            "",
            f"- 首帧：`{clip['image_path']}`",
            f"- 时长：{clip['duration']:.2f}s",
            f"- 卡点：{clip['start']:.2f}s → {clip['end']:.2f}s",
            f"- 转场：{clip['transition']}",
            f"- 接缝类型：{clip.get('seam_contract', {}).get('kind', '')}",
            f"- 连续性要求：{clip.get('seam_contract', {}).get('continuity_required', False)}",
            f"- 动作家族：{clip.get('action_family', '')}",
            f"- 力量等级：{clip.get('energy_level', 'Level 5')}",
            f"- 动作峰值：{clip.get('action_peak_relative', 0.8):.2f}s (relative)",
            f"- 动作峰值重拍：{clip.get('action_peak_downbeat')}",
            f"- 转场母题：{clip.get('transition_motif', '')}",
            f"- 景别：{clip['shot_design']['shot_size']}",
            f"- 运镜：{clip['shot_design']['camera_movement']}",
            f"- 光影：{clip['shot_design']['lighting']}",
            f"- 参考输入：{', '.join(str(x.get('path') or x.get('asset_id')) for x in clip.get('reference_inputs', []))}",
            "",
            "## continuity",
            f"- start_state：{clip['continuity']['start_state']}",
            f"- action：{clip['continuity']['action']}",
            f"- end_state：{clip['continuity']['end_state']}",
            f"- constraints：{clip['continuity']['constraints']}",
            f"- negative：{clip['continuity']['negative']}",
            f"- identity_state：{clip['continuity']['identity_state']}",
            f"- wardrobe_state：{clip['continuity']['wardrobe_state']}",
            f"- prop_state：{clip['continuity']['prop_state']}",
            f"- scene_topology：{clip['continuity']['scene_topology']}",
            f"- screen_direction：{clip['continuity']['screen_direction']}",
            f"- eyeline：{clip['continuity']['eyeline']}",
            f"- motion_vector：{clip['continuity']['motion_vector']}",
            f"- lighting_state：{clip['continuity']['lighting_state']}",
            f"- outgoing_seam：{json.dumps(clip.get('seam_contract') or {}, ensure_ascii=False)}",
            f"- end_frame_target：{clip['continuity'].get('end_frame_target', '')}",
            "",
            "## 视频 prompt",
            f"人物运动：{clip['continuity']['action']}；动作家族：{clip.get('action_family', '')}；力量等级：{clip.get('energy_level', 'Level 5')}；镜头运动：{clip['shot_design']['camera_movement']}；光影继承：{clip['shot_design']['lighting']}；动态细节遵循人物、服装、道具和环境的物理惯性；卡点约束：动作峰值/击中点对齐本 clip 内部的 {clip.get('action_peak_relative', 0.8):.2f}s；接缝执行：{clip.get('seam_contract', {}).get('kind', '')}，连续性要求={clip.get('seam_contract', {}).get('continuity_required', False)}，复核 {', '.join(clip.get('seam_contract', {}).get('review') or [])}；转场母题：{clip.get('transition_motif', '')}；继承约束：不得重定身份、服装、关键道具、场景 setup、空间方向或光色基调；声音约束：无对白、无旁白、不要生成原生人声，音乐由 mv-compose 使用原歌轨统一处理。",
        ]
        mv_utils.write_text(os.path.join(root, clip["video_prompt_path"]), "\n".join(video_lines) + "\n")


def build_markdown(title, clips):
    lines = [f"# MV clip plan — {title}", "", "| Clip | 段落 | 时间 | 时长 | 景别/运镜 | 转场 | 歌词钩子 |", "|---|---|---:|---:|---|---|---|"]
    for c in clips:
        shot = c.get("shot_design", {})
        lines.append(f"| {c['clip_id']} | {c['section']} | {c['start']:.2f}-{c['end']:.2f}s | {c['duration']:.2f}s | {shot.get('shot_size','')} / {shot.get('camera_movement','')} | {c['transition']} | {c.get('lyric_hint','')} |")
    lines.extend(["", "## 下一步", "1. mv-image 按 image_prompt_path 出首帧。", "2. mv-video/scripts/video_jobs.py 生成视频任务包。", "3. mv-compose 按 timeline_manifest.json 合成。"])
    return "\n".join(lines) + "\n"


def quantized_timeline_rows(clips, rate):
    """Create an integer-frame edit timeline with contiguous cut boundaries."""
    if not clips:
        return []
    rate = max(1, int(rate))
    rows = []
    cursor = int(math.floor(float(clips[0]["start"]) * rate + 0.5))
    for index, clip in enumerate(clips):
        target_end = int(math.floor(float(clip["end"]) * rate + 0.5))
        if index == len(clips) - 1:
            target_end = int(math.floor(float(clips[-1]["end"]) * rate + 0.5))
        end_frame = max(cursor + 1, target_end)
        rows.append({
            "clip_id": clip["clip_id"],
            "section": clip["section"],
            "start": round(cursor / rate, 6),
            "end": round(end_frame / rate, 6),
            "duration": round((end_frame - cursor) / rate, 6),
            "start_frame": cursor,
            "end_frame": end_frame,
            "duration_frames": end_frame - cursor,
            "video_path": clip["selected_video_path"],
            "transition": clip["transition"],
            "speed_mode": clip["speed_mode"],
            "seam_contract": clip.get("seam_contract") or {},
        })
        cursor = end_frame
    return rows


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
    errors, warnings = mv_gate.check(root, "plan")
    for msg in warnings:
        print(f"[warn] {msg}")
    if errors:
        for msg in errors:
            print(f"[err] {msg}", file=sys.stderr)
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
    aspect = settings.get("合成画幅") or meta.get("aspect") or "16:9"
    blueprint = mv_utils.read_text(os.path.join(root, "视觉蓝图.md"))
    identities = registry.build_identity_registry(root)
    assets = registry.build_asset_registry(root)
    lyric_sections = parse_lyrics(root)
    aligned_lyrics, alignment_report = alignment_lines(root)
    sections = normalize_sections(bg, meta, lyric_sections)
    clips = build_clips(root, bg, sections, lyric_sections, granularity, strategy, visual_style,
                        blueprint, identities, assets, aspect, aligned_lyrics=aligned_lyrics)
    if not clips:
        print("[err] 未生成任何 clip，请检查 beatgrid duration/sections", file=sys.stderr)
        sys.exit(1)
    write_prompt_files(root, clips, blueprint)
    song_path = mv_utils.find_song(root)
    upstream_paths = {
        "song": song_path,
        "beatgrid": bg_path,
        "lyrics": os.path.join(root, "词", "lyrics.md"),
        "blueprint": os.path.join(root, "视觉蓝图.md"),
        "alignment": os.path.join(root, "字幕", "alignment_report.json"),
    }
    plan = {
        "schema_version": 3,
        "kind": "mv_clip_plan",
        "generated_at": date.today().isoformat(),
        "root_rel": ".",
        "title": title,
        "granularity": granularity,
        "strategy": strategy,
        "visual_style": visual_style,
        "production_bible": {
            "identity_registry": "设定/identity_registry.json",
            "asset_registry": "设定/asset_registry.json",
            "reference_plan": "分镜/reference_plan.json",
            "director_contract_fields": [
                "shot_size", "angle", "camera_movement", "lens_feel", "blocking",
                "lighting", "setup_group", "floorplan_hint", "production_design",
            ],
            "consistency_rule": "首帧锁身份/场景/光色；视频阶段只升级动作、运镜、张力，不重定脸和服化道",
        },
        "beatgrid_path": "节拍/beatgrid.json",
        "section_contract": {
            "source": bg.get("section_source") or "unconfirmed",
            "verified": bool(bg.get("sections_verified")),
            "complete": bool(bg.get("sections_complete")),
            "sections": sections,
        },
        "planning_warnings": (
            [f"max_clips={contract.plan_granularity_profile(granularity)['max_clips']} 是成本目标；为保护段落边界，实际保留 {len(clips)} clips"]
            if len(clips) > contract.plan_granularity_profile(granularity)["max_clips"] else []
        ),
        # Stage-scoped inputs avoid invalidating picture lock when a release-only
        # setting or the human-readable settings history changes.
        "inputs_sha256": {
            **{key: mv_utils.content_hash(path) for key, path in upstream_paths.items()},
            "settings_plan": contract.plan_settings_digest(settings),
        },
        "lyric_timing": {
            "source": "alignment_report" if aligned_lyrics else "none",
            "line_count": len(aligned_lyrics),
            "report_kind": (alignment_report or {}).get("kind"),
            "degraded": not bool(aligned_lyrics),
        },
        # Legacy aliases retained for older readers.
        "beatgrid_hash": mv_utils.content_hash(bg_path),
        "song_hash": mv_utils.content_hash(song_path),
        "clips": clips,
    }
    plan_dir = os.path.join(root, "分镜")
    plan_path = os.path.join(plan_dir, "clip_plan.json")
    # 幂等写盘：同输入重跑（隔天亦然）不得只因 generated_at 变化就换 hash——
    # clip_plan hash 被 timeline/semantic/picture_lock/jobs_manifest 全链绑定。
    mv_utils.write_json_stable(plan_path, plan)
    try:
        output_rate = contract.video_spec_profile(settings.get("出视频规格") or "预算一般")["fps"]
    except KeyError:
        output_rate = 24
    timeline = {
        "schema_version": 3,
        "kind": "mv_timeline_manifest",
        "generated_at": date.today().isoformat(),
        "root_rel": ".",
        "title": title,
        "song_path": mv_utils.relpath(root, song_path) if song_path else "",
        "rate": output_rate,
        "audio_policy": "locked_master_song_only; generated_clip_audio_discarded",
        "beatgrid_path": "节拍/beatgrid.json",
        "source_clip_plan_sha256": mv_utils.content_hash(plan_path),
        "timebase": {"rate": int(output_rate), "unit": "frame", "quantized": True},
        "clips": quantized_timeline_rows(clips, output_rate),
    }
    mv_utils.write_json_stable(os.path.join(plan_dir, "timeline_manifest.json"), timeline)
    mv_utils.write_text(os.path.join(plan_dir, "clip_plan.md"), build_markdown(title, clips))
    # Rebuild registries after clip_plan exists so asset/reference usage reflects this exact plan.
    identities = registry.build_identity_registry(root)
    assets = registry.build_asset_registry(root)
    refs = registry.build_reference_plan(root, identities, assets)
    requirements = registry.build_reference_requirements(root, identities, assets, refs)
    mv_utils.write_json_stable(os.path.join(root, "设定", "identity_registry.json"), identities)
    mv_utils.write_json_stable(os.path.join(root, "设定", "asset_registry.json"), assets)
    mv_utils.write_json_stable(os.path.join(root, "分镜", "reference_plan.json"), refs)
    registry.write_reference_requirements(root, requirements)
    mv_utils.update_progress_stage(root, "plan")
    print(f"[ok] clip plan → {os.path.join(plan_dir, 'clip_plan.json')}（{len(clips)} clips）")
    print(f"[ok] timeline → {os.path.join(plan_dir, 'timeline_manifest.json')}")
    print("\n[推荐下一步] 你可以运行语义分镜引擎，根据歌词和蓝图自动补全画面提示词：")
    print(f"             python3 skills/mv/mv-plan/scripts/compose_prompts.py {root}")


if __name__ == "__main__":
    main()
