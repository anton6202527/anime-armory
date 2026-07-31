#!/usr/bin/env python3
"""Pre-image-prompt contract audit for high-dynamic and large-scale shots."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    LARGE_ESTABLISHING_FIELDS,
    SPECTACLE_PLAN_KIND,
    clip_blob,
    default_degrade_plan,
    field_missing,
    infer_spectacle_type,
    missing_fields,
    spectacle_advisory_fields,
    spectacle_recommendations,
    spectacle_required_fields,
)

try:  # 武器/武技对撞检测（单一真值源·与出图 runner 注入同口径）
    from n2d_const import is_weapon_clash_shot
except Exception:  # pragma: no cover - 异常布局兜底
    def is_weapon_clash_shot(text):  # type: ignore
        return False


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def storyboard_path(root: str, ep: str) -> Path:
    return Path(root) / "脚本" / ep / "storyboard.json"


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def load_storyboard(root: str, ep: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    path = storyboard_path(root, ep)
    if not path.is_file():
        return None, f"缺 storyboard.json: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"storyboard.json 不可解析：{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "storyboard.json 顶层必须是对象"
    return data, None


def _large_contract(clip: Mapping[str, Any]) -> Dict[str, Any]:
    for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
        value = clip.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _clip_spectacle_contract(clip: Mapping[str, Any], kind: str) -> Dict[str, Any]:
    if kind == "large_establishing":
        return _large_contract(clip)
    value = clip.get("template_contract")
    return dict(value) if isinstance(value, dict) else {}


def _finding(clip: str, severity: str, code: str, message: str, **extra: Any) -> Dict[str, Any]:
    out = {"clip": clip, "severity": severity, "code": code, "message": message}
    out.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    return out


def audit_clip(clip: Mapping[str, Any], idx: int) -> Dict[str, Any]:
    cid = clip_id(clip, idx)
    kind = infer_spectacle_type(clip)
    findings: List[Dict[str, Any]] = []
    if not kind:
        return {"clip": cid, "spectacle_type": None, "findings": [], "required_fields": [], "missing_fields": []}

    template = str(clip.get("template") or "").strip()
    contract = _clip_spectacle_contract(clip, kind)
    required = list(spectacle_required_fields(kind))

    if kind in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        if template != kind:
            findings.append(_finding(
                cid,
                "must",
                "missing_spectacle_template",
                f"疑似 {kind} 高动态镜头，但 template 必须显式写成 {kind}。",
                detected_from=clip_blob(clip)[:240],
            ))
        if not isinstance(clip.get("template_contract"), dict):
            findings.append(_finding(
                cid,
                "must",
                "missing_template_contract",
                f"template={template or '(missing)'} 缺 template_contract；高动态镜头不能只靠散文 prompt。",
            ))
        elif str(contract.get("template_id") or "").strip() != kind:
            findings.append(_finding(
                cid,
                "must",
                "template_id_mismatch",
                f"template_contract.template_id 必须等于 {kind}。",
            ))
    elif kind == "large_establishing" and not contract:
        findings.append(_finding(
            cid,
            "must",
            "missing_large_scene_contract",
            "大场景/大场面镜头缺 large_scene_contract 或 spectacle_contract；必须先写 geography/scale/parallax/landmark。",
        ))

    missing = missing_fields(contract, required) if contract else required
    for field in missing:
        findings.append(_finding(
            cid,
            "must",
            "missing_spectacle_field",
            f"{kind} 契约字段缺失或为空：{field}",
            field=field,
        ))

    # 战斗视觉盛宴·建议字段（advisory·WARN）：表情/二级运动/apex 光效——四轴在命中帧汇聚。缺则提示补，不阻断。
    advisory = list(spectacle_advisory_fields(kind))
    missing_advisory = missing_fields(contract, advisory) if contract else advisory
    for field in missing_advisory:
        findings.append(_finding(
            cid,
            "warn",
            "missing_spectacle_polish_field",
            f"{kind} 缺战斗精修字段「{field}」（建议·非阻断）：补上让动作/表情/光线在命中帧同时撞点=视觉盛宴。",
            field=field,
        ))

    # 兵器/武技对撞撞点帧（advisory·WARN）：治"打斗被拆成单人正反打/单向命中、很少出现双方兵器硬碰硬相交"。
    # 本镜文本含 clash 词（相交/格挡/对撞/较力/迸火…）却没写 clash_frame(melee)/collision_or_apex_frame(法术)
    # → 提示单独出一帧撞点（接触点为焦点·face-safe·双主体同框）。magic_burst 的撞点已在必填集，这里主要
    # 补 fight_exchange 的 melee 兵器相交盲区。缺则提示补，不阻断。
    clash_missing = False
    if kind in ("fight_exchange", "magic_burst") and is_weapon_clash_shot(clip_blob(clip)):
        has_clash = bool(str(contract.get("clash_frame") or "").strip()
                         or str(contract.get("collision_or_apex_frame") or "").strip())
        if not has_clash:
            clash_missing = True
            findings.append(_finding(
                cid,
                "info",
                "missing_weapon_clash_frame",
                f"{kind} 本镜含兵器/武技相交（格挡/对撞/较力/迸火…）却没写 clash_frame / "
                "collision_or_apex_frame 撞点帧——建议单独出一帧『双方兵器在接触点硬碰硬相交·迸火星·力对冲』"
                "（接触点为焦点·face-safe·双主体同框，不是单人正反打），别让相交瞬间被拆成单向命中。",
                field="clash_frame",
            ))

    return {
        "clip": cid,
        "spectacle_type": kind,
        "required_fields": required,
        "missing_fields": missing,
        "missing_polish_fields": missing_advisory,
        "clash_frame_missing": clash_missing,
        "recommendations": spectacle_recommendations(kind),
        "degrade_plan": str(contract.get("degrade_plan") or default_degrade_plan(kind)),
        "findings": findings,
    }


def audit(root: str, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    data, err = load_storyboard(root, ep)
    if err:
        return {
            "kind": SPECTACLE_PLAN_KIND,
            "episode": ep,
            "ok": False,
            "clips": [],
            "findings": [{"severity": "must", "code": "missing_storyboard", "message": err}],
            "summary": {"spectacle_clips": 0, "must": 1, "warn": 0},
        }
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips:
        return {
            "kind": SPECTACLE_PLAN_KIND,
            "episode": ep,
            "ok": False,
            "clips": [],
            "findings": [{"severity": "must", "code": "empty_clips", "message": "storyboard.json 缺非空 clips[]。"}],
            "summary": {"spectacle_clips": 0, "must": 1, "warn": 0},
        }

    rows = [audit_clip(c if isinstance(c, dict) else {}, i) for i, c in enumerate(clips, 1)]
    spectacle = [r for r in rows if r.get("spectacle_type")]
    findings: List[Dict[str, Any]] = []
    for row in spectacle:
        findings.extend(row.get("findings") or [])
    must = sum(1 for f in findings if f.get("severity") == "must")
    warn = sum(1 for f in findings if f.get("severity") == "warn")
    clash_missing = sum(1 for r in spectacle if r.get("clash_frame_missing"))
    return {
        "kind": SPECTACLE_PLAN_KIND,
        "episode": ep,
        "ok": must == 0,
        "clips": spectacle,
        "findings": findings,
        "summary": {"spectacle_clips": len(spectacle), "must": must, "warn": warn,
                    "weapon_clash_frame_missing": clash_missing},
    }


def print_human(result: Mapping[str, Any]) -> None:
    summary = result.get("summary") if isinstance(result.get("summary"), Mapping) else {}
    print(f"# 高动态/大场景契约审计 — {result.get('episode')}")
    print(f"spectacle_clips={summary.get('spectacle_clips', 0)} must={summary.get('must', 0)} warn={summary.get('warn', 0)}"
          f" 兵器相交撞点帧缺={summary.get('weapon_clash_frame_missing', 0)}")
    if not result.get("findings"):
        print("- PASS：高动态/大场景镜头结构契约已就位。")
        return
    for f in result.get("findings") or []:
        print(f"- {str(f.get('severity')).upper()} {f.get('clip', '-')}: {f.get('message')}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d spectacle/action storyboard contract audit")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ns = ap.parse_args(argv)
    result = audit(ns.root.rstrip("/"), ep_label(ns.episode))
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    findings = result.get("findings") or []
    has_must = any(f.get("severity") == "must" for f in findings if isinstance(f, Mapping))
    has_warn = any(f.get("severity") == "warn" for f in findings if isinstance(f, Mapping))
    if ns.strict and (has_must or has_warn):
        return 1
    return 1 if has_must else 0


if __name__ == "__main__":
    raise SystemExit(main())
