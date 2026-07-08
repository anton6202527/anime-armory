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
GATE_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "gate.py")


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

contract = load_contract()
mv_utils = load_mv_utils()
mv_gate = load_gate()

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


def get_energy_at(t, energy_map):
    if not energy_map:
        return 0.5
    idx = int(t)
    if idx < 0: return energy_map[0]
    if idx >= len(energy_map): return energy_map[-1]
    return energy_map[idx]


def nearest_downbeat(t, downbeats):
    if not downbeats:
        return None
    return min((float(x) for x in downbeats), key=lambda x: abs(x - t))


def section_location(section, lyric_hint=""):
    blob = f"{section} {lyric_hint}".lower()
    if any(k in blob for k in ("intro", "山门", "石阶", "pre")):
        return ("LOC_MOUNTAIN_GATE", "山门石阶")
    if any(k in blob for k in ("chorus", "副歌", "仗剑", "山高", "水远")):
        return ("LOC_CLOUD_SEA", "云海/山巅")
    if any(k in blob for k in ("verse2", "客栈", "灯", "酒")):
        return ("LOC_INN", "江湖客栈")
    if any(k in blob for k in ("bridge", "竹林", "多年")):
        return ("LOC_BAMBOO_FOREST", "竹林")
    if any(k in blob for k in ("月", "伤", "雪", "荒野")):
        return ("LOC_SNOWFIELD", "雪原/月下荒野")
    return ("LOC_MOUNTAIN_GATE", "山门石阶")


def shot_design_for(section, clip_id, key, energy_level, transition, lyric_hint):
    loc_id, loc_name = section_location(section, lyric_hint)
    if key:
        shot_size = "中近景/特写交替"
        angle = "低角度或荷兰角，服务副歌爆点"
        camera = "快推、轻甩或半环绕，动作峰值压在重拍"
        lens = "35mm-50mm 电影感，近景可用 70mm 压缩背景"
        lighting = "逆光+冷青剑光，副歌光效随鼓点脉冲"
        blocking = "主角占画面中轴，剑/衣袂形成对角线，留出转场遮挡物"
        setup_group = f"{section}/high_energy/{loc_id}"
    else:
        shot_size = "远景/中景/近景按叙事推进"
        angle = "平视或轻低角度，保持人物稳定可认"
        camera = "缓推、横移或跟拍，避免无意义绕圈"
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
        "floorplan_hint": "竖屏 9:16：主体头部不贴边，字幕安全区留在下 18%，剑尖/手部不出框",
        "production_design": "服装、长剑、场景陈设沿同段 setup_group 连续；同一场景不换时代质感",
        "take_intent": "关键镜至少两版挑动作/脸；叙事镜优先稳定和可剪",
        "color_grade": "青白墨为底，按段落加暖灯/冷蓝；相邻镜过渡不突变",
        "qc_notes": "检查脸、手、剑、衣服、字幕安全区、动作峰值与重拍",
    }


def identity_contract_for(section):
    adult = "bridge" in str(section).lower() or "桥" in str(section)
    return {
        "lead_id": "CHAR_LEAD_ADULT" if adult else "CHAR_LEAD_YOUNG",
        "lead_identity_anchor": "鬓染霜、白袍泛旧、眼神沉静，仍背同一柄青锋长剑" if adult else "白衣束发玄发带·眉目清俊倔强眼·背青锋墨鞘长剑·玄色腰穗",
        "reference_group": "REF_LEAD_ADULT" if adult else "REF_LEAD_YOUNG",
        "wardrobe_props": ["月白/白色武袍", "玄色腰穗", "青锋长剑"],
        "forbidden_drift": ["换脸", "换发型", "换主服装", "新增无关人物", "文字/logo/水印", "现代物件"],
    }


def reference_inputs_for(section, location_id):
    refs = [
        {"path": "出图/共享/图片/定妆_少年_常态.png", "use": "lead_identity"},
        {"asset_id": location_id, "use": "scene_anchor"},
        {"asset_id": "PROP_QINGFENG_SWORD", "use": "prop_anchor"},
    ]
    if "bridge" in str(section).lower():
        refs[0] = {"asset_id": "CHAR_LEAD_ADULT", "use": "adult_variant_planned"}
    return refs


def cut_points_for_section(sec, downbeats, energy_map, profile, strategy):
    start, end = sec["start"], sec["end"]
    
    # Calculate average energy for this section to drive ASL curve
    avg_energy = 0.5
    if energy_map:
        relevant = energy_map[int(start):int(end)+1]
        if relevant:
            avg_energy = sum(relevant) / len(relevant)

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
    if not in_range:
        # Fallback to fixed interval if no downbeats
        interval = 2.0 if avg_energy > 0.6 else 4.0
        pts = [start]
        cur = start + interval
        while cur < end:
            pts.append(round(cur, 3))
            cur += interval
        pts.append(end)
        return pts

    pts = [start]
    for idx, t in enumerate(in_range):
        if idx % max(1, int(bars)) == 0:
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
            # Recalculate energy level for merged clip
            cur["energy_level"] = max(cur.get("energy_level", 5), nxt.get("energy_level", 5))
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
    energy_map = bg.get("energy_map")
    raw_clips = []
    lyric_index_by_section = {}
    for sec in sections:
        pts = cut_points_for_section(sec, downbeats, energy_map, profile, strategy)
        for i in range(len(pts) - 1):
            start, end = pts[i], pts[i + 1]
            if end <= start:
                continue
            idx = lyric_index_by_section.get(sec["section"], 0)
            lyric_index_by_section[sec["section"]] = idx + 1
            
            energy = get_energy_at(start, energy_map)
            energy_level = int(energy * 10) + 1
            energy_level = max(1, min(10, energy_level))
            
            raw_clips.append({
                "section": sec["section"],
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "energy_level": energy_level,
                "lyric_hint": lyric_hint_for(sec["section"], lyric_sections, idx),
            })
    raw_clips = merge_to_limit(raw_clips, profile["max_clips"])
    clips = []
    previous_end_state = ""
    for idx, clip in enumerate(raw_clips, 1):
        clip_id = f"Clip_{idx:03d}"
        section = clip["section"]
        start, end = clip["start"], clip["end"]
        energy_level = clip["energy_level"]
        key = is_chorus(section) or is_bridge(section) or energy_level >= 8
        transition = "卡点硬切" if key else "动作切"
        beat_role = "key" if key else "normal"
        speed_mode = "trim" if key else "warp"
        
        # Action Peak logic: Try to find a beat within the second half of the clip
        # Fallback to 80% through the clip
        action_peak_abs = round(end - min(0.2, max(0.05, (end - start) * 0.2)), 3)
        beat_anchor = nearest_downbeat(action_peak_abs, downbeats)
        action_peak_relative = round(action_peak_abs - start, 3)
        
        action_family = "dance_hit/vfx_burst" if key else "performance_pose/expressive_walk"
        action = f"力量等级 Level {energy_level}；副歌高光动作/光效爆点对齐击中点" if key else f"力量等级 Level {energy_level}；叙事动作完整推进，镜头缓推"
        transition_motif = "光效切/whip pan" if key else "动作切/视线切"
        visual_motif = "继承视觉蓝图的主角身份锚点、段落主色和本段反复母题"
        end_state = f"{section} 段 {clip_id} 结束姿态，画面重心留给下一刀"
        start_state = previous_end_state or f"{section} 段首帧，继承视觉蓝图和定妆锚点"
        previous_end_state = end_state
        shot_design = shot_design_for(section, clip_id, key, energy_level, transition, clip.get("lyric_hint", ""))
        identity_contract = identity_contract_for(section)
        reference_inputs = reference_inputs_for(section, shot_design["location_id"])
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
            "action_peak_downbeat": beat_anchor,
            "transition_motif": transition_motif,
            "visual_motif": visual_motif,
            "lyric_hint": clip.get("lyric_hint", ""),
            "shot_design": shot_design,
            "identity_contract": identity_contract,
            "reference_inputs": reference_inputs,
            "asset_ids": [shot_design["location_id"], "PROP_QINGFENG_SWORD", "VFX_SWORD_LIGHT"],
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
            f"- 视觉锚点(global_style/palette_anchor)：{clip['visual_style']}；青、白、墨为底，按段落光色变化",
            f"- 禁止漂移(forbidden_drift)：{', '.join(clip['identity_contract']['forbidden_drift'])}",
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
            "",
            "## 视频 prompt",
            f"人物运动：{clip['continuity']['action']}；动作家族：{clip.get('action_family', '')}；力量等级：{clip.get('energy_level', 'Level 5')}；镜头运动：{clip['shot_design']['camera_movement']}；光影继承：{clip['shot_design']['lighting']}；动态细节：发丝、衣摆、光斑或环境粒子随节拍产生物理惯性偏移；卡点约束：动作峰值/击中点对齐本 clip 内部的 {clip.get('action_peak_relative', 0.8):.2f}s；转场母题：{clip.get('transition_motif', '')}；继承约束：不得重定脸、服装、长剑、场景 setup、光色基调；声音约束：无对白、无旁白、不要生成原生人声，音乐由 mv-compose 使用原歌轨统一处理。",
        ]
        mv_utils.write_text(os.path.join(root, clip["video_prompt_path"]), "\n".join(video_lines) + "\n")


def build_markdown(title, clips):
    lines = [f"# MV clip plan — {title}", "", "| Clip | 段落 | 时间 | 时长 | 景别/运镜 | 转场 | 歌词钩子 |", "|---|---|---:|---:|---|---|---|"]
    for c in clips:
        shot = c.get("shot_design", {})
        lines.append(f"| {c['clip_id']} | {c['section']} | {c['start']:.2f}-{c['end']:.2f}s | {c['duration']:.2f}s | {shot.get('shot_size','')} / {shot.get('camera_movement','')} | {c['transition']} | {c.get('lyric_hint','')} |")
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
        # 内容快照：下游 gate 用它判定换歌/重算 beatgrid 后 clip_plan 是否过期（git-free 失效检测）。
        "beatgrid_hash": mv_utils.content_hash(bg_path),
        "song_hash": mv_utils.content_hash(mv_utils.find_song(root)),
        "clips": clips,
    }
    song_path = mv_utils.find_song(root)
    timeline = {
        "schema_version": 1,
        "kind": "mv_timeline_manifest",
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "title": title,
        "song_path": mv_utils.relpath(root, song_path) if song_path else "",
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
    mv_utils.update_progress_stage(root, "plan")
    print(f"[ok] clip plan → {os.path.join(plan_dir, 'clip_plan.json')}（{len(clips)} clips）")
    print(f"[ok] timeline → {os.path.join(plan_dir, 'timeline_manifest.json')}")
    print("\n[推荐下一步] 你可以运行语义分镜引擎，根据歌词和蓝图自动补全画面提示词：")
    print(f"             python3 skills/mv-plan/scripts/compose_prompts.py {root}")


if __name__ == "__main__":
    main()
