#!/usr/bin/env python3
"""一致性编排（O1）——一键串跑全部一致性检测器，出一张汇总分档报告。

2026 产线核心已从"单点能力"转到**编排层**：检测器再多，没被自动跑就等于没有。
本脚本把散落的检测器统一调起来，n2d-review 模式①工作流第 1 步「跑机检套件」即调它：

  语义谱系 P0 · 状态百科 P1 · 多模态 P2 · 视觉契约继承 · 锚点门 N3 · 脸 G1 ·
  服装/配色 N1 · 片内时序 N2 · 场景 O2 · 糊/低质 N4 · 风格 S1 · 字幕对齐 L1

每个子检测器各自缺库优雅跳过（见各脚本）；本编排只汇总、不重复实现。
纯函数 `summarize` 无依赖、带 pytest。

用法：python3 consistency_audit.py <作品根> 第N集 [--json]
退出码：有任一 🔴 → 1，否则 0。
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import (  # noqa: E402  findings kind / 生产数据目录 / 一致性维度单一真值源
    CONSISTENCY_FINDINGS_KIND,
    consistency_dim_spec,
    production_dir,
)
from n2d_contract_diff import diff_contracts  # noqa: E402  视觉契约继承 Diff 核心（common 层单一真值源）

import face_consistency as fc
import outfit_consistency as oc
import temporal_consistency as tcheck
import quality_check as qc
import scene_consistency as sc
import style_consistency as stc
import semantic_continuity as semc
import state_continuity as statec
import multimodal_consistency as mmc
import subtitle_align as sa


def _verdicts(rows: List[dict]) -> List[str]:
    return [r.get("verdict", "ok") for r in rows]


def summarize(sections: Dict[str, dict]) -> dict:
    """把各检测器的结果压成 {dim: {block,warn,ok,skipped}} + 总 block 数。纯函数·可测。"""
    out: Dict[str, dict] = {}
    total_block = 0
    for dim, sec in sections.items():
        skipped = sec.get("skipped", False)
        vs = sec.get("verdicts", [])
        b = sum(1 for v in vs if v == "block")
        w = sum(1 for v in vs if v == "warn")
        ok = sum(1 for v in vs if v == "ok")
        out[dim] = {"block": b, "warn": w, "ok": ok, "n": len(vs), "skipped": skipped}
        total_block += b
    return {"by_dim": out, "total_block": total_block}


def unique(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def shot_label(value: Any) -> List[str]:
    labels: List[str] = []
    if isinstance(value, int):
        labels.append(f"Clip_{value:02d}")
    text = str(value or "")
    for match in re.finditer(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)", text):
        labels.append(f"Clip_{int(match.group(1)):02d}")
    return unique(labels)


def artifacts_from_text(text: str) -> List[str]:
    pattern = r"(?:出图|出视频|合成|脚本|设定库|合规)/[^\s，。；;|)）]+"
    return unique(m.group(0).rstrip("，。；;:：") for m in re.finditer(pattern, text or ""))


def contract_inheritance_result(root: str, ep: str) -> dict:
    """Read image/video overview contracts and expose inherit_contract diff as audit rows."""
    img_rel = os.path.join("出图", ep, "prompt", "00_总览.md")
    vid_rel = os.path.join("出视频", ep, "prompt", "00_总览.md")
    img_path = os.path.join(root, img_rel)
    vid_path = os.path.join(root, vid_rel)
    if not os.path.isfile(img_path) or not os.path.isfile(vid_path):
        missing = [rel for rel, path in ((img_rel, img_path), (vid_rel, vid_path)) if not os.path.isfile(path)]
        return {"available": False, "fields": [], "notes": [f"契约继承检查跳过：缺 {', '.join(missing)}"]}
    try:
        rows = diff_contracts(
            open(img_path, encoding="utf-8").read(),
            open(vid_path, encoding="utf-8").read(),
        )
    except Exception as exc:
        return {"available": False, "fields": [], "notes": [f"契约继承检查跳过：{exc}"]}
    fields: List[dict] = []
    for row in rows:
        severity = str(row.get("severity") or "")
        verdict = "ok" if severity == "pass" else severity if severity in {"block", "warn"} else "warn"
        fields.append({
            "verdict": verdict,
            "field": row.get("field"),
            "message": row.get("note") or row.get("status") or "",
            "status": row.get("status"),
            "loc": f"视觉契约/{row.get('field')}",
            "affected_artifacts": [img_rel, vid_rel],
        })
    return {"available": True, "fields": fields, "notes": []}


def normalize_details(rows: Sequence[dict], *, dim: str, ep: str, stage: str,
                      default_artifacts: Sequence[str], limit: int = 40) -> List[dict]:
    details: List[dict] = []
    for raw in rows[:limit]:
        row = dict(raw)
        shots: List[str] = []
        for key in ("shot", "heading", "target", "png", "message", "loc"):
            shots.extend(shot_label(row.get(key)))
        artifacts = list(default_artifacts)
        for key in ("source", "target", "png", "message", "loc"):
            artifacts.extend(artifacts_from_text(str(row.get(key) or "")))
        png = str(row.get("png") or "")
        if png and "/" not in png:
            artifacts.append(f"出图/{ep}/图片/{png}")
        row.setdefault("dimension", dim)
        row.setdefault("return_to_stage", stage)
        row.setdefault("rerun_scope", default_scope(dim, stage))
        row["affected_shots"] = unique([*row.get("affected_shots", []), *shots])
        row["affected_artifacts"] = unique([*row.get("affected_artifacts", []), *artifacts])
        details.append(row)
    return details


def default_scope(dim: str, stage: str) -> str:
    spec = consistency_dim_spec(dim)
    if spec:
        return str(spec.get("scope") or f"回 {stage} 修复该一致性维度。")
    if dim == "语义谱系(P0)":
        return "回 n2d-script 阶段2或 prompt 生成层，修 storyboard→出图/出视频的语义继承缺口。"
    if dim == "状态百科(P1)":
        return "回 n2d-image，修 visual_state_ledger / 出图分镜 prompt 的状态锁；必要时回 storyboard 修状态演进。"
    if dim == "多模态(P2)":
        return "回 n2d-image，按离群道具/场景/法宝参考组只重出受影响镜头。"
    return f"回 {stage} 修复该一致性维度。"


def section_from_result(
    *,
    dim: str,
    result: dict,
    detail_key: str,
    skipped: bool,
    ep: str,
    stage: str,
    default_artifacts: Sequence[str],
) -> dict:
    details = normalize_details(
        [r for r in result.get(detail_key, []) if isinstance(r, dict)],
        dim=dim,
        ep=ep,
        stage=stage,
        default_artifacts=default_artifacts,
    )
    return {
        "skipped": skipped,
        "verdicts": _verdicts(details),
        "notes": result.get("notes", []),
        "details": details,
        "return_to_stage": stage,
        "rerun_scope": default_scope(dim, stage),
    }


def build_auto_return_tasks(sections: Dict[str, dict]) -> List[dict]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for dim, sec in sections.items():
        stage = str(sec.get("return_to_stage") or "image")
        active = [d for d in sec.get("details", []) if d.get("verdict") in ("block", "warn")]
        if not active:
            continue
        key = (stage, dim)
        item = grouped.setdefault(key, {
            "return_to_stage": stage,
            "dimensions": [dim],
            "scope": [str(sec.get("rerun_scope") or default_scope(dim, stage))],
            "affected_shots": [],
            "affected_artifacts": [],
            "findings": [],
        })
        for detail in active:
            item["affected_shots"].extend(detail.get("affected_shots", []))
            item["affected_artifacts"].extend(detail.get("affected_artifacts", []))
            item["findings"].append(detail)
    tasks: List[dict] = []
    for item in grouped.values():
        shots = unique(item["affected_shots"])
        artifacts = unique(item["affected_artifacts"])
        scope = "；".join(unique(item["scope"]))
        if shots:
            scope += "；定位镜头：" + "、".join(shots)
        if artifacts:
            scope += "；定位产物：" + "、".join(artifacts[:8])
        tasks.append({
            "return_to_stage": item["return_to_stage"],
            "dimensions": item["dimensions"],
            "scope": scope,
            "affected_shots": shots,
            "affected_artifacts": artifacts,
            "findings": item["findings"][:12],
        })
    return tasks


def active_findings(details: Sequence[dict]) -> List[dict]:
    """details → 检出条目（block/warn），逐条带 severity（外发 findings 结构）。"""
    out: List[dict] = []
    for detail in details:
        if not isinstance(detail, dict) or detail.get("verdict") not in ("block", "warn"):
            continue
        row = dict(detail)
        row["severity"] = row.get("verdict")
        out.append(row)
    return out


def run(root: str, ep: str) -> dict:
    sections: Dict[str, dict] = {}
    export_rows: List[dict] = []  # 结构化外发：逐条带 维度/严重度/镜头定位/return_to_stage

    def collect_simple(dim: str, rows: Sequence[dict], *, stage: str, default_artifacts: Sequence[str]) -> None:
        """简单段（只存 verdicts 的维度）的检出行 → 与 details 同构的外发条目。"""
        details = normalize_details(
            [r for r in rows if isinstance(r, dict)],
            dim=dim, ep=ep, stage=stage, default_artifacts=default_artifacts,
        )
        export_rows.extend(active_findings(details))

    # P0 语义谱系 Diff（raw/voiceover → storyboard → image/video prompt）
    sem = semc.analyze(root, ep)
    sections["语义谱系(P0)"] = section_from_result(
        dim="语义谱系(P0)",
        result=sem,
        detail_key="findings",
        skipped=not sem.get("available", False),
        ep=ep,
        stage="script_stage2",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt", f"出视频/{ep}/prompt"),
    )

    # P1 n2d 动态百科 / 状态哨兵
    stt = statec.analyze(root, ep)
    sections["状态百科(P1)"] = section_from_result(
        dim="状态百科(P1)",
        result=stt,
        detail_key="alerts",
        skipped=not stt.get("available", False) or not stt.get("states", []),
        ep=ep,
        stage="image",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json"),
    )

    # P2 多模态视觉语义/道具漂移（本地 embedding，缺库优雅跳过）
    mm = mmc.analyze(root, ep)
    sections["多模态(P2)"] = section_from_result(
        dim="多模态(P2)",
        result=mm,
        detail_key="shots",
        skipped=not mm.get("available", False) or not mm.get("groups", {}),
        ep=ep,
        stage="image",
        default_artifacts=(f"出图/{ep}/prompt/01_分镜出图.md", f"出图/{ep}/图片"),
    )

    # 出图 → 出视频 视觉契约继承 Diff（光位锚/轴线漂移是视频前硬风险）
    contract_dim = "契约继承"
    contract_spec = consistency_dim_spec("contract_inheritance") or {}
    contract = contract_inheritance_result(root, ep)
    sections[contract_dim] = section_from_result(
        dim=contract_dim,
        result=contract,
        detail_key="fields",
        skipped=not contract.get("available", False),
        ep=ep,
        stage=str(contract_spec.get("return_to_stage") or "video_prompt"),
        default_artifacts=(f"出图/{ep}/prompt/00_总览.md", f"出视频/{ep}/prompt/00_总览.md"),
    )

    # N3 锚点门（全篇定妆，不分集）
    a = fc.audit_anchors(root)
    sections["锚点门(N3)"] = {"skipped": not a.get("available", False),
                             "verdicts": _verdicts(a.get("anchors", [])), "notes": a.get("notes", [])}
    collect_simple("锚点门(N3)", a.get("anchors", []), stage="image", default_artifacts=("出图/共享/图片",))

    # G1 脸（insightface 缺席时自动降级 Pillow 基础机检：mode=pillow_fallback，供 n2d-score 降权消费）
    f = fc.analyze(root, ep)
    sections["脸(G1)"] = {"skipped": not f.get("available", False),
                         "verdicts": [s.get("verdict") for s in f.get("shots", []) if s.get("verdict") != "noface"],
                         "mode": f.get("mode"),
                         "precision": f.get("precision"),
                         "notes": f.get("notes", [])}
    collect_simple("脸(G1)", [s for s in f.get("shots", []) if s.get("verdict") != "noface"],
                   stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # N1 服装/配色
    o = oc.analyze(root, ep)
    sections["服装配色(N1)"] = {"skipped": not o.get("available", False),
                              "verdicts": _verdicts(o.get("shots", [])), "notes": o.get("notes", [])}
    collect_simple("服装配色(N1)", o.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # N2 片内时序
    t = tcheck.analyze(root, ep)
    sections["片内时序(N2)"] = {"skipped": not t.get("clips", []) and bool(t.get("notes")),
                              "verdicts": [c.get("verdict") for c in t.get("clips", [])], "notes": t.get("notes", [])}
    collect_simple("片内时序(N2)", t.get("clips", []), stage="video", default_artifacts=(f"出视频/{ep}/视频",))

    # O2 场景
    s = sc.analyze(root, ep)
    sections["场景(O2)"] = {"skipped": not s.get("available", False),
                          "verdicts": _verdicts(s.get("shots", [])), "notes": s.get("notes", [])}
    collect_simple("场景(O2)", s.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # S1 风格漂移
    st = stc.analyze(root, ep)
    sections["风格(S1)"] = {"skipped": not st.get("available", False) or st.get("floor") is None,
                          "verdicts": _verdicts(st.get("shots", [])), "notes": st.get("notes", [])}
    collect_simple("风格(S1)", st.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # 接缝 接力(尾帧 vs 下一首帧)——PNG 层，把"逐接缝人判"降成机检初筛
    sm = tcheck.seam_analyze(root, ep)
    sections["接缝接力"] = {"skipped": bool(sm.get("notes")) and not sm.get("seams"),
                         "verdicts": _verdicts(sm.get("seams", [])), "notes": sm.get("notes", [])}
    collect_simple("接缝接力", sm.get("seams", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # 字幕对齐(L1)——双语短语边界/阅读速度/译文完整性（补 mechanical_check 的"条数对账"盲区）
    sub = sa.analyze(root, ep)
    sections["字幕对齐(L1)"] = {"skipped": not sub.get("available", False),
                             "verdicts": _verdicts(sub.get("rows", [])), "notes": sub.get("notes", [])}
    collect_simple("字幕对齐(L1)", sub.get("rows", []), stage="script_stage2",
                   default_artifacts=(f"脚本/{ep}/字幕_中文.srt", f"脚本/{ep}/字幕_英文.srt"))

    # N4 糊/低质
    q = qc.analyze(root, ep)
    sections["糊/低质(N4)"] = {"skipped": not q.get("available", False),
                             "verdicts": _verdicts(q.get("shots", [])), "notes": q.get("notes", [])}
    collect_simple("糊/低质(N4)", q.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # 结构化段（P0/P1/P2）已有 details：直接取检出条目，避免双重归一
    for sec in sections.values():
        export_rows.extend(active_findings(sec.get("details", [])))

    summary = summarize(sections)
    return {
        "root": root,
        "episode": ep,
        "summary": summary,
        "sections": sections,
        "findings": export_rows,
        "auto_return_tasks": build_auto_return_tasks(sections),
    }


def findings_payload(res: dict) -> dict:
    """run() 结果 → 结构化外发 payload（kind=CONSISTENCY_FINDINGS_KIND，单一真值源）。"""
    return {
        "kind": CONSISTENCY_FINDINGS_KIND,
        "version": 1,
        "root": res.get("root", ""),
        "episode": res.get("episode", ""),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "summary": res.get("summary", {}),
        "findings": res.get("findings", []),
        "auto_return_tasks": res.get("auto_return_tasks", []),
    }


def _append_dashboard_event(root: str, ep: str, res: dict, findings_path: str) -> bool:
    """复用 n2d-dashboard 的事件写入约定，登记一条 consistency_findings 事件（best-effort）。

    同集旧事件按 (episode, event, source) 替换而非堆积（沿用 cmd_gate 的 replace 约定）。
    dashboard 模块加载失败/写失败不阻塞审计——findings JSON 文件才是主产物。
    """
    try:
        dash_py = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "n2d-dashboard", "scripts", "dashboard.py"))
        spec = importlib.util.spec_from_file_location("n2d_dashboard_for_audit", dash_py)
        if spec is None or spec.loader is None:
            return False
        dash = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dash)
        summary = res.get("summary", {}) or {}
        by_dim = summary.get("by_dim", {}) or {}
        event = dash.make_event(
            ep,
            "review",
            "consistency_findings",
            source="n2d-review/scripts/consistency_audit.py",
            meta={
                "findings_path": os.path.relpath(findings_path, root),
                "total_block": summary.get("total_block", 0),
                "total_warn": sum(int((c or {}).get("warn") or 0) for c in by_dim.values()),
                "finding_count": len(res.get("findings", [])),
            },
        )
        dash.replace_events(
            root,
            lambda e: (
                e.get("episode") == event["episode"]
                and e.get("event") == "consistency_findings"
                and e.get("source") == "n2d-review/scripts/consistency_audit.py"
            ),
            [event],
        )
        return True
    except Exception as exc:  # 事件流是旁路：失败留痕到 stderr，不影响审计与文件外发
        print(f"[consistency_audit][warn] dashboard 事件写入失败（忽略）：{exc}", file=sys.stderr)
        return False


def export_findings(root: str, ep: str, res: dict) -> str:
    """聚合一致性检出 → 生产数据/consistency_findings_<集>.json + dashboard 事件（不改既有报告产物）。"""
    path = os.path.join(production_dir(root), f"consistency_findings_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(findings_payload(res), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _append_dashboard_event(root, ep, res, path)
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-export", action="store_true",
                    help="只审计不外发（默认会写 生产数据/consistency_findings_<集>.json 并登记 dashboard 事件）")
    ns = ap.parse_args(argv)
    res = run(ns.root.rstrip("/"), ns.episode)
    if not ns.no_export and os.path.isdir(ns.root):
        export_findings(ns.root.rstrip("/"), ns.episode, res)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 一致性编排审计（O1·一键全跑）：{ns.root} {ns.episode} ===\n")
    by = res["summary"]["by_dim"]
    print(f"{'维度':<16} 🔴  🟡  ✅  状态")
    for dim, c in by.items():
        st = "（缺库跳过·人判兜）" if c["skipped"] else (f"评 {c['n']}" if c["n"] else "无可评项")
        print(f"{dim:<16} {c['block']:<3} {c['warn']:<3} {c['ok']:<3} {st}")
    print(f"\n合计 🔴 {res['summary']['total_block']}（任一 🔴 即需回源头重出）")
    for dim, sec in res["sections"].items():
        for n in sec.get("notes", []):
            print(f"  · {dim}: {n}")
        for detail in sec.get("details", [])[:3]:
            if detail.get("verdict") in ("block", "warn"):
                print(f"  · {dim}: {detail.get('verdict')} {detail.get('message', '')}")
    if res.get("auto_return_tasks"):
        print("\n自动回流建议：")
        for task in res["auto_return_tasks"]:
            print(f"  · {task['return_to_stage']}: {'、'.join(task['dimensions'])}；{task['scope']}")
    return 1 if res["summary"]["total_block"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
