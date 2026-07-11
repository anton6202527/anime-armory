#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine gate for paid/high-risk ad stages: image, video, compose.

This is the deterministic counterpart to the SKILL.md reminders. It blocks
missing brief compliance, upstream blockers, and final-compose hazards before
money or irreversible production work starts.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import contract

# 读 _设置.md / 全局默认走本线 vendored 的 settings 助手（本线自包含）。
_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "ad", "_lib"))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
try:
    import settings as _settings  # noqa: E402
except Exception:  # pragma: no cover - settings helper optional
    _settings = None


# gate 入口阶段就是契约里登记的「花钱/不可逆」阶段，别在此另抄一份。
STAGES = contract.GATE_STAGES

_PENDING_TOKENS = {"", "未记录", "待补", "待填写", "tbd", "未填", "未定"}
PREFERRED_IMAGE_BACKENDS = {"codex", "openai"}
IMAGE_BACKEND_OVERRIDE_REL = os.path.join("合规", "image_backend_override.json")


def _load_sibling_module(name):
    path = os.path.join(_HERE, f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"_ad_craft_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def finding(severity, code, msg, path=None):
    out = {"severity": severity, "code": code, "msg": msg}
    if path:
        out["path"] = path
    return out


def has_files(folder, suffixes):
    if not os.path.isdir(folder):
        return False
    for name in os.listdir(folder):
        if name.lower().endswith(suffixes):
            return True
    return False


def _newest_mtime(paths):
    newest = 0.0
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    newest = max(newest, child.stat().st_mtime)
        elif path.is_file():
            newest = max(newest, path.stat().st_mtime)
    return newest


def report_freshness_findings(report_path, source_paths, code):
    """A clean but stale report is not evidence for newer inputs."""
    if not os.path.isfile(report_path):
        return []
    report_mtime = os.path.getmtime(report_path)
    newest = _newest_mtime(source_paths)
    if newest and report_mtime + 1e-6 < newest:
        return [finding("block", f"{code}_stale",
                        f"{os.path.basename(report_path)} 早于其输入产物，必须重跑；旧报告不能证明新产物通过",
                        report_path)]
    return []


def brief_findings(root):
    path = os.path.join(root, "需求", "brief.json")
    brief = load_json(path)
    if brief is None:
        return [finding("block", "brief_missing", "缺 需求/brief.json", path)]
    check = contract.brief_check(brief)
    out = []
    if check["missing_required"]:
        out.append(finding("block", "brief_required_missing",
                           "brief 必填最小集缺项：" + "、".join(check["missing_required"]), path))
    if check["missing_deferred"]:
        out.append(finding("block", "brief_deferred_missing",
                           "花钱 gate 前合规项缺项：" + "、".join(check["missing_deferred"]), path))
    return out


def _summary_counts(report):
    """从机检/契约报告读 (block, warn)，格式异常返回 (None, None)。"""
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return None, None
    b, w = summary.get("block"), summary.get("warn")
    try:
        return int(b or 0), int(w or 0)
    except (TypeError, ValueError):
        return None, None


def ad_law_findings(root):
    path = os.path.join(root, "脚本", "广告法机检报告.json")
    report = load_json(path)
    if report is None:
        return [finding("block", "ad_law_report_missing", "缺广告法机检报告，请先跑 ad-script/ad_law_check.py", path)]
    if report.get("disabled"):
        # 关闭模式：仅限非中国大陆投放且用户明确——保留留痕但需人工复核。
        return [finding("warn", "ad_law_disabled",
                        f"广告法机检已关闭（region={report.get('region', '?')}）；仅限非中国大陆投放，需人工确认", path)]
    blocks, warns = _summary_counts(report)
    if blocks is None:
        return [finding("block", "ad_law_report_malformed", "广告法机检报告缺 summary.block 整数字段（格式异常）", path)]
    out = []
    if blocks:
        out.append(finding("block", "ad_law_block", f"广告法机检仍有 block={blocks}", path))
    if warns:
        out.append(finding("warn", "ad_law_warn", f"广告法机检仍有 warn={warns}，需人工确认依据", path))
    return out


def _resolve_image_backend(root):
    """优先 _设置.md(生图AI) → 全局默认 → _meta.json(image_backend)。"""
    val = ""
    if _settings is not None:
        try:
            val = (_settings.get_setting(root, "生图AI", "") or "").strip()
        except Exception:
            val = ""
    if not val:
        meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
        val = (meta.get("image_backend") or "").strip()
    return val


def _image_backend_override_allows(root, canonical):
    """Return (ok, path) for a signed non-Codex image backend exception."""
    path = os.path.join(root, IMAGE_BACKEND_OVERRIDE_REL)
    payload = load_json(path)
    if not isinstance(payload, dict):
        return False, path
    if payload.get("approved") is not True:
        return False, path
    scope = str(payload.get("scope") or payload.get("stage") or "image").lower()
    if "image" not in scope and "生图" not in scope:
        return False, path
    raw_backend = str(
        payload.get("backend")
        or payload.get("canonical")
        or payload.get("image_backend")
        or ""
    ).strip()
    if raw_backend == canonical:
        return True, path
    signed_canon, signed_kind = contract.classify_image_backend(raw_backend)
    if signed_kind == "approved" and signed_canon == canonical:
        return True, path
    return False, path


def image_backend_findings(root):
    """生图后端治理：Codex image2 优先；非 Codex/OpenAI 需签核；项目内不混用。"""
    out = []
    setting_val = _resolve_image_backend(root)
    if not setting_val:
        out.append(finding("warn", "image_backend_unset", "未解析到 生图AI 设置，无法核验后端治理", root))
        return out
    canon, kind = contract.classify_image_backend(setting_val)
    if kind == "forbidden":
        out.append(finding("block", "image_backend_forbidden",
                            f"生图AI『{setting_val}』属禁用/逆向出图路径（ad 投放合规口径），不得用于广告出图"))
    elif kind == "unknown":
        out.append(finding("block", "image_backend_unknown",
                            f"生图AI『{setting_val}』不在 ad 放行白名单内；请改用官方后端或先登记核验"))
    elif canon and canon not in PREFERRED_IMAGE_BACKENDS:
        allowed, signoff_path = _image_backend_override_allows(root, canon)
        if not allowed:
            out.append(finding(
                "block",
                "image_backend_non_codex_requires_signoff",
                "全项目生图优先 Codex image2；非 Codex/OpenAI 生图后端必须先由用户明确签核，"
                f"再写 {IMAGE_BACKEND_OVERRIDE_REL} 后才能进入付费出图。当前：{setting_val}",
                signoff_path,
            ))
    # 后端混用：_设置.md 与 _meta.json 指向不同 canonical 后端 = block。
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    meta_val = (meta.get("image_backend") or "").strip()
    if meta_val:
        meta_canon, meta_kind = contract.classify_image_backend(meta_val)
        if canon and meta_canon and meta_canon != canon:
            out.append(finding("block", "image_backend_mixed",
                                f"项目内后端混用：_设置.md『{setting_val}』≠ _meta.json『{meta_val}』，一个项目只允许一个生图后端"))
    return out


def image_output_backend_findings(root):
    """已落图 provenance 对账：不能用 Dreamina 图片伪装成 Codex 项目继续出视频。"""
    manifest_path = os.path.join(root, "出图", "分镜", "image_jobs_manifest.json")
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        return []
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        return []
    setting_val = _resolve_image_backend(root)
    setting_canon, setting_kind = contract.classify_image_backend(setting_val)
    out = []
    seen = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        status = str(job.get("status") or "").strip().lower()
        if status not in {"done", "pass", "accepted", "ok"}:
            continue
        backend = str(job.get("backend") or "").strip()
        if not backend:
            out.append(finding("block", "image_output_backend_missing",
                               f"已落图 job {job.get('job_id') or job.get('shot') or '?'} 缺 backend provenance",
                               manifest_path))
            continue
        if job.get("requires_image_input") and not job.get("actual_reference_inputs"):
            out.append(finding("block", "image_output_reference_inputs_missing",
                               f"产品镜 job {job.get('job_id') or '?'} 已完成但 actual_reference_inputs=0；"
                               "prompt 声称引用不等于真实图片输入", manifest_path))
        canon, kind = contract.classify_image_backend(backend)
        seen.add(canon or backend)
        if kind == "forbidden":
            out.append(finding("block", "image_output_backend_forbidden",
                               f"已落图 job {job.get('job_id') or '?'} 使用禁用/逆向后端：{backend}",
                               manifest_path))
        elif kind == "unknown":
            out.append(finding("block", "image_output_backend_unknown",
                               f"已落图 job {job.get('job_id') or '?'} 的后端无法核验：{backend}",
                               manifest_path))
        elif canon and canon not in PREFERRED_IMAGE_BACKENDS:
            allowed, signoff_path = _image_backend_override_allows(root, canon)
            if not allowed:
                out.append(finding(
                    "block",
                    "image_output_non_codex_requires_redraw",
                    "已落图来自非 Codex/OpenAI 后端，且无用户签核例外；正式出视频前必须用 Codex image2 重出。"
                    f"当前 job {job.get('job_id') or '?'} backend={backend}",
                    signoff_path,
                ))
        if setting_kind == "approved" and canon and setting_canon and canon != setting_canon:
            out.append(finding("block", "image_output_backend_mismatch",
                               f"已落图后端 {backend} 与当前 生图AI『{setting_val}』不一致；必须重出受影响图",
                               manifest_path))
    if len({x for x in seen if x}) >= 2:
        out.append(finding("block", "image_output_backend_mixed",
                           "已落图 manifest 内混用多个生图后端：" + "、".join(sorted(str(x) for x in seen if x)),
                           manifest_path))
    return out


def product_qc_findings(root):
    """读 ad-image product_qc.py 的机检报告（产品/logo/品牌色漂移 = ad 线的脸漂）。"""
    path = os.path.join(root, "出图", "分镜", "product_qc.json")
    report = load_json(path)
    if report is None:
        return [finding("block", "product_qc_missing",
                        "缺产品一致性机检报告，请先跑 ad-image/scripts/product_qc.py", path)]
    blocks, warns = _summary_counts(report)
    if blocks is None:
        return [finding("block", "product_qc_malformed", "产品一致性报告缺 summary.block（格式异常）", path)]
    out = []
    if blocks:
        out.append(finding("block", "product_qc_block",
                            f"产品/logo/品牌色一致性仍有 block={blocks}（含文生图产品/品牌色漂移）", path))
    env = report.get("qc_environment") or {}
    precision = str(env.get("precision_level") or "").strip()
    manual_ok = bool(report.get("manual_review_accepted") or env.get("manual_review_accepted"))
    if precision and precision != "full" and not manual_ok:
        out.append(finding("block", "product_qc_precision_not_full",
                           f"产品一致性机检精度为 {precision}，品牌色/dHash/logo 像素检未完整执行；"
                           "正式出视频前需补依赖重跑，或在报告中人工留痕 manual_review_accepted=true", path))
    elif precision and precision != "full" and manual_ok:
        out.append(finding("warn", "product_qc_precision_manual_override",
                           f"产品一致性机检精度为 {precision}，但已有人工复核放行留痕", path))
    try:
        pending = int((env.get("pending_product_images") or 0) if isinstance(env, dict) else 0)
    except (TypeError, ValueError):
        pending = 0
    if pending:
        out.append(finding("block", "product_qc_pending_images",
                           f"产品一致性机检有 {pending} 个产品镜图未落档/未读到，不能进出视频", path))
    if any((f.get("detail") or {}).get("degraded") == "no_image" for f in report.get("findings") or []):
        out.append(finding("block", "product_qc_pending_images",
                           "产品一致性报告仍含 no_image pending 项，需先补产品镜图并重跑 product_qc", path))
    if warns:
        out.append(finding("warn", "product_qc_warn", f"产品一致性 warn={warns}，需人工确认", path))
    out.extend(report_freshness_findings(path, [
        os.path.join(root, "脚本", "storyboard.json"),
        os.path.join(root, "出图", "分镜", "prompt"),
        os.path.join(root, "出图", "分镜", "图片"),
        os.path.join(root, "出图", "共享", "asset_registry.json"),
    ], "product_qc"))
    return out


def storyboard_findings(root):
    out = []
    for rel in ("脚本/storyboard.json", "脚本/镜头时长.json"):
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            out.append(finding("block", "storyboard_missing", f"缺 {rel}", path))
    timing = load_json(os.path.join(root, "脚本", "镜头时长.json"), {}) or {}
    for item in timing.get("findings", []):
        if item.get("severity") == "block":
            out.append(finding("block", "storyboard_finalize_block", item.get("msg", "分镜定稿存在 block"),
                               os.path.join(root, "脚本", "镜头时长.json")))
    return out


def voice_findings(root, stage, allow_placeholder=False):
    path = os.path.join(root, "配音", "时长清单.json")
    manifest = load_json(path)
    if manifest is None:
        return [finding("block", "voice_manifest_missing", "缺 配音/时长清单.json", path)]
    if manifest.get("has_placeholder"):
        # image 阶段可先出定妆/首帧（不依赖精确时长）→ warn；
        # video/compose 把占位时长焊进帧/成片 → block（除非 --allow-placeholder 显式放行 demo）。
        sev = "warn" if (allow_placeholder or stage == "image") else "block"
        return [finding(sev, "voice_placeholder", "VO 仍是占位；占位时长会被焊进出视频/成片，正式成片前必须真 VO 复跑", path)]
    return []


def image_findings(root):
    folder = os.path.join(root, "出图", "分镜")
    image_folder = os.path.join(folder, "图片")
    if has_files(image_folder, (".png", ".jpg", ".jpeg", ".webp")):
        return []
    if has_files(folder, (".png", ".jpg", ".jpeg", ".webp")):
        return []
    return [finding("block", "image_frames_missing", "缺逐镜首帧/尾帧图片", image_folder)]


def video_contract_findings(root):
    path = os.path.join(root, "出视频", "分镜", "contract_inheritance.json")
    report = load_json(path)
    if report is None:
        return [finding("block", "video_contract_missing", "缺契约继承机检报告，请先跑 inherit_contract.py", path)]
    blocks = int(((report.get("summary") or {}).get("block")) or 0)
    warns = int(((report.get("summary") or {}).get("warn")) or 0)
    out = []
    if blocks:
        out.append(finding("block", "video_contract_block", f"视频契约继承仍有 block={blocks}", path))
    if warns:
        out.append(finding("warn", "video_contract_warn", f"视频契约继承 warn={warns}，需人工确认", path))
    out.extend(report_freshness_findings(path, [
        os.path.join(root, "脚本", "storyboard.json"),
        os.path.join(root, "出图", "分镜", "prompt", "00_总览.md"),
        os.path.join(root, "出视频", "分镜", "prompt"),
    ], "video_contract"))
    return out


def video_clip_findings(root):
    folder = os.path.join(root, "出视频", "分镜", "视频")
    if has_files(folder, (".mp4", ".mov", ".m4v")):
        return []
    manifest = load_json(os.path.join(root, "出视频", "分镜", "video_jobs_manifest.json"), {}) or {}
    jobs = manifest.get("jobs") if isinstance(manifest, dict) else []
    if isinstance(jobs, list):
        submitted = [
            str(j.get("clip") or j.get("job_id") or "")
            for j in jobs
            if isinstance(j, dict) and j.get("submit_id") and not j.get("output")
        ]
        if submitted:
            return [finding("block", "video_clips_pending",
                            "出视频 Clip 已提交远端但尚未回收下载：" + "、".join(x for x in submitted if x), folder)]
    return [finding("block", "video_clips_missing", "缺出视频 Clip 文件", folder)]


def video_qc_findings(root):
    path = os.path.join(root, "出视频", "分镜", "video_qc.json")
    report = load_json(path)
    if report is None:
        return [finding("block", "video_qc_missing",
                        "缺出视频落档 QC 报告，请先跑 ad-video/scripts/video_qc.py", path)]
    blocks, warns = _summary_counts(report)
    if blocks is None:
        return [finding("block", "video_qc_malformed", "出视频 QC 报告缺 summary.block（格式异常）", path)]
    out = []
    if blocks:
        out.append(finding("block", "video_qc_block",
                           f"出视频落档 QC 仍有 block={blocks}（产品/品牌/接缝/clip 文件需修）", path))
    env = report.get("qc_environment") if isinstance(report.get("qc_environment"), dict) else {}
    precision = str(env.get("precision_level") or "")
    manual_ok = bool(env.get("manual_review_accepted") or report.get("manual_review_accepted"))
    if precision != "full" and not manual_ok:
        out.append(finding("block", "video_qc_precision_not_full",
                           f"视频 QC precision={precision or 'unknown'}；正式合成前需 ffmpeg/ffprobe/Pillow 完整抽帧，或留痕人工放行",
                           path))
    if warns:
        out.append(finding("warn", "video_qc_warn", f"出视频落档 QC warn={warns}，需人工确认", path))
    out.extend(report_freshness_findings(path, [
        os.path.join(root, "出视频", "分镜", "视频"),
        os.path.join(root, "出视频", "分镜", "prompt"),
        os.path.join(root, "出视频", "分镜", "contract_inheritance.json"),
    ], "video_qc"))
    return out


def producer_pack_findings(root):
    module = _load_sibling_module("producer_pack")
    pack = module.build_pack(Path(root))
    blocks = int(((pack.get("summary") or {}).get("approval_blocks")) or 0)
    out = []
    if blocks:
        out.append(finding("block", "producer_pack_block",
                           f"制片前控包仍有 approval_blocks={blocks}；claim 依据/授权/法律声明/资产绑定未闭合",
                           os.path.join(root, "生产数据", "producer_pack.json")))
    return out


def platform_pack_findings(root):
    module = _load_sibling_module("platform_pack")
    pack = module.build_pack(Path(root))
    out = []
    for item in pack.get("findings") or []:
        sev = item.get("severity") if item.get("severity") in {"block", "warn"} else "warn"
        out.append(finding(sev, str(item.get("code") or "platform_pack"),
                           str(item.get("msg") or "平台规格需复核"),
                           os.path.join(root, "生产数据", "platform_pack.json")))
    return out


def score_findings(root):
    """Creative heuristics stay advisory; only the separate ad-law gate can BLOCK."""
    path = os.path.join(root, "评分", "ad_score.json")
    report = load_json(path)
    if not isinstance(report, dict):
        return [finding("warn", "ad_score_missing", "未生成目标化 pre-spend 创意评分；建议先跑 ad-score", path)]
    tier = str(report.get("tier") or "")
    if tier in {"revise", "reject"}:
        return [finding("warn", "ad_score_advisory", f"创意评分为 {tier}；启发式只提示复核，不作为付费硬阻断", path)]
    return []


def compose_output_findings(root):
    path = os.path.join(root, "合成", "成片_主片.mp4")
    if os.path.isfile(path):
        return []
    return [finding("warn", "master_missing_before_compose", "尚未生成主片；compose gate 通过后执行合成", path)]


def run_gate(root, stage, allow_placeholder=False):
    root = os.path.abspath(root)
    if stage not in STAGES:
        raise ValueError(f"unknown gate stage: {stage}")
    findings = []
    findings.extend(brief_findings(root))
    findings.extend(ad_law_findings(root))
    findings.extend(storyboard_findings(root))
    findings.extend(voice_findings(root, stage, allow_placeholder))
    findings.extend(producer_pack_findings(root))
    findings.extend(score_findings(root))
    if stage == "image":
        # 出图前：核验生图后端治理（白名单/不混用），此时图还没生成，不查 product_qc。
        findings.extend(image_backend_findings(root))
    if stage in ("video", "compose"):
        findings.extend(platform_pack_findings(root))
        # 图已生成：查存在性 + 产品/品牌色一致性机检（最便宜的拦截点）+ 契约继承。
        findings.extend(image_backend_findings(root))
        findings.extend(image_output_backend_findings(root))
        findings.extend(image_findings(root))
        findings.extend(product_qc_findings(root))
        findings.extend(video_contract_findings(root))
    if stage == "compose":
        findings.extend(video_clip_findings(root))
        findings.extend(video_qc_findings(root))
        findings.extend(compose_output_findings(root))
    summary = {
        "block": sum(1 for f in findings if f["severity"] == "block"),
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }
    return {"schema_version": 1, "kind": "ad_gate", "stage": stage, "project_root": root,
            "summary": summary, "findings": findings}


def _write_progress_state(root, stage, payload):
    """gate→_进度.md 反馈：阻塞落 🔴block（带首条原因），通过则清除残留 🔴block。

    只动该阶段行，不触碰已 ✅/⬜ 的正常状态（避免覆盖阶段 skill 写的真实进度）。
    """
    try:
        progress_set = _load_sibling_module("progress_set")
        path, text = progress_set.read_progress(root)
    except (ImportError, FileNotFoundError):
        return
    blocked = payload["summary"]["block"] > 0
    cur = progress_set.get_stage_status(text, stage)
    try:
        if blocked:
            top = next((f for f in payload["findings"] if f["severity"] == "block"), None)
            remark = f"gate: {top['code']}" if top else "gate blocked"
            out = progress_set.set_stage_text(text, stage, "🔴block", remark=remark,
                                              note=f"{stage} gate 阻塞：{remark}")
            progress_set.write_progress(path, out)
        elif cur == "🔴block":  # 之前被挡、现已通过 → 清回待做，不动 ✅
            out = progress_set.set_stage_text(text, stage, "⬜", note=f"{stage} gate 通过，清除 🔴block")
            progress_set.write_progress(path, out)
    except (KeyError, ValueError):
        pass


def main():
    ap = argparse.ArgumentParser(description="拍广告花钱/不可逆阶段 gate")
    ap.add_argument("project_root")
    ap.add_argument("--stage", required=True, choices=STAGES)
    ap.add_argument("--json", default=None)
    ap.add_argument("--allow-placeholder", action="store_true",
                    help="允许占位 VO 继续 demo；compose 默认不建议使用")
    ap.add_argument("--write-progress", action="store_true",
                    help="把 gate 结果回写 _进度.md：block 时该阶段置 🔴block 并记首条原因；通过则清除残留 🔴block")
    args = ap.parse_args()
    payload = run_gate(args.project_root, args.stage, args.allow_placeholder)
    if args.write_progress:
        _write_progress_state(args.project_root, args.stage, payload)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    b, w = payload["summary"]["block"], payload["summary"]["warn"]
    print(f"# ad gate stage={args.stage}  block={b}  warn={w}")
    for item in payload["findings"]:
        icon = "🔴" if item["severity"] == "block" else ("🟡" if item["severity"] == "warn" else "ℹ️")
        print(f"{icon} [{item['code']}] {item['msg']}")
    if b == 0:
        print("✅ gate 通过")
    sys.exit(1 if b else 0)


if __name__ == "__main__":
    main()
