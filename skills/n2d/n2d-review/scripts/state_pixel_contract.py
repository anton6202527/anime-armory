#!/usr/bin/env python3
"""SP1-V 角色状态演进像素契约 —— 给文本档 state_continuity（角色状态演进·最严 BLOCK 字段）补
「图里到底处于这个状态吗」。

state_continuity 只查「状态锁有没有写进出图 prompt 文本」；本 runner 进一步查「状态有没有真出现在
生成的图里」——按 `storyboard.visual_contract.角色状态演进` 的逐镜区间（自X 保持 至Y），对每帧的状态
角色判两个方向：
  ① 区间内应有该状态、像素却检不出 → `state_pixel_missing`；
  ② 区间起点之前不该有、像素却已出现 → `state_pixel_premature_leak`
     （最危险：图提前泄露未到点的觉醒/伤/变身——文本对、像素错，正是此前缺的那道兜底）。

状态→检测词桥接：用 identity_registry 的 `identity_marks`（金瞳觉醒态 ↔ MARK_金瞳/detect_phrase）。
状态描述命中某 mark 的搜索词时用其 `detect_phrase`（英文最准），否则退化用中文状态描述（更弱·诚实降级）。

复用 marks_presence_runner 的探测器契约（`N2D_MARKS_PRESENCE_BATCH_CMD` / `N2D_MARKS_PRESENCE_CMD`，
直接复用 `backends/presence_owlv2.py`，它已兼容 `expect:"absent"` 双向判定）；缺探测器命令则只产
manifest（findings 空），交装好后端复跑——绝不臆造在场结论。

诚实边界：OWLv2 对小标记/侧脸/遮挡噪声大，**像素证据一律 warn**（不硬 block，文本档 state_continuity
仍是 BLOCK 权威）。互补关系同 MK1（marks_consistency）↔ MK1-V（marks_presence_runner）。

用法：python3 state_pixel_contract.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import marks_consistency as mc  # noqa: E402  标记归一/桥接 + 探测词
import marks_presence_runner as mpr  # noqa: E402  复用 clip→帧 + 探测器调用
import state_continuity as sc  # noqa: E402  复用逐镜状态区间解析（角色状态演进 + visual_state_ledger）

STATE_PIXEL_KIND = "n2d_state_pixel"


def _char_aliases(char: str, char_marks: List[Mapping[str, Any]]) -> Set[str]:
    """该角色的别名集（用于判该镜在场）：取 identity_registry 同名/同 id 形态的 aliases，并入角色名本身。"""
    al: Set[str] = set()
    for cm in char_marks:
        if cm.get("char_name") == char or char in (cm.get("aliases") or set()):
            al |= set(cm.get("aliases") or set())
    if char:
        al.add(char)
    return {a for a in al if a}


def _marks_for_char(char: str, char_marks: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    out: List[Mapping[str, Any]] = []
    for cm in char_marks:
        if cm.get("char_name") == char or char in (cm.get("aliases") or set()):
            out.extend(cm.get("marks") or [])
    return out


def clip_presence_blob(clip: Mapping[str, Any]) -> str:
    """单 clip 的「在场角色」可搜索文本：clip_storyboard_text(label/scene/continuity/shots[].desc)
    再并入 clip 级 description / character_ids / characters 等结构字段，使按角色名或 CHAR_id 都能命中。纯函数·可测。"""
    parts: List[str] = [mc.clip_storyboard_text(clip)]
    for key in ("description", "desc", "character_ids", "characters", "char_ids", "角色", "在场角色"):
        v = clip.get(key)
        if isinstance(v, str):
            parts.append(v)
        elif v:
            parts.append(json.dumps(v, ensure_ascii=False))
    return " ".join(p for p in parts if p)


def char_in_corpus(char: str, corpus: str, char_marks: List[Mapping[str, Any]]) -> bool:
    """该镜文本/结构是否提到这个状态角色（近似「在场」）。无别名信息时退回角色名直配。纯函数·可测。"""
    aliases = _char_aliases(char, char_marks)
    return any(a in corpus for a in aliases)


def resolve_state_probe(state: Mapping[str, Any], char: str,
                        char_marks: List[Mapping[str, Any]]) -> tuple:
    """状态 → (asset_id, OWLv2 检测词)。命中 identity_registry mark 用其 detect_phrase（英文最准），
    否则退化用中文状态描述（更弱）。纯函数·可测。"""
    desc = str(state.get("description") or "").strip()
    blob = desc + " " + " ".join(str(t) for t in (state.get("terms") or []))
    for mark in _marks_for_char(char, char_marks):
        if any(tok in blob for tok in mc.mark_tokens(mark)):
            phrase = str(mark.get("detect_phrase") or "").strip() or mc._mark_desc(mark)
            return (str(mark.get("mark_id") or mc._mark_desc(mark)), phrase)
    return (desc or "state", desc)


def state_finding(shot: Any, ea: Mapping[str, Any], present: bool,
                  confidence: Any) -> Optional[Dict[str, Any]]:
    """逐 probe（N2D_MARKS_PRESENCE_CMD 路径）的判定 → 缺席/提前泄露 finding 或 None。纯函数·可测。"""
    expect = str(ea.get("expect") or "present")
    base = {
        "shot": shot, "asset": ea.get("asset"), "char": ea.get("char"),
        "state": ea.get("state"), "phrase": ea.get("phrase"), "confidence": confidence,
    }
    if expect == "absent" and present:
        return {**base, "kind": "state_pixel_premature_leak", "expected": False, "present": True,
                "message": f"状态像素在区间起点前已检出「{ea.get('phrase')}」（提前泄露疑似）"}
    if expect == "present" and not present:
        return {**base, "kind": "state_pixel_missing", "expected": True, "present": False,
                "message": f"区间内未检出状态像素「{ea.get('phrase')}」"}
    return None


def build_manifest(root: str, ep: str) -> dict:
    rootp = root.rstrip("/")
    sb = mc._load_json(Path(rootp) / "脚本" / ep / "storyboard.json") or {}
    states = sc.states_from_storyboard(sb) + sc.states_from_visual_ledger(rootp, ep)
    registry = mc._load_json(Path(rootp) / "出图" / "共享" / "identity_registry.json") or {}
    char_marks = mc.collect_character_marks(registry)
    clips = (sb or {}).get("clips") or (sb or {}).get("shots") or []
    images = mpr._episode_images(rootp, ep)

    probes: List[dict] = []
    for idx, clip in enumerate(clips):
        if not isinstance(clip, Mapping):
            continue
        clip_id = str(clip.get("id") or clip.get("label") or f"Clip{idx + 1:02d}")
        clip_no = sc.shot_num(clip_id)
        if clip_no is None:
            continue
        img = images.get(clip_id)
        if not img:
            continue
        corpus = clip_presence_blob(clip)
        expected: List[dict] = []
        for st in states:
            char = str(st.get("character") or "")
            if not char_in_corpus(char, corpus, char_marks):
                continue
            start = int(st.get("start_shot") or 1)
            end = st.get("end_shot")
            end = int(end) if isinstance(end, int) else None
            if clip_no < start:
                expect, kind = "absent", "state_pixel_premature_leak"   # 起点前：查提前泄露
            elif end is not None and clip_no > end:
                continue   # 区间后不查像素（state_leak_after_end 归文本档；OWLv2 对「该消失」噪声更大）
            else:
                expect, kind = "present", "state_pixel_missing"          # 区间内：查应有
            asset, phrase = resolve_state_probe(st, char, char_marks)
            if not phrase:
                continue
            expected.append({
                "asset": asset, "phrase": phrase, "expect": expect, "kind": kind,
                "char": char, "state": str(st.get("description") or ""),
            })
        if expected:
            probes.append({
                "shot": clip_id,
                "image": os.path.relpath(img, rootp) if img else None,
                "expected_assets": expected,
            })
    return {
        "kind": STATE_PIXEL_KIND,
        "root": rootp,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "state_count": len(states),
        "probes": probes,
        "findings": [],
    }


def fill_findings(root: str, manifest: dict) -> dict:
    """N2D_MARKS_PRESENCE_CMD（逐 probe）路径：逐 expected_asset 探活，按 expect 双向判定写 findings。
    批量后端（N2D_MARKS_PRESENCE_BATCH_CMD → presence_owlv2）走 write()，由后端就地覆写 findings。"""
    cmd = os.environ.get("N2D_MARKS_PRESENCE_CMD", "").strip()
    if not cmd:
        return manifest
    findings: List[dict] = []
    for probe in manifest.get("probes", []):
        image = probe.get("image")
        if not image:
            continue
        image_abs = image if os.path.isabs(image) else os.path.join(root, image)
        for ea in probe.get("expected_assets", []):
            verdict = mpr._run_detector(cmd, image_abs, ea.get("phrase") or ea.get("asset"))
            if not isinstance(verdict, dict):
                continue
            f = state_finding(probe.get("shot"), ea, bool(verdict.get("present")), verdict.get("confidence"))
            if f:
                findings.append(f)
    manifest["findings"] = findings
    manifest["detector"] = cmd.split()[0]
    return manifest


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    if not os.environ.get("N2D_MARKS_PRESENCE_BATCH_CMD"):
        manifest = fill_findings(root, manifest)
    path = os.path.join(root.rstrip("/"), "生产数据", f"state_pixel_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    mpr._run_batch(path)  # 复用同一批量后端契约（presence_owlv2 已兼容 expect:"absent"）
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="SP1-V 角色状态演进像素契约 manifest/runner")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.write:
        path = write(root, ns.episode)
        if not ns.json:
            print(path)
            return 0
    manifest = fill_findings(root, build_manifest(root, ns.episode))
    if ns.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        on = bool(os.environ.get("N2D_MARKS_PRESENCE_CMD") or os.environ.get("N2D_MARKS_PRESENCE_BATCH_CMD"))
        print(f"probes={len(manifest['probes'])} findings={len(manifest['findings'])} "
              f"detector={'on' if on else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
