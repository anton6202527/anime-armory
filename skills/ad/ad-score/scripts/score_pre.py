#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 投放前 pre-spend 目标化创意诊断。

本脚本实现「廉价确定性 prescore + LLM 语义分 → 阈值三档决策 + 受影响项回流」
闭环，判据全部围绕广告特有场景，且 **ad 线自包含（纯标准库）**。

为什么在出图前评分：广告一条主片就是全部产出，正式出图/出视频一旦开跑即烧积分；用脚本+分镜阶段
已有的确定性产物先拦平庸 ROI（钩子塌、卖点糊、CTA 弱、品牌露出不足、广告法 block、时长超标），
比出完片再靠 ad-review 发现省得多。

混合模型：
  1) 确定性 prescore（本脚本算，不要 LLM）——读 ad-script/ad-voice 已有产物：
     · 广告法风险（脚本/广告法机检报告.json 的 block/warn）——**任一 block = 硬地板，强制阻断**；
     · 品牌露出充分度（storyboard 里带产品/logo/品牌/CTA/legal 的镜数占比 vs brief mandatories）；
     · 时长贴合（脚本/镜头时长.json 实测总时长 vs 主片目标，广告总时长是硬约束）；
     · CTA 存在（有无 end card/CTA 镜 + brief CTA mandatory 落镜）；
     · 钩子前 3s（首镜/0-3s 段是否钩子镜，非缓起势空镜——半确定性关键词初筛）。
  2) LLM 语义分（--dim 名=分 传入，由调用方 LLM 判）——钩子吸引力/卖点清晰度/CTA 说服力等。
  3) 阈值三档（--threshold）：≥阈值=go；次档=revise；其下=reject 建议。只有广告法硬地板阻断。
     低分维度按成因映射回 ad-concept / ad-script / ad-image，产 affected_items 回流清单；
     --enqueue 落一份 ad 自有格式的返工清单文件（不引用别线 batch）。

用法：
    python3 score_pre.py <作品根> [--master 30s] [--threshold 80] \
        [--dim 钩子吸引力=72] [--dim 卖点清晰度=80] [--enqueue] [--json 评分/ad_score.json]
退出码：0=评分建议（含 revise/reject）；1=广告法硬地板；2=输入缺失/损坏。
"""
import argparse
import json
import os
import re
import sys

AD_SCORE_KIND = "ad_score"
REWORK_QUEUE_KIND = "ad_score_rework_queue"

# 三档边界（百分制）。可被 --threshold 覆盖上档线；revise 下档线 = 上档线 - REVISE_BAND。
DEFAULT_THRESHOLD = 80
REVISE_BAND = 20  # [threshold-REVISE_BAND, threshold) = revise；其下 = reject

# 确定性维度权重（和为 1.0）。LLM 维度另算，二者按 DET_WEIGHT/LLM_WEIGHT 合成总分。
DET_DIM_WEIGHTS = {
    "adlaw": 0.25,          # 广告法风险（block 直接硬地板，这里的分只反映 warn 扣分）
    "brand_exposure": 0.20,  # 品牌/产品/logo 露出充分度
    "first_3s_brand_product": 0.15,  # 信息流前三秒是否已出现品牌/产品
    "duration_fit": 0.15,    # 总时长贴合主片目标
    "cta_present": 0.15,     # CTA/end card 落镜
    "hook": 0.10,            # 钩子前 3s（半确定性）
}
OBJECTIVE_WEIGHTS = {
    "品牌认知": {"adlaw": .25, "brand_exposure": .25, "first_3s_brand_product": .10,
             "duration_fit": .15, "cta_present": .05, "hook": .20},
    "考虑种草": {"adlaw": .25, "brand_exposure": .20, "first_3s_brand_product": .10,
             "duration_fit": .15, "cta_present": .10, "hook": .20},
    "转化行动": {"adlaw": .25, "brand_exposure": .15, "first_3s_brand_product": .20,
             "duration_fit": .15, "cta_present": .20, "hook": .05},
    "全链路": DET_DIM_WEIGHTS,
}
DET_WEIGHT = 0.6   # 确定性 prescore 占总分
LLM_WEIGHT = 0.4   # LLM 语义分占总分（无 --dim 时总分 = 确定性分）

# LLM 语义维度名 → 回流 stage（成因映射）。名字做模糊包含匹配，容中英/近义。
LLM_DIM_STAGE = [
    (("钩子", "hook", "开场", "前3", "前三"), "ad-concept"),
    (("卖点", "usp", "利益点", "信息"), "ad-script"),
    (("cta", "行动", "号召", "转化"), "ad-concept"),
    (("品牌", "brand", "调性", "logo"), "ad-image"),
]

BRAND_TOKENS = ("logo", "品牌", "包装", "slogan", "口号", "cta", "产品", "product", "brand")
HOOK_TOKENS = ("钩子", "hook", "悬念", "冲突", "痛点", "反转", "提问", "数字", "对比", "before")
SLOW_OPEN_TOKENS = ("空镜", "缓起", "establishing", "氛围铺垫", "logo 开场", "片头板")
CTA_TOKENS = ("cta", "end card", "endcard", "片尾", "立即", "扫码", "购买", "下单", "关注", "搜索", "行动")


# ── IO ────────────────────────────────────────────────────────────────────
def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def parse_seconds(value):
    """'30s' / '30' / 30 → 30.0；解析不出 → 0.0。纯函数。"""
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group(0)) if m else 0.0


def _shots(storyboard):
    if not isinstance(storyboard, dict):
        return []
    return storyboard.get("shots") or storyboard.get("clips") or []


def _shot_text(shot):
    if not isinstance(shot, dict):
        return ""
    parts = []
    for k in ("section", "scene", "frame", "label", "title", "shot", "prompt",
              "product_lock", "desc", "description", "camera", "镜头",
              "字幕", "subtitle", "vo", "旁白"):
        v = shot.get(k)
        if isinstance(v, str):
            parts.append(v)
    legal = shot.get("legal_lines")
    if isinstance(legal, list):
        parts.extend(str(x) for x in legal)
    assets = shot.get("assets")
    if isinstance(assets, dict):
        parts.extend(str(k) for k, v in assets.items() if v)
    return " ".join(parts).lower()


def _shot_has_prod_asset(shot):
    assets = shot.get("assets") if isinstance(shot, dict) else None
    if not isinstance(assets, dict):
        return False
    return any(k.startswith("PROD_") and v for k, v in assets.items())


def _shot_has_brand_asset(shot):
    assets = shot.get("assets") if isinstance(shot, dict) else None
    if not isinstance(assets, dict):
        return False
    return any(k.startswith("BRAND_") and v for k, v in assets.items())


# ── 确定性子维度（纯函数·可测）────────────────────────────────────────────────
def adlaw_score(report):
    """广告法机检报告 → (sub_score_0_100, block_count, warn_count, hard_block)。

    任一 block = hard_block=True（违禁词不可投放，强制阻断，与分数无关）；
    sub_score 仅反映 warn 扣分（每条 warn 扣 8 分，地板 0）。报告缺失 → 视为 0 风险但标记 unknown。"""
    if not isinstance(report, dict):
        return 100.0, 0, 0, False
    summary = report.get("summary") or {}
    block = int(summary.get("block") or 0)
    warn = int(summary.get("warn") or 0)
    hard_block = block > 0
    score = max(0.0, 100.0 - warn * 8.0)
    return score, block, warn, hard_block


def brand_exposure_score(storyboard):
    """带品牌/产品/logo/CTA 露出的镜数占比 → 0-100。无镜 → 0。纯函数。

    甜点区间：露出占比 25%~70% 给满分（太少=品牌记不住，太多=像产品说明书招人烦）。"""
    shots = _shots(storyboard)
    if not shots:
        return 0.0, 0, 0
    brand_shots = 0
    for s in shots:
        if _shot_has_prod_asset(s) or _shot_has_brand_asset(s) or any(t in _shot_text(s) for t in BRAND_TOKENS):
            brand_shots += 1
    ratio = brand_shots / len(shots)
    if 0.25 <= ratio <= 0.70:
        score = 100.0
    elif ratio < 0.25:
        score = max(0.0, ratio / 0.25 * 100.0)
    else:  # 露出过载；产品 demo/App 首发常需持续露出，缓扣不打成低分。
        score = max(70.0, 100.0 - (ratio - 0.70) / 0.30 * 30.0)
    return round(score, 1), brand_shots, len(shots)


def duration_fit_score(actual_sec, target_sec):
    """实测总时长 vs 主片目标 → 0-100。广告总时长是硬约束，偏差越大越扣。纯函数。

    ≤2% 偏差满分；之后线性扣到 0（偏差 ≥25% 记 0）。target 缺失 → 100（不评，避免误杀）。"""
    if not target_sec:
        return 100.0, 0.0
    if not actual_sec:
        return 0.0, 1.0
    dev = abs(actual_sec - target_sec) / target_sec
    if dev <= 0.02:
        return 100.0, round(dev, 3)
    score = max(0.0, 100.0 - (dev - 0.02) / 0.23 * 100.0)
    return round(score, 1), round(dev, 3)


def _mandatory_texts(mandatories):
    if isinstance(mandatories, dict):
        out = []
        for key, value in mandatories.items():
            out.append(str(key))
            if isinstance(value, (list, tuple)):
                out.extend(str(v) for v in value)
            else:
                out.append(str(value))
        return out
    if isinstance(mandatories, (list, tuple)):
        return [str(v) for v in mandatories]
    return [str(mandatories)] if mandatories else []


def cta_score(storyboard, mandatories):
    """有无 CTA/end card 镜 + brief CTA mandatory 落镜 → 0-100。纯函数。"""
    shots = _shots(storyboard)
    has_cta_shot = any(any(t in _shot_text(s) for t in CTA_TOKENS) for s in shots)
    mandatory_text = " ".join(_mandatory_texts(mandatories)).lower()
    wants_cta = bool(mandatory_text) and any(
        t in mandatory_text for t in ("cta", "行动", "号召", "购买", "下单", "关注", "预约", "endcard_cta"))
    if not wants_cta:
        return (100.0 if has_cta_shot else 70.0)  # brief 没强制 CTA：有更好，无不重罚
    return 100.0 if has_cta_shot else 0.0          # brief 强制 CTA 却没落镜 = 0


def first_3s_brand_product_score(storyboard):
    """前三秒是否出现品牌/产品/CTA。信息流广告不能把产品藏到后面。纯函数。"""
    shots = _shots(storyboard)
    if not shots:
        return 0.0, []
    elapsed = 0.0
    checked = []
    for idx, shot in enumerate(shots, 1):
        text = _shot_text(shot)
        has_identity = (
            _shot_has_prod_asset(shot)
            or _shot_has_brand_asset(shot)
            or any(t in text for t in BRAND_TOKENS)
        )
        checked.append({"index": idx, "has_identity": has_identity})
        if has_identity:
            return 100.0, checked
        dur = 0.0
        for key in ("duration", "时长", "duration_sec", "seconds"):
            if isinstance(shot, dict) and shot.get(key) is not None:
                dur = parse_seconds(shot.get(key))
                break
        elapsed += dur or 3.0
        if elapsed >= 3.0:
            break
    return 0.0, checked


def hook_score(storyboard):
    """首镜（0-3s）是否钩子镜 → 0-100。半确定性关键词初筛（LLM 维度再细判）。纯函数。"""
    shots = _shots(storyboard)
    if not shots:
        return 0.0
    first = _shot_text(shots[0])
    if any(t in first for t in HOOK_TOKENS):
        return 100.0
    if any(t in first for t in SLOW_OPEN_TOKENS):
        return 30.0   # 缓起势/logo 开场——信息流前 3s 易被划走
    return 60.0       # 中性：无明显钩子也无明显缓起，交 LLM 维度细判


def compute_prescore(brief, adlaw_report, storyboard, duration_report, target_sec):
    """汇总确定性子维度 → {dims, det_score, hard_block, facts}。纯函数·可测。"""
    mandatories = []
    if isinstance(brief, dict):
        m = brief.get("mandatories") or brief.get("强制项") or []
        if isinstance(m, (list, dict)):
            mandatories = m
    adlaw, block, warn, hard_block = adlaw_score(adlaw_report)
    brand, brand_shots, total_shots = brand_exposure_score(storyboard)
    first3, first3_checked = first_3s_brand_product_score(storyboard)
    actual_sec = parse_seconds((duration_report or {}).get("total_seconds") if isinstance(duration_report, dict) else 0) \
        or _sum_shot_durations(storyboard)
    dur, dev = duration_fit_score(actual_sec, target_sec)
    cta = cta_score(storyboard, mandatories)
    hook = hook_score(storyboard)
    dims = {"adlaw": adlaw, "brand_exposure": brand, "first_3s_brand_product": first3, "duration_fit": dur,
            "cta_present": cta, "hook": hook}
    objective = str((brief or {}).get("campaign_objective") or "全链路") if isinstance(brief, dict) else "全链路"
    weights = OBJECTIVE_WEIGHTS.get(objective, DET_DIM_WEIGHTS)
    det_score = round(sum(dims[k] * weights[k] for k in weights), 1)
    return {
        "dims": dims,
        "det_score": det_score,
        "hard_block": hard_block,
        "facts": {"adlaw_block": block, "adlaw_warn": warn, "brand_shots": brand_shots,
                  "total_shots": total_shots, "actual_seconds": round(actual_sec, 2),
                  "target_seconds": target_sec, "duration_deviation": dev,
                  "first_3s_identity_checked": first3_checked, "campaign_objective": objective,
                  "weights": weights},
    }


def _sum_shot_durations(storyboard):
    total = 0.0
    for s in _shots(storyboard):
        for k in ("duration", "时长", "duration_sec", "seconds"):
            if isinstance(s, dict) and s.get(k) is not None:
                total += parse_seconds(s.get(k))
                break
    return total


# ── LLM 维度合成 + 回流映射（纯函数·可测）──────────────────────────────────────
def map_dim_stage(dim_name):
    """LLM 语义维度名 → 回流 stage（成因映射）。未知名 → ad-script（脚本是广告内容的源头）。"""
    low = str(dim_name or "").lower()
    for tokens, stage in LLM_DIM_STAGE:
        if any(t in low for t in tokens):
            return stage
    return "ad-script"


def combine_score(det_score, llm_dims):
    """确定性分 + LLM 维度均分 → 总分。无 LLM 维度时总分=确定性分。纯函数。"""
    if not llm_dims:
        return round(det_score, 1)
    llm_avg = sum(llm_dims.values()) / len(llm_dims)
    return round(det_score * DET_WEIGHT + llm_avg * LLM_WEIGHT, 1)


def decide_tier(total, hard_block, threshold):
    """总分 + 硬地板 + 阈值 → (tier, blocked, reasons)。纯函数·可测。

    hard_block（广告法 block）→ 永远 reject，与分数/阈值无关。threshold=None → 建议性（不阻断）。"""
    reasons = []
    if hard_block:
        reasons.append("广告法机检存在 block 违禁词——不可投放，强制退回 ad-script 改写")
        return "reject", True, reasons
    if threshold is None:
        return "advisory", False, ["未设 --threshold：建议性评分，不阻断"]
    if total >= threshold:
        return "go", False, [f"总分 {total} ≥ 阈值 {threshold}，可进入出图"]
    if total >= threshold - REVISE_BAND:
        reasons.append(f"总分 {total} 落在 [{threshold - REVISE_BAND}, {threshold}) 区间——局部改后重评")
        return "revise", False, reasons
    reasons.append(f"总分 {total} < {threshold - REVISE_BAND}——退回上游重做")
    return "reject", False, reasons


# 确定性低分维度 → 回流 stage（成因映射）。
DET_DIM_STAGE = {
    "adlaw": "ad-script",
    "brand_exposure": "ad-script",   # 露出不足/过载：改分镜/脚本镜头分配（缺产品镜也回 ad-image 补图，见下）
    "first_3s_brand_product": "ad-script",
    "duration_fit": "ad-script",     # 总时长超标：回 finalize_storyboard 重切镜头时长
    "cta_present": "ad-concept",     # CTA 缺失：创意层补 end card/行动号召
    "hook": "ad-concept",            # 钩子弱：创意层重设开场
}


def affected_items(prescore, llm_dims, threshold):
    """低分维度 → [{item, return_to_stage, reason, score}]。纯函数·可测。

    确定性维度低于 60 或 LLM 维度低于 max(60, threshold-REVISE_BAND) 视为低分需回流。
    硬地板（广告法 block）单列一条回 ad-script。"""
    items = []
    floor = 60 if threshold is None else max(60, threshold - REVISE_BAND)
    if prescore.get("hard_block"):
        items.append({"item": "广告法机检", "return_to_stage": "ad-script",
                      "reason": f"{prescore['facts'].get('adlaw_block', 0)} 个 block 违禁词必须改写", "score": 0})
    for name, sc in (prescore.get("dims") or {}).items():
        if name == "adlaw" and prescore.get("hard_block"):
            continue  # 已单列
        if sc < 60:
            it = {"item": name, "return_to_stage": DET_DIM_STAGE.get(name, "ad-script"),
                  "reason": f"确定性维度 {name} 分 {sc} 偏低", "score": sc}
            # 品牌露出不足且镜不足时也提示回 ad-image 补产品镜
            if name == "brand_exposure" and prescore["facts"].get("brand_shots", 0) == 0:
                it["return_to_stage"] = "ad-image"
                it["reason"] = "无任何产品/品牌露出镜——回 ad-image 补 hero/品牌镜并回 ad-script 落镜"
            items.append(it)
    for name, sc in (llm_dims or {}).items():
        if sc < floor:
            items.append({"item": name, "return_to_stage": map_dim_stage(name),
                          "reason": f"LLM 语义维度 {name} 分 {sc} 低于 {floor}", "score": sc})
    return items


# ── 装配 + 落档 ─────────────────────────────────────────────────────────────
def build_payload(root, master, threshold, llm_dims):
    target_sec = parse_seconds(master)
    brief = load_json(os.path.join(root, "需求", "brief.json")) \
        or load_json(os.path.join(root, "脚本", "brief.json")) or {}
    adlaw_report = load_json(os.path.join(root, "脚本", "广告法机检报告.json")) or {}
    storyboard = load_json(os.path.join(root, "脚本", "storyboard.json")) or {}
    duration_report = load_json(os.path.join(root, "脚本", "镜头时长.json")) or {}
    # 主片目标：CLI --master 优先，否则 brief.master_duration
    if not target_sec and isinstance(brief, dict):
        deliverables = brief.get("deliverables") if isinstance(brief.get("deliverables"), dict) else {}
        target_sec = parse_seconds(
            brief.get("master_duration")
            or brief.get("主片时长")
            or deliverables.get("master_duration")
        )
    prescore = compute_prescore(brief, adlaw_report, storyboard, duration_report, target_sec)
    total = combine_score(prescore["det_score"], llm_dims)
    tier, blocked, reasons = decide_tier(total, prescore["hard_block"], threshold)
    items = affected_items(prescore, llm_dims, threshold) if blocked or tier in ("revise", "reject") else []
    return {
        "schema_version": 1,
        "kind": AD_SCORE_KIND,
        "root": os.path.abspath(root),
        "master_target_seconds": target_sec,
        "threshold": threshold,
        "det_score": prescore["det_score"],
        "llm_dims": llm_dims,
        "total_score": total,
        "tier": tier,
        "blocked": blocked,
        "hard_block": prescore["hard_block"],
        "reasons": reasons,
        "dims": prescore["dims"],
        "facts": prescore["facts"],
        "affected_items": items,
    }


def write_enqueue(payload, root):
    """落 ad 自有格式返工清单（不引用别线 batch）。返回路径。"""
    out_dir = os.path.join(root, "评分")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "回流清单.json")
    by_stage = {}
    for it in payload.get("affected_items", []):
        by_stage.setdefault(it["return_to_stage"], []).append(it)
    queue = {"kind": REWORK_QUEUE_KIND, "tier": payload["tier"], "total_score": payload["total_score"],
             "by_stage": by_stage}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    return path


def parse_dims(dim_args):
    """['钩子=72', '卖点=80'] → {'钩子':72.0,...}。非法项忽略。纯函数。"""
    out = {}
    for raw in dim_args or []:
        if "=" not in raw:
            continue
        name, _, val = raw.partition("=")
        name = name.strip()
        m = re.search(r"-?\d+(?:\.\d+)?", val)
        if name and m:
            out[name] = float(m.group(0))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="拍广告 投放前 pre-spend 目标化创意诊断")
    ap.add_argument("project_root")
    ap.add_argument("--master", default=None, help="主片目标时长（如 30s）；缺省读 brief.master_duration")
    ap.add_argument("--threshold", type=float, default=None,
                    help="go 档线（百分制，默认建议性不阻断）；[阈值-20, 阈值)=revise，其下=reject")
    ap.add_argument("--dim", action="append", default=[],
                    help="LLM 语义维度分，可重复：--dim 钩子吸引力=72")
    ap.add_argument("--enqueue", action="store_true", help="落 评分/回流清单.json（ad 自有格式）")
    ap.add_argument("--json", default=None, help="评分产物路径（默认 评分/ad_score.json）")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"❌ 作品根不存在：{root}", file=sys.stderr)
        return 2
    # 至少要有 storyboard 或脚本产物才评得动
    if not (os.path.isfile(os.path.join(root, "脚本", "storyboard.json"))
            or os.path.isfile(os.path.join(root, "脚本", "广告法机检报告.json"))):
        print("❌ 缺 脚本/storyboard.json 与 脚本/广告法机检报告.json——先跑 ad-script", file=sys.stderr)
        return 2

    llm_dims = parse_dims(args.dim)
    payload = build_payload(root, args.master, args.threshold, llm_dims)
    out_json = args.json or os.path.join(root, "评分", "ad_score.json")
    os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    icon = {"go": "✅", "advisory": "ℹ️", "revise": "🟡", "reject": "🔴"}.get(payload["tier"], "")
    print(f"# 投放前评分  总分={payload['total_score']}  档={payload['tier']} {icon}  "
          f"(确定性={payload['det_score']}, 阈值={payload['threshold']})")
    print("维度：" + "  ".join(f"{k}={v}" for k, v in payload["dims"].items()))
    if llm_dims:
        print("LLM：" + "  ".join(f"{k}={v}" for k, v in llm_dims.items()))
    for r in payload["reasons"]:
        print(f"  · {r}")
    for it in payload["affected_items"]:
        print(f"  ↩ [{it['return_to_stage']}] {it['item']}：{it['reason']}")
    if args.enqueue and payload["affected_items"]:
        qp = write_enqueue(payload, root)
        print(f"  写回流清单 {qp}")
    print(f"wrote {out_json}")
    return 1 if payload["blocked"] else 0


if __name__ == "__main__":
    sys.exit(main())
