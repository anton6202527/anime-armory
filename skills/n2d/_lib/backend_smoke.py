#!/usr/bin/env python3
"""Backend smoke evidence for n2d image/video adapters.

Refresh evidence says "current docs/API surface were checked"; smoke evidence
says "this project has a recent runnable proof for the backend route".  The
smoke may be a non-paid probe, a dry-run wrapper, or a manually recorded result
from a real provider-specific test.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:
    import image_backend_adapter
    import video_backend_adapter
except Exception:  # pragma: no cover
    from . import image_backend_adapter, video_backend_adapter  # type: ignore


KIND = "n2d_backend_smoke_evidence"
VERSION = 1
EVENT_KIND = "n2d_production_event"
EVENT_VERSION = 1
PASS_STATUSES = {"pass", "ok"}
FAIL_STATUSES = {"fail", "down", "error"}
DEFAULT_PROFILE = "basic"
SMOKE_PROFILES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "image": {
        "basic": {"required_capabilities": [], "description": "backend is reachable or has a real output asset"},
        "normal_motion": {"required_capabilities": [], "description": "image backend baseline generation/edit path"},
        "talking_closeup": {"required_capabilities": ["supports_image_reference"], "description": "close-up character reference path"},
        "frame_control": {"required_capabilities": ["supports_image_reference"], "description": "reference/frame handoff input path"},
    },
    "video": {
        "basic": {"required_capabilities": [], "description": "backend is reachable or has a real output asset"},
        "normal_motion": {"required_capabilities": ["supports_first_frame"], "description": "ordinary first-frame guided motion clip"},
        "talking_closeup": {"required_capabilities": ["native_av"], "description": "talking close-up / native speech capability"},
        "frame_control": {
            "required_capabilities": ["supports_first_frame"],
            "any_capability": ["supports_last_frame", "supports_native_mid_anchors", "max_reference_images"],
            "description": "first-last, native multi-frame, or reference-image control path",
        },
    },
}


def _slug(value: str) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^0-9a-zA-Z._-]+", "_", text)
    return text.strip("_") or "unknown"


def production_dir(root: str) -> Path:
    return Path(root) / "生产数据"


def smoke_dir(root: str) -> Path:
    return production_dir(root) / "backend_smoke"


def normalize_profile(profile: str = "") -> str:
    text = str(profile or DEFAULT_PROFILE).strip()
    return text or DEFAULT_PROFILE


def profile_spec(backend_kind: str, profile: str = "") -> Dict[str, Any]:
    return dict((SMOKE_PROFILES.get(backend_kind) or {}).get(normalize_profile(profile), {}))


def evidence_basename(kind: str, backend: str, channel: str = "", profile: str = DEFAULT_PROFILE) -> str:
    suffix = f"__via_{_slug(channel)}" if channel else ""
    profile_key = normalize_profile(profile)
    profile_suffix = "" if profile_key == DEFAULT_PROFILE else f"__profile_{_slug(profile_key)}"
    return f"{_slug(kind)}_{_slug(backend)}{suffix}{profile_suffix}"


def latest_path(root: str, kind: str, backend: str, channel: str = "", profile: str = DEFAULT_PROFILE) -> Path:
    return smoke_dir(root) / f"{evidence_basename(kind, backend, channel, profile)}_latest.json"


def dated_path(root: str, kind: str, backend: str, channel: str, date_s: str, profile: str = DEFAULT_PROFILE) -> Path:
    return smoke_dir(root) / f"{evidence_basename(kind, backend, channel, profile)}_{date_s}.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def evidence_id(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "capability_evidence_id"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()[:16]


def parse_capability(items: Sequence[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in items:
        if "=" not in str(item):
            raise ValueError(f"capability must be key=value: {item}")
        key, value = str(item).split("=", 1)
        key = key.strip()
        text = value.strip()
        low = text.lower()
        if low in {"true", "yes", "1", "是", "支持", "pass", "ok"}:
            out[key] = True
        elif low in {"false", "no", "0", "否", "不支持", "fail"}:
            out[key] = False
        else:
            out[key] = text
    return out


def write_payload(root: str, payload: Dict[str, Any]) -> Path:
    date_s = str(payload.get("checked_at") or dt.date.today().isoformat())[:10]
    profile = normalize_profile(str(payload.get("smoke_profile") or DEFAULT_PROFILE))
    path = dated_path(root, payload["backend_kind"], payload["backend"], payload.get("channel", ""), date_s, profile)
    latest = latest_path(root, payload["backend_kind"], payload["backend"], payload.get("channel", ""), profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["capability_evidence_id"] = evidence_id(payload)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for target in (path, latest):
        tmp = target.with_name(f"{target.name}.tmp.{os.getpid()}")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)
    return latest


def append_smoke_event(root: str, payload: Mapping[str, Any]) -> None:
    event = {
        "kind": EVENT_KIND,
        "version": EVENT_VERSION,
        "ts": str(payload.get("checked_at") or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()),
        "episode": "全剧",
        "stage": "backend_smoke",
        "event": "qa",
        "source": "skills/n2d/_lib/backend_smoke.py",
        "qa": {
            "severity": "info" if str(payload.get("status") or "").lower() in PASS_STATUSES else "warn",
            "dim": "后端smoke",
            "loc": f"{payload.get('backend_kind')}:{payload.get('backend')}:{payload.get('smoke_profile')}",
            "msg": f"backend smoke {payload.get('status')} proof={payload.get('proof_type')}",
        },
        "meta": {
            "backend_kind": payload.get("backend_kind"),
            "backend": payload.get("backend"),
            "channel": payload.get("channel"),
            "smoke_profile": payload.get("smoke_profile"),
            "capability_evidence_id": payload.get("capability_evidence_id"),
            "output_asset": payload.get("output_asset"),
        },
    }
    path = production_dir(root) / "production_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def record_smoke(
    root: str,
    backend_kind: str,
    backend: str,
    *,
    channel: str = "",
    status: str,
    capabilities: Optional[Dict[str, Any]] = None,
    source: str = "",
    command: str = "",
    output_asset: str = "",
    note: str = "",
    proof_type: str = "manual_assert",
    checked_at: Optional[str] = None,
    profile: str = DEFAULT_PROFILE,
    record_event: bool = True,
) -> Dict[str, Any]:
    # proof_type 区分「探活证明」vs「手录声明」：live_probe=adapter 真探到后端可跑；manual_assert=人手打的
    # pass（证的是声明不是活性）。严档闸据此要求 live_probe 或可核验的真实 output_asset，堵报废 endpoint 凭一句 pass 绿。
    payload: Dict[str, Any] = {
        "kind": KIND,
        "version": VERSION,
        "backend_kind": backend_kind,
        "backend": backend,
        "channel": channel,
        "smoke_profile": normalize_profile(profile),
        "profile_spec": profile_spec(backend_kind, profile),
        "status": status,
        "proof_type": proof_type,
        "checked_at": checked_at or dt.date.today().isoformat(),
        "capabilities": capabilities or {},
        "source": source,
        "command": command,
        "output_asset": output_asset,
        "note": note,
    }
    path = write_payload(root, payload)
    payload["path"] = str(path)
    if record_event:
        append_smoke_event(root, payload)
    return payload


def probe_smoke(root: str, backend_kind: str, backend: str, *, channel: str = "", profile: str = DEFAULT_PROFILE) -> Dict[str, Any]:
    if backend_kind == "image":
        probe = image_backend_adapter.probe(backend)
        raw = str(probe.get("status") or "unknown")
        status = "pass" if raw == "ok" else ("fail" if raw == "down" else "skipped")
        capabilities = image_backend_adapter.default_capability_assertions(backend)
        note = str(probe.get("detail") or raw)
    elif backend_kind == "video":
        raw, detail = video_backend_adapter.probe_video_backend(backend)
        status = "pass" if raw == "ok" else ("fail" if raw == "down" else "skipped")
        capabilities = video_backend_adapter.default_capability_assertions(backend, channel)
        note = detail or raw
    else:
        raise ValueError("backend_kind must be image or video")
    # adapter 真探到可跑(raw==ok→status==pass)才算 live_probe；skipped/unknown 是「探不了」非「探活」。
    proof_type = "live_probe" if status == "pass" else "probe_inconclusive"
    return record_smoke(
        root,
        backend_kind,
        backend,
        channel=channel,
        status=status,
        capabilities=capabilities,
        source="adapter_probe",
        command="non_paid_probe",
        proof_type=proof_type,
        profile=profile,
        note=note,
    )


def load_latest(root: str, backend_kind: str, backend: str, channel: str = "", profile: str = DEFAULT_PROFILE) -> Optional[Dict[str, Any]]:
    path = latest_path(root, backend_kind, backend, channel, profile)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def smoke_status(
    root: str,
    backend_kind: str,
    backend: str,
    *,
    channel: str = "",
    required_capabilities: Sequence[str] = (),
    profile: str = DEFAULT_PROFILE,
    max_age_days: int = 7,
    require_proof: bool = False,
    today: Optional[dt.date] = None,
) -> Dict[str, Any]:
    profile = normalize_profile(profile)
    path = latest_path(root, backend_kind, backend, channel, profile)
    evidence = load_latest(root, backend_kind, backend, channel, profile)
    if not evidence:
        return {"status": "missing", "path": str(path), "message": "no backend smoke evidence"}
    if evidence.get("kind") != KIND:
        return {"status": "invalid", "path": str(path), "message": f"kind must be {KIND}"}
    raw_date = str(evidence.get("checked_at") or "")
    try:
        checked = dt.date.fromisoformat(raw_date[:10])
    except ValueError:
        return {"status": "bad_date", "path": str(path), "message": f"invalid checked_at: {raw_date}"}
    age = max(0, ((today or dt.date.today()) - checked).days)
    status = str(evidence.get("status") or "").lower()
    if status in FAIL_STATUSES:
        return {"status": "failed", "path": str(path), "checked_at": checked.isoformat(), "age_days": age, "message": "latest smoke failed"}
    if status not in PASS_STATUSES:
        return {"status": "not_passed", "path": str(path), "checked_at": checked.isoformat(), "age_days": age, "message": f"latest smoke status={status or 'missing'}"}
    if age > max_age_days:
        return {"status": "stale", "path": str(path), "checked_at": checked.isoformat(), "age_days": age, "max_age_days": max_age_days, "message": f"smoke evidence is {age} day(s) old"}
    caps = evidence.get("capabilities") if isinstance(evidence.get("capabilities"), dict) else {}
    spec = profile_spec(backend_kind, profile)
    required = list(dict.fromkeys(list(spec.get("required_capabilities") or []) + list(required_capabilities or [])))
    missing_caps = [cap for cap in required if caps.get(cap) in (None, "", False, [])]
    if missing_caps:
        return {
            "status": "missing_capability",
            "path": str(path),
            "checked_at": checked.isoformat(),
            "age_days": age,
            "missing_capabilities": missing_caps,
            "message": "smoke evidence lacks required capabilities: " + ", ".join(missing_caps),
        }
    any_caps = list(spec.get("any_capability") or [])
    if any_caps and not any(caps.get(cap) not in (None, "", False, [], 0) for cap in any_caps):
        return {
            "status": "missing_capability",
            "path": str(path),
            "checked_at": checked.isoformat(),
            "age_days": age,
            "missing_capabilities": any_caps,
            "message": "smoke evidence lacks at least one required alternative capability: " + " / ".join(any_caps),
        }
    # 活性核验：声明的 output_asset 必须真存在（手录 pass 配个真产物路径 = 后端确实出过东西）。
    # 报废 endpoint 凭一句 pass 绿、产物却不在 → asset_missing。空 output_asset 跳过（向后兼容）。
    asset = str(evidence.get("output_asset") or "").strip()
    asset_exists = False
    if asset:
        asset_full = asset if os.path.isabs(asset) else os.path.join(root, asset)
        asset_exists = os.path.exists(asset_full)
        if not asset_exists:
            return {"status": "asset_missing", "path": str(path), "checked_at": checked.isoformat(),
                    "age_days": age, "output_asset": asset,
                    "message": f"声明的 output_asset 不存在：{asset}（证的是声明不是活性——补真实探活或真实产物路径）"}
    # 严档（付费批量/放量硬闸）：要求 live_probe 或可核验的真实 output_asset，否则只是手录声明。
    # 视频后端常无 health 探针、live_probe 不可得，故不强制 live_probe，但要求**某种证据**。
    proof = str(evidence.get("proof_type") or "manual_assert")
    if require_proof and proof != "live_probe" and not asset_exists:
        return {"status": "unverified", "path": str(path), "checked_at": checked.isoformat(),
                "age_days": age, "proof_type": proof,
                "message": "手录 pass 但既无 live_probe 也无可核验 output_asset：证的是声明不是活性——"
                           "用 backend_smoke.py probe 真探活，或 record 时附真实产物 --output-asset 路径。"}
    return {
        "status": "fresh",
        "proof_type": proof,
        "path": str(path),
        "checked_at": checked.isoformat(),
        "age_days": age,
        "capability_evidence_id": evidence.get("capability_evidence_id"),
        "smoke_profile": profile,
        "message": "fresh backend smoke evidence",
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d backend smoke evidence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("root")
    common.add_argument("--kind", required=True, choices=("image", "video"))
    common.add_argument("--backend", required=True)
    common.add_argument("--channel", default="")
    common.add_argument("--profile", default=DEFAULT_PROFILE,
                        choices=sorted({DEFAULT_PROFILE, "normal_motion", "talking_closeup", "frame_control"}))
    p = sub.add_parser("probe", parents=[common])
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("record", parents=[common])
    p.add_argument("--status", required=True, choices=("pass", "fail", "skipped"))
    p.add_argument("--capability", action="append", default=[])
    p.add_argument("--source", default="")
    p.add_argument("--command", default="")
    p.add_argument("--output-asset", default="")
    p.add_argument("--note", default="")
    p.add_argument("--date", default=None)
    p.add_argument("--no-event", action="store_true", help="do not append production_events.jsonl smoke event")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("status", parents=[common])
    p.add_argument("--require", action="append", default=[])
    p.add_argument("--max-age-days", type=int, default=7)
    p.add_argument("--require-proof", action="store_true",
                   help="严档：要求 live_probe 或可核验真实 output_asset，拒手录无产物 pass")
    p.add_argument("--today", default=None)
    p.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ns = parser().parse_args(argv)
    if ns.cmd == "probe":
        payload = probe_smoke(ns.root, ns.kind, ns.backend, channel=ns.channel, profile=ns.profile)
    elif ns.cmd == "record":
        payload = record_smoke(
            ns.root,
            ns.kind,
            ns.backend,
            channel=ns.channel,
            status=ns.status,
            capabilities=parse_capability(ns.capability),
            source=ns.source,
            command=ns.command,
            output_asset=ns.output_asset,
            note=ns.note,
            checked_at=ns.date,
            profile=ns.profile,
            record_event=not ns.no_event,
        )
    elif ns.cmd == "status":
        today = dt.date.fromisoformat(ns.today) if ns.today else None
        payload = smoke_status(
            ns.root,
            ns.kind,
            ns.backend,
            channel=ns.channel,
            required_capabilities=ns.require,
            profile=ns.profile,
            max_age_days=ns.max_age_days,
            require_proof=ns.require_proof,
            today=today,
        )
    else:  # pragma: no cover
        raise AssertionError(ns.cmd)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("status") in {"pass", "fresh", "skipped"} else 1


if __name__ == "__main__":
    sys.exit(main())
