#!/usr/bin/env python3
"""P-3 production handoff pack for n2d.

This is the production-management layer after the stage-2 storyboard and before
image prompt generation. It translates the director/storyboard intent into the
documents a small crew would need before shooting: scene breakdown, continuity
breakdown, and an AI call sheet.

Usage:
  python3 production_breakdown.py <作品根> 第N集 scaffold --write
  python3 production_breakdown.py <作品根> 第N集 check --json --write-missing
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

KIND = "n2d_production_handoff_pack"
CHECK_KIND = "n2d_production_handoff_pack_check"
VERSION = 1
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)
CONFIRMED_RE = re.compile(r"(?im)^\s*(?:status|状态)\s*[:：]\s*(?:confirmed|已确认|pass|通过)\s*$")

REQUIRED_FILES = (
    "production_breakdown.json",
    "continuity_breakdown.json",
    "continuity_bible.json",
    "ai_shooting_schedule.json",
    "ai_call_sheet.md",
)
BATCH_SEED_JSON = "ai_shooting_schedule_batch_seed_{episode}.json"
BATCH_SEED_MD = "ai_shooting_schedule_batch_seed_{episode}.md"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_json_if_absent(path: Path, payload: Mapping[str, Any], *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_json_atomic(path, payload)
    return True


def write_text_if_absent(path: Path, text: str, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_atomic(path, text)
    return True


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_fingerprint(root: Path, rels: Iterable[str]) -> Dict[str, Any]:
    files: Dict[str, str | None] = {}
    h = hashlib.sha256()
    for rel in sorted({str(r).replace(os.sep, "/") for r in rels}):
        path = root / rel
        digest = file_sha256(path) if path.is_file() else None
        files[rel] = digest
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((digest or "-").encode("ascii"))
        h.update(b"\n")
    return {"files": files, "sha": h.hexdigest()}


def fingerprint_is_fresh(recorded: Any, root: Path) -> bool | None:
    if not isinstance(recorded, Mapping):
        return None
    files = recorded.get("files")
    sha = recorded.get("sha")
    if not isinstance(files, Mapping) or not isinstance(sha, str) or not sha:
        return None
    return artifact_fingerprint(root, [str(k) for k in files.keys()])["sha"] == sha


def handoff_input_rels(ep: str) -> List[str]:
    return [
        "设定库/source_comprehension.json",
        f"脚本/{ep}/voiceover.txt",
        f"脚本/{ep}/storyboard.json",
        f"脚本/{ep}/镜头时长.json",
        f"脚本/{ep}/director_blocking_pack.json",
        f"脚本/{ep}/preventive_contracts.json",
        f"生产数据/script_quality_contract_{ep}.json",
    ]


def _episode_dir(root: Path, ep: str) -> Path:
    return root / "脚本" / ep


def _clips(root: Path, ep: str) -> List[Dict[str, Any]]:
    data = load_json(_episode_dir(root, ep) / "storyboard.json")
    if not isinstance(data, dict):
        return []
    clips = data.get("clips") or data.get("shots") or []
    return [c for c in clips if isinstance(c, dict)]


def _clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or f"Clip_{idx:02d}")


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_items(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for value in values:
        if isinstance(value, Mapping):
            text = str(value.get("id") or value.get("text") or value).strip()
        else:
            text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _clip_continuity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    return clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}


def _clip_entity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    return clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), dict) else {}


def _clip_template(clip: Mapping[str, Any]) -> str:
    return str(clip.get("template") or clip.get("rhythm") or "standard_scene").strip()


def _screen_texts(clip: Mapping[str, Any]) -> List[Any]:
    return [x for x in _as_list(clip.get("screen_text_lines")) if x]


def _vfx_assets(clip: Mapping[str, Any]) -> List[str]:
    assets = []
    for item in _clean_items(_as_list(clip.get("object_ids"))):
        if item.startswith("VFX_") or "百妖谱" in item or "overlay" in item.lower():
            assets.append(item)
    return assets


def _overlay_policy(clip: Mapping[str, Any]) -> str:
    if _screen_texts(clip):
        return "所有可读系统文字、数值和状态面板只交 compose overlay；生图/视频只画空面板与安全留白。"
    if _vfx_assets(clip):
        return "VFX 可画形状/光效；若出现可读文字或数值，一律改由 compose overlay。"
    return "本镜无可读画中文字；字幕、花字和临时说明统一在 compose 层处理。"


def _backend_risk(clip: Mapping[str, Any]) -> str:
    template = _clip_template(clip)
    continuity = _clip_continuity(clip)
    anchors = _as_list(continuity.get("anchors"))
    risks: List[str] = []
    if anchors:
        risks.append(f"多锚帧 {len(anchors)} 个，按首/中/尾关键帧拆分控制。")
    if any(token in template for token in ("fight", "action", "追逐", "打斗")):
        risks.append("高运动镜头，动作线、命中点和收势要拆清，失败时降级为更短 Clip。")
    if "system" in template or _screen_texts(clip):
        risks.append("系统面板镜头禁止烤字，保留干净面板区给后期叠字。")
    if "dialogue" in template or "CU" in str(continuity.get("shot_size") or ""):
        risks.append("近景/对话镜优先锁脸和视线，口型只做视觉占位。")
    return " ".join(risks) if risks else "常规镜头：继承本场轴线、光位和身份参考，按首尾帧接力。"


def _department_notes(clip: Mapping[str, Any]) -> Dict[str, str]:
    continuity = _clip_continuity(clip)
    characters = ", ".join(_clean_items(_as_list(clip.get("character_ids")))) or "无具名角色"
    objects = ", ".join(_clean_items(_as_list(clip.get("object_ids")))) or "无关键道具"
    shot_size = str(continuity.get("shot_size") or "").strip() or "按 storyboard 景别"
    eyeline = str(continuity.get("eyeline") or "").strip() or "按本场轴线接力"
    transition = str(continuity.get("transition") or "").strip() or "cut"
    return {
        "art": f"场景 {clip.get('location_id') or clip.get('scene') or '本场主场景'}；入画角色 {characters}；关键物件 {objects}。",
        "camera": f"景别/机位：{shot_size}；视线/轴线：{eyeline}；模板：{_clip_template(clip)}。",
        "post": f"转场 {transition}；{_overlay_policy(clip)}",
    }


def _sfx_notes(clip: Mapping[str, Any]) -> str:
    template = _clip_template(clip)
    notes = ["荒野风声/环境底噪按场景 AMBIENT 延续"]
    objects = " ".join(_clean_items(_as_list(clip.get("object_ids"))))
    if "WEAPON" in objects or "刀" in objects:
        notes.append("横刀出鞘、刀锋破风、金纹灌刀")
    if "fight" in template:
        notes.append("冲撞、妖风、命中点、收势重音")
    if "system" in template or _screen_texts(clip):
        notes.append("百妖谱面板亮起/计数跳变 UI 音效")
    return "；".join(notes) + "。"


def _wardrobe_state(clip: Mapping[str, Any]) -> str:
    entity = _clip_entity(clip)
    required = _clean_items(_as_list(entity.get("required_presence")))
    if not required:
        required = _clean_items(_as_list(clip.get("character_ids")))
    state = "、".join(required) if required else "按 storyboard 入画角色"
    return f"按本镜 required_presence 锁定：{state}；血尘、战损、泪痕和形态只按 start_state→end_state 演进。"


def _props_continuity(clip: Mapping[str, Any]) -> str:
    objects = _clean_items(_as_list(clip.get("object_ids")))
    if not objects:
        return "本镜无关键持物；场景常驻物按 LOC 布局延续。"
    return "关键物件保持可追踪：" + "、".join(objects) + "；位置变化必须由动作或转场解释。"


def _knowledge_state(clip: Mapping[str, Any], *, confirmed: bool = False) -> Any:
    entity = _clip_entity(clip)
    explicit = entity.get("knowledge_state")
    if explicit:
        return explicit
    if not confirmed:
        return "待补：角色此刻知道/不知道什么"
    characters = _clean_items(_as_list(entity.get("required_presence"))) or _clean_items(_as_list(clip.get("character_ids")))
    subject = "、".join(characters) if characters else "本镜角色"
    continuity = _clip_continuity(clip)
    start = str(continuity.get("start_state") or "").strip()
    end = str(continuity.get("end_state") or "").strip()
    change = f"{start}→{end}" if start and end else str(clip.get("label") or clip.get("scene") or "本镜事件")
    return f"{subject}只掌握本镜画面内可见变化（{change}）；不提前知道后续转折。"


def _screen_direction(clip: Mapping[str, Any]) -> str:
    continuity = _clip_continuity(clip)
    eyeline = str(continuity.get("eyeline") or "").strip()
    transition = str(continuity.get("transition") or "").strip() or "cut"
    return f"守本场左右轴线；视线接力：{eyeline or '按角色对手/目标方向'}；转场方式：{transition}。"


def _production_breakdown(root: Path, ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> Dict[str, Any]:
    scenes = []
    for idx, clip in enumerate(clips, start=1):
        vfx_assets = _vfx_assets(clip)
        continuity = _clip_continuity(clip)
        need_endframe = bool(continuity.get("need_endframe") or continuity.get("need_end") or continuity.get("endframe"))
        endframe = clip.get("endframe_png") or continuity.get("endframe_png") or continuity.get("last_frame") or ""
        if not need_endframe:
            endframe = ""
        scenes.append({
            "clip_id": _clip_id(clip, idx),
            "label": clip.get("label") or "",
            "scene": clip.get("scene") or "",
            "location_id": clip.get("location_id") or "",
            "characters": _as_list(clip.get("character_ids")),
            "props_and_objects": _as_list(clip.get("object_ids")),
            "wardrobe_makeup_state": _wardrobe_state(clip),
            "vfx_or_overlay": {
                "system_panels": [x for x in _as_list(clip.get("screen_text_lines")) if x],
                "vfx_assets": vfx_assets or ["场景风沙、血尘、光位变化按本场视觉契约继承"],
                "compose_overlay_only": _overlay_policy(clip),
            },
            "sound_needs": {
                "dialogue_indices": _as_list(clip.get("dialogue_indices")),
                "narration_indices": _as_list(clip.get("narration_indices")),
                "sfx": _sfx_notes(clip),
            },
            "image_video_requirements": {
                "firstframe": clip.get("firstframe_png") or "",
                "endframe": endframe,
                "anchors": _as_list(continuity.get("anchors")),
                "backend_risk": _backend_risk(clip),
            },
            "department_notes": _department_notes(clip),
        })
    return {
        "kind": "n2d_production_breakdown",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "inputs": {
            "storyboard": f"脚本/{ep}/storyboard.json",
            "director_blocking_pack": f"脚本/{ep}/director_blocking_pack.json",
            "script_quality_contract": f"生产数据/script_quality_contract_{ep}.json",
        },
        "summary": {
            "clip_count": len(clips),
            "locations": sorted({str(c.get("location_id") or "") for c in clips if c.get("location_id")}),
            "characters": sorted({str(x) for c in clips for x in _as_list(c.get("character_ids")) if x}),
            "objects": sorted({str(x) for c in clips for x in _as_list(c.get("object_ids")) if x}),
        },
        "scene_breakdowns": scenes or [{
            "clip_id": "Clip_01",
            "label": "待补：storyboard.json 未提供 clips[]，请人工拆解",
            "scene": "待补",
            "location_id": "待补",
            "characters": "待补",
            "props_and_objects": "待补",
        }],
    }


def _continuity_breakdown(ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> Dict[str, Any]:
    rows = []
    for idx, clip in enumerate(clips, start=1):
        continuity = _clip_continuity(clip)
        entity = _clip_entity(clip)
        rows.append({
            "clip_id": _clip_id(clip, idx),
            "location_id": clip.get("location_id") or "",
            "required_presence": _as_list(entity.get("required_presence")),
            "start_state": continuity.get("start_state") or "待补：入点人物/道具/空间状态",
            "end_state": continuity.get("end_state") or "待补：出点人物/道具/空间状态",
            "eyeline": continuity.get("eyeline") or "按本场轴线/主体目标方向接力",
            "screen_direction": _screen_direction(clip),
            "wardrobe_makeup_continuity": _wardrobe_state(clip),
            "props_continuity": _props_continuity(clip),
            "knowledge_state": _knowledge_state(clip, confirmed=confirmed),
            "transition_guard": continuity.get("transition") or "按 storyboard 默认 cut 处理",
        })
    return {
        "kind": "n2d_continuity_breakdown",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "continuity_owner": "script_supervisor",
        "rows": rows or [{
            "clip_id": "Clip_01",
            "start_state": "待补",
            "end_state": "待补",
            "eyeline": "待补",
            "wardrobe_makeup_continuity": "待补",
            "props_continuity": "待补",
        }],
    }


def _sidecar_status(root: Path, ep: str, name: str, rel: str) -> Dict[str, Any]:
    path = root / rel
    data = load_json(path) if path.suffix == ".json" else None
    status = ""
    if isinstance(data, Mapping):
        status = str(data.get("status") or data.get("verdict") or "").strip()
    return {
        "name": name,
        "path": rel,
        "exists": path.exists(),
        "status": status or ("present" if path.exists() else "missing"),
    }


def _source_contract(root: Path) -> Dict[str, Any]:
    path = root / "设定库" / "source_comprehension.json"
    data = load_json(path)
    if not isinstance(data, Mapping):
        return {"path": "设定库/source_comprehension.json", "exists": False, "status": "missing", "trace_ids": []}
    contract = data.get("understanding_contract") if isinstance(data.get("understanding_contract"), Mapping) else {}
    trace_ids: List[str] = []
    blob = json.dumps(data, ensure_ascii=False)
    for match in re.finditer(r"\bSRC_[A-Za-z0-9_.:-]+\b", blob):
        trace = match.group(0)
        if trace not in trace_ids:
            trace_ids.append(trace)
    return {
        "path": "设定库/source_comprehension.json",
        "exists": True,
        "status": str(data.get("status") or "").strip() or "unknown",
        "trace_ids": trace_ids[:50],
        "contract_fields": sorted(contract.keys()),
    }


def _continuity_bible(root: Path, ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> Dict[str, Any]:
    continuity_path = _episode_dir(root, ep) / "continuity_breakdown.json"
    continuity_data = load_json(continuity_path)
    rows_by_clip: Dict[str, Mapping[str, Any]] = {}
    if isinstance(continuity_data, Mapping):
        for row in continuity_data.get("rows") or []:
            if isinstance(row, Mapping):
                cid = str(row.get("clip_id") or "").strip()
                if cid:
                    rows_by_clip[cid] = row

    clips_out: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, start=1):
        cid = _clip_id(clip, idx)
        continuity = _clip_continuity(clip)
        entity = _clip_entity(clip)
        row = rows_by_clip.get(cid, {})
        clips_out.append({
            "clip_id": cid,
            "scene": clip.get("scene") or "",
            "location_id": clip.get("location_id") or "",
            "entities": {
                "characters": _as_list(entity.get("characters") or clip.get("character_ids")),
                "objects": _as_list(entity.get("objects") or clip.get("object_ids")),
                "locations": _as_list(entity.get("locations") or clip.get("location_id")),
                "required_presence": _as_list(entity.get("required_presence")),
                "offscreen_presence": _as_list(entity.get("offscreen_presence")),
                "forbidden_presence": _as_list(entity.get("forbidden_presence")),
            },
            "state": {
                "start_state": continuity.get("start_state") or row.get("start_state") or "",
                "end_state": continuity.get("end_state") or row.get("end_state") or "",
                "entry_exit": continuity.get("entry_exit") or row.get("entry_exit") or "",
                "knowledge_state": entity.get("knowledge_state") or row.get("knowledge_state") or {},
            },
            "screen_direction": row.get("screen_direction") or _screen_direction(clip),
            "transition_guard": continuity.get("transition") or row.get("transition_guard") or "cut",
            "trace_ids": _as_list(clip.get("trace_ids") or clip.get("source_trace_ids") or clip.get("contract_trace_ids")),
        })

    sidecars = [
        _sidecar_status(root, ep, "state_transition_manifest", f"生产数据/state_transition_manifest_{ep}.json"),
        _sidecar_status(root, ep, "interaction_graph", f"生产数据/interaction_graph_{ep}.json"),
        _sidecar_status(root, ep, "contact_graph", f"生产数据/contact_graph_{ep}.json"),
        _sidecar_status(root, ep, "causal_event_graph", f"生产数据/causal_event_graph_{ep}.json"),
        _sidecar_status(root, ep, "story_integrity_ledger", "设定库/story_integrity_ledger.json"),
        _sidecar_status(root, ep, "thread_scheduler", "设定库/thread_scheduler.json"),
        _sidecar_status(root, ep, "contract_trace", f"生产数据/contract_trace_{ep}.json"),
    ]
    return {
        "kind": "n2d_continuity_bible",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "owner": "script_supervisor",
        "inputs": {
            "source_comprehension": "设定库/source_comprehension.json",
            "storyboard": f"脚本/{ep}/storyboard.json",
            "continuity_breakdown": f"脚本/{ep}/continuity_breakdown.json",
        },
        "source_contract": _source_contract(root),
        "sidecars": sidecars,
        "clips": clips_out,
        "open_continuity_questions": [
            row for row in sidecars
            if not row.get("exists") and row["name"] in {"state_transition_manifest", "interaction_graph", "causal_event_graph"}
        ],
    }


def _schedule_priority(clip: Mapping[str, Any]) -> str:
    template = _clip_template(clip)
    text = json.dumps(clip, ensure_ascii=False)
    high_tokens = ("fight", "action", "追逐", "打斗", "拥抱", "拉扯", "亲密", "system", "系统", "CU", "MCU")
    if any(token in template or token in text for token in high_tokens):
        return "high"
    continuity = _clip_continuity(clip)
    if _as_list(continuity.get("anchors")) or continuity.get("need_endframe"):
        return "medium"
    return "normal"


def _schedule_bucket(priority: str) -> str:
    if priority == "high":
        return "pilot_high_risk_first"
    if priority == "medium":
        return "continuity_sensitive"
    return "standard_batch"


def _ai_shooting_schedule(root: Path, ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> Dict[str, Any]:
    tasks: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, start=1):
        cid = _clip_id(clip, idx)
        continuity = _clip_continuity(clip)
        priority = _schedule_priority(clip)
        needs_review = priority in {"high", "medium"} or bool(_screen_texts(clip))
        tasks.append({
            "clip_id": cid,
            "production_order": idx,
            "schedule_bucket": _schedule_bucket(priority),
            "priority": priority,
            "estimated_duration_sec": clip.get("duration") or clip.get("seconds") or "",
            "scene": clip.get("scene") or "",
            "dependencies": {
                "storyboard": f"脚本/{ep}/storyboard.json#{cid}",
                "production_breakdown": f"脚本/{ep}/production_breakdown.json#{cid}",
                "continuity_bible": f"脚本/{ep}/continuity_bible.json#{cid}",
                "firstframe": clip.get("firstframe_png") or "",
                "endframe": clip.get("endframe_png") or continuity.get("endframe_png") or "",
                "anchors": _as_list(continuity.get("anchors")),
            },
            "resource_plan": {
                "image_backend_slot": "按 n2d-image reference planner / 生图后端 smoke 证据分配",
                "video_backend_slot": "按 n2d-model-router route primary/fallback 分配",
                "human_review_point": "出图后 immediate QC；出视频后 video_qc；高风险镜先审再批量",
                "budget_guard": "进入 batch 前写 max_concurrency / budget / max_retries",
            },
            "risk": {
                "tier": priority,
                "template": _clip_template(clip),
                "backend_risk": _backend_risk(clip),
                "review_required": needs_review,
            },
            "fallback_route": {
                "image": "reference_group/image2image/multi_reference；失败则降级拆镜或补参考",
                "video": "native_multiframe → split_relay → shorter_clip_degrade",
                "post": "screen_text/字幕/花字统一 compose overlay",
            },
            "batch_hint": {
                "idempotency_scope": f"{ep}:{cid}:image_video",
                "rerun_scope": f"只重跑 {cid} 及其受影响接缝/后期证据",
            },
        })
    return {
        "kind": "n2d_ai_shooting_schedule",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "owner": "assistant_director",
        "inputs": {
            "storyboard": f"脚本/{ep}/storyboard.json",
            "production_breakdown": f"脚本/{ep}/production_breakdown.json",
            "continuity_bible": f"脚本/{ep}/continuity_bible.json",
            "batch_queue": "生产数据/batch_queue.json",
        },
        "policy": {
            "high_risk_first": True,
            "do_not_batch_past_unreviewed_high_risk_clip": True,
            "call_sheet_is_ordering_not_authorization": True,
        },
        "tasks": tasks,
        "summary": {
            "clip_count": len(tasks),
            "high_risk": sum(1 for t in tasks if t["priority"] == "high"),
            "medium_risk": sum(1 for t in tasks if t["priority"] == "medium"),
        },
    }


def _batch_seed_from_schedule(root: Path, ep: str, schedule: Mapping[str, Any]) -> Dict[str, Any]:
    tasks: List[Dict[str, Any]] = []
    source_tasks = [t for t in (schedule.get("tasks") or []) if isinstance(t, Mapping)]
    order_rank = {"high": 0, "medium": 1, "normal": 2}
    ordered = sorted(
        source_tasks,
        key=lambda t: (order_rank.get(str(t.get("priority") or "normal"), 3), int(t.get("production_order") or 9999)),
    )
    priority = 1
    for task in ordered:
        cid = str(task.get("clip_id") or "").strip()
        if not cid:
            continue
        for stage_key in ("image", "video"):
            tasks.append({
                "episode": ep,
                "stage_key": stage_key,
                "clip_id": cid,
                "priority": priority,
                "reason": "shooting_schedule",
                "schedule_bucket": task.get("schedule_bucket") or "",
                "risk_tier": (task.get("risk") or {}).get("tier") if isinstance(task.get("risk"), Mapping) else task.get("priority"),
                "affected_shots": [cid],
                "affected_artifacts": [],
                "rerun_scope": f"AI shooting schedule {ep} {cid} {stage_key}：按排期单镜执行，保留受影响接缝返工边界。",
                "resource_plan": task.get("resource_plan") if isinstance(task.get("resource_plan"), Mapping) else {},
                "dependencies": task.get("dependencies") if isinstance(task.get("dependencies"), Mapping) else {},
                "source_schedule_order": task.get("production_order") or priority,
            })
            priority += 1
    return {
        "kind": "n2d_ai_shooting_schedule_batch_seed",
        "version": VERSION,
        "episode": ep,
        "status": "ready" if tasks else "block",
        "generated_at": now_iso(),
        "source_schedule": f"脚本/{ep}/ai_shooting_schedule.json",
        "batch_queue_command": f"python3 skills/n2d-batch/scripts/queue.py plan {root} --from-shooting-schedule 生产数据/{BATCH_SEED_JSON.format(episode=ep)}",
        "policy": {
            "one_task_per_clip_stage": True,
            "high_risk_first": True,
            "queue_merge_default": True,
        },
        "summary": {
            "seed_tasks": len(tasks),
            "clips": len({t["clip_id"] for t in tasks}),
            "stages": sorted({t["stage_key"] for t in tasks}),
        },
        "batch_tasks": tasks,
    }


def _write_batch_seed(root: Path, ep: str, schedule: Mapping[str, Any], *, force: bool = False) -> Tuple[str, str]:
    seed = _batch_seed_from_schedule(root, ep, schedule)
    json_path = root / "生产数据" / BATCH_SEED_JSON.format(episode=ep)
    md_path = root / "生产数据" / BATCH_SEED_MD.format(episode=ep)
    if force or not json_path.exists():
        write_json_atomic(json_path, seed)
    if force or not md_path.exists():
        lines = [
            f"# AI Shooting Schedule Batch Seed — {ep}",
            "",
            f"- status: {seed.get('status')}",
            f"- seed tasks: {(seed.get('summary') or {}).get('seed_tasks', 0)}",
            f"- source: `脚本/{ep}/ai_shooting_schedule.json`",
            "",
            "## Import",
            "",
            f"```bash\npython3 skills/n2d-batch/scripts/queue.py plan {root} --from-shooting-schedule 生产数据/{BATCH_SEED_JSON.format(episode=ep)}\n```",
            "",
            "| priority | stage | clip | bucket | scope |",
            "|---|---|---|---|---|",
        ]
        for task in seed.get("batch_tasks") or []:
            lines.append(
                f"| {task.get('priority')} | {task.get('stage_key')} | {task.get('clip_id')} | "
                f"{task.get('schedule_bucket') or '-'} | {str(task.get('rerun_scope') or '').replace('|', '/')} |"
            )
        write_atomic(md_path, "\n".join(lines).rstrip() + "\n")
    return str(json_path), str(md_path)


def _ai_call_sheet(root: Path, ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> str:
    rows = []
    for idx, clip in enumerate(clips, start=1):
        continuity = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        rows.append(
            "| {order} | {clip_id} | {scene} | {duration} | {risk} | {hold} |".format(
                order=idx,
                clip_id=_clip_id(clip, idx),
                scene=str(clip.get("scene") or "").replace("|", "/"),
                duration=clip.get("duration") or "",
                risk=str(clip.get("template") or clip.get("rhythm") or "standard_scene").replace("|", "/"),
                hold="尾帧" if continuity.get("need_endframe") else "无尾帧要求",
            )
        )
    body = "\n".join(rows) if rows else "| 1 | Clip_01 | 待补 | 待补 | 待补 | 待补 |"
    return f"""---
kind: n2d_ai_call_sheet
version: 1
episode: {ep}
status: {'confirmed' if confirmed else 'draft'}
---
# {ep} — AI 拍摄通告单

> 这是 Stage 2 分镜之后、出图 prompt 之前的制片交接单。confirmed 表示已按 storyboard / continuity / 合规包完成出图 prompt 前交接。

## 生产日目标
- 本轮目标：先生成第 2 层出图 prompt；共享定妆已存在时优先打样高风险动作镜与系统面板镜，再进入全集出图。

## 放行前依赖
- P-1 开发包 confirmed；P-2 导演排戏包 confirmed；本 P-3 包 confirmed 后才进入出图 prompt。
- `ai_shooting_schedule.json` 已列出高风险优先级、后端槽位、预算/并发护栏和 batch rerun scope。
- `continuity_bible.json` 已把 source/storyboard/entity/state/sidecar 聚合成场记真值源。
- 角色/场景/道具/VFX 参考从共享 identity_registry / asset_registry 继承；新增缺口由出图 prompt 标为 reference plan。
- 系统文字、状态数值、字幕和花字走 compose overlay；生图/视频只留空面板与安全区。
- 合规包按 internal_only demo 使用，平台审核/备案/出海本地化留到转投放前补齐。

## 拍摄顺序
| 顺序 | Clip | 场景 | 秒数 | 风险/模板 | 保持项 |
|---|---|---|---|---|---|
{body}

## 人工停审点
- 动作/打斗/追逐/高运动镜必须优先审动作线、命中点、收势和可读性。
- 系统面板、状态数值、标题卡和任何文字镜必须确认留白与 overlay 安全区，不允许 AI 烤字。
- 集尾钩、关系转折和高情绪近景必须确认情绪转折与下一集问题清楚。

## 后期交接
- BGM hit 对齐本集爽点、反转、系统信息和集尾钩；J/L cut 用环境声、动作声和 UI 音效衔接。
- 真实配音在先出视频后补，compose 前必须替换 rough timing 并复核字幕/镜头时长。
- 全集保持冷灰写实 3D 国风漫剧，百妖谱金色光只作为剧情信息焦点，不改角色定妆。
"""


def _write_overview(root: Path, ep: str, report: Mapping[str, Any] | None = None) -> str:
    out = root / "生产数据" / f"production_handoff_pack_{ep}.md"
    lines = [
        f"# P-3 制片拆解包 — {ep}",
        "",
        "本包位于 Stage 2 分镜之后、出图 prompt 之前，用来把导演分镜翻译成可执行的制片交接。",
        "",
        "## Required Files",
        "",
    ]
    lines.extend(f"- `脚本/{ep}/{name}`" for name in REQUIRED_FILES)
    lines.append(f"- `生产数据/{BATCH_SEED_JSON.format(episode=ep)}`")
    if report:
        lines.extend([
            "",
            "## Check",
            "",
            f"- 状态：{report.get('status')}",
            f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
            "",
            "| 文件 | 状态 | 问题 |",
            "|---|---|---|",
        ])
        for row in report.get("files") or []:
            issues = "；".join(row.get("issues") or []) or "-"
            lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    write_atomic(out, "\n".join(lines).rstrip() + "\n")
    return str(out)


def scaffold(root: Path, ep: str, *, force: bool = False, confirmed: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    ep_dir = _episode_dir(root, ep)
    clips = _clips(root, ep)
    created: List[str] = []
    schedule_payload = _ai_shooting_schedule(root, ep, clips, confirmed=confirmed)
    payloads: Tuple[Tuple[str, Mapping[str, Any]], ...] = (
        ("production_breakdown.json", _production_breakdown(root, ep, clips, confirmed=confirmed)),
        ("continuity_breakdown.json", _continuity_breakdown(ep, clips, confirmed=confirmed)),
        ("continuity_bible.json", _continuity_bible(root, ep, clips, confirmed=confirmed)),
        ("ai_shooting_schedule.json", schedule_payload),
    )
    for name, payload in payloads:
        if write_json_if_absent(ep_dir / name, payload, force=force):
            created.append(f"脚本/{ep}/{name}")
    if write_text_if_absent(ep_dir / "ai_call_sheet.md", _ai_call_sheet(root, ep, clips, confirmed=confirmed), force=force):
        created.append(f"脚本/{ep}/ai_call_sheet.md")
    seed_json, seed_md = _write_batch_seed(root, ep, schedule_payload, force=force)
    manifest = {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "root": str(root),
        "inputs": {rel.rsplit("/", 1)[-1]: rel for rel in handoff_input_rels(ep)},
        "inputs_fingerprint": artifact_fingerprint(root, handoff_input_rels(ep)),
        "required_files": [f"脚本/{ep}/{name}" for name in REQUIRED_FILES],
        "gate": "run.py image_prompt prework requires all P-3 production handoff files to be confirmed.",
    }
    write_json_atomic(ep_dir / "production_handoff_pack.json", manifest)
    overview = _write_overview(root, ep)
    return {
        "kind": KIND,
        "root": str(root),
        "episode": ep,
        "episode_dir": str(ep_dir),
        "created": created,
        "manifest": f"脚本/{ep}/production_handoff_pack.json",
        "overview_path": overview,
        "batch_seed": [seed_json, seed_md],
    }


def _batch_seed_status(root: Path, ep: str) -> Dict[str, Any]:
    path = root / "生产数据" / BATCH_SEED_JSON.format(episode=ep)
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        issues.append("batch seed JSON 缺失或无效")
    else:
        if data.get("kind") != "n2d_ai_shooting_schedule_batch_seed":
            issues.append("kind 不是 n2d_ai_shooting_schedule_batch_seed")
        if str(data.get("status") or "").lower() != "ready":
            issues.append("status 不是 ready")
        if not data.get("batch_tasks"):
            issues.append("batch_tasks 为空")
    md = root / "生产数据" / BATCH_SEED_MD.format(episode=ep)
    if not md.is_file():
        issues.append("batch seed markdown 缺失")
    return {
        "rel": f"生产数据/{BATCH_SEED_JSON.format(episode=ep)}",
        "status": "pass" if not issues else "block",
        "issues": issues,
    }


def _handoff_manifest_status(root: Path, ep: str) -> Dict[str, Any]:
    rel = f"脚本/{ep}/production_handoff_pack.json"
    path = root / rel
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, Mapping):
        issues.append("production_handoff_pack.json 缺失或无效")
    else:
        if data.get("kind") != KIND:
            issues.append("kind 不是 n2d_production_handoff_pack")
        if str(data.get("status") or "").strip().lower() != "confirmed":
            issues.append("status 不是 confirmed")
        fresh = fingerprint_is_fresh(data.get("inputs_fingerprint"), root)
        if fresh is False:
            issues.append("inputs_fingerprint 已过期，上游输入变更后需重新确认 P-3 handoff")
        elif fresh is None:
            issues.append("缺 inputs_fingerprint，不能证明 handoff 对应当前输入")
    return {"rel": rel, "status": "pass" if not issues else "block", "issues": issues}


def _json_status(path: Path) -> Tuple[str, List[str]]:
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        return "block", ["JSON 无法解析或不是 object"]
    if str(data.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed")
    blob = json.dumps(data, ensure_ascii=False)
    if PLACEHOLDER_RE.search(blob):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def _md_status(path: Path) -> Tuple[str, List[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    issues: List[str] = []
    if not text.strip():
        return "block", ["文件为空"]
    if not CONFIRMED_RE.search(text):
        issues.append("缺 status: confirmed / 状态: confirmed")
    if PLACEHOLDER_RE.search(text):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def check(root: Path, ep: str, *, write_missing: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    if write_missing:
        scaffold(root, ep)
    ep_dir = _episode_dir(root, ep)
    rows: List[Dict[str, Any]] = []
    for name in REQUIRED_FILES:
        path = ep_dir / name
        rel = f"脚本/{ep}/{name}"
        if not path.exists():
            rows.append({"rel": rel, "status": "missing", "issues": ["文件缺失"]})
            continue
        status, issues = _json_status(path) if path.suffix == ".json" else _md_status(path)
        rows.append({"rel": rel, "status": status, "issues": issues})
    rows.append(_handoff_manifest_status(root, ep))
    rows.append(_batch_seed_status(root, ep))
    blockers = [row for row in rows if row["status"] != "pass"]
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "episode": ep,
        "status": "pass" if not blockers else "block",
        "summary": {
            "required": len(rows),
            "pass": len(rows) - len(blockers),
            "block": len(blockers),
        },
        "files": rows,
        "scaffold_command": f"python3 skills/n2d-script/scripts/production_breakdown.py {root} {ep} scaffold --write",
        "next_when_blocked": (
            "补齐 P-3 制片拆解三件套，删除待补/TODO 占位，并把每个文件 status 改为 confirmed；"
            "确认 ai_shooting_schedule 已导出 batch seed；之后重跑 check，再进入出图 prompt。"
        ),
    }
    out = root / "生产数据" / f"production_breakdown_check_{ep}.json"
    write_json_atomic(out, payload)
    payload["check_path"] = str(out)
    payload["overview_path"] = _write_overview(root, ep, payload)
    return payload


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# P-3 制片拆解包检查 — {report.get('episode')}",
        "",
        f"- 状态：{report.get('status')}",
        f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
        "",
        "| 文件 | 状态 | 问题 |",
        "|---|---|---|",
    ]
    for row in report.get("files") or []:
        issues = "；".join(row.get("issues") or []) or "-"
        lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    lines += ["", str(report.get("next_when_blocked") or "")]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    sub = ap.add_subparsers(dest="command", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--write", action="store_true", help="兼容显式写入语义；scaffold 默认即写入")
    p_scaffold.add_argument("--force", action="store_true", help="覆盖已有模板（谨慎）")
    p_scaffold.add_argument("--confirm", action="store_true", help="用 storyboard 可推导字段生成 confirmed 交接包；若仍含占位，check 仍会阻断")
    p_check = sub.add_parser("check")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--markdown", action="store_true")
    p_check.add_argument("--write-missing", action="store_true", help="缺文件时先补 scaffold，再返回 block")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    ep = episode_label(ns.episode)
    if ns.command == "scaffold":
        payload = scaffold(root, ep, force=ns.force, confirmed=ns.confirm)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    report = check(root, ep, write_missing=ns.write_missing)
    if ns.markdown:
        md = render_markdown(report)
        path = root / "生产数据" / f"production_breakdown_check_{ep}.md"
        write_atomic(path, md)
        print(md)
    elif ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"P-3 制片拆解包检查：{report['status']} ({report['summary']['pass']}/{report['summary']['required']})")
        if report["status"] != "pass":
            print(report["next_when_blocked"])
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
