#!/usr/bin/env python3
"""Create a named, media-bound human sign-off for claims machines cannot judge."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


_CRAFT = Path(__file__).resolve().parents[2] / "ad-craft" / "scripts"
if str(_CRAFT) not in sys.path:
    sys.path.insert(0, str(_CRAFT))
import dependency_graph  # noqa: E402


CHECKS = {
    "product_identity": "产品包装、Logo、品牌色和比例跨镜一致",
    "character_identity": "人物脸、发型、服装和年龄/体态一致",
    "scene_prop_identity": "场景空间关系、陈设和关键道具连续",
    "subtitle_legibility": "字幕、价格、CTA、法律声明准确清晰且停留足够",
    "claim_disclosure_presentation": "宣称与来源/条件/范围/有效期同屏或紧邻，未出现大字吸睛小字免责",
    "non_speech_captioning": "有意义的音乐、音效和说话人信息已在需要时进入字幕",
    "flash_safety": "按实际成片复核闪烁风险；机器低分辨率快筛只作提示",
    "color_review": "实际监看确认肤色、产品/品牌色、渐变与 HDR→SDR 转换无异常",
    "av_sync": "VO、口型/动作、音乐/SFX 与画面节奏同步",
    "safe_zone": "每个实际 placement 的核心信息未被 UI/裁切遮挡",
    "visual_claim_truth": "产品尺度、演示、前后对比和效果画面不构成误导",
    "hook_first3s": "前 3 秒钩子、产品/品牌与音频符合广告目标",
    "rights_and_disclosures": "授权、AI 标识/声明、免责声明与 claim 依据一致",
    "locale_copy": "逐语言的翻译、币种、单位、CTA、法律声明和文字布局一致",
    "ai_label_provenance": "逐交付件显式/隐式 AI 标识、C2PA/元数据与平台回执一致",
}
EVIDENCE_REQUIRED = set(CHECKS)
AUTOMATED_REVIEWER_RE = re.compile(
    r"(?:^|[^a-z0-9])(agent|ai|assistant|automation|bot|chatgpt|claude|codex|delegate|listener|"
    r"machine|model|producer|supervisor|system)(?:[^a-z0-9]|$)|"
    r"^(?:代理|制作代理|自动化|机器人|模型|系统|系统代理|执行器)(?:$|[:：/#@])", re.I
)


def is_human_reviewer(value) -> bool:
    name = str(value or "").strip()
    return bool(name) and not AUTOMATED_REVIEWER_RE.search(name)


def sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(root: Path, reviewer: str, approved, note="", evidence=None, evidence_digests=None):
    root = root.resolve()
    approved = set(approved)
    evidence = evidence if isinstance(evidence, dict) else {}
    evidence_digests = evidence_digests if isinstance(evidence_digests, dict) else {}
    missing = [key for key in CHECKS if key not in approved]
    report_path = root / "合规" / "ad_review_m0.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        report = {}
    machine_blocks = int(((report.get("summary") or {}).get("block")) or 0)
    findings = []
    if not reviewer.strip():
        findings.append({"severity": "block", "code": "reviewer_missing", "msg": "缺具名 reviewer"})
    elif not is_human_reviewer(reviewer):
        findings.append({
            "severity": "block",
            "code": "reviewer_automated",
            "msg": "最终签收 reviewer 必须是真实具名人，不能是 AI / agent / automation / system / delegate 身份",
        })
    if machine_blocks:
        findings.append({"severity": "block", "code": "machine_review_block",
                         "msg": f"M0 机器报告仍有 block={machine_blocks}，不能签收"})
    if missing:
        findings.append({"severity": "block", "code": "human_checks_incomplete",
                         "msg": "未逐项签收：" + "、".join(missing)})
    evidence_missing = sorted(key for key in EVIDENCE_REQUIRED if not str(evidence.get(key) or "").strip())
    if evidence_missing:
        findings.append({"severity": "block", "code": "human_evidence_missing",
                         "msg": "高风险人工项缺证据引用：" + "、".join(evidence_missing)})
    evidence_sha256 = {}
    for key, raw in evidence.items():
        ref = str(raw or "").strip()
        if not ref:
            evidence_sha256[key] = None
            continue
        if ref.startswith(("https://", "http://", "record:")):
            digest = str(evidence_digests.get(key) or "").strip().lower()
            evidence_sha256[key] = digest if re.fullmatch(r"[0-9a-f]{64}", digest) else None
            if key in EVIDENCE_REQUIRED and evidence_sha256[key] is None:
                findings.append({"severity": "block", "code": "human_remote_evidence_hash_missing",
                                 "msg": f"{key} 远程/记录证据须提供 64 位 SHA-256"})
            continue
        evidence_path = Path(ref)
        if not evidence_path.is_absolute():
            evidence_path = root / evidence_path
        evidence_sha256[key] = sha(evidence_path)
        if key in EVIDENCE_REQUIRED and evidence_sha256[key] is None:
            findings.append({"severity": "block", "code": "human_evidence_file_missing",
                             "msg": f"{key} 证据文件不存在：{ref}"})
    sources = {
        "master": root / "合成" / "成片_主片.mp4",
        "delivery_plan": root / "合成" / "delivery_plan.json",
        "delivery_qc": root / "合成" / "delivery_qc.json",
        "render_profile": root / "生产数据" / "render_profile.json",
        "placement_adaptation": root / "生产数据" / "placement_adaptation.json",
        "compose_acceptance": root / "生产数据" / "stage_acceptance" / "compose.json",
        "accessibility_qc": root / "合成" / "accessibility_qc.json",
        "color_preflight": root / "合成" / "color_preflight.json",
        "rendered_text_qc": root / "合成" / "rendered_text_qc.json",
        "asr_consistency": root / "合成" / "asr_consistency.json",
        "provenance_qc": root / "合规" / "provenance_qc.json",
        "campaign_readiness": root / "生产数据" / "campaign_readiness.json",
        "compliance_manifest": root / "合规" / "compliance_manifest.json",
        "release_variants": root / "合规" / "release_variant_manifest.json",
        "locale_validation": root / "合规" / "locale_matrix_validation.json",
        "final_media_consistency": root / "生产数据" / "final_media_consistency.json",
        "consistency": root / "生产数据" / "consistency_findings.json",
        "machine_review": report_path,
    }
    hashes = {key: sha(path) for key, path in sources.items()}
    compose_status = dependency_graph.compose_acceptance_status(root)
    hashes["compose_receipts"] = compose_status["receipt_sha256"]
    if not compose_status["accepted"]:
        findings.append({"severity": "block", "code": "compose_acceptance_not_current",
                         "msg": "人工签收要求当前 formal compose acceptance 与 dependency receipts"})
    try:
        plan = json.loads(sources["delivery_plan"].read_text(encoding="utf-8"))
    except Exception:
        plan = {}
    deliverables = {}
    for item in plan.get("deliverables") or []:
        if item.get("status") == "cancelled":
            continue
        did = str(item.get("deliverable_id") or "")
        rel = str(item.get("expected_path") or "")
        if did and rel:
            deliverables[did] = sha(root / rel)
    hashes["deliverables"] = deliverables
    try:
        final_media = json.loads(sources["final_media_consistency"].read_text(encoding="utf-8"))
    except Exception:
        final_media = {}
    contact_sheets = {}
    for aid, row in (final_media.get("assets") or {}).items():
        sheet = (row or {}).get("contact_sheet") if isinstance(row, dict) else None
        rel = (sheet or {}).get("path") if isinstance(sheet, dict) else ""
        if rel:
            contact_sheets[str(aid)] = sha(root / rel)
    hashes["final_contact_sheets"] = contact_sheets
    if any(value is None for value in hashes.values()):
        findings.append({"severity": "block", "code": "signoff_source_missing",
                         "msg": "签收所绑定的主片/QC/一致性/M0 报告不完整"})
    if not deliverables or any(value is None for value in deliverables.values()):
        findings.append({"severity": "block", "code": "signoff_delivery_missing",
                         "msg": "签收未绑定 delivery_plan 中每个未取消交付件"})
    if not contact_sheets or any(value is None for value in contact_sheets.values()):
        findings.append({"severity": "block", "code": "signoff_contact_sheet_missing",
                         "msg": "签收未绑定逐产品/人物/场景/道具最终媒体 contact sheet"})
    return {
        "schema_version": 1, "kind": "ad_human_signoff",
        "reviewer": reviewer.strip(), "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "checks": {key: {"approved": key in approved, "standard": label,
                           "evidence": str(evidence.get(key) or "")} for key, label in CHECKS.items()},
        "evidence_sha256": evidence_sha256,
        "source_sha256": hashes, "note": note,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "approved": not any(f["severity"] == "block" for f in findings)},
        "findings": findings,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="具名签收广告机器不可判的视觉/听觉/真实性项目")
    ap.add_argument("project_root")
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--approve", action="append", default=[], choices=sorted(CHECKS),
                    help="逐项重复传入；不提供 --approve-all，避免误触全签")
    ap.add_argument("--evidence", action="append", default=[], metavar="CHECK=REF",
                    help="逐项证据/审片记录引用；所有人工项必填")
    ap.add_argument("--evidence-sha", action="append", default=[], metavar="CHECK=SHA256",
                    help="URL/record 证据必须提供；本地文件自动计算")
    ap.add_argument("--note", default="")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    evidence = {}
    for raw in ns.evidence:
        key, sep, value = raw.partition("=")
        if not sep or key not in CHECKS or not value.strip():
            ap.error(f"--evidence 格式须为 CHECK=REF，未知/空值：{raw}")
        evidence[key] = value.strip()
    evidence_digests = {}
    for raw in ns.evidence_sha:
        key, sep, value = raw.partition("=")
        if not sep or key not in CHECKS or not re.fullmatch(r"[0-9a-fA-F]{64}", value.strip()):
            ap.error(f"--evidence-sha 格式须为 CHECK=64HEX：{raw}")
        evidence_digests[key] = value.strip().lower()
    payload = build(root, ns.reviewer, ns.approve, ns.note, evidence, evidence_digests)
    out = root / "合规" / "human_signoff.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# human signoff approved={payload['summary']['approved']} block={payload['summary']['block']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
