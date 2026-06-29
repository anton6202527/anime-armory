# -*- coding: utf-8 -*-
"""judge_protocol.py — LLM-as-judge 去偏协议的**确定性执行层**（不调用 LLM·只校验/聚合判官产物）。

研究背景：LitBench(arXiv 2507.00769·去偏人标创作评测基准)、dual-judge 降单模型偏、blind peer
review(arXiv 2601.08003) 一致表明 LLM 判官有系统偏差，最突出的是 **position bias**（偏好靠前
候选）与 **单模型偏**。本模块**不发起任何 LLM 调用**——判官在仓库外产出原始 verdict（成对优劣 /
量规分），本模块把"判官应当如何被使用"的去偏协议钉成可执行约束，校验通过才给可信结论。

去偏协议（每条不满足 → 该结论降为 tie/abstain/low_confidence，绝不当确定性门控·与 B10 一致）：
  1) position-swap 稳定：同一对候选在 (A,B) 与 (B,A) 两种顺序下判同一赢家，否则=位置偏→abstain。
  2) dual-judge 一致：≥2 个不同判官模型给同一结论才采纳，分歧→tie（需人判）。
  3) rubric-anchored：量规分按判官内 z 归一去掉判官宽严偏后再聚合；判官间高方差→标 low_confidence。

纯标准库·纯函数·可测：cd skills/novel/_lib && python3 -m pytest test_judge_protocol.py
"""
import statistics

TIE = "tie"
ABSTAIN = "abstain"
DEFAULT_VARIANCE_THRESHOLD = 1.0   # 量规分（同一 1–10 量纲）判官间 stdev 超此 → low_confidence


# ── 协议1：position-swap 稳定 ──────────────────────────────────────────────
def position_stable_winner(ab_winner, ba_winner):
    """单判官在两种呈现顺序下的稳定赢家。

    ab_winner = 顺序(A,B)下判的赢家实体；ba_winner = 顺序(B,A)下判的赢家实体。
    两次判同一实体 → 返回该实体（位置无关·可信）；否则 → None（位置偏·该判官此对作废）。"""
    a = (str(ab_winner).strip() if ab_winner is not None else "") or None
    b = (str(ba_winner).strip() if ba_winner is not None else "") or None
    if a and b and a == b:
        return a
    return None


# ── 协议2：dual-judge 一致 ────────────────────────────────────────────────
def pairwise_consensus(judgements, min_judges=2):
    """多判官成对裁决去偏聚合。

    judgements: [{"judge": 模型名, "ab_winner": 实体, "ba_winner": 实体}, ...]
    步骤：① 每个判官先过 position-swap，得稳定赢家（不稳→剔除）；② 稳定票里要 ≥min_judges 个
    判官、且其多数指向同一实体且无异议实体（全体一致）才采纳；分歧/票数不足 → tie。
    返回 {winner, decision, stable_votes, position_biased, judges_total, reason}。纯函数。"""
    stable_winners, biased = [], 0
    judges_total = 0
    for j in judgements or []:
        if not isinstance(j, dict):
            continue
        judges_total += 1
        w = position_stable_winner(j.get("ab_winner"), j.get("ba_winner"))
        if w:
            stable_winners.append(w)
        else:
            biased += 1
    if len(stable_winners) < min_judges:
        return {"winner": None, "decision": TIE, "stable_votes": len(stable_winners),
                "position_biased": biased, "judges_total": judges_total,
                "reason": f"position-stable 票数 {len(stable_winners)} < 所需 {min_judges}（位置偏或判官不足）"}
    distinct = set(stable_winners)
    if len(distinct) == 1:
        w = next(iter(distinct))
        return {"winner": w, "decision": w, "stable_votes": len(stable_winners),
                "position_biased": biased, "judges_total": judges_total,
                "reason": "全体 position-stable 判官一致"}
    return {"winner": None, "decision": TIE, "stable_votes": len(stable_winners),
            "position_biased": biased, "judges_total": judges_total,
            "reason": f"判官分歧：{sorted(distinct)} → 需人判"}


# ── 协议3：rubric-anchored（量规分去判官宽严偏 + 高方差降信） ────────────────
def zscore_normalize(scores):
    """判官内 z 归一（去该判官系统性宽/严偏）。std=0 或 <2 项 → 全 0。纯函数。"""
    vals = [float(s) for s in scores if isinstance(s, (int, float))]
    if len(vals) < 2:
        return [0.0 for _ in scores]
    mu = statistics.mean(vals)
    sd = statistics.pstdev(vals)
    if sd == 0:
        return [0.0 for _ in scores]
    return [round((float(s) - mu) / sd, 4) if isinstance(s, (int, float)) else 0.0 for s in scores]


def aggregate_rubric(panel, variance_threshold=DEFAULT_VARIANCE_THRESHOLD):
    """多判官量规分聚合（同量纲·如 1–10）。

    panel: {判官: {准则: 分}}。逐准则取判官均值；判官间 stdev > variance_threshold → low_confidence
    （判官没共识，别拿去当硬结论）。返回 {criterion: {mean, stdev, n, confidence}}。纯函数。"""
    by_crit = {}
    for judge, scores in (panel or {}).items():
        if not isinstance(scores, dict):
            continue
        for crit, val in scores.items():
            if isinstance(val, (int, float)):
                by_crit.setdefault(crit, []).append(float(val))
    out = {}
    for crit, vals in by_crit.items():
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out[crit] = {
            "mean": round(statistics.mean(vals), 3),
            "stdev": round(sd, 3),
            "n": len(vals),
            "confidence": "low" if sd > variance_threshold else "ok",
        }
    return out


# ── 顶层：一对候选的去偏裁决 ───────────────────────────────────────────────
def debias_verdict(judgements, panel=None, min_judges=2, variance_threshold=DEFAULT_VARIANCE_THRESHOLD):
    """对一对候选跑完整去偏协议，返回可信结论 + 全过程留痕（透明·不静默吞偏差）。

    judgements=成对裁决（协议1+2）；panel=可选量规分（协议3）。返回 dict：
    {winner|None, decision, confidence, consensus{...}, rubric{...}}。绝不当确定性门控——
    供 critic-loop / novel-score 作 advisory 与人判依据。纯函数。"""
    consensus = pairwise_consensus(judgements, min_judges=min_judges)
    rubric = aggregate_rubric(panel, variance_threshold) if panel else {}
    low_conf_crits = [c for c, v in rubric.items() if v.get("confidence") == "low"]
    if consensus["decision"] == TIE:
        confidence = "low"
    elif low_conf_crits:
        confidence = "medium"
    else:
        confidence = "high"
    return {
        "winner": consensus["winner"],
        "decision": consensus["decision"],
        "confidence": confidence,
        "consensus": consensus,
        "rubric": rubric,
        "low_confidence_criteria": low_conf_crits,
    }


# ── CLI：让去偏协议从「文档规范」变「可执行闸」（critic-loop / novel-score 真跑此入口） ──
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def _load_json(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    """对仓库外判官产物跑去偏协议，stdout 输出可信结论 + 全过程留痕。

    --verdicts: 成对裁决 JSON（list[{judge, ab_winner, ba_winner}]，协议1+2）。
    --panel:    量规分 JSON（{判官: {准则: 分}}，协议3）。二者至少给一个。
    默认纯 advisory（恒 exit 0）；--require-confidence 才把信心不足升成 exit 1（opt-in 硬闸，
    给 critic-loop 这类「不达标就别采纳」的调用方用；与模块「绝不静默吞偏差」一致）。"""
    import argparse
    import json
    import sys
    p = argparse.ArgumentParser(description="LLM-as-judge 去偏协议确定性执行层（不调用 LLM）")
    p.add_argument("--verdicts", help="成对裁决 JSON 路径：list[{judge,ab_winner,ba_winner}]")
    p.add_argument("--panel", help="量规分 JSON 路径：{judge:{criterion:score}}")
    p.add_argument("--min-judges", type=int, default=2)
    p.add_argument("--variance-threshold", type=float, default=DEFAULT_VARIANCE_THRESHOLD)
    p.add_argument("--require-confidence", choices=["low", "medium", "high"], default=None,
                   help="opt-in 硬闸：实得信心低于此 → exit 1（默认不给则恒 advisory exit 0）")
    args = p.parse_args(argv)
    if not args.verdicts and not args.panel:
        p.error("至少提供 --verdicts 或 --panel 之一")
    judgements = _load_json(args.verdicts) if args.verdicts else []
    panel = _load_json(args.panel) if args.panel else None
    result = debias_verdict(judgements, panel=panel,
                            min_judges=args.min_judges,
                            variance_threshold=args.variance_threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_confidence:
        got = _CONFIDENCE_RANK.get(result["confidence"], 0)
        need = _CONFIDENCE_RANK[args.require_confidence]
        if got < need:
            print(f"[gate] 信心 {result['confidence']} < 所需 {args.require_confidence}（位置偏/判官分歧/高方差）→ 不可采纳",
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    import sys
    sys.exit(main())
