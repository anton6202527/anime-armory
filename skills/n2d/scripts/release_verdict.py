#!/usr/bin/env python3
"""Unified n2d release verdict.

Aggregates gate, score, consistency ledger, review-ui, image_qc freshness,
generation recipe evidence, progress DAG, pilot signoff and compliance into one
pass / blocked / demo-only / internal-only decision.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
N2D_DIR = SCRIPT_DIR.parents[0]
LIB = N2D_DIR / "_lib"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(N2D_DIR) not in sys.path:
    sys.path.insert(0, str(N2D_DIR))
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_findings_utils import finding_counts  # noqa: E402
from n2d_route import normalize_episode  # noqa: E402
from skill_snapshot import fingerprint_is_fresh  # noqa: E402
import failure_taxonomy  # noqa: E402
import generation_recipe_manifest  # noqa: E402


VERSION = 1
OUT_JSON = "release_verdict_{episode}.json"
OUT_MD = "release_verdict_{episode}.md"
PILOT_REQUIRED_COVERAGE = {"face", "scene", "action", "lipsync", "seam", "routing"}


def _load_progress_module():
    spec = importlib.util.spec_from_file_location("n2d_progress_for_release_verdict", N2D_DIR / "progress.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


progress_mod = _load_progress_module()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def component(name: str, status: str, message: str, *, path: str = "", details: Any = None) -> Dict[str, Any]:
    row = {"name": name, "status": status, "message": message}
    if path:
        row["path"] = path
    if details not in (None, "", [], {}):
        row["details"] = details
    return row


def compliance_intent(root: Path) -> Tuple[str, Optional[Dict[str, Any]], Path]:
    path = root / "合规" / "compliance_manifest.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return "", None, path
    return str(data.get("distribution_intent") or data.get("release_intent") or "").strip().lower(), data, path


def check_compliance(root: Path) -> Dict[str, Any]:
    intent, data, path = compliance_intent(root)
    if not isinstance(data, dict):
        return component("compliance", "block", "缺 compliance_manifest.json，不能给发布结论。", path=relpath(root, path))
    status = str(data.get("status") or data.get("verdict") or "pass").strip().lower()
    if status in {"blocked", "block", "fail"}:
        return component("compliance", "block", f"合规 manifest 状态为 {status}。", path=relpath(root, path), details={"distribution_intent": intent})
    return component("compliance", "pass", f"合规 manifest 可读；distribution_intent={intent or 'unset'}。", path=relpath(root, path), details={"distribution_intent": intent})


def check_progress_dag(root: Path, episode: str) -> Dict[str, Any]:
    try:
        header, rows = progress_mod.parse(str(root))
        issues = [i for i in progress_mod._dag_state_issues(str(root), header, rows) if i.get("episode") == episode]
    except SystemExit:
        return component("progress_dag", "block", "无法读取 _进度.md，发布判定 fail-closed。")
    except Exception as exc:
        return component("progress_dag", "block", f"progress DAG 审计失败：{type(exc).__name__}: {str(exc)[:160]}")
    blocks = [i for i in issues if i.get("severity") == "block"]
    if blocks:
        return component("progress_dag", "block", f"下游状态已动但上游非法：{len(blocks)} 条。", details=blocks[:5])
    warns = [i for i in issues if i.get("severity") == "warn"]
    if warns:
        return component("progress_dag", "warn", f"存在人工豁免/待复核状态：{len(warns)} 条。", details=warns[:5])
    return component("progress_dag", "pass", "progress DAG 通过。")


def gate_files(root: Path, episode: str) -> List[Path]:
    return [Path(p) for p in sorted(glob.glob(str(production_dir(root) / f"gate_findings_*_{episode}.json")))]


def check_gate(root: Path, episode: str) -> Dict[str, Any]:
    files = gate_files(root, episode)
    if not files:
        return component("gate", "block", "缺 gate_findings_* 报告；不能证明各阶段 gate 跑过。", path=relpath(root, production_dir(root)))
    block = warn = 0
    samples: List[str] = []
    for path in files:
        data = load_json(path)
        b, w, s = finding_counts(data)
        block += b
        warn += w
        samples.extend(s)
    if block:
        return component("gate", "block", f"gate 仍有 block={block}, warn={warn}。", details=samples[:5])
    if warn:
        return component("gate", "warn", f"gate 有 warn={warn}，需结合 taxonomy 判断是否只可 demo。", details=samples[:5])
    return component("gate", "pass", f"gate 通过；reports={len(files)}。")


def check_score(root: Path, episode: str) -> Dict[str, Any]:
    path = production_dir(root) / f"score_{episode}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return component("score", "block", "缺 score_<集>.json。", path=relpath(root, path))
    score = data.get("total_score", data.get("score"))
    threshold = data.get("threshold", 80)
    status = str(data.get("status") or "").strip().lower()
    low = status not in {"pass", "ok"} if status else False
    try:
        low = low or float(score) < float(threshold)
    except Exception:
        pass
    if low:
        return component("score", "block", f"score 未达标：score={score}, threshold={threshold}, status={status or 'unknown'}。", path=relpath(root, path))
    return component("score", "pass", f"score 通过：score={score}, threshold={threshold}。", path=relpath(root, path))


def check_ledger(root: Path, episode: str) -> Dict[str, Any]:
    path = production_dir(root) / f"consistency_ledger_{episode}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return component("ledger", "block", "缺 consistency_ledger_<集>.json。", path=relpath(root, path))
    counts = data.get("counts") if isinstance(data.get("counts"), dict) else {}
    delivery = data.get("delivery_surface") if isinstance(data.get("delivery_surface"), dict) else {}
    status = str(data.get("status") or delivery.get("status") or "").strip().lower()
    block = int(counts.get("block") or 0)
    high = int(counts.get("high") or 0)
    if status in {"blocked", "block", "fail"} or block or high:
        return component("ledger", "block", f"ledger 未放行：status={status or 'unknown'}, block={block}, high={high}。", path=relpath(root, path))
    return component("ledger", "pass", "consistency ledger 通过。", path=relpath(root, path))


def check_review_ui(root: Path, episode: str) -> Dict[str, Any]:
    prod = production_dir(root)
    manifest = prod / f"review_ui_{episode}.json"
    findings = prod / f"review_ui_findings_{episode}.json"
    data = load_json(manifest)
    fdata = load_json(findings)
    if not isinstance(data, dict) or not isinstance(fdata, dict):
        return component("review_ui", "block", "缺 review_ui manifest 或 review_ui_findings。", path=relpath(root, manifest))
    b, w, samples = finding_counts(fdata)
    ref_mtime = max((prod / f"score_{episode}.json").stat().st_mtime if (prod / f"score_{episode}.json").is_file() else 0,
                    (prod / f"consistency_ledger_{episode}.json").stat().st_mtime if (prod / f"consistency_ledger_{episode}.json").is_file() else 0)
    stale = manifest.stat().st_mtime < ref_mtime or findings.stat().st_mtime < ref_mtime
    if stale:
        return component("review_ui", "block", "review-ui 早于 score/ledger，界面与验收账本不新鲜。", path=relpath(root, manifest))
    if b:
        return component("review_ui", "block", f"review-ui findings 仍有 block={b}, warn={w}。", path=relpath(root, findings), details=samples[:5])
    if w:
        return component("review_ui", "warn", f"review-ui findings 有 warn={w}。", path=relpath(root, findings), details=samples[:5])
    return component("review_ui", "pass", "review-ui 通过且不陈旧。", path=relpath(root, manifest))


def check_image_qc(root: Path, episode: str) -> Dict[str, Any]:
    path = production_dir(root) / "image_qc" / episode / f"image_qc_{episode}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return component("image_qc", "block", "缺 image_qc 报告。", path=relpath(root, path))
    fresh = fingerprint_is_fresh(data.get("inputs_fingerprint"), str(root))
    if fresh is not True:
        state = "stale" if fresh is False else "unknown"
        return component("image_qc", "block", f"image_qc 新鲜度={state}，不能证明当前图片。", path=relpath(root, path))
    env = data.get("qc_environment") if isinstance(data.get("qc_environment"), dict) else {}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    precision = str(env.get("precision_level") or "").strip().lower()
    hard = int(summary.get("hard_blocks") or 0)
    verdict = str(summary.get("verdict") or data.get("status") or "").strip().lower()
    if precision != "full":
        return component("image_qc", "block", f"image_qc 精度不是 full：{precision or 'unknown'}。", path=relpath(root, path))
    if hard or verdict in {"block", "blocked", "fail"}:
        return component("image_qc", "block", f"image_qc 未放行：hard_blocks={hard}, verdict={verdict or 'unknown'}。", path=relpath(root, path))
    return component("image_qc", "pass", "image_qc full 且新鲜。", path=relpath(root, path))


def check_generation_recipe(root: Path, episode: str) -> Dict[str, Any]:
    result = generation_recipe_manifest.check_manifest(root, episode)
    path = Path(result.get("path") or generation_recipe_manifest.manifest_path(root, episode))
    issues = result.get("issues") or []
    if result.get("status") != "pass":
        return component("generation_recipe", "block", "; ".join(str(i) for i in issues[:5]) or "生成配方 manifest 未通过。", path=relpath(root, path))
    return component("generation_recipe", "pass", "生成配方 manifest 通过。", path=relpath(root, path))


def _pilot_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"pilot_acceptance_{episode}.json"


def check_pilot(root: Path, episode: str) -> Dict[str, Any]:
    if normalize_episode(episode) != "第1集":
        return component("pilot", "pass", "非首集，不要求本集 pilot signoff。")
    path = _pilot_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict):
        return component("pilot", "block", "首集缺 pilot_acceptance_<集>.json；先用 2-3 个代表镜头验证脸/场景/动作/口型/接缝/路由。", path=relpath(root, path))
    status = str(data.get("status") or data.get("verdict") or "").strip().lower()
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    coverage = set(str(x).strip().lower() for x in (data.get("coverage") or []))
    missing = sorted(PILOT_REQUIRED_COVERAGE - coverage)
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    bad_checks = [k for k in sorted(PILOT_REQUIRED_COVERAGE) if str(checks.get(k) or "").strip().lower() not in {"pass", "ok", "accepted"}]
    if status not in {"pass", "accepted", "green"} or len(clips) < 2 or missing or bad_checks:
        return component(
            "pilot",
            "block",
            f"首集 pilot 未放行：status={status or 'unset'}, clips={len(clips)}, "
            f"missing_coverage={missing}, checks_not_pass={bad_checks}。",
            path=relpath(root, path),
        )
    return component("pilot", "pass", f"首集 pilot 通过：clips={len(clips)}。", path=relpath(root, path))


def check_taxonomy(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    payload = failure_taxonomy.build_taxonomy(root, episode, profile=profile)
    status = payload.get("status")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if status == "blocked":
        return component("failure_taxonomy", "block", f"report-only findings 升级为 block：{summary.get('escalated_blocks', 0)} 条。", details=payload.get("items", [])[:5])
    if status == "warn":
        return component("failure_taxonomy", "warn", f"存在 findings={summary.get('findings', 0)} 条，但未升级 block。", details=summary)
    return component("failure_taxonomy", "pass", "未发现需要回流的问题。")


def final_status(components: Sequence[Mapping[str, Any]], root: Path) -> str:
    if any(c.get("status") == "block" for c in components):
        return "blocked"
    intent, _, _ = compliance_intent(root)
    if intent == "internal_only":
        return "internal-only"
    if any(c.get("status") == "warn" for c in components):
        return "demo-only"
    return "pass"


def build_verdict(root: Path, episode: str, *, profile: str = "demo") -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    components = [
        check_progress_dag(root, episode),
        check_pilot(root, episode),
        check_compliance(root),
        check_gate(root, episode),
        check_score(root, episode),
        check_ledger(root, episode),
        check_review_ui(root, episode),
        check_image_qc(root, episode),
        check_generation_recipe(root, episode),
        check_taxonomy(root, episode, profile),
    ]
    status = final_status(components, root)
    payload = {
        "kind": "n2d_release_verdict",
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "profile": profile,
        "generated_at": now_iso(),
        "status": status,
        "summary": {
            "block": sum(1 for c in components if c.get("status") == "block"),
            "warn": sum(1 for c in components if c.get("status") == "warn"),
            "pass": sum(1 for c in components if c.get("status") == "pass"),
        },
        "components": components,
        "blocking_reasons": [c for c in components if c.get("status") == "block"],
        "warnings": [c for c in components if c.get("status") == "warn"],
    }
    return payload


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# n2d Release Verdict",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- profile：{payload.get('profile')}",
        f"- 汇总：{payload.get('summary')}",
        "",
        "| component | status | message |",
        "|---|---|---|",
    ]
    for item in payload.get("components") or []:
        msg = str(item.get("message") or "").replace("\n", " ")[:240]
        lines.append(f"| {item.get('name')} | {item.get('status')} | {msg} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, episode: str, payload: Mapping[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / OUT_JSON.format(episode=episode)
    md_path = out / OUT_MD.format(episode=episode)
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="aggregate n2d release verdict")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--profile", choices=["demo", "production"], default="demo")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    payload = build_verdict(root, ns.episode, profile=ns.profile)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload["episode"], payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
