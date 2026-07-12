#!/usr/bin/env python3
"""Low-cost script and animatic acceptance packets for n2d.

This is the traditional read-through / animatic review layer:

* table_read_packet: after Stage 1 voiceover, before director blocking/storyboard.
* animatic_packet: after Stage 2 storyboard, before image prompt / paid visuals.

The script only scaffolds and checks evidence. A draft packet still blocks until
the human/agent reviewer marks it confirmed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from signoff_contract import (  # noqa: E402
    load_manifest as load_signoff_manifest,
    new_manifest as new_signoff_manifest,
    profile_spec as signoff_profile_spec,
    validate_manifest as validate_signoff_manifest,
    write_manifest as write_signoff_manifest,
)


KIND = "n2d_story_acceptance_packets"
CHECK_KIND = "n2d_story_acceptance_packets_check"
VERSION = 1
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)

PACKETS = {
    "table_read": ("table_read_packet.json", "table_read_packet.md"),
    "animatic": ("animatic_packet.json", "animatic_packet.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_digest(root: Path, rel: str) -> str | None:
    path = root / rel
    if path.is_file():
        return file_sha256(path)
    return None


def artifact_fingerprint(root: Path, rels: Iterable[str]) -> Dict[str, Any]:
    files: Dict[str, str | None] = {}
    h = hashlib.sha256()
    for rel in sorted({str(r).replace(os.sep, "/") for r in rels}):
        digest = path_digest(root, rel)
        files[rel] = digest
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((digest or "-").encode("ascii"))
        h.update(b"\n")
    return {"files": files, "sha": h.hexdigest()}


def fingerprint_is_fresh(recorded: Any, root: Path) -> bool | None:
    if not isinstance(recorded, Mapping):
        return None
    files = recorded.get("files")
    sha = recorded.get("sha")
    if not isinstance(files, Mapping) or not isinstance(sha, str) or not sha:
        return None
    return artifact_fingerprint(root, [str(k) for k in files.keys()])["sha"] == sha


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def ep_dir(root: Path, ep: str) -> Path:
    return root / "脚本" / ep


def clean_lines(text: str, *, limit: int = 80) -> List[str]:
    out: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        out.append(re.sub(r"^\s*(?:[-*]|\d+[.)、])\s*", "", line)[:limit])
    return out


def storyboard_clips(root: Path, ep: str) -> List[Dict[str, Any]]:
    data = load_json(ep_dir(root, ep) / "storyboard.json")
    clips = data.get("clips") if isinstance(data, Mapping) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def duration_map(root: Path, ep: str) -> Mapping[str, Any]:
    data = load_json(ep_dir(root, ep) / "镜头时长.json")
    return data if isinstance(data, Mapping) else {}


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or f"Clip_{idx:02d}")


def packet_paths(root: Path, ep: str, kind: str) -> Tuple[Path, Path]:
    names = PACKETS[kind]
    base = ep_dir(root, ep)
    return base / names[0], base / names[1]


def packet_input_rels(ep: str, kind: str) -> List[str]:
    if kind == "table_read":
        return [
            f"脚本/{ep}/voiceover.txt",
            f"合成/{ep}/配音/时长清单.json",
            f"生产数据/script_quality_contract_{ep}.json",
        ]
    return [
        f"脚本/{ep}/storyboard.json",
        f"脚本/{ep}/镜头时长.json",
        f"脚本/{ep}/字幕_中文.srt",
        f"合成/{ep}/配音/voice_zh.wav",
    ]


def _machine_reference(root: Path, ep: str, kind: str) -> Dict[str, Any]:
    """给围读/animatic 的主观验收布尔配上已算好的机器参考量（advisory·不改签收语义）。

    此前 exposition_not_overloaded / duration_risk_understood / mid_episode_drag_checked
    只有 unreviewed/accepted 两态，签收=人点头——而 story_economy/timing_estimate 里其实
    已经算好了可挂钩的量。这里只做只读汇总：报告缺失标 missing，绝不阻断。"""
    ref: Dict[str, Any] = {"advisory": True,
                           "note": "签收前对照：flags>0 时 reviewer 应在 rewrite_notes 说明接受理由或先返工。"}
    econ = load_json(root / "生产数据" / f"story_economy_audit_{ep}.json")
    if isinstance(econ, Mapping):
        findings = econ.get("findings") if isinstance(econ.get("findings"), list) else []
        sev = [str((f or {}).get("severity") or "") for f in findings if isinstance(f, Mapping)]
        codes = [str((f or {}).get("code") or "") for f in findings if isinstance(f, Mapping)]
        ref["story_economy"] = {
            "block": sum(1 for s in sev if s == "block"),
            "warn": sum(1 for s in sev if s == "warn"),
            "narration_heavy_clips": sum(1 for f in findings if isinstance(f, Mapping)
                                         and "narration_heavy" in (f.get("signals") or [])),
            "over_budget_codes": sorted({c for c in codes if "too_long" in c or "over_economy" in c}),
        }
    else:
        ref["story_economy"] = "missing"
    timing = load_json(root / "合成" / ep / "配音" / "timing_estimate.json")
    if isinstance(timing, Mapping):
        summary = timing.get("summary") if isinstance(timing.get("summary"), Mapping) else {}
        ref["timing_estimate"] = {
            "duration_sec": summary.get("duration_sec"),
            "line_count": summary.get("line_count"),
            "split_suggested_lines": summary.get("split_suggested_lines", 0),
        }
    else:
        ref["timing_estimate"] = "missing"
    if kind == "animatic":
        clips = storyboard_clips(root, ep)
        durations = duration_map(root, ep)
        long15 = long20 = 0
        for idx, clip in enumerate(clips, start=1):
            cid = clip_id(clip, idx)
            try:
                dur = float(clip.get("duration") or durations.get(cid) or durations.get(str(idx)) or 0)
            except Exception:
                continue
            if dur > 20.0:
                long20 += 1
            elif dur > 15.0:
                long15 += 1
        ref["long_clips"] = {"over_15s": long15, "over_20s": long20,
                             "note": ">15s 需拆段计划、>20s 详拍叙事跨度已超上限（story_economy 同口径）"}
    return ref


def _table_read_payload(root: Path, ep: str, *, confirmed: bool = False) -> Dict[str, Any]:
    voiceover = clean_lines(read_text(ep_dir(root, ep) / "voiceover.txt"), limit=120)
    timing = load_json(root / "合成" / ep / "配音" / "时长清单.json")
    timing_status = "missing"
    placeholder_count = 0
    if isinstance(timing, Mapping):
        timing_status = str(timing.get("status") or "present")
        blob = json.dumps(timing, ensure_ascii=False)
        placeholder_count = blob.count("占位") + blob.lower().count("placeholder")
    return {
        "kind": "n2d_table_read_packet",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "owner": "writer_director_producer",
        "inputs": {
            "voiceover": f"脚本/{ep}/voiceover.txt",
            "timing_manifest": f"合成/{ep}/配音/时长清单.json",
            "script_quality_contract": f"生产数据/script_quality_contract_{ep}.json",
        },
        "inputs_fingerprint": artifact_fingerprint(root, packet_input_rels(ep, "table_read")),
        "read_through": {
            "line_count": len(voiceover),
            "sample_lines": voiceover[:12],
            "timing_status": timing_status,
            "placeholder_or_rough_timing_mentions": placeholder_count,
        },
        "machine_reference": _machine_reference(root, ep, "table_read"),
        "acceptance": {
            "dialogue_voice_distinct": "unreviewed" if not confirmed else "accepted",
            "exposition_not_overloaded": "unreviewed" if not confirmed else "accepted",
            "duration_risk_understood": "unreviewed" if not confirmed else "accepted",
            "rewrite_notes": [],
            "reviewer": "",
            "signoff_manifest": f"脚本/{ep}/table_read_signoff.json",
        },
    }


def _animatic_payload(root: Path, ep: str, *, confirmed: bool = False) -> Dict[str, Any]:
    clips = storyboard_clips(root, ep)
    durations = duration_map(root, ep)
    rows: List[Dict[str, Any]] = []
    total = 0.0
    for idx, clip in enumerate(clips, start=1):
        cid = clip_id(clip, idx)
        dur = clip.get("duration") or durations.get(cid) or durations.get(str(idx)) or 0
        try:
            total += float(dur)
        except Exception:
            pass
        rows.append({
            "clip_id": cid,
            "duration_sec": dur,
            "dramatic_function": clip.get("dramatic_function") or "",
            "pacing_role": clip.get("pacing_role") or clip.get("runtime_priority") or "",
            "transition": (clip.get("continuity") or {}).get("transition") if isinstance(clip.get("continuity"), Mapping) else "",
            "review_focus": "hook/reversal/seam/readability" if idx in {1, len(clips)} else "rhythm/readability",
        })
    return {
        "kind": "n2d_animatic_packet",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "owner": "director_editor_producer",
        "inputs": {
            "storyboard": f"脚本/{ep}/storyboard.json",
            "shot_durations": f"脚本/{ep}/镜头时长.json",
            "subtitle_zh": f"脚本/{ep}/字幕_中文.srt",
            "rough_audio": f"合成/{ep}/配音/voice_zh.wav",
            "timed_preview": f"生产数据/animatic_{ep}.html",
            "timed_preview_manifest": f"生产数据/animatic_{ep}.json",
        },
        "inputs_fingerprint": artifact_fingerprint(root, packet_input_rels(ep, "animatic")),
        "timeline": {
            "clip_count": len(rows),
            "estimated_total_sec": round(total, 3),
            "clips": rows,
        },
        "machine_reference": _machine_reference(root, ep, "animatic"),
        "acceptance": {
            "opening_readable_without_sound": "unreviewed" if not confirmed else "accepted",
            "mid_episode_drag_checked": "unreviewed" if not confirmed else "accepted",
            "cliffhanger_or_payoff_clear": "unreviewed" if not confirmed else "accepted",
            "image_generation_ready": "unreviewed" if not confirmed else "accepted",
            "reviewer": "",
            "signoff_manifest": f"脚本/{ep}/animatic_signoff.json",
        },
    }


def _load_animatic_assembler():
    path = Path(__file__).with_name("animatic_assembler.py")
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("n2d_animatic_assembler_for_acceptance", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _ensure_animatic_preview(root: Path, ep: str) -> None:
    # Idempotence matters because animatic evidence is hash-signed. A plain
    # `check --write-missing` must not rewrite generated_at/OTIO and stale an
    # otherwise valid approval when inputs have not changed.
    if _animatic_preview_status(root, ep).get("status") == "pass":
        return
    mod = _load_animatic_assembler()
    if mod is None:
        return
    payload = mod.build_report(root, ep)
    mod.write_outputs(root, ep, payload)


def _animatic_preview_status(root: Path, ep: str) -> Dict[str, Any]:
    manifest = root / "生产数据" / f"animatic_{ep}.json"
    preview = root / "生产数据" / f"animatic_{ep}.html"
    otio_snapshot = root / "合成" / ep / "_work" / "animatic_timeline.otio"
    issues: List[str] = []
    data = load_json(manifest)
    if not isinstance(data, Mapping):
        issues.append("缺 timed animatic manifest")
    else:
        if data.get("kind") != "n2d_animatic_preview":
            issues.append("animatic manifest kind 不正确")
        if str(data.get("status") or "").lower() == "block":
            issues.append("timed animatic preview 为 block")
        fresh = fingerprint_is_fresh(data.get("inputs_fingerprint"), root)
        if fresh is False:
            issues.append("timed animatic preview 输入已变化，需重建")
        elif fresh is None:
            issues.append("timed animatic preview 缺 inputs_fingerprint")
        artifact = str(data.get("preview_artifact") or f"生产数据/animatic_{ep}.html")
        artifact_path = root / artifact if not Path(artifact).is_absolute() else Path(artifact)
        if not artifact_path.is_file():
            issues.append("timed animatic preview artifact 缺失")
    if not preview.is_file():
        issues.append("缺 timed animatic HTML 预览")
    if not otio_snapshot.is_file():
        issues.append("缺 animatic OTIO 锁版快照")
    else:
        otio = load_json(otio_snapshot)
        phase = (((otio.get("metadata") or {}).get("n2d") or {}).get("phase") if isinstance(otio, Mapping) else "")
        if otio.get("OTIO_SCHEMA") != "Timeline.1" or phase != "animatic":
            issues.append("animatic OTIO 快照 schema/phase 不正确")
    return {
        "packet": "animatic_preview",
        "file": str(manifest),
        "status": "pass" if not issues else "block",
        "issues": issues,
    }


def _parse_json_stdout(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.rfind("\n{")
    if start >= 0:
        try:
            return json.loads(text[start + 1:])
        except Exception:
            return None
    return None


def _story_economy_status(root: Path, ep: str) -> Dict[str, Any]:
    script = Path(__file__).with_name("story_economy_audit.py")
    out = root / "生产数据" / f"story_economy_audit_{ep}.json"
    if not script.is_file():
        return {
            "packet": "story_economy",
            "file": str(out),
            "status": "block",
            "issues": ["缺 story_economy_audit.py"],
        }
    try:
        r = subprocess.run(
            [sys.executable, str(script), str(root), ep, "--strict", "--write", "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception as exc:
        return {
            "packet": "story_economy",
            "file": str(out),
            "status": "block",
            "issues": [f"story_economy_audit 无法运行：{str(exc)[:160]}"],
        }
    report = _parse_json_stdout(r.stdout) or load_json(out)
    issues: List[str] = []
    if not isinstance(report, Mapping):
        detail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
        issues.append(f"story_economy_audit 未输出有效 JSON：{detail[0][:160]}")
    else:
        over_budget = report.get("over_budget") if isinstance(report.get("over_budget"), list) else []
        for row in over_budget[:5]:
            if isinstance(row, Mapping):
                issues.append(str(row.get("reason") or row.get("clip_id") or "story clip 超预算"))
        if r.returncode != 0 and not issues:
            issues.append("story_economy_audit --strict 未通过")
        if report.get("ok") is not True and not issues:
            issues.append("story_economy_audit ok=false")
    if r.returncode != 0 and not issues:
        issues.append("story_economy_audit --strict 未通过")
    return {
        "packet": "story_economy",
        "file": str(out),
        "status": "pass" if not issues else "block",
        "issues": issues,
    }


def render_md(payload: Mapping[str, Any]) -> str:
    kind = str(payload.get("kind") or "")
    title = "围读验收包" if "table_read" in kind else "Animatic 粗剪验收包"
    lines = [
        "---",
        f"kind: {kind}",
        f"version: {payload.get('version')}",
        f"episode: {payload.get('episode')}",
        f"status: {payload.get('status')}",
        "---",
        f"# {payload.get('episode')} — {title}",
        "",
    ]
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), Mapping) else {}
    lines += ["## Inputs", ""]
    for key, value in inputs.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Acceptance", ""]
    acc = payload.get("acceptance") if isinstance(payload.get("acceptance"), Mapping) else {}
    for key, value in acc.items():
        lines.append(f"- {key}: {value}")
    if "read_through" in payload:
        rt = payload.get("read_through") or {}
        lines += ["", "## Read Through", "", f"- line_count: {rt.get('line_count')}", f"- timing_status: {rt.get('timing_status')}"]
    if "timeline" in payload:
        tl = payload.get("timeline") or {}
        lines += ["", "## Timeline", "", f"- clip_count: {tl.get('clip_count')}", f"- estimated_total_sec: {tl.get('estimated_total_sec')}"]
    return "\n".join(lines).rstrip() + "\n"


def scaffold(root: Path, ep: str, *, kind: str = "both", confirmed: bool = False, force: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    kinds = list(PACKETS) if kind == "both" else [kind]
    created: List[str] = []
    for item in kinds:
        json_path, md_path = packet_paths(root, ep, item)
        payload = _table_read_payload(root, ep, confirmed=confirmed) if item == "table_read" else _animatic_payload(root, ep, confirmed=confirmed)
        if force or not json_path.exists():
            write_json_atomic(json_path, payload)
            created.append(str(json_path))
        if force or not md_path.exists():
            write_atomic(md_path, render_md(payload))
            created.append(str(md_path))
        signoff_spec = signoff_profile_spec(root, item, ep)
        signoff_path = root / signoff_spec["signoff_path"]
        if not signoff_path.exists():
            write_signoff_manifest(signoff_path, new_signoff_manifest(
                root,
                artifact_scope=signoff_spec["artifact_scope"],
                episode=ep,
                author_id="automation:n2d",
                input_paths=signoff_spec["input_paths"],
                evidence_paths=signoff_spec["evidence_paths"],
                required_role_groups=signoff_spec["required_role_groups"],
            ))
    return {"kind": KIND, "episode": ep, "created": created, "status": "scaffolded"}


def _signoff_status(root: Path, ep: str, kind: str) -> Dict[str, Any]:
    spec = signoff_profile_spec(root, kind, ep)
    path = root / spec["signoff_path"]
    issues = validate_signoff_manifest(
        load_signoff_manifest(path),
        root,
        artifact_scope=spec["artifact_scope"],
        input_paths=spec["input_paths"],
        evidence_paths=spec["evidence_paths"],
        required_role_groups=spec["required_role_groups"],
    )
    return {
        "packet": kind,
        "file": str(path),
        "status": "pass" if not issues else "block",
        "issues": issues,
    }


def _json_status(root: Path, path: Path) -> Tuple[str, List[str]]:
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, Mapping):
        return "block", ["JSON 无法解析或不是 object"]
    if str(data.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed")
    if PLACEHOLDER_RE.search(json.dumps(data, ensure_ascii=False)):
        issues.append("仍含待补/TODO 占位")
    fresh = fingerprint_is_fresh(data.get("inputs_fingerprint"), root)
    if fresh is False:
        issues.append("inputs_fingerprint 已过期，上游输入变更后需重新签收")
    elif fresh is None:
        issues.append("缺 inputs_fingerprint，不能证明签收对应当前输入")
    return ("pass" if not issues else "block"), issues


def _md_status(path: Path) -> Tuple[str, List[str]]:
    text = read_text(path)
    issues: List[str] = []
    if not text.strip():
        return "block", ["文件为空"]
    if not re.search(r"(?im)^\s*status\s*[:：]\s*confirmed\s*$", text):
        issues.append("缺 status: confirmed")
    if PLACEHOLDER_RE.search(text):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def check(root: Path, ep: str, *, kind: str = "both", write_missing: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    if write_missing:
        scaffold(root, ep, kind=kind)
        if kind in {"animatic", "both"}:
            _ensure_animatic_preview(root, ep)
    kinds = list(PACKETS) if kind == "both" else [kind]
    rows: List[Dict[str, Any]] = []
    for item in kinds:
        for path in packet_paths(root, ep, item):
            if not path.exists():
                rows.append({"packet": item, "file": str(path), "status": "missing", "issues": ["文件缺失"]})
                continue
            status, issues = _json_status(root, path) if path.suffix == ".json" else _md_status(path)
            rows.append({"packet": item, "file": str(path), "status": status, "issues": issues})
        if item == "animatic":
            rows.append(_animatic_preview_status(root, ep))
            rows.append(_story_economy_status(root, ep))
        rows.append(_signoff_status(root, ep, item))
    blockers = [r for r in rows if r["status"] != "pass"]
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "episode": ep,
        "packet_kind": kind,
        "status": "pass" if not blockers else "block",
        "generated_at": now_iso(),
        "summary": {"required": len(rows), "pass": len(rows) - len(blockers), "block": len(blockers)},
        "files": rows,
        "next_when_blocked": "补齐围读/animatic 内容与 timed preview，把内容 status 改为 confirmed，再用 signoff.py 由明确角色签收当前输入与证据哈希。",
    }
    out = root / "生产数据" / f"story_acceptance_packets_check_{kind}_{ep}.json"
    write_json_atomic(out, payload)
    payload["check_path"] = str(out)
    return payload


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("command", choices=("scaffold", "check"))
    ap.add_argument("--kind", choices=("table_read", "animatic", "both"), default="both")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-missing", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    if ns.command == "scaffold":
        payload = scaffold(root, ns.episode, kind=ns.kind, confirmed=ns.confirm, force=ns.force)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    payload = check(root, ns.episode, kind=ns.kind, write_missing=ns.write_missing)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if ns.json else f"story acceptance: {payload['status']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
