#!/usr/bin/env python3
"""Production lock ledger for n2d.

Traditional productions avoid runaway rework through explicit lock points:
script lock, storyboard lock, picture lock, delivery lock, etc.  This script
records those lock points with artifact hashes, approver, unlock protocol and
affected departments.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
N2D_DIR = SCRIPT_DIR.parents[0]
LIB = N2D_DIR / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # type: ignore
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore


KIND = "n2d_production_locks"
CHECK_KIND = "n2d_production_locks_check"
VERSION = 1
LOCK_FILE = "production_locks_{episode}.json"

LOCK_POINTS: Tuple[Tuple[str, str, Tuple[str, ...], Tuple[str, ...]], ...] = (
    ("source_lock", "源理解锁", ("设定库/source_comprehension.json", "小说/_源指纹.json"), ("writer", "producer")),
    ("script_lock", "剧本锁", ("脚本/{ep}/voiceover.txt", "脚本/{ep}/bgm.txt", "生产数据/script_quality_contract_{ep}.json"), ("writer", "director", "producer")),
    ("storyboard_lock", "分镜锁", ("脚本/{ep}/storyboard.json", "脚本/{ep}/镜头时长.json", "脚本/{ep}/director_blocking_pack.json"), ("director", "script_supervisor", "producer")),
    ("style_identity_lock", "风格身份锁", ("_设置.md", "设定库/global_style.md", "出图/共享/identity_registry.json", "生产数据/identity_adapter_matrix.json"), ("director", "art_director", "identity_supervisor")),
    ("voice_timing_lock", "声音时长锁", ("合成/{ep}/配音/时长清单.json", "合成/{ep}/配音/voice_zh.wav"), ("voice_director", "editor")),
    ("video_material_lock", "视频素材锁", ("出视频/{ep}/视频", "出视频/{ep}/prompt/video_model_routes.json", "生产数据/image_qc/{ep}/image_qc_{ep}.json", "生产数据/video_qc_{ep}.json"), ("director", "editor", "qc")),
    ("rough_cut_lock", "粗剪时间线锁", ("合成/{ep}/_work/timeline.json", "合成/{ep}/rough_cut_preview.html", "生产数据/final_timeline_probe_{ep}.json"), ("director", "editor", "post_supervisor")),
    ("picture_lock", "最终画面锁", ("合成/{ep}/成片*.mp4", "生产数据/final_timeline_probe_{ep}.json", "生产数据/script_supervisor_log_{ep}.jsonl"), ("director", "editor", "qc")),
    ("delivery_lock", "交付母版锁", ("合成/{ep}", "合规/release_manifest_{ep}.json", "生产数据/release_verdict_{ep}.json"), ("producer", "post_supervisor", "compliance")),
)

LOCK_POINT_IDS = tuple(row[0] for row in LOCK_POINTS)
LOCK_POINT_BY_ID = {row[0]: row for row in LOCK_POINTS}

# Stage-scoped checks keep lock enforcement near the work it protects.  The full
# ledger still records every lock point; production entrypoints ask only for the
# subset that must already be stable at that stage.
STAGE_LOCK_IDS: Mapping[str, Tuple[str, ...]] = {
    "script_stage2": ("source_lock", "script_lock"),
    "image_prompt": ("source_lock", "script_lock", "storyboard_lock"),
    "image": ("source_lock", "script_lock", "storyboard_lock", "style_identity_lock"),
    "video_prompt": ("source_lock", "script_lock", "storyboard_lock", "style_identity_lock", "voice_timing_lock"),
    "video": ("source_lock", "script_lock", "storyboard_lock", "style_identity_lock", "voice_timing_lock"),
    "compose": ("source_lock", "script_lock", "storyboard_lock", "style_identity_lock", "voice_timing_lock", "video_material_lock"),
    "review": ("source_lock", "script_lock", "storyboard_lock", "style_identity_lock", "voice_timing_lock", "video_material_lock", "rough_cut_lock", "picture_lock"),
    "release": LOCK_POINT_IDS,
}

STAGE_ALIASES = {
    "image_prompt_preflight": "image_prompt",
    "image_preflight": "image",
    "video_prompt_preflight": "video_prompt",
    "video_preflight": "video_prompt",
    "review_acceptance": "review",
    "post_compose_review": "review",
}

MATERIALIZED_REQUIRED_LOCK_IDS = {"style_identity_lock", "video_material_lock", "rough_cut_lock", "picture_lock"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expand_artifact_paths(root: Path, ep: str, pattern: str) -> List[Path]:
    rel = pattern.format(ep=ep)
    base = root / rel
    if any(ch in rel for ch in "*?[]"):
        matches = [Path(p) for p in sorted(glob.glob(str(base)))]
        return matches or [base]
    if base.is_dir():
        return [p for p in sorted(base.rglob("*")) if p.is_file()]
    return [base]


def artifact_rows(root: Path, ep: str, patterns: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pattern in patterns:
        paths = expand_artifact_paths(root, ep, pattern)
        if len(paths) == 1 and not paths[0].exists():
            rows.append({"path": pattern.format(ep=ep), "exists": False, "sha256": ""})
            continue
        for path in paths:
            if path.is_file():
                rows.append({
                    "path": relpath(root, path),
                    "exists": True,
                    "sha256": sha256_file(path),
                    "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).replace(microsecond=0).isoformat(),
                })
    return rows


def lock_path(root: Path, ep: str) -> Path:
    return production_dir(root) / LOCK_FILE.format(episode=ep)


def normalize_stage(stage: str | None) -> str:
    value = str(stage or "").strip()
    return STAGE_ALIASES.get(value, value)


def stage_lock_ids(stage: str | None) -> Tuple[str, ...]:
    stage_key = normalize_stage(stage)
    if not stage_key:
        return LOCK_POINT_IDS
    return STAGE_LOCK_IDS.get(stage_key, ())


def build_ledger(root: Path, ep: str, *, confirmed: bool = False, reviewer: str = "") -> Dict[str, Any]:
    ep = normalize_episode(ep)
    locks: List[Dict[str, Any]] = []
    for key, label, patterns, approvers in LOCK_POINTS:
        artifacts = artifact_rows(root, ep, patterns)
        existing = [a for a in artifacts if a.get("exists")]
        locks.append({
            "lock_id": key,
            "label": label,
            "episode": ep,
            "status": "confirmed" if confirmed else "draft",
            "approver": reviewer if confirmed else "",
            "approved_at": now_iso() if confirmed else "",
            "required_approver_roles": list(approvers),
            "artifacts": artifacts,
            "artifact_count": len(existing),
            "missing_artifacts": [a["path"] for a in artifacts if not a.get("exists")],
            "unlock_protocol": {
                "requires_reason": True,
                "requires_affected_stage_list": True,
                "record_in": "生产数据/creative_decisions.jsonl",
                "then": "用 n2d-batch 只排受影响镜头/阶段，不整集无账重跑",
            },
            "affected_departments": list(dict.fromkeys(approvers + ("batch", "dashboard"))),
        })
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "locks": locks,
        "notes": [
            "confirmed 表示锁定的是当前 hash；后续文件变化会由 check 标 stale。",
            "解锁必须写 creative_decisions.jsonl，并列出最小返工范围。",
        ],
    }


def write_ledger(root: Path, ep: str, payload: Mapping[str, Any]) -> Path:
    path = lock_path(root, normalize_episode(ep))
    write_json(path, payload)
    return path


def scaffold(root: Path, ep: str, *, confirmed: bool = False, reviewer: str = "", force: bool = False) -> Dict[str, Any]:
    path = lock_path(root, normalize_episode(ep))
    if path.exists() and not force:
        return {"kind": KIND, "episode": normalize_episode(ep), "status": "exists", "path": str(path)}
    payload = build_ledger(root, ep, confirmed=confirmed, reviewer=reviewer)
    write_ledger(root, ep, payload)
    return {"kind": KIND, "episode": normalize_episode(ep), "status": "written", "path": str(path)}


def _selected_lock_ids(stage: str | None = None, lock_ids: Sequence[str] | None = None) -> Tuple[str, ...]:
    explicit = [str(x or "").strip() for x in (lock_ids or []) if str(x or "").strip()]
    if any(x == "all" for x in explicit):
        return LOCK_POINT_IDS
    selected: List[str] = []
    if stage:
        scoped = stage_lock_ids(stage)
        if not scoped:
            raise ValueError(f"未知锁版阶段：{stage}")
        selected.extend(scoped)
    selected.extend(explicit)
    if not selected:
        selected.extend(LOCK_POINT_IDS)
    unknown = [x for x in selected if x not in LOCK_POINT_BY_ID]
    if unknown:
        raise ValueError(f"未知锁点：{', '.join(unknown)}")
    return tuple(dict.fromkeys(selected))


def confirm_locks(root: Path, ep: str, *, stage: str | None = None, lock_ids: Sequence[str] | None = None,
                  reviewer: str = "", write_check: bool = False) -> Dict[str, Any]:
    ep = normalize_episode(ep)
    stage_key = normalize_stage(stage)
    selected_ids = _selected_lock_ids(stage_key, lock_ids)
    existing = load_json(lock_path(root, ep))
    if not isinstance(existing, Mapping):
        existing = build_ledger(root, ep)
    current_confirmed = build_ledger(root, ep, confirmed=True, reviewer=reviewer or "codex")
    current_draft = build_ledger(root, ep)
    confirmed_by_id = {
        str(lock.get("lock_id")): lock
        for lock in current_confirmed.get("locks", [])
        if isinstance(lock, Mapping)
    }
    draft_by_id = {
        str(lock.get("lock_id")): lock
        for lock in current_draft.get("locks", [])
        if isinstance(lock, Mapping)
    }
    old_by_id = {
        str(lock.get("lock_id")): lock
        for lock in existing.get("locks", [])
        if isinstance(lock, Mapping)
    }
    locks: List[Dict[str, Any]] = []
    for lock_id in LOCK_POINT_IDS:
        if lock_id in selected_ids:
            locks.append(dict(confirmed_by_id[lock_id]))
        else:
            locks.append(dict(old_by_id.get(lock_id) or draft_by_id[lock_id]))
    all_confirmed = all(str(lock.get("status") or "").lower() == "confirmed" for lock in locks)
    payload = dict(existing)
    payload.update({
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if all_confirmed else "draft",
        "updated_at": now_iso(),
        "last_confirmed_at": now_iso(),
        "last_confirmed_by": reviewer or "codex",
        "last_confirmed_lock_ids": list(selected_ids),
        "locks": locks,
    })
    path = write_ledger(root, ep, payload)
    check = check_ledger(root, ep, stage=stage_key, write_check=write_check)
    return {
        "kind": KIND,
        "episode": ep,
        "status": check.get("status"),
        "path": str(path),
        "confirmed_lock_ids": list(selected_ids),
        "check": check,
    }


def check_ledger(root: Path, ep: str, *, write_missing: bool = False, stage: str | None = None,
                 write_check: bool = False) -> Dict[str, Any]:
    ep = normalize_episode(ep)
    stage_key = normalize_stage(stage)
    selected_ids = stage_lock_ids(stage_key)
    path = lock_path(root, ep)
    if write_missing and not path.exists():
        scaffold(root, ep)
    data = load_json(path)
    findings: List[Dict[str, Any]] = []
    if stage_key and not selected_ids:
        findings.append({"severity": "block", "code": "unknown_lock_stage", "stage": stage_key, "message": f"未知锁版阶段：{stage_key}"})
        selected_ids = LOCK_POINT_IDS
    if not isinstance(data, Mapping):
        findings.append({"severity": "block", "code": "missing_lock_ledger", "message": f"缺锁版账：{relpath(root, path)}"})
        data = {}
    locks = data.get("locks") if isinstance(data.get("locks"), list) else []
    current_by_id = {row[0]: artifact_rows(root, ep, row[2]) for row in LOCK_POINTS if row[0] in selected_ids}
    for lock in locks:
        if not isinstance(lock, Mapping):
            continue
        lock_id = str(lock.get("lock_id") or "")
        if lock_id not in selected_ids:
            continue
        status = str(lock.get("status") or "").lower()
        if status != "confirmed":
            findings.append({"severity": "block", "code": "lock_not_confirmed", "lock_id": lock_id, "message": f"{lock_id} status 不是 confirmed"})
        old = {a.get("path"): a.get("sha256") for a in lock.get("artifacts") or [] if isinstance(a, Mapping) and a.get("exists")}
        cur = {a.get("path"): a.get("sha256") for a in current_by_id.get(lock_id, []) if a.get("exists")}
        stale = [p for p, digest in old.items() if cur.get(p) and cur.get(p) != digest]
        missing_now = [p for p in old if p not in cur]
        missing_required = [
            a.get("path")
            for a in current_by_id.get(lock_id, [])
            if lock_id in MATERIALIZED_REQUIRED_LOCK_IDS and not a.get("exists")
        ]
        if stale:
            findings.append({"severity": "block", "code": "lock_artifact_stale", "lock_id": lock_id, "message": f"{lock_id} 锁定后文件已变化：{', '.join(stale[:5])}", "artifacts": stale})
        if missing_now:
            findings.append({"severity": "block", "code": "lock_artifact_missing", "lock_id": lock_id, "message": f"{lock_id} 锁定文件已缺失：{', '.join(missing_now[:5])}", "artifacts": missing_now})
        if missing_required:
            findings.append({"severity": "block", "code": "lock_required_artifact_missing", "lock_id": lock_id, "message": f"{lock_id} 缺必需实体产物：{', '.join(str(p) for p in missing_required[:5])}", "artifacts": missing_required})
    seen = {str(lock.get("lock_id")) for lock in locks if isinstance(lock, Mapping) and str(lock.get("lock_id")) in selected_ids}
    for lock_id, _label, _patterns, _roles in LOCK_POINTS:
        if lock_id not in selected_ids:
            continue
        if lock_id not in seen:
            findings.append({"severity": "block", "code": "missing_lock_point", "lock_id": lock_id, "message": f"缺锁点 {lock_id}"})
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "episode": ep,
        "stage": stage_key or "all",
        "checked_lock_ids": list(selected_ids),
        "status": "pass" if not findings else "block",
        "generated_at": now_iso(),
        "lock_path": relpath(root, path),
        "summary": {"block": len(findings), "locks": len(seen), "required_locks": len(selected_ids)},
        "findings": findings,
    }
    stage_part = f"{stage_key}_" if stage_key else ""
    out = production_dir(root) / f"production_locks_check_{stage_part}{ep}.json"
    if write_check:
        write_json(out, payload)
        payload["check_path"] = str(out)
    else:
        payload["check_path_expected"] = str(out)
    return payload


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    sub = ap.add_subparsers(dest="command", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--confirm", action="store_true")
    p_scaffold.add_argument("--reviewer", default="")
    p_scaffold.add_argument("--force", action="store_true")
    p_confirm = sub.add_parser("confirm")
    p_confirm.add_argument("--stage", default="", help="confirm lock points required by this stage")
    p_confirm.add_argument("--lock-id", action="append", default=[], help="lock_id to confirm; repeatable, or use all")
    p_confirm.add_argument("--reviewer", default="codex")
    p_confirm.add_argument("--write-check", action="store_true", help="write production_locks_check_<stage>_<episode>.json")
    p_confirm.add_argument("--json", action="store_true")
    p_check = sub.add_parser("check")
    p_check.add_argument("--write-missing", action="store_true")
    p_check.add_argument("--write-check", action="store_true", help="write production_locks_check_<stage>_<episode>.json")
    p_check.add_argument("--stage", default="", help="limit check to lock points needed by this stage")
    p_check.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    if ns.command == "scaffold":
        payload = scaffold(root, ns.episode, confirmed=ns.confirm, reviewer=ns.reviewer, force=ns.force)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if ns.command == "confirm":
        try:
            payload = confirm_locks(root, ns.episode, stage=ns.stage, lock_ids=ns.lock_id,
                                    reviewer=ns.reviewer, write_check=ns.write_check)
        except ValueError as exc:
            print(json.dumps({"kind": KIND, "episode": normalize_episode(ns.episode), "status": "block", "error": str(exc)}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2) if ns.json else f"production locks confirm: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    payload = check_ledger(root, ns.episode, write_missing=ns.write_missing, stage=ns.stage,
                           write_check=ns.write_check or ns.write_missing)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if ns.json else f"production locks: {payload['status']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
