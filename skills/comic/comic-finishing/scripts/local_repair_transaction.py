#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provider-neutral, SHA-bound local panel repair transaction.

``prepare`` freezes the active master/current panel, edit mask, bbox and prompt.
An external editor/provider writes the proposed full-size master to the printed
candidate path.  ``commit`` verifies that only masked pixels changed, stages a
before/after packet, atomically promotes immutable raw/master/panel derivatives,
reruns current-pixel post-QC, and rolls back on every deterministic failure.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


COMIC_IMAGE_SCRIPTS = Path(__file__).resolve().parents[2] / "comic-image" / "scripts"
if str(COMIC_IMAGE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(COMIC_IMAGE_SCRIPTS))
import codex_panel_runner as image_runner  # noqa: E402


KIND = "comic_local_repair_transaction"


def project_path(root: Path, raw: str | Path) -> Path:
    path = Path(raw).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def parse_bbox(raw: str) -> dict[str, int]:
    try:
        x, y, w, h = [int(item.strip()) for item in raw.split(",")]
    except (TypeError, ValueError) as exc:
        raise ValueError("--bbox 必须是 x,y,w,h 四个整数") from exc
    if min(x, y) < 0 or min(w, h) <= 0:
        raise ValueError("bbox 必须位于非负坐标且宽高大于 0")
    return {"x": x, "y": y, "w": w, "h": h}


def load_job(root: Path, chapter: str, panel_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    data = image_runner.load_json(jobs_path)
    job = next(
        (item for item in data.get("jobs") or [] if isinstance(item, dict) and str(item.get("panel_id") or "") == panel_id),
        None,
    )
    if not isinstance(job, dict):
        raise ValueError(f"unknown panel: {panel_id}")
    return jobs_path, data, job


def validate_mask(source: Path, mask: Path, bbox: dict[str, int]) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(source) as src, Image.open(mask) as msk:
            size = src.size
            mask_size = msk.size
            mask_l = msk.convert("L")
            extrema = mask_l.getextrema()
            mask_bounds = mask_l.getbbox()
    except (ImportError, OSError) as exc:
        raise ValueError(f"无法解码 source/mask: {exc}") from exc
    if size != mask_size:
        raise ValueError(f"mask {mask_size} 必须与 source master {size} 同尺寸")
    x, y, w, h = (bbox[key] for key in ("x", "y", "w", "h"))
    if x + w > size[0] or y + h > size[1]:
        raise ValueError("bbox 超出 source master")
    if not extrema or extrema[1] <= 0:
        raise ValueError("mask 为空；局部修复不得用空 mask")
    if not mask_bounds:
        raise ValueError("mask 为空；局部修复不得用空 mask")
    left, top, right, bottom = mask_bounds
    if left < x or top < y or right > x + w or bottom > y + h:
        raise ValueError("mask 非零区域必须完整位于声明 bbox 内")
    return size


def transaction_dir(root: Path, chapter: str, panel_id: str, transaction_id: str) -> Path:
    return root / "生产数据" / "repair_staging" / chapter / panel_id / transaction_id


def prepare(root: Path, chapter: str, panel_id: str, mask: Path, bbox: dict[str, int], prompt: str) -> Path:
    _jobs_path, _data, job = load_job(root, chapter, panel_id)
    master = image_runner.resolve_path(root, str(job.get("master_path") or f"出图/{chapter}/masters/{panel_id}.png"))
    panel = image_runner.resolve_path(root, str(job.get("result_path") or f"出图/{chapter}/panels/{panel_id}.png"))
    if not image_runner.png_valid(master) or not image_runner.png_valid(panel):
        raise ValueError("当前 active master/panel 不完整，不能准备局部修复")
    mask = project_path(root, mask)
    validate_mask(master, mask, bbox)
    material = {
        "kind": KIND,
        "chapter": chapter,
        "panel_id": panel_id,
        "source_master_sha256": image_runner.file_sha256(master),
        "source_panel_sha256": image_runner.file_sha256(panel),
        "mask_sha256": image_runner.file_sha256(mask),
        "bbox": bbox,
        "edit_prompt": prompt.strip(),
        "execution_input_sha256": str(job.get("execution_input_sha256") or ""),
    }
    if not material["edit_prompt"]:
        raise ValueError("--edit-prompt 必填")
    transaction_id = canonical_sha(material)[:20]
    stage = transaction_dir(root, chapter, panel_id, transaction_id)
    stage.mkdir(parents=True, exist_ok=True)
    before = stage / "before_master.png"
    current_panel = stage / "before_panel.png"
    frozen_mask = stage / "mask.png"
    image_runner.atomic_copy(master, before)
    image_runner.atomic_copy(panel, current_panel)
    image_runner.atomic_copy(mask, frozen_mask)
    payload = {
        "schema_version": 1,
        **material,
        "transaction_id": transaction_id,
        "status": "prepared",
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source_master_path": image_runner.rel_to_root(root, master),
        "source_panel_path": image_runner.rel_to_root(root, panel),
        "frozen_before_path": image_runner.rel_to_root(root, before),
        "frozen_panel_path": image_runner.rel_to_root(root, current_panel),
        "frozen_mask_path": image_runner.rel_to_root(root, frozen_mask),
        "candidate_path": image_runner.rel_to_root(root, stage / "after_candidate.png"),
    }
    payload["contract_sha256"] = canonical_sha({key: value for key, value in payload.items() if key != "contract_sha256"})
    receipt = stage / "repair_transaction.json"
    image_runner.write_json(receipt, payload)
    return receipt


def changes_only_inside_mask(before: Path, after: Path, mask: Path) -> bool:
    try:
        from PIL import Image, ImageChops, ImageStat
        with Image.open(before) as old, Image.open(after) as new, Image.open(mask) as raw_mask:
            if old.size != new.size or old.size != raw_mask.size:
                return False
            old_rgba = old.convert("RGBA")
            new_rgba = new.convert("RGBA")
            outside = ImageChops.invert(raw_mask.convert("L"))
            diff = ImageChops.difference(old_rgba, new_rgba)
            outside_diff = Image.composite(diff, Image.new("RGBA", diff.size), outside)
            return sum(ImageStat.Stat(outside_diff).sum) == 0
    except (ImportError, OSError):
        return False


def before_after_sheet(before: Path, after: Path, out: Path) -> None:
    from PIL import Image, ImageDraw
    with Image.open(before) as old, Image.open(after) as new:
        old = old.convert("RGB")
        new = new.convert("RGB")
        old.thumbnail((720, 720), Image.Resampling.LANCZOS)
        new.thumbnail((720, 720), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (old.width + new.width, max(old.height, new.height) + 36), (30, 30, 32))
        canvas.paste(old, (0, 36))
        canvas.paste(new, (old.width, 36))
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 10), "BEFORE", fill=(240, 240, 240))
        draw.text((old.width + 12, 10), "AFTER CANDIDATE", fill=(240, 240, 240))
        canvas.save(out, "PNG")


def commit(root: Path, receipt_path: Path, candidate: Path | None) -> Path:
    receipt_path = project_path(root, receipt_path)
    tx = image_runner.load_json(receipt_path)
    if tx.get("kind") != KIND or tx.get("status") != "prepared":
        raise ValueError("repair transaction 必须是 prepared 且只能 commit 一次")
    expected_contract_sha = canonical_sha({key: value for key, value in tx.items() if key != "contract_sha256"})
    if expected_contract_sha != str(tx.get("contract_sha256") or ""):
        raise ValueError("repair transaction contract SHA 不匹配")
    chapter = str(tx.get("chapter") or "")
    panel_id = str(tx.get("panel_id") or "")
    jobs_path, data, job = load_job(root, chapter, panel_id)
    master = image_runner.resolve_path(root, str(tx.get("source_master_path") or ""))
    panel = image_runner.resolve_path(root, str(tx.get("source_panel_path") or ""))
    if image_runner.file_sha256(master) != tx.get("source_master_sha256") or image_runner.file_sha256(panel) != tx.get("source_panel_sha256"):
        raise ValueError("active master/panel 已变化；旧 repair transaction 自动失效")
    if str(job.get("execution_input_sha256") or "") != str(tx.get("execution_input_sha256") or ""):
        raise ValueError("panel execution contract 已变化；重新 prepare")
    before = image_runner.resolve_path(root, str(tx.get("frozen_before_path") or ""))
    before_panel = image_runner.resolve_path(root, str(tx.get("frozen_panel_path") or ""))
    mask = image_runner.resolve_path(root, str(tx.get("frozen_mask_path") or ""))
    if image_runner.file_sha256(before) != tx.get("source_master_sha256") or image_runner.file_sha256(mask) != tx.get("mask_sha256"):
        raise ValueError("frozen source/mask 已变化")
    candidate = project_path(root, candidate or str(tx.get("candidate_path") or ""))
    if not image_runner.png_valid(candidate):
        raise ValueError("repair candidate 缺失或不是有效 PNG")
    validate_mask(before, mask, tx.get("bbox") or {})
    if image_runner.file_sha256(candidate) == tx.get("source_master_sha256"):
        raise ValueError("repair candidate 与 source master 完全相同")
    if not changes_only_inside_mask(before, candidate, mask):
        raise ValueError("candidate 在 mask 外改变了像素；事务拒绝且不覆盖当前 master/panel")
    sheet = receipt_path.parent / "before_after.png"
    before_after_sheet(before, candidate, sheet)
    staged_candidate = receipt_path.parent / "commit_candidate.png"
    image_runner.atomic_copy(candidate, staged_candidate)
    old_job = json.loads(json.dumps(job, ensure_ascii=False))
    qc_path = root / "生产数据" / "panel_qc" / chapter / f"{panel_id}.json"
    old_qc_backup = receipt_path.parent / "before_post_qc.json"
    if qc_path.is_file():
        shutil.copy2(qc_path, old_qc_backup)
    old_packet = (old_job.get("post_qc") or {}).get("visual_review_packet") if isinstance(old_job.get("post_qc"), dict) else {}
    old_contact_raw = str(old_packet.get("contact_sheet_path") or "") if isinstance(old_packet, dict) else ""
    old_contact = image_runner.resolve_path(root, old_contact_raw) if old_contact_raw else Path()
    old_contact_backup = receipt_path.parent / "before_contact_sheet.png"
    if old_contact_raw and old_contact.is_file():
        image_runner.atomic_copy(old_contact, old_contact_backup)
    new_contact = root / "生产数据" / "panel_qc" / chapter / f"{panel_id}_contact_sheet.png"
    try:
        provenance = image_runner.promote_generated_artifacts(
            root,
            chapter,
            panel_id,
            staged_candidate,
            panel,
            job.get("size") or {},
            attempt=0,
            resize=True,
        )
        job["master_path"] = provenance["master_path"]
        job["raw_candidate_path"] = provenance["raw_candidate_path"]
        job["resolution_provenance"] = provenance
        references = image_runner.collect_reference_images(root, job)
        post_qc = image_runner.post_qc_panel(
            root,
            chapter,
            job,
            panel,
            references,
            adjacent_paths=image_runner.previous_accepted_panel_paths(root, data.get("jobs") or [], panel_id),
        )
        if str(post_qc.get("verdict") or "") == "block":
            raise ValueError("repaired current pixel failed deterministic post-QC")
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        job.update({
            "status": image_runner.status_after_post_qc(post_qc),
            "artifact_sha256": image_runner.file_sha256(panel),
            "post_qc": post_qc,
            "generated_at": now,
            "generated_from_execution_input_sha256": str(job.get("execution_input_sha256") or ""),
            "repair_transaction": {
                "transaction_id": tx["transaction_id"],
                "contract_sha256": tx["contract_sha256"],
                "mask_sha256": tx["mask_sha256"],
                "edit_prompt_sha256": hashlib.sha256(str(tx["edit_prompt"]).encode("utf-8")).hexdigest(),
                "before_after_path": image_runner.rel_to_root(root, sheet),
                "before_after_sha256": image_runner.file_sha256(sheet),
            },
        })
        job.pop("accepted_at", None)
        image_runner.write_json(jobs_path, data)
    except BaseException:
        image_runner.atomic_copy(before, master)
        image_runner.atomic_copy(before_panel, panel)
        if old_qc_backup.is_file():
            shutil.copy2(old_qc_backup, qc_path)
        else:
            qc_path.unlink(missing_ok=True)
        if old_contact_raw:
            if old_contact_backup.is_file():
                image_runner.atomic_copy(old_contact_backup, old_contact)
            else:
                old_contact.unlink(missing_ok=True)
        elif new_contact.is_file():
            new_contact.unlink(missing_ok=True)
        job.clear()
        job.update(old_job)
        raise
    tx.update({
        "status": "committed_awaiting_current_pixel_review",
        "committed_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "candidate_sha256": image_runner.file_sha256(candidate),
        "current_pixel_sha256": image_runner.file_sha256(panel),
        "before_after_path": image_runner.rel_to_root(root, sheet),
        "before_after_sha256": image_runner.file_sha256(sheet),
        "post_qc_path": f"生产数据/panel_qc/{chapter}/{panel_id}.json",
    })
    tx["completion_sha256"] = canonical_sha({key: value for key, value in tx.items() if key != "completion_sha256"})
    image_runner.write_json(receipt_path, tx)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Comic provider-neutral 局部修复事务")
    parser.add_argument("project_root")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--chapter", default="第1话")
    prep.add_argument("--panel", required=True)
    prep.add_argument("--mask", required=True)
    prep.add_argument("--bbox", required=True, help="x,y,w,h（master 像素坐标）")
    prep.add_argument("--edit-prompt", required=True)
    finish = sub.add_parser("commit")
    finish.add_argument("receipt")
    finish.add_argument("--candidate", default="")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    try:
        if args.command == "prepare":
            out = prepare(root, args.chapter, args.panel, Path(args.mask), parse_bbox(args.bbox), args.edit_prompt)
            tx = image_runner.load_json(out)
            print(f"[prepared] {out}")
            print(f"[candidate] {image_runner.resolve_path(root, tx['candidate_path'])}")
        else:
            out = commit(root, Path(args.receipt), Path(args.candidate) if args.candidate else None)
            print(f"[committed] {out}；当前像素必须重新走结构化逐轴 B14 签收")
    except (OSError, ValueError) as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
