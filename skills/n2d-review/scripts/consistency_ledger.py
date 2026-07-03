#!/usr/bin/env python3
"""验收总账（E3）—— n2d 最终验收的单一交付面。

为什么存在（让 agent 跑得更顺）：一致性信号现在散在多个交付面——剧情继承、角色/资产、
镜头和运动、音频、字幕、合规、生产配方、score、review-ui、gate findings。验收时不应再让
审片人同时盯多份 JSON。本脚本只读既有产物，把两层视角收成一份
`consistency_ledger_第N集.{json,md}`：

1. 角色/资产三态表：事前 prevent · 落档 detect · 契约 contract。
2. 交付域验收表：剧情、角色、资产、镜头、音频、字幕、合规、生产操作。

`counts.block/high` 是最终验收硬阻断；review-ui 和 `run.py next` 均以这份总账作为统一交付面。

用法：python3 consistency_ledger.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
try:
    from n2d_contract import CONSISTENCY_LEDGER_KIND, consistency_dimensions  # noqa: E402
except Exception:  # pragma: no cover - standalone degraded fallback
    CONSISTENCY_LEDGER_KIND = "n2d_consistency_ledger"
    def consistency_dimensions() -> Dict[str, Dict[str, Any]]:  # type: ignore[override]
        return {}

# ---------- 纯逻辑（无 I/O · pytest 覆盖） ----------

# 统一严重度阶（drift band 与 finding severity 混排取最差）
SEV_RANK = {
    "pass": 0,
    "ok": 0,
    "info": 1,
    "low": 1,
    "medium": 2,
    "warn": 2,
    "insufficient_data": 2,
    "high": 3,
    "fail": 4,
    "block": 4,
}
SEV_ICON = {"ok": "🟢", "info": "🟢", "low": "🟢", "medium": "🟡", "warn": "🟡", "high": "🔴", "block": "⛔"}

DELIVERY_DOMAINS = (
    ("story", "剧情"),
    ("character", "角色"),
    ("asset", "资产"),
    ("shot", "镜头"),
    ("audio", "音频"),
    ("subtitle", "字幕"),
    ("compliance", "合规"),
    ("ops", "生产操作"),
)

DIMENSION_DOMAIN = {
    "semantic_continuity": "story",
    "state_continuity": "story",
    "rhythm_density": "story",
    "character_consistency": "character",
    "outfit_consistency": "character",
    "voice_consistency": "audio",
    "scene_consistency": "shot",
    "style_consistency": "shot",
    "multimodal_continuity": "shot",
    "interaction_continuity": "shot",
    "delivery_packaging_consistency": "shot",
    "contract_inheritance": "asset",
    "ui_hud_consistency": "asset",
    "subtitle_correctness": "subtitle",
    "text_render_consistency": "subtitle",
    "audio_visual_sync": "audio",
    "leitmotif_consistency": "audio",
    "production_ops_consistency": "ops",
    "retention_trend": "story",
}

DOMAIN_HINTS = (
    ("compliance", ("合规", "授权", "版权", "rights", "voice clone", "cameo", "localization", "备案", "ai_label")),
    ("subtitle", ("字幕", "srt", "ocr", "译名", "翻译", "subtitle", "caption", "text_render", "文字渲染")),
    ("audio", ("音频", "配音", "音画", "口型", "声纹", "bgm", "环境声", "leitmotif", "audio", "voice", "lipsync")),
    ("character", ("角色", "脸", "发型", "服装", "音色", "身份", "character", "face", "outfit", "identity")),
    ("asset", ("资产", "道具", "物件", "持有", "系统面板", "hud", "ui", "prop", "asset", "contract")),
    ("shot", ("镜头", "场景", "构图", "运动", "相机", "成片", "包装", "motion", "camera", "scene", "video")),
    ("story", ("剧情", "语义", "状态", "节奏", "伏笔", "story", "semantic", "state", "rhythm", "留存趋势", "retention_trend")),
)


def worse(a: str, b: str) -> str:
    """取较差的严重度（纯函数·可测）。未知值按 0 处理。"""
    return a if SEV_RANK.get(a, 0) >= SEV_RANK.get(b, 0) else b


def band_to_sev(band: Optional[str]) -> str:
    """drift_risk band → ledger severity.

    face_drift_risk / asset_drift_risk 的 high/medium 是事前预测预案：
    gate 侧已约定 high→WARN、measured/predicted block 才是真阻断。ledger 作为最终
    验收面不能把已通过落档 QC 的预测 high 永久升成 hard high。
    """
    b = str(band or "").strip().lower()
    if b == "block":
        return "block"
    if b in ("high", "medium", "warn"):
        return "medium"
    return "ok"


def normalize_sev(sev: Any) -> str:
    s = str(sev or "ok").strip().lower()
    return {
        "🔴": "block",
        "🟡": "warn",
        "🟢": "info",
        "error": "block",
        "failed": "block",
        "fail": "block",
        "warning": "warn",
        "needs_review": "warn",
        "insufficient": "medium",
        "insufficient_data": "medium",
        "pass": "ok",
        "passed": "ok",
    }.get(s, s if s in SEV_RANK else "info")


def severity_counts(items: Sequence[Dict[str, Any]], key: str = "overall") -> Dict[str, int]:
    counts = {"block": 0, "high": 0, "medium": 0}
    for item in items:
        sev = normalize_sev(item.get(key))
        if sev == "block":
            counts["block"] += 1
        elif sev == "high":
            counts["high"] += 1
        elif sev in {"medium", "warn"}:
            counts["medium"] += 1
    return counts


def merge_counts(*parts: Dict[str, int]) -> Dict[str, int]:
    return {k: sum(int(part.get(k, 0)) for part in parts) for k in ("block", "high", "medium")}


def _compact_report(report: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(report, Mapping):
        return {"available": False}
    counts = report.get("counts") if isinstance(report.get("counts"), Mapping) else {}
    return {
        "available": True,
        "kind": report.get("kind"),
        "status": report.get("status") or "pass",
        "counts": dict(counts),
        "path": report.get("path") or report.get("manifest_path") or "",
    }


def _compact_graph(graph: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(graph, Mapping):
        return {"available": False}
    summary = graph.get("summary") if isinstance(graph.get("summary"), Mapping) else {}
    return {
        "available": True,
        "kind": graph.get("kind"),
        "path": graph.get("path") or "",
        "summary": dict(summary),
        "impact_plan": graph.get("impact_plan") or {},
    }


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


def _dimension_domain_map() -> Dict[str, str]:
    out = dict(DIMENSION_DOMAIN)
    for key in consistency_dimensions().keys():
        out.setdefault(str(key), "ops")
    return out


def _domain_for_signal(signal: Dict[str, Any]) -> str:
    dim_key = str(signal.get("dim_key") or signal.get("dimension_key") or "").strip()
    dim = str(signal.get("dimension") or signal.get("dim") or "").strip()
    mapping = _dimension_domain_map()
    if dim_key in mapping:
        return mapping[dim_key]
    if dim in mapping:
        return mapping[dim]
    hay = " ".join(str(signal.get(k, "")) for k in ("dim", "dimension", "text", "message", "msg", "loc")).lower()
    for domain, hints in DOMAIN_HINTS:
        if any(h.lower() in hay for h in hints):
            return domain
    return "ops"


def build_delivery_domains(signals: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    domains: Dict[str, Dict[str, Any]] = {
        key: {
            "key": key,
            "label": label,
            "overall": "ok",
            "counts": {"block": 0, "high": 0, "medium": 0},
            "findings": [],
            "sources": [],
        }
        for key, label in DELIVERY_DOMAINS
    }
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        sev = normalize_sev(signal.get("sev") or signal.get("severity") or signal.get("status"))
        domain = domains.get(_domain_for_signal(signal)) or domains["ops"]
        domain["overall"] = worse(str(domain["overall"]), sev)
        if sev == "block":
            domain["counts"]["block"] += 1
        elif sev == "high":
            domain["counts"]["high"] += 1
        elif sev in {"medium", "warn"}:
            domain["counts"]["medium"] += 1
        source = str(signal.get("source") or "unknown").strip() or "unknown"
        if source not in domain["sources"]:
            domain["sources"].append(source)
        if SEV_RANK.get(sev, 0) >= 2 and len(domain["findings"]) < 8:
            text = str(signal.get("text") or signal.get("message") or signal.get("msg") or "")
            dim = str(signal.get("dimension") or signal.get("dim") or signal.get("dim_key") or "")
            loc = str(signal.get("loc") or "")
            domain["findings"].append({
                "severity": sev,
                "dimension": dim,
                "loc": loc,
                "message": text[:180],
                "source": source,
            })
    return list(domains.values())


ENTITY_ID_RE = re.compile(r"\b(?:CHAR|LOC|PROP|WEAPON|OUTFIT|VFX)_\d{2,}\b")
ENTITY_DOMAIN = {
    "CHAR": "character",
    "LOC": "shot",
    "PROP": "asset",
    "WEAPON": "asset",
    "OUTFIT": "character",
    "VFX": "asset",
}


def _root_cause_anchor(signal: Dict[str, Any]) -> str:
    text = " ".join(str(signal.get(k, "")) for k in ("loc", "text", "message", "msg", "dimension", "dim"))
    m = ENTITY_ID_RE.search(text)
    if m:
        return m.group(0)
    loc = str(signal.get("loc") or "").strip()
    if loc:
        base = os.path.basename(loc)
        return base or loc
    return _domain_for_signal(signal)


def _domain_for_root_cause(signal: Dict[str, Any], anchor: str) -> str:
    prefix = str(anchor or "").split("_", 1)[0]
    if prefix in ENTITY_DOMAIN:
        return ENTITY_DOMAIN[prefix]
    return _domain_for_signal(signal)


def build_root_causes(signals: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group noisy multi-dimension findings into likely root-cause buckets.

    This does not suppress any raw finding. It adds an acceptance view so one bad
    first frame does not appear as unrelated face/style/VLM/seam repair requests.
    """
    buckets: Dict[tuple, Dict[str, Any]] = {}
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        sev = normalize_sev(signal.get("sev") or signal.get("severity") or signal.get("status"))
        if SEV_RANK.get(sev, 0) < 2:
            continue
        anchor = _root_cause_anchor(signal)
        domain = _domain_for_root_cause(signal, anchor)
        key = (domain, anchor)
        bucket = buckets.setdefault(key, {
            "domain": domain,
            "anchor": anchor,
            "severity": "ok",
            "dimensions": [],
            "sources": [],
            "symptoms": [],
            "suggested_return_to_stage": signal.get("return_to_stage") or "",
        })
        bucket["severity"] = worse(str(bucket["severity"]), sev)
        dim = str(signal.get("dimension") or signal.get("dim") or signal.get("dim_key") or "").strip()
        if dim and dim not in bucket["dimensions"]:
            bucket["dimensions"].append(dim)
        src = str(signal.get("source") or "unknown").strip() or "unknown"
        if src not in bucket["sources"]:
            bucket["sources"].append(src)
        if not bucket.get("suggested_return_to_stage") and signal.get("return_to_stage"):
            bucket["suggested_return_to_stage"] = signal.get("return_to_stage")
        if len(bucket["symptoms"]) < 8:
            msg = str(signal.get("text") or signal.get("message") or signal.get("msg") or "")
            bucket["symptoms"].append({
                "severity": sev,
                "dimension": dim,
                "loc": signal.get("loc", ""),
                "message": msg[:180],
                "source": src,
            })
    out = list(buckets.values())
    out.sort(key=lambda row: (-SEV_RANK.get(normalize_sev(row.get("severity")), 0), str(row.get("domain")), str(row.get("anchor"))))
    return out


def build_ledger(*, characters: List[Dict[str, Any]], assets: List[Dict[str, Any]],
                 face_drift: Dict[str, str], asset_drift: Dict[str, str],
                 findings: Sequence[Dict[str, Any]],
                 delivery_signals: Optional[Sequence[Dict[str, Any]]] = None,
                 dependency_graph: Optional[Mapping[str, Any]] = None,
                 discontinuity_audit: Optional[Mapping[str, Any]] = None,
                 supplemental_reports: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
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
        overall = normalize_sev(worse(worse(prevent, detect), contract))
        out_rows.append({
            "id": r["id"], "name": r.get("name", ""), "kind": r["kind"],
            "prevent": prevent, "detect": detect, "contract": contract,
            "overall": overall, "hits": st["hits"],
        })
    out_rows.sort(key=lambda x: -SEV_RANK.get(x["overall"], 0))
    domains = build_delivery_domains(delivery_signals if delivery_signals is not None else findings)
    root_causes = build_root_causes(delivery_signals if delivery_signals is not None else findings)
    entity_counts = severity_counts(out_rows)
    domain_counts = severity_counts(domains)
    counts = merge_counts(entity_counts, domain_counts)
    delivery_status = "blocked" if counts.get("block", 0) or counts.get("high", 0) else "pass"
    return {
        "kind": CONSISTENCY_LEDGER_KIND, "version": 1,
        "rows": out_rows, "domains": domains, "root_causes": root_causes, "counts": counts,
        "entity_counts": entity_counts,
        "domain_counts": domain_counts,
        "delivery_surface": {
            "status": delivery_status,
            "blocking_counts": {"block": counts.get("block", 0), "high": counts.get("high", 0)},
            "required_domains": [label for _, label in DELIVERY_DOMAINS],
        },
        "dependency_graph": _compact_graph(dependency_graph),
        "intentional_discontinuity": _compact_report(discontinuity_audit),
        "supplemental_reports": {
            str(k): _compact_report(v) for k, v in (supplemental_reports or {}).items()
        },
        "unattributed": attr.get("_unattributed", []),
    }


def render_markdown(ledger: Dict[str, Any], ep: str) -> str:
    c = ledger.get("counts", {})
    surface = ledger.get("delivery_surface") or {}
    status = surface.get("status") or ("blocked" if c.get("block") or c.get("high") else "pass")
    lines = [
        f"# 验收总账 · {ep}",
        "",
        f"- 验收状态：{'阻断' if status == 'blocked' else '通过'}",
        f"- ⛔ block {c.get('block',0)} · 🔴 high {c.get('high',0)} · 🟡 medium {c.get('medium',0)}",
        "",
        "## 交付域闭环",
        "",
        "| 交付域 | 综合 | block | high | medium | 证据源 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for d in ledger.get("domains", []):
        counts = d.get("counts") or {}
        src = ", ".join(d.get("sources") or []) or "—"
        lines.append(
            f"| {d.get('label')} | {SEV_ICON.get(normalize_sev(d.get('overall')), '🟢')} {normalize_sev(d.get('overall'))} "
            f"| {counts.get('block', 0)} | {counts.get('high', 0)} | {counts.get('medium', 0)} | {src} |"
        )
    for d in ledger.get("domains", []):
        findings = d.get("findings") or []
        if not findings:
            continue
        lines.extend(["", f"### {d.get('label')}问题"])
        for f in findings:
            loc = f" @ {f.get('loc')}" if f.get("loc") else ""
            lines.append(f"- {f.get('severity')} [{f.get('source')}] {f.get('dimension')}{loc}: {f.get('message')}")
    if ledger.get("root_causes"):
        lines.extend(["", "## 根因聚合", ""])
        for row in ledger["root_causes"][:12]:
            dims = " / ".join(row.get("dimensions") or []) or "未标维度"
            ret = f" → 回 {row.get('suggested_return_to_stage')}" if row.get("suggested_return_to_stage") else ""
            lines.append(f"- {normalize_sev(row.get('severity'))} · {row.get('domain')}:{row.get('anchor')} · {dims}{ret}")
            for symptom in (row.get("symptoms") or [])[:3]:
                loc = f" @ {symptom.get('loc')}" if symptom.get("loc") else ""
                lines.append(f"  - {symptom.get('severity')} [{symptom.get('source')}] {symptom.get('dimension')}{loc}: {symptom.get('message')}")
    graph = ledger.get("dependency_graph") if isinstance(ledger.get("dependency_graph"), dict) else {}
    if graph.get("available"):
        summary = graph.get("summary") or {}
        lines.extend([
            "",
            "## 依赖传播",
            "",
            f"- nodes={summary.get('nodes', 0)} · edges={summary.get('edges', 0)} · clips={summary.get('clips', 0)} · images={summary.get('images', 0)} · videos={summary.get('videos', 0)}",
        ])
        if graph.get("path"):
            lines.append(f"- graph: `{graph.get('path')}`")
    dis = ledger.get("intentional_discontinuity") if isinstance(ledger.get("intentional_discontinuity"), dict) else {}
    if dis.get("available"):
        counts = dis.get("counts") or {}
        lines.extend([
            "",
            "## 合法不连续签收",
            "",
            f"- status={dis.get('status')} · accepted={counts.get('accepted', 0)} · block={counts.get('block', 0)} · warn={counts.get('warn', 0)}",
        ])
    supplemental = ledger.get("supplemental_reports") if isinstance(ledger.get("supplemental_reports"), dict) else {}
    if supplemental:
        lines.extend(["", "## 补充一致性合约", ""])
        for name, report in supplemental.items():
            counts = report.get("counts") or {}
            lines.append(
                f"- {name}: status={report.get('status')} · "
                f"block={counts.get('block', 0)} · warn={counts.get('warn', counts.get('medium', 0))}"
            )
    lines.extend([
        "",
        "## 角色/资产一致性画像",
        "",
        "- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)",
        "",
        "| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |",
        "|---|---|---|---|---|---|",
    ])
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
    lines.append("说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。")
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
        text = " ".join(str(f.get(k, "")) for k in ("char", "dimension", "dim", "note", "message", "msg"))
        out.append({
            "sev": sev,
            "severity": sev,
            "source": "detect",
            "dim_key": f.get("dim_key"),
            "dimension": f.get("dimension") or f.get("dim"),
            "loc": f.get("loc"),
            "text": text,
        })
    # detect：image_qc 完整 gate findings（复用 image_qc.to_findings，避免只读 lint 漏掉像素/语义/道具复核）
    iq = _load(os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")) or {}
    if isinstance(iq, dict) and iq:
        for f in _image_qc_to_findings(iq):
            text = " ".join(str(f.get(k, "")) for k in ("dim", "dimension", "loc", "msg", "message"))
            out.append({
                "sev": str(f.get("sev") or f.get("severity") or "warn"),
                "severity": str(f.get("sev") or f.get("severity") or "warn"),
                "source": "detect",
                "dim_key": f.get("dim_key"),
                "dimension": f.get("dimension") or f.get("dim"),
                "loc": f.get("loc"),
                "text": text,
            })
    # contract：契约继承 identity/asset handoff findings
    ci = _load(os.path.join(root, "生产数据", f"contract_inheritance_{ep}.json")) or {}
    for bucket in ("identity_handoff", "asset_handoff"):
        for f in ((ci.get(bucket) or {}).get("findings") or []):
            text = " ".join(str(f.get(k, "")) for k in ("clip_id", "code", "note"))
            out.append({
                "sev": str(f.get("severity") or "warn"),
                "severity": str(f.get("severity") or "warn"),
                "source": "contract",
                "dim_key": "contract_inheritance",
                "dimension": "视觉契约继承",
                "loc": f.get("clip_id"),
                "text": text,
            })
    return out


def _payload_findings(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("findings") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    return [r for r in rows if isinstance(r, dict)]


def _signals_from_findings_payload(payload: Any, source: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in _payload_findings(payload):
        sev = str(f.get("severity") or f.get("sev") or f.get("verdict") or "info")
        msg = str(f.get("message") or f.get("msg") or f.get("reason") or "")
        dim = f.get("dimension") or f.get("dim")
        out.append({
            "sev": sev,
            "severity": sev,
            "source": source,
            "dim_key": f.get("dim_key"),
            "dimension": dim,
            "loc": f.get("loc"),
            "text": " ".join(str(x or "") for x in (dim, msg)).strip(),
            "message": msg,
        })
    return out


def _is_self_ledger_signal(signal: Mapping[str, Any], ep: str) -> bool:
    """Whether a review finding is only the previous ledger gate result.

    review gate writes `gate_findings_review_<ep>.json`. If the previous run
    failed because `consistency_ledger_<ep>.json` was not clear, blindly reading
    that file while rebuilding the same ledger creates a self-referential block
    that survives after the real upstream causes are fixed.
    """
    dim = str(signal.get("dimension") or signal.get("dim") or signal.get("dim_key") or "")
    loc = str(signal.get("loc") or "")
    text = " ".join(str(signal.get(k) or "") for k in ("text", "message", "msg"))
    return (
        "验收总账" in dim
        and f"consistency_ledger_{ep}.json" in (loc + " " + text)
    )


def _score_status_severity(status: str) -> str:
    s = str(status or "").strip().lower()
    if s == "pass":
        return "ok"
    if s == "fail":
        return "block"
    if s in {"warn", "warning", "insufficient_data"}:
        return "medium"
    return "medium"


def _score_dimension_severity(item: Dict[str, Any], threshold: int) -> str:
    status = str(item.get("status") or "").strip().lower()
    if int(item.get("blocks") or 0) > 0 or status == "fail":
        return "block"
    if status == "insufficient_data":
        return "warn"
    if int(item.get("warnings") or 0) > 0 or status == "warn":
        return "warn"
    try:
        if int(item.get("score") or 0) < threshold:
            return "warn"
    except Exception:
        pass
    return "ok"


def collect_delivery_signals(root: str, ep: str, base_findings: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gather every acceptance-facing signal into the ledger domain surface."""
    out: List[Dict[str, Any]] = [dict(f) for f in base_findings]
    prod = os.path.join(root, "生产数据")

    for path in sorted(glob.glob(os.path.join(prod, f"gate_findings_*_{ep}.json"))):
        stage = os.path.basename(path).replace(f"_{ep}.json", "").replace("gate_findings_", "")
        stage_signals = _signals_from_findings_payload(_load(path), f"gate:{stage}")
        if stage == "review":
            stage_signals = [s for s in stage_signals if not _is_self_ledger_signal(s, ep)]
        out.extend(stage_signals)

    out.extend(_signals_from_findings_payload(_load(os.path.join(prod, f"review_ui_findings_{ep}.json")), "review-ui"))

    score = _load(os.path.join(prod, f"score_{ep}.json")) or {}
    if isinstance(score, dict) and score:
        threshold = int(score.get("threshold") or 85)
        status = str(score.get("status") or "")
        out.append({
            "sev": _score_status_severity(status),
            "severity": _score_status_severity(status),
            "source": "score",
            "dim_key": "production_ops_consistency",
            "dimension": "自动审片总分",
            "loc": os.path.join("生产数据", f"score_{ep}.json"),
            "text": f"score status={status or 'unknown'} total={score.get('total_score')} threshold={threshold}",
            "message": f"score status={status or 'unknown'} total={score.get('total_score')} threshold={threshold}",
        })
        for item in score.get("dimensions") or []:
            if not isinstance(item, dict):
                continue
            sev = _score_dimension_severity(item, threshold)
            out.append({
                "sev": sev,
                "severity": sev,
                "source": "score",
                "dim_key": item.get("key"),
                "dimension": item.get("label") or item.get("key"),
                "loc": os.path.join("生产数据", f"score_{ep}.json"),
                "text": (
                    f"{item.get('label') or item.get('key')}: status={item.get('status')} "
                    f"score={item.get('score')} block={item.get('blocks')} warn={item.get('warnings')}"
                ),
                "message": str((item.get("evidence") or [""])[0] if isinstance(item.get("evidence"), list) else ""),
            })
    else:
        out.append({
            "sev": "block",
            "severity": "block",
            "source": "score",
            "dim_key": "production_ops_consistency",
            "dimension": "自动审片总分",
            "loc": os.path.join("生产数据", f"score_{ep}.json"),
            "text": "缺 score JSON；验收总账无法闭环",
            "message": "缺 score JSON；验收总账无法闭环",
        })

    compliance_path = os.path.join(root, "合规", "compliance_manifest.json")
    if os.path.isfile(compliance_path):
        out.append({
            "sev": "ok",
            "severity": "ok",
            "source": "compliance",
            "dim_key": "compliance",
            "dimension": "合规",
            "loc": os.path.join("合规", "compliance_manifest.json"),
            "text": "compliance_manifest exists",
        })
    else:
        out.append({
            "sev": "block",
            "severity": "block",
            "source": "compliance",
            "dim_key": "compliance",
            "dimension": "合规",
            "loc": os.path.join("合规", "compliance_manifest.json"),
            "text": "缺 compliance_manifest.json；review 交付边界不能验收",
            "message": "缺 compliance_manifest.json；review 交付边界不能验收",
        })
    return out


def _local_script_module(name: str) -> Optional[Any]:
    path = os.path.join(os.path.dirname(__file__), f"{name}.py")
    try:
        spec = importlib.util.spec_from_file_location(f"n2d_review_{name}", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _signals_from_report(report: Mapping[str, Any], source: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for finding in report.get("findings") or []:
        if not isinstance(finding, Mapping):
            continue
        sev = str(finding.get("severity") or finding.get("sev") or "warn")
        dim = finding.get("dimension") or finding.get("dim") or "production_ops_consistency"
        msg = str(finding.get("message") or finding.get("msg") or finding.get("text") or "")
        out.append({
            "sev": sev,
            "severity": sev,
            "source": source,
            "dim_key": finding.get("dim_key") or "production_ops_consistency",
            "dimension": dim,
            "loc": finding.get("loc"),
            "text": " ".join(str(x or "") for x in (dim, msg)).strip(),
            "message": msg,
        })
    return out


def _write_dependency_graph(root: str, ep: str) -> Optional[Dict[str, Any]]:
    module = _local_script_module("consistency_dependency_graph")
    if module is None:
        return None
    try:
        graph = module.build_graph(root, ep)
        path = module.write_graph(graph, root, ep)
        graph["path"] = str(path)
        return graph
    except Exception:
        return None


def _run_intentional_discontinuity(root: str, ep: str, findings: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    module = _local_script_module("intentional_discontinuity")
    if module is None:
        return {"kind": "n2d_intentional_discontinuity_audit", "status": "pass", "counts": {"block": 0, "warn": 0, "accepted": 0}, "findings": []}
    try:
        return module.run(root, ep, findings, write=True)
    except Exception as exc:
        return {
            "kind": "n2d_intentional_discontinuity_audit",
            "status": "blocked",
            "counts": {"block": 1, "warn": 0, "accepted": 0},
            "findings": [{"severity": "block", "message": f"intentional discontinuity audit failed: {exc}"}],
        }


def _run_supplemental_reports(root: str, ep: str) -> Dict[str, Dict[str, Any]]:
    reports: Dict[str, Dict[str, Any]] = {}
    for name in ("motion_grammar_consistency", "audio_space_consistency", "expression_state_consistency"):
        module = _local_script_module(name)
        if module is None:
            continue
        try:
            report = module.run(root, ep, write=True)
            if isinstance(report, dict):
                reports[name] = report
        except Exception as exc:
            reports[name] = {
                "kind": name,
                "status": "blocked",
                "counts": {"block": 1, "warn": 0},
                "findings": [{"severity": "block", "message": f"{name} failed: {exc}"}],
            }
    return reports


def _image_qc_to_findings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d-image", "scripts", "image_qc.py"))
    try:
        spec = importlib.util.spec_from_file_location("n2d_image_qc_for_ledger", script)
        if spec is None or spec.loader is None:
            raise RuntimeError("module spec unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        findings = module.to_findings(payload)
        return [f for f in findings if isinstance(f, dict)]
    except Exception:
        # Fallback for damaged local environments: lint-only is older behavior,
        # kept so ledger generation never blocks consistency_audit export.
        return [
            {"sev": str(f.get("level") or "warn"), "dim": "image_prompt_lint", "msg": str(f.get("msg") or "")}
            for f in ((payload.get("lint") or {}).get("findings") or [])
            if isinstance(f, dict)
        ]


def run(root: str, ep: str) -> Dict[str, Any]:
    chars, assets = _registry_entities(root)
    face_drift = _drift_band_map(_load(os.path.join(root, "生产数据", f"face_drift_risk_{ep}.json")), "characters")
    asset_drift = _drift_band_map(_load(os.path.join(root, "生产数据", f"asset_drift_risk_{ep}.json")), "assets")
    findings = collect_findings(root, ep)
    discontinuity_audit = _run_intentional_discontinuity(root, ep, findings)
    annotated = discontinuity_audit.get("annotated_findings") if isinstance(discontinuity_audit, Mapping) else None
    if isinstance(annotated, list):
        findings = [dict(f) for f in annotated if isinstance(f, Mapping)]
    delivery_signals = collect_delivery_signals(root, ep, findings)
    supplemental_reports = _run_supplemental_reports(root, ep)
    for name, report in supplemental_reports.items():
        delivery_signals.extend(_signals_from_report(report, name))
    delivery_signals.extend(_signals_from_report(discontinuity_audit, "intentional-discontinuity"))
    dependency_graph = _write_dependency_graph(root, ep)
    ledger = build_ledger(characters=chars, assets=assets, face_drift=face_drift,
                          asset_drift=asset_drift, findings=findings,
                          delivery_signals=delivery_signals,
                          dependency_graph=dependency_graph,
                          discontinuity_audit=discontinuity_audit,
                          supplemental_reports=supplemental_reports)
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
    status = (ledger.get("delivery_surface") or {}).get("status")
    print(f"=== 验收总账 {ns.episode}：{status} · ⛔{c['block']} · 🔴{c['high']} · 🟡{c['medium']}（共 {len(ledger['rows'])} 实体）===")
    for d in ledger.get("domains", []):
        if SEV_RANK.get(normalize_sev(d.get("overall")), 0) < 2:
            continue
        dc = d.get("counts") or {}
        print(f"{SEV_ICON.get(normalize_sev(d.get('overall')), '🟢')} {d.get('label')} "
              f"block{dc.get('block', 0)}·high{dc.get('high', 0)}·medium{dc.get('medium', 0)}")
    for r in ledger["rows"]:
        if SEV_RANK.get(r["overall"], 0) < 2:
            continue
        print(f"{SEV_ICON.get(r['overall'])} {r['name']}（{r['id']}/{r['kind']}）"
              f" 事前{r['prevent']}·落档{r['detect']}·契约{r['contract']}")
    print(f"→ {ledger['markdown_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
