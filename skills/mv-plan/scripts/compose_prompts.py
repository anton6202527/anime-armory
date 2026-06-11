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
            f"Clip ID: {c['clip_id']} | 时长: {c['duration']}s | 段落: {c['section']} | 动作家族建议: {c.get('action_family', '')} | 动作峰值: {c.get('action_peak', c.get('end'))}s | 歌词: {lyric}"
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
- 主歌（Verse）：通常节奏较慢，适合推拉镜头，注重氛围和情绪铺垫。
- 副歌（Chorus）：通常节奏快，适合环绕、快速切入，动作幅度大，展现高光时刻。
- 空镜/转场：如果没有具体歌词，可以设计符合情绪的空镜。
- 动作设计参考 mv-video/references/action_knowledge.md：一 clip 一个主动作，动作峰值对齐 beat/downbeat；复杂多人接触优先拆成特写/剪影/道具/光效切。
- 视觉一致性参考 mv-image/references/visual_consistency.md：主角身份锚点、global_style、palette_anchor、motif_ledger 必须继承；副歌可以增强光效但不能换脸换风格。

输出 JSON 格式，严格包含所有传入的 Clip ID，结构如下：
{{
  "clips": [
    {{
      "clip_id": "Clip_001",
      "start_state": "画面开始时的场景和人物状态",
      "action_family": "动作家族，如 dance_hit/vfx_burst/expressive_walk",
      "action": "人物在此期间的具体动作（如：抬头看天、转身走开）",
      "action_peak": "动作峰值应对齐的秒点，如 48.80",
      "end_state": "动作结束时的状态",
      "camera": "运镜方式（如：缓慢推进、跟随镜头、固定特写）",
      "lighting": "光影氛围（如：逆光剪影、冷色调霓虹光）",
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
        if sem.get("action_peak") not in (None, ""):
            try:
                clip["action_peak"] = round(float(sem.get("action_peak")), 3)
            except (TypeError, ValueError):
                clip["action_peak"] = sem.get("action_peak")
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
            if sem.get("transition_motif"):
                vid_content = re.sub(r"- 转场母题：.*", f"- 转场母题：{sem.get('transition_motif', '')}", vid_content)
            
            # Update video prompt section
            peak = clip.get("action_peak", clip["end"])
            try:
                peak_text = f"{float(peak):.2f}s"
            except (TypeError, ValueError):
                peak_text = str(peak)
            prompt_replacement = f"人物运动：{sem.get('action', '')}；动作家族：{clip.get('action_family', '')}；镜头运动：{sem.get('camera', '按段落张力')}；光影：{sem.get('lighting', '按视觉蓝图')}；动态细节：发丝、衣摆、光斑或环境粒子随节拍变化；卡点约束：动作峰值对齐 {peak_text}；转场母题：{clip.get('transition_motif', '')}；"
            vid_content = re.sub(r"人物运动：.*?(?:卡点约束：.*?s；|声音约束：)", prompt_replacement + "声音约束：", vid_content, flags=re.DOTALL)
            
            write_text(vid_prompt_path, vid_content)
            
        updated_count += 1
        
    # Save the updated clip_plan.json
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    write_json(plan_path, plan)
    
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
