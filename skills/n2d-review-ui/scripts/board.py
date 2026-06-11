#!/usr/bin/env python3
"""Work-level production board for n2d — the MVP of the 「PC端 + 无限画布」 vision (Q36.6).

Reads a 作品 root's `_进度.md` state machine and renders a zoomable/pannable canvas:
作品 → 集(swimlane) → 阶段(stage chips, colored by progress) → Clip 卡(接力链 edges, QA 状态色).

Deliberately zero-build (self-contained HTML + vanilla JS), matching the repo's
"no build / no npm" convention. It READS existing artifacts only (single source of
truth): `_进度.md`, `脚本/<集>/storyboard.json`, `生产数据/score_<集>.json`, frames/clips.
Per-episode deep canvas stays in review_ui.py; this is the whole-work overview that
review_ui never covered. Heavy per-clip media inference is reused from review_ui
(not re-implemented), so the two stay one source of truth.

Usage:
  python3 board.py <作品根> [--write] [--markdown]
  python3 board.py <作品根> --serve [--port 8765]   # 起 127.0.0.1 本地服务看板
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
_COMMON = str(_SCRIPT_DIR.parent.parent / "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from n2d_contract import PRODUCTION_DIR  # noqa: E402  生产数据目录单一真值源
import n2d_route  # noqa: E402  进度解析/集号/路由单一真值源


def _load_review_ui():
    """Import review_ui as a module so we reuse its clip/frame/score helpers (no fork)."""
    spec = importlib.util.spec_from_file_location("n2d_review_ui", _SCRIPT_DIR / "review_ui.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


review_ui = _load_review_ui()

KIND = "n2d_production_board"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def work_title(root: Path) -> str:
    return root.resolve().name


def episode_block(root: Path, html_dir: Path, header: List[str], stages: List[str], row: Dict[str, str]) -> Dict[str, Any]:
    """One swimlane: stage states from `_进度.md` + (if storyboard exists) clips/seams/score."""
    ep = str(row.get("_ep") or row.get("集") or "").strip()
    ep_norm = n2d_route.normalize_episode(ep)
    stage_states = {col: n2d_route.cell_state(row.get(col, "")) for col in stages}
    done_stages = sum(1 for col in stages if n2d_route.is_progress_satisfied(str(root), row, col))

    # 前沿：下一步该跑哪个 skill（mode-aware；与 n2d-progress 同源）。
    # cmd = 契约里的下一步命令模板（多为 Claude Code 斜杠命令 /n2d-* {root} {ep}），格式化好供桌面端命令面板预填。
    route = n2d_route.stage_of(str(root), row, header)
    frontier = None
    if route.get("cmd"):
        try:
            cmd = str(route["cmd"]).format(root=str(root), ep=ep_norm)
        except (KeyError, IndexError, ValueError):
            cmd = str(route["cmd"])
        frontier = {"label": route.get("label"), "skill": route.get("skill"), "col": route.get("col"), "cmd": cmd}

    # Clips/seams/score 只在该集已有 storyboard 时采集（未开工的集保持轻量）
    clips: List[Dict[str, Any]] = []
    seams: List[Dict[str, Any]] = []
    score_block: Dict[str, Any] = {"available": False}
    sb_path = review_ui.storyboard_path(root, ep_norm)
    if sb_path.is_file():
        storyboard = review_ui.load_storyboard(root, ep_norm)
        score = review_ui.load_score(root, ep_norm)
        flags = review_ui.flatten_evidence(score)
        clips_full = review_ui.collect_clips(root, ep_norm, html_dir, storyboard, flags)
        clips = [_slim_clip(c) for c in clips_full]
        seams = [_slim_seam(s) for s in review_ui.collect_seams(clips_full, flags)]
        score_block = review_ui.score_summary(root, ep_norm, score)

    # 跨集深链：board 点 Clip → 跳该集 review_ui 深画布（同在 生产数据/，相对链接）
    ru_html = production_dir(root) / f"review_ui_{ep_norm}.html"
    review_ui_link = {"url": f"review_ui_{ep_norm}.html", "exists": ru_html.is_file()}

    return {
        "episode": ep_norm,
        "num": row.get("_num"),
        "word_count": row.get("字数") or row.get("字数估计"),
        "review_ui": review_ui_link,
        "stages": stage_states,
        "done_stages": done_stages,
        "total_stages": len(stages),
        "frontier": frontier,
        "has_storyboard": sb_path.is_file(),
        "clips": clips,
        "seams": seams,
        "score": {"available": score_block.get("available", False),
                  "total_score": score_block.get("total_score"),
                  "status": score_block.get("status")},
    }


def _clip_status(clip: Dict[str, Any]) -> str:
    flags = clip.get("qa_flags") or []
    if any(f.get("severity") == "block" for f in flags):
        return "block"
    missing = any(clip.get(k) and not clip[k].get("exists") for k in ("first_frame", "end_frame", "video"))
    if any(f.get("severity") == "warn" for f in flags) or missing:
        return "warn"
    return "pass"


def _slim_clip(clip: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "index": clip.get("index"),
        "id": clip.get("id"),
        "label": clip.get("label"),
        "duration": clip.get("duration"),
        "scene": clip.get("scene"),
        "transition": clip.get("transition"),
        "status": _clip_status(clip),
        "thumb": (clip.get("first_frame") or {}).get("url") if (clip.get("first_frame") or {}).get("exists") else None,
        "has_video": bool((clip.get("video") or {}).get("exists")),
        "flags": len(clip.get("qa_flags") or []),
    }


def _slim_seam(seam: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "index": seam.get("index"),
        "from": seam.get("from"),
        "to": seam.get("to"),
        "transition": seam.get("transition"),
        "block": any(f.get("severity") == "block" for f in (seam.get("qa_flags") or [])),
    }


def build_manifest(root: Path) -> Dict[str, Any]:
    html_dir = production_dir(root)
    try:
        header, rows = n2d_route.parse_progress(str(root))
    except (FileNotFoundError, ValueError) as exc:
        return {"kind": KIND, "version": VERSION, "root": str(root), "title": work_title(root),
                "generated_at": now_iso(), "error": f"无法解析 _进度.md：{exc}", "stages": [], "episodes": []}

    stages = [c for c in n2d_route.flow_columns(header) if c != "raw"]
    rows_sorted = sorted(rows, key=lambda r: int(r.get("_num", 10 ** 9)))
    episodes = [episode_block(root, html_dir, header, stages, row) for row in rows_sorted]

    done_eps = sum(1 for e in episodes if e["done_stages"] >= e["total_stages"] and e["total_stages"] > 0)
    total_cells = sum(e["total_stages"] for e in episodes) or 1
    done_cells = sum(e["done_stages"] for e in episodes)
    try:
        summary_route = n2d_route.summarize(str(root))
        bottleneck = summary_route.get("bottleneck") or {}
        first = summary_route.get("first") or None
    except Exception:
        bottleneck, first = {}, None

    first_action = None
    if first:
        fa_cmd = None
        if first.get("cmd"):
            try:
                fa_cmd = str(first["cmd"]).format(root=str(root), ep=first.get("ep"))
            except (KeyError, IndexError, ValueError):
                fa_cmd = str(first["cmd"])
        first_action = {"episode": first.get("ep"), "label": first.get("label"), "skill": first.get("skill"), "cmd": fa_cmd}

    return {
        "kind": KIND,
        "version": VERSION,
        "root": str(root),
        "title": work_title(root),
        "generated_at": now_iso(),
        "stages": stages,
        "episodes": episodes,
        "summary": {
            "episodes": len(episodes),
            "done_episodes": done_eps,
            "completion_pct": round(100.0 * done_cells / total_cells, 1),
            "bottleneck": bottleneck,
            "first_action": first_action,
        },
    }


# ── self-contained zero-build canvas (vanilla JS pan/zoom + swimlanes) ──
HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>
:root{{--bg:#f7f8fb;--ink:#172033;--muted:#657085;--line:#d8dee9;--panel:#fff;
--red:#c7372f;--amber:#b7791f;--green:#2f855a;--grey:#9aa3b2;--blue:#2563eb;}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink);overflow:hidden}}
button,select{{font:inherit}}
.topbar{{position:fixed;inset:0 0 auto 0;height:60px;display:flex;align-items:center;gap:12px;padding:8px 16px;background:rgba(255,255,255,.95);border-bottom:1px solid var(--line);z-index:10}}
.title strong{{display:block;font-size:15px}}.title span{{display:block;color:var(--muted);font-size:12px;margin-top:2px}}
.toolbar{{display:flex;align-items:center;gap:8px;margin-left:auto;flex-wrap:wrap}}
.iconbtn{{width:32px;height:32px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer}}
.control{{height:32px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:0 10px}}
.viewport{{position:fixed;inset:60px 0 0 0;overflow:hidden;cursor:grab;
background:linear-gradient(#e8edf5 1px,transparent 1px),linear-gradient(90deg,#e8edf5 1px,transparent 1px);background-size:40px 40px}}
.canvas{{position:absolute;left:0;top:0;transform-origin:0 0}}
svg.edges{{position:absolute;left:0;top:0;overflow:visible;pointer-events:none}}
.lane{{position:absolute;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.55)}}
.lane-head{{position:absolute;display:flex;flex-direction:column;gap:2px;padding:8px 10px;width:150px;cursor:pointer;border-radius:8px}}
.lane-head:hover{{background:rgba(37,99,235,.06)}}
.lane-head b{{font-size:14px}}.lane-head small{{color:var(--muted);font-size:11px;line-height:1.35}}
.donebar{{height:6px;border-radius:999px;background:#edf2f7;overflow:hidden;margin-top:4px}}
.donebar>span{{display:block;height:100%;background:var(--green)}}
.frontier{{margin-top:4px;font-size:11px;color:var(--blue);border:1px dashed #b9c8f0;border-radius:6px;padding:1px 5px;align-self:flex-start}}
.chip{{position:absolute;width:96px;height:48px;border:1px solid var(--line);border-radius:8px;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:11px;gap:2px;box-shadow:0 4px 10px rgba(25,35,55,.05)}}
.chip .dot{{width:8px;height:8px;border-radius:50%;background:var(--grey)}}
.chip.done{{border-color:#9bd8b9;background:#ecfdf3}}.chip.done .dot{{background:var(--green)}}
.chip.partial{{border-color:#f4d39a;background:#fff8e8}}.chip.partial .dot{{background:var(--amber)}}
.chip.rough{{border-color:#f4d39a;background:#fff8e8}}.chip.rough .dot{{background:var(--amber)}}
.chip.na{{opacity:.5}}.chip.na .dot{{background:#cbd2dc}}
.chip.todo{{}}
.chip b{{font-weight:600;text-align:center;line-height:1.1;max-width:88px;overflow:hidden}}
.chip small{{color:var(--muted);font-size:10px}}
.clip{{position:absolute;width:118px;border:1px solid var(--line);border-radius:8px;background:#fff;overflow:hidden;box-shadow:0 6px 14px rgba(25,35,55,.07);cursor:pointer}}
.clip:hover{{outline:2px solid var(--blue);outline-offset:1px}}
.clip.hidden{{display:none}}
.clip .thumb{{height:66px;background:#eef2f7;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:11px}}
.clip .thumb img{{width:100%;height:100%;object-fit:cover}}
.clip .cap{{padding:4px 6px;font-size:11px;display:flex;justify-content:space-between;align-items:center;gap:4px}}
.clip.block{{border-color:#f1b3ae}}.clip.block .cap{{background:#fff1f0}}
.clip.warn{{border-color:#f4d39a}}.clip.warn .cap{{background:#fff8e8}}
.clip.pass{{border-color:#9bd8b9}}
.sdot{{width:7px;height:7px;border-radius:50%;background:var(--green);flex:0 0 auto}}
.clip.block .sdot{{background:var(--red)}}.clip.warn .sdot{{background:var(--amber)}}
.tag{{position:absolute;font-size:11px;color:var(--muted);padding:1px 6px;border:1px solid var(--line);border-radius:6px;background:#fff}}
.help{{position:fixed;right:12px;bottom:12px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:rgba(255,255,255,.92);color:var(--muted);font-size:12px;z-index:11}}
.legend{{display:flex;gap:10px;align-items:center;font-size:12px;color:var(--muted)}}
.legend i{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:3px;vertical-align:-1px}}
.banner{{position:fixed;inset:60px 0 auto 0;padding:8px 16px;background:#fff1f0;color:var(--red);font-size:13px;z-index:9}}
</style></head>
<body>
<div class="topbar">
 <div class="title"><strong id="titleText"></strong><span id="subtitleText"></span></div>
 <div class="toolbar">
  <span class="legend"><i style="background:var(--green)"></i>完成<i style="background:var(--amber)"></i>进行中<i style="background:var(--grey)"></i>未开始<i style="background:var(--red)"></i>QA阻断</span>
  <select class="control" id="filter" title="筛选集">
    <option value="all">全部集</option><option value="incomplete">未完成的集</option><option value="started">已开工的集</option><option value="hasclips">有分镜的集</option>
  </select>
  <button class="iconbtn" id="zoomOut">−</button><button class="iconbtn" id="zoomIn">+</button><button class="iconbtn" id="reset">⌂</button>
 </div>
</div>
<div class="viewport" id="viewport"><div class="canvas" id="canvas"></div></div>
<div class="help">拖拽平移 · 滚轮缩放 · 空格重置 · 点 Clip/集头→深入该集人审画布</div>
<script id="manifest" type="application/json">{manifest_json}</script>
<script>
const data = JSON.parse(document.getElementById('manifest').textContent);
const canvas = document.getElementById('canvas');
const viewport = document.getElementById('viewport');
let scale=.8, offX=20, offY=16, drag=false, dragMoved=false, sx=0, sy=0, ox=0, oy=0;
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));}}
function tf(){{canvas.style.transform=`translate(${{offX}}px,${{offY}}px) scale(${{scale}})`;}}
// layout constants
const LANE_X=24, HEAD_W=160, STAGE_X0=HEAD_W+24, STAGE_W=104, STAGE_H=48;
const CLIP_X0=STAGE_X0, CLIP_W=130, CLIP_H=96, ROW_GAP=28;
function laneHeight(ep){{ return 14 + STAGE_H + (ep.clips.length? (ROW_GAP+CLIP_H+20):16); }}
function build(){{
  document.getElementById('titleText').textContent = `${{data.title||data.root}} · 生产看板`;
  const sm = data.summary||{{}};
  document.getElementById('subtitleText').textContent =
    `${{sm.episodes||0}} 集 · 完成度 ${{sm.completion_pct??0}}% · ${{(sm.first_action? '下一步 '+sm.first_action.episode+' '+(sm.first_action.label||'') : '✅ 全部就绪')}} · ${{data.generated_at}}`;
  if(data.error){{ const b=document.createElement('div'); b.className='banner'; b.textContent=data.error; document.body.appendChild(b); return; }}
  const stages=data.stages||[];
  const laneW = STAGE_X0 + Math.max(stages.length*STAGE_W, ((data.episodes||[]).reduce((m,e)=>Math.max(m,e.clips.length),0))*CLIP_W) + 40;
  let y=14, parts=[], edges=[];
  (data.episodes||[]).forEach((ep,ei)=>{{
    const h=laneHeight(ep);
    const sc=ep.score&&ep.score.available? ` · 分${{ep.score.total_score}}(${{ep.score.status}})`:'';
    parts.push(`<div class="lane" data-ep="${{ei}}" style="left:${{LANE_X}}px;top:${{y}}px;width:${{laneW}}px;height:${{h}}px"></div>`);
    parts.push(`<div class="lane-head" data-ep="${{ei}}" title="点开该集人审深画布" style="left:${{LANE_X+8}}px;top:${{y+8}}px"><b>${{esc(ep.episode)}}</b>`+
      `<small>${{ep.done_stages}}/${{ep.total_stages}} 阶段${{esc(sc)}}</small>`+
      `<div class="donebar"><span style="width:${{Math.round(100*ep.done_stages/Math.max(1,ep.total_stages))}}%"></span></div>`+
      (ep.frontier? `<span class="frontier">下一步：${{esc(ep.frontier.label||ep.frontier.skill||'')}}</span>`:`<span class="frontier" style="color:var(--green);border-color:#9bd8b9">本集就绪</span>`)+
      `</div>`);
    // stage chips
    const cy=y+8;
    stages.forEach((st,si)=>{{
      const stt=ep.stages[st]||'todo';
      parts.push(`<div class="chip ${{stt}}" style="left:${{STAGE_X0+si*STAGE_W}}px;top:${{cy}}px"><span class="dot"></span><b>${{esc(st)}}</b><small>${{esc(stt)}}</small></div>`);
    }});
    // clip row + 接力链 edges
    if(ep.clips.length){{
      const cyc=cy+STAGE_H+ROW_GAP;
      parts.push(`<div class="tag" style="left:${{STAGE_X0}}px;top:${{cyc-20}}px">分镜 ${{ep.clips.length}} Clip · 接力链</div>`);
      ep.clips.forEach((cl,ci)=>{{
        const x=CLIP_X0+ci*CLIP_W;
        parts.push(`<div class="clip ${{cl.status}}" data-ep="${{ei}}" data-clip="${{esc(cl.id||'')}}" title="点开该集人审深画布（定位本 Clip）" data-search="${{esc((cl.label||'')+' '+(cl.scene||'')+' '+(cl.id||''))}}" style="left:${{x}}px;top:${{cyc}}px">`+
          `<div class="thumb">${{cl.thumb? `<img src="${{cl.thumb}}" loading="lazy">`:'无首帧'}}</div>`+
          `<div class="cap"><span>${{esc(cl.id||('C'+cl.index))}}</span><span class="sdot" title="${{cl.status}}"></span></div></div>`);
        if(ci>0){{ const x0=CLIP_X0+(ci-1)*CLIP_W+CLIP_W-6, x1=x+6, ey=cyc+CLIP_H/2;
          const blk=(ep.seams[ci-1]||{{}}).block;
          edges.push(`<path d="M${{x0}},${{ey}} C${{x0+22}},${{ey}} ${{x1-22}},${{ey}} ${{x1}},${{ey}}" stroke="${{blk?'#c7372f':'#9aa3b2'}}" stroke-width="2" fill="none" marker-end="url(#arw)"/>`);
        }}
      }});
    }}
    y += h + 18;
  }});
  canvas.style.width=(laneW+LANE_X+40)+'px'; canvas.style.height=(y+40)+'px';
  canvas.innerHTML = `<svg class="edges" width="${{laneW+LANE_X+40}}" height="${{y+40}}">`+
    `<defs><marker id="arw" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#9aa3b2"/></marker></defs>`+
    edges.join('')+`</svg>`+parts.join('');
  tf();
}}
function applyFilter(){{
  const f=document.getElementById('filter').value;
  document.querySelectorAll('.lane').forEach(el=>{{
    const ep=data.episodes[+el.dataset.ep]; let ok=true;
    if(f==='incomplete') ok=ep.done_stages<ep.total_stages;
    if(f==='started') ok=ep.done_stages>0;
    if(f==='hasclips') ok=ep.clips.length>0;
    el.style.opacity = ok? '1':'.18';
  }});
}}
document.getElementById('filter').addEventListener('change',applyFilter);
document.getElementById('zoomIn').onclick=()=>{{scale=Math.min(2.2,scale*1.12);tf();}};
document.getElementById('zoomOut').onclick=()=>{{scale=Math.max(.2,scale/1.12);tf();}};
document.getElementById('reset').onclick=()=>{{scale=.8;offX=20;offY=16;tf();}};
viewport.addEventListener('mousedown',e=>{{drag=true;dragMoved=false;sx=e.clientX;sy=e.clientY;ox=offX;oy=offY;viewport.style.cursor='grabbing';}});
window.addEventListener('mouseup',()=>{{drag=false;viewport.style.cursor='grab';}});
window.addEventListener('mousemove',e=>{{if(!drag)return;if(Math.abs(e.clientX-sx)+Math.abs(e.clientY-sy)>4)dragMoved=true;offX=ox+e.clientX-sx;offY=oy+e.clientY-sy;tf();}});
// 跨集深链：点 Clip → 该集 review_ui 深画布并定位本 Clip；点集头 → 该集深画布。拖动不触发。
function openReview(ei, clipId){{
  const ep=data.episodes[ei]; if(!ep) return;
  const ru=ep.review_ui||{{}};
  if(!ru.url||!ru.exists){{
    toast(`${{ep.episode}} 人审深画布未生成 — 先跑：python3 skills/n2d-review-ui/scripts/review_ui.py "${{data.root}}" ${{ep.episode}} --write`);
    return;
  }}
  window.open(ru.url + (clipId? ('#clip='+encodeURIComponent(clipId)) : ''), '_blank');
}}
canvas.addEventListener('click',e=>{{
  if(dragMoved) return;
  const clipEl=e.target.closest('.clip');
  if(clipEl){{ openReview(+clipEl.dataset.ep, clipEl.dataset.clip); return; }}
  const headEl=e.target.closest('.lane-head');
  if(headEl) openReview(+headEl.dataset.ep, null);
}});
let toastTimer;
function toast(msg){{
  let el=document.getElementById('toast');
  if(!el){{el=document.createElement('div');el.id='toast';el.style.cssText='position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:#172033;color:#fff;padding:10px 14px;border-radius:8px;font-size:13px;max-width:84vw;z-index:20;box-shadow:0 10px 28px rgba(0,0,0,.28)';document.body.appendChild(el);}}
  el.textContent=msg; el.style.opacity='1'; clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>{{el.style.opacity='0';}},6000);
}}
viewport.addEventListener('wheel',e=>{{e.preventDefault();const f=e.deltaY>0?.92:1.08;scale=Math.max(.2,Math.min(2.2,scale*f));tf();}},{{passive:false}});
window.addEventListener('keydown',e=>{{if(e.code==='Space'){{e.preventDefault();document.getElementById('reset').click();}}}});
build();
</script>
</body></html>
"""


def render_html(manifest: Dict[str, Any]) -> str:
    manifest_json = (
        json.dumps(manifest, ensure_ascii=False)
        .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    )
    return HTML_TEMPLATE.format(title=html.escape(manifest.get("title", "n2d 生产看板")), manifest_json=manifest_json)


def output_paths(root: Path) -> Dict[str, Path]:
    out = production_dir(root)
    return {"dir": out, "json": out / "board.json", "html": out / "board.html"}


def write_outputs(root: Path, manifest: Dict[str, Any]) -> Dict[str, str]:
    paths = output_paths(root)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["json"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["html"].write_text(render_html(manifest), encoding="utf-8")
    return {k: str(v) for k, v in paths.items() if k != "dir"}


def markdown_summary(manifest: Dict[str, Any], paths: Optional[Dict[str, str]] = None) -> str:
    sm = manifest.get("summary", {})
    lines = [
        "# n2d 生产看板",
        "",
        f"- 作品：{manifest.get('title')}",
        f"- 集数：{sm.get('episodes')} · 完成集：{sm.get('done_episodes')} · 完成度：{sm.get('completion_pct')}%",
        f"- 阶段数：{len(manifest.get('stages', []))}",
    ]
    fa = sm.get("first_action")
    if fa:
        lines.append(f"- 下一步：{fa.get('episode')} {fa.get('label')}（{fa.get('skill')}）")
    if paths:
        lines += [f"- html: {paths.get('html')}", f"- json: {paths.get('json')}"]
    return "\n".join(lines) + "\n"


def serve(root: Path, manifest: Dict[str, Any], port: int) -> int:
    """Write outputs then serve the 作品根 over 127.0.0.1 so relative media URLs resolve."""
    import http.server
    import socketserver
    import functools

    paths = write_outputs(root, manifest)
    rel = os.path.relpath(paths["html"], root).replace(os.sep, "/")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    except OSError as exc:
        print(f"[err] 无法在 127.0.0.1:{port} 起服务：{exc}（换 --port）", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{port}/{rel}"
    print(f"[board] 本地看板：{url}")
    print("[board] Ctrl-C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[board] 已停止")
    finally:
        httpd.server_close()
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Build n2d work-level production board (whole-drama canvas).")
    ap.add_argument("root", help="作品根, e.g. 制漫剧/剧名")
    ap.add_argument("--write", action="store_true", help="write 生产数据/board.html + board.json")
    ap.add_argument("--markdown", action="store_true", help="print a Markdown summary (with --write)")
    ap.add_argument("--serve", action="store_true", help="write then serve on 127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    manifest = build_manifest(root)
    if ns.serve:
        return serve(root, manifest, ns.port)
    if ns.write:
        paths = write_outputs(root, manifest)
        print(markdown_summary(manifest, paths) if ns.markdown else f"wrote {paths['html']}\nwrote {paths['json']}")
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
