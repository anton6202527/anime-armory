#!/usr/bin/env python3
"""Automatic episode scoring for novel2drama/n2d.

The score is a deterministic roll-up over existing n2d-review checks,
n2d-dashboard events, and optional cached inputs.  It does not replace human
review; it decides whether an episode should automatically flow back to the
smallest likely stage before more expensive work continues.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(__file__)
SKILL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))
COMMON = os.path.join(REPO_SKILLS, "common")
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import EPISODE_REVIEW_SCORE_KIND, PRODUCTION_DIR, production_dir  # noqa: E402  生产数据目录 / kind 单一真值源
from n2d_thresholds import load_thresholds  # noqa: E402  告警阈值单一真值源（与 n2d-dashboard 共用）

INPUT_DIR = "score_inputs"
SCORE_KIND = EPISODE_REVIEW_SCORE_KIND
VERSION = 1

DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "character_consistency": {
        "label": "角色一致性",
        "weight": 20,
        "return_to_stage": "image",
        "scope": "回 n2d-image 重出崩脸/身份漂移镜头；必要时补 identity_registry / reference_group。",
    },
    "outfit_consistency": {
        "label": "服装一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 重出服装/配色漂移镜头；先检查定妆组和服装参考图。",
    },
    "scene_consistency": {
        "label": "场景一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 修场景定妆、光位锚或尾帧；必要时回 n2d-video 重出接缝 clip。",
    },
    "subtitle_correctness": {
        "label": "字幕正确性",
        "weight": 16,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2重跑 finalize_storyboard / 字幕重定时；必要时重出配音 manifest。",
    },
    "audio_visual_sync": {
        "label": "音画同步",
        "weight": 16,
        "return_to_stage": "compose",
        "scope": "回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略；若时长源头错，回 n2d-script 阶段2。",
    },
    "rhythm_density": {
        "label": "节奏密度",
        "weight": 12,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。",
    },
    "style_consistency": {
        "label": "风格一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 继承 style_contract 重出偏风格镜头；必要时回 n2d-script 修 style_contract。",
    },
    "semantic_continuity": {
        "label": "语义继承",
        "weight": 8,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2或 prompt 生成层，修 raw/voiceover→storyboard→出图/出视频的语义谱系断点。",
    },
    "state_continuity": {
        "label": "状态百科",
        "weight": 8,
        "return_to_stage": "image",
        "scope": "回 n2d-image 修 visual_state_ledger / 出图分镜状态锁；必要时回 storyboard 修角色状态演进。",
    },
    "multimodal_continuity": {
        "label": "多模态漂移",
        "weight": 8,
        "return_to_stage": "image",
        "scope": "回 n2d-image 按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产 taxonomy。",
    },
}

CONSISTENCY_MAP = {
    "语义谱系(P0)": "semantic_continuity",
    "状态百科(P1)": "state_continuity",
    "多模态(P2)": "multimodal_continuity",
    "锚点门(N3)": "character_consistency",
    "脸(G1)": "character_consistency",
    "片内时序(N2)": "character_consistency",
    "服装配色(N1)": "outfit_consistency",
    "场景(O2)": "scene_consistency",
    "接缝接力": "scene_consistency",
    "风格(S1)": "style_consistency",
    "糊/低质(N4)": "style_consistency",
}

MECHANICAL_DIM_MAP = {
    "字幕": "subtitle_correctness",
    "节奏": "rhythm_density",
    "配音": "audio_visual_sync",
    "故事板": "audio_visual_sync",
    "衔接": "scene_consistency",
}

QA_KEYWORDS = (
    ("semantic_continuity", ("语义", "谱系", "继承", "semantic", "voiceover", "storyboard")),
    ("state_continuity", ("状态", "动态百科", "visual_state_ledger", "state")),
    ("multimodal_continuity", ("多模态", "道具", "法宝", "视觉语义", "embedding")),
    ("character_consistency", ("角色", "脸", "资产身份", "identity", "Face", "锚点")),
    ("outfit_consistency", ("服装", "配色", "妆造")),
    ("scene_consistency", ("场景", "接缝", "光位", "轴线", "尾帧")),
    ("subtitle_correctness", ("字幕", "SRT", "cue")),
    ("audio_visual_sync", ("音画", "配音", "原生音", "双人声", "时长")),
    ("rhythm_density", ("节奏", "钩子", "爽点", "留存", "集尾")),
    ("style_consistency", ("风格", "style", "画风", "基础视觉")),
)


from n2d_route import episode_number, normalize_episode  # noqa: E402  集号单一真值源


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def score_input_dir(root: str) -> str:
    return os.path.join(production_dir(root), INPUT_DIR)


def safe_ep(ep: str) -> str:
    return normalize_episode(ep)


def cached_path(root: str, ep: str, name: str) -> str:
    return os.path.join(score_input_dir(root), f"{safe_ep(ep)}_{name}.json")


def load_json(path: str) -> Optional[Any]:
    if not os.path.isfile(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def run_json(cmd: Sequence[str]) -> Any:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not return JSON: {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}") from exc


def run_json_safe(cmd: Sequence[str]) -> Any:
    """像 run_json，但命令失败 / 没吐 JSON 时返回 None（不抛）。
    用于可缺席的旁路机检（如 identity 跨集漂移：registry 缺失或 insightface 没装时不该让整次评分崩）。"""
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return json.loads(proc.stdout or "null")
    except Exception:
        return None


def run_identity_drift(root: str, ep: str) -> Optional[Dict[str, Any]]:
    """跨集角色漂移：对截至本集的小窗口跑 n2d-identity，取其 drift 报告。

    窗口 = 本集 + 前两集（给跨集趋势又把面部机检成本压住）。registry 缺失 / insightface 不可用 /
    无早集 → 返回 None 或 available=false 的报告，评分侧按"缺数据"处理，不崩、不臆造。
    这里只拿来识别**跨集回归**（早集稳、本集崩），片内崩脸已由 consistency_audit 脸(G1) 计分，避免双重扣分。"""
    identity_py = os.path.join(REPO_SKILLS, "n2d-identity", "scripts", "identity.py")
    n = episode_number(ep)
    eps_arg = f"{max(1, n - 2)}-{n}" if n is not None else ep
    combined = run_json_safe([sys.executable, identity_py, root, "--episodes", eps_arg, "--json"])
    if not isinstance(combined, dict):
        return None
    drift = combined.get("drift")
    return drift if isinstance(drift, dict) else None


def run_checks(root: str, ep: str) -> Dict[str, Any]:
    review_scripts = os.path.join(REPO_SKILLS, "n2d-review", "scripts")
    consistency = run_json([sys.executable, os.path.join(review_scripts, "consistency_audit.py"), root, ep, "--json"])
    mechanical = run_json([sys.executable, os.path.join(review_scripts, "mechanical_check.py"), root, ep, "--json"])
    visual = run_json([sys.executable, os.path.join(SCRIPT_DIR, "visual_checks.py"), root, ep, "--json"])
    identity = run_identity_drift(root, ep)
    write_json(cached_path(root, ep, "consistency"), consistency)
    write_json(cached_path(root, ep, "mechanical"), mechanical)
    write_json(cached_path(root, ep, "visual"), visual)
    if identity is not None:
        write_json(cached_path(root, ep, "identity"), identity)
    return {"consistency": consistency, "mechanical": mechanical, "visual": visual, "identity": identity}


def load_dashboard_episode(root: str, ep: str) -> Optional[Dict[str, Any]]:
    dashboard = load_json(os.path.join(production_dir(root), "dashboard.json"))
    if not isinstance(dashboard, dict):
        return None
    for item in dashboard.get("episodes", []):
        if isinstance(item, dict) and item.get("episode") == ep:
            return item
    return None


def empty_dimension(key: str) -> Dict[str, Any]:
    spec = DIMENSIONS[key]
    return {
        "key": key,
        "label": spec["label"],
        "weight": spec["weight"],
        "score": 70,
        "status": "insufficient_data",
        "blocks": 0,
        "warnings": 0,
        "infos": 0,
        "skipped": True,
        "evidence": ["未采集该维度机器信号"],
        "return_to_stage": spec["return_to_stage"],
        "rerun_scope": spec["scope"],
    }


def severity_counts_to_score(blocks: int, warnings: int, infos: int, skipped: bool) -> Tuple[int, str]:
    if skipped and blocks == 0 and warnings == 0:
        return 70, "insufficient_data"
    score = max(0, 100 - blocks * 35 - warnings * 12 - infos * 2)
    if blocks > 0:
        return score, "fail"
    if warnings > 0 or score < 85:
        return score, "warn"
    return score, "pass"


def add_signal(
    dims: Dict[str, Dict[str, Any]],
    dim_key: str,
    *,
    blocks: int = 0,
    warnings: int = 0,
    infos: int = 0,
    skipped: bool = False,
    evidence: Optional[str] = None,
) -> None:
    item = dims[dim_key]
    item["blocks"] += int(blocks)
    item["warnings"] += int(warnings)
    item["infos"] += int(infos)
    item["skipped"] = bool(item["skipped"] and skipped)
    if evidence:
        item["evidence"].append(evidence)


def normalize_mechanical_severity(sev: str) -> str:
    return {"🔴": "block", "🟡": "warn", "🟢": "info", "block": "block", "warn": "warn", "info": "info"}.get(sev, "info")


def map_qa_dim(text: str) -> Optional[str]:
    hay = text or ""
    for key, words in QA_KEYWORDS:
        if any(word in hay for word in words):
            return key
    return None


FACE_DIM = "脸(G1)"
PILLOW_FALLBACK_MODE = "pillow_fallback"  # 与 n2d-review face_consistency.PILLOW_FALLBACK_MODE 同字面值


def apply_face_precision(dims: Dict[str, Dict[str, Any]], consistency: Optional[Dict[str, Any]]) -> None:
    """G1 Pillow 降级档消费：有真实（但低精度）信号 → 不再整维度 insufficient_data，给降权分。

    face_consistency 无 insightface 时降级为 Pillow 基础机检（图存在/可解码/分辨率/清晰度），
    section 标 mode=pillow_fallback。此时 character_consistency：
      - skipped=False（有信号，避免假性缺数据）；
      - 标 precision=pillow_fallback → finalize 时维度权重减半（降权分），状态封顶 warn(需复核)；
      - 留证据提示「建议装 insightface 提升精度」。
    """
    if not isinstance(consistency, dict):
        return
    sections = consistency.get("sections") if isinstance(consistency.get("sections"), dict) else {}
    face = sections.get(FACE_DIM) if isinstance(sections.get(FACE_DIM), dict) else {}
    if face.get("mode") != PILLOW_FALLBACK_MODE:
        return
    item = dims["character_consistency"]
    item["precision"] = PILLOW_FALLBACK_MODE
    item["skipped"] = False
    item["evidence"].append(
        "脸(G1) 为 Pillow 降级机检（仅查图存在/可解码/分辨率/清晰度，无人脸相似度）——"
        "该维度按降权分计入；建议安装 insightface 提升精度，崩脸仍需人判兜底"
    )


def apply_consistency(dims: Dict[str, Dict[str, Any]], consistency: Optional[Dict[str, Any]]) -> None:
    if not isinstance(consistency, dict):
        return
    by_dim = ((consistency.get("summary") or {}).get("by_dim") or {})
    for source_dim, target in CONSISTENCY_MAP.items():
        data = by_dim.get(source_dim)
        if not isinstance(data, dict):
            continue
        add_signal(
            dims,
            target,
            blocks=int(data.get("block") or 0),
            warnings=int(data.get("warn") or 0),
            infos=0,
            skipped=bool(data.get("skipped")),
            evidence=f"{source_dim}: block={data.get('block', 0)} warn={data.get('warn', 0)} ok={data.get('ok', 0)} skipped={data.get('skipped', False)}",
        )
        sections_obj = consistency.get("sections") if isinstance(consistency.get("sections"), dict) else {}
        section = (sections_obj.get(source_dim) or {})
        details = section.get("details") if isinstance(section, dict) else []
        if isinstance(details, list):
            for detail in details[:4]:
                if not isinstance(detail, dict):
                    continue
                msg = str(detail.get("message") or detail.get("kind") or "")
                shots = "、".join(str(x) for x in detail.get("affected_shots", [])[:4])
                artifacts = "、".join(str(x) for x in detail.get("affected_artifacts", [])[:4])
                suffix = ""
                if shots:
                    suffix += f" 定位镜头：{shots}"
                if artifacts:
                    suffix += f" 定位产物：{artifacts}"
                add_signal(dims, target, skipped=bool(data.get("skipped")), evidence=f"{source_dim} detail: {msg}{suffix}".strip())


def apply_identity_drift(dims: Dict[str, Dict[str, Any]], drift: Optional[Dict[str, Any]], ep: str) -> None:
    """把 n2d-identity 的跨集漂移报告并进 character_consistency。

    只加**跨集回归**信号（早集稳、本集崩/临界）且是 warn 级——片内崩脸的 block 已由
    consistency_audit 的脸(G1) 计入，这里再按 block 计就会双重扣分。机检不可用时只标 skipped、
    不臆造分数（与"缺数据"语义一致：单集评分对跨集本就是盲的，缺则显式标注而非假装通过）。"""
    if not isinstance(drift, dict):
        return
    if not drift.get("available"):
        add_signal(
            dims, "character_consistency", skipped=True,
            evidence="跨集漂移机检不可用（insightface/cv2 缺失、identity_registry 缺失或机检跳过）——本集未核对跨集角色漂",
        )
        return
    episodes = list(drift.get("episodes") or [])
    if len(episodes) < 2:
        return  # 窗口不足两集，无跨集信息

    def _num(value: str) -> int:
        n = episode_number(value)
        return n if n is not None else 10 ** 9

    this_num = _num(ep)
    for name, info in sorted((drift.get("characters") or {}).items()):
        if not isinstance(info, dict):
            continue
        eps = info.get("episodes") or {}
        cur = eps.get(ep) or {}
        block = int(cur.get("block") or 0)
        warn = int(cur.get("warn") or 0)
        first_bad = str(info.get("first_bad_episode") or "")
        prior_clean = any(
            int((eps.get(e) or {}).get("block") or 0) == 0 and int((eps.get(e) or {}).get("ok") or 0) > 0
            for e in episodes if _num(e) < this_num
        )
        if block > 0 and (first_bad == ep or prior_clean):
            add_signal(
                dims, "character_consistency", warnings=1, skipped=False,
                evidence=f"跨集漂移：{name} 在 {ep} 有 {block} 个崩脸镜头、早集尚稳（first_bad={first_bad or ep}）→ 角色相对前集回归，定位重出该角色镜头",
            )
        elif warn > 0 and prior_clean:
            add_signal(
                dims, "character_consistency", warnings=1, skipped=False,
                evidence=f"跨集漂移预警：{name} 在 {ep} 有 {warn} 个临界镜头、早集稳→ 关注该角色是否开始漂",
            )


def apply_mechanical(dims: Dict[str, Dict[str, Any]], mechanical: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """把 mechanical_check findings 并进维度分，返回**无法归到任一维度的 findings**。
    历史 bug：dim 命不中关键词就 `continue` 静默丢弃——`BLOCK 完整性`(缺产物)/`BLOCK 水印`(AI 标识)
    这类真问题不归任何七维，曾被静默吞掉、不扣分、可放行。现改为回传给上层显式留痕、阻断静默通过。"""
    unmapped: List[Dict[str, Any]] = []
    if not isinstance(mechanical, list):
        return unmapped
    for finding in mechanical:
        if not isinstance(finding, dict):
            continue
        dim = str(finding.get("dim") or "")
        msg = str(finding.get("msg") or "")
        sev = normalize_mechanical_severity(str(finding.get("sev") or ""))
        target = MECHANICAL_DIM_MAP.get(dim) or map_qa_dim(dim + msg)
        if not target:
            unmapped.append({"source": "mechanical", "sev": sev, "dim": dim, "loc": str(finding.get("loc") or ""), "msg": msg})
            continue
        add_signal(
            dims,
            target,
            blocks=1 if sev == "block" else 0,
            warnings=1 if sev == "warn" else 0,
            infos=1 if sev == "info" else 0,
            skipped=False,
            evidence=f"mechanical[{dim}] {finding.get('loc', '')}: {msg}",
        )
    return unmapped


def resolve_pass_rate_floor(root: str, explicit: Optional[float]) -> Optional[float]:
    """通过率下限与 n2d-dashboard 完全同源：显式 --pass-rate-floor >
    n2d_thresholds.load_thresholds（默认 ← _设置.md「告警通过率下限」← alert_thresholds.json ← 环境变量）。
    历史 bug：曾只读 json、漏 _设置.md/env，现统一走 load_thresholds 修掉。"""
    if explicit is not None:
        return explicit
    val = load_thresholds(root).get("final_pass_rate_floor")
    if isinstance(val, (int, float)):
        return float(val)
    return None


def apply_dashboard(dims: Dict[str, Dict[str, Any]], dashboard_ep: Optional[Dict[str, Any]], pass_rate_floor: Optional[float] = None) -> List[Dict[str, Any]]:
    """并进 dashboard 的 recent_blockers + 通过率告警，返回**无法归维的 blocker**（均为 block 级）。"""
    unmapped: List[Dict[str, Any]] = []
    if not isinstance(dashboard_ep, dict):
        return unmapped
    for blocker in dashboard_ep.get("recent_blockers", []):
        if not isinstance(blocker, dict):
            continue
        target = map_qa_dim(" ".join(str(blocker.get(k, "")) for k in ("dim", "loc", "msg")))
        if target:
            add_signal(
                dims,
                target,
                blocks=1,
                skipped=False,
                evidence=f"dashboard block[{blocker.get('stage', '')}/{blocker.get('dim', '')}]: {blocker.get('msg', '')}",
            )
        else:
            unmapped.append({"source": "dashboard", "sev": "block", "dim": str(blocker.get("dim") or ""),
                             "loc": f"{blocker.get('stage', '')}/{blocker.get('loc', '')}".strip("/"), "msg": str(blocker.get("msg") or "")})
    pass_rate = dashboard_ep.get("final_pass_rate")
    # 通过率下限不再硬编码：与 n2d-dashboard 的 final_pass_rate_floor 同源（生产数据/alert_thresholds.json
    # 或 _设置.md 告警通过率下限）。floor=None（默认，同 dashboard）→ 不告警，避免两处口径打架。
    if pass_rate_floor is not None and isinstance(pass_rate, (int, float)) and pass_rate < pass_rate_floor:
        # Low final pass rate is a production instability signal.  It is not a
        # content-specific dimension, so attach it to the most expensive visual
        # stages as a warning.
        add_signal(
            dims,
            "character_consistency",
            warnings=1,
            skipped=False,
            evidence=f"dashboard final_pass_rate={pass_rate:.2f} < 下限 {pass_rate_floor:.2f}（同 dashboard 阈值），生成稳定性偏低",
        )
    return unmapped


VISUAL_DIM_MAP = {
    "image_similarity": "scene_consistency",
    "subtitle_ocr": "subtitle_correctness",
    "av_duration": "audio_visual_sync",
    "lip_sync": "audio_visual_sync",
    "final_rhythm_density": "rhythm_density",
}


def apply_visual(dims: Dict[str, Dict[str, Any]], visual: Optional[Dict[str, Any]]) -> None:
    if not isinstance(visual, dict):
        return
    sections = visual.get("sections")
    if not isinstance(sections, dict):
        return
    for source, target in VISUAL_DIM_MAP.items():
        sec = sections.get(source)
        if not isinstance(sec, dict):
            continue
        evidence = sec.get("evidence") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        metrics = sec.get("metrics")
        metric_text = f" metrics={json.dumps(metrics, ensure_ascii=False, sort_keys=True)}" if isinstance(metrics, dict) and metrics else ""
        add_signal(
            dims,
            target,
            blocks=int(sec.get("blocks") or 0),
            warnings=int(sec.get("warnings") or 0),
            infos=int(sec.get("infos") or 0),
            skipped=bool(sec.get("skipped")),
            evidence=f"visual[{source}]: block={sec.get('blocks', 0)} warn={sec.get('warnings', 0)} skipped={sec.get('skipped', False)}{metric_text}",
        )
        for item in evidence[:4]:
            add_signal(dims, target, infos=0, skipped=bool(sec.get("skipped")), evidence=f"visual[{source}] {item}")


def finalize_dimensions(dims: Dict[str, Dict[str, Any]], threshold: int) -> None:
    for item in dims.values():
        # Remove the default "no data" note once real evidence exists.
        if len(item["evidence"]) > 1 and item["evidence"][0] == "未采集该维度机器信号":
            item["evidence"] = item["evidence"][1:]
        score, status = severity_counts_to_score(item["blocks"], item["warnings"], item["infos"], item["skipped"])
        item["score"] = score
        if score < threshold and status == "pass":
            status = "warn"
        if item.get("precision") == PILLOW_FALLBACK_MODE:
            # 降级档（低精度信号）：维度权重减半（降权分），干净结果也只给 warn(需复核)、不臆造满信心 pass
            item["weight"] = max(1, int(round(int(item["weight"]) / 2)))
            if status == "pass":
                status = "warn"
        item["status"] = status


def weighted_total(dims: Dict[str, Dict[str, Any]]) -> int:
    total_weight = sum(int(item["weight"]) for item in dims.values())
    weighted = sum(float(item["score"]) * int(item["weight"]) for item in dims.values())
    return int(round(weighted / total_weight)) if total_weight else 0


def unique(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def extract_shots(text: str) -> List[str]:
    shots: List[str] = []
    for match in re.finditer(r"(?i)\b(EP\d+[_-]CLIP[_-]?0*(\d+)|CLIP[_\s-]*0*(\d+))\b", text or ""):
        raw = match.group(1)
        number = match.group(2) or match.group(3)
        if raw.upper().startswith("EP"):
            shots.append(raw.upper().replace("-", "_"))
        if number:
            shots.append(f"Clip_{int(number):02d}")
    for match in re.finditer(r"镜头\s*0*(\d+)", text or ""):
        shots.append(f"Clip_{int(match.group(1)):02d}")
    return unique(shots)


def extract_artifacts(text: str) -> List[str]:
    artifacts: List[str] = []
    pattern = r"(?:出图|出视频|合成|脚本|设定库|合规)/[^\s，。；;|)）]+"
    for match in re.finditer(pattern, text or ""):
        artifacts.append(match.group(0).rstrip("，。；;:："))
    return unique(artifacts)


def inferred_artifacts(stage: str, dim_key: str, ep: str, shots: Sequence[str]) -> List[str]:
    out: List[str] = []
    if not shots and stage == "script_stage2":
        shots = []
    for shot in shots:
        if stage == "image":
            out.append(f"出图/{ep}/图片/{shot}.png")
        elif stage == "video":
            out.append(f"出视频/{ep}/视频/{shot}.mp4")
        elif stage == "compose":
            out.append(f"出视频/{ep}/视频/{shot}.mp4")
    if stage == "script_stage2":
        if dim_key == "subtitle_correctness":
            out.extend([f"脚本/{ep}/字幕_中文.srt", f"脚本/{ep}/字幕_英文.srt"])
        out.append(f"脚本/{ep}/storyboard.json")
        if dim_key == "semantic_continuity":
            out.extend([f"出图/{ep}/prompt", f"出视频/{ep}/prompt"])
    elif stage == "compose":
        out.append(f"合成/{ep}")
    elif stage == "image":
        if dim_key == "state_continuity":
            out.extend([f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/visual_state_ledger.json"])
        elif dim_key == "multimodal_continuity":
            out.extend([f"出图/{ep}/prompt/01_分镜出图.md", f"出图/{ep}/图片"])
    return unique(out)


def evidence_scope(item: Dict[str, Any], ep: str) -> Tuple[List[str], List[str]]:
    stage = str(item["return_to_stage"])
    dim_key = str(item["key"])
    shots: List[str] = []
    artifacts: List[str] = []
    for ev in item.get("evidence", []) or []:
        text = str(ev)
        shots.extend(extract_shots(text))
        artifacts.extend(extract_artifacts(text))
    shots = unique(shots)
    artifacts = unique([*artifacts, *inferred_artifacts(stage, dim_key, ep, shots)])
    return shots, artifacts


def build_auto_return_tasks(dims: Dict[str, Dict[str, Any]], threshold: int, ep: str) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for item in dims.values():
        if item["status"] == "insufficient_data":
            continue
        if item["score"] >= threshold and item["status"] not in {"fail", "insufficient_data"}:
            continue
        stage = str(item["return_to_stage"])
        if stage not in grouped:
            grouped[stage] = {
                "return_to_stage": stage,
                "dimensions": [],
                "scope": [],
                "affected_artifacts": [],
                "affected_shots": [],
            }
        grouped[stage]["dimensions"].append(item["label"])
        grouped[stage]["scope"].append(item["rerun_scope"])
        shots, artifacts = evidence_scope(item, ep)
        grouped[stage]["affected_shots"].extend(shots)
        grouped[stage]["affected_artifacts"].extend(artifacts)
    tasks = []
    for stage, data in grouped.items():
        shots = unique(data["affected_shots"])
        artifacts = unique(data["affected_artifacts"])
        scope_parts = unique(data["scope"])
        if shots:
            scope_parts.append("定位镜头：" + "、".join(shots))
        if artifacts:
            scope_parts.append("定位产物：" + "、".join(artifacts[:8]))
        unique_scope = "；".join(scope_parts)
        tasks.append({
            "return_to_stage": stage,
            "dimensions": data["dimensions"],
            "scope": unique_scope,
            "affected_artifacts": artifacts,
            "affected_shots": shots,
        })
    return tasks


def build_data_collection_tasks(dims: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    missing = [item for item in dims.values() if item["status"] == "insufficient_data"]
    if not missing:
        return []
    return [{
        "skill": "n2d-score",
        "action": "run_checks",
        "dimensions": [item["label"] for item in missing],
        "scope": "缺机器信号，先采集 consistency/mechanical/visual checks；不要在缺证据时直接返工。",
        "command": "python3 skills/n2d-score/scripts/score.py <作品根> <集> --run-checks --threshold <阈值>",
    }]


def build_triage_tasks(unmapped: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """无法归到七维的 findings → 分诊任务。block 级单列（必须人判归类，不能放行），warn/info 仅留痕。"""
    if not unmapped:
        return []
    blocks = [u for u in unmapped if u.get("sev") == "block"]
    others = [u for u in unmapped if u.get("sev") != "block"]
    tasks: List[Dict[str, Any]] = []
    if blocks:
        tasks.append({
            "skill": "n2d-score",
            "action": "triage_unmapped",
            "scope": "存在无法自动归到七维的 block 级证据（如 完整性/水印/视频）——必须人判归类或修复，不能直接放行。"
                     + "；".join(f"[{b['dim']}] {b['loc']}: {b['msg']}" for b in blocks[:6]),
            "findings": blocks,
        })
    if others:
        tasks.append({
            "skill": "n2d-score",
            "action": "triage_unmapped_low",
            "scope": "未归类的 warn/info 证据，仅留痕供复核：" + "；".join(f"[{o['dim']}] {o['msg']}" for o in others[:6]),
            "findings": others,
        })
    return tasks


def score_episode(
    root: str,
    ep: str,
    *,
    consistency: Optional[Dict[str, Any]] = None,
    mechanical: Optional[List[Dict[str, Any]]] = None,
    visual: Optional[Dict[str, Any]] = None,
    identity: Optional[Dict[str, Any]] = None,
    dashboard_ep: Optional[Dict[str, Any]] = None,
    threshold: int = 85,
    pass_rate_floor: Optional[float] = None,
) -> Dict[str, Any]:
    ep = normalize_episode(ep)
    dims = {key: empty_dimension(key) for key in DIMENSIONS}
    apply_consistency(dims, consistency)
    apply_face_precision(dims, consistency)
    apply_identity_drift(dims, identity, ep)
    unmapped = apply_mechanical(dims, mechanical)
    apply_visual(dims, visual)
    unmapped += apply_dashboard(dims, dashboard_ep, pass_rate_floor)
    finalize_dimensions(dims, threshold)
    total = weighted_total(dims)
    hard_fail = any(item["status"] == "fail" for item in dims.values())
    insufficient = any(item["status"] == "insufficient_data" for item in dims.values())
    # 无法归到七维的 findings 不能静默吞：block 级强制不通过（曾因关键词没命中而被丢弃、放行）。
    unmapped_blocks = [u for u in unmapped if u.get("sev") == "block"]
    status = "fail" if hard_fail or total < threshold else "pass"
    if unmapped_blocks and status == "pass":
        status = "warn"  # 有未归类的 block 证据时，绝不给 pass；交人判分诊
    if insufficient and status == "pass":
        status = "warn"
    return {
        "kind": SCORE_KIND,
        "version": VERSION,
        "root": root,
        "episode": ep,
        "generated_at": now_iso(),
        "threshold": threshold,
        "total_score": total,
        "status": status,
        "score_inputs": {
            "consistency": cached_path(root, ep, "consistency"),
            "mechanical": cached_path(root, ep, "mechanical"),
            "visual": cached_path(root, ep, "visual"),
            "identity": cached_path(root, ep, "identity"),
        },
        "dimensions": list(dims.values()),
        "auto_return_tasks": build_auto_return_tasks(dims, threshold, ep),
        "data_collection_tasks": build_data_collection_tasks(dims) + build_triage_tasks(unmapped),
        "unmapped_findings": unmapped,
    }


def format_status(status: str) -> str:
    return {"pass": "通过", "warn": "需复核", "fail": "回流", "insufficient_data": "缺数据"}.get(status, status)


def render_markdown(score: Dict[str, Any]) -> str:
    lines = [
        "# n2d 自动审片评分",
        "",
        f"- 集：{score['episode']}",
        f"- 总分：{score['total_score']} / 100",
        f"- 阈值：{score['threshold']}",
        f"- 状态：{format_status(score['status'])}",
        f"- 生成时间：{score['generated_at']}",
        "",
        "## 维度",
        "",
        "| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for item in score["dimensions"]:
        lines.append(
            f"| {item['label']} | {item['weight']} | {item['score']} | {format_status(item['status'])} | "
            f"{item['blocks']} | {item['warnings']} | {item['return_to_stage']} |"
        )
    if score.get("auto_return_tasks"):
        lines.extend(["", "## 自动回流建议", ""])
        for task in score["auto_return_tasks"]:
            dims = "、".join(task.get("dimensions", []))
            lines.append(f"- `{task['return_to_stage']}`：{dims}；{task.get('scope', '')}")
    if score.get("data_collection_tasks"):
        lines.extend(["", "## 数据采集建议", ""])
        for task in score["data_collection_tasks"]:
            dims = "、".join(task.get("dimensions", []))
            lines.append(f"- `{task['skill']}`：{dims}；{task.get('scope', '')}")
    if score.get("unmapped_findings"):
        lines.extend(["", "## 未归类证据（无法自动归到七维·需人判分诊）", ""])
        for u in score["unmapped_findings"]:
            lines.append(f"- {u.get('sev')} [{u.get('dim')}] {u.get('loc', '')}: {u.get('msg', '')}（来源 {u.get('source')}）")
    lines.extend(["", "## 证据", ""])
    for item in score["dimensions"]:
        lines.append(f"### {item['label']}")
        for ev in item.get("evidence", [])[:8]:
            lines.append(f"- {ev}")
        if len(item.get("evidence", [])) > 8:
            lines.append(f"- ...另有 {len(item['evidence']) - 8} 条")
    lines.append("")
    return "\n".join(lines)


def write_score(root: str, score: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    ep = score["episode"]
    write_json(os.path.join(production_dir(root), f"score_{ep}.json"), score)
    with open(os.path.join(production_dir(root), f"score_{ep}.md"), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(score))


def enqueue_low(score: Dict[str, Any], *, max_concurrency: int, max_retries: int, budget: Optional[float], budget_unit: Optional[str]) -> Optional[Dict[str, Any]]:
    tasks_spec = score.get("auto_return_tasks") or []
    if not tasks_spec:
        return None
    queue_py = os.path.join(REPO_SKILLS, "n2d-batch", "scripts", "queue.py")
    spec = importlib.util.spec_from_file_location("n2d_batch_queue_for_score", queue_py)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load n2d-batch queue.py")
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    root = score["root"]
    ep = score["episode"]
    estimates = batch.load_cost_estimates(root)
    tasks: List[Dict[str, Any]] = []
    for item in tasks_spec:
        tasks.extend(
            batch.rerun_tasks(
                root,
                episodes={ep},
                rerun_from=item["return_to_stage"],
                cost_estimates=estimates,
                max_retries=max_retries,
                rerun_scope=item.get("scope", ""),
                affected_artifacts=item.get("affected_artifacts", []),
                affected_shots=item.get("affected_shots", []),
            )
        )
    tasks = batch.dedupe_task_ids(tasks)
    budget_data = batch.apply_budget(tasks, budget, budget_unit)
    queue = batch.make_queue(root, tasks, max_concurrency=max_concurrency, max_retries=max_retries, budget=budget_data)
    return batch.write_planned_queue(root, queue, replace=False)


def cmd_score(ns: argparse.Namespace) -> int:
    root = ns.root.rstrip("/")
    ep = normalize_episode(ns.episode)
    inputs: Dict[str, Any] = {}
    if ns.run_checks:
        inputs.update(run_checks(root, ep))
    else:
        inputs["consistency"] = load_json(cached_path(root, ep, "consistency"))
        inputs["mechanical"] = load_json(cached_path(root, ep, "mechanical"))
        inputs["visual"] = load_json(cached_path(root, ep, "visual"))
        inputs["identity"] = load_json(cached_path(root, ep, "identity"))
    inputs["dashboard_ep"] = load_dashboard_episode(root, ep)
    score = score_episode(
        root,
        ep,
        consistency=inputs.get("consistency"),
        mechanical=inputs.get("mechanical"),
        visual=inputs.get("visual"),
        identity=inputs.get("identity"),
        dashboard_ep=inputs.get("dashboard_ep"),
        threshold=ns.threshold,
        pass_rate_floor=resolve_pass_rate_floor(root, ns.pass_rate_floor),
    )
    queue = None
    if ns.enqueue_low and score["status"] != "pass":
        queue = enqueue_low(
            score,
            max_concurrency=ns.max_concurrency,
            max_retries=ns.max_retries,
            budget=ns.budget,
            budget_unit=ns.budget_unit,
        )
        score["enqueued_batch_tasks"] = len((queue or {}).get("tasks", []))
    if not ns.no_write:
        write_score(root, score)
    print(render_markdown(score) if ns.markdown else json.dumps(score, ensure_ascii=False, indent=2))
    return 1 if score["status"] == "fail" else 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d automatic episode review score")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--run-checks", action="store_true", help="run consistency/mechanical/visual checks and cache their JSON")
    ap.add_argument("--threshold", type=int, default=85)
    ap.add_argument("--pass-rate-floor", type=float, default=None,
                    help="通过率下限告警阈值；缺省读 生产数据/alert_thresholds.json 的 final_pass_rate_floor（与 n2d-dashboard 同源），都没有则不告警")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--enqueue-low", action="store_true", help="write n2d-batch rerun queue when score is below threshold")
    ap.add_argument("--max-concurrency", type=int, default=1)
    ap.add_argument("--max-retries", type=int, default=1)
    ap.add_argument("--budget", type=float)
    ap.add_argument("--budget-unit")
    return ap


def main(argv: List[str]) -> int:
    return cmd_score(parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
