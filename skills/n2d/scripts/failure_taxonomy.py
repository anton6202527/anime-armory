#!/usr/bin/env python3
"""Classify n2d review findings by root-cause layer and escalate report-only risks.

This script is read-only unless --write is passed.  It consumes existing gate,
score, consistency and review-ui findings; it does not regenerate media.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
LIB = SCRIPT_DIR.parents[0] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # noqa: E402
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore


VERSION = 1
OUT_JSON = "failure_taxonomy_{episode}.json"
OUT_MD = "failure_taxonomy_{episode}.md"

_CATEGORY_PATTERNS = [
    ("script", ("剧本", "改编", "剧情", "节奏", "台词", "对白", "旁白", "因果", "动机", "伏笔", "爽点", "story", "beat", "dialogue", "adapt")),
    ("director_blocking", ("导演", "分镜", "景别", "机位", "轴线", "调度", "运镜", "动作线", "转场", "接缝", "连续性", "blocking", "staging", "camera", "seam")),
    ("production_breakdown", ("制片", "拆解", "call_sheet", "资产", "身份注册", "continuity_breakdown", "production_breakdown", "ledger", "state_continuity")),
    ("image_prompt", ("出图", "图像", "prompt", "脸", "五官", "发型", "服装", "角色一致", "场景", "道具", "风格", "光影", "image_qc", "reference")),
    ("backend", ("后端", "模型", "路由", "seed", "motion control", "mouth", "口型", "唇形", "音画", "video_backend", "lipsync", "provider")),
    ("qc", ("qc", "review", "score", "评分", "验收", "新鲜度", "stale", "指纹", "freshness", "校准", "golden")),
]

_CORE_MARKERS = ("核心", "关键", "主角", "脸", "口型", "唇形", "高潮", "开场", "结尾", "封面", "hero", "critical", "must_fix")
_INTERNAL_INTENTS = {"", "internal", "internal_only", "demo", "demo_only", "research", "private"}
_CATEGORY_ACTIONS = {
    "script": {
        "owner": "编剧/故事编辑",
        "fix": "回到剧本改编、voiceover、伏笔/状态账本，先修动机、因果、台词、信息回报和集尾钩。",
        "rerun": [
            "python3 skills/n2d-review/scripts/gate.py {root} {episode} review --json",
            "python3 skills/n2d/scripts/failure_taxonomy.py {root} {episode} --json",
        ],
    },
    "director_blocking": {
        "owner": "导演/分镜",
        "fix": "回到导演排戏包、轴线图、景别进程、转场/首尾帧接力，先修可拍性和剪辑连续性。",
        "rerun": [
            "python3 skills/n2d-script/scripts/director_blocking_pack.py {root} {episode} check --json",
            "python3 skills/n2d-review/scripts/gate.py {root} {episode} image --json",
        ],
    },
    "production_breakdown": {
        "owner": "制片主任/场记",
        "fix": "回到 production_breakdown、continuity_breakdown、ai_call_sheet、identity/asset registry 和 production_events。",
        "rerun": [
            "python3 skills/n2d-script/scripts/production_breakdown.py {root} {episode} check --json",
            "python3 skills/n2d/scripts/release_verdict.py {root} {episode} --json",
        ],
    },
    "image_prompt": {
        "owner": "出图提示/美术资产",
        "fix": "回到参考包、定妆、场景 atlas、逐镜 prompt 和 image_qc，禁止只靠文字外貌描述补救。",
        "rerun": [
            "python3 skills/n2d-image/scripts/image_qc.py {root} {episode} --prop-shape-report",
            "python3 skills/n2d-review/scripts/gate.py {root} {episode} image --json",
        ],
    },
    "backend": {
        "owner": "模型路由/后端适配",
        "fix": "回到模型路由、能力证据、seed/参考输入、口型/原生音画策略和失败降级方案。",
        "rerun": [
            "python3 skills/n2d-model-router/scripts/router.py {root} {episode} --json",
            "python3 skills/n2d/scripts/release_verdict.py {root} {episode} --json",
        ],
    },
    "qc": {
        "owner": "QC/验收",
        "fix": "重跑过期 QC、score、ledger、review-ui 和校准集，确认报告指纹对应当前产物。",
        "rerun": [
            "python3 skills/n2d-review/scripts/consistency_ledger.py {root} {episode}",
            "python3 skills/n2d-review-ui/scripts/review_ui.py {root} {episode} --write --export-findings --markdown",
            "python3 skills/n2d/scripts/release_verdict.py {root} {episode} --json",
        ],
    },
}

_PREVENTIVE_RULE_BY_CATEGORY = {
    "script": {
        "gate": "episode_promise_gate",
        "template_section": "episode_promise",
        "rule": "高频剧情/动机/因果问题出现后，提升每集承诺合同的 promise/obstacle/payoff/cliffhanger 与 source_trace_ids 填写要求。",
    },
    "director_blocking": {
        "gate": "interaction_physics_gate",
        "template_section": "interaction_physics",
        "rule": "高频调度/接缝/动作问题出现后，提升动作分解、屏幕站位、接触点、首尾帧/转场降级方案要求。",
    },
    "production_breakdown": {
        "gate": "reference_slot_gate",
        "template_section": "reference_slots",
        "rule": "高频资产/场记问题出现后，提升引用槽位 path/hash、状态机、适用后端和降级策略要求。",
    },
    "image_prompt": {
        "gate": "reference_slot_gate",
        "template_section": "reference_slots",
        "rule": "高频脸漂/道具漂/风格漂问题出现后，提升真实参考、多视角、身份锁句和 prompt 继承回执要求。",
    },
    "backend": {
        "gate": "audio_timing_gate",
        "template_section": "audio_timing",
        "rule": "高频口型/路由/模型能力问题出现后，提升 mouth_policy、voice_or_native_policy、fallback backend 和能力证据要求。",
    },
    "qc": {
        "gate": "release_verdict",
        "template_section": "release_evidence",
        "rule": "高频 QC 新鲜度/验收问题出现后，提升证据指纹、母版 hash、review-ui/ledger 新鲜度和人工签收要求。",
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def canonical_severity(row: Mapping[str, Any]) -> str:
    raw = str(row.get("severity") or row.get("sev") or row.get("level") or "").strip().lower()
    if raw in {"block", "blocked", "fail", "fatal", "error", "high"}:
        return "block"
    if raw in {"warn", "warning", "medium"}:
        return "warn"
    if raw in {"info", "low", "note", "advisory"}:
        return "info"
    return "warn"


def finding_text(row: Mapping[str, Any]) -> str:
    parts = [
        row.get("dimension") or row.get("dim") or row.get("category") or "",
        row.get("message") or row.get("msg") or row.get("reason") or "",
        row.get("loc") or row.get("asset") or row.get("clip") or row.get("shot") or row.get("png") or "",
        row.get("suggestion") or row.get("fix") or "",
    ]
    return " ".join(str(p) for p in parts if p not in (None, "", [], {}))


def classify_category(row: Mapping[str, Any], source_name: str = "") -> str:
    explicit = str(row.get("root_cause_layer") or row.get("return_to") or "").strip()
    if explicit in _CATEGORY_ACTIONS:
        return explicit
    text = (finding_text(row) + " " + source_name).lower()
    for category, markers in _CATEGORY_PATTERNS:
        if any(marker.lower() in text for marker in markers):
            return category
    return "qc"


def source_stage(path: Path) -> str:
    name = path.name
    if name.startswith("gate_findings_"):
        body = name[len("gate_findings_"):]
        return body.split("_第", 1)[0] or "gate"
    if name.startswith("review_ui"):
        return "review_ui"
    if "consistency" in name or "ledger" in name:
        return "consistency"
    if "score" in name:
        return "score"
    return "review"


def iter_finding_files(root: Path, episode: str) -> Iterable[Path]:
    prod = production_dir(root)
    patterns = [
        f"gate_findings_*_{episode}.json",
        f"*findings*{episode}.json",
        f"consistency_ledger_{episode}.json",
    ]
    seen = set()
    for pattern in patterns:
        for raw in sorted(glob.glob(str(prod / pattern))):
            path = Path(raw)
            if path in seen:
                continue
            seen.add(path)
            yield path


def rows_from_payload(data: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for key in ("findings", "issues", "blocks", "warnings"):
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    rows.append(dict(item))
                elif isinstance(item, str):
                    rows.append({"severity": "warn", "message": item})
    domains = data.get("domains")
    if isinstance(domains, list):
        for item in domains:
            if not isinstance(item, dict):
                continue
            counts = item.get("counts") if isinstance(item.get("counts"), dict) else {}
            for sev in ("block", "high", "warn"):
                n = int(counts.get(sev) or 0)
                if n:
                    rows.append({
                        "severity": "block" if sev in {"block", "high"} else "warn",
                        "dimension": item.get("label") or item.get("domain"),
                        "message": f"consistency ledger {sev}={n}",
                    })
    return rows


def compliance_intent(root: Path) -> str:
    data = load_json(root / "合规" / "compliance_manifest.json")
    if not isinstance(data, dict):
        return ""
    return str(data.get("distribution_intent") or data.get("release_intent") or "").strip().lower()


def score_signal(root: Path, episode: str) -> Dict[str, Any]:
    path = production_dir(root) / f"score_{episode}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return {"available": False, "low": False, "path": relpath(root, path)}
    score = data.get("total_score", data.get("score"))
    threshold = data.get("threshold", 80)
    low = str(data.get("status") or "").strip().lower() not in {"pass", "ok"} if data.get("status") else False
    try:
        low = low or (float(score) < float(threshold))
    except Exception:
        pass
    return {"available": True, "low": low, "score": score, "threshold": threshold, "status": data.get("status"), "path": relpath(root, path)}


def escalation_reasons(row: Mapping[str, Any], *, repeated: bool, low_score: bool, production_mode: bool, distribution_mode: bool) -> List[str]:
    sev = canonical_severity(row)
    if sev == "block":
        return ["already_block"]
    if sev != "warn":
        return []
    text = finding_text(row).lower()
    reasons: List[str] = []
    if any(marker.lower() in text for marker in _CORE_MARKERS):
        reasons.append("core_shot_or_core_identity")
    if repeated:
        reasons.append("repeated_report_only_findings")
    if low_score:
        reasons.append("low_score_context")
    if production_mode:
        reasons.append("production_profile")
    if distribution_mode:
        reasons.append("distribution_profile")
    return reasons


def _format_commands(commands: Sequence[str], root: Path, episode: str) -> List[str]:
    return [cmd.format(root=str(root), episode=episode) for cmd in commands]


def return_plan(root: Path, episode: str, items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Mapping[str, Any]]] = {}
    for item in items:
        buckets.setdefault(str(item.get("category") or "qc"), []).append(item)
    rows: List[Dict[str, Any]] = []
    for category, rows_for_category in sorted(buckets.items(), key=lambda kv: (-sum(1 for i in kv[1] if i.get("escalated_severity") == "block"), kv[0])):
        action = _CATEGORY_ACTIONS.get(category, _CATEGORY_ACTIONS["qc"])
        blocks = sum(1 for item in rows_for_category if item.get("escalated_severity") == "block")
        rows.append({
            "category": category,
            "owner": action["owner"],
            "count": len(rows_for_category),
            "block": blocks,
            "fix_strategy": action["fix"],
            "rerun_after_fix": _format_commands(action["rerun"], root, episode),
            "sample_messages": [str(i.get("message") or i.get("loc") or "")[:160] for i in rows_for_category[:3]],
        })
    return rows


def preventive_rule_updates(items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Mapping[str, Any]]] = {}
    for item in items:
        buckets.setdefault(str(item.get("category") or "qc"), []).append(item)
    updates: List[Dict[str, Any]] = []
    for category, rows in sorted(buckets.items()):
        blocks = [row for row in rows if row.get("escalated_severity") == "block"]
        if len(rows) < 3 and not blocks:
            continue
        spec = _PREVENTIVE_RULE_BY_CATEGORY.get(category, _PREVENTIVE_RULE_BY_CATEGORY["qc"])
        repeated_dimensions = Counter(str(row.get("dimension") or row.get("message") or "") for row in rows)
        updates.append({
            "category": category,
            "gate": spec["gate"],
            "template_section": spec["template_section"],
            "severity": "must_update" if blocks or len(rows) >= 3 else "suggested",
            "trigger_count": len(rows),
            "block_count": len(blocks),
            "rule": spec["rule"],
            "sample_dimensions": [key for key, _ in repeated_dimensions.most_common(5) if key],
            "write_target": "脚本/<集>/preventive_contracts.json 或对应 *_pack scaffold 模板",
        })
    return updates


def build_taxonomy(root: Path, episode: str, *, profile: str = "demo") -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    raw_rows: List[Dict[str, Any]] = []
    for path in iter_finding_files(root, episode):
        data = load_json(path)
        for row in rows_from_payload(data):
            row["_source"] = relpath(root, path)
            row["_stage"] = source_stage(path)
            raw_rows.append(row)

    dim_counts = Counter(str(r.get("dimension") or r.get("dim") or classify_category(r, r.get("_source", ""))) for r in raw_rows)
    score = score_signal(root, episode)
    intent = compliance_intent(root)
    production_mode = str(profile or "").strip().lower() == "production"
    distribution_mode = bool(intent and intent not in _INTERNAL_INTENTS)

    items: List[Dict[str, Any]] = []
    for row in raw_rows:
        dim_key = str(row.get("dimension") or row.get("dim") or classify_category(row, row.get("_source", "")))
        sev = canonical_severity(row)
        reasons = escalation_reasons(
            row,
            repeated=dim_counts[dim_key] >= 3,
            low_score=bool(score.get("low")),
            production_mode=production_mode,
            distribution_mode=distribution_mode,
        )
        escalated = "block" if "already_block" in reasons or reasons else sev
        category = classify_category(row, row.get("_source", ""))
        action = _CATEGORY_ACTIONS.get(category, _CATEGORY_ACTIONS["qc"])
        owner = str(row.get("owner") or action["owner"])
        minimal_scope = str(row.get("minimal_rerun_scope") or row.get("rerun_scope") or action["fix"])
        items.append({
            "category": category,
            "root_cause_layer": category,
            "source": row.get("_source"),
            "source_stage": row.get("_stage"),
            "dimension": row.get("dimension") or row.get("dim") or "",
            "severity": sev,
            "escalated_severity": escalated,
            "escalation_reasons": reasons,
            "message": row.get("message") or row.get("msg") or row.get("reason") or "",
            "loc": row.get("loc") or row.get("asset") or row.get("clip") or row.get("shot") or row.get("png") or "",
            "return_to": category,
            "owner": owner,
            "minimal_rerun_scope": minimal_scope,
            "fix_strategy": action["fix"],
            "root_cause": {
                "layer": category,
                "owner": owner,
                "minimal_rerun_scope": minimal_scope,
                "source": "finding" if row.get("root_cause_layer") else "taxonomy_fallback",
            },
        })

    by_category = Counter(item["category"] for item in items)
    escalated_blocks = sum(1 for item in items if item["escalated_severity"] == "block")
    payload = {
        "kind": "n2d_failure_taxonomy",
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "profile": profile,
        "generated_at": now_iso(),
        "distribution_intent": intent,
        "score": score,
        "summary": {
            "findings": len(items),
            "escalated_blocks": escalated_blocks,
            "by_category": dict(sorted(by_category.items())),
        },
        "status": "blocked" if escalated_blocks else ("warn" if items else "pass"),
        "return_plan": return_plan(root, episode, items),
        "preventive_rule_updates": preventive_rule_updates(items),
        "items": items,
    }
    return payload


def render_markdown(payload: Mapping[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# n2d Failure Taxonomy",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- 升级 block：{summary.get('escalated_blocks', 0)}",
        f"- 分类：{summary.get('by_category', {})}",
        "",
        "## Return Plan",
        "",
        "| category | owner | block | fix | rerun |",
        "|---|---|---:|---|---|",
    ]
    for row in payload.get("return_plan") or []:
        rerun = "<br>".join(f"`{cmd}`" for cmd in row.get("rerun_after_fix") or [])
        fix = str(row.get("fix_strategy") or "").replace("\n", " ")[:220]
        lines.append(f"| {row.get('category')} | {row.get('owner')} | {row.get('block')} | {fix} | {rerun} |")
    lines.extend([
        "",
        "## Findings",
        "",
        "| category | stage | severity | escalated | reason | message |",
        "|---|---|---|---|---|---|",
    ])
    for item in payload.get("items") or []:
        msg = str(item.get("message") or item.get("loc") or "").replace("\n", " ")[:180]
        reason = ",".join(item.get("escalation_reasons") or []) or "-"
        lines.append(f"| {item.get('category')} | {item.get('source_stage')} | {item.get('severity')} | {item.get('escalated_severity')} | {reason} | {msg} |")
    updates = payload.get("preventive_rule_updates") or []
    if updates:
        lines.extend(["", "## Preventive Rule Updates", "", "| category | gate | severity | rule |", "|---|---|---|---|"])
        for row in updates:
            rule = str(row.get("rule") or "").replace("\n", " ")[:220]
            lines.append(f"| {row.get('category')} | {row.get('gate')} | {row.get('severity')} | {rule} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, episode: str, payload: Mapping[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / OUT_JSON.format(episode=episode)
    md_path = out / OUT_MD.format(episode=episode)
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="classify n2d findings and escalate report-only risks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--profile", choices=["demo", "production"], default="demo")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    payload = build_taxonomy(root, ns.episode, profile=ns.profile)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload["episode"], payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
