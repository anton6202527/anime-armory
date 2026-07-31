#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract emotional flow (energy curve) from voice segments."""

import subprocess
import json
import os
import re

def extract_energy(wav_path):
    """Extract mean volume and max volume as a proxy for energy."""
    try:
        # Use ffmpeg volumedetect filter
        cmd = [
            'ffmpeg', '-i', wav_path, 
            '-filter:a', 'volumedetect', 
            '-f', 'null', '-'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        
        mean_vol = 0.0
        max_vol = 0.0
        
        m_mean = re.search(r"mean_volume:\s*([-+]?\d*\.\d+|\d+) dB", output)
        if m_mean:
            mean_vol = float(m_mean.group(1))
            
        m_max = re.search(r"max_volume:\s*([-+]?\d*\.\d+|\d+) dB", output)
        if m_max:
            max_vol = float(m_max.group(1))
            
        return {
            "mean_db": mean_vol,
            "max_db": max_vol,
            "energy_score": max(0, 100 + mean_vol) / 100.0 # Normalized 0-1 approx
        }
    except Exception:
        return {"mean_db": -60.0, "max_db": -60.0, "energy_score": 0.0}

def analyze_emotion_flow(wav_dir, manifest, output_path):
    """Analyze all segments in a manifest and save the emotion flow."""
    flow = []
    for entry in manifest:
        wav_file = os.path.join(wav_dir, entry.get("wav", ""))
        if os.path.exists(wav_file):
            energy = extract_energy(wav_file)
            flow.append({
                "index": entry.get("index"),
                "shot": entry.get("shot"),
                "role": entry.get("role"),
                "energy": energy,
                "emotion_applied": entry.get("emotion_applied"),
                "duration": entry.get("duration")
            })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flow, f, ensure_ascii=False, indent=2)
    return flow
