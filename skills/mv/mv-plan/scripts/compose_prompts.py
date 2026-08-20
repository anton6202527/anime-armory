#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic Prompt Composer for MV pipeline.

Reads the clip_plan.json, lyrics.md, and 视觉蓝图.md, and generates semantic
prompts (action, camera, state) for each clip using an LLM integration.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CRAFT_SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "mv-craft", "scripts"))
if CRAFT_SCRIPTS not in sys.path:
    sys.path.insert(0, CRAFT_SCRIPTS)
import mv_utils
import completion

REQUIRED_SEMANTIC_FIELDS = (
    "clip_id",
    "start_state",
    "action_family",
    "energy_level",
    "action",
    "action_peak_relative",
    "end_state",
    "camera",
    "lighting",
    "visual_motif",
    "transition_motif",
    "screen_direction",
    "eyeline",
    "prop_state",
    "scene_topology",
    "motion_vector",
)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def file_sha256(path):
    if not path or not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_composer_prompt(clips, blueprint, lyrics):
    clip_summaries = []
    for c in clips:
        lyric = c.get('lyric_hint') or '无'
        clip_summaries.append(
            f"Clip ID: {c['clip_id']} | 时间: {c['start']}-{c['end']}s | 时长: {c['duration']}s | 段落: {c['section']} | 动作家族建议: {c.get('action_family', '')} | 能量等级: {c.get('energy_level', '')} | 景别: {(c.get('shot_design') or {}).get('shot_size', '')} | 运镜: {(c.get('shot_design') or {}).get('camera_movement', '')} | 歌词参考: {lyric}"
        )
        
    return f"""# MV 分镜语义补全任务

请作为专业 MV 导演，为以下分镜规划具体的画面内容（人物动作、场景状态、运镜）。

## 视觉蓝图与设定
{blueprint[:2000]}

## 歌词参考
{lyrics[:1500]}

## 待补全的 Clip 列表
{chr(10).join(clip_summaries)}

## 任务要求
请根据每个 Clip 的时长、所属段落（Verse/Chorus）和对应的歌词，设计具体的画面表现。
- **动态对口型 (Dynamic Lip-Sync)**：如果 Clip 的动作家族是 `performance_vocal`，必须在 `action` 中明确指出人物正在演唱的具体歌词（参考“歌词参考”列），并在 `vocal_lyrics` 字段填入该片段。
- **色彩剧本 (Color Script)**：参考“视觉蓝图”中的色彩剧本定义，为每个 Clip 设定符合段落氛围的 `lighting`。副歌应有更强烈的灯光律动。
- **剪辑张力**：副歌（Chorus）通常节奏快，适合环绕、快速切入，动作幅度大；主歌（Verse）注重氛围和情绪铺垫。
- **动作设计**：参考 mv-video/references/action_knowledge.md 和 mv-video/references/dance_choreography.md。一 clip 一个主动作，动作峰值对齐音乐重拍。
- **力量等级**：根据段落张力分配 Level 1-10 的能量。

输出 JSON 格式，严格包含所有传入的 Clip ID，结构如下：
{{
  "generator": {{"model": "具体模型名", "version": "具体版本"}},
  "clips": [
    {{
      "clip_id": "Clip_001",
      "start_state": "画面开始时的场景和人物状态",
      "action_family": "动作家族，如 dance_hit/performance_vocal/expressive_walk",
      "energy_level": "力量等级 Level 1-10",
      "action": "人物在此期间的具体动作。若是演唱，格式为：[演唱神态]并演唱歌词“[具体歌词片段]”",
      "vocal_lyrics": "具体演唱的歌词片段 (仅当 action_family 为 performance_vocal 时填写)",
      "action_peak_relative": "动作峰值相对于本 clip 开始的秒点（如 0.8s），应严格对齐音乐重拍",
	      "end_state": "动作结束时的状态",
	      "shot_size": "景别，如远景/中景/特写/大特写",
	      "angle": "机位角度，如低角度/平视/荷兰角",
	      "camera": "运镜方式（如：缓慢推进、跟随镜头、固定特写）",
	      "lens_feel": "焦段感，如 35mm 自然透视 / 70mm 压缩背景",
	      "blocking": "主体走位和画面重心",
	      "lighting": "光影氛围（如：逆光剪影、红蓝霓虹律动），需符合色彩剧本",
	      "visual_motif": "本 clip 继承或强化的视觉母题",
	      "transition_motif": "转场母题，如 光效切/遮挡擦镜/动作切",
      "screen_direction": "主体运动方向，如 left_to_right",
      "eyeline": "视线目标与反打轴线",
      "prop_state": "关键道具、持握手和状态",
      "scene_topology": "入口、主体、背景和陈设空间关系",
      "motion_vector": "动作速度、方向和相位承接"
    }}
  ]
}}
	"""


def parse_seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().lower().replace("seconds", "").replace("second", "").replace("s", "")
    return float(text)


def validate_semantic_data(plan, semantic_data, allow_partial=False):
    if not isinstance(semantic_data, dict) or not isinstance(semantic_data.get("clips"), list):
        return ["语义 JSON 必须是对象，且包含 clips 数组"]
    plan_clips = plan.get("clips") or []
    plan_ids = [c.get("clip_id") for c in plan_clips]
    sem_clips = semantic_data.get("clips") or []
    sem_ids = [c.get("clip_id") for c in sem_clips if isinstance(c, dict)]
    errors = []
    generator = semantic_data.get("generator") if isinstance(semantic_data, dict) else None
    if not isinstance(generator, dict) or not str(generator.get("model") or "").strip() \
            or not str(generator.get("version") or "").strip():
        errors.append("语义 JSON 缺 generator.model/version，不能审计由哪个具体模型生成")
    missing = [cid for cid in plan_ids if cid not in sem_ids]
    extra = [cid for cid in sem_ids if cid not in plan_ids]
    if missing and not allow_partial:
        errors.append(f"语义 JSON 缺 {len(missing)} 个 clip：{missing[:5]}")
    if extra:
        errors.append(f"语义 JSON 含 clip_plan 之外的 clip：{extra[:5]}")
    plan_by_id = {c.get("clip_id"): c for c in plan_clips}
    for row in sem_clips:
        if not isinstance(row, dict):
            errors.append("clips[] 必须是对象")
            continue
        cid = row.get("clip_id")
        if cid not in plan_by_id:
            continue
        missing_fields = [k for k in REQUIRED_SEMANTIC_FIELDS if row.get(k) in (None, "")]
        if missing_fields:
            errors.append(f"{cid} 缺字段：{', '.join(missing_fields)}")
        try:
            peak = parse_seconds(row.get("action_peak_relative"))
            dur = float(plan_by_id[cid].get("duration") or 0)
            if peak < 0 or (dur and peak > dur + 0.05):
                errors.append(f"{cid} action_peak_relative={peak} 超出 clip 时长 {dur}")
            anchor = plan_by_id[cid].get("action_peak_anchor", plan_by_id[cid].get("action_peak_downbeat"))
            start = plan_by_id[cid].get("start")
            if anchor is not None and start is not None:
                expected = float(anchor) - float(start)
                if abs(peak - expected) > 0.08:
                    errors.append(
                        f"{cid} action_peak_relative={peak} 未对齐已签收音乐锚点 {expected:.3f}s（容差80ms）"
                    )
        except (TypeError, ValueError):
            errors.append(f"{cid} action_peak_relative 不是秒数：{row.get('action_peak_relative')}")
        if row.get("action_family") == "performance_vocal":
            expected_lyrics = str(plan_by_id[cid].get("vocal_lyrics") or "").strip()
            actual_lyrics = str(row.get("vocal_lyrics") or "").strip()
            if not expected_lyrics:
                errors.append(f"{cid} 无对齐歌词区间，不得声明 performance_vocal")
            elif actual_lyrics != expected_lyrics:
                errors.append(f"{cid} vocal_lyrics 必须逐字继承对齐区间，不能由语义模型改写")
    return errors


def ensure_shot_design(clip):
    if not isinstance(clip.get("shot_design"), dict):
        clip["shot_design"] = {}
    return clip["shot_design"]


def apply_prompts(root, plan, semantic_data, allow_partial=False, assessment_path=None):
    validation_errors = validate_semantic_data(plan, semantic_data, allow_partial=allow_partial)
    if validation_errors:
        raise ValueError("\n".join(validation_errors))
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    source_plan_sha256 = file_sha256(plan_path)
    clip_map = {c["clip_id"]: c for c in semantic_data.get("clips", [])}
    updated_count = 0
    
    for clip in plan.get("clips", []):
        cid = clip["clip_id"]
        sem = clip_map.get(cid)
        if not sem:
            continue
            
        # Update clip plan continuity
        if "continuity" not in clip:
            clip["continuity"] = {}
            
        clip["continuity"]["start_state"] = sem.get("start_state", "")
        clip["continuity"]["action"] = sem.get("action", "")
        clip["continuity"]["end_state"] = sem.get("end_state", "")
        for key in ("screen_direction", "eyeline", "prop_state", "scene_topology", "motion_vector"):
            if sem.get(key):
                clip["continuity"][key] = sem.get(key)
        if sem.get("action_family"):
            clip["action_family"] = sem.get("action_family")
        if sem.get("energy_level"):
            clip["energy_level"] = sem.get("energy_level")
        if sem.get("vocal_lyrics"):
            clip["vocal_lyrics"] = sem.get("vocal_lyrics")
        if sem.get("action_peak_relative") not in (None, ""):
            try:
                clip["action_peak_relative"] = round(float(sem.get("action_peak_relative")), 3)
            except (TypeError, ValueError):
                clip["action_peak_relative"] = sem.get("action_peak_relative")
        if sem.get("visual_motif"):
            clip["visual_motif"] = sem.get("visual_motif")
        if sem.get("transition_motif"):
            clip["transition_motif"] = sem.get("transition_motif")
        shot = ensure_shot_design(clip)
        for sem_key, target_key in (
            ("shot_size", "shot_size"),
            ("angle", "angle"),
            ("camera", "camera_movement"),
            ("lens_feel", "lens_feel"),
            ("blocking", "blocking"),
            ("lighting", "lighting"),
        ):
            if sem.get(sem_key):
                shot[target_key] = sem.get(sem_key)
        
        # Apply to Markdown files
        img_prompt_path = os.path.join(root, clip.get("image_prompt_path", f"出图/段落/prompt/{cid}.md"))
        vid_prompt_path = os.path.join(root, clip.get("video_prompt_path", f"出视频/prompt/{cid}.md"))
        
        # Rewrite Image Prompt
        if os.path.exists(img_prompt_path):
            img_content = read_text(img_prompt_path)
            img_content = re.sub(
                r"(?<=画面必须服务：).*?(?=\n)", 
                sem.get("action", ""), 
                img_content
            )
            img_content = re.sub(r"- 景别：.*", f"- 景别：{shot.get('shot_size', '')}", img_content)
            img_content = re.sub(r"- 机位：.*", f"- 机位：{shot.get('angle', '')}", img_content)
            img_content = re.sub(r"- 运镜：.*", f"- 运镜：{shot.get('camera_movement', '')}", img_content)
            img_content = re.sub(r"- 光影：.*", f"- 光影：{shot.get('lighting', '')}", img_content)
            write_text(img_prompt_path, img_content)
            
        # Rewrite Video Prompt
        if os.path.exists(vid_prompt_path):
            vid_content = read_text(vid_prompt_path)
            
            # Update continuity section
            vid_content = re.sub(r"- start_state：.*", f"- start_state：{sem.get('start_state', '')}", vid_content)
            vid_content = re.sub(r"- action：.*", f"- action：{sem.get('action', '')}", vid_content)
            vid_content = re.sub(r"- end_state：.*", f"- end_state：{sem.get('end_state', '')}", vid_content)
            if sem.get("action_family"):
                vid_content = re.sub(r"- 动作家族：.*", f"- 动作家族：{sem.get('action_family', '')}", vid_content)
            if sem.get("energy_level"):
                vid_content = re.sub(r"- 力量等级：.*", f"- 力量等级：{sem.get('energy_level', '')}", vid_content)
            if sem.get("transition_motif"):
                vid_content = re.sub(r"- 转场母题：.*", f"- 转场母题：{sem.get('transition_motif', '')}", vid_content)
            vid_content = re.sub(r"- 景别：.*", f"- 景别：{shot.get('shot_size', '')}", vid_content)
            vid_content = re.sub(r"- 运镜：.*", f"- 运镜：{shot.get('camera_movement', '')}", vid_content)
            vid_content = re.sub(r"- 光影：.*", f"- 光影：{shot.get('lighting', '')}", vid_content)
            
            # Update video prompt section
            peak_rel = clip.get("action_peak_relative", "0.8s")
            try:
                peak_text = f"{parse_seconds(peak_rel):.2f}s (relative)"
            except (TypeError, ValueError):
                peak_text = str(peak_rel)
                
            vocal_lyrics = sem.get("vocal_lyrics", "")
            action_desc = sem.get("action", "")
            if vocal_lyrics and sem.get("action_family") == "performance_vocal":
                action_desc = f"{action_desc}；对口型约束：人物正在演唱歌词“{vocal_lyrics}”，口型必须完全对齐"

            prompt_replacement = f"人物运动：{action_desc}；动作家族：{clip.get('action_family', '')}；力量等级：{clip.get('energy_level', 'Level 5')}；镜头运动：{shot.get('camera_movement') or sem.get('camera', '按段落张力')}；光影：{shot.get('lighting') or sem.get('lighting', '按视觉蓝图')}；动态细节：发丝、衣摆、光斑或环境粒子随节拍产生物理惯性偏移；卡点约束：动作峰值/击中点对齐本 clip 内部的 {peak_text}；转场母题：{clip.get('transition_motif', '')}；"
            vid_content = re.sub(r"人物运动：.*?(?:卡点约束：.*?s；|声音约束：)", prompt_replacement + "声音约束：", vid_content, flags=re.DOTALL)
            
            write_text(vid_prompt_path, vid_content)
            
        updated_count += 1
        
    # Save the updated clip_plan.json
    write_json(plan_path, plan)
    result_plan_sha256 = file_sha256(plan_path)
    timeline_path = os.path.join(root, "分镜", "timeline_manifest.json")
    timeline = load_json(timeline_path, {}) or {}
    payload = {
        "schema_version": 3,
        "kind": "mv_semantic_prompts",
        "generated_at": date.today().isoformat(),
        "updated_clips": updated_count,
        "source_clip_plan_sha256": source_plan_sha256,
        "result_clip_plan_sha256": result_plan_sha256,
        "inputs_sha256": {
            "lyrics": file_sha256(os.path.join(root, "词", "lyrics.md")),
            "blueprint": file_sha256(os.path.join(root, "视觉蓝图.md")),
            "alignment": file_sha256(os.path.join(root, "字幕", "alignment_report.json")),
            "assessment": file_sha256(assessment_path),
        },
        "generator": semantic_data.get("generator"),
        "complete": updated_count == len(plan.get("clips") or []) and not allow_partial,
        "prompt_outputs_sha256": {
            clip["clip_id"]: {
                "image": file_sha256(os.path.join(root, clip.get("image_prompt_path", ""))),
                "video": file_sha256(os.path.join(root, clip.get("video_prompt_path", ""))),
            }
            for clip in plan.get("clips") or []
        },
        "clips": semantic_data.get("clips", []),
    }
    # 幂等写收据：semantic_prompts.json 被 picture_lock inputs_sha256 绑定；
    # 同输入重跑仅 generated_at 不同时保持文件字节不变，避免无谓打断 hash 链。
    receipt_path = os.path.join(root, "分镜", "semantic_prompts.json")
    existing_receipt = load_json(receipt_path, None)

    def _stable(doc):
        return {k: v for k, v in (doc or {}).items() if k != "generated_at"}

    if not (isinstance(existing_receipt, dict) and _stable(existing_receipt) == _stable(payload)):
        write_json(receipt_path, payload)

    receipt_sha256 = file_sha256(receipt_path)
    if timeline:
        timeline["source_clip_plan_sha256"] = result_plan_sha256
        timeline["semantic_prompts_applied"] = bool(payload["complete"])
        timeline["semantic_receipt_sha256"] = receipt_sha256
        write_json(timeline_path, timeline)
    if payload["complete"]:
        completion.mark_stage_complete(root, "semantic_plan")

    return updated_count


def main():
    ap = argparse.ArgumentParser(description="语义分镜引擎：基于歌词和蓝图自动补全画面提示词")
    ap.add_argument("project_root")
    ap.add_argument("--assessment", help="具体模型生成的语义 JSON；须含 generator.model/version")
    ap.add_argument("--mock-assessment", help="旧别名：提供语义 JSON 路径")
    ap.add_argument("--allow-partial", action="store_true", help="允许只注入部分 clip；默认要求覆盖全部 clip")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = load_json(plan_path)
    if not plan:
        print(f"[err] 找不到 clip_plan.json，请先运行 mv-plan。", file=sys.stderr)
        sys.exit(2)
        
    blueprint = read_text(os.path.join(root, "视觉蓝图.md"))
    lyrics = read_text(os.path.join(root, "词", "lyrics.md"))
    
    assessment_path = args.assessment or args.mock_assessment
    if not assessment_path:
        prompt = build_composer_prompt(plan.get("clips", []), blueprint, lyrics)
        print("--- LLM SEMANTIC COMPOSER PROMPT ---")
        print(prompt)
        print("--- END PROMPT ---")
        print("\n[info] 请根据上述 prompt 获取 LLM 生成的 JSON，并使用 --mock-assessment 注入结果。")
        sys.exit(3)
        
    semantic_data = load_json(assessment_path)
    if not semantic_data:
        print(f"[err] 无法读取注入的 JSON: {assessment_path}", file=sys.stderr)
        sys.exit(2)
        
    try:
        count = apply_prompts(root, plan, semantic_data, allow_partial=args.allow_partial,
                              assessment_path=assessment_path)
    except ValueError as exc:
        print(f"[err] 语义 JSON 校验失败：\n{exc}", file=sys.stderr)
        sys.exit(2)
    print(f"[ok] 已成功将语义信息注入到 {count} 个 Clip 的 prompt 文件及 clip_plan.json 中。")


if __name__ == "__main__":
    main()
