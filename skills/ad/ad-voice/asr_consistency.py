#!/usr/bin/env python3
"""Compare approved VO with actual VO, captions and final-master ASR text.

Heavy ASR is optional and adapter-driven.  Without a local whisper CLI the
script emits stable transcript jobs and blocks final review until operators
provide precomputed transcripts.  Deterministic exact-copy terms (numbers,
prices, CTA, spoken claims and legal lines) are hard checked; fuzzy transcript
similarity is advisory only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Mapping


KIND = "ad_asr_consistency"
SCHEMA_VERSION = 1
CRITICAL_TOKEN = re.compile(r"(?:[¥￥$€£]\s*\d[\d,.]*|\d+(?:[.,]\d+)?\s*(?:%|％|元|块|美元|秒|天|年|倍)?)")
TIMECODE = re.compile(r"^\s*\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->.*$")


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
    text = re.sub(r"^\s*[^\n：:]{1,12}[：:]\s*", "", text, flags=re.M)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff%]+", "", text)


def subtitle_text(raw: str):
    lines = []
    for line in raw.splitlines():
        if TIMECODE.match(line) or re.fullmatch(r"\s*\d+\s*", line):
            continue
        if line.strip():
            lines.append(re.sub(r"<[^>]+>", "", line.strip()))
    return "\n".join(lines)


def _copy_values(brief: Mapping[str, Any]):
    mand = brief.get("mandatories") if isinstance(brief.get("mandatories"), Mapping) else {}
    values = []
    cta = mand.get("endcard_cta") or mand.get("cta")
    if cta:
        values.append(("cta", str(cta)))
    legal = mand.get("legal_lines") or []
    if isinstance(legal, str):
        legal = [legal]
    values.extend(("legal", str(value)) for value in legal if str(value))
    claims = brief.get("claims") or []
    if isinstance(claims, Mapping):
        claims = [claims]
    values.extend(("claim", str(row.get("claim"))) for row in claims if isinstance(row, Mapping) and row.get("claim"))
    return values


def critical_terms(expected: str, brief: Mapping[str, Any]):
    normalized_expected = normalize(expected)
    rows = [{"kind": "number_or_price", "text": match.group(0)} for match in CRITICAL_TOKEN.finditer(expected)]
    for kind, text in _copy_values(brief):
        if normalize(text) and normalize(text) in normalized_expected:
            rows.append({"kind": kind, "text": text})
    unique = []
    positions = {}
    for row in rows:
        key = (row["kind"], normalize(row["text"]))
        if not key[1]:
            continue
        if key in positions:
            unique[positions[key]]["expected_count"] += 1
        else:
            positions[key] = len(unique)
            unique.append({**row, "expected_count": 1})
    return unique


def compare(expected: str, actual: str, terms):
    a, b = normalize(expected), normalize(actual)
    ratio = SequenceMatcher(None, a, b).ratio() if a and b else 0.0
    expected_numbers = Counter(normalize(match.group(0)) for match in CRITICAL_TOKEN.finditer(expected))
    actual_numbers = Counter(normalize(match.group(0)) for match in CRITICAL_TOKEN.finditer(actual))
    checks = []
    for term in terms:
        wanted = normalize(term["text"])
        count = int(term.get("expected_count") or 1)
        actual_count = actual_numbers.get(wanted, 0) if term["kind"] == "number_or_price" else b.count(wanted)
        checks.append({**term, "normalized": wanted, "actual_count": actual_count,
                       "present": bool(wanted and actual_count == count)})
    return {"similarity": round(ratio, 4), "expected_chars": len(a), "actual_chars": len(b),
            "critical_terms": checks, "numeric_tokens_expected": dict(expected_numbers),
            "numeric_tokens_actual": dict(actual_numbers), "numeric_tokens_exact": expected_numbers == actual_numbers}


def _run_whisper(media: Path, out_dir: Path, model=""):
    exe = shutil.which("whisper")
    if not exe or not media.is_file():
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [exe, str(media), "--output_dir", str(out_dir), "--output_format", "txt"]
    if model:
        command.extend(["--model", model])
    proc = subprocess.run(command,
                          capture_output=True, text=True)
    target = out_dir / f"{media.stem}.txt"
    return target if proc.returncode == 0 and target.is_file() else None


def _valid_receipt(receipts, name, media: Path, transcript: Path):
    row = receipts.get(name) if isinstance(receipts, Mapping) and isinstance(receipts.get(name), Mapping) else {}
    try:
        checked = datetime.fromisoformat(str(row.get("checked_at") or "").replace("Z", "+00:00"))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        checked_valid = checked <= datetime.now(timezone.utc)
    except ValueError:
        checked_valid = False
    valid = (row.get("media_sha256") == sha(media) and row.get("transcript_sha256") == sha(transcript) and
             bool(row.get("engine")) and checked_valid)
    return {**dict(row), "valid": valid}


def build(root: Path, *, run_asr=False, vo_transcript=None, master_transcript=None, asr_model=""):
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    voiceover_path = root / "脚本" / "voiceover.txt"
    subtitle_path = root / "脚本" / "字幕_zh.srt"
    if not subtitle_path.is_file() and (root / "脚本" / "字幕_en.srt").is_file():
        subtitle_path = root / "脚本" / "字幕_en.srt"
    vo_media = root / "配音" / "vo.wav"
    master_media = root / "合成" / "成片_主片.mp4"
    vo_path = Path(vo_transcript) if vo_transcript else root / "配音" / "asr" / "vo.txt"
    master_path = Path(master_transcript) if master_transcript else root / "合成" / "asr" / "master.txt"
    receipt_path = root / "合成" / "asr_receipts.json"
    receipt_doc = load(receipt_path, {}) or {"schema_version": 1, "kind": "ad_asr_receipts", "receipts": {}}
    receipt_rows = receipt_doc.get("receipts") if isinstance(receipt_doc.get("receipts"), Mapping) else {}
    if run_asr:
        generated_rows = {}
        for name, media, target in (("vo", vo_media, vo_path), ("master", master_media, master_path)):
            generated = _run_whisper(media, target.parent, asr_model)
            if generated and generated != target:
                generated.replace(target)
            if target.is_file() and generated:
                generated_rows[name] = {"media_path": str(media.relative_to(root)), "media_sha256": sha(media),
                                        "transcript_path": (str(target.relative_to(root))
                                                            if target.is_relative_to(root) else str(target)),
                                        "transcript_sha256": sha(target), "engine": "whisper_cli",
                                        "model": asr_model or "whisper_cli_default",
                                        "checked_at": datetime.now(timezone.utc).isoformat()}
        if generated_rows:
            receipt_rows = {**dict(receipt_rows), **generated_rows}
            receipt_doc["receipts"] = receipt_rows
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(json.dumps(receipt_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    expected = voiceover_path.read_text(encoding="utf-8") if voiceover_path.is_file() else ""
    subtitle = subtitle_text(subtitle_path.read_text(encoding="utf-8")) if subtitle_path.is_file() else ""
    vo_actual = vo_path.read_text(encoding="utf-8") if vo_path.is_file() else ""
    master_actual = master_path.read_text(encoding="utf-8") if master_path.is_file() else ""
    terms = critical_terms(expected, brief)
    findings = []
    if not expected.strip():
        findings.append({"severity": "block", "code": "approved_voiceover_missing", "msg": "缺已批准 voiceover.txt"})
    for name, path, actual in (("vo", vo_path, vo_actual), ("master", master_path, master_actual)):
        if not actual.strip():
            findings.append({"severity": "block", "code": "asr_transcript_missing",
                             "msg": f"缺 {name} 实际 ASR transcript：{path.relative_to(root) if path.is_relative_to(root) else path}"})
    receipt_results = {"vo": _valid_receipt(receipt_rows, "vo", vo_media, vo_path),
                       "master": _valid_receipt(receipt_rows, "master", master_media, master_path)}
    for name, row in receipt_results.items():
        if not row.get("valid"):
            findings.append({"severity": "block", "code": "asr_receipt_invalid",
                             "msg": f"{name} transcript 缺引擎/时间或未绑定当前媒体与 transcript SHA"})
    comparisons = {
        "vo": compare(expected, vo_actual, terms),
        "subtitle": compare(expected, subtitle, terms),
        "master": compare(expected, master_actual, terms),
    }
    for target, result in comparisons.items():
        if target != "subtitle" and result["similarity"] < 0.92:
            findings.append({"severity": "warn", "code": "transcript_similarity_house_warn",
                             "msg": f"{target} 与批准 VO 归一文本相似度 {result['similarity']:.3f}<0.92；属内部快筛，须人工听审"})
        for term in result["critical_terms"]:
            if not term["present"]:
                findings.append({"severity": "block", "code": "critical_copy_mismatch",
                                 "msg": f"{target} 缺精确 {term['kind']}：{term['text']}"})
        if not result["numeric_tokens_exact"]:
            findings.append({"severity": "block", "code": "critical_numeric_set_mismatch",
                             "msg": f"{target} 数字/价格 token 集不精确：expected={result['numeric_tokens_expected']} actual={result['numeric_tokens_actual']}"})
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND,
        "adapter": {"whisper_cli_available": bool(shutil.which("whisper")), "run_requested": run_asr,
                    "fallback": "提供预计算 transcript；建议在含 whisper 的本线适配环境运行"},
        "sources": {
            "voiceover": {"path": "脚本/voiceover.txt", "sha256": sha(voiceover_path)},
            "vo_media": {"path": "配音/vo.wav", "sha256": sha(vo_media)},
            "vo_transcript": {"path": str(vo_path.relative_to(root)) if vo_path.is_relative_to(root) else str(vo_path), "sha256": sha(vo_path)},
            "subtitle": {"path": str(subtitle_path.relative_to(root)), "sha256": sha(subtitle_path)},
            "master_media": {"path": "合成/成片_主片.mp4", "sha256": sha(master_media)},
            "master_transcript": {"path": str(master_path.relative_to(root)) if master_path.is_relative_to(root) else str(master_path), "sha256": sha(master_path)},
            "receipt": {"path": "合成/asr_receipts.json", "sha256": sha(receipt_path)},
        },
        "receipts": receipt_results, "critical_terms": terms, "comparisons": comparisons, "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="ASR consistency for approved VO, captions and final master")
    ap.add_argument("project_root")
    ap.add_argument("--run-asr", action="store_true")
    ap.add_argument("--vo-transcript")
    ap.add_argument("--master-transcript")
    ap.add_argument("--asr-model", default="")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    payload = build(root, run_asr=ns.run_asr, vo_transcript=ns.vo_transcript,
                    master_transcript=ns.master_transcript, asr_model=ns.asr_model)
    out = root / "合成" / "asr_consistency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# ASR consistency block={payload['summary']['block']} warn={payload['summary']['warn']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
