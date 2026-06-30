#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hybrid Identity Tool - Support for complex character states and multi-LoRA setups."""

import os
import json
import sys

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_const import IDENTITY_ANCHOR_POINTS_FIELD
except ImportError:
    IDENTITY_ANCHOR_POINTS_FIELD = "identity_anchor_points"

def apply_hybrid_identity(root, ep, char_id, features):
    """Apply specific anchor points to a character in a specific episode."""
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(sb_path):
        return
    
    with open(sb_path, "r", encoding="utf-8") as f:
        sb = json.load(f)
    
    clips = sb.get("clips", [])
    count = 0
    for clip in clips:
        # Check if character is in this clip
        if char_id in str(clip.get("character_ids", "")):
            cont = clip.setdefault("continuity", {})
            # Merge features
            anchors = cont.get(IDENTITY_ANCHOR_POINTS_FIELD, {})
            if isinstance(anchors, dict):
                anchors.update(features)
                cont[IDENTITY_ANCHOR_POINTS_FIELD] = anchors
                count += 1
                
    if count > 0:
        tmp_path = sb_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sb, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, sb_path)
        print(f"[opt] Applied hybrid identity anchors to {count} clips in {ep} for {char_id}.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: hybrid_identity_tool.py <root> <ep> <char_id> '<json_features>'")
    else:
        features = json.loads(sys.argv[4])
        apply_hybrid_identity(sys.argv[1], sys.argv[2], sys.argv[3], features)
