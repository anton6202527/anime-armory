#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic Prompt Composer for MV pipeline.

Reads the clip_plan.json, lyrics.md, and 视觉蓝图.md, and generates semantic
prompts (action, camera, state) for each clip using an LLM integration.
"""
import argparse
import json
import os
import re
import sys
from datetime import date


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


def build_composer_prompt(clips, blueprint, lyrics):
    clip_summaries = []
    for c in clips:
        lyric = c.get('lyric_hint') or '无'
        clip_summaries.append(
            f"Clip ID: {c['clip_id']} | 时间: {c['start']}-{c['end']}s | 时长: {c['duration']}s | 段落: {c['section']} | 动作家族建议: {c.get('action_family', '')} | 能量等级: {c.get('energy_level', '')} | 歌词参考: {lyric}"
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
      "camera": "运镜方式（如：缓慢推进、跟随镜头、固定特写）",
      "lighting": "光影氛围（如：逆光剪影、红蓝霓虹律动），需符合色彩剧本",
      "visual_motif": "本 clip 继承或强化的视觉母题",
      "transition_motif": "转场母题，如 光效切/遮挡擦镜/动作切"
    }}
  ]
}}
"""


def apply_prompts(root, plan, semantic_data):
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
            
            # Update video prompt section
            peak_rel = clip.get("action_peak_relative", "0.8s")
            try:
                peak_text = f"{float(peak_rel):.2f}s (relative)"
            except (TypeError, ValueError):
                peak_text = str(peak_rel)
                
            vocal_lyrics = sem.get("vocal_lyrics", "")
            action_desc = sem.get("action", "")
            if vocal_lyrics and sem.get("action_family") == "performance_vocal":
                action_desc = f"{action_desc}；对口型约束：人物正在演唱歌词“{vocal_lyrics}”，口型必须完全对齐"

            prompt_replacement = f"人物运动：{action_desc}；动作家族：{clip.get('action_family', '')}；力量等级：{clip.get('energy_level', 'Level 5')}；镜头运动：{sem.get('camera', '按段落张力')}；光影：{sem.get('lighting', '按视觉蓝图')}；动态细节：发丝、衣摆、光斑或环境粒子随节拍产生物理惯性偏移；卡点约束：动作峰值/击中点对齐本 clip 内部的 {peak_text}；转场母题：{clip.get('transition_motif', '')}；"
            vid_content = re.sub(r"人物运动：.*?(?:卡点约束：.*?s；|声音约束：)", prompt_replacement + "声音约束：", vid_content, flags=re.DOTALL)
            
            write_text(vid_prompt_path, vid_content)
            
        updated_count += 1
        
    # Save the updated clip_plan.json
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    write_json(plan_path, plan)
    payload = {
        "schema_version": 1,
        "kind": "mv_semantic_prompts",
        "generated_at": date.today().isoformat(),
        "updated_clips": updated_count,
        "clips": semantic_data.get("clips", []),
    }
    write_json(os.path.join(root, "分镜", "semantic_prompts.json"), payload)
    
    return updated_count


def main():
    ap = argparse.ArgumentParser(description="语义分镜引擎：基于歌词和蓝图自动补全画面提示词")
    ap.add_argument("project_root")
    ap.add_argument("--mock-assessment", help="提供模拟评估 JSON 的路径，用于测试或手动注入")
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
    
    if not args.mock_assessment:
        prompt = build_composer_prompt(plan.get("clips", []), blueprint, lyrics)
        print("--- LLM SEMANTIC COMPOSER PROMPT ---")
        print(prompt)
        print("--- END PROMPT ---")
        print("\n[info] 请根据上述 prompt 获取 LLM 生成的 JSON，并使用 --mock-assessment 注入结果。")
        sys.exit(0)
        
    semantic_data = load_json(args.mock_assessment)
    if not semantic_data:
        print(f"[err] 无法读取注入的 JSON: {args.mock_assessment}", file=sys.stderr)
        sys.exit(2)
        
    count = apply_prompts(root, plan, semantic_data)
    print(f"[ok] 已成功将语义信息注入到 {count} 个 Clip 的 prompt 文件及 clip_plan.json 中。")


if __name__ == "__main__":
    main()
