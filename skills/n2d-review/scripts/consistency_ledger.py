#!/usr/bin/env python3
"""一致性总账（E3）—— 把散落各处的一致性信号按「角色 × 资产」滚成一张表。

为什么存在（让 agent 跑得更顺）：一致性信号现在散在 ≥4 处——出图前预案
（face/asset_drift_risk）、落档机检（image_qc / consistency_findings）、跨阶段契约
（contract_inheritance 的 identity/asset handoff）。agent / 审片人要同时盯好几个 JSON 才知道
"沈念这个角色到底稳不稳"。本脚本只读这些既有产物，按每个角色 / 每个资产滚成一行 **三态**
（事前 prevent · 落档 detect · 契约 contract）+ 综合档，落一张 `consistency_ledger_第N集.{json,md}`，
让 agent 和 review-ui 只读这一份就拿到全局一致性画像。**只读·不生产·不阻断**。

用法：python3 consistency_ledger.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

# ---------- 纯逻辑（无 I/O · pytest 覆盖） ----------

# 统一严重度阶（drift band 与 finding severity 混排取最差）
SEV_RANK = {"ok": 0, "info": 1, "low": 1, "medium": 2, "warn": 2, "high": 3, "block": 4}
SEV_ICON = {"ok": "🟢", "info": "🟢", "low": "🟢", "medium": "🟡", "warn": "🟡", "high": "🔴", "block": "⛔"}


def worse(a: str, b: str) -> str:
    """取较差的严重度（纯函数·可测）。未知值按 0 处理。"""
    return a if SEV_RANK.get(a, 0) >= SEV_RANK.get(b, 0) else b


def band_to_sev(band: Optional[str]) -> str:
    """drift_risk 的 high/medium/low → 统一严重度（high/medium/ok）。"""
    b = str(band or "").strip().lower()
    return b if b in ("high", "medium") else "ok"


def name_tokens(name: str) -> List[str]:
    """角色名「沈念 / 林婉儿」→ ['沈念','林婉儿']（别名拆分，供 finding 文本归属匹配）。"""
    raw = str(name or "")
    out: List[str] = []
    for part in raw.replace("／", "/").split("/"):
        t = part.strip()
        if len(t) >= 2:
            out.append(t)
    return out


def _matches(row: Dict[str, Any], text: str) -> bool:
    """finding 文本是否指向该行实体：id 命中，或任一名字别名命中。"""
    rid = str(row.get("id") or "")
    if rid and rid in text:
        return True
    return any(tok in text for tok in row.get("name_tokens", []))


def attribute(rows: List[Dict[str, Any]], findings: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """把规范化 findings 按文本归属到各行，分 detect / contract 两桶记最差severity + 命中样本。纯函数·可测。

    findings: [{sev, source('detect'|'contract'), text}]。无法归属到任何行的 finding 计入 _unattributed。"""
    state: Dict[str, Dict[str, Any]] = {
        r["id"]: {"detect": "ok", "contract": "ok", "hits": []} for r in rows
    }
    unattributed: List[str] = []
    for f in findings:
        text = str(f.get("text") or "")
        sev = str(f.get("sev") or "ok").lower()
        bucket = "contract" if f.get("source") == "contract" else "detect"
        matched = False
        for r in rows:
            if _matches(r, text):
                st = state[r["id"]]
                st[bucket] = worse(st[bucket], sev)
                if SEV_RANK.get(sev, 0) >= 2 and len(st["hits"]) < 3:
                    st["hits"].append(f"[{sev}] {text[:70]}")
                matched = True
        if not matched and SEV_RANK.get(sev, 0) >= 2:
            unattributed.append(f"[{sev}] {text[:70]}")
    state["_unattributed"] = unattributed  # type: ignore[assignment]
    return state


def build_ledger(*, characters: List[Dict[str, Any]], assets: List[Dict[str, Any]],
                 face_drift: Dict[str, str], asset_drift: Dict[str, str],
                 findings: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """三态总账（纯函数·可测）。每行：prevent(drift) / detect(落档) / contract(契约) / overall(最差)。"""
    rows: List[Dict[str, Any]] = []
    for c in characters:
        c = dict(c)
        c.setdefault("name_tokens", name_tokens(c.get("name", "")))
        c["kind"] = "character"
        rows.append(c)
    for a in assets:
        a = dict(a)
        a.setdefault("name_tokens", name_tokens(a.get("name", "")))
        a["kind"] = a.get("type") or "asset"
        rows.append(a)

    attr = attribute(rows, findings)
    out_rows: List[Dict[str, Any]] = []
    for r in rows:
        st = attr[r["id"]]
        prevent = band_to_sev((face_drift if r["kind"] == "character" else asset_drift).get(r["id"]))
        detect, contract = st["detect"], st["contract"]
        overall = worse(worse(prevent, detect), contract)
        out_rows.append({
            "id": r["id"], "name": r.get("name", ""), "kind": r["kind"],
            "prevent": prevent, "detect": detect, "contract": contract,
            "overall": overall, "hits": st["hits"],
        })
    order = {"⛔": 0}
    out_rows.sort(key=lambda x: -SEV_RANK.get(x["overall"], 0))
    counts = {k: sum(1 for r in out_rows if r["overall"] == k) for k in ("block", "high", "medium")}
    return {
        "kind": "n2d_consistency_ledger", "version": 1,
        "rows": out_rows, "counts": counts,
        "unattributed": attr.get("_unattributed", []),
    }


def render_markdown(ledger: Dict[str, Any], ep: str) -> str:
    c = ledger.get("counts", {})
    lines = [
        f"# 一致性总账 · {ep}（角色×资产 · 事前/落档/契约 三态）",
        "",
        f"- ⛔ block {c.get('block',0)} · 🔴 high {c.get('high',0)} · 🟡 medium {c.get('medium',0)}",
        "- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)",
        "",
        "| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |",
        "|---|---|---|---|---|---|",
    ]
    for r in ledger.get("rows", []):
        ic = SEV_ICON.get
        lines.append(f"| {r['name']}（{r['id']}） | {r['kind']} | {ic(r['overall'],'?')} {r['overall']} "
                     f"| {ic(r['prevent'],'?')} | {ic(r['detect'],'?')} | {ic(r['contract'],'?')} |")
    lines.append("")
    for r in ledger.get("rows", []):
        if SEV_RANK.get(r["overall"], 0) < 2 or not r.get("hits"):
            continue
        lines.append(f"## {SEV_ICON.get(r['overall'])} {r['name']}（{r['id']}）")
        for h in r["hits"]:
            lines.append(f"- {h}")
        lines.append("")
    if ledger.get("unattributed"):
        lines.append("## 未归属到具体角色/资产的一致性问题")
        for u in ledger["unattributed"][:8]:
            lines.append(f"- {u}")
        lines.append("")
    lines.append("说明：本表只读汇总，不阻断。综合档=事前/落档/契约三者取最差；要修先看落档(image_qc gate)与契约(inherit_contract)硬阻断。")
    return "\n".join(lines) + "\n"


# ---------- I/O：读既有产物 ----------

def _load(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _registry_entities(root: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    reg = _load(os.path.join(root, "出图", "共享", "identity_registry.json")) or {}
    chars = [{"id": str(c.get("id") or ""), "name": str(c.get("name") or "")}
             for c in (reg.get("characters") or []) if c.get("id")]
    areg = _load(os.path.join(root, "出图", "共享", "asset_registry.json")) or {}
    assets = [{"id": str(a.get("id") or ""), "name": str(a.get("name") or ""), "type": str(a.get("type") or "asset")}
              for a in (areg.get("assets") or []) if a.get("id")]
    return chars, assets


def _drift_band_map(report: Optional[Dict[str, Any]], key: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for r in (report or {}).get(key, []) or []:
        rid = str(r.get("character_id") or r.get("id") or "")
        if rid:
            out[rid] = str(r.get("band") or "low")
    return out


def collect_findings(root: str, ep: str) -> List[Dict[str, Any]]:
    """从既有产物汇规范化 findings：detect(一致性机检/image_qc lint) + contract(handoff)。"""
    out: List[Dict[str, Any]] = []
    # detect：一致性机检 findings
    cf = _load(os.path.join(root, "生产数据", f"consistency_findings_{ep}.json")) or {}
    for f in (cf.get("findings") or []):
        sev = str(f.get("severity") or f.get("verdict") or "ok")
        text = " ".join(str(f.get(k, "")) for k in ("char", "dimension", "note", "message", "msg"))
        out.append({"sev": sev, "source": "detect", "text": text})
    # detect：image_qc lint findings（msg 内含镜头/资产名）
    iq = _load(os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")) or {}
    for f in ((iq.get("lint") or {}).get("findings") or []):
        out.append({"sev": str(f.get("level") or "warn"), "source": "detect", "text": str(f.get("msg") or "")})
    # contract：契约继承 identity/asset handoff findings
    ci = _load(os.path.join(root, "生产数据", f"contract_inheritance_{ep}.json")) or {}
    for bucket in ("identity_handoff", "asset_handoff"):
        for f in ((ci.get(bucket) or {}).get("findings") or []):
            text = " ".join(str(f.get(k, "")) for k in ("clip_id", "code", "note"))
            out.append({"sev": str(f.get("severity") or "warn"), "source": "contract", "text": text})
    return out


def run(root: str, ep: str) -> Dict[str, Any]:
    chars, assets = _registry_entities(root)
    face_drift = _drift_band_map(_load(os.path.join(root, "生产数据", f"face_drift_risk_{ep}.json")), "characters")
    asset_drift = _drift_band_map(_load(os.path.join(root, "生产数据", f"asset_drift_risk_{ep}.json")), "assets")
    findings = collect_findings(root, ep)
    ledger = build_ledger(characters=chars, assets=assets, face_drift=face_drift,
                          asset_drift=asset_drift, findings=findings)
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"consistency_ledger_{ep}.json")
    md_path = os.path.join(out_dir, f"consistency_ledger_{ep}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(ledger, ep))
    ledger["json_path"], ledger["markdown_path"] = json_path, md_path
    return ledger


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    ledger = run(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    c = ledger["counts"]
    print(f"=== 一致性总账 {ns.episode}：⛔{c['block']} · 🔴{c['high']} · 🟡{c['medium']}（共 {len(ledger['rows'])} 实体）===")
    for r in ledger["rows"]:
        if SEV_RANK.get(r["overall"], 0) < 2:
            continue
        print(f"{SEV_ICON.get(r['overall'])} {r['name']}（{r['id']}/{r['kind']}）"
              f" 事前{r['prevent']}·落档{r['detect']}·契约{r['contract']}")
    print(f"→ {ledger['markdown_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
