#!/usr/bin/env python3
"""一致性编排（O1）——一键串跑全部一致性检测器，出一张汇总分档报告。

2026 产线核心已从"单点能力"转到**编排层**：检测器再多，没被自动跑就等于没有。
本脚本把散落的检测器统一调起来，n2d-review 模式①工作流第 1 步「跑机检套件」即调它：

  语义谱系 P0 · 状态百科 P1 · 多模态 P2 · 视觉契约继承 · 锚点门 N3 · 脸 G1 ·
  发型 H1 · 服装/配色 N1 · 片内时序 N2 · 场景 O2 · 糊/低质 N4 · 手部/解剖 N5 ·
  身高比例 R1 · 轴线视线 X1 · 天气时辰 W1（含光位方向 W2 advisory）· 字幕安全区 L2 ·
  称谓口头禅 A1 · 风格 S1 · 字幕对齐 L1 · 音画同步 AV1（口型↔配音偏移·advisory）·
  节奏密度 Rhythm（节奏/留存启发式 advisory）· 空间站位 B1（跨镜站位/遮挡）·
  视频 VLM 判题 VLM1 · 视频语义一致 VSEM · 多人对话音画 DAV · 物理因果链 CG1 ·
  相机空间轨迹 CAM1 · 运动质量 MOT1 · 主体视频一致 S2V ·
  生产一致性补强（实体记忆/物件常驻/持有账本/物理事件图/视频证据完整性/状态转场/交互图谱/成片探针/强配方/包装/语域/平面图/成本路由/人审校准/probe）

每个子检测器各自缺库优雅跳过（见各脚本）；本编排只汇总、不重复实现。
纯函数 `summarize` 无依赖、带 pytest。

用法：python3 consistency_audit.py <作品根> 第N集 [--json]
退出码：有任一 🔴 → 1，否则 0。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import (  # noqa: E402  findings kind / 生产数据目录 / 一致性维度单一真值源
    CONSISTENCY_FINDINGS_KIND,
    consistency_dim_spec,
    production_dir,
)
from n2d_contract_diff import diff_contracts  # noqa: E402  视觉契约继承 Diff 核心（common 层单一真值源）
from n2d_cross_episode import core_scene_names  # noqa: E402  核心场景判定单一真值源（与 gate 跨集光位轴线共用）
# Seam conditioning hints (writes advisory JSON for next-episode prompt generation)
import importlib.util as _imu
_seam_cond_spec = _imu.find_spec("seam_conditioning")
if _seam_cond_spec is not None:
    import seam_conditioning as seam_cond  # noqa: E402
else:
    seam_cond = None  # type: ignore[assignment]

import face_consistency as fc
import outfit_consistency as oc
import hair_consistency as hc
import marks_consistency as mk
import temporal_consistency as tcheck
import quality_check as qc
import hand_anatomy as hand
import scale_consistency as scc
import axis_geometry
import world_continuity as wcont
import subtitle_safearea as ssa
import scene_consistency as sc
import style_consistency as stc
import dof_consistency as dof
import vfx_color_consistency as vfxc
import color_grade_consistency as cgc
import semantic_continuity as semc
import state_continuity as statec
import address_consistency as addr
import multimodal_consistency as mmc
import subtitle_align as sa
import lipsync_consistency as lipc
import audio_continuity as audioc
import scene_blocking_continuity as sbc
import pacing_retention as pr
import video_vlm_consistency as vvlm
import video_semantic_consistency as vsem
import dialogue_av_consistency as davc
import causal_event_consistency as cg
import camera_trajectory_consistency as camt
import motion_quality_consistency as motq
import subject_video_consistency as s2vc
import spectacle_video_qc as svqc
import production_consistency as pc
import extended_consistency as ec
import costume_consistency as cstc
import expression_verification as expv
import state_pixel_verify as spv
import av_emotion_consistency as avec
import expression_state_consistency as exstate  # EXP2 状态化表情（state_delta 改 identity invariants → block）
import motion_grammar_consistency as mgram      # MG1 运动语法（运镜/动作语义 advisory）
import audio_space_consistency as aspace        # ASP/NV1 声音空间 + 原生声纹路由证据
import object_state_continuity as objstate      # OST 物件状态（未声明的道具状态互斥翻转）

# 音色声纹 / 跨集 voice_key 漂移住在 n2d-identity（同线 n2d-* 互引允许）。2026-06 接入主审计：
# 此前音色机检只走 n2d-identity identity.py --write 旁路，纯 consistency_audit 调用漏掉音色漂移
# （n2d_schema 旧注 1 的已知缺口）。voice_consistency 纯 stdlib 报跨集换声；voice_print 用 speaker
# embedding 量真实音色相似度，缺后端/音频优雅降级交人判。advisory：block 封顶 warn，不硬阻断视觉 gate。
_IDENTITY_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d-identity", "scripts"))
if _IDENTITY_SCRIPTS not in sys.path:
    sys.path.insert(0, _IDENTITY_SCRIPTS)
try:
    import voice_consistency as vcon  # noqa: E402
except Exception:  # pragma: no cover - 缺文件/异常布局兜底
    vcon = None  # type: ignore[assignment]
try:
    import voice_print_consistency as vprint  # noqa: E402
except Exception:  # pragma: no cover
    vprint = None  # type: ignore[assignment]


PRODUCTION_CONSISTENCY_META = {
    "实体记忆(EMB)": {
        "stage": "image",
        "artifacts": ("生产数据/entity_memory_bank.json", "出图/共享/entity_memory_bank.json", "出图/共享/identity_registry.json", "脚本/{ep}/storyboard.json"),
    },
    "物件常驻(O3)": {
        "stage": "image",
        "artifacts": ("脚本/{ep}/storyboard.json", "出图/{ep}/prompt/01_分镜出图.md", "出图/共享/asset_registry.json"),
    },
    "持有账本(POS)": {
        "stage": "script_stage2",
        "artifacts": ("脚本/{ep}/storyboard.json", "生产数据/possession_ledger_{ep}.json"),
    },
    "视线状态回读(X2)": {
        "stage": "image",
        "artifacts": ("脚本/{ep}/storyboard.json", "出图/{ep}/prompt/01_分镜出图.md"),
    },
    "状态转场视频证据(ST1)": {
        "stage": "video",
        "artifacts": ("脚本/{ep}/storyboard.json", "生产数据/state_transition_manifest_{ep}.json"),
    },
    "交互接触(I1)": {
        "stage": "script_stage2",
        "artifacts": ("脚本/{ep}/storyboard.json", "出视频/{ep}/prompt/video_model_routes.json"),
    },
    "结构化交互图谱(I2)": {
        "stage": "script_stage2",
        "artifacts": ("脚本/{ep}/storyboard.json",),
    },
    "物理事件图(PHY)": {
        "stage": "review",
        "artifacts": ("生产数据/physical_event_graph_{ep}.json", "生产数据/causal_event_graph_{ep}.json", "出视频/{ep}"),
    },
    "视频证据完整性(EVID)": {
        "stage": "review",
        "artifacts": ("生产数据/video_eval_manifest_{ep}.json", "生产数据/*_{ep}.json", "出视频/{ep}", "合成/{ep}"),
    },
    "成片统一(C1)": {
        "stage": "compose",
        "artifacts": ("合成/{ep}", "出视频/{ep}/prompt/video_model_routes.json"),
    },
    "成片时间线探针(FT1)": {
        "stage": "compose",
        "artifacts": ("合成/{ep}/final_timeline_probe.json", "合成/{ep}"),
    },
    "生成配方(RCP)": {
        "stage": "review",
        "artifacts": ("生产数据/production_events.jsonl", "生产数据/generation_recipe_{ep}.json"),
    },
    "强配方Schema(RCP2)": {
        "stage": "review",
        "artifacts": ("生产数据/production_events.jsonl", "生产数据/generation_recipe_{ep}.json"),
    },
    "系列包装(PKG)": {
        "stage": "compose",
        "artifacts": ("设定库/series_packaging.json", "合成/交付"),
    },
    "台词语域(D1)": {
        "stage": "script_stage1",
        "artifacts": ("脚本/{ep}/voiceover.txt", "设定库/dialogue_register.json"),
    },
    "场景平面(FP1)": {
        "stage": "script_stage2",
        "artifacts": ("脚本/{ep}/storyboard.json", "设定库/scene_floorplan.json"),
    },
    "成本路由(K1)": {
        "stage": "review",
        "artifacts": ("生产数据/production_events.jsonl", "出视频/{ep}/prompt/video_model_routes.json"),
    },
    "人审校准集(CAL)": {
        "stage": "review",
        "artifacts": ("生产数据/consistency_calibration.jsonl", "生产数据/consistency_findings_{ep}.json"),
    },
    "一致性探针包(PROBE)": {
        "stage": "review",
        "artifacts": ("生产数据/consistency_probe_pack.json", "设定库/consistency_probe_pack.json"),
    },
}


def _verdicts(rows: List[dict]) -> List[str]:
    return [r.get("verdict", "ok") for r in rows]


def summarize(sections: Dict[str, dict]) -> dict:
    """把各检测器的结果压成 {dim: {block,warn,ok,skipped}} + 总 block 数。纯函数·可测。"""
    out: Dict[str, dict] = {}
    total_block = 0
    for dim, sec in sections.items():
        skipped = sec.get("skipped", False)
        vs = sec.get("verdicts", [])
        b = sum(1 for v in vs if v == "block")
        w = sum(1 for v in vs if v == "warn")
        ok = sum(1 for v in vs if v == "ok")
        out[dim] = {"block": b, "warn": w, "ok": ok, "n": len(vs), "skipped": skipped}
        total_block += b
    return {"by_dim": out, "total_block": total_block}


def audit_precision_level(capabilities: Dict[str, Any]) -> str:
    """本次审计的总精度三档（契约 PRECISION_*）。把"本机机检能力"映射成诚实根信号，
    根治"缺库全 skip → 0 block → 退出 0 全绿"的假绿灯：
    无 Pillow=像素级一致性一概没检(none)；无 insightface=脸跑降级(degraded)；齐全=full。"""
    if not capabilities.get("pillow"):
        return "none"
    if not capabilities.get("insightface"):
        return "degraded"
    return "full"


def _image_qc_full_precision_evidence(root: str, ep: str) -> Optional[dict]:
    """Return reusable full-precision image_qc evidence when it is current.

    consistency_audit is often run from the system Python, while image_qc may
    already have been run in the project QC environment with insightface.  The
    release gate should not mark that completed evidence as degraded merely
    because the current interpreter lacks insightface.  Freshness is checked
    against episode PNG mtimes so stale reports are not accepted.
    """
    path = os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    env = payload.get("qc_environment") if isinstance(payload.get("qc_environment"), dict) else {}
    coverage = payload.get("face_reference_coverage") if isinstance(payload.get("face_reference_coverage"), dict) else {}
    precision = str(env.get("precision_level") or coverage.get("precision_level") or "").strip().lower()
    if precision != "full":
        return None
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if int(summary.get("hard_blocks") or 0) > 0:
        return None
    for key in ("missing", "pending", "unclassified"):
        if coverage.get(key):
            return None
    try:
        report_mtime = os.path.getmtime(path)
    except OSError:
        return None
    image_dir = os.path.join(root, "出图", ep, "图片")
    latest_png = 0.0
    for name in os.listdir(image_dir) if os.path.isdir(image_dir) else []:
        if not name.lower().endswith(".png"):
            continue
        try:
            latest_png = max(latest_png, os.path.getmtime(os.path.join(image_dir, name)))
        except OSError:
            continue
    if latest_png and latest_png > report_mtime + 1.0:
        return None
    return {
        "path": os.path.relpath(path, root),
        "precision_level": "full",
        "covered": coverage.get("covered"),
        "required": coverage.get("required"),
    }


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _video_semantic_embedding_evidence(root: str, ep: str) -> Optional[dict]:
    """Return reusable S2V embedding evidence from a fresh DINO/CLIP report.

    The review gate may run from the system Python while `video_semantic_runner`
    was already executed in the QC environment with torch.  Under-proven means
    "no numeric embedding proof exists", not "the current interpreter cannot
    import torch".  Freshness is checked with both mtimes and recorded video
    hashes so stale semantic reports cannot mask changed MP4s.
    """
    path = os.path.join(root, "生产数据", f"video_semantic_consistency_{ep}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    method = str(payload.get("embedding_method") or "").strip().lower()
    model = str(payload.get("embedding_model") or "").strip().lower()
    if not any(token in (method + " " + model) for token in ("dinov2", "clip", "dreamsim")):
        return None
    segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
    if not segments:
        return None
    try:
        report_mtime = os.path.getmtime(path)
    except OSError:
        return None
    checked = 0
    numeric = 0
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        video = str(seg.get("video") or "").strip()
        if not video:
            continue
        video_path = video if os.path.isabs(video) else os.path.join(root, video)
        if not os.path.isfile(video_path):
            return None
        try:
            if os.path.getmtime(video_path) > report_mtime + 1.0:
                return None
        except OSError:
            return None
        expected_sha = str(seg.get("video_sha256") or "").strip().lower()
        if expected_sha and _sha256_file(video_path).lower() != expected_sha:
            return None
        checked += 1
        for key in ("subject_similarity", "start_frame_similarity", "mid_frame_nearest_reference_similarity", "end_frame_similarity"):
            try:
                float(seg.get(key))
                numeric += 1
                break
            except (TypeError, ValueError):
                continue
    if checked <= 0 or numeric <= 0:
        return None
    return {
        "path": os.path.relpath(path, root),
        "embedding_model": payload.get("embedding_model"),
        "embedding_method": payload.get("embedding_method"),
        "segments_checked": checked,
        "numeric_segments": numeric,
    }


def apply_image_qc_precision_evidence(capabilities: Dict[str, Any], root: str, ep: str) -> Dict[str, Any]:
    """Upgrade capability facts with fresh full image_qc evidence, if present."""
    caps = dict(capabilities)
    evidence = _image_qc_full_precision_evidence(root, ep)
    if not evidence:
        return caps
    caps["insightface"] = True
    caps["image_qc_full_evidence"] = evidence
    notes = [
        str(note) for note in (caps.get("notes") or [])
        if "本机无 insightface" not in str(note)
    ]
    notes.append(
        f"复用新鲜 full image_qc 证据：{evidence['path']}（covered={evidence.get('covered')}, required={evidence.get('required')}）。"
    )
    caps["notes"] = notes
    caps["degraded"] = not caps.get("pillow") or not caps.get("insightface")
    return caps


def apply_video_semantic_embedding_evidence(capabilities: Dict[str, Any], root: str, ep: str) -> Dict[str, Any]:
    """Upgrade S2V evidence facts with a fresh embedding report, if present."""
    caps = dict(capabilities)
    evidence = _video_semantic_embedding_evidence(root, ep)
    if not evidence:
        return caps
    caps["s2v_embedding_evidence"] = evidence
    missing = [
        str(item) for item in (caps.get("advanced_metrics_missing") or [])
        if "DINOv2" not in str(item) and "CoTracker" not in str(item)
    ]
    if missing:
        caps["advanced_metrics_missing"] = missing
    else:
        caps.pop("advanced_metrics_missing", None)
    notes = [str(note) for note in (caps.get("notes") or [])]
    if not missing:
        notes = [
            note for note in notes
            if "DINOv2" not in note and "进阶数值化一致性指标未运行" not in note
        ]
    notes.append(
        f"复用新鲜 S2V embedding 证据：{evidence['path']}（segments={evidence.get('numeric_segments')}/{evidence.get('segments_checked')}）。"
    )
    caps["notes"] = notes
    return caps


# ── 证据等级账本（#3·2026-06-27）─────────────────────────────────────────────
# 把"这条一致性维度本次到底验到什么程度"显式化：闸的"通过"强度 = 最弱可适用维度的证据级；
# 某维度本可验到 pixel/embedding，却因依赖缺位只到 structured/declared → under_proven(PENDING)。
# 设计要点（避免与既有闸重复 block）：
#   - pixel tier（脸/服装/发型/场景/景深/风格…）依赖全局 pillow/insightface，其 degraded 已由
#     precision_level 全局闸在交付边界 block——这里只给它们标 proof_type 做**可见化**，不重复 block；
#   - advanced tier（S2V 跨帧主体一致需 torch-DINOv2 / AV1 口型词级需 SyncNet）此前"未跑也不阻断"
#     （见 probe_capabilities 注释），是**完全不可见**的盲区——#3 真正新增的可见化 + 交付边界 PENDING；
#   - 其余=structured 文本检，跑了即达 structured 级，不 under_proven。
PROOF_ORDER = {"absent": 0, "declared": 1, "structured": 2, "embedding": 3, "pixel": 4}
_PIXEL_TIER_CODES = {"G1", "G1b", "G5", "EXP1", "EXP2", "EXP3", "N1", "COST", "H1", "MK1",
                     "O2", "B1", "S1", "DOF1", "VFXC", "GRADE1", "N4", "N5", "R1", "X1", "W1", "SP1V"}
_EMBED_TIER_CODES = {"G1", "G5"}        # 人脸=embedding 证据（ArcFace 余弦）
_TORCH_TIER_CODES = {"S2V"}            # DINOv2 跨帧主体一致：torch 缺则退结构级
_SYNCNET_TIER_CODES = {"AV1"}         # 口型词级数值：SyncNet 缺则退启发式


def _dim_code(dim: str) -> str:
    """维度名里括号中的稳定代号（"脸(G1)"→"G1"）。按代号建注册表，Chinese label 改名不破。纯函数。"""
    m = re.search(r"\(([A-Za-z0-9]+)\)", str(dim or ""))
    return m.group(1) if m else ""


def evidence_grade(sections: Dict[str, dict], capabilities: Optional[Dict[str, Any]] = None) -> dict:
    """各维度证据等级账本 → {by_dim:{dim:{tier,actual,achievable,applicable,under_proven}}, under_proven:[...], weakest}。

    actual = 本次实际验到的证据级；achievable = 依赖齐备时这条维度能达到的最强级。
    under_proven 只对 advanced tier（torch/syncnet 进阶依赖缺位、此前完全不阻断）置位——pixel tier 的
    degraded 由全局 precision_level 闸处置，不在此重复。纯函数·可测。"""
    caps = capabilities or {}
    pixel_full = bool(caps.get("pillow")) and bool(caps.get("insightface"))
    torch_ok = bool(caps.get("torch"))
    s2v_embedding_ok = bool(caps.get("s2v_embedding_evidence"))
    syncnet_ok = bool(caps.get("syncnet"))
    by_dim: Dict[str, dict] = {}
    under: List[str] = []
    applicable_actual: List[str] = []
    for dim, sec in sections.items():
        code = _dim_code(dim)
        skipped = bool(sec.get("skipped", False))
        # 有内容可验：跑过(未 skip) / 有 verdicts / 有 precision 字段（runner 真的 engage 了内容）。
        has_content = (not skipped) or bool(sec.get("verdicts")) or (sec.get("precision") is not None)
        if code in _TORCH_TIER_CODES:
            tier = "advanced"; achievable = "embedding"
            actual = "embedding" if (torch_ok or s2v_embedding_ok) else ("structured" if has_content else "absent")
        elif code in _SYNCNET_TIER_CODES:
            tier = "advanced"; achievable = "pixel"
            prec = str(sec.get("precision") or "")
            actual = "pixel" if (syncnet_ok or prec == "full") else ("structured" if has_content else "absent")
        elif code in _PIXEL_TIER_CODES:
            tier = "pixel"; achievable = "embedding" if code in _EMBED_TIER_CODES else "pixel"
            actual = achievable if pixel_full else ("declared" if has_content else "absent")
        else:
            tier = "structured"; achievable = "structured"
            actual = "structured" if has_content else "absent"
        applicable = has_content
        # 只有 advanced tier 的不足计入 under_proven（pixel tier 走全局 precision 闸，structured 已达级）。
        is_under = applicable and tier == "advanced" and PROOF_ORDER[actual] < PROOF_ORDER[achievable]
        by_dim[dim] = {"tier": tier, "actual": actual, "achievable": achievable,
                       "applicable": applicable, "under_proven": is_under}
        if applicable:
            applicable_actual.append(actual)
        if is_under:
            under.append(dim)
    weakest = min(applicable_actual, key=lambda a: PROOF_ORDER[a]) if applicable_actual else "absent"
    return {"by_dim": by_dim, "under_proven": sorted(under), "weakest": weakest}


PRODUCTION_PROFILE_VALUES = {"production", "prod", "release", "strict", "投放", "上线", "正式", "发布", "严格", "生产"}


def normalize_profile(value: str) -> str:
    text = str(value or "").strip().lower()
    return "production" if any(v in text for v in PRODUCTION_PROFILE_VALUES) else "demo"


def exit_code_for(summary: dict, profile: str = "demo") -> int:
    """退出码：有 🔴=1；否则总精度=none（啥像素都没检过）=2 inconclusive；其余=0。
    让 CI/批处理调用方据退出码区分"检查了很干净"(0) 与"根本没法检查"(2)。"""
    if summary.get("total_block"):
        return 1
    if summary.get("precision_level") == "none":
        return 2
    if normalize_profile(profile) == "production" and summary.get("precision_level") != "full":
        if os.environ.get("N2D_ALLOW_DEGRADED_QC") == "1":
            return 0
        return 1
    return 0


def unique(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def shot_label(value: Any) -> List[str]:
    labels: List[str] = []
    if isinstance(value, int):
        labels.append(f"Clip_{value:02d}")
    text = str(value or "")
    for match in re.finditer(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)", text):
        labels.append(f"Clip_{int(match.group(1)):02d}")
    return unique(labels)


def artifacts_from_text(text: str) -> List[str]:
    pattern = r"(?:出图|出视频|合成|脚本|设定库|合规)/[^\s，。；;|)）]+"
    return unique(m.group(0).rstrip("，。；;:：") for m in re.finditer(pattern, text or ""))


def contract_inheritance_result(root: str, ep: str) -> dict:
    """Read image/video overview contracts and expose inherit_contract diff as audit rows."""
    img_rel = os.path.join("出图", ep, "prompt", "00_总览.md")
    vid_rel = os.path.join("出视频", ep, "prompt", "00_总览.md")
    img_path = os.path.join(root, img_rel)
    vid_path = os.path.join(root, vid_rel)
    if not os.path.isfile(img_path) or not os.path.isfile(vid_path):
        missing = [rel for rel, path in ((img_rel, img_path), (vid_rel, vid_path)) if not os.path.isfile(path)]
        return {"available": False, "fields": [], "notes": [f"契约继承检查跳过：缺 {', '.join(missing)}"]}
    try:
        rows = diff_contracts(
            open(img_path, encoding="utf-8").read(),
            open(vid_path, encoding="utf-8").read(),
        )
    except Exception as exc:
        return {"available": False, "fields": [], "notes": [f"契约继承检查跳过：{exc}"]}
    fields: List[dict] = []
    for row in rows:
        severity = str(row.get("severity") or "")
        verdict = "ok" if severity == "pass" else severity if severity in {"block", "warn"} else "warn"
        fields.append({
            "verdict": verdict,
            "field": row.get("field"),
            "message": row.get("note") or row.get("status") or "",
            "status": row.get("status"),
            "loc": f"视觉契约/{row.get('field')}",
            "affected_artifacts": [img_rel, vid_rel],
        })
    return {"available": True, "fields": fields, "notes": []}


# Per-dimension risk_score defaults for WARN tiering (consumed by gate.py display).
# Pattern: substring match against the dimension label, first match wins.
# High (0.7+): face, identity, cross-episode — audience-visible drift
# Moderate (0.4-0.7): scene, outfit, hair, scale — noticeable but not fatal
# Low (<0.4): style, tone, advisory — may be intentional creative choice
_DIM_RISK_MAP: List[Tuple[str, float]] = [
    ("脸(G1)", 0.85), ("无脸崩坏", 0.80), ("锚点门(N3)", 0.80),
    ("跨集脸漂(G5)", 0.75), ("语义谱系(P0)", 0.80), ("状态百科(P1)", 0.75),
    ("多模态(P2)", 0.70), ("称谓口头禅(A1)", 0.60),
    ("片内时序(N2)", 0.70), ("服装配色(N1)", 0.55), ("发型(H1)", 0.55),
    ("辨识标记(MK1)", 0.60), ("场景(O2)", 0.55), ("字幕对齐(L1)", 0.60),
    ("字幕安全区(L2)", 0.50), ("身高比例(R1)", 0.50), ("风格(S1)", 0.30),
    ("景深一致(DOF1)", 0.25), ("特效窜色(VFXC)", 0.30),
    ("色温调色(GRADE1)", 0.25), ("天气时辰(W1)", 0.50),
    ("光位方向(W2)", 0.55), ("轴线视线(X1)", 0.55),
    ("空间站位(B1)", 0.50), ("接缝接力", 0.65), ("视频VLM判题(VLM1)", 0.60),
    ("视频语义一致(VSEM)", 0.65), ("多人对话音画(DAV)", 0.55),
    ("物理因果链(CG1)", 0.50), ("相机空间轨迹(CAM1)", 0.45),
    ("运动质量(MOT1)", 0.45), ("主体视频一致(S2V)", 0.65),
    ("高动态成片证据(SPECV)", 0.55),
    ("音画同步(AV1)", 0.55), ("配音情绪弧(VEA)", 0.45),
    ("口音方言(ACC)", 0.40), ("音乐衔接(BGM)", 0.30),
    ("节奏密度(Rhythm)", 0.25), ("糊/低质(N4)", 0.50),
    ("手部/解剖(N5)", 0.45), ("实体记忆(EMB)", 0.50),
    ("物件常驻(O3)", 0.50), ("持有账本(POS)", 0.50),
    ("视线状态回读(X2)", 0.45), ("状态转场视频证据(ST1)", 0.40),
    ("交互接触(I1)", 0.50), ("结构化交互图谱(I2)", 0.45),
    ("物理事件图(PHY)", 0.45), ("视频证据完整性(EVID)", 0.40),
    ("成片统一(C1)", 0.35), ("成片时间线探针(FT1)", 0.30),
    ("生成配方(RCP)", 0.30), ("强配方Schema(RCP2)", 0.35),
    ("系列包装(PKG)", 0.20), ("台词语域(D1)", 0.35),
    ("场景平面(FP1)", 0.25), ("成本路由(K1)", 0.20),
    ("人审校准集(CAL)", 0.20), ("一致性探针包(PROBE)", 0.20),
    ("系统面板(UI1)", 0.30), ("音乐母题(LM1)", 0.20),
    ("系列调色(GRD)", 0.25), ("环境声(AMB)", 0.20),
    ("跨集体型(R2)", 0.45), ("在场检测(O3V)", 0.45),
    ("外观判官(VAP)", 0.55), ("表情连续(EXP1)", 0.70), ("表情过锁(EXP3)", 0.20),
    ("伏笔兑现(SP1)", 0.30), ("文字渲染(OCR1)", 0.35),
    ("服装独立(COST)", 0.50), ("状态像素验证(SP1V)", 0.75),
    ("音画情绪一致(AVE)", 0.50),
    ("状态化表情(EXP2)", 0.45), ("运动语法(MG1)", 0.35),
    ("声音空间(ASP)", 0.30), ("原生声纹(NV1)", 0.55),
    ("物件状态(OST)", 0.50), ("音色声纹", 0.55),
    ("打斗撞点(SPEC-APEX)", 0.60),
]


def _dim_risk_score(dim: str) -> float:
    """Auto-derived risk_score from consistency dimension label.
    Falls back to 0.5 (moderate) for unrecognised dims."""
    for pattern, score in _DIM_RISK_MAP:
        if pattern in dim:
            return score
    return 0.5  # unrecognised → moderate (conservative)


def normalize_details(rows: Sequence[dict], *, dim: str, ep: str, stage: str,
                      default_artifacts: Sequence[str], limit: int = 40) -> List[dict]:
    details: List[dict] = []
    for raw in rows[:limit]:
        row = dict(raw)
        shots: List[str] = []
        for key in ("shot", "heading", "target", "png", "message", "loc"):
            shots.extend(shot_label(row.get(key)))
        artifacts = list(default_artifacts)
        for key in ("source", "target", "png", "message", "loc"):
            artifacts.extend(artifacts_from_text(str(row.get(key) or "")))
        png = str(row.get("png") or "")
        if png and "/" not in png:
            artifacts.append(f"出图/{ep}/图片/{png}")
        row.setdefault("dimension", dim)
        row.setdefault("return_to_stage", stage)
        row.setdefault("rerun_scope", default_scope(dim, stage))
        # risk_score for WARN tiering (carried through to gate.py display).
        # Detectors can override by setting risk_score on individual rows;
        # this default is per-dimension based on the detector's real-world impact.
        if "risk_score" not in row:
            row["risk_score"] = _dim_risk_score(dim)
        row["affected_shots"] = unique([*row.get("affected_shots", []), *shots])
        row["affected_artifacts"] = unique([*row.get("affected_artifacts", []), *artifacts])
        details.append(row)
    return details


def default_scope(dim: str, stage: str) -> str:
    spec = consistency_dim_spec(dim)
    if spec:
        return str(spec.get("scope") or f"回 {stage} 修复该一致性维度。")
    if dim == "语义谱系(P0)":
        return "回 n2d-script 阶段2或 prompt 生成层，修 storyboard→出图/出视频的语义继承缺口。"
    if dim == "状态百科(P1)":
        return "回 n2d-image，修 visual_state_ledger / 出图分镜 prompt 的状态锁；必要时回 storyboard 修状态演进。"
    if dim == "多模态(P2)":
        return "回 n2d-image，按离群道具/场景/法宝参考组只重出受影响镜头。"
    return f"回 {stage} 修复该一致性维度。"


def section_from_result(
    *,
    dim: str,
    result: dict,
    detail_key: str,
    skipped: bool,
    ep: str,
    stage: str,
    default_artifacts: Sequence[str],
) -> dict:
    details = normalize_details(
        [r for r in result.get(detail_key, []) if isinstance(r, dict)],
        dim=dim,
        ep=ep,
        stage=stage,
        default_artifacts=default_artifacts,
    )
    return {
        "skipped": skipped,
        "verdicts": _verdicts(details),
        "notes": result.get("notes", []),
        "details": details,
        "return_to_stage": stage,
        "rerun_scope": default_scope(dim, stage),
    }


def build_auto_return_tasks(sections: Dict[str, dict]) -> List[dict]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for dim, sec in sections.items():
        stage = str(sec.get("return_to_stage") or "image")
        active = [d for d in sec.get("details", []) if d.get("verdict") in ("block", "warn")]
        if not active:
            continue
        key = (stage, dim)
        item = grouped.setdefault(key, {
            "return_to_stage": stage,
            "dimensions": [dim],
            "scope": [str(sec.get("rerun_scope") or default_scope(dim, stage))],
            "affected_shots": [],
            "affected_artifacts": [],
            "findings": [],
        })
        for detail in active:
            item["affected_shots"].extend(detail.get("affected_shots", []))
            item["affected_artifacts"].extend(detail.get("affected_artifacts", []))
            item["findings"].append(detail)
    tasks: List[dict] = []
    for item in grouped.values():
        shots = unique(item["affected_shots"])
        artifacts = unique(item["affected_artifacts"])
        scope = "；".join(unique(item["scope"]))
        if shots:
            scope += "；定位镜头：" + "、".join(shots)
        if artifacts:
            scope += "；定位产物：" + "、".join(artifacts[:8])
        tasks.append({
            "return_to_stage": item["return_to_stage"],
            "dimensions": item["dimensions"],
            "scope": scope,
            "affected_shots": shots,
            "affected_artifacts": artifacts,
            "findings": item["findings"][:12],
        })
    return tasks


def active_findings(details: Sequence[dict]) -> List[dict]:
    """details → 检出条目（block/warn），逐条带 severity（外发 findings 结构）。"""
    out: List[dict] = []
    for detail in details:
        if not isinstance(detail, dict) or detail.get("verdict") not in ("block", "warn"):
            continue
        row = dict(detail)
        row["severity"] = row.get("verdict")
        out.append(row)
    return out


def _combat_cue_apex_rows(root: str, ep: str) -> List[dict]:
    """打斗剪辑 cue↔apex 对齐 findings → consistency rows（核心打斗镜在 gate 升 BLOCK）。

    in-process 调 n2d-script 的 combat_cue_apex_audit.build_audit（纯 stdlib·同 n2d 线·非跨线·
    与 sc.analyze/exstate.run 等同样 in-process），保证每跑必新鲜、不被静默跳过。任何异常→[]（绝不让
    打斗审计拖垮总审）。row 带 scene(场景 LOC·核心场景对账) + clip_label(高潮/爆点 key-scene 对账) +
    metric(code) → _strict_advisory_should_block 据此把 warn 码在核心打斗镜×交付边界升 BLOCK。"""
    try:
        import importlib.util
        from pathlib import Path as _Path
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "n2d-script", "scripts", "combat_cue_apex_audit.py")
        spec = importlib.util.spec_from_file_location("combat_cue_apex_audit", path)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        audit = mod.build_audit(_Path(root), ep)
    except Exception:
        return []
    rows: List[dict] = []
    for f in audit.get("findings") or []:
        if not isinstance(f, dict):
            continue
        rows.append({
            "scene": f.get("scene") or f.get("clip_id"),
            "shot": f.get("clip_id"),
            "verdict": "warn" if f.get("level") == "warn" else "info",
            "msg": f.get("msg"),
            "metric": f.get("code"),
            "clip_label": f.get("clip_label"),
            "spectacle_type": f.get("spectacle_type"),
            "return_to_stage": "script_stage2",
        })
    return rows


def _episode_num(ep: str) -> int:
    m = re.search(r"(\d+)", str(ep))
    return int(m.group(1)) if m else 0


def cross_episode_face_rows(root: str, ep: str, face_result: dict) -> List[dict]:
    """G5 跨集脸漂：累计每集每角色脸均值，再跑 fc.cross_episode_drift。

    治"每集各自过 floor、角色却逐集系统性偏离锚点"——单集机检看不到的漂。把本集均值落进
    `生产数据/face_ep_means.json` 自累积（审计本就会写 findings/ledger，侧车账本同源），按集序
    对每角色查掉幅。high→block、medium→warn 行，交 collect_simple 外发。≥2 集才有结果。"""
    means_path = os.path.join(production_dir(root), "face_ep_means.json")
    try:
        hist = json.load(open(means_path, encoding="utf-8")) if os.path.exists(means_path) else {}
    except Exception:
        hist = {}
    if not isinstance(hist, dict):
        hist = {}
    cur: Dict[str, float] = {}
    for char, rec in (face_result.get("characters") or {}).items():
        m = rec.get("ep_mean_score") if isinstance(rec, dict) else None
        if isinstance(m, (int, float)):
            cur[char] = round(float(m), 4)
    if cur:
        hist[ep] = cur
        try:
            os.makedirs(production_dir(root), exist_ok=True)
            with open(means_path, "w", encoding="utf-8") as fh:
                json.dump(hist, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass
    eps_sorted = sorted(hist.keys(), key=_episode_num)
    chars: set = set()
    for e in eps_sorted:
        chars |= set((hist.get(e) or {}).keys())
    rows: List[dict] = []
    for char in sorted(chars):
        series = [(e, (hist.get(e) or {}).get(char)) for e in eps_sorted]
        for d in fc.cross_episode_drift(series):
            rows.append({
                "verdict": "block" if d.get("severity") == "high" else "warn",
                "shot": f"{char} {d['episode_from']}→{d['episode_to']}",
                "msg": (f"{char} 跨集脸漂：{d['episode_from']}(均值{d['from_mean']})→"
                        f"{d['episode_to']}(均值{d['to_mean']})，相对基线掉幅 {d['drop']}"
                        + ("，且本集均值低于绝对下限——已系统性偏离定妆锚" if d.get("below_abs_low") else "")),
                "char": char,
            })
    return rows


# ── 跨集场景漂移（SCNX·#5·2026-06-27）──────────────────────────────────────────
# 场景是唯一无跨集机检的视觉轴（脸有 G5，场景只有集内 dHash）。这里镜像 G5：累计每集每场景的
# 平均色调指纹（scene_ep_means.json），当前集 vs 历史基线比 L1 → 揪"每集内部一致、却跨集慢慢变样"
# 的场景漂。三条互补指纹（各抓不同失效模式·见 cross_episode_scene_rows）：①色调直方图(torch-free·Pillow)
# 抓色温/调色漂；②结构 dHash 原型抓布局/朝向漂；③DINOv2 语义嵌入(scene_embed·可选后端)抓材质/几何/
# 语义漂(色调/结构盲区)。①②常开，③有嵌入后端时叠加、无则优雅退回①②。
SCENE_DRIFT_WARN = 0.45    # 跨集场景色调 L1 漂移告警阈（归一直方图）
SCENE_DRIFT_BLOCK = 0.80   # 核心场景跨集硬漂阈
# 跨集场景**结构**漂移（dHash 原型汉明·补色调直方图看不出的布局/朝向变化）。64 位里差这么多算结构变样；
# 跨集天然比集内噪（不同镜/构图/时段），故阈比集内 floor(12) 宽。
SCENE_STRUCT_DRIFT_WARN = 18
SCENE_STRUCT_DRIFT_BLOCK = 26


def scene_hist_l1(a: Sequence[float], b: Sequence[float]) -> float:
    """两个等长归一直方图的 L1 距离（0=同，越大越漂）。纯函数·可测。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    return round(sum(abs(float(x) - float(y)) for x, y in zip(a, b)), 4)


def scene_drift_rows(means_by_ep: Dict[str, Dict[str, Sequence[float]]], cur_ep: str,
                     core_scenes: Iterable[str] = (),
                     warn: float = SCENE_DRIFT_WARN, block: float = SCENE_DRIFT_BLOCK) -> List[dict]:
    """跨集场景漂移判定（纯函数·可测）。

    means_by_ep：{集: {场景: 平均色调指纹}}；cur_ep：当前集。当前集每个场景的指纹 vs 该场景**历史各集
    指纹的逐维基线均值** 比 L1：≥warn 出行；核心场景且 ≥block → block，否则 warn。历史无该场景/当前集
    无该场景 → 跳过（≥2 集出现才比）。core_scenes 子串匹配（定妆名 vs asset name 可能略不同）。"""
    core = list(core_scenes or ())
    cur = means_by_ep.get(cur_ep) or {}
    eps_prior = [e for e in means_by_ep if _episode_num(e) < _episode_num(cur_ep)]
    rows: List[dict] = []
    for scene, cur_fp in sorted(cur.items()):
        prior = [means_by_ep[e][scene] for e in eps_prior
                 if isinstance(means_by_ep.get(e), dict) and scene in means_by_ep[e]]
        if not prior or not cur_fp:
            continue
        dim = len(cur_fp)
        base = [sum(float(p[i]) for p in prior) / len(prior) for i in range(dim)]
        d = scene_hist_l1(cur_fp, base)
        if d < warn:
            continue
        is_core = any(scene in c or c in scene for c in core if c)
        verdict = "block" if (is_core and d >= block) else "warn"
        rows.append({
            "verdict": verdict,
            "shot": f"场景[{scene}] 跨{len(prior) + 1}集",
            "msg": (f"场景[{scene}] 跨集色调/光位漂移 L1={d}（vs 前 {len(prior)} 集基线，阈 warn={warn}"
                    f"{'·core block=' + str(block) if is_core else ''}）"
                    + ("——核心场景跨集硬漂，回 n2d-image 对齐定妆/光位锚；若为有意昼夜/季节变化按 allowed_variations 签收。"
                       if verdict == "block"
                       else "——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。")),
            "scene": scene,
        })
    return rows


def scene_struct_drift_rows(protos_by_ep: Dict[str, Dict[str, Sequence[int]]], cur_ep: str,
                            core_scenes: Iterable[str] = (),
                            warn: int = SCENE_STRUCT_DRIFT_WARN, block: int = SCENE_STRUCT_DRIFT_BLOCK) -> List[dict]:
    """跨集场景**结构**漂移（纯函数·可测）。当前集每场景结构原型 dHash vs 历史各集原型的共识原型比汉明：
    ≥warn 出行；核心场景且 ≥block → block，否则 warn。≥2 集出现该场景才比。"""
    core = list(core_scenes or ())
    cur = protos_by_ep.get(cur_ep) or {}
    eps_prior = [e for e in protos_by_ep if _episode_num(e) < _episode_num(cur_ep)]
    rows: List[dict] = []
    for scene, cur_proto in sorted(cur.items()):
        priors = [protos_by_ep[e][scene] for e in eps_prior
                  if isinstance(protos_by_ep.get(e), dict) and protos_by_ep[e].get(scene)]
        if not priors or not cur_proto:
            continue
        base = sc.majority_bits(priors)  # 历史共识结构原型
        d = sc.hamming(list(cur_proto), base)
        if d < warn:
            continue
        is_core = any(scene in c or c in scene for c in core if c)
        verdict = "block" if (is_core and d >= block) else "warn"
        rows.append({
            "verdict": verdict,
            "shot": f"场景[{scene}] 跨{len(priors) + 1}集结构",
            "msg": (f"场景[{scene}] 跨集结构漂移 dHash 汉明={d}（vs 前 {len(priors)} 集结构原型，阈 warn={warn}"
                    f"{'·core block=' + str(block) if is_core else ''}）"
                    + ("——核心场景跨集结构硬漂：色调没动但布局/家具/构图朝向变了（同房间被重新布置/拍反向），"
                       "回 n2d-image 对齐场景定妆 spatial_layout/floor_plan；若为有意改建/换机位按 allowed_variations 签收。"
                       if verdict == "block"
                       else "——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。")),
            "scene": scene,
        })
    return rows


def _accumulate_scene_history(path: str, ep: str, cur: dict) -> dict:
    """读 path 的 {集:{场景:指纹}} 历史账本，写入当前集（若非空）并落盘，返回累计后的账本。"""
    try:
        hist = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    except Exception:
        hist = {}
    if not isinstance(hist, dict):
        hist = {}
    if cur:
        hist[ep] = cur
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(hist, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return hist


def _load_asset_registry(root: str) -> dict:
    path = os.path.join(root, "出图", "共享", "asset_registry.json")
    try:
        data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _variation_expiry_ok(value: object) -> bool:
    if value in (None, ""):
        return False
    text = str(value).strip()
    try:
        # Accept date-only strings and ISO timestamps with Z/offset.
        norm = text.replace("Z", "+00:00")
        if "T" not in norm:
            expires = dt.datetime.fromisoformat(norm).replace(tzinfo=dt.timezone.utc)
        else:
            expires = dt.datetime.fromisoformat(norm)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=dt.timezone.utc)
        return expires >= dt.datetime.now(dt.timezone.utc)
    except Exception:
        return False


def _episode_in_scope(ep: str, scope: object) -> bool:
    if scope in (None, "", [], {}):
        return True
    ep_text = str(ep)
    ep_num = _episode_num(ep)
    values = scope if isinstance(scope, list) else [scope]
    for item in values:
        text = str(item).strip()
        if not text:
            continue
        if text in {ep_text, ep_text.replace("第", "").replace("集", "")}:
            return True
        if text.isdigit() and ep_num == int(text):
            return True
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", text)
        if m and int(m.group(1)) <= ep_num <= int(m.group(2)):
            return True
    return False


def _scene_allowed_variations(root: str, ep: str) -> Dict[str, dict]:
    registry = _load_asset_registry(root)
    out: Dict[str, dict] = {}
    assets = registry.get("assets") if isinstance(registry, dict) else []
    if not isinstance(assets, list):
        return out
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        raw = asset.get("allowed_variations") or asset.get("variation_policy")
        if not raw:
            continue
        variations = raw if isinstance(raw, list) else [raw]
        for item in variations:
            if not isinstance(item, dict):
                continue
            if item.get("accepted") is not True and str(item.get("status") or "").lower() not in {"accepted", "ok", "pass"}:
                continue
            if not str(item.get("reviewer") or "").strip() or not str(item.get("reason") or "").strip():
                continue
            if not _variation_expiry_ok(item.get("expires_at") or item.get("expires")):
                continue
            if not _episode_in_scope(ep, item.get("episodes") or item.get("episode_scope")):
                continue
            dim = str(item.get("dimension") or item.get("dim") or "")
            if dim and "SCNX" not in dim and "跨集场景漂移" not in dim:
                continue
            scene_names = {str(asset.get("name") or "").strip(), str(asset.get("id") or "").strip()}
            scene_names.add(str(item.get("scene") or "").strip())
            for scene in [s for s in scene_names if s]:
                out[scene] = item
    return out


def _apply_scene_allowed_variations(rows: Sequence[dict], variations: Dict[str, dict]) -> List[dict]:
    if not rows or not variations:
        return list(rows)
    out: List[dict] = []
    for row in rows:
        scene = str(row.get("scene") or "").strip()
        match = variations.get(scene)
        if not match:
            for known, item in variations.items():
                if known and (known in scene or scene in known):
                    match = item
                    break
        if match and row.get("verdict") == "block":
            row = dict(row)
            row["verdict"] = "warn"
            row["signed_off"] = True
            row["signoff_source"] = "asset_registry.allowed_variations"
            row["signoff_reason"] = match.get("reason")
            row["msg"] = "[allowed_variations 已签收] " + str(row.get("msg") or row.get("message") or "")
        out.append(row)
    return out


def cross_episode_scene_rows(root: str, ep: str) -> List[dict]:
    """SCNX 跨集场景漂移：累计每集每场景的(色调指纹 + 结构原型 dHash)，当前集 vs 历史基线比对。
    核心场景(asset_registry 显式标 core)硬漂→block，其余→warn。镜像 G5 脸漂的自累积侧车账本。
    色调直方图治色温/调色跨集漂；结构 dHash 原型补「色调没动但布局/朝向变了」（两者互补，同段 SCNX 输出）。"""
    try:
        core = core_scene_names(root)
    except Exception:
        core = []
    allowed_variations = _scene_allowed_variations(root, ep)
    # ① 色调指纹（既有）
    hist = _accumulate_scene_history(
        os.path.join(production_dir(root), "scene_ep_means.json"), ep, sc.scene_tone_means(root, ep))
    color_rows = scene_drift_rows(hist, ep, core_scenes=core)
    # ② 结构原型（新增）：补色调看不出的布局/构图朝向漂移
    sproto = _accumulate_scene_history(
        os.path.join(production_dir(root), "scene_struct_ep_means.json"), ep, sc.scene_struct_prototypes(root, ep))
    struct_rows = scene_struct_drift_rows(sproto, ep, core_scenes=core)
    # ③ 语义嵌入（DINOv2·最强指纹）：连材质/几何/布局都能测，色调/结构盲区的兜底。
    #    仅当可选嵌入后端已回填逐镜 embedding 时才有数据，否则空（退回①②，不硬失败）。
    embed_rows: List[dict] = []
    try:
        import scene_embed as se
        cur_embed = se.scene_embed_means(root, ep)
        if cur_embed:
            ehist = _accumulate_scene_history(
                os.path.join(production_dir(root), "scene_embed_ep_means.json"), ep, cur_embed)
            embed_rows = se.scene_embed_drift_rows(ehist, ep, core_scenes=core)
    except Exception:
        embed_rows = []
    return _apply_scene_allowed_variations(color_rows + struct_rows + embed_rows, allowed_variations)


def _clip_num(value: Any) -> int | None:
    """从 png 名 / clip_id 解析 Clip 号（Clip_05 / 镜5 / shot5 / 裸数字回退）。"""
    s = str(value or "")
    m = re.search(r"(?:Clip|片段|镜头?|shot)\s*[_\- ]?\s*0*([0-9]+)", s, re.I)
    if not m:
        m = re.search(r"0*([0-9]+)", s)
    return int(m.group(1)) if m else None


def expression_confirmed_clips(expr_result: dict,
                               mouth_threshold: float = expv.DEFAULT_MOUTH_THRESHOLD,
                               eye_threshold: float = expv.DEFAULT_EYE_THRESHOLD) -> set:
    """EXP1 像素已确认「表情确实大幅形变」的 Clip 号集合（用于 G1↔EXP1 调和）。

    只认 verdict==ok 且 mouth/eye 形变越过阈值的镜——这些近景的脸-身份余弦掉到 floor 下，
    极可能是表情形变（哭/吼/瞪）所致而非崩脸（"Motion by Queries"：身份与表情共用同组特征）。
    EXP1 的 warn=声称大却没动，恰恰相反（脸该动没动），绝不放行。纯函数·可测。"""
    out: set = set()
    for f in (expr_result.get("findings") or []):
        if not isinstance(f, dict) or f.get("verdict") != "ok":
            continue
        mc, ec = f.get("mouth_change"), f.get("eye_change")
        if mc is None and ec is None:
            continue  # 跳过/无脸的占位 finding，非确认形变
        moved = (isinstance(mc, (int, float)) and mc >= mouth_threshold) or \
                (isinstance(ec, (int, float)) and ec >= eye_threshold)
        if moved:
            num = _clip_num(f.get("shot"))
            if num is not None:
                out.add(num)
    return out


def reconcile_face_with_expression(face_result: dict, confirmed_clips: set) -> int:
    """G1 脸 block ∩ EXP1 像素确认大表情形变 → 降 warn（surface·不硬阻断）。

    根治掣肘：G1 floor 基于中性定妆自标定、无表情豁免；EXP1 又要求大情绪近景首尾帧表情大幅变化。
    两者共用同一镜时结构性互掐——清 G1 硬 block 最省力的路是把脸做平（只换一个软 EXP1 warn）。
    这里让「像素已证明表情真的大幅动了」的镜把 G1 block 降 warn，不再奖励面瘫。原地改 shots，返回降级数。
    无 EXP1 能力（insightface 缺）→ confirmed_clips 空 → 不动（保守=现状）。"""
    if not confirmed_clips:
        return 0
    n = 0
    for s in face_result.get("shots", []) or []:
        if not isinstance(s, dict) or s.get("verdict") != "block":
            continue
        num = _clip_num(s.get("png") or s.get("shot"))
        if num is not None and num in confirmed_clips:
            s["abs_verdict"] = "block"
            s["verdict"] = "warn"
            s["expression_span_expected"] = True
            n += 1
    return n


# ── EXP3 表情过锁 / copy-paste 冻脸（report-only·IPRO/PixelSmile 减害）──────────────
# 与上面的 G1↔EXP1 调和互补、方向相反：那个被动防「把脸做平骗过 G1」（已 block 才降级）；
# 这个**主动**检出「脸该随情绪动却纹丝不动」的系统性过锁——高 face-cosine 恰恰可能是 copy-paste
# 冻脸的假高分（IPRO 2510.14255 实证：身份分越高、表演越差；WithAnyone/PixelSmile 同结论）。
# 永不 block（不进 STRICT_ADVISORY_DIMENSIONS），全 WARN/INFO：过锁是创作权衡提示，不是穿帮。
OVERLOCK_MIN_FLAT = int(os.environ.get("N2D_OVERLOCK_MIN_FLAT", "2") or "2")
OVERLOCK_COS_MEAN = float(os.environ.get("N2D_OVERLOCK_COS_MEAN", "0.97") or "0.97")
OVERLOCK_COS_SPREAD = float(os.environ.get("N2D_OVERLOCK_COS_SPREAD", "0.012") or "0.012")
OVERLOCK_MIN_CLOSEUPS = int(os.environ.get("N2D_OVERLOCK_MIN_CLOSEUPS", "3") or "3")


def char_closeup_emotions(root: str, ep: str) -> Dict[str, Dict[str, Any]]:
    """每角色在近景镜里脚本命中的情绪桶集合 + 近景镜数（驱动 EXP3 过锁判断）。复用 ec/pc 读取层。"""
    out: Dict[str, Dict[str, Any]] = {}
    try:
        it = ec._clip_iter(root, ep)
    except Exception:
        return out
    for _clip, _label, text in it:
        if not any(m.lower() in text.lower() for m in ec.CLOSEUP_MARKERS):
            continue
        emos = ec._emotions_in(text)
        for cid in pc._char_ids(text):
            rec = out.setdefault(cid, {"emotions": set(), "closeups": 0})
            rec["closeups"] += 1
            rec["emotions"] |= emos
    return out


def expression_overlock_findings(expr_result: dict, face_result: dict,
                                 char_emotions: Dict[str, Dict[str, Any]],
                                 *, min_flat: int = OVERLOCK_MIN_FLAT,
                                 cos_mean: float = OVERLOCK_COS_MEAN,
                                 cos_spread: float = OVERLOCK_COS_SPREAD,
                                 min_closeups: int = OVERLOCK_MIN_CLOSEUPS) -> List[dict]:
    """EXP3：表情过锁 / copy-paste 冻脸（report-only）。纯函数·可测。复用已算的 expr(形变)+face(余弦)。

    A 像素·系统性：≥min_flat 个「声称大表情但首尾帧零形变」镜（EXP1 verdict==warn 且有实测 Δ）→ WARN。
      与 EXP1 逐镜 warn 互补——这是聚合诊断：系统性过锁 ≠ 单镜偶发，给 IPRO 整体重制建议而非单镜重抽。
    B 统计·copy-paste 指纹：宽情绪角色（≥2 情绪桶·≥min_closeups 近景）脸跨镜最佳锚余弦均值≥cos_mean
      且 散度<cos_spread（近乎恒定）→ INFO（高身份×零表情=IPRO 过锁区）。
    C 文本兜底：无像素也无脸数据时，宽情绪角色（≥3 桶·≥min_closeups 近景）→ INFO 过锁风险提醒。"""
    rows: List[dict] = []
    # Signal A —— 系统性像素零形变
    flat: List[str] = []
    for f in (expr_result.get("findings") or []):
        if not isinstance(f, dict) or f.get("verdict") != "warn":
            continue
        if f.get("mouth_change") is None and f.get("eye_change") is None:
            continue  # skip/无脸占位 finding，非实测形变
        sh = str(f.get("shot") or "")
        if sh:
            flat.append(sh)
    if len(flat) >= min_flat:
        shown = "、".join(flat[:6]) + ("…" if len(flat) > 6 else "")
        rows.append(pc._row(
            "warn",
            f"本集 {len(flat)} 个大情绪近景像素零形变（{shown}）·系统性疑似过锁/copy-paste 冻脸——按 "
            "IPRO/PixelSmile：高 face-cosine 假高分是身份锁过紧的征兆，别只重抽单镜；解耦表情（加 AU/FACS "
            "表情控件 / expressions 表情参考）或下调身份参考权重，再整体重出情绪镜。",
            stage="image", artifacts=["出图/共享/图片", "identity_registry.json"]))
    # Signal B —— 跨镜余弦近乎恒定的 copy-paste 指纹
    face_avail = bool(face_result.get("available")) and bool(face_result.get("shots"))
    if face_avail:
        scores_by_char: Dict[str, List[float]] = {}
        for s in face_result.get("shots", []) or []:
            if not isinstance(s, dict):
                continue
            c = str(s.get("char") or "")
            sc = s.get("score")
            if c and isinstance(sc, (int, float)):
                scores_by_char.setdefault(c, []).append(float(sc))
        for c, info in (char_emotions or {}).items():
            if len(info.get("emotions") or ()) < 2 or int(info.get("closeups") or 0) < min_closeups:
                continue
            scs = scores_by_char.get(c) or []
            if len(scs) < min_closeups:
                continue
            mean = sum(scs) / len(scs)
            spread = max(scs) - min(scs)
            if mean >= cos_mean and spread < cos_spread:
                rows.append(pc._row(
                    "info",
                    f"角色 {c} 跨 {len(scs)} 个情绪近景脸-身份余弦近乎恒定（均值 {mean:.3f}·散度 {spread:.3f}），"
                    f"但脚本跨 {len(info['emotions'])} 种情绪——疑似高身份×零表情的 copy-paste 冻脸（IPRO）。"
                    "确认表情真在动；必要时解耦表情控件或下调身份权重。",
                    stage="image", artifacts=["出图/共享/图片"]))
    # Signal C —— 文本兜底（无像素也无脸数据）
    elif not expr_result.get("available"):
        for c, info in (char_emotions or {}).items():
            if len(info.get("emotions") or ()) >= 3 and int(info.get("closeups") or 0) >= min_closeups:
                rows.append(pc._row(
                    "info",
                    f"角色 {c} 脚本跨 {len(info['emotions'])} 种情绪共 {info['closeups']} 个近景、身份锁强——IPRO "
                    "过锁风险区：确认表情真随情绪变化（别让脸纹丝不动），必要时加 AU/FACS 表情控件。"
                    "（缺像素/脸数据，跑表情判官或 insightface 可实判）",
                    stage="image", artifacts=["identity_registry.json"]))
    return rows


def noface_violation_rows(ep: str, face_result: dict) -> List[dict]:
    """G1b 无脸崩坏：该镜应有具名角色却检测不到脸（脸糊/被遮挡/崩脸）。

    过去 noface 镜被显式过滤丢弃——最严重的崩脸结果反而 severity=0 消失。这里把"应在场具名
    角色 + noface"的镜捞回成 warn（风格化脸 + 检测器误检可能，故不直接 block），不再静默放过。"""
    rows: List[dict] = []
    for s in face_result.get("shots", []) or []:
        if not isinstance(s, dict) or s.get("verdict") != "noface":
            continue
        chars = [c for c in (s.get("chars") or []) if c]
        if not chars:
            continue  # 合法无脸镜（空镜/纯背身），不报
        rows.append({
            "verdict": "warn",
            "png": s.get("png"),
            "msg": f"{'/'.join(chars)} 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景",
        })
    return rows


def probe_capabilities() -> Dict[str, Any]:
    """本机机检能力探针——把"哪些检查运行在降级精度"亮在台面上，避免"机检全绿"错觉。"""
    import importlib.util as _ilu

    caps: Dict[str, Any] = {
        "insightface": _ilu.find_spec("insightface") is not None,
        "pillow": _ilu.find_spec("PIL") is not None,
        # 进阶数值化指标的依赖（业界 SOTA：序列级主体/世界一致 + 词级口型）。缺则相应数值未跑，
        # 现有检退到 dHash/色相直方图/人脸余弦/SyncNet——把这层"未跑"亮在台面，避免"机检全绿"错觉。
        "torch": _ilu.find_spec("torch") is not None,
        "syncnet": os.path.isdir(os.path.expanduser("~/syncnet_python")),
    }
    notes: List[str] = []
    if not caps["pillow"]:
        notes.append("本机无 Pillow——全部像素级一致性机检（脸/发型/服装/接缝/风格/时序）不可用，交人判。")
    elif not caps["insightface"]:
        notes.append("本机无 insightface——脸部/片内身份机检运行在 Pillow 降级精度，"
                     "机检通过≠脸部一致已验证；正式定稿前在装好 insightface 的环境复跑。")
    # 进阶数值化指标缺位提示（不降级精度等级、不阻断；只让 SOTA 盲区可见、可追）。
    advanced: List[str] = []
    if not caps["torch"]:
        advanced.append("DINOv2 跨帧主体一致 / CoTracker 背景塌陷（需 torch）——当前主体一致退到"
                        "色相直方图+dHash+人脸余弦，未做序列级数值化")
    if not caps["syncnet"]:
        advanced.append("口型词级数值（SyncNet/LatentSync LSE-C·LMD·TREPA）——未装 ~/syncnet_python，口型仅启发式")
    if advanced:
        caps["advanced_metrics_missing"] = advanced
        notes.append("进阶数值化一致性指标未运行：" + "；".join(advanced)
                     + "。装好对应依赖可把这些维度从启发式升级为数值化（不影响现有 degraded 精度判定）。")
    caps["degraded"] = not caps["pillow"] or not caps["insightface"]
    caps["notes"] = notes
    return caps


def run(root: str, ep: str) -> dict:
    sections: Dict[str, dict] = {}
    export_rows: List[dict] = []  # 结构化外发：逐条带 维度/严重度/镜头定位/return_to_stage

    def collect_simple(dim: str, rows: Sequence[dict], *, stage: str, default_artifacts: Sequence[str]) -> None:
        """简单段（只存 verdicts 的维度）的检出行 → 与 details 同构的外发条目。"""
        details = normalize_details(
            [r for r in rows if isinstance(r, dict)],
            dim=dim, ep=ep, stage=stage, default_artifacts=default_artifacts,
        )
        export_rows.extend(active_findings(details))

    # P0 语义谱系 Diff（raw/voiceover → storyboard → image/video prompt）
    sem = semc.analyze(root, ep)
    sections["语义谱系(P0)"] = section_from_result(
        dim="语义谱系(P0)",
        result=sem,
        detail_key="findings",
        skipped=not sem.get("available", False),
        ep=ep,
        stage="script_stage2",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt", f"出视频/{ep}/prompt"),
    )

    # P1 n2d 动态百科 / 状态哨兵
    stt = statec.analyze(root, ep)
    sections["状态百科(P1)"] = section_from_result(
        dim="状态百科(P1)",
        result=stt,
        detail_key="alerts",
        skipped=not stt.get("available", False) or not stt.get("states", []),
        ep=ep,
        stage="image",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json"),
    )

    # P2 多模态视觉语义/道具漂移（本地 embedding，缺库优雅跳过）
    mm = mmc.analyze(root, ep)
    sections["多模态(P2)"] = section_from_result(
        dim="多模态(P2)",
        result=mm,
        detail_key="shots",
        skipped=not mm.get("available", False) or not mm.get("groups", {}),
        ep=ep,
        stage="image",
        default_artifacts=(f"出图/{ep}/prompt/01_分镜出图.md", f"出图/{ep}/图片"),
    )

    # SP1V 状态像素验证（VLM-based：角色状态变化是否真的呈现在像素中）
    state_pix = spv.analyze(root, ep)
    sections["状态像素验证(SP1V)"] = {"skipped": not state_pix.get("available", False),
                                    "verdicts": _verdicts(state_pix.get("findings", [])), "notes": state_pix.get("notes", [])}
    collect_simple("状态像素验证(SP1V)", state_pix.get("findings", []), stage="image", default_artifacts=(f"出图/{ep}/图片", "生产数据/state_ledger_{ep}.json"))

    # 出图 → 出视频 视觉契约继承 Diff（光位锚/轴线漂移是视频前硬风险）
    contract_dim = "契约继承"
    contract_spec = consistency_dim_spec("contract_inheritance") or {}
    contract = contract_inheritance_result(root, ep)
    sections[contract_dim] = section_from_result(
        dim=contract_dim,
        result=contract,
        detail_key="fields",
        skipped=not contract.get("available", False),
        ep=ep,
        stage=str(contract_spec.get("return_to_stage") or "video_prompt"),
        default_artifacts=(f"出图/{ep}/prompt/00_总览.md", f"出视频/{ep}/prompt/00_总览.md"),
    )

    # N3 锚点门（全篇定妆，不分集）
    a = fc.audit_anchors(root)
    sections["锚点门(N3)"] = {"skipped": not a.get("available", False),
                             "verdicts": _verdicts(a.get("anchors", [])), "notes": a.get("notes", [])}
    collect_simple("锚点门(N3)", a.get("anchors", []), stage="image", default_artifacts=("出图/共享/图片",))

    # G1 脸（insightface 缺席时自动降级 Pillow 基础机检：mode=pillow_fallback，供 n2d-score 降权消费）
    f = fc.analyze(root, ep)
    # EXP1 先算（G1 section 之前）：用「像素已确认大表情形变」的镜调和 G1——把因表情(非崩脸)掉到
    # floor 下的近景 block 降 warn，破除「闸门结构性奖励面瘫」。无 insightface→空集→不动（保守）。
    expr = expv.analyze(root, ep)
    _exp_downgraded = reconcile_face_with_expression(f, expression_confirmed_clips(expr)) if f.get("available", False) else 0
    # noface 由 G1b 单列；unverifiable=远景人小身份不可辨，既非崩脸也非"已验证 ok"——排除出 G1，
    # 否则会被当成通过镜拉高一致性通过率（"稳定地错"反被记成过）。统计另列 unverifiable_shots。
    _g1_excluded = {"noface", "unverifiable"}
    sections["脸(G1)"] = {"skipped": not f.get("available", False),
                         "verdicts": [s.get("verdict") for s in f.get("shots", []) if s.get("verdict") not in _g1_excluded],
                         "unverifiable_shots": sum(1 for s in f.get("shots", []) if s.get("verdict") == "unverifiable"),
                         "mode": f.get("mode"),
                         "precision": f.get("precision"),
                         # G4 KPI 直读：每角色本集质心接近度 + 用了哪个 encoder + fidelity-gate 状态
                         # （避免 score 侧重跑脸推理；ep_mean_score 已过 G3 fidelity-gate）
                         "encoder": f.get("encoder"),
                         "fidelity_gate": f.get("fidelity_gate"),
                         "characters": f.get("characters", {}),
                         "notes": f.get("notes", [])}
    collect_simple("脸(G1)", [s for s in f.get("shots", []) if s.get("verdict") not in _g1_excluded],
                   stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # G1b 无脸崩坏：应在场具名角色却 noface（过去被静默丢弃）→ 捞回成 warn
    g1b_rows = noface_violation_rows(ep, f) if f.get("available", False) else []
    sections["无脸崩坏(G1b)"] = {"skipped": not g1b_rows,
                              "verdicts": [r["verdict"] for r in g1b_rows], "notes": []}
    collect_simple("无脸崩坏(G1b)", g1b_rows, stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # G5 跨集脸漂：每集各自过 floor 但角色逐集系统性偏离锚点（单集机检看不到）。≥2 集才有结果。
    g5_rows = cross_episode_face_rows(root, ep, f) if f.get("available", False) else []
    sections["跨集脸漂(G5)"] = {"skipped": not g5_rows,
                            "verdicts": [r["verdict"] for r in g5_rows], "notes": []}
    collect_simple("跨集脸漂(G5)", g5_rows, stage="image", default_artifacts=("出图/共享/图片",))

    # EXP1 表情像素验证（expression_span=大 近景→首尾帧 landmark 对比）——结果已在 G1 前算并用于调和
    notes_exp = list(expr.get("notes", []))
    if _exp_downgraded:
        notes_exp.append(f"已据 EXP1 像素确认的大表情形变，将 {_exp_downgraded} 处 G1 脸 block 降为 warn（避免奖励面瘫）。")
    sections["表情连续(EXP1)"] = {"skipped": not expr.get("available", False),
                                "verdicts": _verdicts(expr.get("findings", [])), "notes": notes_exp}
    collect_simple("表情连续(EXP1)", expr.get("findings", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # EXP3 表情过锁 / copy-paste 冻脸（report-only·IPRO 减害）——复用上面已算的 f(脸余弦)+expr(形变)，零新增推理
    overlock_rows = expression_overlock_findings(expr, f, char_closeup_emotions(root, ep))
    sections["表情过锁(EXP3)"] = {"skipped": not overlock_rows,
                              "verdicts": _verdicts(overlock_rows), "notes": []}
    collect_simple("表情过锁(EXP3)", overlock_rows, stage="image", default_artifacts=("出图/共享/图片",))

    # N1 服装/配色
    o = oc.analyze(root, ep)
    sections["服装配色(N1)"] = {"skipped": not o.get("available", False),
                              "verdicts": _verdicts(o.get("shots", [])), "notes": o.get("notes", [])}
    collect_simple("服装配色(N1)", o.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))
    # COST 服装独立维度（CLIP-I embedding，与 N1 配色互补）
    costume = cstc.analyze(root, ep)
    sections["服装独立(COST)"] = {"skipped": not costume.get("available", False),
                                "verdicts": _verdicts(costume.get("shots", [])), "notes": costume.get("notes", [])}
    collect_simple("服装独立(COST)", costume.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # H1 发型/发色（脸、服装之外的第三类漂移；缺 Pillow 优雅跳过）
    hr = hc.analyze(root, ep)
    sections["发型(H1)"] = {"skipped": not hr.get("available", False),
                          "verdicts": _verdicts(hr.get("shots", [])), "notes": hr.get("notes", [])}
    collect_simple("发型(H1)", hr.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # MK1 辨识标记（疤痕/胎记/纹身/异瞳/痣/义体——载剧情，丢一次既崩脸又崩剧情；文本/结构机检，无 identity_marks 登记则跳过）
    mks = mk.analyze(root, ep)
    sections["辨识标记(MK1)"] = {"skipped": not mks.get("available", False),
                              "verdicts": _verdicts(mks.get("shots", [])), "notes": mks.get("notes", [])}
    collect_simple("辨识标记(MK1)", mks.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # N2 片内时序
    t = tcheck.analyze(root, ep)
    sections["片内时序(N2)"] = {"skipped": not t.get("clips", []) and bool(t.get("notes")),
                              "verdicts": [c.get("verdict") for c in t.get("clips", [])], "notes": t.get("notes", [])}
    collect_simple("片内时序(N2)", t.get("clips", []), stage="video", default_artifacts=(f"出视频/{ep}/视频",))

    # EXP2 状态化表情：storyboard state_delta 改 identity_invariants 又没进 allowed_state_deltas → block；
    # 大表情跨度近景缺 micro_expression → warn。此前只落 ledger 从不进闸（孤儿）；现接入审计→gate。
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    has_sb = os.path.isfile(sb_path)
    exp2 = exstate.run(root, ep)
    sections["状态化表情(EXP2)"] = section_from_result(
        dim="状态化表情(EXP2)", result=exp2, detail_key="findings",
        skipped=not has_sb, ep=ep, stage="script_stage2",
        default_artifacts=(f"脚本/{ep}/storyboard.json", "出图/共享/identity_registry.json"))

    # MG1 运动语法（advisory）：运镜/动作语义连贯——此前只落 ledger 从不进闸（孤儿）。
    mg1 = mgram.run(root, ep)
    sections["运动语法(MG1)"] = section_from_result(
        dim="运动语法(MG1)", result=mg1, detail_key="findings",
        skipped=not has_sb, ep=ep, stage="video",
        default_artifacts=(f"脚本/{ep}/storyboard.json", f"出视频/{ep}/prompt"))

    # ASP 声音空间 + NV1 原生声纹路由证据：native_speech 路由缺声纹证据/ambient_map 缺位 → warn，
    # 证据显式 fail/mismatch → block。与 check_native_voice_identity 互补（路由级交叉核验）。原孤儿。
    routes_path = os.path.join(root, "出视频", ep, "prompt", "video_model_routes.json")
    asp = aspace.run(root, ep)
    sections["声音空间(ASP)"] = section_from_result(
        dim="声音空间(ASP)", result=asp, detail_key="findings",
        skipped=not os.path.isfile(routes_path), ep=ep, stage="video",
        default_artifacts=(routes_path, "设定库/ambient_map.json", f"生产数据/native_voice_identity_{ep}.json"))

    # OST 物件状态：未声明的道具状态互斥翻转（满↔空/完好↔破碎…）——补 prop_alerts 只查已声明转换的洞。
    ost = objstate.analyze(root, ep)
    sections["物件状态(OST)"] = {"skipped": not ost.get("available", False),
                              "verdicts": _verdicts(ost.get("shots", [])), "notes": ost.get("notes", [])}
    collect_simple("物件状态(OST)", ost.get("shots", []), stage="image",
                   default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json"))

    # O2 场景：结构离群/色光离群（scene_consistency）+ floor_plan/门窗几何核对（scene_geometry sidecar·#5）。
    s = sc.analyze(root, ep)
    o2_rows = list(s.get("shots", []))
    geom_path = os.path.join(production_dir(root), f"scene_geometry_{ep}.json")
    geom_notes: List[str] = []
    try:
        if os.path.isfile(geom_path):
            geom = json.load(open(geom_path, encoding="utf-8"))
            for f in (geom.get("findings") or []):
                if isinstance(f, dict) and f.get("verdict") in ("warn", "block"):
                    o2_rows.append({"scene": f.get("scene"), "verdict": f["verdict"],
                                    "msg": f.get("message"), "kind": "几何"})
            geom_notes = list(geom.get("notes") or [])
    except Exception:
        pass
    # 击中光效(apex)：复活 scene_consistency.verify_impact_frames——impact_frame_sync 镜的命中帧须比首帧
    # 亮度涌动 >15%（motivated 闪光/apex 轮廓光），否则"打击感软弱"。此前 res["impact_physics"] 被算出却丢弃
    # （consistency_audit 只读 shots），本轮接入 O2 roll-up，让光绑战斗节拍的检测真正生效（heuristic·warn）。
    for f in (s.get("impact_physics") or []):
        if isinstance(f, dict):
            o2_rows.append({"scene": f.get("clip"), "verdict": f.get("severity", "warn"),
                            "msg": f.get("message"), "kind": "击中光效",
                            "actual_surge": f.get("actual_surge")})
    sections["场景(O2)"] = {"skipped": not s.get("available", False),
                          "verdicts": _verdicts(o2_rows), "notes": s.get("notes", []) + geom_notes}
    collect_simple("场景(O2)", o2_rows, stage="image",
                   default_artifacts=(f"出图/{ep}/图片", "出图/共享/asset_registry.json"))

    # SCNX 跨集场景漂移（#5）：补上场景轴此前完全缺失的跨集机检（脸有 G5，场景没有）。自累积每集每场景
    # 平均色调指纹，当前集 vs 历史基线比 L1；核心场景硬漂=block，其余 warn。需 ≥2 集且 Pillow 可用。
    scnx_rows = cross_episode_scene_rows(root, ep)
    sections["跨集场景漂移(SCNX)"] = {"skipped": not s.get("available", False) or not scnx_rows,
                                  "verdicts": [r["verdict"] for r in scnx_rows], "notes": []}
    collect_simple("跨集场景漂移(SCNX)", scnx_rows, stage="image",
                   default_artifacts=("出图/共享/asset_registry.json", f"出图/{ep}/图片"))

    # 打斗撞点(SPEC-APEX·P1 升闸)：combat_cue_apex_audit 平时 report-only，核心打斗镜(核心场景 LOC 或
    # 高潮/爆点/关键 key 镜)×交付边界(compose/review) 的 combat_apex_untimestamped/combat_cue_apex_no_keyframe
    # 由 gate._strict_advisory_should_block 升 BLOCK——剪辑峰值对不上命中关键帧=打击感软散，交付前挡。
    # in-process 跑(纯 stdlib·同 n2d 线)；fix 回 n2d-script 把 impact_frame 写成带秒命中帧 + anchor_planner 注回。
    combat_rows = _combat_cue_apex_rows(root, ep)
    sections["打斗撞点(SPEC-APEX)"] = {"skipped": not combat_rows,
                                  "verdicts": _verdicts(combat_rows), "notes": []}
    collect_simple("打斗撞点(SPEC-APEX)", combat_rows, stage="script_stage2",
                   default_artifacts=(f"脚本/{ep}/storyboard.json", f"生产数据/combat_cue_apex_{ep}.json"))

    # B1 跨镜空间站位/遮挡（同 LOC 各镜站位声明 vs 注册场景站位；违锁=block，链式=warn；纯文本无依赖）
    sb = sbc.analyze(root, ep)
    sections["空间站位(B1)"] = {"skipped": not sb.get("available", False),
                             "verdicts": _verdicts(sb.get("shots", [])), "notes": sb.get("notes", [])}
    collect_simple("空间站位(B1)", sb.get("shots", []), stage="image",
                   default_artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md"))

    # S1 风格漂移
    st = stc.analyze(root, ep)
    sections["风格(S1)"] = {"skipped": not st.get("available", False) or st.get("floor") is None,
                          "verdicts": _verdicts(st.get("shots", [])), "notes": st.get("notes", [])}
    collect_simple("风格(S1)", st.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # DOF1 景深/虚化（镜头光学：同场景深焦↔浅景深横跳像换相机；shot_scale 只管景别不管景深；缺 Pillow 优雅跳过）
    df = dof.analyze(root, ep)
    sections["景深一致(DOF1)"] = {"skipped": not df.get("available", False),
                               "verdicts": _verdicts(df.get("shots", [])), "notes": df.get("notes", [])}
    collect_simple("景深一致(DOF1)", df.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # DOFL 景深锁：实测景深比 vs 场景注册 dof_profile.depth_intent（per-scene 锁；补 DOF1 只集内自比的缺口）
    dofl_rows = dof.dof_profile_rows(root, ep)
    sections["景深锁(DOFL)"] = {"skipped": not df.get("available", False) or not dofl_rows,
                             "verdicts": [r["verdict"] for r in dofl_rows], "notes": []}
    collect_simple("景深锁(DOFL)", dofl_rows, stage="image",
                   default_artifacts=("出图/共享/asset_registry.json", f"出图/{ep}/图片"))

    # VFXC 特效窜色：剑气/系统面板/妖纹光效跨镜变色（registry color_target 已声明却没人量）
    vx = vfxc.analyze(root, ep)
    sections["特效窜色(VFXC)"] = {"skipped": not vx.get("available", False) or not vx.get("shots"),
                              "verdicts": _verdicts(vx.get("shots", [])), "notes": vx.get("notes", [])}
    collect_simple("特效窜色(VFXC)", vx.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # GRADE1 色温/调色：同场景跨镜暖冷/品绿横跳（光位锚有了、色温调色没成常量的盲区）
    cgr = cgc.analyze(root, ep)
    sections["色温调色(GRADE1)"] = {"skipped": not cgr.get("available", False) or not cgr.get("shots"),
                                "verdicts": _verdicts(cgr.get("shots", [])), "notes": cgr.get("notes", [])}
    collect_simple("色温调色(GRADE1)", cgr.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # LSIG 光照签名数值强制：实测色相/饱和度 vs 场景注册 constraints.lighting_signature（接活死 schema）
    lsig_rows = sc.lighting_signature_rows(root, ep)
    sections["光照签名(LSIG)"] = {"skipped": not s.get("available", False) or not lsig_rows,
                              "verdicts": [r["verdict"] for r in lsig_rows], "notes": []}
    collect_simple("光照签名(LSIG)", lsig_rows, stage="image",
                   default_artifacts=("出图/共享/asset_registry.json", f"出图/{ep}/图片"))

    # 接缝 接力(尾帧 vs 下一首帧)——PNG 层，把"逐接缝人判"降成机检初筛
    sm = tcheck.seam_analyze(root, ep)
    sections["接缝接力"] = {"skipped": bool(sm.get("notes")) and not sm.get("seams"),
                         "verdicts": _verdicts(sm.get("seams", [])), "notes": sm.get("notes", [])}
    collect_simple("接缝接力", sm.get("seams", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))
    # Write seam conditioning hints for next-episode prompt generation
    if seam_cond is not None and sm.get("seams"):
        try:
            hints = seam_cond.build_hints(sm["seams"], ep)
            seam_cond.write_hints(root, ep, hints)
        except Exception:
            pass  # advisory only; never block the audit

    # 称谓/口头禅(A1)——剧本层人设漂移（称呼/自称/口头禅忽 A 忽 B；缺词典优雅跳过）
    ad = addr.analyze(root, ep)
    sections["称谓口头禅(A1)"] = {"skipped": not ad.get("available", False),
                              "verdicts": _verdicts(ad.get("findings", [])), "notes": ad.get("notes", [])}
    collect_simple("称谓口头禅(A1)", ad.get("findings", []), stage="script_stage1",
                   default_artifacts=(f"脚本/{ep}/voiceover.txt", "设定库/称谓表.json"))

    # 字幕对齐(L1)——双语短语边界/阅读速度/译文完整性（补 mechanical_check 的"条数对账"盲区）
    sub = sa.analyze(root, ep)
    sections["字幕对齐(L1)"] = {"skipped": not sub.get("available", False),
                             "verdicts": _verdicts(sub.get("rows", [])), "notes": sub.get("notes", [])}
    collect_simple("字幕对齐(L1)", sub.get("rows", []), stage="script_stage2",
                   default_artifacts=(f"脚本/{ep}/字幕_中文.srt", f"脚本/{ep}/字幕_英文.srt"))

    # N4 糊/低质
    q = qc.analyze(root, ep)
    sections["糊/低质(N4)"] = {"skipped": not q.get("available", False),
                             "verdicts": _verdicts(q.get("shots", [])), "notes": q.get("notes", [])}
    collect_simple("糊/低质(N4)", q.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # N5 手部/解剖畸形（六指/粘连——AI 生图头号翻车点，face/outfit/hair/糊 都不看手；缺 cv2 优雅跳过）
    ha = hand.analyze(root, ep)
    sections["手部/解剖(N5)"] = {"skipped": not ha.get("available", False),
                              "verdicts": _verdicts(ha.get("shots", [])), "notes": ha.get("notes", [])}
    collect_simple("手部/解剖(N5)", ha.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # R1 角色身高/体型比例（双人同框相对身高漂——shot_scale 只管景别不管角色间高矮；缺 insightface 优雅跳过）
    sca = scc.analyze(root, ep)
    sections["身高比例(R1)"] = {"skipped": not sca.get("available", False),
                             "verdicts": _verdicts(sca.get("shots", [])), "notes": sca.get("notes", [])}
    collect_simple("身高比例(R1)", sca.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # X1 轴线/视线像素核验（场景轴线视线此前只查 prompt 写没写；这里从脸朝向/屏幕位像素验越轴。warn-only）
    ax = axis_geometry.analyze(root, ep)
    sections["轴线视线(X1)"] = {"skipped": not ax.get("available", False),
                             "verdicts": _verdicts(ax.get("shots", [])), "notes": ax.get("notes", [])}
    collect_simple("轴线视线(X1)", ax.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # W1 天气/时辰推进连续性（同场景相邻镜时辰硬跳 day↔night + scene_dna 光色天气违锁；缺 Pillow 优雅跳过）
    #    + W2 光位方向连续性（同场景相邻镜主光左右硬翻转 advisory·随 W1 同段产出 metric=light_dir）
    wco = wcont.analyze(root, ep)
    try:
        wcont.write_scene_world_ledger(root, ep, wco)
    except Exception as exc:
        wco.setdefault("notes", []).append(f"scene_world_ledger 写入失败：{type(exc).__name__}: {str(exc)[:120]}")
    sections["天气时辰(W1)"] = {"skipped": not wco.get("available", False),
                             "verdicts": _verdicts(wco.get("shots", [])), "notes": wco.get("notes", [])}
    collect_simple("天气时辰(W1)", wco.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # L2 字幕安全区构图一致（脸落进底部字幕带会被烧字幕遮挡——advisory，缺 insightface 优雅跳过）
    ssec = ssa.analyze(root, ep)
    sections["字幕安全区(L2)"] = {"skipped": not ssec.get("available", False),
                              "verdicts": _verdicts(ssec.get("shots", [])), "notes": ssec.get("notes", [])}
    collect_simple("字幕安全区(L2)", ssec.get("shots", []), stage="image", default_artifacts=(f"出图/{ep}/图片",))

    # AV1 音画同步（口型↔配音偏移）——advisory（block 已在 analyze 封顶到 warn，绝不硬阻断 gate）；
    # 缺 SyncNet/ffmpeg 且无外部偏移报告时优雅跳过，交人判。实测严重档另喂 n2d-score（非 gate 退出码）。
    lip = lipc.analyze(root, ep)
    sections["音画同步(AV1)"] = {"skipped": not lip.get("available", False),
                              "verdicts": _verdicts(lip.get("shots", [])), "notes": lip.get("notes", []),
                              "mode": lip.get("mode"), "precision": lip.get("precision")}
    collect_simple("音画同步(AV1)", lip.get("shots", []), stage="compose", default_artifacts=(f"合成/{ep}",))

    # D 档音频白区：配音情绪弧(VEA) + 口音方言(ACC) + 音乐衔接(BGM)——文本/结构机检，缺 voiceover.txt 优雅跳过。
    ac = audioc.analyze(root, ep)
    ac_skipped = not ac.get("available", False)
    # VEA 含两路：设计态(台词强情绪×标注平淡) + 设计情绪×配音声学能量 reconcile(强情绪却念得平)。同轴合并，不新增 label。
    ac_vea = list(ac.get("vea", [])) + list(ac.get("vea_audio", []))
    sections["配音情绪弧(VEA)"] = {"skipped": ac_skipped, "verdicts": _verdicts(ac_vea), "notes": ac.get("notes", [])}
    collect_simple("配音情绪弧(VEA)", ac_vea, stage="voice",
                   default_artifacts=(f"脚本/{ep}/voiceover.txt", f"合成/{ep}/配音/emotion_flow.json"))
    sections["口音方言(ACC)"] = {"skipped": ac_skipped, "verdicts": _verdicts(ac.get("acc", []))}
    collect_simple("口音方言(ACC)", ac.get("acc", []), stage="voice", default_artifacts=("设定库/voicemap.json",))
    sections["音乐衔接(BGM)"] = {"skipped": ac_skipped, "verdicts": _verdicts(ac.get("bgm", []))}
    collect_simple("音乐衔接(BGM)", ac.get("bgm", []), stage="compose", default_artifacts=(f"脚本/{ep}/bgm.txt",))
    # AVE 音画情绪一致性（cross-modal: voiceover emotion vs visual expression）
    av_emo = avec.analyze(root, ep)
    sections["音画情绪一致(AVE)"] = {"skipped": not av_emo.get("available", False),
                                   "verdicts": _verdicts(av_emo.get("findings", [])), "notes": av_emo.get("notes", [])}
    collect_simple("音画情绪一致(AVE)", av_emo.get("findings", []), stage="compose", default_artifacts=(f"出图/{ep}/图片",))

    # 音色声纹 + 跨集 voice_key 漂移（VOICE·advisory）——2026-06 接入主审计：此前只走 n2d-identity
    # identity.py --write 旁路，纯 consistency_audit 漏音色漂移。preflight 纯 stdlib 报跨集换声/未登记；
    # voice_print 用 speaker embedding 量真实音色相似度（缺后端/音频优雅降级交人判）。block 封顶 warn，
    # 不硬阻断视觉 gate（音色返工回 n2d-voice，不该卡出图/出视频）。
    voice_rows: List[dict] = []
    voice_notes: List[str] = []
    voice_skipped = True
    if vcon is not None:
        try:
            pf = vcon.preflight(root, ep)
            voice_skipped = False
            for w in pf.get("warnings", []):
                voice_rows.append({
                    "verdict": "warn",
                    "message": w.get("scope") or w.get("type") or "voice_key 跨集漂移",
                    "character": w.get("character", ""),
                    "loc": f"voicemap:{w.get('character', '')}",
                    "return_to_stage": "voice",
                    "affected_artifacts": ["设定库/voicemap.json"],
                })
            voice_notes += [n for n in pf.get("notes", []) if n]
        except Exception:
            pass  # advisory only; never break the audit
    if vprint is not None:
        try:
            vp = vprint.analyze(root, ep)
            if vp.get("available"):
                voice_skipped = False
                payload = vprint.findings_payload(root, ep, vp)
                for f in payload.get("findings", []):
                    row = dict(f)
                    sev = str(row.get("severity") or row.get("verdict") or "warn")
                    # advisory 封顶：声纹机检 block→warn，不进 total_block 硬阻断视觉 gate。
                    row["verdict"] = "warn" if sev in ("block", "warn") else "ok"
                    row.setdefault("return_to_stage", "voice")
                    voice_rows.append(row)
            elif vp.get("note"):
                voice_notes.append(vp.get("note"))
        except Exception:
            pass
    sections["音色声纹"] = {"skipped": voice_skipped, "verdicts": _verdicts(voice_rows), "notes": voice_notes}
    collect_simple("音色声纹", voice_rows, stage="voice",
                   default_artifacts=("设定库/voicemap.json", f"合成/{ep}/配音/voice_zh.wav"))

    # Rhythm 节奏/留存启发式（advisory）：不声称是成片观感模型，但把 storyboard 时长曲线/钩子密度纳入审计链。
    pace = pr.analyze(root, ep)
    pace_rows: List[dict] = []
    if pace.get("available") and pace.get("verdict") == "warn":
        score = pace.get("score")
        pace_rows.append({
            "verdict": "warn",
            "message": f"节奏/留存 advisory 总分偏低：{score}",
            "loc": f"脚本/{ep}/storyboard.json",
            "affected_artifacts": [f"脚本/{ep}/storyboard.json"],
        })
    for risk in pace.get("risk_shots", []):
        if not isinstance(risk, dict):
            continue
        row = dict(risk)
        clips = [str(c) for c in row.get("clips", []) if c]
        row.setdefault("verdict", "warn")
        if clips:
            row["affected_shots"] = clips
            row["shot"] = " ".join(clips)
        pace_rows.append(row)
    sections["节奏密度(Rhythm)"] = {
        "skipped": not pace.get("available", False),
        "verdicts": _verdicts(pace_rows),
        "notes": pace.get("notes", []),
        "score": pace.get("score"),
        "details": normalize_details(
            pace_rows,
            dim="节奏密度(Rhythm)",
            ep=ep,
            stage="script_stage2",
            default_artifacts=(f"脚本/{ep}/storyboard.json",),
        ),
        "return_to_stage": "script_stage2",
        "rerun_scope": default_scope("节奏密度(Rhythm)", "script_stage2"),
    }

    # 视频侧一致性补强：VLM/LMM 判题、视频 embedding 语义漂移、原生多人对话音画结构、
    # 物理因果链与相机/空间轨迹。重模型 runner 只需写 sidecar；主审计纯标准库读取。
    video_checks = (
        (
            "视频VLM判题(VLM1)",
            vvlm.analyze(root, ep),
            "video",
            (f"生产数据/video_vlm_consistency_{ep}.json", f"出视频/{ep}/video_vlm_consistency.json"),
        ),
        (
            "视频语义一致(VSEM)",
            vsem.analyze(root, ep),
            "video",
            (f"生产数据/video_semantic_consistency_{ep}.json", f"出视频/{ep}/video_semantic_consistency.json"),
        ),
        (
            "多人对话音画(DAV)",
            davc.analyze(root, ep),
            "compose",
            (f"生产数据/dialogue_av_alignment_{ep}.json", f"合成/{ep}"),
        ),
        (
            "物理因果链(CG1)",
            cg.analyze(root, ep),
            "script_stage2",
            (f"脚本/{ep}/storyboard.json", f"生产数据/causal_event_graph_{ep}.json"),
        ),
        (
            "相机空间轨迹(CAM1)",
            camt.analyze(root, ep),
            "video",
            (f"生产数据/camera_trajectory_probe_{ep}.json", f"出视频/{ep}"),
        ),
        (
            "运动质量(MOT1)",
            motq.analyze(root, ep),
            "video",
            (f"生产数据/motion_quality_{ep}.json", f"出视频/{ep}"),
        ),
        (
            "主体视频一致(S2V)",
            s2vc.analyze(root, ep),
            "video",
            (f"生产数据/subject_video_consistency_{ep}.json", f"出视频/{ep}"),
        ),
        (
            "高动态成片证据(SPECV)",
            svqc.analyze(root, ep),
            "video",
            (f"生产数据/spectacle_video_qc_{ep}.json", f"出视频/{ep}"),
        ),
    )
    for dim, raw, stage, artifacts in video_checks:
        sections[dim] = section_from_result(
            dim=dim,
            result=raw,
            detail_key="findings",
            skipped=not raw.get("available", False),
            ep=ep,
            stage=stage,
            default_artifacts=artifacts,
        )

    # 生产一致性补强：纯标准库检查器，覆盖实体记忆、物件/持有/状态转场、交互因果/图谱、
    # 可归因物理事件图、视频证据完整性、成片统一/时间线探针、生成配方/强 schema、
    # 系列包装、语域、场景平面图、成本/路由/重试口径、人审校准集与项目 probe pack。
    prod = pc.analyze(root, ep)
    for dim, raw in (prod.get("sections") or {}).items():
        if not isinstance(raw, dict):
            continue
        meta = PRODUCTION_CONSISTENCY_META.get(dim, {})
        stage = str(meta.get("stage") or "review")
        artifacts = tuple(str(a).format(ep=ep) for a in meta.get("artifacts", ()))
        sections[dim] = section_from_result(
            dim=dim,
            result=raw,
            detail_key="findings",
            skipped=not raw.get("available", False),
            ep=ep,
            stage=stage,
            default_artifacts=artifacts,
        )

    # 扩展一致性补强（2026-06 第二批）：UI/系统面板、音乐母题、系列调色、环境声、
    # 跨集体型，及可插拔 sidecar 的视觉在场检测/外观判官。纯标准库，缺契约/缺登记优雅 WARN。
    ext = ec.analyze(root, ep)
    for dim, raw in (ext.get("sections") or {}).items():
        if not isinstance(raw, dict):
            continue
        meta = ec.SECTION_META.get(dim, {})
        stage = str(meta.get("stage") or "image")
        artifacts = tuple(str(a).format(ep=ep) for a in meta.get("artifacts", ()))
        sections[dim] = section_from_result(
            dim=dim,
            result=raw,
            detail_key="findings",
            skipped=not raw.get("available", False),
            ep=ep,
            stage=stage,
            default_artifacts=artifacts,
        )

    # 结构化段（P0/P1/P2）已有 details：直接取检出条目，避免双重归一
    for sec in sections.values():
        export_rows.extend(active_findings(sec.get("details", [])))

    summary = summarize(sections)
    return {
        "root": root,
        "episode": ep,
        "summary": summary,
        "sections": sections,
        "findings": export_rows,
        "auto_return_tasks": build_auto_return_tasks(sections),
    }


def findings_payload(res: dict) -> dict:
    """run() 结果 → 结构化外发 payload（kind=CONSISTENCY_FINDINGS_KIND，单一真值源）。"""
    return {
        "kind": CONSISTENCY_FINDINGS_KIND,
        "version": 1,
        "root": res.get("root", ""),
        "episode": res.get("episode", ""),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "summary": res.get("summary", {}),
        "findings": res.get("findings", []),
        "auto_return_tasks": res.get("auto_return_tasks", []),
    }


def _append_dashboard_event(root: str, ep: str, res: dict, findings_path: str) -> bool:
    """复用 n2d-dashboard 的事件写入约定，登记一条 consistency_findings 事件（best-effort）。

    同集旧事件按 (episode, event, source) 替换而非堆积（沿用 cmd_gate 的 replace 约定）。
    dashboard 模块加载失败/写失败不阻塞审计——findings JSON 文件才是主产物。
    """
    try:
        dash_py = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "n2d-dashboard", "scripts", "dashboard.py"))
        spec = importlib.util.spec_from_file_location("n2d_dashboard_for_audit", dash_py)
        if spec is None or spec.loader is None:
            return False
        dash = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dash)
        summary = res.get("summary", {}) or {}
        by_dim = summary.get("by_dim", {}) or {}
        event = dash.make_event(
            ep,
            "review",
            "consistency_findings",
            source="n2d-review/scripts/consistency_audit.py",
            meta={
                "findings_path": os.path.relpath(findings_path, root),
                "total_block": summary.get("total_block", 0),
                "total_warn": sum(int((c or {}).get("warn") or 0) for c in by_dim.values()),
                "finding_count": len(res.get("findings", [])),
            },
        )
        dash.replace_events(
            root,
            lambda e: (
                e.get("episode") == event["episode"]
                and e.get("event") == "consistency_findings"
                and e.get("source") == "n2d-review/scripts/consistency_audit.py"
            ),
            [event],
        )
        return True
    except Exception as exc:  # 事件流是旁路：失败留痕到 stderr，不影响审计与文件外发
        print(f"[consistency_audit][warn] dashboard 事件写入失败（忽略）：{exc}", file=sys.stderr)
        return False


def export_findings(root: str, ep: str, res: dict) -> str:
    """聚合一致性检出 → 生产数据/consistency_findings_<集>.json + dashboard 事件（不改既有报告产物）。"""
    path = os.path.join(production_dir(root), f"consistency_findings_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(findings_payload(res), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _append_dashboard_event(root, ep, res, path)
    _refresh_generation_recipe(root, ep)
    _refresh_consistency_ledger(root, ep)
    return path


def _refresh_generation_recipe(root: str, ep: str) -> bool:
    """Best-effort generation recipe hash ledger, derived from production_events."""
    try:
        pc.write_recipe_ledger(root, ep)
        return True
    except Exception as exc:
        print(f"[consistency_audit][warn] generation_recipe 刷新失败（忽略）：{exc}", file=sys.stderr)
        return False


def _refresh_consistency_ledger(root: str, ep: str) -> bool:
    """Best-effort refresh of the read-only consistency ledger after findings export."""
    try:
        ledger_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "consistency_ledger.py"))
        spec = importlib.util.spec_from_file_location("n2d_consistency_ledger_for_audit", ledger_py)
        if spec is None or spec.loader is None:
            return False
        ledger = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ledger)
        ledger.run(root, ep)
        return True
    except Exception as exc:
        print(f"[consistency_audit][warn] consistency_ledger 刷新失败（忽略）：{exc}", file=sys.stderr)
        return False


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--profile", default=os.environ.get("N2D_CONSISTENCY_PROFILE", "demo"),
                    help="demo|production；production 下 degraded 精度退出码为 1")
    ap.add_argument("--no-export", action="store_true",
                    help="只审计不外发（默认会写 生产数据/consistency_findings_<集>.json 并登记 dashboard 事件）")
    ns = ap.parse_args(argv)
    res = run(ns.root.rstrip("/"), ns.episode)
    profile = normalize_profile(ns.profile)
    res["profile"] = profile
    caps = apply_image_qc_precision_evidence(probe_capabilities(), ns.root.rstrip("/"), ns.episode)
    res["capabilities"] = apply_video_semantic_embedding_evidence(caps, ns.root.rstrip("/"), ns.episode)
    # 总精度写进 summary（外发/score/gate/人 据此判"没检查"≠"通过"）——必须在 export 之前算
    res["summary"]["precision_level"] = audit_precision_level(res["capabilities"])
    # 证据等级账本：每维度 proof_type + advanced tier 的 under_proven（gate 据此在交付边界 PENDING→BLOCK）。
    res["summary"]["evidence_grade"] = evidence_grade(res["sections"], res["capabilities"])
    if not ns.no_export and os.path.isdir(ns.root):
        export_findings(ns.root.rstrip("/"), ns.episode, res)
    exit_code = exit_code_for(res["summary"], profile=profile)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return exit_code
    print(f"=== 一致性编排审计（O1·一键全跑）：{ns.root} {ns.episode} ===\n")
    plv = res["summary"].get("precision_level", "full")
    if plv != "full":
        reason = ("无 Pillow，像素级一致性一概未跑，结果不可作通过依据" if plv == "none"
                  else "脸部运行在降级精度，机检通过≠脸一致已验证")
        print(f"⚠️ 本次机检总精度：{plv}——{reason}\n")
    for note in res["capabilities"].get("notes", []):
        print(f"⚠️ {note}\n")
    eg = res["summary"].get("evidence_grade") or {}
    if eg.get("under_proven"):
        print(f"⚠️ 证据等级未达标(PENDING)：{('、').join(eg['under_proven'])} 本可验到 embedding/pixel 级却只到结构/启发式级"
              f"（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 未数值化）；交付边界(compose/review)将 BLOCK，"
              f"装好进阶依赖复跑或显式 N2D_ALLOW_DEGRADED_QC=1 自负其责。\n")
    by = res["summary"]["by_dim"]
    print(f"{'维度':<16} 🔴  🟡  ✅  状态")
    for dim, c in by.items():
        st = "（缺库跳过·人判兜）" if c["skipped"] else (f"评 {c['n']}" if c["n"] else "无可评项")
        print(f"{dim:<16} {c['block']:<3} {c['warn']:<3} {c['ok']:<3} {st}")
    print(f"\n合计 🔴 {res['summary']['total_block']}（任一 🔴 即需回源头重出）")
    for dim, sec in res["sections"].items():
        for n in sec.get("notes", []):
            print(f"  · {dim}: {n}")
        for detail in sec.get("details", [])[:3]:
            if detail.get("verdict") in ("block", "warn"):
                print(f"  · {dim}: {detail.get('verdict')} {detail.get('message', '')}")
    if res.get("auto_return_tasks"):
        print("\n自动回流建议：")
        for task in res["auto_return_tasks"]:
            print(f"  · {task['return_to_stage']}: {'、'.join(task['dimensions'])}；{task['scope']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
