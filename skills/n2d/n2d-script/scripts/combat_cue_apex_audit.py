#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打斗剪辑 cue ↔ apex 关键帧对齐审计（把"cue 必须对齐命中/apex"从散文规则变成可机检闸）。

为什么存在：combat 四轴加固后，`action_edit_cues`（hit_stop/screen_shake/impact_sfx/white_flash/
impact_or_energy_boom 等剪辑峰值）只被**生成**，`anchor_planner` 的 apex 关键帧也只被**生成**，
但二者是否真落在同一秒**从没人核对**——唯一的连接是 `spectacle_sequence_plan.py` 里一句
散文 post_rule（"action_edit_cues 的 hit-stop/速度坡/闪白/震屏/SFX 峰值必须和 impact/apex 对齐"）。
散文不是闸。本审计把它兑现成确定性对账：

  C1 impact_frame/collision_or_apex_frame 没带秒数（cue 的 when 取不到 `<秒>s`）
     → `combat_apex_untimestamped`：剪辑峰值无法钉到任何关键帧，整条 apex 链浮空（最常见真缺陷）。
  C2 cue 钉了某秒，但 storyboard `continuity.anchors` 没有该秒的 keyframe 锚（anchor_planner 未注回 /
     该镜被手动锚跳过）→ `combat_cue_apex_no_keyframe`：SFX/震屏峰值引用了一个不存在的离散关键帧。
  C3 anchor 计划有 keyframe 锚，但没有任何 impact 剪辑 cue 落在它附近 → `combat_apex_no_edit_cue`：
     有了命中关键帧却没在剪辑层用它做峰值（四轴撞点没被剪辑兑现）。

只审 impact 型奇观（fight_exchange / magic_burst）——chase/flight 等无离散命中帧，不在此闸。
零像素·零花钱·纯 stdlib：写 `生产数据/combat_cue_apex_<集>.{json,md}`，给人审。复用（不重造）：
anchor_planner.apex_anchor_seconds / n2d_contract.infer_spectacle_type / edit_cues_for_spectacle
（单一真值源·与生产侧同口径）。

**已接 n2d-review 硬闸（不再只是 report-only）**：consistency_audit 把本审计 in-process 卷进
「打斗撞点(SPEC-APEX)」维度，C1/C2(warn 码)在 **核心打斗镜（核心场景 LOC 或 高潮/爆点/关键/反转 key 镜）
× 交付边界(compose/review)** 由 `gate._strict_advisory_should_block` **升 BLOCK**（与 W2/W3 光照核心场景硬化同口径）；
C3(info) 不升。确属可接受（如慢镜处理无需离散命中帧）写 `生产数据/consistency_advisory_signoff_<集>.json`
签收降回 WARN。非核心/非 key 的普通打斗镜仍保持 advisory WARN。

用法：python3 combat_cue_apex_audit.py <作品根> <第N集> [--json]
测试：cd skills/n2d/n2d-script/scripts && python -m pytest test_combat_cue_apex_audit.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from anchor_planner import apex_anchor_seconds  # 同目录·apex 秒抽取单一真值源
from n2d_contract import edit_cues_for_spectacle, infer_spectacle_type  # 生产侧同口径

AUDIT_KIND = "n2d_combat_cue_apex_audit"

# impact 型奇观（有离散命中/峰值帧才谈得上 cue↔apex 对齐）。
IMPACT_SPECTACLE = frozenset({"fight_exchange", "magic_burst"})
# 钉在命中/峰值帧上的剪辑峰值 cue（其 when 应解析出 apex 秒）。
IMPACT_CUE_NAMES = frozenset({
    "hit_stop", "screen_shake", "impact_sfx", "micro_silence_drop",
    "white_flash", "impact_or_energy_boom",
})
_SEC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*s")
_TOLERANCE = 0.4  # 与 anchor_planner apex 合并容差一致


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def parse_when_seconds(when: Any) -> Optional[float]:
    """从 cue 的 `when`（如 "命中 1.8s 狰狞峰"）抽秒数；取不到返回 None。纯函数·可测。"""
    m = _SEC_RE.search(str(when or ""))
    if not m:
        return None
    try:
        return round(float(m.group(1)), 2)
    except ValueError:
        return None


def keyframe_anchor_secs(clip: Mapping[str, Any]) -> List[float]:
    """storyboard `continuity.anchors` 里 use==keyframe 的 at_sec（anchor_planner apex-aware 注回）。纯函数·可测。"""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    out: List[float] = []
    for a in cont.get("anchors") or []:
        if isinstance(a, dict) and str(a.get("use") or "") == "keyframe":
            try:
                out.append(round(float(a.get("at_sec")), 2))
            except (TypeError, ValueError):
                continue
    return sorted(set(out))


def _clip_contract(clip: Mapping[str, Any]) -> Dict[str, Any]:
    tc = clip.get("template_contract")
    return dict(tc) if isinstance(tc, dict) else {}


def audit_clip(clip: Mapping[str, Any], clip_id: str, *, tolerance: float = _TOLERANCE) -> List[Dict[str, Any]]:
    """单镜 cue↔apex 对齐审计 → findings（C1/C2/C3）。纯函数·可测。只审 impact 型奇观。"""
    kind = infer_spectacle_type(clip)
    if kind not in IMPACT_SPECTACLE:
        return []
    duration = clip.get("duration")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return []
    contract = _clip_contract(clip)
    cues = edit_cues_for_spectacle(kind, contract)
    impact_cues = [c for c in cues if isinstance(c, dict) and c.get("cue") in IMPACT_CUE_NAMES]
    if not impact_cues:
        return []
    cue_secs = sorted({s for c in impact_cues if (s := parse_when_seconds(c.get("when"))) is not None})
    kf = keyframe_anchor_secs(clip)
    apexes = apex_anchor_seconds(clip, float(duration))
    # 核心打斗镜判定输入（供 n2d-review 升 BLOCK）：scene=场景 LOC（核心场景对账）、
    # clip_label=描述/标签文本（高潮/爆点/关键/反转等 key-scene 标记对账）。与 W2/W3 升闸同口径。
    scene = str(clip.get("scene") or clip.get("label") or "")
    clip_label = " ".join(str(clip.get(k) or "") for k in ("label", "scene", "description"))

    def _ctx(f: Dict[str, Any]) -> Dict[str, Any]:
        f.setdefault("scene", scene)
        f.setdefault("clip_label", clip_label)
        return f

    findings: List[Dict[str, Any]] = []

    # C1：impact 剪辑 cue 全部取不到秒数 → impact_frame/collision_or_apex_frame 没带 `<秒>s`，峰值浮空。
    if not cue_secs:
        findings.append({
            "clip_id": clip_id, "spectacle_type": kind, "code": "combat_apex_untimestamped",
            "level": "warn",
            "msg": (f"{clip_id}（{kind}）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when "
                    f"取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧"
                    "（如「命中 1.8s」），剪辑峰值才能钉到 apex 关键帧；否则四轴撞点无处对齐。"),
        })
        return [_ctx(f) for f in findings]  # 没有秒就谈不上后续对齐

    # C2：cue 钉了某秒，但 storyboard 没有该秒的 keyframe 锚（anchor_planner 未注回 / 手动锚跳过）。
    if not kf:
        findings.append({
            "clip_id": clip_id, "spectacle_type": kind, "code": "combat_cue_apex_no_keyframe",
            "level": "warn",
            "msg": (f"{clip_id}（{kind}）：剪辑峰值钉在 {cue_secs}s，但本镜 continuity.anchors 无 keyframe 锚——"
                    "跑 `anchor_planner.py <根> <集> --write` 让 apex 命中帧落成真关键帧，剪辑峰值才有离散落点。"),
        })
    else:
        for s in cue_secs:
            if not any(abs(s - a) <= tolerance for a in kf):
                findings.append({
                    "clip_id": clip_id, "spectacle_type": kind, "code": "combat_cue_apex_no_keyframe",
                    "level": "warn", "at_sec": s,
                    "msg": (f"{clip_id}（{kind}）：剪辑峰值 @{s}s 附近（±{tolerance}s）无 keyframe 锚"
                            f"（现有 keyframe 锚 {kf}s）——峰值引用了不存在的离散关键帧，重排锚帧或对齐 cue 秒。"),
                })
        # C3：keyframe 锚没有任何 impact 剪辑 cue 落上去 → 有命中关键帧却没在剪辑层兑现。
        for a in kf:
            if not any(abs(a - s) <= tolerance for s in cue_secs):
                findings.append({
                    "clip_id": clip_id, "spectacle_type": kind, "code": "combat_apex_no_edit_cue",
                    "level": "info", "at_sec": a,
                    "msg": (f"{clip_id}（{kind}）：keyframe 锚 @{a}s 没有 impact 剪辑峰值落上去——"
                            "该命中关键帧建议补 hit_stop/震屏/SFX/闪白峰值，让四轴撞点在剪辑层兑现。"),
                })
    return [_ctx(f) for f in findings]


# ── 装配（读盘 → 审计 → 落档） ─────────────────────────────────────────────────

def _clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I) or re.search(r"(\d+)", raw)
    return f"Clip_{int(m.group(1)):02d}" if m else f"Clip_{idx:02d}"


def storyboard_path(root: Path, ep: str) -> Path:
    return root / "脚本" / ep / "storyboard.json"


def build_audit(root: Path, ep: str) -> Dict[str, Any]:
    p = storyboard_path(root, ep)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"kind": AUDIT_KIND, "version": 1, "episode": ep, "findings": [],
                "summary": {"error": f"缺少或损坏：{p}", "combat_clips": 0, "findings": 0}}
    clips = data.get("clips") if isinstance(data, dict) else None
    findings: List[Dict[str, Any]] = []
    combat_clips = 0
    for idx, clip in enumerate(clips or [], 1):
        if not isinstance(clip, dict):
            continue
        if infer_spectacle_type(clip) in IMPACT_SPECTACLE:
            combat_clips += 1
        findings.extend(audit_clip(clip, _clip_id(clip, idx)))
    by_code: Dict[str, int] = {}
    for f in findings:
        by_code[f["code"]] = by_code.get(f["code"], 0) + 1
    return {
        "kind": AUDIT_KIND, "version": 1, "episode": ep,
        "findings": findings,
        "summary": {
            "combat_clips": combat_clips,
            "findings": len(findings),
            "by_code": by_code,
            "blocking_candidates": sum(1 for f in findings if f.get("level") == "warn"),
        },
    }


def render_md(audit: Mapping[str, Any]) -> str:
    s = audit.get("summary") or {}
    lines = [
        "# 打斗剪辑 cue ↔ apex 关键帧对齐审计",
        "",
        f"- episode: {audit.get('episode')}",
        f"- impact 型奇观镜: {s.get('combat_clips', 0)} ｜ 问题: {s.get('findings', 0)}"
        f"（warn {s.get('blocking_candidates', 0)}，核心打斗镜(核心场景/key 镜)×交付边界由 n2d-review 升 BLOCK·可签收降级）",
        "",
        "> 把「剪辑峰值必须对齐命中/apex」从散文规则兑现成对账：impact_frame 须带 `<秒>s` → "
        "anchor_planner 把该秒落成 keyframe 锚 → 剪辑 hit-stop/震屏/SFX/闪白峰值钉在同一秒。",
        "",
    ]
    if s.get("error"):
        return "\n".join(lines + [f"⚠️ {s['error']}", ""])
    if not audit.get("findings"):
        return "\n".join(lines + ["✅ 所有 impact 型打斗镜：剪辑峰值已带秒、keyframe 锚已落点、四轴撞点对齐。", ""])
    for f in audit["findings"]:
        tag = {"warn": "⚠️", "info": "ℹ️"}.get(f.get("level"), "·")
        lines.append(f"- {tag} `{f.get('code')}` {f.get('msg')}")
    lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="打斗剪辑 cue ↔ apex 关键帧对齐审计")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="只打印 JSON，不落档")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ns.episode if str(ns.episode).startswith("第") else f"第{ns.episode}集"
    audit = build_audit(root, ep)
    if ns.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 0
    out = root / "生产数据"
    _atomic_write(out / f"combat_cue_apex_{ep}.json", json.dumps(audit, ensure_ascii=False, indent=2))
    _atomic_write(out / f"combat_cue_apex_{ep}.md", render_md(audit))
    s = audit["summary"]
    print(f"[ok] 打斗 cue↔apex 对齐审计 → {out / f'combat_cue_apex_{ep}.json'}")
    print(f"     impact 打斗镜 {s.get('combat_clips', 0)} / 问题 {s.get('findings', 0)}（{s.get('by_code') or {}}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
