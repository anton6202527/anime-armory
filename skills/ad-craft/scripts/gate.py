#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine gate for paid/high-risk ad stages: image, video, compose.

This is the deterministic counterpart to the SKILL.md reminders. It blocks
missing brief compliance, upstream blockers, and final-compose hazards before
money or irreversible production work starts.
"""
import argparse
import json
import os
import sys

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


def image_backend_findings(root):
    """生图后端治理（安全 invariant）：拦 ① 禁用/逆向后端 ② 项目内后端混用。"""
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
    # 后端混用：_设置.md 与 _meta.json 指向不同 canonical 后端 = block。
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    meta_val = (meta.get("image_backend") or "").strip()
    if meta_val:
        meta_canon, meta_kind = contract.classify_image_backend(meta_val)
        if canon and meta_canon and meta_canon != canon:
            out.append(finding("block", "image_backend_mixed",
                                f"项目内后端混用：_设置.md『{setting_val}』≠ _meta.json『{meta_val}』，一个项目只允许一个生图后端"))
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
    if warns:
        out.append(finding("warn", "product_qc_warn", f"产品一致性 warn={warns}，需人工确认", path))
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
    if has_files(folder, (".png", ".jpg", ".jpeg", ".webp")):
        return []
    return [finding("block", "image_frames_missing", "缺逐镜首帧/尾帧图片", folder)]


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
    return out


def video_clip_findings(root):
    folder = os.path.join(root, "出视频", "分镜", "视频")
    if has_files(folder, (".mp4", ".mov", ".m4v")):
        return []
    return [finding("block", "video_clips_missing", "缺出视频 Clip 文件", folder)]


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
    if stage == "image":
        # 出图前：核验生图后端治理（白名单/不混用），此时图还没生成，不查 product_qc。
        findings.extend(image_backend_findings(root))
    if stage in ("video", "compose"):
        # 图已生成：查存在性 + 产品/品牌色一致性机检（最便宜的拦截点）+ 契约继承。
        findings.extend(image_findings(root))
        findings.extend(product_qc_findings(root))
        findings.extend(video_contract_findings(root))
    if stage == "compose":
        findings.extend(video_clip_findings(root))
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
        import progress_set  # 同目录 sibling
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
