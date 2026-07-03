#!/usr/bin/env python3
"""Creative experiment registry for n2d feedback."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


KIND = "n2d_creative_experiments"
EXPERIMENTS_JSON = "creative_experiments.json"
AUDIT_JSON = "creative_experiment_audit.json"
AUDIT_MD = "creative_experiment_audit.md"


def production_dir(root: str) -> Path:
    return Path(root) / "生产数据"


def experiments_path(root: str) -> Path:
    return production_dir(root) / EXPERIMENTS_JSON


def load_experiments(root: str) -> Dict[str, Any]:
    path = experiments_path(root)
    if not path.is_file():
        return {"kind": KIND, "version": 1, "experiments": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != KIND:
        raise ValueError(f"{path} is not {KIND}")
    data.setdefault("experiments", [])
    return data


def save_experiments(root: str, data: Dict[str, Any]) -> Path:
    path = experiments_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def parse_variant(items: Sequence[str]) -> List[Dict[str, str]]:
    out = []
    for item in items:
        if "=" not in str(item):
            raise ValueError(f"--variant expects id=description: {item}")
        key, value = str(item).split("=", 1)
        out.append({"variant_id": key.strip(), "description": value.strip()})
    return out


def upsert_experiment(
    root: str,
    experiment_id: str,
    *,
    episode: str,
    hypothesis: str,
    variants: Sequence[Dict[str, str]],
    primary_metric: str,
    min_samples: int,
    owner: str = "",
) -> Dict[str, Any]:
    data = load_experiments(root)
    exp = {
        "experiment_id": experiment_id,
        "episode": episode,
        "hypothesis": hypothesis,
        "variants": list(variants),
        "primary_metric": primary_metric,
        "min_samples": int(min_samples),
        "owner": owner,
        "status": "planned",
    }
    rows = [item for item in data.get("experiments") or [] if isinstance(item, dict) and item.get("experiment_id") != experiment_id]
    rows.append(exp)
    data["experiments"] = sorted(rows, key=lambda item: str(item.get("experiment_id")))
    return data


def read_metrics(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        if isinstance(data, dict):
            rows = data.get("rows") or data.get("records") or data.get("metrics")
            return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def audit_metrics(root: str, metrics_path: Path) -> Dict[str, Any]:
    data = load_experiments(root)
    experiments = {str(item.get("experiment_id")): item for item in data.get("experiments") or [] if isinstance(item, dict)}
    rows = read_metrics(metrics_path)
    ab_ids = sorted({str(row.get("ab_test_id") or "").strip() for row in rows if str(row.get("ab_test_id") or "").strip()})
    missing = [ab for ab in ab_ids if ab not in experiments]
    underpowered = []
    for exp_id, exp in experiments.items():
        variants = {str(v.get("variant_id")) for v in exp.get("variants") or [] if isinstance(v, dict)}
        matched = [row for row in rows if str(row.get("ab_test_id") or "") == exp_id]
        seen_variants = {str(row.get("variant_id") or "") for row in matched if str(row.get("variant_id") or "")}
        plays = sum(float(row.get("plays") or row.get("views") or 0) for row in matched)
        if variants and not variants <= seen_variants:
            underpowered.append({"experiment_id": exp_id, "issue": "missing_variant_metrics", "missing": sorted(variants - seen_variants)})
        if plays < int(exp.get("min_samples") or 0):
            underpowered.append({"experiment_id": exp_id, "issue": "below_min_samples", "plays": plays, "min_samples": exp.get("min_samples")})
    payload = {
        "kind": "n2d_creative_experiment_audit",
        "version": 1,
        "root": root,
        "metrics_path": str(metrics_path),
        "experiments": sorted(experiments),
        "ab_test_ids_in_metrics": ab_ids,
        "missing_experiment_definitions": missing,
        "underpowered": underpowered,
        "status": "fail" if missing else ("observe" if underpowered else "pass"),
    }
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d 投放实验审计",
        "",
        f"- 状态：{payload.get('status')}",
        f"- metrics A/B：{', '.join(payload.get('ab_test_ids_in_metrics') or []) or '—'}",
        "",
        "## 缺实验定义",
        "",
    ]
    lines.extend([f"- {item}" for item in payload.get("missing_experiment_definitions") or []] or ["- 无"])
    lines.extend(["", "## 样本/变体不足", ""])
    lines.extend([f"- {item}" for item in payload.get("underpowered") or []] or ["- 无"])
    lines.append("")
    return "\n".join(lines)


def write_audit(root: str, payload: Dict[str, Any]) -> None:
    pdir = production_dir(root)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / AUDIT_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (pdir / AUDIT_MD).write_text(render_markdown(payload), encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d creative experiment registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("upsert")
    p.add_argument("root")
    p.add_argument("--id", required=True)
    p.add_argument("--episode", required=True)
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--variant", action="append", required=True)
    p.add_argument("--primary-metric", default="retention_3s")
    p.add_argument("--min-samples", type=int, default=1000)
    p.add_argument("--owner", default="")
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("audit")
    p.add_argument("root")
    p.add_argument("--metrics", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "upsert":
        data = upsert_experiment(
            ns.root,
            ns.id,
            episode=ns.episode,
            hypothesis=ns.hypothesis,
            variants=parse_variant(ns.variant),
            primary_metric=ns.primary_metric,
            min_samples=ns.min_samples,
            owner=ns.owner,
        )
        if ns.write:
            path = save_experiments(ns.root, data)
            print(f"wrote {path}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    payload = audit_metrics(ns.root, Path(ns.metrics))
    if ns.write:
        write_audit(ns.root, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
