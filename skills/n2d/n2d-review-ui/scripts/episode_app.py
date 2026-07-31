#!/usr/bin/env python3
"""Per-episode production workspace for n2d desktop/app views.

This script is a read-only aggregation layer.  It does not replace board.py or
review_ui.py; it turns their outputs plus dashboard/gate evidence into a stable
per-episode JSON contract that a desktop app or static HTML can consume.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import quote

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
_COMMON = str(_SCRIPT_DIR.parent.parent / "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

import board  # noqa: E402
import review_ui  # noqa: E402
from n2d_contract import PRODUCTION_DIR  # noqa: E402
from n2d_route import normalize_episode  # noqa: E402


KIND_INDEX = "n2d_episode_index"
KIND_EPISODE = "n2d_episode_workspace"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def load_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def rel_to(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def url_to(path: Path, html_dir: Path) -> str:
    return quote(os.path.relpath(path, html_dir).replace(os.sep, "/"), safe="/._-()[]@+,~:%")


def output_paths(root: Path, ep: str) -> Dict[str, Path]:
    ep = normalize_episode(ep)
    prod = production_dir(root)
    return {
        "dir": prod,
        "episode_dir": prod / "episodes",
        "index": prod / "episode_index.json",
        "json": prod / "episodes" / f"{ep}.json",
        "html": prod / f"episode_app_{ep}.html",
    }


def dashboard_path(root: Path) -> Path:
    return production_dir(root) / "dashboard.json"


def board_path(root: Path) -> Path:
    return production_dir(root) / "board.json"


def episode_sort_key(ep: str) -> tuple:
    text = normalize_episode(ep)
    digits = "".join(ch for ch in text if ch.isdigit())
    return (int(digits) if digits else 10**9, text)


def dashboard_episode_map(root: Path) -> Dict[str, Dict[str, Any]]:
    data = load_json(dashboard_path(root))
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(data, dict):
        for item in data.get("episodes") or []:
            if isinstance(item, dict) and item.get("episode"):
                out[normalize_episode(str(item["episode"]))] = item
    return out


def board_manifest(root: Path) -> Dict[str, Any]:
    existing = load_json(board_path(root))
    if isinstance(existing, dict) and existing.get("kind") == board.KIND:
        return existing
    return board.build_manifest(root)


def board_episode_map(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for item in manifest.get("episodes") or []:
        if isinstance(item, dict) and item.get("episode"):
            out[normalize_episode(str(item["episode"]))] = item
    return out


def cost_text(costs: Dict[str, Any]) -> str:
    if not isinstance(costs, dict) or not costs:
        return "—"
    parts = []
    for unit, value in sorted(costs.items()):
        try:
            num = float(value)
            shown = f"{num:.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            shown = str(value)
        parts.append(f"{shown} {unit}")
    return " / ".join(parts)


def rate_text(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def clip_status(clip: Dict[str, Any]) -> str:
    flags = clip.get("qa_flags") or []
    if any(str(f.get("severity")) == "block" for f in flags if isinstance(f, dict)):
        return "block"
    missing = any(
        isinstance(clip.get(key), dict) and not clip[key].get("exists")
        for key in ("first_frame", "end_frame", "video")
    )
    if missing or any(str(f.get("severity")) == "warn" for f in flags if isinstance(f, dict)):
        return "warn"
    return "pass"


def slim_clip(clip: Dict[str, Any]) -> Dict[str, Any]:
    first = clip.get("first_frame") if isinstance(clip.get("first_frame"), dict) else {}
    video = clip.get("video") if isinstance(clip.get("video"), dict) else {}
    flags = [f for f in clip.get("qa_flags") or [] if isinstance(f, dict)]
    counts = Counter(str(f.get("severity") or "info") for f in flags)
    return {
        "index": clip.get("index"),
        "id": clip.get("id"),
        "label": clip.get("label"),
        "scene": clip.get("scene"),
        "duration": clip.get("duration"),
        "status": clip_status(clip),
        "thumb": first.get("url") if first.get("exists") else "",
        "video_url": video.get("url") if video.get("exists") else "",
        "has_video": bool(video.get("exists")),
        "qa_counts": dict(counts),
        "qa_total": len(flags),
    }


def file_entry(root: Path, html_dir: Path, path: Path, label: str) -> Dict[str, Any]:
    return {
        "label": label,
        "path": rel_to(path, root),
        "exists": path.is_file(),
        "url": url_to(path, html_dir),
    }


def gate_stage_from_path(path: Path, ep: str) -> str:
    name = path.name
    prefix = "gate_findings_"
    suffix = f"_{normalize_episode(ep)}.json"
    if name.startswith(prefix) and name.endswith(suffix):
        return name[len(prefix):-len(suffix)]
    return ""


def normalize_issue(raw: Dict[str, Any], *, source: str, gate_stage: str = "") -> Dict[str, Any]:
    sev = str(raw.get("sev") or raw.get("severity") or "info").lower()
    if sev not in {"block", "warn", "info"}:
        sev = "info"
    return {
        "severity": sev,
        "return_to_stage": str(raw.get("return_to_stage") or raw.get("rerun_from") or gate_stage or "review"),
        "dimension": str(raw.get("dim") or raw.get("dimension") or "QA"),
        "loc": str(raw.get("loc") or ""),
        "message": str(raw.get("msg") or raw.get("message") or ""),
        "affected_shots": [str(x) for x in (raw.get("affected_shots") or [])],
        "affected_artifacts": [str(x) for x in (raw.get("affected_artifacts") or [])],
        "source": source,
        "gate_stage": gate_stage,
    }


def collect_gate_payloads(root: Path, ep: str) -> List[Dict[str, Any]]:
    prod = production_dir(root)
    payloads = []
    for path in sorted(prod.glob(f"gate_findings_*_{normalize_episode(ep)}.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        stage = str(data.get("gate_stage") or gate_stage_from_path(path, ep))
        data = dict(data)
        data["_path"] = rel_to(path, root)
        data["_stage"] = stage
        payloads.append(data)
    return payloads


def collect_issues(review_manifest: Dict[str, Any], gate_payloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    try:
        payload = review_ui.findings_payload(review_manifest)
    except Exception:
        payload = {}
    for item in payload.get("findings") or []:
        if isinstance(item, dict):
            issues.append(normalize_issue(item, source="review_ui"))
    for payload in gate_payloads:
        stage = str(payload.get("_stage") or payload.get("gate_stage") or "")
        source = f"gate:{stage}" if stage else "gate"
        for item in payload.get("findings") or []:
            if isinstance(item, dict):
                issues.append(normalize_issue(item, source=source, gate_stage=stage))

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for issue in issues:
        key = (
            issue["severity"], issue["return_to_stage"], issue["dimension"],
            issue["loc"], issue["message"], tuple(issue["affected_shots"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)

    severity_rank = {"block": 0, "warn": 1, "info": 2}
    deduped.sort(key=lambda i: (severity_rank.get(i["severity"], 9), i["return_to_stage"], i["dimension"], i["loc"]))
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for issue in deduped:
        grouped[issue["return_to_stage"]].append(issue)
    groups = []
    for stage, items in sorted(grouped.items(), key=lambda kv: (severity_rank.get(kv[1][0]["severity"], 9), kv[0])):
        counts = Counter(item["severity"] for item in items)
        groups.append({"return_to_stage": stage, "counts": dict(counts), "items": items})
    return {"total": len(deduped), "severity": dict(Counter(i["severity"] for i in deduped)), "groups": groups}


def collect_return_tasks(score: Dict[str, Any], gate_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    if isinstance(score, dict):
        for item in score.get("auto_return_tasks") or []:
            if isinstance(item, dict):
                copied = dict(item)
                copied["source"] = "score"
                tasks.append(copied)
    for payload in gate_payloads:
        stage = str(payload.get("_stage") or payload.get("gate_stage") or "")
        for item in payload.get("auto_return_tasks") or []:
            if isinstance(item, dict):
                copied = dict(item)
                copied["source"] = f"gate:{stage}" if stage else "gate"
                tasks.append(copied)
    return tasks


def build_episode_workspace(
    root: Path,
    ep: str,
    *,
    board_data: Optional[Dict[str, Any]] = None,
    dashboard_eps: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    ep = normalize_episode(ep)
    prod = production_dir(root)
    board_data = board_data or board_manifest(root)
    board_ep = board_episode_map(board_data).get(ep, {})
    dashboard_ep = (dashboard_eps or dashboard_episode_map(root)).get(ep, {})
    review_manifest = review_ui.build_manifest(root, ep)
    score = review_manifest.get("score") if isinstance(review_manifest.get("score"), dict) else {}
    gate_payloads = collect_gate_payloads(root, ep)
    issues = collect_issues(review_manifest, gate_payloads)
    tasks = collect_return_tasks(score, gate_payloads)
    paths = output_paths(root, ep)

    evidence = [
        file_entry(root, prod, paths["json"], "本集聚合 JSON"),
        file_entry(root, prod, paths["html"], "本集工作台 HTML"),
        file_entry(root, prod, prod / f"review_ui_{ep}.json", "人审画布 JSON"),
        file_entry(root, prod, prod / f"review_ui_{ep}.html", "人审画布 HTML"),
        file_entry(root, prod, prod / f"score_{ep}.json", "机器评分"),
        file_entry(root, prod, prod / f"consistency_ledger_{ep}.json", "一致性总账"),
        file_entry(root, prod, dashboard_path(root), "生产数据 dashboard"),
        file_entry(root, prod, board_path(root), "整部生产看板 JSON"),
    ]
    for payload in gate_payloads:
        p = root / str(payload.get("_path") or "")
        evidence.append(file_entry(root, prod, p, f"gate findings {payload.get('_stage') or ''}".strip()))

    clips = [slim_clip(c) for c in review_manifest.get("clips") or [] if isinstance(c, dict)]
    status = "pass"
    if issues["severity"].get("block") or int(dashboard_ep.get("qa_blockers") or 0) > 0:
        status = "block"
    elif issues["severity"].get("warn") or int(dashboard_ep.get("qa_warnings") or 0) > 0:
        status = "warn"

    return {
        "kind": KIND_EPISODE,
        "version": VERSION,
        "root": str(root),
        "episode": ep,
        "generated_at": now_iso(),
        "status": status,
        "links": {
            "board": {"url": "board.html", "exists": (prod / "board.html").is_file()},
            "review_ui": {"url": f"review_ui_{ep}.html", "exists": (prod / f"review_ui_{ep}.html").is_file()},
            "self": {"url": f"episode_app_{ep}.html", "exists": paths["html"].is_file()},
        },
        "next_action": board_ep.get("frontier") or {
            "label": dashboard_ep.get("progress_next_stage"),
            "skill": dashboard_ep.get("progress_next_skill"),
        },
        "progress": {
            "accepted": bool(board_ep.get("accepted")),
            "done_stages": board_ep.get("done_stages", 0),
            "total_stages": board_ep.get("total_stages", 0),
            "stages": board_ep.get("stages", {}),
        },
        "metrics": {
            "cost_totals": dashboard_ep.get("cost_totals", {}),
            "cost_text": cost_text(dashboard_ep.get("cost_totals", {})),
            "duration_hms": dashboard_ep.get("duration_hms", "—"),
            "runtime_hms": dashboard_ep.get("runtime_hms", "—"),
            "event_count": dashboard_ep.get("event_count", 0),
            "generation_attempts": dashboard_ep.get("generation_attempts", 0),
            "generation_pass_rate": dashboard_ep.get("generation_pass_rate"),
            "generation_pass_rate_text": rate_text(dashboard_ep.get("generation_pass_rate")),
            "final_pass_rate": dashboard_ep.get("final_pass_rate"),
            "final_pass_rate_text": rate_text(dashboard_ep.get("final_pass_rate")),
            "one_pass_rate": dashboard_ep.get("one_pass_rate"),
            "one_pass_rate_text": rate_text(dashboard_ep.get("one_pass_rate")),
            "redraw_count": dashboard_ep.get("redraw_count", 0),
            "redraw_rate": dashboard_ep.get("redraw_rate"),
            "redraw_rate_text": rate_text(dashboard_ep.get("redraw_rate")),
            "qa_blockers": dashboard_ep.get("qa_blockers", 0),
            "qa_warnings": dashboard_ep.get("qa_warnings", 0),
            "score": score.get("total_score"),
            "score_status": score.get("status") or "missing",
        },
        "stage_metrics": dashboard_ep.get("stages", {}),
        "clips": clips,
        "clip_summary": {
            "total": len(clips),
            "status": dict(Counter(c.get("status") for c in clips)),
            "with_video": sum(1 for c in clips if c.get("has_video")),
        },
        "issues": issues,
        "return_tasks": tasks,
        "evidence": evidence,
    }


def build_episode_index(root: Path, *, board_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    board_data = board_data or board_manifest(root)
    dash_eps = dashboard_episode_map(root)
    prod = production_dir(root)
    episodes = []
    for item in sorted(board_episode_map(board_data).values(), key=lambda e: episode_sort_key(str(e.get("episode") or ""))):
        ep = normalize_episode(str(item.get("episode") or ""))
        dash = dash_eps.get(ep, {})
        paths = output_paths(root, ep)
        score = item.get("score") if isinstance(item.get("score"), dict) else {}
        episodes.append({
            "episode": ep,
            "num": item.get("num"),
            "accepted": bool(item.get("accepted")),
            "done_stages": item.get("done_stages", 0),
            "total_stages": item.get("total_stages", 0),
            "frontier": item.get("frontier"),
            "has_storyboard": bool(item.get("has_storyboard")),
            "clips": len(item.get("clips") or []),
            "score": score.get("total_score"),
            "score_status": score.get("status") or "missing",
            "cost_text": cost_text(dash.get("cost_totals", {})),
            "duration_hms": dash.get("duration_hms", "—"),
            "runtime_hms": dash.get("runtime_hms", "—"),
            "final_pass_rate": dash.get("final_pass_rate"),
            "redraw_rate": dash.get("redraw_rate"),
            "qa_blockers": dash.get("qa_blockers", 0),
            "qa_warnings": dash.get("qa_warnings", 0),
            "episode_app": {
                "url": f"episode_app_{ep}.html",
                "json": f"episodes/{ep}.json",
                "exists": paths["html"].is_file(),
            },
            "review_ui": item.get("review_ui") or {"url": f"review_ui_{ep}.html", "exists": (prod / f"review_ui_{ep}.html").is_file()},
        })
    return {
        "kind": KIND_INDEX,
        "version": VERSION,
        "root": str(root),
        "title": board_data.get("title") or root.name,
        "generated_at": now_iso(),
        "summary": board_data.get("summary", {}),
        "episodes": episodes,
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#f6f7fb;--panel:#fff;--ink:#172033;--muted:#667085;--line:#d8dee9;--blue:#2563eb;--red:#c7372f;--amber:#b7791f;--green:#2f855a}}
*{{box-sizing:border-box}} body{{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink);letter-spacing:0}}
button{{font:inherit}} .top{{height:60px;display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:5}}
.title{{min-width:240px}} .title b{{display:block;font-size:15px}} .title span{{display:block;color:var(--muted);font-size:12px;margin-top:2px}}
.tabs{{display:flex;gap:6px;margin-left:auto;flex-wrap:wrap}} .tab{{height:34px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:0 12px;cursor:pointer}}
.tab.active{{border-color:var(--blue);color:var(--blue);background:#eff6ff}} .link{{height:34px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:0 12px;cursor:pointer;color:var(--ink)}}
.wrap{{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;padding:16px;max-width:1480px;margin:0 auto}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}} .panel h2{{font-size:14px;margin:0 0 10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}} .metric{{border:1px solid var(--line);border-radius:8px;padding:10px;background:#fff}}
.metric span{{display:block;color:var(--muted);font-size:12px}} .metric b{{display:block;font-size:20px;margin-top:4px;overflow-wrap:anywhere}}
.badge{{display:inline-flex;align-items:center;min-height:22px;padding:2px 7px;border-radius:999px;font-size:12px;border:1px solid var(--line);color:var(--muted);background:#f8fafc;white-space:nowrap}}
.badge.block{{color:var(--red);border-color:#f1b3ae;background:#fff1f0}} .badge.warn{{color:var(--amber);border-color:#f4d39a;background:#fff8e8}} .badge.pass{{color:var(--green);border-color:#9bd8b9;background:#ecfdf3}}
.stage-row,.issue,.evidence-row{{display:grid;grid-template-columns:150px minmax(0,1fr) auto;gap:10px;align-items:start;border-top:1px solid var(--line);padding:9px 0;font-size:13px}}
.stage-row:first-child,.issue:first-child,.evidence-row:first-child{{border-top:0}} .muted{{color:var(--muted)}} code{{background:#eef2f7;border:1px solid var(--line);border-radius:5px;padding:1px 4px;overflow-wrap:anywhere}}
.clip-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}} .clip{{border:1px solid var(--line);border-radius:8px;background:#fff;overflow:hidden}}
.clip.block{{border-color:#f1b3ae}} .clip.warn{{border-color:#f4d39a}} .thumb{{height:112px;background:#eef2f7;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:12px}}
.thumb img{{width:100%;height:100%;object-fit:cover}} .clip-body{{padding:9px;font-size:12px}} .clip-title{{font-weight:700;font-size:13px;margin-bottom:4px}}
.hidden{{display:none}} .side{{display:flex;flex-direction:column;gap:16px}} .openbtn{{display:inline-flex;align-items:center;justify-content:center;height:30px;border:1px solid var(--line);border-radius:7px;padding:0 9px;color:var(--ink);text-decoration:none;background:#fff;font-size:12px}}
@media(max-width:920px){{.wrap{{grid-template-columns:1fr}}.tabs{{margin-left:0}}.top{{height:auto;align-items:flex-start;flex-wrap:wrap}}}}
</style></head><body>
<div class="top"><div class="title"><b id="title"></b><span id="sub"></span></div><button class="link" id="boardBtn">作品看板</button><button class="link" id="reviewBtn">人审画布</button><div class="tabs" id="tabs"></div></div>
<div class="wrap"><main id="main"></main><aside class="side" id="side"></aside></div>
<script id="manifest" type="application/json">{manifest_json}</script>
<script>
const data=JSON.parse(document.getElementById('manifest').textContent); let active='overview';
const tabDefs=[['overview','总览'],['stages','阶段'],['clips','镜头'],['issues','问题'],['evidence','证据']];
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));}}
function badge(v){{const c=v==='block'?'block':v==='warn'?'warn':v==='pass'?'pass':'';return `<span class="badge ${{c}}">${{esc(v||'—')}}</span>`}}
function openMaybe(link, fallback){{if(link&&link.exists&&link.url) window.open(link.url,'_blank'); else alert(fallback);}}
document.getElementById('boardBtn').onclick=()=>openMaybe(data.links.board,'先生成 board.html');
document.getElementById('reviewBtn').onclick=()=>openMaybe(data.links.review_ui,`先运行：python3 skills/n2d/n2d-review-ui/scripts/review_ui.py "${{data.root}}" ${{data.episode}} --write`);
function renderTabs(){{document.getElementById('tabs').innerHTML=tabDefs.map(([id,label])=>`<button class="tab ${{active===id?'active':''}}" data-id="${{id}}">${{label}}</button>`).join('');document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{{active=b.dataset.id;render();}});}}
function metric(label,value){{return `<div class="metric"><span>${{esc(label)}}</span><b>${{esc(value??'—')}}</b></div>`}}
function renderOverview(){{
 const m=data.metrics||{{}}, p=data.progress||{{}}, n=data.next_action||{{}};
 return `<section class="panel"><h2>本集总览</h2><div class="grid">
 ${{metric('状态',data.status)}}${{metric('阶段完成',`${{p.done_stages||0}}/${{p.total_stages||0}}`)}}${{metric('下一步',n.label||n.skill||'—')}}${{metric('机器分',`${{m.score??'—'}} (${{m.score_status||'missing'}})`)}}
 ${{metric('成本',m.cost_text)}}${{metric('生产耗时',m.duration_hms)}}${{metric('成片时长',m.runtime_hms)}}${{metric('生成尝试',m.generation_attempts)}}
 ${{metric('可交付通过率',m.final_pass_rate_text)}}${{metric('一次通过率',m.one_pass_rate_text)}}${{metric('重抽率',m.redraw_rate_text)}}${{metric('QA',`${{m.qa_blockers||0}} block / ${{m.qa_warnings||0}} warn`)}}
 </div></section>`;
}}
function renderStages(){{
 const prog=data.progress&&data.progress.stages?data.progress.stages:{{}}, sm=data.stage_metrics||{{}};
 const rows=Object.keys(prog).map(k=>{{const s=sm[k]||sm[stageKey(k)]||{{}};return `<div class="stage-row"><b>${{esc(k)}}</b><div>${{badge(prog[k])}} <span class="muted">尝试 ${{s.generation_attempts||0}} · 通过 ${{s.generation_passes||0}} · 重抽 ${{s.redraw_count||0}} · QA ${{s.qa_blockers||0}}/${{s.qa_warnings||0}}</span></div><span class="muted">${{secs(s.duration_sec)}}</span></div>`;}}).join('');
 const extra=Object.keys(sm).filter(k=>!Object.keys(prog).includes(k)).map(k=>`<div class="stage-row"><b>${{esc(k)}}</b><div><span class="muted">尝试 ${{sm[k].generation_attempts||0}} · 通过 ${{sm[k].generation_passes||0}} · 重抽 ${{sm[k].redraw_count||0}} · QA ${{sm[k].qa_blockers||0}}/${{sm[k].qa_warnings||0}}</span></div><span class="muted">${{secs(sm[k].duration_sec)}}</span></div>`).join('');
 return `<section class="panel"><h2>阶段</h2>${{rows||'<div class="muted">暂无进度阶段</div>'}}${{extra}}</section>`;
}}
function stageKey(k){{return k==='出图'?'image':k==='成片'?'compose':k==='配音'?'voice':k==='分镜设计'?'script':k}}
function secs(v){{v=Number(v||0); if(!v)return '0s'; const m=Math.floor(v/60), s=Math.round(v%60); return m?`${{m}}m${{s}}s`:`${{s}}s`;}}
function renderClips(){{
 const clips=data.clips||[]; return `<section class="panel"><h2>镜头 ${{clips.length}}</h2><div class="clip-grid">${{clips.map(c=>`<article class="clip ${{c.status}}"><div class="thumb">${{c.thumb?`<img src="${{c.thumb}}" loading="lazy">`:'无首帧'}}</div><div class="clip-body"><div class="clip-title">${{esc(c.label||c.id)}}</div><div class="muted">${{esc(c.id)}} · ${{esc(c.duration||'—')}}s</div><div class="muted">${{esc(c.scene||'')}}</div><p>${{badge(c.status)}} <span class="muted">QA ${{c.qa_total||0}} · 视频 ${{c.has_video?'有':'缺'}}</span></p>${{data.links.review_ui&&data.links.review_ui.exists?`<a class="openbtn" href="${{data.links.review_ui.url}}#clip=${{encodeURIComponent(c.id||'')}}" target="_blank">打开镜头</a>`:''}}</div></article>`).join('')}}</div></section>`;
}}
function renderIssues(){{
 const groups=(data.issues&&data.issues.groups)||[]; if(!groups.length)return '<section class="panel"><h2>问题</h2><div class="muted">暂无问题</div></section>';
 return `<section class="panel"><h2>问题：按回流阶段分组</h2>${{groups.map(g=>`<div class="panel" style="margin:10px 0 0"><h2>回 ${{esc(g.return_to_stage)}} · ${{esc((g.counts.block||0))}} block / ${{esc((g.counts.warn||0))}} warn</h2>${{(g.items||[]).slice(0,80).map(i=>`<div class="issue"><div>${{badge(i.severity)}}<br><span class="muted">${{esc(i.source)}}</span></div><div><b>${{esc(i.dimension)}}</b><br>${{esc(i.message)}}<br><span class="muted">${{esc(i.loc)}} ${{(i.affected_shots||[]).length? ' · '+esc(i.affected_shots.join(', ')):''}}</span></div><div class="muted">${{esc(i.return_to_stage)}}</div></div>`).join('')}}</div>`).join('')}}</section>`;
}}
function renderEvidence(){{
 return `<section class="panel"><h2>证据文件</h2>${{(data.evidence||[]).map(e=>`<div class="evidence-row"><b>${{esc(e.label)}}</b><div><code>${{esc(e.path)}}</code></div><div>${{e.exists?`<a class="openbtn" href="${{e.url}}" target="_blank">打开</a>`:badge('missing')}}</div></div>`).join('')}}</section>`;
}}
function renderSide(){{
 const m=data.metrics||{{}}, cs=data.clip_summary||{{}}, is=data.issues||{{}};
 document.getElementById('side').innerHTML=`<section class="panel"><h2>摘要</h2><p>${{badge(data.status)}} <span class="muted">${{esc(data.generated_at)}}</span></p><p>Clip：${{cs.total||0}}，有视频 ${{cs.with_video||0}}</p><p>问题：${{is.total||0}}（${{(is.severity&&is.severity.block)||0}} block / ${{(is.severity&&is.severity.warn)||0}} warn）</p><p>事件：${{m.event_count||0}}</p></section><section class="panel"><h2>回流任务</h2>${{(data.return_tasks||[]).slice(0,8).map(t=>`<p><b>${{esc(t.return_to_stage||'')}}</b><br><span class="muted">${{esc(t.scope||t.source||'')}}</span></p>`).join('')||'<p class="muted">暂无</p>'}}</section>`;
}}
function render(){{document.getElementById('title').textContent=`${{data.episode}} 工作台`;document.getElementById('sub').textContent=data.root;renderTabs();renderSide();document.getElementById('main').innerHTML=active==='overview'?renderOverview():active==='stages'?renderStages():active==='clips'?renderClips():active==='issues'?renderIssues():renderEvidence();}}
render();
</script></body></html>
"""


def render_html(manifest: Dict[str, Any]) -> str:
    manifest_json = (
        json.dumps(manifest, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return HTML_TEMPLATE.format(
        title=html.escape(f"{manifest.get('episode', '')} 工作台"),
        manifest_json=manifest_json,
    )


def write_episode(root: Path, ep: str, *, board_data: Optional[Dict[str, Any]] = None,
                  dashboard_eps: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, str]:
    manifest = build_episode_workspace(root, ep, board_data=board_data, dashboard_eps=dashboard_eps)
    paths = output_paths(root, ep)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["episode_dir"].mkdir(parents=True, exist_ok=True)
    paths["json"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["html"].write_text(render_html(manifest), encoding="utf-8")
    return {"json": str(paths["json"]), "html": str(paths["html"])}


def write_index(root: Path, *, board_data: Optional[Dict[str, Any]] = None) -> str:
    manifest = build_episode_index(root, board_data=board_data)
    path = output_paths(root, "第1集")["index"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def write_all(root: Path) -> Dict[str, Any]:
    b = board_manifest(root)
    dash = dashboard_episode_map(root)
    episodes = [str(e.get("episode")) for e in (b.get("episodes") or []) if isinstance(e, dict) and e.get("episode")]
    written = [write_episode(root, ep, board_data=b, dashboard_eps=dash) for ep in episodes]
    index = write_index(root, board_data=b)
    return {"index": index, "episodes": written}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Build n2d per-episode production workspace JSON/HTML.")
    ap.add_argument("root", help="作品根, e.g. 创作区/制漫剧/剧名")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--episode", help="只生成第N集")
    group.add_argument("--all", action="store_true", help="生成所有集")
    ap.add_argument("--write", action="store_true", help="write outputs; without this prints JSON")
    ap.add_argument("--index", action="store_true", help="also write/update episode_index.json")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    b = board_manifest(root)
    if ns.all:
        result = write_all(root) if ns.write else build_episode_index(root, board_data=b)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    ep = normalize_episode(ns.episode or "第1集")
    if ns.write:
        paths = write_episode(root, ep, board_data=b, dashboard_eps=dashboard_episode_map(root))
        if ns.index:
            paths["index"] = write_index(root, board_data=b)
        print(json.dumps(paths, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(build_episode_workspace(root, ep, board_data=b), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
