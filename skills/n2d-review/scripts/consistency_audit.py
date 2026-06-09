#!/usr/bin/env python3
"""一致性编排（O1）——一键串跑全部一致性检测器，出一张汇总分档报告。

2026 产线核心已从"单点能力"转到**编排层**：检测器再多，没被自动跑就等于没有。
本脚本把散落的检测器统一调起来，n2d-review 模式①工作流第 1 步「跑机检套件」即调它：

  锚点门 N3 · 脸 G1 · 服装/配色 N1 · 片内时序 N2 · 场景 O2 · 糊/低质 N4 · 风格 S1

每个子检测器各自缺库优雅跳过（见各脚本）；本编排只汇总、不重复实现。
纯函数 `summarize` 无依赖、带 pytest。

用法：python3 consistency_audit.py <作品根> 第N集 [--json]
退出码：有任一 🔴 → 1，否则 0。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

import face_consistency as fc
import outfit_consistency as oc
import temporal_consistency as tcheck
import quality_check as qc
import scene_consistency as sc
import style_consistency as stc


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


def run(root: str, ep: str) -> dict:
    sections: Dict[str, dict] = {}

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
    return {"root": root, "episode": ep, "summary": summary, "sections": sections}


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
    return 1 if res["summary"]["total_block"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
