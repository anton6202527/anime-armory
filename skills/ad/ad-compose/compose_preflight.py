#!/usr/bin/env python3
"""Small deterministic compose decisions shared by compose.sh and tests."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


ENDCARD_TOKENS = ("end card", "endcard", "片尾", "品牌包装", "cta")


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def storyboard_has_endcard(root: Path) -> bool:
    sb = load(root / "脚本" / "storyboard.json", {}) or {}
    for shot in sb.get("shots") or sb.get("clips") or []:
        if not isinstance(shot, dict):
            continue
        text = " ".join(str(shot.get(k) or "") for k in ("section", "scene", "shot", "frame", "description")).lower()
        if any(token in text for token in ENDCARD_TOKENS):
            return True
    return False


def probe_color(path: Path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
        return None
    proc = subprocess.run([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=color_primaries,color_transfer,color_space,color_range,field_order,pix_fmt",
        "-of", "json", str(path),
    ], capture_output=True, text=True)
    if proc.returncode:
        return None
    try:
        streams = json.loads(proc.stdout).get("streams") or []
        return streams[0] if streams else None
    except (json.JSONDecodeError, AttributeError):
        return None


def _evidence_exists(root: Path, value) -> bool:
    ref = str(value or "").strip()
    if not ref:
        return False
    if ref.startswith(("https://", "http://", "record:")):
        return True
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path.is_file()


def color_preflight(root: Path):
    """Detect HDR/non-BT.709/mixed clip sources before an SDR master encode.

    We never silently retag HDR as BT.709.  An explicit conversion plan can
    authorize heterogeneous sources; final delivery_qc still verifies output
    tags. Missing source metadata is a WARN because it is not proof of HDR.
    """
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    policy = brief.get("color_management") if isinstance(brief.get("color_management"), dict) else {}
    mode = str(policy.get("mode") or "sdr_bt709").strip()
    evidence = policy.get("conversion_evidence")
    explicit = mode == "explicit_conversion" and _evidence_exists(root, evidence)
    clips = sorted((root / "出视频" / "分镜" / "视频").glob("*.mp4"))
    findings = []
    rows = []
    signatures = set()
    if not clips:
        findings.append({"severity": "block", "code": "color_source_missing", "msg": "缺待合成 clip，无法做色彩预检"})
    for path in clips:
        data = probe_color(path)
        if data is None:
            findings.append({"severity": "block", "code": "color_probe_failed", "msg": f"ffprobe 无法读取色彩元数据：{path.name}"})
            rows.append({"path": str(path.relative_to(root)), "probe": None})
            continue
        signature = tuple(str(data.get(k) or "unspecified") for k in
                          ("color_primaries", "color_transfer", "color_space", "color_range"))
        signatures.add(signature)
        rows.append({"path": str(path.relative_to(root)), **data})
        hdr = (str(data.get("color_primaries") or "") == "bt2020" or
               str(data.get("color_transfer") or "") in {"smpte2084", "arib-std-b67"})
        known_non709 = any(str(data.get(k) or "") not in {"", "unknown", "unspecified", "bt709"}
                           for k in ("color_primaries", "color_transfer", "color_space"))
        unspecified = all(not data.get(k) or str(data.get(k)) in {"unknown", "unspecified"}
                          for k in ("color_primaries", "color_transfer", "color_space"))
        if (hdr or known_non709) and not explicit:
            findings.append({
                "severity": "block", "code": "color_conversion_plan_missing",
                "msg": f"{path.name} 为 HDR/非 BT.709 源；不得仅改标签。请在 brief.color_management 写 explicit_conversion + conversion_evidence。",
            })
        elif unspecified:
            findings.append({
                "severity": "warn", "code": "color_metadata_unspecified",
                "msg": f"{path.name} 未声明色彩元数据；按 SDR BT.709 处理前须人工确认来源。",
            })
        if "10" in str(data.get("pix_fmt") or "") and not hdr:
            findings.append({"severity": "warn", "code": "high_bit_depth_sdr_source",
                             "msg": f"{path.name} 是高位深 SDR 源；降到 yuv420p 8-bit 前复核渐变/抖动（不自动判 HDR）。"})
    if len(signatures) > 1 and not explicit:
        findings.append({"severity": "block", "code": "mixed_color_sources",
                         "msg": "clip 色彩签名不一致；需显式统一转换方案，不能在 concat 时静默混色。"})
    if mode == "explicit_conversion" and not explicit:
        findings.append({"severity": "block", "code": "color_conversion_evidence_missing",
                         "msg": "声明 explicit_conversion 但 conversion_evidence 不存在/不可查询。"})
    return {
        "schema_version": 1, "kind": "ad_color_preflight", "target": "SDR_BT709",
        "policy": {"mode": mode, "conversion_evidence": evidence or "", "evidence_valid": explicit},
        "sources": rows, "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--should-append-endcard", action="store_true")
    ap.add_argument("--color-report", default=None, help="运行色彩源预检并写 JSON；有 block 返回非零")
    ns = ap.parse_args(argv)
    if ns.color_report:
        payload = color_preflight(Path(ns.project_root))
        out = Path(ns.color_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"# color preflight block={payload['summary']['block']} warn={payload['summary']['warn']}")
        return 1 if payload["summary"]["block"] else 0
    if ns.should_append_endcard:
        return 1 if storyboard_has_endcard(Path(ns.project_root)) else 0
    print(json.dumps({"storyboard_has_endcard": storyboard_has_endcard(Path(ns.project_root))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
