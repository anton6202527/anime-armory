#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spatial Anchor Planner - Consistency optimization for environmental spaces."""

import os
import json
import sys

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_const import SPATIAL_ANCHOR_FIELD
except ImportError:
    SPATIAL_ANCHOR_FIELD = "spatial_anchor"

def plan_spatial_anchors(root, ep):
    """Scan storyboard.json and suggest spatial anchors for recurring locations."""
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(sb_path):
        return
    
    with open(sb_path, "r", encoding="utf-8") as f:
        sb = json.load(f)
    
    clips = sb.get("clips", [])
    location_usage = {}
    
    for clip in clips:
        loc = clip.get("location")
        if loc:
            location_usage.setdefault(loc, []).append(clip)
            
    recommendations = []
    for loc, loc_clips in location_usage.items():
        if len(loc_clips) >= 3: # Suggest for locations used 3+ times
            recommendations.append({
                "location": loc,
                "clips_count": len(loc_clips),
                "suggestion": f"Generate a 360° panorama master card for '{loc}' to ensure spatial consistency."
            })
            
            # Inject spatial_anchor field if not present
            for clip in loc_clips:
                cont = clip.setdefault("continuity", {})
                if SPATIAL_ANCHOR_FIELD not in cont:
                    cont[SPATIAL_ANCHOR_FIELD] = f"LOC_{loc}_MASTER"
                    
    if recommendations:
        tmp_path = sb_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sb, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, sb_path)
        print(f"[opt] Spatial anchors injected into {sb_path} for {len(recommendations)} locations.")
        for rec in recommendations:
            print(f"   - {rec['location']}: {rec['clips_count']} clips")
            
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: spatial_planner.py <root> <ep>")
    else:
        plan_spatial_anchors(sys.argv[1], sys.argv[2])
