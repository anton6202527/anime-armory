#!/usr/bin/env python3
"""Build and accept the single SHA-bound completion verdict for a song release.

``release_pack.release_ready`` remains component evidence.  Only this module's
current digest plus a matching acceptance receipt may declare the release
complete.  The digest binds exact bytes so replacing any release input
invalidates the previous acceptance without relying on mtimes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = 1
KIND = "song_release_verdict"
VERDICT_REL = Path("生产数据") / "release_verdict.json"
ACCEPTANCE_REL = Path("生产数据") / "release_acceptance.json"
FORMAL_COVER_PROFILES = {"distribution", "streaming", "apple_digital_masters"}
AUTOMATED_REVIEWER_RE = re.compile(
    r"(?:^|[^a-z0-9])(agent|ai|assistant|automation|bot|chatgpt|claude|codex|delegate|listener|"
    r"machine|model|producer|supervisor|system)(?:[^a-z0-9]|$)|"
    r"^(?:代理|制作代理|自动化|机器人|模型|系统|系统代理|执行器)(?:$|[:：/#@])", re.I
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp.exists():
            tmp.unlink()


def is_human_reviewer(value: Any) -> bool:
    name = str(value or "").strip()
    return bool(name) and not AUTOMATED_REVIEWER_RE.search(name)


def _release_pack_module():
    path = Path(__file__).resolve().parents[1] / "song-craft" / "scripts" / "release_pack.py"
    spec = importlib.util.spec_from_file_location("song_release_pack_for_verdict", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load release pack module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _logical_pack(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: child for key, child in value.items() if key not in {"generated_at", "project_root"}}


def _record(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    return {"path": rel, "sha256": sha256_file(path), "size_bytes": path.stat().st_size if path.is_file() else None}


def build_verdict(root: Path) -> dict[str, Any]:
    root = root.resolve()
    pack_path = root / "导出" / "release_pack.json"
    stored_pack = load_json(pack_path, {}) or {}
    profile = str(stored_pack.get("release_profile") or "distribution")
    release_name = str(stored_pack.get("release_name") or "v1")
    required = {
        "release_pack": "导出/release_pack.json",
        "master": "导出/master.wav",
        "rights": "合规/rights_metadata.json",
        "rights_check": "合规/rights_metadata_check.json",
        "mix_signoff": "混音/mix_signoff.json",
        "pre_master": "混音/pre_master.wav",
    }
    if profile in FORMAL_COVER_PROFILES:
        required["cover_art"] = "导出/cover.jpg"
    inputs = {name: _record(root, rel) for name, rel in required.items()}
    if isinstance(stored_pack, Mapping) and stored_pack:
        inputs["release_pack"]["logical_sha256"] = canonical_sha256(_logical_pack(stored_pack))
    blockers: list[dict[str, str]] = []

    for name, row in inputs.items():
        if not row.get("sha256"):
            blockers.append({"code": f"{name}_missing", "message": f"缺当前字节：{row['path']}"})

    fresh_pack: Mapping[str, Any] = {}
    if isinstance(stored_pack, Mapping) and stored_pack:
        try:
            fresh_pack = _release_pack_module().build_pack(str(root), release_name, profile)
        except Exception as exc:
            blockers.append({"code": "release_pack_rebuild_failed", "message": f"无法重算 release pack：{exc}"})
        else:
            if canonical_sha256(_logical_pack(stored_pack)) != canonical_sha256(_logical_pack(fresh_pack)):
                blockers.append({"code": "release_pack_stale", "message": "release_pack 未绑定当前母版、权利、签收或封面字节"})
            if fresh_pack.get("release_ready") is not True:
                blockers.append({"code": "release_pack_not_ready", "message": "当前重算 release pack 仍有 blocker"})
    else:
        blockers.append({"code": "release_pack_missing", "message": "缺 导出/release_pack.json"})

    mix = load_json(root / "混音" / "mix_signoff.json", {}) or {}
    reviewer = str(mix.get("reviewer") or "").strip()
    if mix.get("passed") is not True:
        blockers.append({"code": "mix_signoff_not_passed", "message": "最终 mix signoff 未通过"})
    if not is_human_reviewer(reviewer):
        blockers.append({"code": "mix_signoff_not_human", "message": "最终 mix signoff 缺真实具名人"})
    if ((mix.get("audio") or {}).get("sha256") or "") != (inputs["pre_master"].get("sha256") or ""):
        blockers.append({"code": "mix_signoff_stale", "message": "mix signoff 未绑定当前 pre_master.wav"})

    digest_inputs = {name: dict(row) for name, row in inputs.items()}
    # release_pack contains generated_at/project_root diagnostics.  Its
    # semantic hash is authoritative so a clock-only rewrite cannot invalidate
    # a human acceptance; every production-bearing field and all exact media
    # bytes remain bound by the other records.
    if "release_pack" in digest_inputs:
        digest_inputs["release_pack"].pop("sha256", None)
        digest_inputs["release_pack"].pop("size_bytes", None)
    digest_payload = {
        "schema_version": SCHEMA_VERSION,
        "release_name": release_name,
        "release_profile": profile,
        "inputs": digest_inputs,
    }
    release_digest = canonical_sha256(digest_payload)
    acceptance = load_json(root / ACCEPTANCE_REL, {}) or {}
    acceptance_current = (
        not blockers
        and acceptance.get("kind") == "song_release_acceptance"
        and acceptance.get("release_digest") == release_digest
        and is_human_reviewer(acceptance.get("accepted_by"))
    )
    status = "blocked" if blockers else ("complete" if acceptance_current else "ready_for_acceptance")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "generated_at": now_iso(),
        "project_root": str(root),
        "release_name": release_name,
        "release_profile": profile,
        "release_digest": release_digest,
        "status": status,
        "complete": status == "complete",
        "component_release_ready": bool(fresh_pack.get("release_ready")) if fresh_pack else False,
        "inputs": inputs,
        "final_human_signoff": {"reviewer": reviewer, "current": not any(row["code"].startswith("mix_signoff") for row in blockers)},
        "acceptance": {
            "path": ACCEPTANCE_REL.as_posix(),
            "current": acceptance_current,
            "accepted_by": acceptance.get("accepted_by") or "",
            "accepted_at": acceptance.get("accepted_at") or "",
        },
        "blockers": blockers,
    }


def write_verdict(root: Path, verdict: Mapping[str, Any]) -> Path:
    out = root.resolve() / VERDICT_REL
    atomic_json(out, verdict)
    return out


def accept(root: Path, accepted_by: str = "") -> dict[str, Any]:
    root = root.resolve()
    verdict = build_verdict(root)
    if verdict["status"] == "blocked":
        raise ValueError("release verdict blocked: " + "; ".join(row["message"] for row in verdict["blockers"][:3]))
    reviewer = accepted_by.strip() or str((verdict.get("final_human_signoff") or {}).get("reviewer") or "").strip()
    if not is_human_reviewer(reviewer):
        raise ValueError("acceptance requires a real named human reviewer")
    receipt = {
        "schema_version": 1,
        "kind": "song_release_acceptance",
        "release_digest": verdict["release_digest"],
        "accepted_by": reviewer,
        "accepted_at": now_iso(),
    }
    atomic_json(root / ACCEPTANCE_REL, receipt)
    accepted = build_verdict(root)
    write_verdict(root, accepted)
    return accepted


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="song single SHA-bound release verdict")
    sub = ap.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("project_root")
    check.add_argument("--write", action="store_true")
    check.add_argument("--json", action="store_true")
    approve = sub.add_parser("accept")
    approve.add_argument("project_root")
    approve.add_argument("--accepted-by", default="", help="默认复用当前 mix_signoff 的真实 reviewer")
    approve.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    try:
        verdict = accept(root, ns.accepted_by) if ns.command == "accept" else build_verdict(root)
    except ValueError as exc:
        print(f"[block] {exc}")
        return 2
    if ns.command == "check" and ns.write:
        write_verdict(root, verdict)
    if ns.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(f"# song release status={verdict['status']} complete={verdict['complete']} digest={verdict['release_digest']}")
        for row in verdict["blockers"]:
            print(f"- BLOCK [{row['code']}] {row['message']}")
    return 0 if verdict["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
