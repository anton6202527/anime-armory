#!/usr/bin/env python3
"""Unified n2d release verdict.

Aggregates gate, score, consistency ledger, review-ui, image_qc freshness,
generation recipe evidence, progress DAG, pilot signoff and compliance into one
pass / blocked / demo-only / internal-only decision.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import glob
import hashlib
import importlib.util
import io
import json
import os
import re
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
from n2d_thresholds import score_threshold_for_profile  # noqa: E402  机器分 profile 阈值单一真值源（与 n2d-score 共用）
from n2d_route import normalize_episode  # noqa: E402
from skill_snapshot import fingerprint_is_fresh  # noqa: E402
import failure_taxonomy  # noqa: E402
import generation_recipe_manifest  # noqa: E402
import preventive_contracts  # noqa: E402
import audience_experience  # noqa: E402
import contract_trace  # noqa: E402
import pilot_risk_sampler  # noqa: E402
import production_locks  # noqa: E402
import script_supervisor_log  # noqa: E402
import stop_loss  # noqa: E402
import acceptance_contract  # noqa: E402

try:
    from flow_telemetry import record_milestone as _record_flow_milestone  # noqa: E402
except Exception:  # pragma: no cover
    _record_flow_milestone = None


VERSION = 2
OUT_JSON = "release_verdict_{episode}.json"
OUT_MD = "release_verdict_{episode}.md"
PILOT_REQUIRED_COVERAGE = {"face", "scene", "action", "lipsync", "seam", "routing"}
PRODUCTION_REQUIRED_FILES = (
    "production_breakdown.json",
    "continuity_breakdown.json",
    "continuity_bible.json",
    "ai_shooting_schedule.json",
    "ai_call_sheet.md",
)
PRODUCTION_HANDOFF_MANIFEST = "production_handoff_pack.json"
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)
CONFIRMED_RE = re.compile(r"(?im)^\s*(?:status|状态)\s*[:：]\s*(?:confirmed|已确认|pass|通过)\s*$")
STRICT_PROFILES = {"production", "commercial", "cn_public", "overseas"}
INTERNAL_PROFILES = {"internal", "internal_only", "internal-only"}
DEMO_PROFILES = {"", "demo", "demo_only", "demo-only"}


def _load_progress_module():
    spec = importlib.util.spec_from_file_location("n2d_progress_for_release_verdict", N2D_DIR / "progress.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


progress_mod = _load_progress_module()


def _load_compliance_module():
    path = N2D_DIR / "n2d-compliance" / "scripts" / "compliance.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("n2d_compliance_for_release_verdict", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


compliance_mod = _load_compliance_module()


def _load_local_module(name: str, path: Path):
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


media_artifact_mod = _load_local_module(
    "n2d_media_artifact_for_release_verdict",
    N2D_DIR / "n2d-compose" / "media_artifact.py",
)
creative_watchdown_mod = _load_local_module(
    "n2d_creative_watchdown_for_release_verdict",
    N2D_DIR / "n2d-review" / "scripts" / "creative_watchdown.py",
)


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def check_compliance(root: Path, episode: str) -> Dict[str, Any]:
    intent, data, path = compliance_intent(root)
    if not isinstance(data, dict):
        return component("compliance", "block", "缺 compliance_manifest.json，不能给发布结论。", path=relpath(root, path))
    if compliance_mod is not None:
        verdict = compliance_mod.compliance_verdict(root, episode, stage="review")
        issues = verdict.get("issues") or []
        blocks = [i for i in issues if str(i).startswith("BLOCK ")]
        warns = [i for i in issues if not str(i).startswith("BLOCK ")]
        if blocks:
            return component(
                "compliance",
                "block",
                f"字段级合规未通过：BLOCK={len(blocks)}, INFO/WARN={len(warns)}；distribution_intent={intent or 'unset'}。",
                path=relpath(root, path),
                details={"field_verdict": verdict, "issues": issues[:20]},
            )
        if warns:
            return component(
                "compliance",
                "warn",
                f"字段级合规存在发布待办：INFO/WARN={len(warns)}；distribution_intent={intent or 'unset'}。",
                path=relpath(root, path),
                details={"field_verdict": verdict, "issues": issues[:20]},
            )
        return component("compliance", "pass", f"字段级合规通过；distribution_intent={intent or 'unset'}。", path=relpath(root, path), details={"field_verdict": verdict})
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


def _json_confirmed(path: Path) -> Tuple[bool, List[str]]:
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        return False, ["JSON 无法解析或不是 object"]
    if str(data.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed")
    if PLACEHOLDER_RE.search(json.dumps(data, ensure_ascii=False)):
        issues.append("仍含待补/TODO 占位")
    return not issues, issues


def _markdown_confirmed(path: Path) -> Tuple[bool, List[str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = ""
    issues: List[str] = []
    if not text.strip():
        return False, ["文件为空"]
    if not CONFIRMED_RE.search(text):
        issues.append("缺 status: confirmed / 状态: confirmed")
    if PLACEHOLDER_RE.search(text):
        issues.append("仍含待补/TODO 占位")
    return not issues, issues


def check_production_handoff(root: Path, episode: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    ep_dir = root / "脚本" / episode
    for name in PRODUCTION_REQUIRED_FILES:
        path = ep_dir / name
        rel = relpath(root, path)
        if not path.is_file():
            rows.append({"file": rel, "status": "block", "issues": ["文件缺失"]})
            continue
        ok, issues = _json_confirmed(path) if path.suffix == ".json" else _markdown_confirmed(path)
        rows.append({"file": rel, "status": "pass" if ok else "block", "issues": issues})
    manifest = ep_dir / PRODUCTION_HANDOFF_MANIFEST
    mrel = relpath(root, manifest)
    mdata = load_json(manifest)
    miss: List[str] = []
    if not isinstance(mdata, dict):
        miss.append("production_handoff_pack.json 缺失或无效")
    else:
        if str(mdata.get("status") or "").strip().lower() != "confirmed":
            miss.append("status 不是 confirmed")
        fresh = fingerprint_is_fresh(mdata.get("inputs_fingerprint"), str(root))
        if fresh is False:
            miss.append("inputs_fingerprint 已过期，上游输入变更后需重新确认 P-3 handoff")
        elif fresh is None:
            miss.append("缺 inputs_fingerprint，不能证明 handoff 对应当前输入")
    rows.append({"file": mrel, "status": "pass" if not miss else "block", "issues": miss})
    blockers = [r for r in rows if r["status"] != "pass"]
    if blockers:
        return component(
            "production_handoff",
            "block",
            f"P-3 制片/场记交接未确认：{len(blockers)}/{len(rows)} 个文件未通过。",
            path=relpath(root, ep_dir),
            details=blockers,
        )
    return component("production_handoff", "pass", "P-3 制片/场记交接已 confirmed。", path=relpath(root, ep_dir))


def check_production_locks(root: Path, episode: str) -> Dict[str, Any]:
    report = production_locks.check_ledger(root, episode, write_missing=False, stage="review", write_check=False)
    status = str(report.get("status") or "").lower()
    if status != "pass":
        findings = report.get("findings") if isinstance(report.get("findings"), list) else []
        msg = "锁版账未通过；先确认 source/script/storyboard/style_identity/voice_timing/picture lock，或记录解锁决策后重跑。"
        return component(
            "production_locks",
            "block",
            msg,
            path=report.get("lock_path") or relpath(root, production_locks.lock_path(root, episode)),
            details={"findings": findings[:20], "check_path": report.get("check_path")},
        )
    return component("production_locks", "pass", "生产锁版账通过，未发现锁后漂移。", path=report.get("lock_path"))


def check_script_supervisor_log(root: Path, episode: str) -> Dict[str, Any]:
    report = script_supervisor_log.check_log(root, episode, write_missing=False)
    if report.get("status") != "pass":
        return component(
            "script_supervisor_log",
            "block",
            "缺生成后场记日志或存在未签收 take；先跑 script_supervisor_log.py check --write-missing 并确认 accepted_take。",
            path=report.get("log_path"),
            details={"findings": (report.get("findings") or [])[:20], "check_path": report.get("check_path")},
        )
    return component("script_supervisor_log", "pass", "生成后场记日志已覆盖 storyboard Clip 和 accepted take。", path=report.get("log_path"))


def gate_files(root: Path, episode: str) -> List[Path]:
    return [Path(p) for p in sorted(glob.glob(str(production_dir(root) / f"gate_findings_*_{episode}.json")))]


def _gate_stage_of(path: Path, data: Any, episode: str) -> str:
    """gate_findings 的阶段名：优先读 payload.gate_stage，回退解析文件名 gate_findings_<stage>_<ep>.json。"""
    if isinstance(data, dict):
        stage = str(data.get("gate_stage") or "").strip()
        if stage:
            return stage
    name = path.name
    prefix, suffix = "gate_findings_", f"_{normalize_episode(episode)}.json"
    if name.startswith(prefix) and name.endswith(suffix):
        return name[len(prefix):-len(suffix)] or name
    return name


def check_gate(root: Path, episode: str) -> Dict[str, Any]:
    files = gate_files(root, episode)
    if not files:
        return component("gate", "block", "缺 gate_findings_* 报告；不能证明各阶段 gate 跑过。", path=relpath(root, production_dir(root)))
    block = warn = 0
    samples: List[str] = []
    stale: List[str] = []          # 指纹证明陈旧的阶段（跑过后产物又变，旧绿不算数）
    unverifiable: List[str] = []   # 缺可核验 inputs_fingerprint 的阶段（旧报告，无法证明对应当前产物）
    for path in files:
        data = load_json(path)
        b, w, s = finding_counts(data)
        block += b
        warn += w
        samples.extend(s)
        # 新鲜度耦合：绿闸（block=0）也必须证明凭据对应**当前产物**。gate_findings 的 inputs_fingerprint
        # 现覆盖本阶段认证的 PNG/clip/母版/角色卡（见 dashboard.gate_findings_payload）；此前 check_gate
        # 只数 block、无视指纹——video/compose 重出 clip/母版后旧绿仍判 pass（image 阶段另有 check_image_qc
        # 独立验新鲜度兜底，video/compose 没有，check_gate 是其唯一质量后盾）。与 check_image_qc 同口径 fail-closed。
        fp = data.get("inputs_fingerprint") if isinstance(data, dict) else None
        fresh = fingerprint_is_fresh(fp, str(root))
        if fresh is False:
            stale.append(_gate_stage_of(path, data, episode))
        elif fresh is None:
            unverifiable.append(_gate_stage_of(path, data, episode))
    if block:
        return component("gate", "block", f"gate 仍有 block={block}, warn={warn}。", details=samples[:5])
    if stale:
        return component(
            "gate", "block",
            f"gate 凭据陈旧：{'、'.join(sorted(set(stale)))} 跑过后产物又变（clip/母版/图/角色卡被改），"
            f"绿闸不算数；对当前产物重跑对应 gate 后再裁决。",
            details=samples[:5])
    if warn or unverifiable:
        msg = f"gate 有 warn={warn}"
        if unverifiable:
            msg += f"；{'、'.join(sorted(set(unverifiable)))} 凭据缺可核验 inputs_fingerprint（旧报告，无法证明对应当前产物，建议重跑 gate 盖新鲜指纹）"
        msg += "，需结合 taxonomy 判断是否只可 demo。"
        return component("gate", "warn", msg, details=samples[:5])
    return component("gate", "pass", f"gate 通过；reports={len(files)}。")


# release profile → 机器分 profile（阈值经 n2d_thresholds.score_threshold_for_profile 解析）。
# cn_public/commercial 公开/商用发布按 production(90) 档，overseas 按 88，internal 按 standard(85)。
_RELEASE_TO_SCORE_PROFILE = {
    "demo": "demo", "internal": "standard",
    "cn_public": "production", "overseas": "overseas",
    "commercial": "production", "production": "production",
}


def check_score(root: Path, episode: str, profile: str = "demo") -> Dict[str, Any]:
    path = production_dir(root) / f"score_{episode}.json"
    data = load_json(path)
    if not isinstance(data, dict):
        return component("score", "block", "缺 score_<集>.json。", path=relpath(root, path))
    score = data.get("total_score", data.get("score"))
    # 阈值下限按 release profile 收紧：此前只信 score 文件里已写的 threshold（fallback 还是 80），
    # commercial 发布可以放行按 demo(75) 档生成的 score 文件——release 侧必须重申自己的机器分下限。
    file_threshold = data.get("threshold", 85)
    score_profile = _RELEASE_TO_SCORE_PROFILE.get(str(profile or "").strip().lower(), "standard")
    profile_floor = score_threshold_for_profile(score_profile)
    try:
        threshold = max(float(file_threshold), float(profile_floor))
    except Exception:
        threshold = float(profile_floor)
    status = str(data.get("status") or "").strip().lower()
    low = status not in {"pass", "ok"} if status else False
    try:
        low = low or float(score) < float(threshold)
    except Exception:
        pass
    if low:
        return component("score", "block",
                         f"score 未达标：score={score}, threshold={threshold:g}"
                         f"（file={file_threshold}, {profile} profile 下限={profile_floor}）, status={status or 'unknown'}。",
                         path=relpath(root, path))
    return component("score", "pass",
                     f"score 通过：score={score}, threshold={threshold:g}（{profile} profile 下限={profile_floor}）。",
                     path=relpath(root, path))


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


def _structured_signoff_fresh(root: Path, episode: str, source_path: Path) -> Tuple[bool, str]:
    prod = production_dir(root)
    candidates = (
        prod / f"image_qc_advisory_signoff_{episode}.json",
        prod / f"consistency_advisory_signoff_{episode}.json",
    )
    source_mtime = source_path.stat().st_mtime if source_path.is_file() else 0
    for path in candidates:
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        try:
            if path.stat().st_mtime < source_mtime:
                continue
        except OSError:
            continue
        status = str(data.get("status") or data.get("verdict") or "").strip().lower()
        accepted = data.get("accepted") if isinstance(data.get("accepted"), list) else []
        approvals = data.get("approvals") if isinstance(data.get("approvals"), list) else []
        if status in {"approved", "accepted", "pass", "ok", "signed_off"} or accepted or approvals:
            return True, relpath(root, path)
    return False, ""


def check_image_qc(root: Path, episode: str, profile: str = "demo") -> Dict[str, Any]:
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
    if verdict in {"review", "warn", "advisory"} and _strict_release_context(root, profile):
        signed, signoff_path = _structured_signoff_fresh(root, episode, path)
        if not signed:
            return component(
                "image_qc",
                "block",
                f"image_qc verdict={verdict}；production/公开发布/投放前必须补结构化 advisory signoff 后再放行。",
                path=relpath(root, path),
            )
        return component("image_qc", "pass", f"image_qc full 且 review advisory 已签收：{signoff_path}。", path=relpath(root, path))
    return component("image_qc", "pass", "image_qc full 且新鲜。", path=relpath(root, path))


def check_generation_recipe(root: Path, episode: str) -> Dict[str, Any]:
    result = generation_recipe_manifest.check_manifest(root, episode)
    path = Path(result.get("path") or generation_recipe_manifest.manifest_path(root, episode))
    issues = result.get("issues") or []
    if result.get("status") != "pass":
        return component("generation_recipe", "block", "; ".join(str(i) for i in issues[:5]) or "生成配方 manifest 未通过。", path=relpath(root, path))
    return component("generation_recipe", "pass", "生成配方 manifest 通过。", path=relpath(root, path))


def check_operational_evidence(root: Path, episode: str, name: str, filename: str) -> Dict[str, Any]:
    path = production_dir(root) / filename
    issues, projection = acceptance_contract.validate_operational_evidence(
        root, episode, role=name, path=path
    )
    if issues:
        return component(
            name,
            "block",
            f"{filename} 强契约未通过；不能证明报告来自当前源证据。",
            path=relpath(root, path),
            details={
                "issues": issues[:20],
                "projection": projection,
                "report_sha256": sha256_file(path) if path.is_file() else "",
            },
        )
    return component(
        name,
        "pass",
        f"{filename} kind/version/root/source/content/current 均通过。",
        path=relpath(root, path),
        details={"projection": projection},
    )


def _final_master_files(root: Path, episode: str) -> List[Path]:
    return acceptance_contract.final_master_candidates(root, episode)


def _master_details(root: Path, masters: Sequence[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in masters:
        stat = path.stat()
        rows.append({
            "path": relpath(root, path),
            "sha256": sha256_file(path),
            "bytes": stat.st_size,
            "mtime": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat(),
        })
    return rows


def check_final_master(root: Path, episode: str) -> Dict[str, Any]:
    if media_artifact_mod is None:
        return component("final_master", "block", "统一 MediaArtifactReceipt validator 不可用。")
    canonical = acceptance_contract.resolve_final_master(root, episode)
    if canonical is None:
        return component(
            "final_master", "block", "缺 canonical final master；MediaArtifactReceipt 不能替代母版。",
            path=relpath(root, root / "合成" / episode),
        )
    current = media_artifact_mod.current_receipt(root, episode, canonical=canonical)
    if current.get("status") != "pass":
        return component(
            "final_master",
            "block",
            "canonical master 缺 current MediaArtifactReceipt；文件存在或 provider succeeded 均不能放行。",
            path=str(current.get("path") or ""),
            details={"issues": current.get("issues") or [], "receipt": current.get("receipt") or {}},
        )
    receipt = current.get("receipt") or {}
    probe = ((receipt.get("validation") or {}).get("probe") or {})
    return component(
        "final_master",
        "pass",
        f"current MediaArtifactReceipt 已绑定 canonical SHA/规格/recipe 并通过完整解码：{current.get('artifact')}。",
        path=str(current.get("artifact") or ""),
        details={
            "selected": current.get("artifact"),
            "selected_sha256": current.get("artifact_sha256"),
            "duration_sec": probe.get("duration_sec"),
            "spec_sha256": receipt.get("spec_sha256"),
            "recipe": receipt.get("recipe"),
            "validator_version": receipt.get("validator_version"),
        },
    )


def check_creative_watchdown(root: Path, episode: str) -> Dict[str, Any]:
    if creative_watchdown_mod is None:
        return component("creative_watchdown", "block", "creative_watchdown validator 不可用。")
    path = creative_watchdown_mod.receipt_path(root, episode)
    canonical = acceptance_contract.resolve_final_master(root, episode)
    if canonical is None:
        return component(
            "creative_watchdown", "block", "缺 canonical final master，无法进行整片听看校验。",
            path=relpath(root, path),
        )
    result = creative_watchdown_mod.validate_watchdown(root, episode, master=canonical)
    if result.get("status") != "pass":
        return component(
            "creative_watchdown", "block",
            "current canonical master 尚无完整、hash-bound 的创作听看收据。",
            path=relpath(root, path), details={"issues": result.get("issues") or []},
        )
    return component(
        "creative_watchdown", "pass",
        "整片故事表演/视觉连续性/对白声音/节奏听看已绑定当前 canonical SHA；不冒充最终用户验收。",
        path=relpath(root, path), details={"final_user_acceptance": False},
    )


def check_release_evidence_freshness(root: Path, episode: str) -> Dict[str, Any]:
    masters = _final_master_files(root, episode)
    if not masters:
        return component("release_evidence_freshness", "block", "缺最终母版；无法证明 score/ledger/review-ui/配方证据新鲜。")
    selected_master = acceptance_contract.resolve_final_master(root, episode)
    assert selected_master is not None
    latest_master_mtime = selected_master.stat().st_mtime
    prod = production_dir(root)
    evidence = [
        prod / f"score_{episode}.json",
        prod / f"consistency_ledger_{episode}.json",
        prod / f"review_ui_{episode}.json",
        prod / f"review_ui_findings_{episode}.json",
        prod / f"generation_recipe_manifest_{episode}.json",
    ]
    stale = []
    missing = []
    for path in evidence:
        if not path.is_file():
            missing.append(relpath(root, path))
            continue
        if path.stat().st_mtime < latest_master_mtime:
            stale.append(relpath(root, path))
    if missing or stale:
        return component(
            "release_evidence_freshness",
            "block",
            "最终母版晚于部分发布证据；旧证据不能证明当前成片。",
            details={"masters": _master_details(root, masters), "missing": missing, "stale": stale},
        )
    return component("release_evidence_freshness", "pass", "发布证据晚于最终母版，时序新鲜。", details={"masters": _master_details(root, masters)})


def _pilot_path(root: Path, episode: str) -> Path:
    return production_dir(root) / f"pilot_acceptance_{episode}.json"


def check_pilot(root: Path, episode: str) -> Dict[str, Any]:
    if normalize_episode(episode) != "第1集":
        return component("pilot_release_gate", "pass", "非首集，不要求本集 pilot signoff。")
    path = _pilot_path(root, episode)
    data = load_json(path)
    if not isinstance(data, dict):
        return component("pilot_release_gate", "block", "首集缺 pilot_acceptance_<集>.json；先用 2-3 个代表镜头验证脸/场景/动作/口型/接缝/路由。", path=relpath(root, path))
    status = str(data.get("status") or data.get("verdict") or "").strip().lower()
    clips = data.get("clips") if isinstance(data.get("clips"), list) else []
    coverage = set(str(x).strip().lower() for x in (data.get("coverage") or []))
    missing = sorted(PILOT_REQUIRED_COVERAGE - coverage)
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    bad_checks = [k for k in sorted(PILOT_REQUIRED_COVERAGE) if str(checks.get(k) or "").strip().lower() not in {"pass", "ok", "accepted"}]
    evidence_issues = preventive_contracts.pilot_acceptance_evidence_issues(root, data)
    if status not in {"pass", "accepted", "green"} or len(clips) < 2 or missing or bad_checks or evidence_issues:
        return component(
            "pilot_release_gate",
            "block",
            f"首集 pilot 未放行：status={status or 'unset'}, clips={len(clips)}, "
            f"missing_coverage={missing}, checks_not_pass={bad_checks}, evidence_issues={len(evidence_issues)}。",
            path=relpath(root, path),
            details={"evidence_issues": evidence_issues[:12]},
        )
    return component("pilot_release_gate", "pass", f"首集 pilot 通过：clips={len(clips)}。", path=relpath(root, path))


def check_taxonomy(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    payload = failure_taxonomy.build_taxonomy(root, episode, profile=profile)
    status = payload.get("status")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if status == "blocked":
        return component("failure_taxonomy", "block", f"report-only findings 升级为 block：{summary.get('escalated_blocks', 0)} 条。", details=payload.get("items", [])[:5])
    if status == "warn":
        return component("failure_taxonomy", "warn", f"存在 findings={summary.get('findings', 0)} 条，但未升级 block。", details=summary)
    return component("failure_taxonomy", "pass", "未发现需要回流的问题。")


def _strict_release_context(root: Path, profile: str) -> bool:
    prof = str(profile or "").strip().lower()
    intent, _, _ = compliance_intent(root)
    if prof in STRICT_PROFILES:
        return True
    if intent and intent not in {"internal_only", "internal", "demo", "demo_only", "research", "private"}:
        return True
    return False


def _report_component(name: str, payload: Mapping[str, Any], *, strict: bool, pass_message: str, warn_message: str, block_message: str) -> Dict[str, Any]:
    status = str(payload.get("status") or "").strip().lower()
    if status in {"pass", "ok"}:
        return component(name, "pass", pass_message, details={"summary": payload.get("summary")})
    return component(name, "block" if strict else "warn", block_message if strict else warn_message, details=payload)


def check_contract_trace(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    payload = contract_trace.build_report(root, episode)
    return _report_component(
        "contract_trace",
        payload,
        strict=_strict_release_context(root, profile),
        pass_message="源理解 trace_id 已贯通到每集合同/分镜/生成证据/镜头产物。",
        warn_message="源理解 trace_id 未完全贯通；demo/internal 可继续，但 production 不能只靠 confirmed。",
        block_message="源理解 trace_id 未完全贯通；production 发布前必须证明承诺/伏笔/因果被下游消费。",
    )


def check_mini_pilot(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    payload = pilot_risk_sampler.build_report(root, episode)
    risks = int((payload.get("summary") or {}).get("risk_clips") or 0)
    if risks == 0:
        return component("mini_pilot", "pass", "未发现需额外 mini-pilot 的新/高风险条件。", details={"summary": payload.get("summary")})
    return _report_component(
        "mini_pilot",
        payload,
        strict=_strict_release_context(root, profile),
        pass_message=f"mini-pilot 已覆盖本集新/高风险条件：risk_clips={risks}。",
        warn_message=f"本集有 {risks} 个新/高风险代表镜头缺 mini-pilot；demo/internal 可继续，放量前必须补。",
        block_message=f"本集有 {risks} 个新/高风险代表镜头缺 mini-pilot；不能进入 production/批量发布。",
    )


def check_identity_drift(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    """跨集身份漂移证据（2026-07 实跑痛点回修）。

    run.py 日常路由用 --skip-face 只刷骨架（省钱正确）；但此前**没有任何环节要求交付前跑过
    一次全量报告**——实证某片 identity_drift_report available=False（skip-face 空壳）直接过验收，
    跨集脸漂 0.04 的 medium 信号无人消费。strict 档要求 available=true 的真实报告。"""
    path = production_dir(root) / "identity_drift_report.json"
    data = load_json(path)
    strict = _strict_release_context(root, profile)
    if not isinstance(data, dict):
        return component(
            "identity_drift",
            "warn" if strict else "pass",
            "缺 identity_drift_report.json——跨集身份漂移未核过；"
            "strict 发布前跑 python3 skills/n2d/n2d-identity/scripts/identity.py <作品根> --write（不带 --skip-face）。"
            if strict else "identity_drift_report 未生成（demo/单集可接受）。",
            path=relpath(root, path),
        )
    if data.get("available") is not True:
        notes = "；".join(str(n) for n in (data.get("notes") or [])[:2])
        return component(
            "identity_drift",
            "block" if strict else "warn",
            f"identity_drift_report 是 --skip-face 骨架（available=false{f'：{notes}' if notes else ''}）——"
            "空壳不算证据；交付边界前必须跑一次全量脸漂移报告（identity.py --write，不带 --skip-face）。",
            path=relpath(root, path),
        )
    return component("identity_drift", "pass", "跨集身份漂移报告可用。", path=relpath(root, path))


def check_stop_loss(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    payload = stop_loss.build_report(root, episode=episode)
    if payload.get("status") == "critical":
        strict = _strict_release_context(root, profile)
        return component(
            "stop_loss",
            "block" if strict else "warn",
            "批量 stop-loss 阈值触发；先停线回合同层修复。" if strict else "批量 stop-loss 阈值触发；demo/internal 仅提示，放量前必须停线修复。",
            details=payload,
        )
    if payload.get("status") == "no_evidence":
        strict = _strict_release_context(root, profile)
        return component(
            "stop_loss",
            "warn" if strict else "pass",
            "stop-loss 无任何遥测证据（无 findings/事件账本/dashboard）——空账恒过≠核过；"
            "strict 发布前先跑一集真实生产把遥测建起来。" if strict else "stop-loss 暂无遥测证据（demo/internal 放行）。",
            details=payload,
        )
    return component("stop_loss", "pass", "批量 stop-loss 未触发。", details={"metrics": payload.get("metrics"), "thresholds": payload.get("thresholds")})


def check_audience_experience(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    payload = audience_experience.build_report(root, episode)
    status = str(payload.get("status") or "").lower()
    if status == "pass":
        return component("audience_experience", "pass", "观众体验 gate 通过：首钩/回报节奏/尾钩具备。", details={"summary": payload.get("summary")})
    strict = _strict_release_context(root, profile)
    if status == "blocked":
        return component("audience_experience", "block" if strict else "warn", "观众体验 gate 阻断：前3秒钩子、兑现/回报或尾钩不足。" if strict else "观众体验 gate 有硬缺口；demo/internal 可看样，production 必须先修。", details=payload)
    return component("audience_experience", "warn", "观众体验 gate 有 warn：可能制作没错但不想追。", details=payload)


def _real(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return not PLACEHOLDER_RE.search(text) and text.lower() not in {"todo", "pending", "xxx", "n/a?"}


def _done(value: Any) -> bool:
    return str(value or "").strip().lower() in {"done", "pass", "ready", "approved", "not_applicable", "ok", "已完成", "通过"}


def check_release_profile(root: Path, episode: str, profile: str) -> Dict[str, Any]:
    profile_key = "commercial" if str(profile or "").lower() == "production" else str(profile or "demo").lower()
    intent, data, path = compliance_intent(root)
    if not isinstance(data, dict):
        return component("release_profile", "block", "缺 compliance_manifest.json，无法按地区/用途裁决。", path=relpath(root, path))

    issues: List[Dict[str, Any]] = []
    ai = data.get("ai_labeling") if isinstance(data.get("ai_labeling"), dict) else {}
    label = ai.get("explicit_label") if isinstance(ai.get("explicit_label"), dict) else {}
    meta = ai.get("implicit_metadata") if isinstance(ai.get("implicit_metadata"), dict) else {}
    targets = (data.get("platform_review") or {}).get("targets") if isinstance(data.get("platform_review"), dict) else []
    targets = [t for t in targets or [] if isinstance(t, dict)]
    reg = data.get("regulatory_filing") if isinstance(data.get("regulatory_filing"), dict) else {}
    rights = data.get("rights") if isinstance(data.get("rights"), dict) else {}

    def add(sev: str, code: str, message: str) -> None:
        issues.append({"severity": sev, "code": code, "message": message})

    if profile_key == "cn_public":
        cn_targets = [t for t in targets if str(t.get("region") or "").upper() in {"CN", "CHINA", "中国"}]
        if not cn_targets:
            add("block", "missing_cn_target", "中国公开发布 profile 必须有 CN platform_review target。")
        if str(label.get("status") or "").lower() != "done":
            add("block", "explicit_ai_label_not_done", "中国公开发布必须确认显式 AI 标识已落成片。")
        if meta.get("applied") is not True:
            add("block", "implicit_ai_metadata_not_applied", "中国公开发布必须确认隐式元数据/标识已应用。")
        if reg.get("applicable") is not False:
            if not _done(reg.get("pre_broadcast_review")):
                add("block", "pre_broadcast_review_not_done", "境内公开/投放须完成播前审核。")
            if not _real(reg.get("release_filing_no")):
                add("block", "missing_release_filing_no", "境内公开/投放须有上线备案号或写明不适用理由。")
            if not _done(reg.get("platform_human_review")):
                add("warn", "platform_human_review_not_done", "平台逐集人工终审未确认。")
    elif profile_key == "overseas":
        overseas_targets = [t for t in targets if str(t.get("region") or "").upper() not in {"CN", "CHINA", "中国", ""} or t.get("requires_localization") is True]
        if not overseas_targets:
            add("block", "missing_overseas_target", "海外发布 profile 必须有非 CN target 或 requires_localization=true。")
        localization = data.get("localization") if isinstance(data.get("localization"), dict) else {}
        if overseas_targets and not _done(localization.get("status")):
            add("block", "localization_not_ready", "海外发布必须完成本地化/字幕语言策略。")
        if not _real(label.get("text")):
            add("warn", "ai_disclosure_text_missing", "海外发布建议保留 AI 内容披露文案。")
    elif profile_key == "commercial":
        for key, row in rights.items():
            if isinstance(row, dict) and str(row.get("status") or "") not in {"not_applicable", "original"} and not _real(row.get("evidence")):
                add("block", f"rights_{key}_evidence_missing", f"商业发行缺 rights.{key}.evidence。")
        authorship = data.get("human_authorship") or data.get("copyright_human_authorship")
        if not _real(authorship):
            add("warn", "human_authorship_manifest_missing", "商业/版权登记候选建议补 human_authorship：说明人类作者表达不只是一句 prompt。")
    elif profile_key in INTERNAL_PROFILES:
        return component("release_profile", "pass", f"发行 profile=internal；公开/投放域不作为发布通过条件，授权域仍由 compliance 组件裁决。", path=relpath(root, path), details={"distribution_intent": intent})
    else:
        # demo profile: only surface profile matrix, do not block.
        return component("release_profile", "pass", f"发行 profile=demo；正式发布请改 cn_public/overseas/commercial 复核。", path=relpath(root, path), details={"distribution_intent": intent})

    blocks = [i for i in issues if i["severity"] == "block"]
    warns = [i for i in issues if i["severity"] == "warn"]
    if blocks:
        return component("release_profile", "block", f"发行 profile={profile_key} 字段级阻断：block={len(blocks)}, warn={len(warns)}。", path=relpath(root, path), details={"issues": issues})
    if warns:
        return component("release_profile", "warn", f"发行 profile={profile_key} 有待办：warn={len(warns)}。", path=relpath(root, path), details={"issues": issues})
    return component("release_profile", "pass", f"发行 profile={profile_key} 通过。", path=relpath(root, path), details={"distribution_intent": intent})


def final_status(components: Sequence[Mapping[str, Any]], root: Path, profile: str) -> str:
    if any(c.get("status") == "block" for c in components):
        return "blocked"
    intent, _, _ = compliance_intent(root)
    prof = str(profile or "").strip().lower()
    if prof in INTERNAL_PROFILES or (intent == "internal_only" and prof in DEMO_PROFILES):
        return "internal-only"
    if any(c.get("status") == "warn" for c in components):
        return "demo-only"
    return "pass"


def build_components(root: Path, episode: str, profile: str) -> List[Dict[str, Any]]:
    """Evaluate the existing release checks for one profile without writing state."""
    return [
        check_progress_dag(root, episode),
        check_production_handoff(root, episode),
        check_script_supervisor_log(root, episode),
        check_production_locks(root, episode),
        check_pilot(root, episode),
        check_mini_pilot(root, episode, profile),
        check_contract_trace(root, episode, profile),
        check_compliance(root, episode),
        check_release_profile(root, episode, profile),
        check_gate(root, episode),
        check_identity_drift(root, episode, profile),
        check_score(root, episode, profile),
        check_ledger(root, episode),
        check_review_ui(root, episode),
        check_image_qc(root, episode, profile),
        check_generation_recipe(root, episode),
        check_operational_evidence(root, episode, "event_ledger_audit", "production_events_audit.json"),
        check_operational_evidence(root, episode, "artifact_validation", "artifact_validation.json"),
        check_audience_experience(root, episode, profile),
        check_stop_loss(root, episode, profile),
        check_final_master(root, episode),
        check_creative_watchdown(root, episode),
        check_release_evidence_freshness(root, episode),
        check_taxonomy(root, episode, profile),
    ]


def _clip_delivery_coverage(root: Path, episode: str) -> Dict[str, Any]:
    storyboard = load_json(root / "脚本" / episode / "storyboard.json")
    clips = storyboard.get("clips") if isinstance(storyboard, dict) else []
    expected: set[str] = set()
    for index, row in enumerate(clips or [], 1):
        raw = str((row or {}).get("id") or (row or {}).get("clip") or f"Clip_{index:02d}") if isinstance(row, Mapping) else f"Clip_{index:02d}"
        match = re.search(r"Clip[_-]?(\d+)", raw, re.I)
        expected.add(f"Clip_{int(match.group(1)):02d}" if match else f"Clip_{index:02d}")
    present: set[str] = set()
    media_paths: List[str] = []
    for path in (root / "出视频" / episode / "视频").rglob("*.mp4") if (root / "出视频" / episode / "视频").is_dir() else []:
        match = re.search(r"Clip[_-]?(\d+)", path.name, re.I)
        if not match:
            continue
        cid = f"Clip_{int(match.group(1)):02d}"
        present.add(cid)
        media_paths.append(relpath(root, path))
    for path in production_dir(root).glob(f"video_batch_{episode}_*.json"):
        batch = load_json(path)
        if not isinstance(batch, dict):
            continue
        for item in batch.get("items") or []:
            if not isinstance(item, Mapping) or str(item.get("status") or "") not in {"accepted", "downloaded", "downloaded_existing_target"}:
                continue
            match = re.search(r"Clip[_-]?(\d+)", str(item.get("story_clip") or item.get("relay_parent") or item.get("clip") or ""), re.I)
            if match:
                present.add(f"Clip_{int(match.group(1)):02d}")
    missing = sorted(expected - present)
    complete = bool(expected) and not missing
    return {
        "complete": complete,
        "status": "complete" if complete else ("not_started" if not present else "incomplete"),
        "expected": sorted(expected),
        "present": sorted(expected & present),
        "missing": missing,
        "media_paths": sorted(media_paths),
    }


def _state_from_components(profile: str, components: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    blockers = [
        {"name": row.get("name"), "status": row.get("status"), "message": row.get("message")}
        for row in components if row.get("status") != "pass"
    ]
    ready = not blockers
    return {
        "complete": ready,
        "status": "complete" if ready else "blocked",
        "profile": profile,
        "blockers": blockers,
    }


def delivery_state_matrix(
    root: Path,
    episode: str,
    requested_profile: str,
    requested_components: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Separate production delivery from public/commercial publication readiness.

    Public AI labels, filing and platform review may block publish readiness but
    cannot retroactively make a technically accepted clip/master nonexistent.
    Rights/label compliance remains fully enforced in each publication profile.
    """
    clip_state = _clip_delivery_coverage(root, episode)
    internal_components = (
        list(requested_components)
        if str(requested_profile).lower() in INTERNAL_PROFILES
        else build_components(root, episode, "internal")
    )
    publication_only = {"compliance", "release_profile", "release_evidence_freshness"}
    technical_blockers = [
        {"name": row.get("name"), "status": row.get("status"), "message": row.get("message")}
        for row in internal_components
        if row.get("name") not in publication_only and row.get("status") == "block"
    ]
    final_master = next((row for row in internal_components if row.get("name") == "final_master"), {})
    master_complete = clip_state["complete"] and final_master.get("status") == "pass" and not technical_blockers
    master_technical_state = {
        "complete": master_complete,
        "status": "complete" if master_complete else "incomplete",
        "blockers": technical_blockers + ([] if final_master.get("status") == "pass" else [{
            "name": "final_master", "status": final_master.get("status") or "missing", "message": final_master.get("message") or "final master missing",
        }]),
        "publication_labels_required": False,
    }
    master_delivery_state = {
        **master_technical_state,
        "complete": False,
        "status": "pending_acceptance" if master_complete else "incomplete",
        "technical_complete": master_complete,
        "acceptance_required": True,
        "definition": "canonical completion is adjudicated only by release_verdict + fresh acceptance_receipt",
    }
    profile_components: Dict[str, Sequence[Mapping[str, Any]]] = {}
    normalized_requested = "commercial" if str(requested_profile).lower() == "production" else str(requested_profile).lower()
    for target in ("cn_public", "overseas", "commercial"):
        profile_components[target] = (
            requested_components if normalized_requested == target else build_components(root, episode, target)
        )
    publish = {target: _state_from_components(target, rows) for target, rows in profile_components.items()}
    current_publish = publish.get(normalized_requested) if normalized_requested in publish else {
        "complete": False,
        "status": "not_evaluated_for_internal_or_demo",
        "profile": normalized_requested or "demo",
        "blockers": [],
    }
    return {
        "clip_delivery_complete": clip_state,
        "master_technical_complete": master_technical_state,
        "master_delivery_complete": master_delivery_state,
        "production_complete": {
            **master_delivery_state,
            "definition": "technical master complete + canonical human acceptance receipt; verdict alone can never assert completion",
        },
        "publish_ready_cn": publish["cn_public"],
        "publish_ready_overseas": publish["overseas"],
        "publish_ready_commercial": publish["commercial"],
        "publish_ready_current_profile": current_publish,
        "separation_rule": "delivery completion excludes public AI-label/filing/platform fields; publication readiness never does",
    }


def build_verdict(root: Path, episode: str, *, profile: str = "demo") -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    components = build_components(root, episode, profile)
    status = final_status(components, root, profile)
    delivery_states = delivery_state_matrix(root, episode, profile, components)
    # Freeze the exact evidence set adjudicated by this verdict.  The later
    # human acceptance receipt must bind these same hashes plus this verdict's
    # own hash; a regenerated master/score/ledger/review UI can never inherit an
    # older approval by filename or mtime alone.
    evidence_bindings = acceptance_contract.current_evidence_bindings(root, episode)
    content_fingerprint = acceptance_contract.release_content_fingerprint(root, episode, profile)
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
        "delivery_states": delivery_states,
        "evidence_bindings": evidence_bindings,
        "content_fingerprint": content_fingerprint,
        "acceptance_contract": {
            "required": True,
            "receipt_path": relpath(root, acceptance_contract.receipt_path(root, episode)),
            "allowed_decisions": sorted(acceptance_contract.ALLOWED_DECISIONS),
            "completion_rule": "release verdict is acceptable AND canonical acceptance receipt is present, hash-bound and fresh",
        },
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
        f"- clip delivery：{((payload.get('delivery_states') or {}).get('clip_delivery_complete') or {}).get('status')}",
        f"- master delivery：{((payload.get('delivery_states') or {}).get('master_delivery_complete') or {}).get('status')}",
        f"- publish ready（当前 profile）：{((payload.get('delivery_states') or {}).get('publish_ready_current_profile') or {}).get('status')}",
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
    if _record_flow_milestone is not None:
        try:
            states = payload.get("delivery_states") if isinstance(payload.get("delivery_states"), Mapping) else {}
            current = states.get("publish_ready_current_profile") if isinstance(states, Mapping) else {}
            _record_flow_milestone(
                root, "release_verdict_evaluated", episode=episode, stage="review",
                extra={
                    "status": payload.get("status"), "profile": payload.get("profile"),
                    "clip_delivery_complete": bool((states.get("clip_delivery_complete") or {}).get("complete")),
                    "master_delivery_complete": bool((states.get("master_delivery_complete") or {}).get("complete")),
                    "publish_ready": bool((current or {}).get("complete")),
                    "artifact": relpath(root, json_path),
                },
            )
        except Exception:
            pass
    return {"json": relpath(root, json_path), "markdown": relpath(root, md_path)}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="aggregate n2d release verdict")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--profile", choices=["demo", "production", "internal", "cn_public", "overseas", "commercial"], default="demo")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    if ns.json:
        # Imported legacy checks may still emit human diagnostics (notably progress.py when
        # `_progress.md` is absent).  JSON mode is a machine contract: preserve those messages
        # on stderr while guaranteeing that stdout contains exactly one JSON document.
        diagnostics = io.StringIO()
        try:
            with contextlib.redirect_stdout(diagnostics):
                payload = build_verdict(root, ns.episode, profile=ns.profile)
                if ns.write:
                    payload["outputs"] = write_outputs(root, payload["episode"], payload)
        finally:
            captured = diagnostics.getvalue()
            if captured:
                sys.stderr.write(captured)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        payload = build_verdict(root, ns.episode, profile=ns.profile)
        if ns.write:
            payload["outputs"] = write_outputs(root, payload["episode"], payload)
        print(render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
