#!/usr/bin/env python3
"""Final-pixel QC for subtitles, CTA, prices, claims and legal copy.

Tesseract/OCR and pixel contrast are locators, not semantic judges.  Automated
OCR mismatch and contrast remain WARN.  A human-corrected observed_text with a
queryable evidence record becomes deterministic and exact-copy mismatch blocks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Mapping


KIND = "ad_rendered_text_qc"
PLAN_KIND = "ad_rendered_text_plan"
SCHEMA_VERSION = 1


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(text: str):
    text = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff%]+", "", text)


def evidence_exists(root: Path, value: Any):
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def _extract(path: Path, at: float, out: Path):
    exe = shutil.which("ffmpeg")
    if not exe or not path.is_file():
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([exe, "-y", "-v", "error", "-ss", f"{max(0, at):.3f}", "-i", str(path),
                           "-frames:v", "1", str(out)], capture_output=True)
    return proc.returncode == 0 and out.is_file()


def _image_size(path: Path):
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def _ocr(path: Path):
    exe = shutil.which("tesseract")
    if not exe or not path.is_file():
        return None
    proc = subprocess.run([exe, str(path), "stdout", "tsv"], capture_output=True, text=True)
    if proc.returncode:
        return None
    words = []
    for line in proc.stdout.splitlines()[1:]:
        cells = line.split("\t")
        if len(cells) < 12 or not cells[11].strip():
            continue
        try:
            words.append({"text": cells[11].strip(), "confidence": float(cells[10]),
                          "bbox": [int(cells[6]), int(cells[7]), int(cells[8]), int(cells[9])]})
        except ValueError:
            continue
    return {"text": " ".join(row["text"] for row in words), "words": words}


def _relative_luminance(rgb):
    values = []
    for value in rgb:
        value = value / 255.0
        values.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast_estimate(path: Path, bbox_norm):
    try:
        from PIL import Image  # type: ignore
        image = Image.open(path).convert("RGB")
        width, height = image.size
        x, y, w, h = [float(v) for v in bbox_norm]
        crop = image.crop((max(0, int(x * width)), max(0, int(y * height)),
                           min(width, int((x + w) * width)), min(height, int((y + h) * height))))
        sample = crop.resize((min(128, max(1, crop.width)), min(64, max(1, crop.height))))
        pixels = list(sample.get_flattened_data() if hasattr(sample, "get_flattened_data") else sample.getdata())
        if not pixels:
            return None
        lum = sorted(_relative_luminance(pixel) for pixel in pixels)
        dark = lum[max(0, int(len(lum) * 0.1) - 1)]
        light = lum[min(len(lum) - 1, int(len(lum) * 0.9))]
        return round((light + 0.05) / (dark + 0.05), 3)
    except Exception:
        return None


def _inside(inner, outer):
    try:
        x, y, w, h = [float(v) for v in inner]; ox, oy, ow, oh = [float(v) for v in outer]
        return x >= ox and y >= oy and x + w <= ox + ow and y + h <= oy + oh
    except Exception:
        return False


def _srt_seconds(raw: str):
    match = re.fullmatch(r"\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*", raw)
    if not match:
        return None
    hours, minutes, seconds, millis = (int(value) for value in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def _subtitle_rows(root: Path):
    path = root / "脚本" / "字幕_zh.srt"
    if not path.is_file():
        path = root / "脚本" / "字幕_en.srt"
    if not path.is_file():
        return []
    rows = []
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    for pos, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_pos = next((idx for idx, line in enumerate(lines) if "-->" in line), None)
        if timing_pos is None:
            continue
        start_raw, end_raw = (part.strip() for part in lines[timing_pos].split("-->", 1))
        start, end = _srt_seconds(start_raw), _srt_seconds(end_raw)
        text = " ".join(lines[timing_pos + 1:])
        if start is None or end is None or end <= start or not text:
            continue
        rows.append({"id": f"subtitle:{pos:03d}", "kind": "subtitle", "expected_text": text,
                     "timestamp": (start + end) / 2, "start": start, "end": end})
    return rows


def _story_texts(brief: Mapping[str, Any], storyboard: Mapping[str, Any]):
    rows = []
    raw_claims = brief.get("claims") or []
    if isinstance(raw_claims, Mapping):
        raw_claims = [raw_claims]
    claims = {str(row.get("id") or f"claim_{pos:02d}"): str(row.get("claim") or "")
              for pos, row in enumerate(raw_claims, 1) if isinstance(row, Mapping)}
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    cursor = 0.0
    for pos, shot in enumerate(shots, 1):
        if not isinstance(shot, Mapping):
            continue
        duration = float(shot.get("duration") or shot.get("duration_sec") or 0)
        sid = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"S{pos:02d}")
        legal = shot.get("legal_lines") or []
        if isinstance(legal, str):
            legal = [legal]
        for idx, text in enumerate(legal, 1):
            rows.append({"id": f"{sid}:legal:{idx}", "kind": "legal", "expected_text": str(text),
                         "timestamp": cursor + duration * 0.5, "start": cursor, "end": cursor + duration})
        claim_ids = shot.get("claim_ids") or []
        if isinstance(claim_ids, str):
            claim_ids = [claim_ids]
        for claim_id in claim_ids:
            text = claims.get(str(claim_id), "")
            if text:
                rows.append({"id": f"{sid}:claim:{claim_id}", "kind": "claim", "expected_text": text,
                             "timestamp": cursor + duration * 0.5, "start": cursor, "end": cursor + duration})
        for field in ("on_screen_text", "screen_text", "super_text", "price_text", "cta"):
            values = shot.get(field) or []
            if isinstance(values, str):
                values = [values]
            for idx, text in enumerate(values, 1) if isinstance(values, list) else []:
                if str(text).strip():
                    rows.append({"id": f"{sid}:{field}:{idx}", "kind": field, "expected_text": str(text),
                                 "timestamp": cursor + duration * 0.5, "start": cursor, "end": cursor + duration})
        disclosures = shot.get("disclosures") or []
        if isinstance(disclosures, Mapping):
            disclosures = [disclosures]
        for idx, disclosure in enumerate(disclosures, 1):
            if not isinstance(disclosure, Mapping):
                continue
            for field in ("text", "source_text"):
                if disclosure.get(field):
                    rows.append({"id": f"{sid}:disclosure:{idx}:{field}", "kind": "disclosure",
                                 "expected_text": str(disclosure[field]), "timestamp": cursor + duration * 0.5,
                                 "start": cursor, "end": cursor + duration})
        cursor += duration
    mand = brief.get("mandatories") if isinstance(brief.get("mandatories"), Mapping) else {}
    cta = mand.get("endcard_cta") or mand.get("cta")
    if cta:
        rows.append({"id": "endcard:cta", "kind": "cta", "expected_text": str(cta),
                     "timestamp": max(0.0, cursor - 1.0), "start": max(0.0, cursor - 3.0), "end": cursor})
    return rows


def template(root: Path):
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    storyboard = load(root / "脚本" / "storyboard.json", {}) or {}
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    texts = _subtitle_rows(root) + _story_texts(brief, storyboard)
    checks = []
    for item in plan.get("deliverables") or []:
        if item.get("status") == "cancelled" or not item.get("deliverable_id"):
            continue
        did = str(item["deliverable_id"])
        for row in texts:
            generated = dict(row)
            generated.update({"id": f"{did}:{row['id']}", "deliverable_id": did,
                              "timestamp": row["timestamp"] if did == "master" else "待补",
                              "start": row["start"] if did == "master" else "待补",
                              "end": row["end"] if did == "master" else "待补",
                              "bbox_norm": "待补", "safe_zone_norm": "待补", "min_contrast": 4.5,
                              "observed_text": "", "observed_by": "", "observed_evidence": "",
                              "contrast_approved": False, "duration_approved": False,
                              "occlusion_approved": False})
            checks.append(generated)
    return {"schema_version": SCHEMA_VERSION, "kind": PLAN_KIND, "checks": checks,
            "note": "timestamp/bbox/safe-zone 必须按每个最终版位填写；自动 OCR 仅定位，具名人审裁决。"}


def build(root: Path, plan: Mapping[str, Any] | None = None):
    root = root.resolve()
    plan_path = root / "合规" / "rendered_text_plan.json"
    plan = plan if isinstance(plan, Mapping) else load(plan_path, {}) or {}
    delivery = load(root / "合成" / "delivery_plan.json", {}) or {}
    by_id = {str(row.get("deliverable_id")): row for row in delivery.get("deliverables") or [] if row.get("deliverable_id")}
    findings = []
    results = []
    if not plan:
        findings.append({"severity": "block", "code": "rendered_text_plan_missing", "msg": "缺 合规/rendered_text_plan.json"})
    covered = set()
    for pos, check in enumerate(plan.get("checks") or [], 1):
        if not isinstance(check, Mapping):
            findings.append({"severity": "block", "code": "rendered_text_check_malformed", "msg": f"check {pos} 非对象"})
            continue
        did = str(check.get("deliverable_id") or "")
        item = by_id.get(did)
        expected = str(check.get("expected_text") or "")
        missing = [key for key in ("id", "deliverable_id", "kind", "expected_text", "timestamp", "start", "end", "bbox_norm", "safe_zone_norm")
                   if check.get(key) in (None, "", "待补")]
        if missing or not item:
            findings.append({"severity": "block", "code": "rendered_text_check_incomplete",
                             "msg": f"check {check.get('id') or pos} 缺/无效：{', '.join(missing or ['deliverable_id'])}"})
            continue
        covered.add(did)
        try:
            at, start, end = float(check["timestamp"]), float(check["start"]), float(check["end"])
            bbox = [float(v) for v in check["bbox_norm"]]
            safe = [float(v) for v in check["safe_zone_norm"]]
        except Exception:
            findings.append({"severity": "block", "code": "rendered_text_measurement_invalid",
                             "msg": f"check {check.get('id')} 时间/坐标不可解析"})
            continue
        if end <= start or not (start <= at <= end) or len(bbox) != 4 or len(safe) != 4:
            findings.append({"severity": "block", "code": "rendered_text_measurement_invalid",
                             "msg": f"check {check.get('id')} 时间窗或坐标无效"})
            continue
        media = root / str(item.get("expected_path") or "")
        frame = root / "合成" / "rendered_text_frames" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', str(check['id']))}.jpg"
        extracted = _extract(media, at, frame)
        if not extracted:
            findings.append({"severity": "block", "code": "rendered_text_frame_missing", "msg": f"{check['id']} 无法从最终交付件抽帧"})
            continue
        automated = _ocr(frame)
        contrast = contrast_estimate(frame, bbox)
        if automated is None:
            findings.append({"severity": "warn", "code": "ocr_adapter_unavailable",
                             "msg": f"{check['id']} 无本地 tesseract；已抽帧，须具名人工核对精确文案"})
        elif normalize(expected) not in normalize(automated["text"]):
            findings.append({"severity": "warn", "code": "automated_ocr_mismatch",
                             "msg": f"{check['id']} 自动 OCR 未完整定位预期文案；OCR 为启发式，须人工裁决",
                             "confidence": "heuristic"})
        observed = str(check.get("observed_text") or "")
        manual_flags = {key: check.get(key) is True for key in
                        ("contrast_approved", "duration_approved", "occlusion_approved")}
        if (not observed or not check.get("observed_by") or
                not evidence_exists(root, check.get("observed_evidence")) or not all(manual_flags.values())):
            findings.append({"severity": "block", "code": "rendered_manual_confirmation_missing",
                             "msg": f"{check['id']} 缺具名最终文字、对比度、停留时间或遮挡逐项确认及证据"})
        elif normalize(observed) != normalize(expected):
            findings.append({"severity": "block", "code": "rendered_exact_copy_mismatch",
                             "msg": f"{check['id']} 人工确认的最终文字与批准文案不一致"})
        if contrast is None:
            findings.append({"severity": "warn", "code": "contrast_unmeasured", "msg": f"{check['id']} 无法估算像素对比度"})
        elif contrast < float(check.get("min_contrast") or 4.5):
            findings.append({"severity": "warn", "code": "contrast_house_warn",
                             "msg": f"{check['id']} 像素区域对比度快筛约 {contrast}:1；须按实际文字边缘和 WCAG/客户目标人工复核",
                             "confidence": "heuristic"})
        if not _inside(bbox, safe):
            findings.append({"severity": "block", "code": "rendered_text_outside_safe_zone",
                             "msg": f"{check['id']} 登记文字框超出该版位机器安全区"})
        duration = end - start
        if duration < 0.7:
            findings.append({"severity": "warn", "code": "rendered_text_duration_house_warn",
                             "msg": f"{check['id']} 仅展示 {duration:.2f}s；内部快筛，须实机审读"})
        results.append({"id": check["id"], "deliverable_id": did, "kind": check["kind"],
                        "expected_text": expected, "frame": frame.relative_to(root).as_posix(), "frame_sha256": sha(frame),
                        "ocr": automated, "contrast_estimate": contrast, "duration_seconds": duration,
                        "bbox_norm": bbox, "safe_zone_norm": safe, "manual_observed_text": observed})
    active = {str(row.get("deliverable_id")) for row in delivery.get("deliverables") or []
              if row.get("status") != "cancelled" and row.get("deliverable_id")}
    brief = load(root / "需求" / "brief.json", {}) or {}
    storyboard = load(root / "脚本" / "storyboard.json", {}) or {}
    expected_base = _subtitle_rows(root) + _story_texts(brief, storyboard)
    required_ids = {f"{did}:{row['id']}" for did in active for row in expected_base}
    exclusions = {}
    for row in plan.get("not_applicable") or []:
        if not isinstance(row, Mapping) or not row.get("id"):
            continue
        valid = (bool(row.get("reason")) and bool(row.get("approved_by")) and
                 evidence_exists(root, row.get("evidence")))
        exclusions[str(row["id"])] = valid
        if not valid:
            findings.append({"severity": "block", "code": "rendered_text_exclusion_invalid",
                             "msg": f"{row.get('id')} not_applicable 缺 reason/approved_by/evidence"})
    present_ids = {str(row.get("id")) for row in plan.get("checks") or [] if isinstance(row, Mapping) and row.get("id")}
    missing_contract = sorted(required_ids - present_ids - {key for key, valid in exclusions.items() if valid})
    if missing_contract:
        findings.append({"severity": "block", "code": "rendered_text_contract_uncovered",
                         "msg": "批准字幕/CTA/价格/claim/法律声明未逐项进入最终像素检查：" +
                                ", ".join(missing_contract[:12]) + ("…" if len(missing_contract) > 12 else "")})
    missing_variants = sorted(active - covered) if expected_base else []
    if missing_variants:
        findings.append({"severity": "block", "code": "rendered_text_variant_uncovered",
                         "msg": "以下交付件没有最终文字检查：" + ", ".join(missing_variants)})
    return {"schema_version": SCHEMA_VERSION, "kind": KIND, "plan_sha256": sha(plan_path),
            "qc_environment": {"ffmpeg": bool(shutil.which("ffmpeg")), "tesseract": bool(shutil.which("tesseract")),
                               "pillow": _image_size(next((root / row["frame"] for row in results), Path())) is not None if results else False},
            "checks": results, "findings": findings,
            "standards": [{"authority": "W3C_WCAG_2_2", "criterion": "1.4.3 Contrast (Minimum)",
                           "source": "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum"}],
            "summary": {"block": sum(f["severity"] == "block" for f in findings),
                        "warn": sum(f["severity"] == "warn" for f in findings)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="final-pixel ad text/OCR/contrast/safe-zone QC")
    ap.add_argument("project_root")
    ap.add_argument("--init-plan", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve(); plan_path = root / "合规" / "rendered_text_plan.json"
    if ns.init_plan and not plan_path.exists():
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(template(root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok] {plan_path}")
    payload = build(root)
    out = root / "合成" / "rendered_text_qc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# rendered text QC block={payload['summary']['block']} warn={payload['summary']['warn']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
