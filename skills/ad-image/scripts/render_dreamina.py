#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render ad-image prompt jobs through the official Dreamina CLI.

Reads 出图/分镜/image_jobs_manifest.json, submits each planned prompt via
`dreamina text2image`, downloads the first returned image to expected_output,
and records deterministic provenance. This script only supports the official
CLI path; reverse/third-party paths remain forbidden by ad-craft contract.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


KEY_SECTIONS = (
    "画面 prompt",
    "身份锁定句",
    "产品/品牌锁",
    "文字锁",
    "构图与光位",
    "尾帧接力",
    "负向",
)
SIGNOFF_REL = Path("合规") / "image_backend_override.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def dreamina_image_signoff_allows(root: Path) -> bool:
    """Dreamina image spend requires an explicit per-project exception."""
    payload = load_json(root / SIGNOFF_REL, {})
    if not isinstance(payload, dict) or payload.get("approved") is not True:
        return False
    scope = str(payload.get("scope") or payload.get("stage") or "image").lower()
    if "image" not in scope and "生图" not in scope:
        return False
    backend = str(
        payload.get("channel")
        or payload.get("backend")
        or payload.get("canonical")
        or payload.get("image_backend")
        or ""
    ).lower()
    return "dreamina" in backend or "即梦" in backend or backend == "dreamina_official"


def require_dreamina_image_signoff(root: Path) -> None:
    if dreamina_image_signoff_allows(root):
        return
    raise RuntimeError(
        "全项目生图优先 Codex image2；Dreamina/即梦只能作为图片阶段签核例外。"
        f"如确需使用，请先写 {SIGNOFF_REL.as_posix()}，包含 "
        '{"approved": true, "scope": "image", "backend": "dreamina_official", "reason": "..."}'
    )


def extract_sections(markdown: str, wanted: Iterable[str] = KEY_SECTIONS) -> Dict[str, str]:
    """Return {heading: body} for level-2 sections in a prompt markdown file."""
    wanted_set = set(wanted)
    sections: Dict[str, list[str]] = {}
    current: Optional[str] = None
    for raw in markdown.splitlines():
        if raw.startswith("## "):
            heading = raw[3:].strip()
            current = heading if heading in wanted_set else None
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(raw)
    return {key: "\n".join(lines).strip() for key, lines in sections.items() if "\n".join(lines).strip()}


def build_prompt(prompt_file: Path) -> str:
    text = prompt_file.read_text(encoding="utf-8")
    sections = extract_sections(text)
    body = "\n".join(sections[key] for key in KEY_SECTIONS if sections.get(key)).strip()
    if not body:
        body = text.strip()
    return body


def run_dreamina_image(prompt: str, images: Sequence[str], *, ratio: str, resolution_type: str, model_version: str, poll: int) -> Dict[str, Any]:
    cmd = [
        "dreamina",
        "image2image" if images else "text2image",
    ]
    if images:
        cmd.extend(["--images", *images])
    cmd.extend([
        "--prompt", prompt,
        "--ratio", ratio,
        "--resolution_type", resolution_type,
        "--model_version", model_version,
        "--poll", str(poll),
    ])
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "dreamina text2image failed")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"dreamina returned non-JSON output: {exc}") from exc
    status = payload.get("gen_status")
    if status != "success":
        raise RuntimeError(f"dreamina task not successful: {status}; submit_id={payload.get('submit_id')}")
    images = ((payload.get("result_json") or {}).get("images") or [])
    if not images or not images[0].get("image_url"):
        raise RuntimeError(f"dreamina result has no image_url; submit_id={payload.get('submit_id')}")
    return payload


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read()
    if len(data) < 1024:
        raise RuntimeError(f"download too small: {target} bytes={len(data)}")
    target.write_bytes(data)


def job_matches(job: Mapping[str, Any], only: set[str]) -> bool:
    if not only:
        return True
    keys = {str(job.get("job_id") or ""), str(job.get("shot") or ""), Path(str(job.get("prompt") or "")).stem}
    return bool(keys & only)


def enforce_gate(root: Path) -> None:
    gate_cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "ad-craft" / "scripts" / "gate.py"),
                str(root), "--stage", "image"]
    gate = subprocess.run(gate_cmd, text=True)
    if gate.returncode:
        raise RuntimeError("ad image gate blocked paid generation")
    acceptance_cmd = [sys.executable, str(Path(__file__).resolve().parents[2] / "ad-craft" / "scripts" / "stage_acceptance.py"),
                      str(root), "--stage", "storyboard", "--mode", "rough"]
    acceptance = subprocess.run(acceptance_cmd, text=True)
    if acceptance.returncode:
        raise RuntimeError("storyboard stage acceptance blocked paid image generation")


def render_jobs(
    root: Path,
    *,
    only: set[str],
    limit: Optional[int],
    force: bool,
    ratio: str,
    resolution_type: str,
    model_version: str,
    poll: int,
) -> Dict[str, Any]:
    root = root.resolve()
    require_dreamina_image_signoff(root)
    enforce_gate(root)
    manifest_path = root / "出图" / "分镜" / "image_jobs_manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise FileNotFoundError(f"缺 image_jobs_manifest.json: {manifest_path}")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        raise RuntimeError("image_jobs_manifest.json 缺 jobs[]")

    rendered = skipped = failed = 0
    events_path = root / "生产数据" / "production_events.jsonl"
    for job in jobs:
        if not isinstance(job, dict) or not job_matches(job, only):
            continue
        if limit is not None and rendered >= limit:
            break
        out_rel = Path(str(job.get("expected_output") or ""))
        prompt_rel = Path(str(job.get("prompt") or ""))
        if not out_rel or not prompt_rel:
            continue
        out_path = root / out_rel
        prompt_path = root / prompt_rel
        if out_path.exists() and not force:
            job["status"] = "done"
            job.setdefault("backend", "Dreamina/即梦官方 CLI")
            job.setdefault("model", f"Dreamina Image {model_version}")
            job.setdefault("channel", "Dreamina/即梦官方 CLI/API")
            job.setdefault("output", out_rel.as_posix())
            skipped += 1
            continue
        try:
            prompt = build_prompt(prompt_path)
            refs = [root / str(p) for p in (job.get("reference_inputs") or [])]
            missing_refs = [str(p) for p in refs if not p.is_file()]
            if job.get("requires_image_input") and (not refs or missing_refs):
                raise RuntimeError(f"产品镜缺真实参考图输入：{missing_refs or 'reference_inputs=[]'}")
            payload = run_dreamina_image(
                prompt,
                [str(p) for p in refs],
                ratio=ratio,
                resolution_type=resolution_type,
                model_version=model_version,
                poll=poll,
            )
            image = ((payload.get("result_json") or {}).get("images") or [])[0]
            download(str(image["image_url"]), out_path)
            job.update({
                "status": "done",
                "backend": "Dreamina/即梦官方 CLI",
                "model": f"Dreamina Image {model_version}",
                "channel": "Dreamina/即梦官方 CLI/API",
                "model_version": model_version,
                "actual_reference_inputs": [str(p.relative_to(root)) for p in refs],
                "submit_id": payload.get("submit_id"),
                "credit_count": payload.get("credit_count"),
                "output": out_rel.as_posix(),
                "width": image.get("width"),
                "height": image.get("height"),
                "generated_at": now_iso(),
            })
            append_jsonl(events_path, {
                "ts": now_iso(),
                "stage": "image",
                "event": "generation",
                "generation": {
                    "method": "dreamina_official_cli_image2image" if refs else "dreamina_official_cli_text2image",
                    "asset": out_rel.as_posix(),
                    "prompt": prompt_rel.as_posix(),
                    "submit_id": payload.get("submit_id"),
                    "model_version": model_version,
                    "credit_count": payload.get("credit_count"),
                    "reference_inputs": [str(p.relative_to(root)) for p in refs],
                },
            })
            rendered += 1
            print(f"[ok] {job.get('job_id')} -> {out_rel} submit_id={payload.get('submit_id')}", flush=True)
        except Exception as exc:
            failed += 1
            job["status"] = "failed"
            job["error"] = str(exc)
            print(f"[block] {job.get('job_id')} {exc}", file=sys.stderr, flush=True)
            if not force:
                break
        finally:
            write_json(manifest_path, manifest)
            time.sleep(0.2)
    manifest["render_summary"] = {
        "backend": "Dreamina/即梦官方 CLI",
        "model": f"Dreamina Image {model_version}",
        "channel": "Dreamina/即梦官方 CLI/API",
        "model_version": model_version,
        "rendered": rendered,
        "skipped": skipped,
        "failed": failed,
        "updated_at": now_iso(),
    }
    write_json(manifest_path, manifest)
    return manifest["render_summary"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Dreamina 官方 CLI 渲染广告首/尾帧 PNG")
    ap.add_argument("project_root")
    ap.add_argument("--only", nargs="*", default=[], help="job_id / 镜头NN / prompt stem")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--ratio", default="9:16")
    ap.add_argument("--resolution-type", default="2k")
    ap.add_argument("--model-version", default="5.0")
    ap.add_argument("--poll", type=int, default=180)
    ns = ap.parse_args(argv)
    try:
        summary = render_jobs(
            Path(ns.project_root),
            only=set(ns.only),
            limit=ns.limit,
            force=ns.force,
            ratio=ns.ratio,
            resolution_type=ns.resolution_type,
            model_version=ns.model_version,
            poll=ns.poll,
        )
    except Exception as exc:
        print(f"[block] {exc}", file=sys.stderr, flush=True)
        return 2
    print(f"# Dreamina image render rendered={summary['rendered']} skipped={summary['skipped']} failed={summary['failed']}", flush=True)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
