#!/usr/bin/env python3
"""State pixel verification via VLM: semantic triage for claimed visual states.

Reads state_continuity ledger for claimed state changes (injured/transformed/
awakened/blood/tears). For each state-change shot, uses VLM (N2D_VLM_CMD) to ask
"does this image show [state]?".

Complements state_pixel_contract.py (which uses identity_marks + OWLv2 detection
for registered marks). This covers states NOT backed by registered identity_marks.

Verdict: VLM says "no" on claimed state → WARN + mandatory human confirmation;
VLM alone never supplies a load-bearing BLOCK. "uncertain" → WARN.
Degrades gracefully: no N2D_VLM_CMD → available=False, skip.

Usage: python3 state_pixel_verify.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence

KIND = "n2d_state_pixel_verify"
VERSION = 2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import detector_reliability  # noqa: E402

# State types requiring pixel verification (not covered by identity_marks)
STATE_VERIFY_TERMS = (
    "受伤", "流血", "泪", "湿透", "变身", "觉醒", "黑化", "异化",
    "伤", "创伤", "烧伤", "断肢", "变形",
    "transformed", "injured", "blood", "tears", "awakened",
)
STATE_RE = re.compile("|".join(STATE_VERIFY_TERMS))


# ── Pure functions ─────────────────────────────────────────────────────

def build_judge_prompt(char_name: str, state_desc: str) -> str:
    """Build VLM judge prompt for state verification. Pure function."""
    return (
        f"Examine the image carefully. Does {char_name} show {state_desc}? "
        f"Answer ONLY one word: yes, no, or uncertain."
    )


def parse_state_verdict(raw: str) -> Optional[str]:
    """Parse VLM response: yes/no/uncertain. Pure function."""
    raw = raw.strip().lower()
    for prefix in ("yes", "是的", "有", "是"):
        if raw.startswith(prefix) or raw == prefix:
            return "yes"
    for prefix in ("no", "没有", "不是", "否"):
        if raw.startswith(prefix) or raw == prefix:
            return "no"
    if any(w in raw for w in ("uncertain", "不确定", "unsure", "无法判断", "maybe")):
        return "uncertain"
    return None


def state_verdict_to_finding(vlm_answer: str, claim: str, shot: str) -> Dict[str, str]:
    """VLM answer → finding dict. Pure function."""
    if vlm_answer == "no":
        governed = detector_reliability.govern_verdict("block", detector_kind="vlm")
        return {"verdict": governed["verdict"], "raw_verdict": "block",
                "needs_human_confirmation": "true",
                "msg": f"VLM 判定图中未呈现声明状态「{claim}」；VLM 仅作告警，须人审或确定性像素证据确认后才能 BLOCK",
                "shot": shot, "detector_kind": "vlm"}
    if vlm_answer == "uncertain":
        return {"verdict": "warn", "msg": f"VLM 无法确定图中是否呈现状态「{claim}」，建议人判",
                "shot": shot}
    return {"verdict": "ok", "msg": "", "shot": shot}


def _probe_vlm() -> bool:
    return bool(os.environ.get("N2D_VLM_CMD", "").strip())


# ── State discovery ────────────────────────────────────────────────────

def _find_state_change_shots(root: str, ep: str) -> List[Dict[str, Any]]:
    """Find shots with claimed state changes from state_continuity ledger.
    Returns [{shot, character, state_desc, png}]."""
    led_path = os.path.join(root, "生产数据", f"state_ledger_{ep}.json")
    if not os.path.isfile(led_path):
        return []
    with open(led_path, encoding="utf-8") as fh:
        ledger = json.load(fh)
    shots = []
    for entry in ledger.get("entries", []):
        if not isinstance(entry, dict):
            continue
        desc = str(entry.get("state_description") or entry.get("state") or "")
        if not STATE_RE.search(desc):
            continue
        png = entry.get("png") or entry.get("frame") or ""
        char = entry.get("character") or entry.get("char") or ""
        cid = entry.get("clip_id") or entry.get("shot") or ""
        if png and desc:
            shots.append({"shot": str(cid), "character": str(char),
                         "state_desc": desc, "png": str(png)})
    return shots


# ── VLM integration ────────────────────────────────────────────────────

def call_vlm(image_path: str, prompt: str) -> Optional[str]:
    """Call N2D_VLM_CMD with image and prompt. Returns raw VLM response or None."""
    tmpl = os.environ.get("N2D_VLM_CMD", "").strip()
    if not tmpl:
        return None
    cmd_str = tmpl.replace("{image}", shlex.quote(image_path)).replace("{prompt}", shlex.quote(prompt))
    try:
        proc = subprocess.run(
            cmd_str, shell=True, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, check=False,
        )
        return proc.stdout.strip()[:500] if proc.stdout else None
    except Exception:
        return None


def analyze(root: str, ep: str) -> Dict[str, Any]:
    """Main entry: find state-change shots, verify via VLM.
    Returns {available, notes, findings}."""
    if not _probe_vlm():
        return {"available": False, "notes": ["N2D_VLM_CMD 未设。跳过状态像素验证。"], "findings": []}
    shots = _find_state_change_shots(root, ep)
    if not shots:
        return {"available": True, "notes": ["本集无声明状态变化的镜头。"], "findings": []}
    findings = []
    for s in shots:
        png = os.path.join(root, s["png"]) if s["png"] else ""
        if not png or not os.path.isfile(png):
            findings.append({"shot": s["shot"], "verdict": "ok",
                           "note": f"状态变化镜头的 PNG 不可用：{s['png']}"})
            continue
        prompt = build_judge_prompt(s["character"], s["state_desc"])
        raw = call_vlm(png, prompt)
        if raw is None:
            findings.append({"shot": s["shot"], "verdict": "warn",
                           "msg": f"VLM 调用失败；状态「{s['state_desc']}」未经像素验证",
                           "dimension": "状态像素验证(SP1V)"})
            continue
        verdict = parse_state_verdict(raw)
        if verdict is None:
            findings.append({"shot": s["shot"], "verdict": "warn",
                           "msg": f"VLM 回复不可解析（{raw[:80]}）；状态「{s['state_desc']}」未经可靠验证",
                           "dimension": "状态像素验证(SP1V)"})
            continue
        finding = state_verdict_to_finding(verdict, s["state_desc"], s["shot"])
        finding["dimension"] = "状态像素验证(SP1V)"
        findings.append(finding)
    return {"available": True, "notes": [], "findings": findings}


# ── CLI ────────────────────────────────────────────────────────────────

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d state pixel verification (VLM)")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"available={result['available']}")
        for f in result.get("findings", []):
            print(f"  [{f.get('verdict','?')}] {f.get('shot','')}: {f.get('msg', f.get('note',''))}")
    return 0 if result.get("available") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
