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
from datetime import datetime, timezone
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


def _resolve_image_route(root):
    """Resolve concrete model + access channel; old `生图AI` is migration-only."""
    model = channel = legacy = ""
    if _settings is not None:
        try:
            model = (_settings.get_setting(root, "生图模型", "GPT Image 2") or "").strip()
            channel = (_settings.get_setting(root, "生图渠道", "Codex CLI") or "").strip()
            try:
                raw_settings = Path(root, "_设置.md").read_text(encoding="utf-8")
            except OSError:
                raw_settings = ""
            import re
            match = re.search(r"^\s*[-*]?\s*生图AI\s*[:：]\s*([^#\n]+)", raw_settings, re.M)
            legacy = match.group(1).strip() if match else ""
        except Exception:
            model = channel = legacy = ""
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    model = model or str(meta.get("image_model") or "").strip()
    channel = channel or str(meta.get("image_channel") or "").strip()
    legacy = legacy or str(meta.get("image_backend") or "").strip()
    return {"model": model, "channel": channel, "legacy": legacy}


def _route_family(canonical):
    return "openai" if canonical in {"codex", "openai"} else canonical


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
        payload.get("model")
        or payload.get("backend")
        or payload.get("canonical")
        or payload.get("image_backend")
        or ""
    ).strip()
    if raw_backend == canonical:
        return True, path
    signed_model, signed_model_kind = contract.classify_image_model(raw_backend)
    if signed_model_kind in {"approved", "manual"} and signed_model == canonical:
        return True, path
    signed_canon, signed_kind = contract.classify_image_backend(raw_backend)
    if signed_kind == "approved" and signed_canon == canonical:
        return True, path
    return False, path


def image_backend_findings(root):
    """生图路由治理：具体模型/渠道分列；非默认路线需签核；项目内不混用。"""
    out = []
    route = _resolve_image_route(root)
    model, channel, legacy = route["model"], route["channel"], route["legacy"]
    if not model or not channel:
        out.append(finding("block", "image_route_incomplete",
                           "生图必须分列具体 生图模型 + 生图渠道；旧 生图AI/厂商壳不能作为生成者", root))
        if legacy:
            out.append(finding("block", "image_route_legacy",
                               f"检测到旧 生图AI/image_backend={legacy}；迁移为具体模型与访问渠道后再花钱", root))
        return out
    if legacy:
        _, legacy_kind = contract.classify_image_backend(legacy)
        out.append(finding("block", "image_backend_forbidden" if legacy_kind == "forbidden" else "image_route_legacy",
                           f"_设置.md/旧默认仍使用 生图AI={legacy}；请删除旧键并保留具体模型+渠道"))
    model_canon, model_kind = contract.classify_image_model(model)
    channel_canon, channel_kind = contract.classify_image_channel(channel)
    if channel_kind == "forbidden":
        out.append(finding("block", "image_backend_forbidden",
                           f"生图渠道『{channel}』属逆向/未授权路径，不得用于广告出图"))
    if model_kind in {"unknown", "legacy"}:
        out.append(finding("block", "image_model_unknown",
                           f"生图模型『{model}』不是已核验的具体模型名；不得用 agent/渠道/厂商壳代替"))
    if channel_kind == "unknown":
        out.append(finding("block", "image_channel_unknown",
                           f"生图渠道『{channel}』未登记；请录入官方访问路径或 manual 签核"))
    if (model_kind == "manual" or channel_kind == "manual"):
        allowed, signoff_path = _image_backend_override_allows(root, model_canon or channel_canon or "manual")
        if not allowed:
            out.append(finding("block", "image_backend_non_codex_requires_signoff",
                               f"manual 生图模型/渠道需项目签核：{model} via {channel}", signoff_path))
    elif model_canon and channel_canon and _route_family(model_canon) != _route_family(channel_canon):
        out.append(finding("block", "image_model_channel_mismatch",
                           f"生图模型 {model} 与渠道 {channel} 不属于同一路线；适配层不得偷偷换模型"))
    elif model_canon and model_canon not in PREFERRED_IMAGE_BACKENDS:
        allowed, signoff_path = _image_backend_override_allows(root, model_canon)
        if not allowed:
            out.append(finding("block", "image_backend_non_codex_requires_signoff",
                               "默认 GPT Image 2；其它具体模型必须由用户明确签核后才能进入付费出图。"
                               f"当前：{model} via {channel}", signoff_path))
    # _设置.md 与 _meta.json 路由不同 = block。
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    meta_model = str(meta.get("image_model") or "").strip()
    meta_channel = str(meta.get("image_channel") or "").strip()
    meta_legacy = str(meta.get("image_backend") or "").strip()
    if meta_legacy:
        _, legacy_kind = contract.classify_image_backend(meta_legacy)
        out.append(finding("block", "image_backend_forbidden" if legacy_kind == "forbidden" else "image_route_legacy",
                           f"_meta.json 仍使用旧 image_backend={meta_legacy}；请迁移为 image_model + image_channel"))
    if meta_model and meta_model != model or meta_channel and meta_channel != channel:
        out.append(finding("block", "image_backend_mixed",
                           f"项目内生图路由混用：设置={model} via {channel}，meta={meta_model} via {meta_channel}"))
    return out


def registry_snapshot_findings(root):
    """定妆库母本↔快照对账：照过期 registry 出图，本身就是漂移源。

    `设定库/asset_registry.json` 是人写的**母本**；`出图/共享/asset_registry.json` 是
    `plan_prompts.build_shared_registry` 生成的**快照**（图实际是照它出的，故 product_qc /
    asset_consistency 读快照才是对的）。两份的主从关系此前没有文档、也没有机检：母本改了而
    快照没刷新时，prompt 与 QC 会照旧快照跑，而这套系统本身就是用来防漂移的。
    与 report_freshness_findings 同一条哲学：干净但过期的证据不是证据。
    """
    master = os.path.join(root, "设定库", "asset_registry.json")
    snapshot = os.path.join(root, "出图", "共享", "asset_registry.json")
    if not os.path.isfile(master) or not os.path.isfile(snapshot):
        return []
    if os.path.getmtime(snapshot) + 1e-6 < os.path.getmtime(master):
        return [finding("block", "asset_registry_snapshot_stale",
                        "出图/共享/asset_registry.json 早于 设定库/asset_registry.json："
                        "定妆母本已改而出图快照未刷新，prompt/QC 会照过期 registry 跑；"
                        "重跑 ad-image plan_prompts.py 刷新快照后再出图", snapshot)]
    return []


def image_output_backend_findings(root):
    """已落图 provenance 对账：不能用 Dreamina 图片伪装成 Codex 项目继续出视频。"""
    manifest_path = os.path.join(root, "出图", "分镜", "image_jobs_manifest.json")
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        return []
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        return []
    route = _resolve_image_route(root)
    setting_model_canon, setting_model_kind = contract.classify_image_model(route["model"])
    setting_channel_canon, _ = contract.classify_image_channel(route["channel"])
    out = []
    seen = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        status = str(job.get("status") or "").strip().lower()
        if status not in {"done", "pass", "accepted", "ok"}:
            continue
        model = str(job.get("model") or "").strip()
        channel = str(job.get("channel") or job.get("access_path") or "").strip()
        backend = str(job.get("backend") or "").strip()
        if not model or not channel:
            out.append(finding("block", "image_output_route_missing",
                               f"已落图 job {job.get('job_id') or job.get('shot') or '?'} 缺具体 model/channel provenance"
                               + (f"（旧 backend={backend} 不能替代）" if backend else ""),
                               manifest_path))
            continue
        if job.get("requires_image_input") and not job.get("actual_reference_inputs"):
            out.append(finding("block", "image_output_reference_inputs_missing",
                               f"产品镜 job {job.get('job_id') or '?'} 已完成但 actual_reference_inputs=0；"
                               "prompt 声称引用不等于真实图片输入", manifest_path))
        canon, kind = contract.classify_image_model(model)
        channel_canon, channel_kind = contract.classify_image_channel(channel)
        seen.add(f"{canon or model}@{channel_canon or channel}")
        if channel_kind == "forbidden":
            out.append(finding("block", "image_output_backend_forbidden",
                               f"已落图 job {job.get('job_id') or '?'} 使用禁用/逆向渠道：{channel}",
                               manifest_path))
        elif kind in {"unknown", "legacy"} or channel_kind == "unknown":
            out.append(finding("block", "image_output_backend_unknown",
                               f"已落图 job {job.get('job_id') or '?'} 的模型/渠道无法核验：{model} via {channel}",
                               manifest_path))
        elif canon and canon not in PREFERRED_IMAGE_BACKENDS:
            allowed, signoff_path = _image_backend_override_allows(root, canon)
            if not allowed:
                out.append(finding(
                    "block",
                    "image_output_non_codex_requires_redraw",
                    "已落图来自非 Codex/OpenAI 后端，且无用户签核例外；正式出视频前必须用 Codex image2 重出。"
                    f"当前 job {job.get('job_id') or '?'} model={model} channel={channel}",
                    signoff_path,
                ))
        if (setting_model_kind == "approved" and canon and setting_model_canon and
                _route_family(canon) != _route_family(setting_model_canon)):
            out.append(finding("block", "image_output_backend_mismatch",
                               f"已落图模型 {model} 与当前 生图模型『{route['model']}』不一致；必须重出受影响图",
                               manifest_path))
        if channel_canon and setting_channel_canon and _route_family(channel_canon) != _route_family(setting_channel_canon):
            out.append(finding("block", "image_output_channel_mismatch",
                               f"已落图渠道 {channel} 与当前 生图渠道『{route['channel']}』不一致", manifest_path))
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


def _advisory_report_findings(root, relpath, code, hint, sources=()):
    """读一份 advisory 侧车报告并降档并入 gate。

    与 product_qc_findings 那类硬闸的分界线（`score_findings` 立的规矩：创意/启发式只提示复核，
    只有广告法与确定性闸门能 BLOCK）：
      · 报告缺失 → info（"建议先跑"），**不是 block**——这些是"审"不是"门"。
      · 报告里的 block → 降为 warn；warn → 降为 info。侧车自己也不产 block，此处是第二道保险。
      · 报告过期 → warn（不用 report_freshness_findings，那个硬编码 block）。
    """
    path = os.path.join(root, relpath)
    report = load_json(path)
    if not isinstance(report, dict):
        return [finding("info", f"{code}_missing", hint, path)]
    if report.get("available") is False:
        return [finding("info", f"{code}_unavailable",
                        f"{relpath} 因缺料降级（available=false），未产出有效结论", path)]
    out = []
    summary = report.get("summary") or {}
    try:
        blocks, warns = int(summary.get("block") or 0), int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        return [finding("info", f"{code}_malformed", f"{relpath} 缺 summary.block/warn", path)]
    if blocks:
        out.append(finding("warn", f"{code}_advisory",
                           f"{relpath} 有 {blocks} 条待处理；启发式只提示复核，不作为付费硬阻断", path))
    if warns:
        out.append(finding("info", f"{code}_warn", f"{relpath} warn={warns}，建议复核", path))
    newest = _newest_mtime([p for p in (os.path.join(root, s) for s in sources) if os.path.exists(p)])
    if newest and os.path.getmtime(path) + 1e-6 < newest:
        out.append(finding("warn", f"{code}_stale",
                           f"{os.path.basename(path)} 早于其输入产物，结论可能过期；建议重跑", path))
    return out


def reference_plan_findings(root):
    """出图前·参考处方落实（事前处方，与 product_qc 的事后诊断互补）。"""
    return _advisory_report_findings(
        root, os.path.join("生产数据", "ad_reference_plan.json"), "ad_reference_plan",
        "未生成逐镜参考处方；建议出图前先跑 ad-image/scripts/reference_planner.py"
        "（产品镜单参考是最危险的漂移源）",
        sources=[os.path.join("脚本", "storyboard.json"),
                 os.path.join("设定库", "asset_registry.json")])


def creative_axis_findings(root):
    """编剧轴 advisory：创意包结构 / 创意承诺兑现 / 文案质量。

    与 score_findings 同档——创意启发式只提示复核，永不硬挡付费。
    """
    out = []
    out.extend(_advisory_report_findings(
        root, os.path.join("生产数据", "ad_concept_pack_check.json"), "ad_concept_pack",
        "未生成创意包机检；建议 ad-concept 落 创意/concept.json 后跑 concept_pack.py",
        sources=[os.path.join("创意", "concept.json"), os.path.join("需求", "brief.json")]))
    out.extend(_advisory_report_findings(
        root, os.path.join("生产数据", "ad_idea_payoff_audit.json"), "ad_idea_payoff",
        "未对账创意承诺→分镜兑现；建议跑 ad-script/scripts/idea_payoff_ledger.py"
        "（big idea/主张定完无人核对是否落镜）",
        sources=[os.path.join("创意", "concept.json"), os.path.join("脚本", "storyboard.json")]))
    out.extend(_advisory_report_findings(
        root, os.path.join("生产数据", "ad_copy_quality_audit.json"), "ad_copy_quality",
        "未跑文案质量机检；建议跑 ad-script/scripts/copy_quality_audit.py",
        sources=[os.path.join("脚本", "voiceover.txt"), os.path.join("脚本", "storyboard.json")]))
    out.extend(_advisory_report_findings(
        root, os.path.join("生产数据", "ad_shot_variety_audit.json"), "ad_shot_variety",
        "未跑分镜视觉多样性机检；建议出图前跑 ad-script/scripts/shot_variety_audit.py"
        "（同景别机位反复/画面复读/场景单调，出图前拦最省钱）",
        sources=[os.path.join("脚本", "storyboard.json")]))
    out.extend(_advisory_report_findings(
        root, os.path.join("生产数据", "ad_product_craft_audit.json"), "ad_product_craft",
        "未跑产品镜工艺声明机检；建议出图前跑 ad-script/scripts/product_craft_audit.py"
        "（光位/质感手法/角度三轴没写进产品镜，AI 只会给平光电商图）",
        sources=[os.path.join("脚本", "storyboard.json")]))
    out.extend(_advisory_report_findings(
        root, os.path.join("生产数据", "ad_performance_cue_audit.json"), "ad_performance_cue",
        "未跑人物镜表演指令机检；建议出图前跑 ad-script/scripts/performance_cue_audit.py"
        "（情绪/视线/可演动作三轴没写进人物镜，AI 只会给死脸假笑）",
        sources=[os.path.join("脚本", "storyboard.json")]))
    return out


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
    findings.extend(registry_snapshot_findings(root))
    findings.extend(creative_axis_findings(root))
    if stage == "image":
        # 出图前：核验生图后端治理（白名单/不混用），此时图还没生成，不查 product_qc。
        findings.extend(image_backend_findings(root))
        # 事前处方：出图前就该开好"每镜喂哪些参考"，等 product_qc 事后发现产品漂就已花钱。
        findings.extend(reference_plan_findings(root))
    if stage in ("video", "compose"):
        findings.extend(platform_pack_findings(root))
        # 图已生成：查存在性 + 产品/品牌色一致性机检（最便宜的拦截点）+ 契约继承。
        findings.extend(image_backend_findings(root))
        findings.extend(image_output_backend_findings(root))
        findings.extend(image_findings(root))
        findings.extend(product_qc_findings(root))
        findings.extend(video_contract_findings(root))
        # 止损账本（advisory）：出图已花钱，进视频/合成前把重抽率/credit 消耗抬到台面上。
        findings.extend(_advisory_report_findings(
            root, os.path.join("生产数据", "ad_stop_loss.json"), "ad_stop_loss",
            "未跑生成止损审计；建议跑 ad-craft/scripts/stop_loss.py --write"
            "（重抽率/单资产次数/credit 消耗，带病续抽是最贵的浪费）",
            sources=[os.path.join("生产数据", "production_events.jsonl")]))
        # animatic 预演（advisory·传统 PPM 纪律）：image2video 是最贵一步，先用首帧+实测时长+VO
        # 拼免费预演签核节奏/镜序，再进付费生成；首帧或时长变更后预演过期。
        findings.extend(_advisory_report_findings(
            root, os.path.join("生产数据", "ad_animatic_manifest.json"), "ad_animatic",
            "未拼 animatic 预演；建议跑 ad-video/scripts/animatic.py"
            "（传统制前会纪律：节奏塌在预演里改是免费的，生完视频再改是重烧）",
            sources=[os.path.join("出图", "分镜", "图片"), os.path.join("脚本", "镜头时长.json"),
                     os.path.join("配音", "vo.wav")]))
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


# gate 每一阶段核验的关键输入（相对路径）。gate 落档新鲜度以它们为准：
# 任一关键输入晚于落档 = gate 结论已过期。stage_acceptance 的 advisory 互链也复用本表，
# 避免两份清单各自漂移。
GATE_INPUT_RELS = {
    "image": [
        os.path.join("需求", "brief.json"),
        os.path.join("脚本", "广告法机检报告.json"),
        os.path.join("脚本", "storyboard.json"),
        os.path.join("脚本", "镜头时长.json"),
        os.path.join("配音", "时长清单.json"),
        os.path.join("设定库", "asset_registry.json"),
        os.path.join("出图", "共享", "asset_registry.json"),
    ],
    "video": [
        os.path.join("需求", "brief.json"),
        os.path.join("脚本", "广告法机检报告.json"),
        os.path.join("脚本", "storyboard.json"),
        os.path.join("脚本", "镜头时长.json"),
        os.path.join("配音", "时长清单.json"),
        os.path.join("设定库", "asset_registry.json"),
        os.path.join("出图", "共享", "asset_registry.json"),
        os.path.join("出图", "分镜", "图片"),
        os.path.join("出图", "分镜", "image_jobs_manifest.json"),
        os.path.join("出图", "分镜", "product_qc.json"),
        os.path.join("出视频", "分镜", "contract_inheritance.json"),
    ],
    "compose": [
        os.path.join("需求", "brief.json"),
        os.path.join("脚本", "广告法机检报告.json"),
        os.path.join("脚本", "storyboard.json"),
        os.path.join("脚本", "镜头时长.json"),
        os.path.join("配音", "时长清单.json"),
        os.path.join("设定库", "asset_registry.json"),
        os.path.join("出图", "共享", "asset_registry.json"),
        os.path.join("出图", "分镜", "图片"),
        os.path.join("出图", "分镜", "image_jobs_manifest.json"),
        os.path.join("出图", "分镜", "product_qc.json"),
        os.path.join("出视频", "分镜", "contract_inheritance.json"),
        os.path.join("出视频", "分镜", "视频"),
        os.path.join("出视频", "分镜", "video_qc.json"),
    ],
}


def gate_report_path(root, stage):
    return os.path.join(root, "生产数据", "gate_reports", f"{stage}.json")


def record_gate_report(root, payload):
    """把本次 gate 结果落档到 生产数据/gate_reports/<stage>.json（原子写）。

    两链哲学：验收（stage_acceptance）管「完成」、gate 管「花钱」，各自独立；但两边要互相
    可见——落档让验收侧能 advisory 提示「花钱 gate 未跑/已过期」，而不必重放 gate 逻辑。
    落档含 findings 摘要、时间戳与被检输入清单（相对路径 + 当时 mtime），供人和机器复盘。
    """
    root = os.path.abspath(root)
    stage = payload["stage"]
    checked_inputs = []
    for rel in GATE_INPUT_RELS.get(stage, []):
        path = os.path.join(root, rel)
        row = {"path": rel, "exists": os.path.exists(path)}
        if row["exists"]:
            row["mtime"] = _newest_mtime([path])
        checked_inputs.append(row)
    doc = {
        "schema_version": 1, "kind": "ad_gate_report", "stage": stage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": payload["summary"],
        "findings": payload["findings"],
        "checked_inputs": checked_inputs,
    }
    out_path = gate_report_path(root, stage)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, out_path)
    return out_path


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
    ap.add_argument("--no-record", action="store_true",
                    help="不落档 生产数据/gate_reports/<stage>.json（默认每次运行都落档，供验收侧互链）")
    args = ap.parse_args()
    payload = run_gate(args.project_root, args.stage, args.allow_placeholder)
    if not args.no_record:
        record_gate_report(args.project_root, payload)
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
