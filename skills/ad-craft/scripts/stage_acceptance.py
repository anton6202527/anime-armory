#!/usr/bin/env python3
"""Single machine-readable acceptance contract for every ad production stage."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import contract
import dependency_graph
import compliance_manifest
# gate 与本文件同属 ad-craft：母本↔快照对账与「花钱 gate 关键输入表」直接复用 gate 的实现，
# 避免同口径检查抄两份后各自漂移。
import gate as spend_gate


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def finding(severity, code, msg, path="", criterion=""):
    return {"severity": severity, "code": code, "msg": msg,
            "path": str(path) if path else "", "criterion": criterion or code}


def counts(report):
    summary = report.get("summary") if isinstance(report, dict) else None
    if not isinstance(summary, dict):
        return None, None
    try:
        return int(summary.get("block") or 0), int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        return None, None


def newest(paths):
    value = 0.0
    for path in paths:
        path = Path(path)
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    value = max(value, child.stat().st_mtime)
        elif path.is_file():
            value = max(value, path.stat().st_mtime)
    return value


def stale(report, sources):
    return report.is_file() and newest(sources) > report.stat().st_mtime + 1e-6


def sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require_file(out, root, rel, code, criterion, nonempty=True):
    path = root / rel
    if not path.is_file() or (nonempty and path.stat().st_size <= 0):
        out.append(finding("block", code, f"缺失或为空：{rel}", rel, criterion))
        return None
    return path


def report_clean(out, root, rel, criterion, *, precision=False):
    path = require_file(out, root, rel, f"{criterion}_missing", criterion)
    if not path:
        return None
    payload = load(path)
    block, warn = counts(payload)
    if block is None:
        out.append(finding("block", f"{criterion}_malformed", f"{rel} 缺 summary.block/warn", rel, criterion))
    elif block:
        out.append(finding("block", f"{criterion}_block", f"{rel} block={block}", rel, criterion))
    if warn:
        out.append(finding("warn", f"{criterion}_warn", f"{rel} warn={warn}，需处理或签收", rel, criterion))
    if precision:
        level = str(((payload or {}).get("qc_environment") or {}).get("precision_level") or "")
        if level != "full":
            out.append(finding("block", f"{criterion}_precision", f"{rel} precision={level or 'unknown'}", rel, criterion))
    return payload


def accept_brief(root, out, mode):
    path = require_file(out, root, "需求/brief.json", "brief_missing", "brief_required")
    if not path:
        return
    brief = load(path, {}) or {}
    check = contract.brief_check(brief)
    if check["missing_required"]:
        out.append(finding("block", "brief_required", "缺必填：" + "、".join(check["missing_required"]), path, "brief_required"))
    if check["missing_deferred"]:
        # 与花钱 gate 的口径差是 by design：验收宽松（允许先做创意/脚本）、花钱前从严。
        out.append(finding("warn", "brief_production_pending",
                           "花钱前待闭合：" + "、".join(check["missing_deferred"])
                           + "（此处仅 warn；进入出图/出视频/合成时，花钱 gate 将按 block 处理）",
                           path, "measurement_design"))


def accept_concept(root, out, mode):
    concept = require_file(out, root, "创意/concept.md", "concept_missing", "strategy_sections")
    treatment = root / "创意" / "创意脚本.md"
    if not treatment.is_file():
        treatment = root / "创意脚本.md"
    if not treatment.is_file() or treatment.stat().st_size <= 0:
        out.append(finding("block", "creative_treatment_missing", "缺 创意/创意脚本.md", treatment, "strategy_sections"))
    raw = ((concept.read_text(encoding="utf-8") if concept else "") + "\n" +
           (treatment.read_text(encoding="utf-8") if treatment.is_file() else "")).lower()
    groups = {
        "big_idea": ("big idea", "大创意"), "key_message": ("一句话主张", "key message"),
        "objective": ("广告目标", "campaign objective", "objective"),
        "hypothesis": ("创意假设", "hypothesis", "为什么"),
        "mandatories": ("强制项", "mandatories", "logo", "法律声明"),
    }
    for key, aliases in groups.items():
        if not any(alias in raw for alias in aliases):
            out.append(finding("block", f"concept_{key}_missing", f"创意包缺 {key}", concept or treatment, "strategy_sections"))
    for path in (concept, treatment if treatment.is_file() else None):
        if path and stale(path, [root / "需求" / "brief.json"]):
            out.append(finding("block", "concept_stale", f"{path.name} 早于 brief，需重审", path, "strategy_sections"))


def _timeline_findings(out, path, data):
    """时间轴.json 结构校验：段落字段齐全、start<end、按序不重叠、累计与总时长一致。

    schema 以 golden 项目为准：list[{"start","end",...}]，或 dict 里挂
    segments/sections/timeline/items 列表（dict 顶层可带 master_seconds/total_seconds 总时长）。
    自相矛盾的时间轴会顺着 VO/分镜一路错到成片，必须在 script 验收就拦下。
    """
    total = None
    if isinstance(data, dict):
        segments = next((data.get(key) for key in ("segments", "sections", "timeline", "items")
                         if isinstance(data.get(key), list)), None)
        if segments is None:
            out.append(finding("block", "timeline_segments_missing",
                               "时间轴 JSON 找不到段落列表（segments/sections/timeline/items）", path, "script_package"))
            return
        total = next((data.get(key) for key in ("master_seconds", "total_seconds", "总时长")
                      if data.get(key) is not None), None)
    else:
        segments = data
    prev_end = None
    last_end = 0.0
    for pos, row in enumerate(segments, 1):
        if not isinstance(row, dict):
            out.append(finding("block", "timeline_segment_malformed",
                               f"时间轴第 {pos} 段不是对象", path, "script_package"))
            return
        try:
            start, end = float(row["start"]), float(row["end"])
        except (KeyError, TypeError, ValueError):
            out.append(finding("block", "timeline_segment_fields_missing",
                               f"时间轴第 {pos} 段缺数值 start/end 字段", path, "script_package"))
            return
        if start >= end:
            out.append(finding("block", "timeline_segment_invalid",
                               f"时间轴第 {pos} 段 start={start} >= end={end}", path, "script_package"))
        if prev_end is not None and start + 1e-6 < prev_end:
            out.append(finding("block", "timeline_overlap",
                               f"时间轴第 {pos} 段 start={start} 早于上一段 end={prev_end}（乱序/重叠）",
                               path, "script_package"))
        prev_end = end
        last_end = max(last_end, end)
    if total is not None:
        try:
            total = float(total)
        except (TypeError, ValueError):
            out.append(finding("block", "timeline_total_malformed",
                               "时间轴总时长字段不是数值", path, "script_package"))
            return
        if abs(last_end - total) > 0.5:
            out.append(finding("block", "timeline_total_mismatch",
                               f"时间轴累计 {last_end}s 与声明总时长 {total}s 不一致", path, "script_package"))


def accept_script(root, out, mode):
    script = require_file(out, root, "脚本/广告脚本.md", "script_missing", "script_package")
    vo = require_file(out, root, "脚本/voiceover.txt", "voiceover_missing", "script_package")
    timeline = require_file(out, root, "脚本/时间轴.json", "timeline_missing", "script_package")
    if timeline:
        data = load(timeline)
        if not isinstance(data, (list, dict)) or not data:
            out.append(finding("block", "timeline_empty", "时间轴 JSON 无有效段落", timeline, "script_package"))
        else:
            _timeline_findings(out, timeline, data)
    law = report_clean(out, root, "脚本/广告法机检报告.json", "ad_law")
    if isinstance(law, dict) and law.get("disabled"):
        out.append(finding("warn", "ad_law_disabled", "广告法机检关闭，须确认非大陆发行", "脚本/广告法机检报告.json", "ad_law"))
    if script and stale(script, [root / "创意" / "concept.md", root / "创意" / "创意脚本.md"]):
        out.append(finding("block", "script_stale", "广告脚本早于创意包", script, "script_package"))
    if vo and vo.read_text(encoding="utf-8").strip() == "":
        out.append(finding("block", "voiceover_empty", "voiceover.txt 为空", vo, "script_package"))
    law_path = root / "脚本" / "广告法机检报告.json"
    if law and stale(law_path, [path for path in (script, vo, timeline, root / "脚本" / "storyboard.json") if path]):
        out.append(finding("block", "ad_law_stale", "广告法报告早于当前脚本/VO/时间轴/分镜", law_path, "ad_law"))


def accept_voice(root, out, mode):
    path = require_file(out, root, "配音/时长清单.json", "voice_manifest_missing", "voice_manifest")
    manifest = load(path, {}) if path else {}
    lines = (manifest or {}).get("lines") or []
    if not lines:
        out.append(finding("block", "voice_lines_missing", "时长清单无 lines[]", path or "配音/时长清单.json", "voice_manifest"))
    for pos, row in enumerate(lines, 1):
        if float(row.get("seconds") or 0) <= 0 or not row.get("voice_key") or not row.get("line_wav"):
            out.append(finding("block", "voice_line_contract", f"第 {pos} 句缺 seconds/voice_key/line_wav", path, "voice_manifest"))
    if (manifest or {}).get("has_placeholder"):
        sev = "warn" if mode == "rough" else "block"
        out.append(finding(sev, "voice_placeholder", "占位 VO 不能作为正式阶段完成", path, "voice_manifest"))
    if path and stale(path, [root / "脚本" / "voiceover.txt"]):
        out.append(finding("block", "voice_manifest_stale", "时长清单早于 voiceover.txt", path, "voice_manifest"))
    # voice_key 由 render_voice 读 设定库/voicemap.json 计算：音色绑定改了而清单没重算，
    # 下游会拿旧音色继续排产。voicemap 缺失不新增要求（占位/内置归类项目本就没有它）。
    voicemap = root / "设定库" / "voicemap.json"
    if path and voicemap.is_file() and stale(path, [voicemap]):
        out.append(finding("block", "voice_manifest_voicemap_stale",
                           "时长清单早于 设定库/voicemap.json：音色绑定已变，须重跑 ad-voice 重算清单",
                           path, "voice_manifest"))
    qc = report_clean(out, root, "配音/voice_qc.json", "voice_technical_qc", precision=True)
    sources = [p for p in (root / "配音").glob("line_*.wav")]
    sources.extend([p for p in (path, root / "配音" / "vo.wav") if p])
    if qc and stale(root / "配音" / "voice_qc.json", sources):
        out.append(finding("block", "voice_qc_stale", "voice_qc 早于逐句音频/整轨/manifest", "配音/voice_qc.json", "voice_technical_qc"))


def shots(root):
    data = load(root / "脚本" / "storyboard.json", {}) or {}
    return data.get("shots") or data.get("clips") or []


def accept_storyboard(root, out, mode):
    path = require_file(out, root, "脚本/storyboard.json", "storyboard_missing", "timing_lock")
    rows = shots(root) if path else []
    if not rows:
        out.append(finding("block", "storyboard_empty", "storyboard 无镜头", path or "脚本/storyboard.json", "timing_lock"))
    ids = []
    for pos, row in enumerate(rows, 1):
        sid = str(row.get("shot_id") or row.get("clip_id") or row.get("id") or "")
        ids.append(sid)
        if not sid or float(row.get("duration") or row.get("duration_sec") or 0) <= 0:
            out.append(finding("block", "shot_contract", f"第 {pos} 镜缺唯一 ID 或正时长", path, "timing_lock"))
    if len(ids) != len(set(ids)):
        out.append(finding("block", "shot_id_duplicate", "storyboard 镜头 ID 重复", path, "timing_lock"))
    final = require_file(out, root, "脚本/镜头时长.json", "timing_report_missing", "timing_lock")
    if final:
        data = load(final, {}) or {}
        bad = [f for f in data.get("findings") or [] if f.get("severity") in {"block", "error"}]
        if bad:
            out.append(finding("block", "timing_report_block", f"镜头时长报告仍有 block={len(bad)}", final, "timing_lock"))
        if stale(final, [path, root / "配音" / "时长清单.json"]):
            out.append(finding("block", "timing_report_stale", "镜头时长报告早于分镜/配音", final, "timing_lock"))
        brief = load(root / "需求" / "brief.json", {}) or {}
        raw_claims = brief.get("claims") or []
        if isinstance(raw_claims, dict):
            raw_claims = [raw_claims]
        claim_ids = [str(row.get("id") or f"claim_{pos:02d}") for pos, row in enumerate(raw_claims, 1)
                     if isinstance(row, dict)]
        if claim_ids:
            if int(data.get("schema_version") or 0) < 2 or not (data.get("standards") or {}).get("cited_content"):
                out.append(finding("block", "claim_presentation_report_legacy",
                                   "当前 claim 项目必须用新版 finalize_storyboard 重跑引证呈现合同",
                                   final, "disclosure_presentation"))
            bound = set()
            disclosed = set()
            for row in rows:
                raw = row.get("claim_ids") or []
                if isinstance(raw, str):
                    raw = [raw]
                bound.update(str(v) for v in raw if v)
                disclosures = row.get("disclosures") or []
                if isinstance(disclosures, dict):
                    disclosures = [disclosures]
                disclosed.update(str(v.get("claim_id")) for v in disclosures if isinstance(v, dict) and v.get("claim_id"))
            missing = sorted(set(claim_ids) - (bound & disclosed))
            if missing:
                out.append(finding("block", "claim_presentation_binding_missing",
                                   "claim 未同时绑定宣称镜与披露：" + "、".join(missing),
                                   path, "disclosure_presentation"))


def _jobs_accept(root, out, rel, criterion, output_keys):
    path = require_file(out, root, rel, f"{criterion}_manifest_missing", criterion)
    data = load(path, {}) if path else {}
    jobs = (data or {}).get("jobs") or []
    if not jobs:
        out.append(finding("block", f"{criterion}_jobs_empty", f"{rel} 无 jobs[]", path or rel, criterion))
    for job in jobs:
        jid = str(job.get("job_id") or job.get("clip") or "?")
        if job.get("status") == "cancelled":
            continue
        if job.get("status") != "done":
            out.append(finding("block", f"{criterion}_job_incomplete", f"job {jid} status={job.get('status')}", path, criterion))
        if criterion == "image_provenance" and job.get("status") == "done":
            if not job.get("model") or not (job.get("channel") or job.get("access_path")):
                out.append(finding("block", "image_route_provenance_missing",
                                   f"job {jid} 缺具体 model/channel；旧 backend 字段不能替代模型指代", path, criterion))
        relout = next((job.get(k) for k in output_keys if job.get(k)), None)
        if not relout or not (root / str(relout)).is_file():
            out.append(finding("block", f"{criterion}_output_missing", f"job {jid} 缺真实输出 {relout}", path, criterion))
        if job.get("requires_image_input") and not job.get("actual_reference_inputs"):
            out.append(finding("block", "image_reference_not_used", f"产品 job {jid} 未记录实际参考图输入", path, criterion))
    return data


def gate_advisory(out, root, stage):
    """gate↔验收互链（advisory，不 block）：验收管完成、gate 管花钱，两链独立但要互相可见。

    无对应 gate 落档，或落档早于 gate 自己的关键输入（清单复用 gate.GATE_INPUT_RELS，
    避免两份漂移）→ warn「花钱 gate 未跑/已过期」。阶段 ✅ 不蕴含 gate 通过，但至少要说出来。
    """
    rel = f"生产数据/gate_reports/{stage}.json"
    path = root / rel
    if not path.is_file():
        out.append(finding("warn", "gate_report_missing",
                           f"花钱 gate 未跑：缺 {rel}；阶段验收不代表 gate 通过，"
                           f"正式花钱前先跑 ad-craft/scripts/gate.py --stage {stage}",
                           rel, "gate_crosslink"))
        return
    sources = [root / src for src in spend_gate.GATE_INPUT_RELS.get(stage, [])]
    if stale(path, sources):
        out.append(finding("warn", "gate_report_stale",
                           f"花钱 gate 落档早于关键输入，结论已过期；重跑 gate.py --stage {stage} 刷新落档",
                           rel, "gate_crosslink"))


def accept_image(root, out, mode):
    _jobs_accept(root, out, "出图/分镜/image_jobs_manifest.json", "image_provenance", ("output", "expected_output"))
    qc = report_clean(out, root, "出图/分镜/product_qc.json", "product_qc", precision=True)
    if qc and stale(root / "出图" / "分镜" / "product_qc.json", [root / "出图" / "分镜" / "图片", root / "出图" / "分镜" / "prompt"]):
        out.append(finding("block", "product_qc_stale", "product_qc 早于图片/prompt", "出图/分镜/product_qc.json", "product_qc"))
    # 定妆母本↔出图快照对账与 gate 同口径（直接复用 gate 的实现）：母本晚于快照 = 图照过期
    # registry 出的，验收侧同样 block，不再只靠花钱 gate 单边兜底。
    for item in spend_gate.registry_snapshot_findings(str(root)):
        out.append(finding(item["severity"], item["code"], item["msg"],
                           item.get("path", ""), "image_provenance"))
    gate_advisory(out, root, "image")


def accept_video(root, out, mode):
    _jobs_accept(root, out, "出视频/分镜/video_jobs_manifest.json", "video_provenance", ("output", "expected_output"))
    report_clean(out, root, "出视频/分镜/contract_inheritance.json", "video_provenance")
    qc = report_clean(out, root, "出视频/分镜/video_qc.json", "video_qc", precision=True)
    if qc and stale(root / "出视频" / "分镜" / "video_qc.json", [root / "出视频" / "分镜" / "视频", root / "出视频" / "分镜" / "prompt"]):
        out.append(finding("block", "video_qc_stale", "video_qc 早于 clips/prompt", "出视频/分镜/video_qc.json", "video_qc"))
    gate_advisory(out, root, "video")


def accept_compose(root, out, mode):
    plan_path = require_file(out, root, "合成/delivery_plan.json", "delivery_plan_missing", "delivery_matrix")
    qc = report_clean(out, root, "合成/delivery_qc.json", "delivery_matrix")
    plan = load(plan_path, {}) if plan_path else {}
    passed = {item.get("deliverable_id") for item in (qc or {}).get("items") or [] if item.get("passed")}
    for item in (plan or {}).get("deliverables") or []:
        if item.get("status") == "cancelled":
            continue
        did = item.get("deliverable_id")
        # 不信任 delivery_plan 里写的 exists 布尔（可能是陈旧/手改的自报）：逐件按
        # expected_path 复查磁盘真身，文件不在就是不在。
        expected = str(item.get("expected_path") or "")
        on_disk = bool(expected) and os.path.isfile(root / expected)
        if not on_disk or did not in passed:
            out.append(finding("block", "deliverable_not_accepted",
                               f"交付件 {did} 磁盘缺失或未通过 delivery_qc（exists 自报不作数，已按 expected_path 复查）",
                               plan_path, "delivery_matrix"))
    if qc and stale(root / "合成" / "delivery_qc.json", [root / "合成" / "成片_主片.mp4", root / "合成" / "cutdown", root / "合成" / "多比例"]):
        out.append(finding("block", "delivery_qc_stale", "delivery_qc 早于交付媒体", "合成/delivery_qc.json", "delivery_matrix"))
    color = report_clean(out, root, "合成/color_preflight.json", "color_delivery")
    if color and stale(root / "合成" / "color_preflight.json", [root / "出视频" / "分镜" / "视频"]):
        out.append(finding("block", "color_preflight_stale", "色彩预检早于当前 clip", "合成/color_preflight.json", "color_delivery"))
    access = report_clean(out, root, "合成/accessibility_qc.json", "accessibility_delivery")
    if access and stale(root / "合成" / "accessibility_qc.json", [
        root / "脚本" / "字幕_zh.srt", root / "脚本" / "字幕_en.srt",
        root / "合成" / "成片_主片.mp4", root / "合成" / "cutdown", root / "合成" / "多比例",
    ]):
        out.append(finding("block", "accessibility_qc_stale", "无障碍 QC 早于当前字幕/交付媒体",
                           "合成/accessibility_qc.json", "accessibility_delivery"))
    rendered = report_clean(out, root, "合成/rendered_text_qc.json", "rendered_text_delivery")
    if rendered and stale(root / "合成" / "rendered_text_qc.json", [
        root / "合规" / "rendered_text_plan.json", root / "合成" / "成片_主片.mp4",
        root / "合成" / "cutdown", root / "合成" / "多比例",
    ]):
        out.append(finding("block", "rendered_text_qc_stale", "最终文字 QC 早于当前计划/交付媒体",
                           "合成/rendered_text_qc.json", "rendered_text_delivery"))
    asr = report_clean(out, root, "合成/asr_consistency.json", "asr_delivery")
    if asr and stale(root / "合成" / "asr_consistency.json", [
        root / "脚本" / "voiceover.txt", root / "配音" / "vo.wav", root / "合成" / "成片_主片.mp4",
        root / "脚本" / "字幕_zh.srt", root / "脚本" / "字幕_en.srt",
        root / "配音" / "asr" / "vo.txt", root / "合成" / "asr" / "master.txt",
        root / "合成" / "asr_receipts.json",
    ]):
        out.append(finding("block", "asr_consistency_stale", "ASR 对账早于当前 VO/字幕/母版",
                           "合成/asr_consistency.json", "asr_delivery"))
    gate_advisory(out, root, "compose")


def accept_handoff(root, out, mode):
    require_file(out, root, "合规/ai_usage.json", "ai_usage_missing", "release_compliance")
    locale = report_clean(out, root, "合规/locale_matrix_validation.json", "locale_release")
    provenance = report_clean(out, root, "合规/provenance_qc.json", "provenance_release")
    variants = report_clean(out, root, "合规/release_variant_manifest.json", "variant_release")
    cm = report_clean(out, root, "合规/compliance_manifest.json", "release_compliance")
    if isinstance(locale, dict) and locale.get("matrix_sha256") != sha(root / "合规" / "locale_matrix.json"):
        out.append(finding("block", "locale_validation_stale", "locale validation 未绑定当前 locale_matrix",
                           "合规/locale_matrix_validation.json", "locale_release"))
    fresh_locale = compliance_manifest.locale_matrix.validate(root)
    if (isinstance(locale, dict) and
            (locale.get("locales") != fresh_locale.get("locales") or
             locale.get("deliverable_locales") != fresh_locale.get("deliverable_locales"))):
        out.append(finding("block", "locale_validation_evidence_stale",
                           "locale validation 的语言/排版证据哈希已变化",
                           "合规/locale_matrix_validation.json", "locale_release"))
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    current = {str(row.get("deliverable_id")): sha(root / str(row.get("expected_path") or ""))
               for row in plan.get("deliverables") or []
               if row.get("status") != "cancelled" and row.get("deliverable_id")}
    variant_rows = {str(row.get("deliverable_id")): row for row in (variants or {}).get("variants") or []
                    if isinstance(row, dict) and row.get("deliverable_id")}
    if (not current or set(variant_rows) != set(current) or
            any((variant_rows.get(did) or {}).get("sha256") != digest for did, digest in current.items()) or
            (variants or {}).get("delivery_plan_sha256") != sha(root / "合成" / "delivery_plan.json") or
            (variants or {}).get("locale_matrix_sha256") != sha(root / "合规" / "locale_matrix.json")):
        out.append(finding("block", "release_variant_manifest_stale",
                           "release variant manifest 未逐件绑定当前媒体/delivery plan/locale SHA",
                           "合规/release_variant_manifest.json", "variant_release"))
    fresh_variants = compliance_manifest.release_variant_manifest.build(root)
    if isinstance(variants, dict) and variants.get("variants") != fresh_variants.get("variants"):
        out.append(finding("block", "release_variant_evidence_stale",
                           "release variant 的 claim/rights/legal/AI label 证据或哈希已变化",
                           "合规/release_variant_manifest.json", "variant_release"))
    provenance_rows = {str(row.get("deliverable_id")): row for row in (provenance or {}).get("items") or []
                       if isinstance(row, dict) and row.get("deliverable_id")}
    if (set(provenance_rows) != set(current) or
            any((provenance_rows.get(did) or {}).get("sha256") != digest for did, digest in current.items())):
        out.append(finding("block", "provenance_qc_stale", "provenance QC 未逐件绑定当前媒体 SHA",
                           "合规/provenance_qc.json", "provenance_release"))
    for did, row in provenance_rows.items():
        receipt = row.get("external_receipt") if isinstance(row.get("external_receipt"), dict) else None
        if not receipt:
            continue
        ref = str(receipt.get("evidence_file") or "")
        bound = receipt.get("evidence_sha256_actual")
        if ref.startswith(("https://", "http://", "record:")):
            current_evidence = bound if isinstance(bound, str) and len(bound) == 64 else None
        else:
            path = Path(ref)
            if ref and not path.is_absolute():
                path = root / path
            current_evidence = sha(path) if ref else None
        if current_evidence != bound:
            out.append(finding("block", "provenance_receipt_evidence_stale",
                               f"{did} provenance 外部探测证据已变化/缺失",
                               "合规/provenance_qc.json", "provenance_release"))
    if isinstance(cm, dict) and cm.get("release_content_sha256") != compliance_manifest.release_content_sha256(root):
        out.append(finding("block", "compliance_manifest_stale", "compliance manifest 未绑定当前 release content",
                           "合规/compliance_manifest.json", "release_compliance"))
    if isinstance(cm, dict) and not bool((cm.get("summary") or {}).get("release_ready")):
        out.append(finding("block", "release_not_ready", "compliance_manifest release_ready=false", "合规/compliance_manifest.json", "release_compliance"))


def accept_review(root, out, mode):
    machine = report_clean(out, root, "合规/ad_review_m0.json", "machine_review")
    machine_path = root / "合规" / "ad_review_m0.json"
    if machine and stale(machine_path, [root / "合成" / "成片_主片.mp4", root / "合成" / "delivery_qc.json",
                                        root / "生产数据" / "consistency_findings.json",
                                        root / "生产数据" / "final_media_consistency.json",
                                        root / "合规" / "compliance_manifest.json",
                                        root / "合规" / "release_variant_manifest.json",
                                        root / "合规" / "provenance_qc.json"]):
        out.append(finding("block", "machine_review_stale", "M0 机器报告早于当前交付/一致性/合规证据",
                           "合规/ad_review_m0.json", "machine_review"))
    sign_path = require_file(out, root, "合规/human_signoff.json", "human_signoff_missing", "human_signoff")
    sign = load(sign_path, {}) if sign_path else {}
    if sign and not bool((sign.get("summary") or {}).get("approved")):
        out.append(finding("block", "human_signoff_incomplete", "human_signoff 未全部批准", sign_path, "human_signoff"))
    expected = {
        "master": root / "合成" / "成片_主片.mp4", "delivery_plan": root / "合成" / "delivery_plan.json",
        "delivery_qc": root / "合成" / "delivery_qc.json",
        "accessibility_qc": root / "合成" / "accessibility_qc.json",
        "color_preflight": root / "合成" / "color_preflight.json",
        "rendered_text_qc": root / "合成" / "rendered_text_qc.json",
        "asr_consistency": root / "合成" / "asr_consistency.json",
        "provenance_qc": root / "合规" / "provenance_qc.json",
        "release_variants": root / "合规" / "release_variant_manifest.json",
        "locale_validation": root / "合规" / "locale_matrix_validation.json",
        "final_media_consistency": root / "生产数据" / "final_media_consistency.json",
        "consistency": root / "生产数据" / "consistency_findings.json", "machine_review": root / "合规" / "ad_review_m0.json",
    }
    signed = (sign or {}).get("source_sha256") or {}
    for key, path in expected.items():
        if signed.get(key) != sha(path):
            out.append(finding("block", "human_signoff_stale", f"签收未绑定当前 {key}", sign_path or "合规/human_signoff.json", "human_signoff"))
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    current_deliverables = {}
    for item in plan.get("deliverables") or []:
        if item.get("status") == "cancelled":
            continue
        if item.get("deliverable_id") and item.get("expected_path"):
            current_deliverables[str(item["deliverable_id"])] = sha(root / str(item["expected_path"]))
    if signed.get("deliverables") != current_deliverables or not current_deliverables:
        out.append(finding("block", "human_signoff_delivery_stale", "签收未绑定当前全部未取消交付媒体",
                           sign_path or "合规/human_signoff.json", "human_signoff"))
    final_media = load(root / "生产数据" / "final_media_consistency.json", {}) or {}
    current_sheets = {}
    for asset_id, row in (final_media.get("assets") or {}).items():
        sheet = (row or {}).get("contact_sheet") if isinstance(row, dict) else None
        rel = (sheet or {}).get("path") if isinstance(sheet, dict) else ""
        if rel:
            current_sheets[str(asset_id)] = sha(root / rel)
    if signed.get("final_contact_sheets") != current_sheets or not current_sheets:
        out.append(finding("block", "human_signoff_contact_sheet_stale",
                           "签收未绑定当前逐资产最终 contact sheet",
                           sign_path or "合规/human_signoff.json", "human_signoff"))
    for key, row in ((sign or {}).get("checks") or {}).items():
        ref = str((row or {}).get("evidence") or "") if isinstance(row, dict) else ""
        signed_digest = ((sign or {}).get("evidence_sha256") or {}).get(key)
        if not ref or ref.startswith(("https://", "http://", "record:")):
            continue
        evidence_path = Path(ref)
        if not evidence_path.is_absolute():
            evidence_path = root / evidence_path
        if signed_digest != sha(evidence_path):
            out.append(finding("block", "human_evidence_stale", f"{key} 人工证据已变化/缺失",
                               ref, "human_signoff"))


def accept_feedback(root, out, mode):
    canonical_path = require_file(out, root, "投放反馈/experiment_plan.json", "experiment_plan_missing", "experiment_design")
    plan = report_clean(out, root, "投放反馈/experiment_plan_validation.json", "experiment_design")
    if isinstance(plan, dict) and not bool((plan.get("summary") or {}).get("approved")):
        out.append(finding("block", "experiment_not_approved", "实验预注册未通过", "投放反馈/experiment_plan_validation.json", "experiment_design"))
    if canonical_path and isinstance(plan, dict):
        canonical = load(canonical_path, {}) or {}
        if plan.get("plan_sha256") != json_sha(canonical):
            out.append(finding("block", "experiment_validation_stale", "实验计划已变化，预注册验证失效",
                               "投放反馈/experiment_plan_validation.json", "experiment_design"))
    report = report_clean(out, root, "投放反馈/feedback_report.json", "statistical_read")
    if isinstance(report, dict):
        if report.get("experiment_plan_approved") is not True:
            out.append(finding("block", "feedback_without_approved_plan", "反馈报告未消费已批准实验计划",
                               "投放反馈/feedback_report.json", "statistical_read"))
        source = report.get("source_data") if isinstance(report.get("source_data"), dict) else {}
        source_path = root / str(source.get("path") or "")
        if not source_path.is_file() or source.get("sha256") != sha(source_path):
            out.append(finding("block", "feedback_source_stale", "反馈报告未绑定当前原始投放数据",
                               "投放反馈/feedback_report.json", "statistical_read"))


ACCEPTORS = {
    "brief": accept_brief, "concept": accept_concept, "script": accept_script, "voice": accept_voice,
    "storyboard": accept_storyboard, "image": accept_image, "video": accept_video, "compose": accept_compose,
    "handoff": accept_handoff, "review": accept_review, "feedback": accept_feedback,
}


def evaluate(root: Path, stage: str, mode="formal"):
    root = root.resolve()
    findings = []
    for item in dependency_graph.upstream_findings(root, stage):
        findings.append(finding(item["severity"], item["code"], item["msg"],
                                "生产数据/dependency_receipts.json", "dependency_lineage"))
    ACCEPTORS[stage](root, findings, mode)
    result = {
        "schema_version": 1, "kind": "ad_stage_acceptance", "contract_version": contract.CONTRACT_VERSION,
        "acceptance_version": contract.STAGE_ACCEPTANCE_VERSION, "stage": stage, "mode": mode,
        "project_root": str(root), "criteria": contract.stage_criteria(stage), "findings": findings,
        "summary": {"block": sum(f["severity"] == "block" for f in findings),
                    "warn": sum(f["severity"] == "warn" for f in findings)},
    }
    result["summary"]["accepted"] = result["summary"]["block"] == 0
    return result


def write_report(root: Path, payload):
    out = root / "生产数据" / "stage_acceptance" / f"{payload['stage']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="ad per-stage acceptance contract")
    ap.add_argument("project_root")
    ap.add_argument("--stage", required=True, choices=tuple(ACCEPTORS))
    ap.add_argument("--mode", default="formal", choices=("formal", "rough"))
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    payload = evaluate(root, ns.stage, ns.mode)
    if not payload["summary"]["block"]:
        try:
            dependency_graph.accept_stage(root, ns.stage)
        except ValueError as exc:
            payload["findings"].append(finding("block", "dependency_accept_failed", str(exc),
                                               "生产数据/dependency_receipts.json", "dependency_lineage"))
            payload["summary"]["block"] += 1
            payload["summary"]["accepted"] = False
    out = write_report(root, payload)
    print(f"# stage acceptance {ns.stage} accepted={payload['summary']['accepted']} block={payload['summary']['block']} warn={payload['summary']['warn']}")
    for item in payload["findings"]:
        print(("🔴" if item["severity"] == "block" else "🟡") + f" [{item['code']}] {item['msg']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
