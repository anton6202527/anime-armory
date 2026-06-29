#!/usr/bin/env python3
"""Shot split decision planner for n2d storyboard clips.

This converts story/grammar/generation-risk signals into a pre-cost decision
artifact: keep a clip as-is, split it, require a template, add anchors, or defer
fragile pieces to compositing. It is report-first; hard blocking remains in the
existing contract/risk gates.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import shot_risk_audit as sra  # noqa: E402

KIND = "n2d_shot_split_decision_plan"

NARRATIVE_RE = re.compile(
    r"(选择|决定|代价|后果|真相|揭示|反转|爽点|打脸|觉醒|危机|集尾|钩|兑现|承诺|目标|动机|杀局|赴险)"
)
PEAK_RE = re.compile(r"(爽点|反转|觉醒|高光|集尾|CU硬切|真相|揭示|危机)")
ESTABLISH_RE = re.compile(r"(ELS|LS|大全景|大远景|全景|远景|establish|定场)", re.I)
CLOSE_RE = re.compile(r"(CU|ECU|MCU|特写|近景|大特写|反打|正反打)")
COMPOSITE_RE = re.compile(
    r"(overlay|系统面板|屏幕|文字|字幕|妖纹|证据|光幕|法阵|阵法|阵图|剪影|长安气象|VFX_|EVIDENCE_|特效)"
)
def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    return str(value or "")


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def load_storyboard(root: Path, ep: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    path = root / "脚本" / ep / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return [], f"缺 {path}"
    except json.JSONDecodeError as exc:
        return [], f"storyboard.json 不可解析：{exc}"
    clips = data.get("clips") if isinstance(data, dict) else None
    if not isinstance(clips, list) or not clips:
        return [], "storyboard.json 缺非空 clips[]"
    return [c for c in clips if isinstance(c, dict)], None


def _shot_size(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return str(cont.get("shot_size") or clip.get("shot_size") or "")


def _has_anchor(clip: Mapping[str, Any]) -> bool:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return bool(cont.get("midframe") or cont.get("anchors") or cont.get("midframe_exempt_reason"))


def narrative_weight(clip: Mapping[str, Any], idx: int) -> int:
    """0-3: how much story value would be harmed by deleting/flattening this clip."""
    blob = " ".join(str(clip.get(k) or "") for k in ("rhythm", "narrative_function", "native_speech", "visual", "label"))
    score = 0
    if idx == 1 or "first_3s" in blob or "开场" in blob:
        score += 1
    if NARRATIVE_RE.search(blob):
        score += 1
    if PEAK_RE.search(blob) or clip.get("causal_bridge") or clip.get("template") == "reveal_reaction_chain":
        score += 1
    return min(3, score)


def grammar_need(clip: Mapping[str, Any], idx: int) -> int:
    """0-3: how much film grammar suggests an explicit split/shot pattern."""
    blob = flatten(clip)
    shot_size = _shot_size(clip)
    tags = []
    if idx == 1 or ESTABLISH_RE.search(shot_size):
        tags.append("establish")
    if CLOSE_RE.search(shot_size) and PEAK_RE.search(blob):
        tags.append("reaction_or_peak_closeup")
    if str(clip.get("template") or "") in {"dialogue_shot_reverse", "reveal_reaction_chain", "public_confrontation"}:
        tags.append("structured_chain")
    if "multi_character" in blob or "character_slots" in blob or "same_frame_policy" in blob:
        tags.append("multi_subject_blocking")
    return min(3, len(tags))


def generation_risk_bucket(risk_row: Mapping[str, Any]) -> int:
    """0-5 bucket from shot_risk_audit's numeric score."""
    score = int(risk_row.get("score") or 0)
    if score <= 0:
        return 0
    if score <= 3:
        return 1
    if score <= 5:
        return 2
    if score <= 8:
        return 3
    if score <= 11:
        return 4
    return 5


def decide_actions(clip: Mapping[str, Any], risk_row: Mapping[str, Any], idx: int) -> List[str]:
    tags = set(risk_row.get("tags") or [])
    findings = risk_row.get("findings") or []
    score = int(risk_row.get("score") or 0)
    template = str(clip.get("template") or "")
    shot_size = _shot_size(clip)
    blob = flatten(clip)
    actions: List[str] = []

    def add(action: str) -> None:
        if action not in actions:
            actions.append(action)

    if any(isinstance(f, Mapping) and f.get("severity") == "must" for f in findings):
        add("template_required")
    if risk_row.get("spectacle_type") or template or "many_named_characters" in tags:
        add("template_required")
    if ("multi_character" in tags or "many_named_characters" in tags) and ("mouth_visible" in tags or CLOSE_RE.search(shot_size)):
        add("split_reaction")
    if template == "reveal_reaction_chain" or ("reveal" in blob.lower() and "急报" in blob):
        add("split_establish_detail_reaction")
    if ("large_expression_span" in tags or "long_clip_8s" in tags or score >= 8) and not _has_anchor(clip):
        add("add_mid_or_multi_anchor")
    if "vfx_or_asset" in tags and COMPOSITE_RE.search(blob) and not (template or risk_row.get("spectacle_type")):
        add("defer_to_composite")
    if score >= 11 and ("vfx_or_asset" in tags or "multi_character" in tags or risk_row.get("spectacle_type")):
        add("defer_to_composite")
    if not actions:
        add("keep_single")
    return actions


def primary_action(actions: Sequence[str]) -> str:
    priority = [
        "template_required",
        "split_establish_detail_reaction",
        "split_reaction",
        "add_mid_or_multi_anchor",
        "defer_to_composite",
        "keep_single",
    ]
    for item in priority:
        if item in actions:
            return item
    return actions[0] if actions else "keep_single"


def action_note(action: str) -> str:
    notes = {
        "keep_single": "低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。",
        "split_reaction": "把说话/多人/强表情镜拆成单人 CU、反打、听者反应，减少同框脸漂和口型压力。",
        "split_establish_detail_reaction": "按建制/证据细节/人物反应拆链，尤其适合真相揭示、搜证、关系翻转。",
        "template_required": "复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。",
        "add_mid_or_multi_anchor": "高风险长镜或大表情镜补中段锚帧/多锚/豁免说明。",
        "defer_to_composite": "把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。",
    }
    return notes.get(action, "")


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips, err = load_storyboard(root, ep)
    if err:
        return {"kind": KIND, "episode": ep, "ok": False, "findings": [
            {"severity": "must", "code": "missing_storyboard", "message": err}
        ], "decisions": []}

    risk = sra.audit(str(root), ep)
    risk_rows = risk.get("clips") or []
    by_id = {str(row.get("id")): row for row in risk_rows if isinstance(row, Mapping)}
    decisions: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        row = by_id.get(cid)
        if row is None and idx - 1 < len(risk_rows) and isinstance(risk_rows[idx - 1], Mapping):
            row = risk_rows[idx - 1]
        if row is None:
            row = {}
        actions = decide_actions(clip, row, idx)
        primary = primary_action(actions)
        tags = list(row.get("tags") or [])
        decisions.append({
            "clip": cid,
            "label": clip.get("label", ""),
            "primary_action": primary,
            "actions": actions,
            "narrative_weight": narrative_weight(clip, idx),
            "grammar_need": grammar_need(clip, idx),
            "generation_risk": generation_risk_bucket(row),
            "risk_score": row.get("score", 0),
            "risk_tags": tags,
            "reason": action_note(primary),
            "pilot_candidate": cid in {str(p.get("id")) for p in risk.get("pilot_candidates") or [] if isinstance(p, Mapping)},
        })

    must_findings = [
        {**f, "source": "shot_risk_audit"}
        for f in risk.get("findings") or []
        if isinstance(f, Mapping) and f.get("severity") == "must"
    ]
    summary = {
        "clips": len(decisions),
        "keep_single": sum(1 for d in decisions if d["primary_action"] == "keep_single"),
        "split_or_template": sum(1 for d in decisions if d["primary_action"] != "keep_single"),
        "template_required": sum(1 for d in decisions if "template_required" in d["actions"]),
        "add_anchor": sum(1 for d in decisions if "add_mid_or_multi_anchor" in d["actions"]),
        "defer_to_composite": sum(1 for d in decisions if "defer_to_composite" in d["actions"]),
    }
    return {
        "kind": KIND,
        "episode": ep,
        "ok": not must_findings,
        "summary": summary,
        "decisions": decisions,
        "findings": must_findings,
        "notes": [
            "report-first；真正硬阻塞仍由 validate_storyboard_contract / shot_risk_audit / spectacle_contract_audit 执行。",
            "本计划用于把拆镜理由提前落盘，避免出图/出视频阶段临场重判。",
        ],
    }


def render_md(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 镜头拆分决策计划",
        "",
        f"- episode: {plan.get('episode')}",
        f"- ok: {plan.get('ok')}",
        "",
        "| Clip | Action | N | G | R | Risk Tags | Reason |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in plan.get("decisions") or []:
        lines.append(
            f"| {row.get('clip')} | {row.get('primary_action')} | "
            f"{row.get('narrative_weight')} | {row.get('grammar_need')} | {row.get('generation_risk')} | "
            f"{'、'.join(row.get('risk_tags') or [])} | {row.get('reason')} |"
        )
    lines.append("")
    lines.append("N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, plan: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"shot_split_plan_{ep}.json"
    md_path = out / f"shot_split_plan_{ep}.md"
    tmp = json_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(plan) + "\n", encoding="utf-8")
    os.replace(tmp_md, md_path)
    return json_path, md_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d shot split decision planner")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if inherited risk audit has must findings")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, plan)
        plan = {**plan, "outputs": {"json": str(jp), "markdown": str(mp)}}
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_md(plan))
    if ns.strict and not plan.get("ok", False):
        return 1
    return 0 if plan.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
