#!/usr/bin/env python3
"""Smart upgrade suggestions based on production history."""

from __future__ import annotations
import json
import os
import sys
from typing import Dict, List, Any, Optional

# Use vendorized n2d _lib
COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'n2d', '_lib'))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

try:
    from n2d_contract import classify_redraw_reason, load_identity_registry
except ImportError:
    from n2d_logic import classify_redraw_reason
    from n2d_registry import load_identity_registry

def get_smart_suggestions(root: str) -> List[Dict[str, Any]]:
    """Analyze production events and return actionable suggestions."""
    events_path = os.path.join(root, "生产数据", "production_events.jsonl")
    if not os.path.isfile(events_path):
        return []

    events = []
    bad_lines = 0
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # 一行坏 jsonl 不该让整个建议引擎崩掉；跳过并计数。
                bad_lines += 1
    if bad_lines:
        print(f"⚠️ smart_suggestions：跳过 {bad_lines} 行无法解析的 production_events.jsonl",
              file=sys.stderr)

    # 统计角色/后端失败频次
    # { (char_id, backend): { "blocks": N, "redraws": M, "reasons": set() } }
    stats = {}
    
    for ev in events:
        qa = ev.get("qa")
        meta = ev.get("meta") or {}
        if not qa:
            continue
            
        status = qa.get("status")
        reason = qa.get("redraw_reason") or qa.get("message") or ""
        dimension = qa.get("dimension") or ""
        
        char_id = meta.get("character_id") or meta.get("char")
        backend = meta.get("backend") or ev.get("provider")
        
        if not char_id or not backend:
            continue
            
        key = (char_id, backend)
        if key not in stats:
            stats[key] = {"blocks": 0, "redraws": 0, "reasons": set()}
            
        if status == "block":
            stats[key]["blocks"] += 1
            
        classified = classify_redraw_reason(reason)
        if classified == "identity_drift":
            stats[key]["redraws"] += 1
            
        if reason:
            stats[key]["reasons"].add(reason[:50])

    suggestions = []
    registry = load_identity_registry(root)
    characters = registry.get("characters", {})

    for (char_id, backend), s in stats.items():
        # 判定标准：同一角色在同一后端下 block 次数 >= 3 或 身份漂移重抽 >= 5
        if s["blocks"] >= 3 or s["redraws"] >= 5:
            char_name = characters.get(char_id, {}).get("name", char_id)
            
            # 查当前状态
            char_cfg = characters.get(char_id, {})
            adapters = char_cfg.get("identity_adapters", {})
            backend_cfg = adapters.get(backend, {})
            # mode 可能不存在、也可能显式为 null —— 两种都归一到 "reference"，
            # 避免 None.lower() AttributeError 让整条建议静默消失。
            current_mode = backend_cfg.get("mode") or "reference"

            if "lora" not in current_mode.lower() and "id" not in current_mode.lower():
                suggestions.append({
                    "type": "upgrade_identity",
                    "character_id": char_id,
                    "character_name": char_name,
                    "backend": backend,
                    "reason": f"高频失败 ({s['blocks']}次阻断, {s['redraws']}次漂移重抽)",
                    "action": "建议升档一致性方案：尝试 LoRA 训练或使用平台内置 Character ID。",
                    "priority": "high" if s["blocks"] >= 5 else "medium"
                })
            else:
                suggestions.append({
                    "type": "switch_backend",
                    "character_id": char_id,
                    "character_name": char_name,
                    "backend": backend,
                    "reason": f"即便使用 LoRA/{current_mode} 仍反复失败",
                    "action": "建议考虑更换视频后端，或重新采样 LoRA 数据集。",
                    "priority": "high"
                })

    return suggestions

def print_suggestions(suggestions: List[Dict[str, Any]]):
    if not suggestions:
        return
        
    print("\n💡 智能优化建议 (Smart Suggestions):")
    for s in suggestions:
        print(f"  · [{s['priority'].upper()}] {s['character_name']} @ {s['backend']}:")
        print(f"    原因: {s['reason']}")
        print(f"    动作: {s['action']}")
    print("")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: smart_suggestions.py <作品根>")
        sys.exit(1)
    
    root = sys.argv[1]
    suggs = get_smart_suggestions(root)
    print_suggestions(suggs)
