#!/usr/bin/env python3
"""一致性编排（O1）——一键串跑全部一致性检测器，出一张汇总分档报告。

2026 产线核心已从"单点能力"转到**编排层**：检测器再多，没被自动跑就等于没有。
本脚本把散落的检测器统一调起来，n2d-review 模式①工作流第 1 步「跑机检套件」即调它：

  语义谱系 P0 · 状态百科 P1 · 多模态 P2 · 锚点门 N3 · 脸 G1 · 服装/配色 N1 ·
  片内时序 N2 · 场景 O2 · 糊/低质 N4 · 风格 S1

每个子检测器各自缺库优雅跳过（见各脚本）；本编排只汇总、不重复实现。
纯函数 `summarize` 无依赖、带 pytest。

用法：python3 consistency_audit.py <作品根> 第N集 [--json]
退出码：有任一 🔴 → 1，否则 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import face_consistency as fc
import outfit_consistency as oc
import temporal_consistency as tcheck
import quality_check as qc
import scene_consistency as sc
import style_consistency as stc
import semantic_continuity as semc
import state_continuity as statec
import multimodal_consistency as mmc


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


def run(root: str, ep: str) -> dict:
    sections: Dict[str, dict] = {}

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

    # N3 锚点门（全篇定妆，不分集）
    a = fc.audit_anchors(root)
    sections["锚点门(N3)"] = {"skipped": not a.get("available", False),
                             "verdicts": _verdicts(a.get("anchors", [])), "notes": a.get("notes", [])}

    # G1 脸
    f = fc.analyze(root, ep)
    sections["脸(G1)"] = {"skipped": not f.get("available", False),
                         "verdicts": [s.get("verdict") for s in f.get("shots", []) if s.get("verdict") != "noface"],
                         "notes": f.get("notes", [])}

    # N1 服装/配色
    o = oc.analyze(root, ep)
    sections["服装配色(N1)"] = {"skipped": not o.get("available", False),
                              "verdicts": _verdicts(o.get("shots", [])), "notes": o.get("notes", [])}

    # N2 片内时序
    t = tcheck.analyze(root, ep)
    sections["片内时序(N2)"] = {"skipped": not t.get("clips", []) and bool(t.get("notes")),
                              "verdicts": [c.get("verdict") for c in t.get("clips", [])], "notes": t.get("notes", [])}

    # O2 场景
    s = sc.analyze(root, ep)
    sections["场景(O2)"] = {"skipped": not s.get("available", False),
                          "verdicts": _verdicts(s.get("shots", [])), "notes": s.get("notes", [])}

    # S1 风格漂移
    st = stc.analyze(root, ep)
    sections["风格(S1)"] = {"skipped": not st.get("available", False) or st.get("floor") is None,
                          "verdicts": _verdicts(st.get("shots", [])), "notes": st.get("notes", [])}

    # 接缝 接力(尾帧 vs 下一首帧)——PNG 层，把"逐接缝人判"降成机检初筛
    sm = tcheck.seam_analyze(root, ep)
    sections["接缝接力"] = {"skipped": bool(sm.get("notes")) and not sm.get("seams"),
                         "verdicts": _verdicts(sm.get("seams", [])), "notes": sm.get("notes", [])}

    # N4 糊/低质
    q = qc.analyze(root, ep)
    sections["糊/低质(N4)"] = {"skipped": not q.get("available", False),
                             "verdicts": _verdicts(q.get("shots", [])), "notes": q.get("notes", [])}

    summary = summarize(sections)
    return {
        "root": root,
        "episode": ep,
        "summary": summary,
        "sections": sections,
        "auto_return_tasks": build_auto_return_tasks(sections),
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = run(ns.root.rstrip("/"), ns.episode)
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
