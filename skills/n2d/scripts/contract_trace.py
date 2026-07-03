#!/usr/bin/env python3
"""Audit traceability from source comprehension contracts to delivery evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set


SCRIPT_DIR = Path(__file__).resolve().parent
LIB = SCRIPT_DIR.parents[0] / "_lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

try:
    from n2d_route import normalize_episode  # type: ignore
except Exception:  # pragma: no cover
    normalize_episode = lambda x: str(x or "").strip()  # type: ignore


VERSION = 1
OUT_JSON = "contract_trace_{episode}.json"
OUT_MD = "contract_trace_{episode}.md"
TRACE_RE = re.compile(r"\bSRC_[A-Z]+_\d{3,}\b")


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


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def trace_ids_in(value: Any) -> Set[str]:
    found = set(TRACE_RE.findall(flatten(value)))
    if isinstance(value, Mapping):
        for key in ("trace_id", "source_trace_id", "contract_trace_id"):
            raw = value.get(key)
            if isinstance(raw, str) and raw.strip():
                found.add(raw.strip())
        for key in ("trace_ids", "source_trace_ids", "contract_trace_ids"):
            raw = value.get(key)
            if isinstance(raw, list):
                found.update(str(x).strip() for x in raw if str(x).strip())
            elif isinstance(raw, str):
                found.update(TRACE_RE.findall(raw))
    return {x for x in found if TRACE_RE.fullmatch(x)}


def source_contract(root: Path) -> Mapping[str, Any]:
    data = load_json(root / "设定库" / "source_comprehension.json")
    return data if isinstance(data, Mapping) else {}


def source_trace_ids(root: Path) -> Dict[str, Dict[str, Any]]:
    data = source_contract(root)
    contract = data.get("understanding_contract") if isinstance(data.get("understanding_contract"), Mapping) else {}
    sections = {
        "episode_promise_basis": "promise",
        "character_motives": "motive",
        "causality_chain": "causality",
        "foreshadowing_ledger": "foreshadowing",
    }
    out: Dict[str, Dict[str, Any]] = {}
    for section, category in sections.items():
        rows = contract.get(section)
        if not isinstance(rows, list):
            continue
        for idx, row in enumerate(rows, 1):
            if not isinstance(row, Mapping):
                continue
            ids = trace_ids_in(row)
            for trace_id in ids:
                out[trace_id] = {
                    "trace_id": trace_id,
                    "category": category,
                    "section": section,
                    "index": idx,
                    "summary": flatten(row)[:220],
                }
    return out


def _storyboard(root: Path, episode: str) -> List[Mapping[str, Any]]:
    data = load_json(root / "脚本" / episode / "storyboard.json")
    clips = data.get("clips") if isinstance(data, Mapping) else []
    return [c for c in clips or [] if isinstance(c, Mapping)]


def _clip_id(row: Mapping[str, Any], idx: int = 0) -> str:
    raw = str(row.get("clip_id") or row.get("clip") or row.get("id") or row.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return raw or (f"Clip_{idx:02d}" if idx else "")


def _preventive_contract(root: Path, episode: str) -> Mapping[str, Any]:
    data = load_json(root / "脚本" / episode / "preventive_contracts.json")
    return data if isinstance(data, Mapping) else {}


def _episode_refs(contract: Mapping[str, Any]) -> Set[str]:
    return trace_ids_in(contract.get("episode_promise") if isinstance(contract.get("episode_promise"), Mapping) else {})


def _shot_refs(root: Path, episode: str) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    contract = _preventive_contract(root, episode)
    for row in contract.get("shots") or []:
        if isinstance(row, Mapping):
            cid = _clip_id(row)
            out.setdefault(cid, set()).update(trace_ids_in(row))
    for idx, clip in enumerate(_storyboard(root, episode), 1):
        cid = _clip_id(clip, idx)
        out.setdefault(cid, set()).update(trace_ids_in(clip))
    return out


def _prompt_files(root: Path, episode: str) -> Iterable[Path]:
    patterns = [
        root / "出图" / episode / "prompt" / "*",
        root / "出图" / episode / "*.md",
        root / "出视频" / episode / "prompt" / "*",
        root / "出视频" / episode / "*.md",
        production_dir(root) / f"generation_recipe*{episode}*.json",
        production_dir(root) / f"script_contract_applied_{episode}.json",
    ]
    for pattern in patterns:
        for raw in glob.glob(str(pattern)):
            path = Path(raw)
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"}:
                yield path


def _prompt_refs(root: Path, episode: str) -> Set[str]:
    found: Set[str] = set()
    for path in _prompt_files(root, episode):
        try:
            found.update(TRACE_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
        except Exception:
            continue
    return found


def _clip_artifacts(root: Path, episode: str, clip_id: str) -> List[str]:
    m = re.search(r"(\d+)", clip_id)
    needles = {clip_id, clip_id.replace("_", ""), clip_id.replace("_0", "")}
    if m:
        n = int(m.group(1))
        needles.update({f"Clip{n:02d}", f"Clip_{n:02d}", f"clip{n:02d}", f"{n:02d}"})
    roots = [root / "出图" / episode, root / "出视频" / episode, root / "合成" / episode]
    out: List[str] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            low = path.name.lower()
            if any(needle.lower() in low for needle in needles):
                out.append(relpath(root, path))
    return sorted(set(out))


def build_report(root: Path, episode: str) -> Dict[str, Any]:
    root = root.resolve()
    episode = normalize_episode(episode)
    source_ids = source_trace_ids(root)
    contract = _preventive_contract(root, episode)
    ep_refs = _episode_refs(contract)
    shot_refs = _shot_refs(root, episode)
    prompt_refs = _prompt_refs(root, episode)

    findings: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    if not source_contract(root):
        findings.append({"severity": "block", "code": "missing_source_comprehension", "message": "缺 source_comprehension.json，无法追踪源理解合同。"})
    if source_contract(root) and not source_ids:
        findings.append({"severity": "block", "code": "missing_source_trace_ids", "message": "源理解合同缺 SRC_* trace_id，confirmed 不能证明被下游消费。"})

    for trace_id, meta in sorted(source_ids.items()):
        clips = sorted(cid for cid, refs in shot_refs.items() if trace_id in refs)
        artifacts = sorted({path for cid in clips for path in _clip_artifacts(root, episode, cid)})
        missing = []
        if trace_id not in ep_refs:
            missing.append("episode_contract")
        if not clips:
            missing.append("shot_intent/storyboard")
        if trace_id not in prompt_refs:
            missing.append("prompt_or_generation_recipe")
        if not artifacts:
            missing.append("final_shot_artifact")
        row = {**meta, "episode_contract": trace_id in ep_refs, "clips": clips, "prompt": trace_id in prompt_refs, "artifacts": artifacts, "missing": missing}
        rows.append(row)
        if missing:
            findings.append({
                "severity": "block",
                "code": "trace_not_consumed",
                "trace_id": trace_id,
                "message": f"{trace_id} 未贯通：" + "、".join(missing),
                "return_to_stage": "script_stage1",
                "root_cause_layer": "script",
            })

    return {
        "kind": "n2d_contract_trace",
        "version": VERSION,
        "root": str(root),
        "episode": episode,
        "generated_at": now_iso(),
        "status": "blocked" if findings else "pass",
        "summary": {"source_trace_ids": len(source_ids), "block": len(findings), "traced": sum(1 for r in rows if not r["missing"])},
        "source_comprehension": relpath(root, root / "设定库" / "source_comprehension.json"),
        "rows": rows,
        "findings": findings,
    }


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# n2d Contract Trace",
        "",
        f"- 集：{payload.get('episode')}",
        f"- 状态：{payload.get('status')}",
        f"- 汇总：{payload.get('summary')}",
        "",
        "| trace_id | category | clips | missing |",
        "|---|---|---|---|",
    ]
    for row in payload.get("rows") or []:
        lines.append(f"| {row.get('trace_id')} | {row.get('category')} | {', '.join(row.get('clips') or []) or '-'} | {', '.join(row.get('missing') or []) or '-'} |")
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
    ap = argparse.ArgumentParser(description="audit source contract traceability")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    payload = build_report(root, ns.episode)
    if ns.write:
        payload["outputs"] = write_outputs(root, payload["episode"], payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if ns.json else render_markdown(payload))
    return 2 if payload.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
