#!/usr/bin/env python3
"""Signature-effect (特效镜头) detection for this line's video prompt pack.

Self-contained and line-local: loads only THIS line's
`../references/特效镜头/manifest.json` (no cross-line imports). Named signature
shots bundle 运镜 + 主体动作 + 特效 + 时基 into one paste-ready core prompt; the
video prompt pack detects effect names a shot declares, surfaces the core prompt,
and for identity_risk=high effects folds the effect's own negatives plus the
identity-lock terms into the submitted negative prompt.

Query/self-check CLI lives in `../scripts/effect_reference.py`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1] / "references" / "特效镜头" / "manifest.json"
)

# 高身份风险特效命中时默认拼上的身份锁负向词（自包含，不依赖其它模块）。
IDENTITY_LOCK_NEGATIVE_TERMS: Tuple[str, ...] = (
    "de-aging", "morphing features", "shifting jawline", "changing face shape",
    "changing clothes", "color shift", "disappearing accessories",
    "extra limbs", "extra fingers", "flickering background", "identity drift",
)


def _unique(seq) -> Tuple[str, ...]:
    out: List[str] = []
    seen = set()
    for value in seq or ():
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _load_manifest() -> Dict[str, Any]:
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 0, "effects": []}


def _build_lexicon() -> Dict[str, Dict[str, Any]]:
    lexicon: Dict[str, Dict[str, Any]] = {}
    for entry in _load_manifest().get("effects") or []:
        if not isinstance(entry, dict):
            continue
        effect_id = str(entry.get("id") or "").strip()
        name_zh = str(entry.get("name_zh") or "").strip()
        if not effect_id or not name_zh:
            continue
        triggers = _unique([
            name_zh, entry.get("name_en"), effect_id,
            *(entry.get("aliases_zh") or ()), *(entry.get("aliases_en") or ()),
        ])
        lexicon[name_zh] = {
            "id": effect_id,
            "name_en": str(entry.get("name_en") or ""),
            "category": str(entry.get("category") or ""),
            "camera_move": str(entry.get("camera_move") or ""),
            "identity_risk": str(entry.get("identity_risk") or ""),
            "triggers": triggers,
            "core_prompt_zh": str(entry.get("core_prompt_zh") or ""),
            "core_prompt_en": str(entry.get("core_prompt_en") or ""),
            "negatives": _unique(entry.get("negatives") or ()),
        }
    return lexicon


SIGNATURE_EFFECT_LEXICON: Dict[str, Dict[str, Any]] = _build_lexicon()
HIGH_IDENTITY_RISK_EFFECTS: Tuple[str, ...] = tuple(
    name for name, spec in SIGNATURE_EFFECT_LEXICON.items()
    if str(spec.get("identity_risk") or "") == "high"
)


def normalize_signature_effect(text: str) -> Dict[str, Any]:
    """把自由文本里的命名特效镜头归一到 SIGNATURE_EFFECT_LEXICON（活引用）。

    返回 {effects:[{id,zh,name_en,category,camera_move,identity_risk,core_prompt_zh,
    core_prompt_en,negatives}], recognized:bool, has_high_identity_risk:bool}。"""
    t = str(text or "")
    low = t.lower()
    effects: List[Dict[str, Any]] = []
    for zh, spec in SIGNATURE_EFFECT_LEXICON.items():
        triggers = tuple(spec.get("triggers") or ()) or (zh,)
        if any((trg in t) or (trg.lower() in low) for trg in triggers):
            effects.append({
                "id": str(spec.get("id") or ""),
                "zh": zh,
                "name_en": str(spec.get("name_en") or ""),
                "category": str(spec.get("category") or ""),
                "camera_move": str(spec.get("camera_move") or ""),
                "identity_risk": str(spec.get("identity_risk") or ""),
                "core_prompt_zh": str(spec.get("core_prompt_zh") or ""),
                "core_prompt_en": str(spec.get("core_prompt_en") or ""),
                "negatives": list(spec.get("negatives") or ()),
            })
    effects.sort(key=lambda item: len(str(item.get("zh") or "")), reverse=True)
    return {
        "effects": effects,
        "recognized": bool(effects),
        "has_high_identity_risk": any(e.get("identity_risk") == "high" for e in effects),
    }


def signature_effect_directive(text: str) -> Tuple[str, List[str], bool]:
    """检测文本中声明的命名特效镜头，返回 (指引行, 追加负向词, 是否高身份风险)。

    命中即暴露该特效可粘贴核心 prompt 与回链运镜；identity_risk=high 时把该特效
    negatives 与身份锁负向词并入以强化提交负向 prompt。未命中返回空，不改变既有输出。"""
    sig = normalize_signature_effect(text)
    effects = sig.get("effects") or []
    if not effects:
        return "", [], False
    primary = effects[0]
    extra_negatives: List[str] = []
    high_risk = bool(sig.get("has_high_identity_risk"))
    if high_risk:
        for effect in effects:
            if effect.get("identity_risk") == "high":
                extra_negatives.extend(effect.get("negatives") or [])
        extra_negatives.extend(IDENTITY_LOCK_NEGATIVE_TERMS)
    hit_names = "、".join(f"{e.get('zh')}({e.get('identity_risk')})" for e in effects)
    line = (
        f"特效镜头/Signature Effect：命中={hit_names}；运镜链={primary.get('camera_move')}；"
        f"核心 prompt（{primary.get('zh')}）：{primary.get('core_prompt_zh')}"
    )
    if high_risk:
        line += "；⚠️ 高身份风险特效：已自动拼身份锁负向词；换装/换脸类须确认为有意形变，不得用于假冒真实人物。"
    return line, extra_negatives, high_risk
