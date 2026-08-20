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


AD_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(AD_LIB) not in sys.path:
    sys.path.insert(0, str(AD_LIB))
import io_utils  # noqa: E402  本线 _lib 原子写（账本落盘不可半写）

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import image_job_receipt  # noqa: E402  ad-image 自维护的逐图 B14 收据
import product_qc  # noqa: E402  当前像素落地后立即跑本线最完整 QC

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
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    io_utils.write_json_atomic(str(path), data)


def retry_call(fn, *, describe: str, attempts: int = RETRY_ATTEMPTS, base_delay: float = RETRY_BASE_DELAY):
    """幂等操作（下载/查询）的有限重试：指数退避，逐次记录。付费提交绝不走这里。"""
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            print(f"[retry] {describe} 第{attempt}/{attempts}次失败: {exc}", file=sys.stderr, flush=True)
            if attempt == attempts:
                raise
            time.sleep(base_delay * (2 ** (attempt - 1)))


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


def first_image(payload: Mapping[str, Any]) -> Dict[str, Any]:
    images = ((payload.get("result_json") or {}).get("images") or [])
    if not images or not images[0].get("image_url"):
        raise RuntimeError(f"dreamina result has no image_url; submit_id={payload.get('submit_id')}")
    return images[0]


def query_dreamina_result(submit_id: str) -> Dict[str, Any]:
    """按 submit_id 免费查询已提交任务（不重新扣费）。"""
    proc = subprocess.run(["dreamina", "query_result", "--submit_id", submit_id], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "dreamina query_result failed")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"dreamina query_result returned non-JSON output: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("dreamina query_result returned non-JSON object")
    status = str(payload.get("gen_status") or payload.get("status") or "").lower()
    if status and status != "success":
        raise RuntimeError(f"dreamina task not successful: {status}; submit_id={submit_id}")
    return payload


def collect_existing_image(job: Dict[str, Any], out_path: Path) -> Dict[str, Any]:
    """已付费 job 的免费取回：优先 query_result，退回记录的 result_url；都不可用则报错并保留 submit_id。

    绝不在这里重新提交——重新提交等于对同一 job 二次付费。
    """
    submit_id = str(job.get("submit_id") or "")
    query_error: Optional[Exception] = None
    try:
        payload = retry_call(lambda: query_dreamina_result(submit_id),
                             describe=f"query_result submit_id={submit_id}")
        image = first_image(payload)
        retry_call(lambda: download(str(image["image_url"]), out_path),
                   describe=f"download submit_id={submit_id}")
        return {"image": image, "retrieved_via": "query_result"}
    except Exception as exc:
        query_error = exc
    result_url = str(job.get("result_url") or "")
    if result_url:
        retry_call(lambda: download(result_url, out_path),
                   describe=f"download result_url submit_id={submit_id}")
        return {"image": {"image_url": result_url}, "retrieved_via": "result_url"}
    raise RuntimeError(
        f"已付费任务免费取回失败（query_result: {query_error}；无 result_url 记录）。"
        f"保留 submit_id={submit_id}，不会重新提交付费任务；请稍后重跑或人工用 "
        f"`dreamina query_result --submit_id {submit_id}` 取回。"
    )


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


def spent_credits(jobs: Sequence[Any]) -> float:
    """累计本 manifest 已付费消耗：有 submit_id 即已扣费；credit_count 缺失按 1 计。"""
    total = 0.0
    for job in jobs:
        if not isinstance(job, dict) or not job.get("submit_id"):
            continue
        credit = job.get("credit_count")
        total += float(credit) if isinstance(credit, (int, float)) and not isinstance(credit, bool) else 1.0
    return total


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


def prepare_image_receipt(root: Path, manifest: Mapping[str, Any], job: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Hard preflight wrapper kept injectable for unit tests; no runtime bypass flag."""
    return image_job_receipt.preflight(root, manifest, job, index)


def finish_image_receipt(root: Path, job: Dict[str, Any]) -> Dict[str, Any]:
    """Run full current-image QC and bind it to the output pixel SHA."""
    product_qc.run_qc(root / "出图" / "分镜", strict=True, refresh_vlm_tasks=True)
    return image_job_receipt.postflight(root, job)


def accepted_image_receipt(root: Path, job: Mapping[str, Any]) -> tuple[bool, str]:
    return image_job_receipt.current_accepted(root, job)


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
    max_credits: Optional[float] = None,
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

    rendered = skipped = failed = awaiting_review = qc_blocked = 0
    budget_halt: Optional[Dict[str, Any]] = None
    events_path = root / "生产数据" / "production_events.jsonl"
    for job_index, job in enumerate(jobs):
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
            accepted, _ = accepted_image_receipt(root, job)
            if accepted:
                job["status"] = "done"
                job.setdefault("backend", "Dreamina/即梦官方 CLI")
                job.setdefault("model", f"Dreamina Image {model_version}")
                job.setdefault("channel", "Dreamina/即梦官方 CLI/API")
                job.setdefault("output", out_rel.as_posix())
                skipped += 1
                continue
            # 文件存在不等于通过：旧图/刚落地图先补当前 preflight + postflight，
            # 收据未显式签收前绝不继续下一张。
            try:
                prepare_image_receipt(root, manifest, job, job_index)
                receipt = finish_image_receipt(root, job)
                if receipt.get("status") == "accepted":  # 仅测试注入可达；正式 postflight 必须等人工签核
                    job["status"] = "done"
                    skipped += 1
                    continue
                job["status"] = "awaiting_human_signoff"
                awaiting_review += 1
                print(f"[review] {job.get('job_id')} 已完成机器 QC，须按当前像素 SHA 人工并排签收", flush=True)
            except image_job_receipt.ReceiptBlocked as exc:
                job["status"] = "qc_blocked"
                job["error"] = str(exc)
                failed += 1
                qc_blocked += 1
                print(f"[block] {job.get('job_id')} {exc}", file=sys.stderr, flush=True)
            write_json(manifest_path, manifest)
            break
        existing_submit_id = str(job.get("submit_id") or "")
        if existing_submit_id:
            # 已付费未落图：免费取回，绝不重新提交（与兄弟脚本 existing_submit_id 语义一致）
            try:
                collected = collect_existing_image(job, out_path)
                image = collected.get("image") or {}
                job.update({
                    "status": "output_ready",
                    "backend": "Dreamina/即梦官方 CLI",
                    "model": f"Dreamina Image {model_version}",
                    "channel": "Dreamina/即梦官方 CLI/API",
                    "output": out_rel.as_posix(),
                    "retrieved_via": collected.get("retrieved_via"),
                    "generated_at": now_iso(),
                })
                job.pop("error", None)
                rendered += 1
                print(f"[ok] {job.get('job_id')} -> {out_rel} submit_id={existing_submit_id} (免费取回)", flush=True)
                try:
                    prepare_image_receipt(root, manifest, job, job_index)
                    receipt = finish_image_receipt(root, job)
                    if receipt.get("status") == "accepted":
                        job["status"] = "done"
                    else:
                        job["status"] = "awaiting_human_signoff"
                        awaiting_review += 1
                except image_job_receipt.ReceiptBlocked as exc:
                    job["status"] = "qc_blocked"
                    job["error"] = str(exc)
                    failed += 1
                    qc_blocked += 1
            except Exception as exc:
                failed += 1
                job["status"] = "collect_pending"
                job["error"] = str(exc)
                print(f"[block] {job.get('job_id')} {exc}", file=sys.stderr, flush=True)
                if not force:
                    break
            finally:
                write_json(manifest_path, manifest)
                time.sleep(0.2)
            # 免费取回也必须在当前图完成签收；不批量越过这张继续提交后续付费 job。
            break
        if max_credits is not None:
            spent = spent_credits(jobs)
            if spent >= max_credits:
                budget_halt = {"stopped_before": str(job.get("job_id") or ""), "spent_credits": spent}
                print(f"[budget] 已消耗 credit={spent} >= --max-credits {max_credits}，"
                      f"停止在 {job.get('job_id')} 之前，不再提交付费任务", file=sys.stderr, flush=True)
                break
        try:
            # B14 前闸：真实参考非空、可解码、带用途/owner/SHA；上一张必须仍按当前
            # 像素 SHA accepted。--force 只允许重抽当前图，不能跳过前闸。
            prepare_image_receipt(root, manifest, job, job_index)
            prompt = build_prompt(prompt_path)
            refs = [root / str(p) for p in (job.get("reference_inputs") or [])]
            missing_refs = [str(p) for p in refs if not p.is_file()]
            if not refs or missing_refs:
                raise RuntimeError(f"逐图生成缺真实参考图输入：{missing_refs or 'reference_inputs=[]'}")
            payload = run_dreamina_image(
                prompt,
                [str(p) for p in refs],
                ratio=ratio,
                resolution_type=resolution_type,
                model_version=model_version,
                poll=poll,
            )
            image = first_image(payload)
            # 提交已扣费：先原子落盘 submit_id/result_url 再下载，下载失败也不丢取回凭据
            job.update({
                "status": "collect_pending",
                "backend": "Dreamina/即梦官方 CLI",
                "model": f"Dreamina Image {model_version}",
                "channel": "Dreamina/即梦官方 CLI/API",
                "model_version": model_version,
                "actual_reference_inputs": [str(p.relative_to(root)) for p in refs],
                "submit_id": payload.get("submit_id"),
                "credit_count": payload.get("credit_count"),
                "result_url": image.get("image_url"),
                "submitted_at": now_iso(),
            })
            write_json(manifest_path, manifest)
            retry_call(lambda: download(str(image["image_url"]), out_path),
                       describe=f"download {job.get('job_id')}")
            job.update({
                "status": "output_ready",
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
            receipt = finish_image_receipt(root, job)
            if receipt.get("status") == "accepted":
                job["status"] = "done"
            else:
                job["status"] = "awaiting_human_signoff"
                awaiting_review += 1
                print(f"[review] {job.get('job_id')} 已完成机器 QC，须按当前像素 SHA 人工并排签收", flush=True)
            # 正式 postflight 只会到 awaiting_human_signoff；当前图未签收，不得生成下一张。
            if job["status"] != "done":
                write_json(manifest_path, manifest)
                break
        except image_job_receipt.ReceiptBlocked as exc:
            failed += 1
            qc_blocked += 1
            job["status"] = "qc_blocked" if out_path.exists() else "preflight_blocked"
            job["error"] = str(exc)
            print(f"[block] {job.get('job_id')} {exc}", file=sys.stderr, flush=True)
            break
        except Exception as exc:
            failed += 1
            # 已有 submit_id ⇒ 已付费，落可续跑状态；重跑走免费取回，不再二次付费
            job["status"] = "collect_pending" if job.get("submit_id") else "failed"
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
        "awaiting_human_signoff": awaiting_review,
        "qc_blocked": qc_blocked,
        "updated_at": now_iso(),
    }
    if max_credits is not None:
        unrun = [str(j.get("job_id") or "") for j in jobs
                 if isinstance(j, dict) and job_matches(j, only)
                 and not j.get("submit_id") and not (root / str(j.get("expected_output") or "")).exists()]
        manifest["render_summary"]["budget"] = {
            "max_credits": max_credits,
            "spent_credits": spent_credits(jobs),
            "halted": budget_halt is not None,
            "unrun_jobs": unrun,
            **(budget_halt or {}),
        }
        if budget_halt is not None:
            print(f"[budget] 剩余未跑 job：{'、'.join(unrun) or '无'}", file=sys.stderr, flush=True)
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
    ap.add_argument("--max-credits", type=float, default=None,
                    help="本 manifest 累计 credit 封顶；付费提交前检查，超限停止（默认不设限）")
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
            max_credits=ns.max_credits,
        )
    except Exception as exc:
        print(f"[block] {exc}", file=sys.stderr, flush=True)
        return 2
    print(
        f"# Dreamina image render rendered={summary['rendered']} skipped={summary['skipped']} "
        f"failed={summary['failed']} awaiting_human_signoff={summary['awaiting_human_signoff']}",
        flush=True,
    )
    return 1 if summary["failed"] or summary["awaiting_human_signoff"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
