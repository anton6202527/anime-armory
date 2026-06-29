#!/usr/bin/env python3
"""Production readiness gate for n2d episode delivery.

This script ties existing deterministic checks into one release decision.  It
does not generate creative assets, spend money, or update `_进度.md`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parents[1]
LIB = SCRIPT_DIR.parents[0] / "_lib"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from n2d_const import PRODUCTION_DIR, PRODUCTION_READINESS_KIND  # noqa: E402
from n2d_schema_registry import scan_artifacts, write_validation  # noqa: E402
from gate_policy_matrix import validate_matrix as validate_gate_policy_matrix  # noqa: E402
import artifact_lineage  # noqa: E402
import gate_policy_coverage  # noqa: E402
import generation_recipe_manifest  # noqa: E402
import genre_packs  # noqa: E402


VERSION = 1
READINESS_JSON = "production_readiness_{episode}.json"
READINESS_MD = "production_readiness_{episode}.md"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


release_manifest = load_module("n2d_release_manifest_for_readiness", SKILLS_DIR / "n2d-compose" / "release_manifest.py")
event_ledger = load_module("n2d_event_ledger_for_readiness", SKILLS_DIR / "n2d-dashboard" / "scripts" / "event_ledger.py")
queue_mod = load_module("n2d_batch_queue_for_readiness", SKILLS_DIR / "n2d-batch" / "scripts" / "queue.py")
governance = load_module("n2d_batch_governance_for_readiness", SKILLS_DIR / "n2d-batch" / "scripts" / "governance.py")
golden_set = load_module("n2d_golden_set_for_readiness", SKILLS_DIR / "n2d-review" / "scripts" / "golden_set_bootstrap.py")
review_calibration = load_module("n2d_review_calibration_for_readiness", SKILLS_DIR / "n2d-review-ui" / "scripts" / "calibration.py")
freshness = load_module("n2d_freshness_for_readiness", LIB / "freshness.py")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def check(name: str, status: str, message: str = "", **extra: Any) -> Dict[str, Any]:
    row = {"name": name, "status": status, "message": message}
    row.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    return row


def status_from_exit(code: int) -> str:
    return "pass" if code == 0 else "fail"


def run_next_action(root: Path, episode: str, *, skip: bool = False) -> Dict[str, Any]:
    if skip:
        return check("next_action", "skip", "skipped by --skip-next-action")
    cmd = [sys.executable, str(SKILLS_DIR / "n2d" / "run.py"), "next", str(root), episode, "--json"]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    payload: Any = None
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = None
    status = "pass" if proc.returncode == 0 else "fail"
    stop_reason = payload.get("stop_reason") if isinstance(payload, dict) else ""
    if stop_reason in {"done", "needs_acceptance_signoff"}:
        status = "pass"
    elif stop_reason and status == "pass":
        status = "warn"
    return check(
        "next_action",
        status,
        stop_reason or (proc.stderr.strip()[:300] if proc.stderr else ""),
        command=" ".join(cmd),
        stop_reason=stop_reason,
    )


def run_artifact_validation(root: Path, *, write: bool) -> Dict[str, Any]:
    payload = scan_artifacts(str(root), strict_unknown=False)
    outputs = write_validation(str(root), payload) if write else {}
    return check(
        "artifact_validation",
        "fail" if payload.get("status") == "fail" else ("warn" if payload.get("status") == "warn" else "pass"),
        f"checked={payload.get('checked_count')} block={(payload.get('summary') or {}).get('block', 0)}",
        outputs=outputs,
    )


def run_event_ledger(root: Path, *, write: bool, strict_trace: bool) -> List[Dict[str, Any]]:
    audit = event_ledger.audit(str(root), write=write, strict_trace=strict_trace)
    replay = event_ledger.replay(str(root), write=write)
    return [
        check("event_ledger_audit", "fail" if audit.get("status") == "fail" else ("warn" if audit.get("status") == "warn" else "pass"),
              f"events={audit.get('event_count')} trace_coverage={(audit.get('trace_summary') or {}).get('coverage')}",
              path=relpath(root, production_dir(root) / "production_events_audit.json")),
        check("event_ledger_replay", "fail" if replay.get("status") == "fail" else "pass",
              f"events={replay.get('event_count', 0)}",
              path=relpath(root, production_dir(root) / "dashboard_replay.json") if write else ""),
    ]


def run_gate_policy_matrix() -> Dict[str, Any]:
    errors = validate_gate_policy_matrix()
    return check("gate_policy_matrix", "fail" if errors else "pass", "; ".join(errors[:5]) if errors else "matrix valid")


def run_generation_recipe(root: Path, episode: str, *, write: bool) -> Dict[str, Any]:
    payload = generation_recipe_manifest.build_manifest(root, episode)
    if write:
        generation_recipe_manifest.write_manifest(root, episode, payload)
    result = generation_recipe_manifest.check_manifest(root, episode) if write else {"status": payload.get("status"), "issues": []}
    return check(
        "generation_recipe_manifest",
        "fail" if result.get("status") != "pass" else "pass",
        "; ".join((result.get("issues") or [])[:5]) or f"records={(payload.get('summary') or {}).get('records', 0)}",
        path=relpath(root, generation_recipe_manifest.manifest_path(root, episode)),
    )


def run_gate_policy_coverage(root: Path, episode: str, *, write: bool) -> Dict[str, Any]:
    payload = gate_policy_coverage.build_coverage(root, episode)
    if write:
        gate_policy_coverage.write_coverage(root, episode, payload)
    result = gate_policy_coverage.check_coverage(root, episode) if write else {"status": payload.get("status"), "issues": []}
    return check(
        "gate_policy_coverage",
        "fail" if result.get("status") != "pass" else "pass",
        "; ".join((result.get("issues") or [])[:5]) or f"groups={(payload.get('summary') or {}).get('groups', 0)}",
        path=relpath(root, gate_policy_coverage.coverage_path(root, episode)),
    )


def run_gate_inventory() -> Dict[str, Any]:
    """全量闸门自清点（项目无关·读 gate.py 源）：任何 check_* 从 run() 不可达=死闸=fail。

    回归守卫：把「dead BLOCK 分支」那类 bug（曾需整 commit 人肉修）变成发布前自动拦截。"""
    inv = gate_policy_coverage.gate_inventory()
    return check(
        "gate_inventory",
        "fail" if inv.get("status") != "pass" else "pass",
        "; ".join((inv.get("issues") or [])[:5])
        or f"{inv.get('reachable', 0)}/{inv.get('total', 0)} check_ 可达，0 死闸",
        dead=inv.get("dead") or None,
    )


def queue_exists(root: Path) -> bool:
    return (production_dir(root) / queue_mod.QUEUE_JSON).is_file()


def run_batch_checks(root: Path, *, write: bool) -> List[Dict[str, Any]]:
    if not queue_exists(root):
        return [check("batch_queue", "skip", "no batch_queue.json")]
    out: List[Dict[str, Any]] = []
    coord = queue_mod.coordination_backend_status(str(root))
    out.append(check("batch_coordination", "warn" if coord.get("status") == "warn" else ("fail" if coord.get("status") not in {"ok", "warn"} else "pass"),
                     str(coord.get("note") or coord.get("warning") or coord.get("status")), backend=coord.get("backend")))
    if coord.get("backend") == "sqlite":
        doctor = queue_mod.sqlite_doctor(str(root), write=write)
        out.append(check(
            "batch_sqlite_doctor",
            "fail" if doctor.get("status") == "fail" else ("skip" if doctor.get("status") == "skip" else "pass"),
            f"issues={(doctor.get('summary') or {}).get('issues', 0)}",
            path=relpath(root, production_dir(root) / queue_mod.SQLITE_DOCTOR_JSON) if write else "",
        ))
    if write:
        rec = queue_mod.reconcile_jobs(str(root), apply=False)
        out.append(check("batch_job_reconcile", "fail" if rec.get("status") == "fail" else ("warn" if rec.get("status") == "warn" else "pass"),
                         f"matched={(rec.get('summary') or {}).get('matched', 0)} warnings={(rec.get('summary') or {}).get('warnings', 0)}",
                         path=relpath(root, production_dir(root) / queue_mod.JOB_RECONCILE_JSON)))
    gov = governance.evaluate(str(root))
    if write:
        governance.write_report(str(root), gov)
    out.append(check("batch_governance", "fail" if gov.get("status") == "critical" else ("warn" if gov.get("status") == "warn" else "pass"),
                     f"dead_letters={(gov.get('summary') or {}).get('dead_letters', 0)} retry_rate={(gov.get('summary') or {}).get('retry_rate', 0)}",
                     path=relpath(root, production_dir(root) / governance.REPORT_JSON) if write else ""))
    return out


def run_release(root: Path, episode: str, *, write: bool, asset: Optional[str]) -> List[Dict[str, Any]]:
    lineage = artifact_lineage.build_lineage(root, episode, asset=asset)
    if write:
        artifact_lineage.write_lineage(root, episode, lineage)
    lineage_check = artifact_lineage.check_lineage(root, episode) if write else {"status": lineage.get("status"), "issues": []}
    manifest = release_manifest.build_manifest(root, episode, asset=asset, stage="review")
    if write:
        release_manifest.write_manifest(root, episode, manifest)
    manifest_check = release_manifest.check_manifest(root, episode) if write else {"status": "fail" if manifest.get("readiness", {}).get("status") == "blocked" else "pass", "issues": manifest.get("readiness", {}).get("blocks") or []}
    return [
        check("artifact_lineage", "fail" if lineage_check.get("status") != "pass" else "pass",
              "; ".join((lineage_check.get("issues") or [])[:5]) or f"lineage_id={lineage.get('lineage_id')}",
              path=relpath(root, artifact_lineage.lineage_path(root, episode))),
        check("release_manifest", "fail" if manifest_check.get("status") != "pass" else "pass",
              "; ".join((manifest_check.get("issues") or [])[:5]) or f"readiness={manifest.get('readiness', {}).get('status')}",
              path=relpath(root, release_manifest.release_manifest_path(root, episode))),
    ]


def run_genre_packs(root: Path, episode: str, *, write: bool) -> Dict[str, Any]:
    payload = genre_packs.validate_all()
    context = genre_packs.build_context(root, episode, "review")
    if write:
        genre_packs.write_context(root, episode, "review", context)
    statuses = [payload.get("status"), context.get("status")]
    status = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "pass")
    return check(
        "genre_packs",
        status,
        f"packs={len(payload.get('packs') or [])} active_scenes={(context.get('summary') or {}).get('active_scenes', 0)}",
        path=relpath(root, genre_packs.context_path(root, episode, "review")) if write else "",
    )


def scale_up_required(root: Path, explicit: bool = False) -> bool:
    if explicit:
        return True
    data = release_manifest.load_json(release_manifest.compliance.manifest_path(root))
    if not isinstance(data, dict):
        return False
    return str(data.get("distribution_intent") or "").strip().lower() == "paid_distribution"


def run_freshness_checks(root: Path) -> List[Dict[str, Any]]:
    rows = freshness.check_all()
    bad = [r for r in rows if r.get("status") in freshness._BAD_STATUSES]
    if not bad:
        return [check("candidate_freshness", "pass", f"sources={len(rows)} all fresh")]
    sample = "; ".join(f"{r.get('id')}={r.get('status')}" for r in bad[:5])
    return [check(
        "candidate_freshness",
        "warn",
        f"{len(bad)} candidate source(s) stale/missing; run skills/n2d/_lib/refresh.py status then refresh/bump. {sample}",
        path="skills/n2d/_lib/freshness.py",
    )]


# judge≠generator 模型族独立性（2026 LLM/VLM-as-judge 铁律）：同族自评会虚高一致性、漏判崩坏，
# 不得用作自动闸。族标记取常见生图/生视频/LMM 厂商；未知名 → "" 不参与同族判定（不臆造冲突）。
_MODEL_FAMILIES: Dict[str, Sequence[str]] = {
    "openai": ("gpt", "openai", "dall-e", "dalle", "sora", "chatgpt", "o1-", "o3-", "o4-"),
    "google": ("gemini", "veo", "imagen", "bard"),
    "anthropic": ("claude", "opus", "sonnet", "haiku"),
    "bytedance": ("seedream", "seedance", "doubao", "jimeng", "dreamina", "即梦", "豆包"),
    "kuaishou": ("kling", "kolors", "keling", "可灵"),
    "alibaba": ("wanx", "wan2", "万相", "qwen", "tongyi", "通义"),
    "minimax": ("minimax", "hailuo", "海螺", "abab"),
    "tencent": ("hunyuan", "混元"),
    "baidu": ("ernie", "文心"),
}

_JUDGE_REPORT_RELS = (
    "生产数据/video_vlm_consistency_{ep}.json",
    "生产数据/video_vlm_judgements_{ep}.json",
    "生产数据/video_vlm_judgments_{ep}.json",
    "出视频/{ep}/video_vlm_consistency.json",
    "合成/{ep}/video_vlm_consistency.json",
    "生产数据/appearance_judge_{ep}.json",
)


def _model_family(name: Any) -> str:
    low = str(name or "").strip().lower()
    if not low:
        return ""
    for family, markers in _MODEL_FAMILIES.items():
        if any(marker in low for marker in markers):
            return family
    return ""


def _load_json_quiet(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _judge_models(root: Path, episode: str) -> Set[str]:
    out: Set[str] = set()
    for rel in _JUDGE_REPORT_RELS:
        data = _load_json_quiet(root / rel.format(ep=episode))
        if not isinstance(data, dict):
            continue
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        for value in (data.get("judge_model"), summary.get("judge_model"), meta.get("judge_model")):
            if value:
                out.add(str(value))
        for key in ("rows", "judgements", "judgments", "findings"):
            for row in data.get(key) or []:
                if isinstance(row, dict) and row.get("judge_model"):
                    out.add(str(row.get("judge_model")))
    return out


def _generator_models(root: Path, episode: str) -> Set[str]:
    try:
        payload = generation_recipe_manifest.build_manifest(root, episode)
    except Exception:
        return set()
    out: Set[str] = set()
    for record in payload.get("records") or []:
        if isinstance(record, dict) and record.get("model"):
            out.add(str(record.get("model")))
    return out


def judge_generator_independence(root: Path, episode: str, *, scale_up: bool = False) -> Dict[str, Any]:
    judge = _judge_models(root, episode)
    if not judge:
        return check(
            "judge_generator_independence",
            "info",
            "未记录 judge_model（无 VLM 判题 sidecar）；无法核验 judge≠generator 模型族独立性",
        )
    generator = _generator_models(root, episode)
    judge_fams = {_model_family(m) for m in judge} - {""}
    gen_fams = {_model_family(m) for m in generator} - {""}
    overlap = judge_fams & gen_fams
    if overlap:
        return check(
            "judge_generator_independence",
            "fail" if scale_up else "warn",
            f"VLM 判题与生成同属模型族 {sorted(overlap)}（judge={sorted(judge)} generator={sorted(generator)}）；"
            "同族自评会虚高一致性、漏判崩坏（2026 LLM/VLM-as-judge 铁律：judge 不得与 generator 同族）；"
            "换异族 VLM 判题，或令该判题仅作 triage 不入自动闸。",
        )
    return check(
        "judge_generator_independence",
        "pass",
        f"judge={sorted(judge)} generator={sorted(generator)} 模型族独立",
    )


def run_calibration_checks(root: Path, episode: str, *, write: bool, scale_up: bool = False) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        report = golden_set.build(str(root))
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        by_dim = summary.get("by_dimension") if isinstance(summary.get("by_dimension"), dict) else {}
        char = by_dim.get("character_consistency") if isinstance(by_dim.get("character_consistency"), dict) else {}
        pass_n = int(char.get("pass") or 0)
        fail_n = int(char.get("fail") or 0)
        enough = pass_n >= 1 and fail_n >= 1
        # 标定是**放量(scale-up)前**的门，不是单集 release 门——缺标定数据(跨项目/跨集才攒得出)只在
        # scale_up 时 warn 阻断；单集 readiness 下记 info 不降级（同「留存只观察」口径，避免类目串扰把
        # 一集 demo 的 release 误判成 warn）。real error(build 抛异常)仍 warn。
        out.append(check(
            "golden_set_calibration",
            "pass" if enough else ("warn" if scale_up else "info"),
            f"character_consistency pass={pass_n} fail={fail_n}; total={summary.get('total', 0)}",
            path=relpath(root, production_dir(root) / "consistency_golden_set.jsonl"),
        ))
    except Exception as exc:
        out.append(check("golden_set_calibration", "warn", f"unavailable: {type(exc).__name__}: {str(exc)[:160]}"))

    cal_path = production_dir(root) / review_calibration.REPORT_JSON
    data = review_calibration.load_json(cal_path)
    if not isinstance(data, dict):
        out.append(check(
            "reviewer_calibration",
            "fail" if scale_up else "info",
            "missing review_calibration.json; run n2d-review-ui calibration on a small gold set before scale-up",
            path=relpath(root, cal_path),
        ))
    else:
        status = str(data.get("status") or "").strip()
        out.append(check(
            "reviewer_calibration",
            "pass" if status == "pass" else ("fail" if scale_up else "info"),
            f"status={status or 'unknown'} reviewers={len(data.get('reviewers') or [])} cases={data.get('case_count', 0)}",
            path=relpath(root, cal_path),
        ))
    out.append(judge_generator_independence(root, episode, scale_up=scale_up))
    return out


def summarize(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {"pass": 0, "warn": 0, "fail": 0, "skip": 0}
    for item in checks:
        status = str(item.get("status") or "warn")
        counts[status] = counts.get(status, 0) + 1
    return counts


def build_readiness(root: Path, episode: str, *, write: bool = False, asset: Optional[str] = None,
                    strict_trace: bool = True, skip_next_action: bool = False,
                    scale_up: bool = False) -> Dict[str, Any]:
    root = root.resolve()
    scale_up_mode = scale_up_required(root, explicit=scale_up)
    checks: List[Dict[str, Any]] = []
    checks.append(run_next_action(root, episode, skip=skip_next_action))
    checks.extend(run_event_ledger(root, write=write, strict_trace=strict_trace))
    checks.append(run_generation_recipe(root, episode, write=write))
    checks.append(run_gate_policy_matrix())
    checks.append(run_gate_inventory())
    checks.append(run_gate_policy_coverage(root, episode, write=write))
    checks.append(run_artifact_validation(root, write=write))
    checks.extend(run_batch_checks(root, write=write))
    checks.extend(run_release(root, episode, write=write, asset=asset))
    checks.extend(run_freshness_checks(root))
    checks.extend(run_calibration_checks(root, episode, write=write, scale_up=scale_up_mode))
    checks.append(run_genre_packs(root, episode, write=write))
    summary = summarize(checks)
    payload = {
        "kind": PRODUCTION_READINESS_KIND,
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "profile": "production",
        "scale_up": scale_up_mode,
        "generated_at": now_iso(),
        "checks": checks,
        "summary": summary,
        "status": "fail" if summary.get("fail") else ("warn" if summary.get("warn") else "pass"),
    }
    if write:
        write_readiness(root, episode, payload)
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Production Readiness",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- pass/warn/fail/skip：{payload.get('summary')}",
        "",
        "| check | status | message |",
        "|---|---|---|",
    ]
    for item in payload.get("checks") or []:
        msg = str(item.get("message") or "").replace("\n", " ")[:240]
        lines.append(f"| {item.get('name')} | {item.get('status')} | {msg} |")
    lines.append("")
    return "\n".join(lines)


def write_readiness(root: Path, episode: str, payload: Dict[str, Any]) -> Dict[str, str]:
    out = production_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / READINESS_JSON.format(episode=episode)
    md_path = out / READINESS_MD.format(episode=episode)
    tmp = json_path.with_name(f"{json_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="run n2d production readiness gate")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--asset")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-strict-trace", action="store_true")
    ap.add_argument("--scale-up", action="store_true", help="paid/batch release profile: reviewer calibration gaps fail instead of warn")
    ap.add_argument("--skip-next-action", action="store_true", help="for CI fixtures only; production should run run.py next --json")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    payload = build_readiness(
        Path(ns.root),
        ns.episode,
        write=ns.write,
        asset=ns.asset,
        strict_trace=not ns.no_strict_trace,
        skip_next_action=ns.skip_next_action,
        scale_up=ns.scale_up,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 1 if payload.get("status") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
