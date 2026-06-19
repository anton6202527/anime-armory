#!/usr/bin/env python3
"""
foley_agent.py - V2A 视觉拟音系统 (Next Gen)
分析故事板与视频 Clip，识别视觉动因（如：拔剑、脚步、雨声），
自动检索或生成对齐的音效轨道 (SFX/Foley)。
"""
import sys
import os
import json
import re

def main():
    if len(sys.argv) < 3:
        print("Usage: foley_agent.py <root> <episode>")
        return

    root = sys.argv[1]
    ep = sys.argv[2]
    
    # 1. 读取故事板与时长清单
    storyboard_path = os.path.join(root, "脚本", ep, "storyboard.json")
    timing_path = os.path.join(root, "合成", ep, "配音", "时长清单.json")
    
    if not os.path.exists(storyboard_path) or not os.path.exists(timing_path):
        return

    try:
        sb = json.load(open(storyboard_path, encoding="utf-8"))
        timings = json.load(open(timing_path, encoding="utf-8"))
    except Exception:
        return

    # 2. 识别需要 SFX 的 Clip
    clips = sb.get("clips", [])
    foley_plan = []
    
    current_time = 0.0
    for i, clip in enumerate(clips):
        duration = float(clip.get("duration", 0))
        # 搜索 Clip 描述中的音效关键词
        body = clip.get("prompt", "") + " " + clip.get("导演意图", "")
        
        # 极简语义拟音逻辑
        sfx_tags = []
        if re.search(r"剑|武器|击打|挥舞", body): sfx_tags.append("sword_whoosh")
        if re.search(r"雨|雷|风", body): sfx_tags.append("ambience_weather")
        if re.search(r"脚步|走|跑", body): sfx_tags.append("footsteps")
        if re.search(r"门|开门|关门", body): sfx_tags.append("door_creak")
        
        if sfx_tags:
            foley_plan.append({
                "clip_id": clip.get("id"),
                "start": current_time,
                "duration": duration,
                "tags": sfx_tags
            })
        current_time += duration

    # 3. 输出拟音计划 (实际生成逻辑可在此接入 V2A API)
    out_path = os.path.join(root, "合成", ep, "_work", "foley_plan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(foley_plan, f, ensure_ascii=False, indent=2)
    
    print(f"Generated Foley plan with {len(foley_plan)} targeted sound events.")
    
    # 4. 生成静音占位轨 (演示用，实际应在此合成 SFX)
    # ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=stereo -t <total_dur> foley_mix.wav
    total_dur = current_time
    foley_wav = os.path.join(root, "合成", ep, "_work", "foley_mix.wav")
    os.system(f"ffmpeg -y -loglevel error -f lavfi -i anullsrc=r=44100:cl=stereo -t {total_dur} {foley_wav}")

if __name__ == "__main__":
    main()
