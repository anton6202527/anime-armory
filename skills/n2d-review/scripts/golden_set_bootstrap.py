#!/usr/bin/env python3
"""一致性地板 golden-set 自举（P1-4）。

掣肘：一致性机检的余弦地板 `consistency_threshold_registry` 默认 `threshold_floor=None`+
`human_review_required`——有 insightface 余弦机器，却没标定地板 → 维度长期停在 advisory 而非
机器硬卡。`calibrate_thresholds.py --calibrate` 早就会把金标集 `consistency_golden_set.jsonl`
反推成 per-(维度,后端,风格) floor 并刷进 registry——**但没人产那份金标集**（它要人工标 pass/fail）。

本脚本补上缺失的生产者：从**人审通过的集**（`_进度.md` 验收=✅）自举金标行，把链路接通：
  • PASS 锚 = 人审通过集里 face 机检的 worst_score（人说能发 = 该集最差的镜也过了人审 → 真 pass 下界）；
  • FAIL 锚 = **未通过**集里机检 block 的 worst_score（机检报崩 且 没发 → 确认负样本）。
  用「人审 accepted / not」当标签、机检余弦当特征 → 学的是**人审对齐**的 floor，非把机检自身的
  floor 再喂回去（非循环）。样本不足时 derive_floor 返回 insufficient_samples、registry 维持
  human_review——**绝不臆造阈值**。

数据源（只读已落盘产物，不出图不花钱）：
  • `_进度.md` 验收列 → 人审通过的集；
  • `生产数据/identity_drift_report.json`（n2d-identity 产）→ per-(角色,集) worst_score/block 计数。

用法：
  python3 golden_set_bootstrap.py <作品根> [--write] [--calibrate] [--json]
    --write      落 生产数据/consistency_golden_set.jsonl（与既有人工标注合并去重）
    --calibrate  落金标后链式跑 calibrate_thresholds --calibrate（产 calibration + 刷 registry）

测试：cd skills/n2d-review/scripts && python3 -m pytest test_golden_set_bootstrap.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

KIND = "n2d_consistency_golden_set"
FACE_DIM = "character_consistency"


# ── 纯函数（无 IO·可测）────────────────────────────────────────────────────────

def _row(dimension: str, backend: str, style: str, label: str, score: float,
         episode: str, character: str) -> Dict[str, Any]:
    return {
        "dimension": dimension,
        "backend": backend or "any",
        "style": style or "any",
        "label": label,                       # pass | fail
        "similarity": round(float(score), 6),  # calibrate_thresholds._agg_score 读 similarity
        "episode": episode,
        "character": character,
        "source": "golden_set_bootstrap",
    }


def golden_rows_from_drift(
    drift: Mapping[str, Any],
    accepted_eps: Sequence[str],
    *,
    backend: str = "any",
    style: str = "any",
    dimension: str = FACE_DIM,
) -> List[Dict[str, Any]]:
    """drift_report × 人审通过集 → 金标 pass/fail 行（character_consistency 维度）。纯函数。

    PASS = 通过集里有 worst_score 且 block==0 的 (角色,集)；
    FAIL = **未通过**集里 block>0 且有 worst_score 的 (角色,集)。
    通过集里仍 block>0 的镜（人审与机检相左：要么导演意图豁免、要么人审漏看）不当任何一类——
    既不污染 pass 也不当 fail，留人工去 consistency_calibration.jsonl 显式标。"""
    accepted = {str(e).strip() for e in accepted_eps if str(e).strip()}
    rows: List[Dict[str, Any]] = []
    chars = drift.get("characters") if isinstance(drift.get("characters"), Mapping) else {}
    for char, crec in sorted(chars.items()):
        if not isinstance(crec, Mapping):
            continue
        eps = crec.get("episodes") if isinstance(crec.get("episodes"), Mapping) else {}
        for ep, e in sorted(eps.items()):
            if not isinstance(e, Mapping):
                continue
            ws = e.get("worst_score")
            if not isinstance(ws, (int, float)):
                continue
            block = int(e.get("block") or 0)
            is_accepted = str(ep).strip() in accepted
            if is_accepted and block == 0:
                rows.append(_row(dimension, backend, style, "pass", ws, str(ep), str(char)))
            elif (not is_accepted) and block > 0:
                rows.append(_row(dimension, backend, style, "fail", ws, str(ep), str(char)))
    return rows


def _dedup_key(row: Mapping[str, Any]) -> tuple:
    return (
        str(row.get("dimension")), str(row.get("backend")), str(row.get("style")),
        str(row.get("label")), str(row.get("episode")), str(row.get("character")),
        round(float(row.get("similarity") or 0.0), 4),
    )


def merge_rows(existing: Sequence[Mapping[str, Any]], new: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """合并既有金标行（含人工标注）与本次自举行，按内容去重。保留既有在前（人工优先）。"""
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in list(existing) + list(new):
        if not isinstance(row, Mapping):
            continue
        k = _dedup_key(row)
        if k in seen:
            continue
        seen.add(k)
        out.append(dict(row))
    return out


def summarize(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_dim: Dict[str, Dict[str, int]] = {}
    for row in rows:
        dim = str(row.get("dimension") or "?")
        d = by_dim.setdefault(dim, {"pass": 0, "fail": 0})
        lbl = str(row.get("label") or "")
        if lbl in d:
            d[lbl] += 1
    return {"total": len(rows), "by_dimension": by_dim}


# ── IO ────────────────────────────────────────────────────────────────────────

def accepted_episodes(root: str) -> List[str]:
    """读 `_进度.md` 验收列=✅ 的集（人审通过）。缺文件/无验收列 → []。"""
    try:
        from n2d_route import parse_progress, cell_state
    except Exception:
        return []
    try:
        header, prog_rows = parse_progress(root)
    except Exception:
        return []
    if "验收" not in header:
        return []
    out: List[str] = []
    for r in prog_rows:
        if cell_state(r.get("验收", "")) == "done":
            ep = r.get("_ep") or r.get("集") or ""
            if ep:
                out.append(str(ep).strip())
    return out


def _backend_style(root: str) -> tuple:
    """从 _设置.md 取生图后端作 backend 维度键；style 暂统一 any（风格分桶留待显式标注）。"""
    backend = "any"
    try:
        from settings import load_settings
        s = load_settings(root)
        raw = s.get("生图模型") or s.get("生图AI") or ""
        backend = str(raw).strip().split("（")[0].split("(")[0].strip() or "any"
    except Exception:
        backend = "any"
    return backend, "any"


def _read_drift(root: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(root, "生产数据", "identity_drift_report.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _golden_path(root: str) -> str:
    for rel in ("生产数据/consistency_golden_set.jsonl", "设定库/consistency_golden_set.jsonl"):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            return p
    return os.path.join(root, "生产数据", "consistency_golden_set.jsonl")


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except FileNotFoundError:
        pass
    return rows


def build(root: str) -> Dict[str, Any]:
    """组装：drift × 验收 → 自举行；与既有金标合并。返回报告（不落盘）。"""
    root = root.rstrip("/")
    accepted = accepted_episodes(root)
    drift = _read_drift(root)
    backend, style = _backend_style(root)
    notes: List[str] = []
    new_rows: List[Dict[str, Any]] = []
    if not accepted:
        notes.append("无人审通过的集（_进度.md 验收列无 ✅）——地板维持 human_review，不自举、不臆造。")
    if drift is None:
        notes.append("缺 生产数据/identity_drift_report.json——先跑 n2d-identity 出跨集漂移报表再自举。")
    if accepted and drift is not None:
        new_rows = golden_rows_from_drift(drift, accepted, backend=backend, style=style)
        if not new_rows:
            notes.append("通过集里无可用 worst_score / 无未通过集的 block 负样本——金标暂不可自举。")
    existing = _read_jsonl(_golden_path(root))
    merged = merge_rows(existing, new_rows)
    return {
        "kind": KIND, "version": 1, "root": root,
        "accepted_episodes": accepted, "backend": backend, "style": style,
        "new_rows": new_rows, "existing_n": len(existing),
        "rows": merged, "summary": summarize(merged), "notes": notes,
    }


def write_golden_set(root: str, rows: Sequence[Mapping[str, Any]]) -> str:
    path = _golden_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + f".tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    return path


def _chain_calibrate(root: str) -> List[str]:
    """落金标后链式跑 calibrate_thresholds --calibrate --write --registry。返回产物路径。"""
    out: List[str] = []
    try:
        import calibrate_thresholds as ct
        out.append(ct.write_calibration(root))
        reg = ct.write_registry_if_available(root)
        if reg:
            out.append(reg)
    except Exception as exc:  # pragma: no cover - 防御
        out.append(f"(calibrate 链式失败：{exc})")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="一致性地板 golden-set 自举（人审通过集 → 金标 → 标定）")
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help="落 consistency_golden_set.jsonl（合并去重）")
    ap.add_argument("--calibrate", action="store_true", help="落金标后链式刷 calibration + registry")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    report = build(ns.root)
    if ns.write and report["rows"]:
        report["golden_set_path"] = write_golden_set(ns.root, report["rows"])
        if ns.calibrate:
            report["calibration_outputs"] = _chain_calibrate(ns.root)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        s = report["summary"]
        print(f"人审通过集: {len(report['accepted_episodes'])} · 自举新增: {len(report['new_rows'])} · "
              f"金标合计: {s['total']}（{s['by_dimension']}）")
        for n in report["notes"]:
            print(f"  · {n}")
        for k in ("golden_set_path",):
            if report.get(k):
                print(f"  → {report[k]}")
        for p in report.get("calibration_outputs", []):
            print(f"  → {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
