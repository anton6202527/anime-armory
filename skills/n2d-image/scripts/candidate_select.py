#!/usr/bin/env python3
"""best-of-N 候选自动排序选片 + reroll 决策 —— 把人从「抽卡选片」里解放出来。

批量产线的最大人工触点之一是「一个可用镜要生 20-30 张、人工挑一张」（2026 行业实测）。本脚本对一个
镜头的 N 张候选图自动排序、选最优、并判「是否全废需 reroll」，让批量 runner 不必每镜等人挑版。

**2026 SOTA 铁律（arXiv 2604.25235「VLM Judges Can Rank but Cannot Score」）**：VLM 能可靠地**成对排序**
（A 和 B 哪张更好），但给的**绝对分不可校准**。故本脚本把 VLM 当 **ranker（成对比较）** 用、绝不当
绝对打分器；硬地板（崩脸/QC 硬伤）用**确定性**信号兜底，VLM 只在合格者之间挑更好的那张。

三层（自上而下，缺则降级，绝不臆造）：
  ① 硬地板·确定性：`qc_hard_fail`(崩脸/纯文生图/接缝断等 image_qc 硬伤) 直接淘汰，不进选片；
  ② 排序·VLM ranker（可选）：配 `N2D_VLM_COMPARE_CMD`（占位 {image_a}{image_b}{prompt}，stdout 回
     `{"winner":"a"|"b"|"tie"}`·厂商无关）→ 合格者单淘汰赛选冠军（N-1 次比较，确定性分做平局裁决）；
  ③ 排序·确定性兜底：无 VLM 时按 face 余弦(对锚)→QC warn 数→清晰度 排序。
reroll_needed：全部候选都硬伤（无合格者），或最优者 face 余弦仍 < identity_floor（最好的也崩脸）。

**Genflow 式纠偏 reroll（arXiv 2605.16748·2026）**：reroll 不再只是二元"重抽"，而是从**失败分布**生成
**负权纠偏处方**（`corrective`：该加的 negatives + 该强化的 reinforce + raise_face_anchor/force_image2image
标志），喂给 runner 下一轮**有的放矢**地重生成——动态纠偏比固定 best-of-N 抽卡把可用率从 42%→89%。
处方纯由已采集的确定性信号（qc 硬伤原因 / face 余弦）推导，不挂 LLM 评委。

**可用率账本（yield ledger）**：2026 工业级第一指标是 usable-yield（可用率=过硬地板/总生成），不是 cost。
每次选片把逐镜可用率事件追加到 `生产数据/yield_ledger.jsonl`，并重算滚动汇总 `生产数据/yield_summary.json`；
reroll 后再跑即记一轮新事件，可用率随纠偏回升可见。n2d-feedback/self_audit 可读该账本看趋势。

报告型：写 `生产数据/candidate_selection_第N集.json`；`--apply` 才把选中图拷到落档路径（不可逆=显式）。
keyshot 候选旁车若声明 `source_target`，优先按该目标落档（如 `出图/第N集/图片/Clip01_first.png`），
否则回退到旧路径 `出图/<ep>/图片/<clip>.png`。
纯排序/选片/纠偏/可用率是纯函数，有 pytest 覆盖（test_candidate_select.py）。

用法：python3 candidate_select.py <作品根> 第N集 [--clip 镜头X] [--apply] [--no-ledger] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import codex_image_runner as cir  # noqa: E402

KIND = "n2d_candidate_selection"
VERSION = 1
TARGET_HINT_KEYS = ("source_target", "target", "target_path", "output_path")

# 确定性兜底排序权重（face 余弦是身份主信号 → 最高权重；清晰度兜底）。
DET_WEIGHTS = {"face_consistency": 1.0, "composition": 0.3, "hook_strength": 0.3,
               "style_match": 0.3, "asset_consistency": 0.4, "sharpness": 0.2}
# 最优者 face 余弦仍低于此 → 判「最好的也崩脸」→ reroll（与 face_consistency 自标定地板同量级的保守线）。
IDENTITY_FLOOR = float(os.environ.get("N2D_CANDIDATE_IDENTITY_FLOOR", "0.45") or "0.45")


# ── 纯函数：排序 / 单淘汰冠军 / 选片 ─────────────────────────────────────────────

def deterministic_score(cand: Dict[str, Any]) -> float:
    """候选确定性总分（信号缺失记 0，绝不臆造）。纯函数。"""
    s = 0.0
    for key, w in DET_WEIGHTS.items():
        v = cand.get(key)
        if isinstance(v, (int, float)):
            s += w * float(v)
    return round(s, 4)


def deterministic_rank(cands: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """确定性排序：硬伤沉底；合格者按 face 余弦→总分→清晰度 降序。纯函数。"""
    def key(c: Dict[str, Any]):
        hard = bool(c.get("qc_hard_fail"))
        face = c.get("face_consistency")
        face = float(face) if isinstance(face, (int, float)) else -1.0
        return (not hard, face, deterministic_score(c),
                float(c.get("sharpness") or 0))
    return sorted(cands, key=key, reverse=True)


def vlm_champion(survivors: Sequence[Dict[str, Any]],
                 compare: Callable[[Dict[str, Any], Dict[str, Any]], str]) -> Dict[str, Any]:
    """合格候选里用成对比较（VLM ranker）单淘汰选冠军，N-1 次比较。平局→确定性分高者胜。纯函数。

    compare(a, b) → 'a' | 'b' | 'tie'。VLM 当 ranker（成对）用，不当绝对打分器。"""
    champ = survivors[0]
    for challenger in survivors[1:]:
        try:
            verdict = compare(champ, challenger)
        except Exception:
            verdict = "tie"
        if verdict == "b":
            champ = challenger
        elif verdict == "tie":
            if deterministic_score(challenger) > deterministic_score(champ):
                champ = challenger
    return champ


# ── Genflow 式纠偏处方：从失败分布生成"负权纠偏" + 该强化项（确定性·非 LLM）────────────
# arXiv 2605.16748 Genflow：把"为什么废"动态回灌成 negative 提示（而非固定 best-of-N 抽卡），
# 可用率 42%→89%、judge↔人 ρ=0.84。本处方纯由已采集确定性信号（qc 硬伤原因 / face 余弦）推导。
FAILURE_CORRECTIONS: Dict[str, Dict[str, Any]] = {
    "face_drift": {
        "label": "崩脸/换脸",
        "negatives": ["不要换脸", "不要重画五官", "不要改脸型/发型/发饰", "no face swap", "no identity drift"],
        "reinforce": ["以定妆脸 image2image 派生（非纯文生图）", "提高脸锚参考强度", "锁脸型/五官比例/发型发饰"],
        "raise_face_anchor": True, "force_image2image": True,
    },
    "text2img": {
        "label": "纯文生图脱参考",
        "negatives": ["不要纯文生图", "no text-to-image from scratch"],
        "reinforce": ["必须以同 Clip 首帧/定妆库 image2image 派生", "注入 source_frame 参考"],
        "force_image2image": True,
    },
    "seam_break": {
        "label": "接缝断/姿态跳",
        "negatives": ["不要姿态突变", "不要光线跳变", "no pose jump"],
        "reinforce": ["以相邻帧 image2image 接力", "对齐构图/光位/人物状态到相邻帧"],
        "force_image2image": True,
    },
    "hands": {
        "label": "崩手/多指",
        "negatives": ["不要多指", "不要畸形手", "no extra fingers", "no malformed hands"],
        "reinforce": ["手部清晰、五指正常", "必要时遮挡或避开手部特写"],
    },
    "composition": {
        "label": "构图/景别偏",
        "negatives": ["不要主体出框", "不要构图失衡"],
        "reinforce": ["按分镜景别与构图意图", "主体居正确画域、留运镜余量"],
    },
}
# 失败信号 → 失败模式键（解析候选 sidecar 里的硬伤原因文本/码；中英文都认）。
FAIL_KEYWORDS: Dict[str, Sequence[str]] = {
    "face_drift": ("崩脸", "换脸", "脸漂", "face_drift", "faceswap", "face swap", "identity"),
    "text2img": ("纯文生图", "text2img", "txt2img", "文生", "from scratch"),
    "seam_break": ("接缝", "seam", "姿态跳", "闪烁", "flicker"),
    "hands": ("崩手", "多指", "畸形手", "hand", "finger"),
    "composition": ("构图", "出框", "composition", "crop"),
}


def _fail_reason_text(cand: Mapping[str, Any]) -> str:
    """把候选上可能记录失败原因的字段拼成一段可检索文本（小写）。纯函数。"""
    parts: List[str] = []
    for k in ("qc_hard_fail", "qc_fail_reason", "fail_reason", "reason"):
        v = cand.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        elif isinstance(v, dict):
            parts.extend(f"{kk} {vv}" for kk, vv in v.items())
    for k in ("fail_codes", "qc_codes", "codes"):
        v = cand.get(k)
        if isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
    return " ".join(parts).lower()


def classify_failures(cands: Sequence[Dict[str, Any]],
                      identity_floor: float = IDENTITY_FLOOR) -> Dict[str, int]:
    """统计 N 张候选里各失败模式命中数（从已采信号推导·确定性）。纯函数。"""
    counts = {k: 0 for k in FAILURE_CORRECTIONS}
    for c in cands:
        text = _fail_reason_text(c)
        matched = False
        for key, kws in FAIL_KEYWORDS.items():
            if any(kw.lower() in text for kw in kws):
                counts[key] += 1
                matched = True
        face = c.get("face_consistency")
        if isinstance(face, (int, float)) and float(face) < identity_floor:
            if "face" not in text and "崩脸" not in text and "换脸" not in text:
                counts["face_drift"] += 1
            matched = True
        if not matched and c.get("qc_hard_fail"):
            # 硬伤但无可解析原因 → 最常见根因是脸漂，保守归 face_drift。
            counts["face_drift"] += 1
    return {k: v for k, v in counts.items() if v > 0}


def corrective_prescription(cands: Sequence[Dict[str, Any]],
                            identity_floor: float = IDENTITY_FLOOR) -> Optional[Dict[str, Any]]:
    """从失败分布生成负权纠偏处方（喂给 runner 下一轮生成）。无可解析失败信号→None。纯函数。

    返回 {dominant, failure_counts, negatives, reinforce, raise_face_anchor, force_image2image, reason}。"""
    counts = classify_failures(cands, identity_floor)
    if not counts:
        return None
    dominant = sorted(counts, key=lambda k: (counts[k], k), reverse=True)
    negatives: List[str] = []
    reinforce: List[str] = []
    raise_face = force_i2i = False
    for key in dominant:
        spec = FAILURE_CORRECTIONS[key]
        for t in spec["negatives"]:
            if t not in negatives:
                negatives.append(t)
        for t in spec["reinforce"]:
            if t not in reinforce:
                reinforce.append(t)
        raise_face = raise_face or bool(spec.get("raise_face_anchor"))
        force_i2i = force_i2i or bool(spec.get("force_image2image"))
    dist = "；".join(f"{FAILURE_CORRECTIONS[k]['label']}×{counts[k]}" for k in dominant)
    return {
        "dominant": dominant, "failure_counts": counts,
        "negatives": negatives, "reinforce": reinforce,
        "raise_face_anchor": raise_face, "force_image2image": force_i2i,
        "reason": f"上一轮失败分布：{dist}（负权纠偏后重生成·非简单 best-of-N 抽卡）",
    }


# ── 可用率（yield）：逐镜 + 集级汇总 + 滚动账本（纯函数 + I/O 分离）─────────────────────

def shot_yield(res: Mapping[str, Any]) -> Dict[str, Any]:
    """单镜可用率：survivors/candidate_count = 过硬地板的比例；usable_pick=是否拿到可落档终选。纯函数。"""
    n = int(res.get("candidate_count") or 0)
    surv = int(res.get("survivors") or 0)
    usable = 1 if (res.get("picked") and not res.get("reroll_needed")) else 0
    return {
        "candidate_count": n, "survivors": surv, "usable_pick": usable,
        "shot_yield": round(surv / n, 4) if n else 0.0,
        "reroll_needed": bool(res.get("reroll_needed")),
    }


def aggregate_yield(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """集级可用率汇总（usable_yield=过硬地板/总生成；resolution_rate=拿到终选的镜比例）。纯函数。"""
    total_c = sum(int(r.get("candidate_count") or 0) for r in rows)
    total_s = sum(int(r.get("survivors") or 0) for r in rows)
    resolved = sum(1 for r in rows if r.get("picked") and not r.get("reroll_needed"))
    reroll = sum(1 for r in rows if r.get("reroll_needed"))
    clips = len(rows)
    return {
        "clips": clips, "total_candidates": total_c, "total_survivors": total_s,
        "usable_yield": round(total_s / total_c, 4) if total_c else 0.0,
        "resolved_clips": resolved, "reroll_clips": reroll,
        "resolution_rate": round(resolved / clips, 4) if clips else 0.0,
    }


def rolling_yield_from_events(events: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """从账本全部事件重算滚动可用率（跨集/跨轮）。纯函数·可测。"""
    total_c = sum(int(e.get("candidate_count") or 0) for e in events)
    total_s = sum(int(e.get("survivors") or 0) for e in events)
    rounds = len(events)
    rerolls = sum(1 for e in events if e.get("reroll_needed"))
    return {
        "rounds": rounds, "total_candidates": total_c, "total_survivors": total_s,
        "usable_yield": round(total_s / total_c, 4) if total_c else 0.0,
        "reroll_rounds": rerolls,
        "reroll_rate": round(rerolls / rounds, 4) if rounds else 0.0,
    }


def select_best(cands: Sequence[Dict[str, Any]], *,
                vlm_compare: Optional[Callable[[Dict[str, Any], Dict[str, Any]], str]] = None,
                identity_floor: float = IDENTITY_FLOOR) -> Dict[str, Any]:
    """对一个镜头的候选排序选片 + reroll 决策。纯函数·report-only（不落盘、不拷文件）。

    返回 {ranked, picked, reroll_needed, reason, method, survivors, disqualified}。"""
    cands = [dict(c) for c in cands]
    if not cands:
        return {"ranked": [], "picked": None, "reroll_needed": True,
                "reason": "无候选图", "method": "none", "survivors": 0, "disqualified": 0,
                "corrective": None}
    ranked = deterministic_rank(cands)
    survivors = [c for c in ranked if not c.get("qc_hard_fail")]
    disq = len(cands) - len(survivors)
    if not survivors:
        return {"ranked": ranked, "picked": None, "reroll_needed": True,
                "reason": f"全部 {len(cands)} 张候选都有 QC 硬伤（崩脸/纯文生图/接缝断）→ 整镜 reroll",
                "method": "deterministic", "survivors": 0, "disqualified": disq,
                "corrective": corrective_prescription(cands, identity_floor)}
    if vlm_compare is not None and len(survivors) > 1:
        picked = vlm_champion(survivors, vlm_compare)
        method = "vlm_ranker"
    else:
        picked = survivors[0]
        method = "deterministic"
    face = picked.get("face_consistency")
    reroll = isinstance(face, (int, float)) and float(face) < identity_floor
    reason = ("选出最优候选" if not reroll
              else f"最优候选 face 余弦 {float(face):.3f} < 地板 {identity_floor:.2f}（最好的也崩脸）→ reroll")
    # 纠偏处方只在 reroll 时给（按全部候选的失败分布·含被淘汰者）；非 reroll 时为 None。
    return {"ranked": ranked, "picked": picked, "reroll_needed": bool(reroll),
            "reason": reason, "method": method, "survivors": len(survivors), "disqualified": disq,
            "corrective": corrective_prescription(cands, identity_floor) if reroll else None}


# ── VLM ranker 适配（厂商无关·N2D_VLM_COMPARE_CMD）────────────────────────────────

COMPARE_PROMPT = ("你是漫剧出图选片助手。比较 A、B 两张同一镜头候选图，哪张在【角色身份不崩脸、贴合分镜"
                  "意图、构图与画质】上整体更好？只回 JSON：{\"winner\":\"a\"} 或 {\"winner\":\"b\"} 或 "
                  "{\"winner\":\"tie\"}。不要解释。")


def make_vlm_compare() -> Optional[Callable[[Dict[str, Any], Dict[str, Any]], str]]:
    """从 `N2D_VLM_COMPARE_CMD` 构造成对比较器；未配置→None（降级确定性）。

    模板占位 {image_a} {image_b} {prompt}（路径/prompt 经 shell-quote）；stdout 回 {"winner":"a"|"b"|"tie"}。
    例：export N2D_VLM_COMPARE_CMD='python3 ~/bin/vlm_pair.py --a {image_a} --b {image_b} --q {prompt}'"""
    tmpl = os.environ.get("N2D_VLM_COMPARE_CMD", "").strip()
    if not tmpl or "{image_a}" not in tmpl or "{image_b}" not in tmpl:
        return None

    def compare(a: Dict[str, Any], b: Dict[str, Any]) -> str:
        pa, pb = str(a.get("path") or ""), str(b.get("path") or "")
        if not (pa and pb and os.path.exists(pa) and os.path.exists(pb)):
            return "tie"
        cmd = tmpl.replace("{image_a}", shlex.quote(pa)).replace("{image_b}", shlex.quote(pb))
        if "{prompt}" in cmd:
            cmd = cmd.replace("{prompt}", shlex.quote(COMPARE_PROMPT))
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
            data = json.loads(res.stdout or "{}")
            w = str(data.get("winner") or "").strip().lower()
            return w if w in {"a", "b", "tie"} else "tie"
        except Exception:
            return "tie"

    return compare


# ── 信号采集（确定性·优雅降级）──────────────────────────────────────────────────

def _sharpness(png: str) -> Optional[float]:
    """归一化清晰度代理（梯度能量·Pillow 纯实现，无 cv2 依赖）；失败→None。"""
    try:
        from PIL import Image
        im = Image.open(png).convert("L")
        im.thumbnail((256, 256))
        flattened = getattr(im, "get_flattened_data", None)
        px = list(flattened() if callable(flattened) else im.getdata())
        w = im.width
        if w < 2 or len(px) < w * 2:
            return None
        total, n = 0, 0
        for y in range(im.height - 1):
            row = y * w
            for x in range(w - 1):
                i = row + x
                gx = px[i] - px[i + 1]
                gy = px[i] - px[i + w]
                total += gx * gx + gy * gy
                n += 1
        return round((total / n) / 6000.0, 4) if n else None  # 经验归一到 ~0-1
    except Exception:
        return None


def gather_candidate(png: str, root: str) -> Dict[str, Any]:
    """采一张候选的确定性信号：旁车 JSON（face_consistency/composition/qc_hard_fail…·沿用 候选 sidecar 约定）
    + 自动清晰度。绝不臆造缺失信号。"""
    cand: Dict[str, Any] = {"path": png, "candidate": Path(png).stem,
                            "rel": os.path.relpath(png, root)}
    sidecar = os.path.splitext(png)[0] + ".json"
    if os.path.isfile(sidecar):
        try:
            data = json.loads(Path(sidecar).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # 选片信号 + 失败原因（后者喂 Genflow 纠偏处方·classify_failures 用）。
                for k in ("face_consistency", "composition", "hook_strength", "style_match",
                          "asset_consistency", "qc_hard_fail",
                          "qc_fail_reason", "fail_reason", "reason",
                          "fail_codes", "qc_codes", "codes",
                          "source_target", "source_prompt_shot",
                          "target", "target_path", "output_path"):
                    if k in data:
                        cand[k] = data[k]
        except Exception:
            pass
    sh = _sharpness(png)
    if sh is not None:
        cand["sharpness"] = sh
    return cand


def candidate_dir(root: str, ep: str, clip: str) -> str:
    return os.path.join(root, "出图", ep, "候选", clip)


def list_clips(root: str, ep: str) -> List[str]:
    base = os.path.join(root, "出图", ep, "候选")
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _production_events_path(root: str) -> str:
    return os.path.join(root, "生产数据", "production_events.jsonl")


def _read_production_events(root: str) -> List[Dict[str, Any]]:
    path = _production_events_path(root)
    if not os.path.isfile(path):
        return []
    events: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _event_status_pass(event: Mapping[str, Any]) -> bool:
    generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    status = str(generation.get("status") or event.get("status") or "").strip().lower()
    return status in {"", "pass", "passed", "ok", "success", "succeeded", "done", "ready"}


def _source_generation_event(root: str, candidate_rel: str) -> Optional[Dict[str, Any]]:
    """Return latest pass generation/redraw event for the selected candidate image."""
    latest: Optional[Dict[str, Any]] = None
    for event in _read_production_events(root):
        if str(event.get("stage") or "") != "image":
            continue
        if str(event.get("event") or "") not in {"generation", "redraw"}:
            continue
        generation = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
        if generation.get("asset") != candidate_rel:
            continue
        if not _event_status_pass(event):
            continue
        latest = dict(event)
    return latest


def record_promotion_event(root: str, ep: str, picked: Mapping[str, Any], dst_rel: str) -> bool:
    """Write a production event for a selected candidate copied into its final frame path.

    The generated pixels were already paid for and recorded against the candidate path.  This event
    promotes that evidence to the final PNG, preserving the original model/reference recipe while
    marking the operation as a candidate selection copy rather than a fresh generation.
    """
    src = str(picked.get("path") or "")
    candidate_rel = str(picked.get("rel") or (os.path.relpath(src, root) if src else "")).strip()
    if not candidate_rel:
        return False
    source_event = _source_generation_event(root, candidate_rel)
    if not source_event:
        return False
    generation = dict(source_event.get("generation") if isinstance(source_event.get("generation"), Mapping) else {})
    meta = dict(source_event.get("meta") if isinstance(source_event.get("meta"), Mapping) else {})
    dst_abs = os.path.join(root, dst_rel)
    if not os.path.isfile(dst_abs):
        return False
    artifact_sha = _sha256_file(dst_abs)
    source_candidate_sha = _sha256_file(src) if src and os.path.isfile(src) else ""
    source_recipe = str(meta.get("recipe_hash") or "")
    input_fingerprint = _sha256_text(json.dumps({
        "artifact_sha256": artifact_sha,
        "dst": dst_rel,
        "promotion_method": "candidate_select_apply",
        "source_candidate": candidate_rel,
        "source_candidate_sha256": source_candidate_sha,
        "source_recipe_hash": source_recipe,
    }, ensure_ascii=False, sort_keys=True))
    meta.update({
        "artifact_sha256": artifact_sha,
        "candidate_select_version": str(VERSION),
        "input_fingerprint": input_fingerprint,
        "promoted_from": candidate_rel,
        "promotion_method": "candidate_select_apply",
        "recipe_hash": _sha256_text(json.dumps({
            "artifact_sha256": artifact_sha,
            "input_fingerprint": input_fingerprint,
            "promotion_method": "candidate_select_apply",
            "source_recipe_hash": source_recipe,
        }, ensure_ascii=False, sort_keys=True)),
        "source_candidate_sha256": source_candidate_sha,
    })
    generation.update({
        "asset": dst_rel,
        "status": "pass",
    })
    promoted = {
        "duration_sec": 0.0,
        "episode": ep,
        "event": "generation",
        "generation": generation,
        "kind": "n2d_production_event",
        "meta": meta,
        "source": "skills/n2d-image/scripts/candidate_select.py",
        "stage": "image",
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "version": 1,
    }
    out = _production_events_path(root)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(promoted, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def select_clip(root: str, ep: str, clip: str,
                vlm_compare: Optional[Callable] = None) -> Dict[str, Any]:
    cdir = candidate_dir(root, ep, clip)
    pngs = sorted(glob.glob(os.path.join(cdir, "*.png")))
    cands = [gather_candidate(p, root) for p in pngs]
    res = select_best(cands, vlm_compare=vlm_compare)
    res["clip"] = clip
    res["candidate_count"] = len(cands)
    return res


def _safe_target_path(root: str, ep: str, picked: Mapping[str, Any]) -> Optional[str]:
    """从候选 sidecar 的目标路径提示解析安全落档路径。

    只接受当前集 `出图/<ep>/图片/*.png` 下的目标，防止旁车误写或越界路径污染其它资产。
    """
    root_abs = os.path.abspath(root)
    allowed_dir = os.path.abspath(os.path.join(root_abs, "出图", ep, "图片"))
    for key in TARGET_HINT_KEYS:
        raw = picked.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        raw = raw.strip()
        dst = raw if os.path.isabs(raw) else os.path.join(root_abs, raw)
        dst_abs = os.path.abspath(os.path.normpath(dst))
        try:
            common = os.path.commonpath([allowed_dir, dst_abs])
        except ValueError:
            continue
        if common != allowed_dir:
            continue
        if not dst_abs.lower().endswith(".png"):
            continue
        return dst_abs
    return None


def apply_pick(root: str, ep: str, clip: str, picked: Mapping[str, Any]) -> Optional[str]:
    """把选中候选拷到落档路径。

    keyshot runner 的候选旁车会声明 `source_target`（真实分镜目标，如 Clip01_first.png）；
    普通候选没有目标提示时，回退到旧路径 `出图/<ep>/图片/<clip>.png`。
    """
    src = str(picked.get("path") or "")
    if not src or not os.path.isfile(src):
        return None
    dst_dir = os.path.join(root, "出图", ep, "图片")
    os.makedirs(dst_dir, exist_ok=True)
    dst = _safe_target_path(root, ep, picked) or os.path.join(dst_dir, f"{clip}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    dst_rel = os.path.relpath(dst, root)
    record_promotion_event(root, ep, picked, dst_rel)
    return dst_rel


def _apply_interlock_targets(root: str, ep: str, rows: Sequence[Mapping[str, Any]]) -> List[Any]:
    """Resolve selected candidate rows back to their real Clip targets.

    The candidate sidecar written by keyshot_candidate_runner carries the
    source prompt shot.  Legacy candidates may not; for those, fall back to the
    clip id.  An unresolved row intentionally returns an empty list so the
    caller can run the whole-episode shared-first scan rather than silently
    waive it.
    """
    requested: List[str] = []
    for row in rows:
        picked = row.get("picked") if isinstance(row.get("picked"), Mapping) else {}
        value = str(picked.get("source_prompt_shot") or row.get("clip") or "").strip()
        if value:
            requested.append(value)
    if not requested:
        return []
    try:
        return list(cir.build_targets(Path(root), ep, requested))
    except Exception:
        return []


def enforce_apply_shared_first(root: str, ep: str, rows: Sequence[Mapping[str, Any]]) -> bool:
    """Non-waivable shared-first lock before a candidate becomes a live frame."""
    targets = _apply_interlock_targets(root, ep, rows)
    return cir.enforce_shared_first_interlock(
        Path(root), ep, targets=targets or None
    )


def build_report(root: str, ep: str, only_clip: Optional[str] = None) -> Dict[str, Any]:
    vlm = make_vlm_compare()
    clips = [only_clip] if only_clip else list_clips(root, ep)
    rows = [select_clip(root, ep, c, vlm_compare=vlm) for c in clips if c]
    for r in rows:
        r["yield"] = shot_yield(r)
    reroll = [r["clip"] for r in rows if r.get("reroll_needed")]
    return {
        "kind": KIND, "version": VERSION, "episode": ep,
        "vlm_ranker": vlm is not None,
        "clips_selected": len(rows),
        "reroll_clips": reroll,
        "yield": aggregate_yield(rows),
        "rows": rows,
        "notes": ([] if vlm is not None else
                  ["未配置 N2D_VLM_COMPARE_CMD：用确定性排序（face 余弦→QC→清晰度）选片；"
                   "配置厂商无关成对比较器可启用 VLM ranker（成对·非绝对打分）。"]),
    }


YIELD_LEDGER = "yield_ledger.jsonl"
YIELD_SUMMARY = "yield_summary.json"
YIELD_EVENT_KIND = "n2d_yield_event"


def _read_yield_events(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if isinstance(e, dict) and e.get("kind") == YIELD_EVENT_KIND:
                out.append(e)
    return out


def append_yield_ledger(root: str, ep: str, rows: Sequence[Mapping[str, Any]],
                        *, now: Optional[str] = None) -> Optional[str]:
    """把逐镜可用率事件追加到 生产数据/yield_ledger.jsonl，并重算滚动汇总 yield_summary.json。

    每次跑 = 一轮测量；reroll 后再跑即记新一轮事件（round 按 (集,镜) 历史计数 +1），
    可用率随纠偏回升可见。返回账本路径（无可记行 → None）。I/O 层（pure 部分见 *_yield 函数）。"""
    rows = [r for r in rows if int(r.get("candidate_count") or 0) > 0]
    if not rows:
        return None
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, YIELD_LEDGER)
    prior = _read_yield_events(path)
    round_of: Dict[str, int] = {}
    for e in prior:
        k = f"{e.get('episode')}/{e.get('clip')}"
        round_of[k] = max(round_of.get(k, 0), int(e.get("round") or 0))
    new_events: List[Dict[str, Any]] = []
    for r in rows:
        clip = r.get("clip")
        k = f"{ep}/{clip}"
        rnd = round_of.get(k, 0) + 1
        round_of[k] = rnd
        ev = {"kind": YIELD_EVENT_KIND, "episode": ep, "clip": clip, "round": rnd}
        ev.update(shot_yield(r))
        ev["had_corrective"] = bool(r.get("corrective"))
        if now:
            ev["at"] = now
        new_events.append(ev)
    with open(path, "a", encoding="utf-8") as fh:
        for ev in new_events:
            fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
    summary = rolling_yield_from_events(prior + new_events)
    summary["kind"] = "n2d_yield_summary"
    if now:
        summary["updated_at"] = now
    tmp = os.path.join(out_dir, YIELD_SUMMARY + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, os.path.join(out_dir, YIELD_SUMMARY))
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--clip", help="只选某一镜（默认全集所有候选镜）")
    ap.add_argument("--apply", action="store_true", help="把选中候选拷到落档路径（不可逆）")
    ap.add_argument("--no-ledger", action="store_true", help="不追加 yield_ledger.jsonl（默认追加可用率账本）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    report = build_report(root, ns.episode, ns.clip)
    applied = []
    if ns.apply:
        eligible = [r for r in report["rows"] if r.get("picked") and not r.get("reroll_needed")]
        if eligible and not enforce_apply_shared_first(root, ns.episode, eligible):
            report["apply_blocked"] = True
            report["apply_block_reason"] = (
                "shared-first interlock blocked; candidate was not copied into the live frame namespace"
            )
        else:
            for r in eligible:
                dst = apply_pick(root, ns.episode, r["clip"], r["picked"])
                if dst:
                    applied.append({"clip": r["clip"], "dst": dst})
        report["applied"] = applied
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    if not ns.no_ledger:
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        ledger = append_yield_ledger(root, ns.episode, report["rows"], now=now)
        if ledger:
            report["yield_ledger"] = os.path.relpath(ledger, root)
            report["yield_summary"] = rolling_yield_from_events(_read_yield_events(ledger))
    path = os.path.join(out_dir, f"candidate_selection_{ns.episode}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        y = report.get("yield") or {}
        print(f"候选选片 {ns.episode}：{report['clips_selected']} 镜，VLM ranker={report['vlm_ranker']}，"
              f"需 reroll {len(report['reroll_clips'])} 镜｜可用率 {y.get('usable_yield')}（终选率 {y.get('resolution_rate')}）")
        for r in report["rows"]:
            pick = (r.get("picked") or {}).get("candidate") if r.get("picked") else "—"
            flag = "🔁REROLL" if r.get("reroll_needed") else f"✅{pick}"
            print(f"  · {r['clip']}（{r['candidate_count']}选·{r['method']}）：{flag}　{r['reason']}")
            corr = r.get("corrective")
            if corr:
                print(f"      ↳ 纠偏处方：{corr['reason']}")
                print(f"        negatives: {('、'.join(corr['negatives'][:6]))}")
                print(f"        reinforce: {('、'.join(corr['reinforce'][:5]))}"
                      + ("｜提脸锚强度" if corr.get("raise_face_anchor") else "")
                      + ("｜强制 image2image" if corr.get("force_image2image") else ""))
        if report.get("yield_summary"):
            ys = report["yield_summary"]
            print(f"  滚动可用率账本：{ys.get('rounds')} 轮，累计可用率 {ys.get('usable_yield')}，"
                  f"reroll 轮占比 {ys.get('reroll_rate')} → {report.get('yield_ledger')}")
        if ns.apply:
            print(f"  已落档 {len(applied)} 镜")
    # Ranking remains report-only.  --apply is a mutating production action;
    # refusing it on the non-waivable shared-first lock must be visible to
    # batch callers as a non-zero exit.
    return 1 if report.get("apply_blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
