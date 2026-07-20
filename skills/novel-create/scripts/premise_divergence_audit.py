#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""premise_divergence_audit.py — 蓝图三方案"真差异化"机检（advisory·纯标准库）。

为什么：novel-create 的创意闸要求锁蓝图前给 **3 个差异化方向**且"不是同一方案的三种措辞"，
但这一直是 prose 指令——LLM 完全可以交三条换汤不换药的 logline 而无人拦（mode collapse
的典型形态）。对标兄弟线镜头多样性审计（shot_variety_audit）的重复对检测，把"三方案够不够散"做成
可机检的最低门槛。

输入：`设定/premise_candidates.json`（立项访谈时落盘，schema 见下）。缺文件优雅跳过并
提示落盘——**先有结构化候选，才有差异化机检**。

    {"schema_version": 1, "kind": "novel_premise_candidates",
     "candidates": [{"id": "A", "logline": "…", "memory_point": "…",
                     "closest_hit": "…", "key_diff": "…"}, …],
     "chosen": "A" | "A+C杂交" | null}

三个信号（全部 advisory·blocking 恒 0）：
  ① too_few_candidates   候选 <3 → 建议级（创意闸要求的最低发散量）
  ② paraphrase_pair      两候选 logline+记忆点 char-2gram Jaccard ≥ 阈值 → 建议级
                          （"同一方案的三种措辞"实锤候选）
  ③ shared_trope_anchor  两候选命中**同一批**高频套路词（CLICHE_KW）→ info
                          （表面措辞不同、套路骨架相同）

口径纪律：相似度是字面近似（confidence=heuristic），语义级同质仍需人判——本检只拦
"明显糊弄"，不拦"真发散但字面撞词"；blocking 恒 0。

用法：
    python3 premise_divergence_audit.py <作品根> [--json]
测试：cd skills/novel-create/scripts && python3 -m pytest test_premise_divergence_audit.py
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "novel", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
try:
    from keyword_banks import CLICHE_KW
except Exception:
    CLICHE_KW = []

CANDIDATES_REL = os.path.join("设定", "premise_candidates.json")
PAIR_SIM_WARN = float(os.environ.get("NOVEL_PREMISE_PAIR_SIM", "0.45"))
MIN_CANDIDATES = int(os.environ.get("NOVEL_PREMISE_MIN_CANDIDATES", "3"))
NGRAM = 2
PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】《》]+")


def clean(text):
    return _NOISE_RE.sub("", str(text or ""))


def shingles(text, n=NGRAM):
    c = clean(text)
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def candidate_text(cand):
    """参与相似度判定的文本 = logline + 差异化记忆点（closest_hit 是外部参照不算自述）。"""
    return f"{cand.get('logline') or ''}{cand.get('memory_point') or ''}"


def trope_anchors(cand):
    """候选命中的高频套路词集合。"""
    text = f"{cand.get('logline') or ''}{cand.get('memory_point') or ''}"
    return {w for w in CLICHE_KW if w and w in text}


def audit_candidates(candidates):
    """跑三信号，返回 alerts（纯函数·可测）。candidates=[{id, logline, …}]。"""
    alerts = []
    cands = [c for c in (candidates or []) if isinstance(c, dict)]
    if len(cands) < MIN_CANDIDATES:
        alerts.append({
            "type": "too_few_candidates", "severity": "建议级", "auto": True,
            "note": (f"仅 {len(cands)} 个候选方向（创意闸要求 ≥{MIN_CANDIDATES}）——"
                     f"先按 premise-divergence.md 的六个撬棍补足发散再收敛"),
        })
    items = [(str(c.get("id") or i + 1), c, shingles(candidate_text(c)))
             for i, c in enumerate(cands)]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            sim = jaccard(items[i][2], items[j][2])
            if sim >= PAIR_SIM_WARN:
                alerts.append({
                    "type": "paraphrase_pair", "severity": "建议级", "auto": True,
                    "pair": [items[i][0], items[j][0]], "similarity": round(sim, 2),
                    "note": (f"方向 {items[i][0]} 与 {items[j][0]} 相似度 {sim:.0%}——"
                             f"疑似同一方案的两种措辞，不算真发散；换切口重出一个"
                             f"（{PROVENANCE}）"),
                })
                continue
            shared = trope_anchors(items[i][1]) & trope_anchors(items[j][1])
            if shared:
                alerts.append({
                    "type": "shared_trope_anchor", "severity": "info", "auto": True,
                    "pair": [items[i][0], items[j][0]], "tropes": sorted(shared),
                    "note": (f"方向 {items[i][0]} 与 {items[j][0]} 措辞不同但共享套路锚"
                             f"（{'、'.join(sorted(shared))}）——套路骨架相同的两个皮，"
                             f"考虑让其中一个真正换骨架（{PROVENANCE}）"),
                })
    return alerts


def find_market_candidates(project, max_up=6):
    """向上找 <repo>/生产战绩/差异化候选.json（外部投放侧回灌的白空间组合）。

    该文件被 novel-create/score/title 三处 SKILL 引用为"立项先读"，但此前全是 prose、
    无任何机器读端——选题反哺闭环的上游落地无机器保证。这里做**发现层**：找到就把
    路径写进报告，立项 agent 据此必读；没有返回 None（正常，不是错误）。"""
    cur = os.path.abspath(project)
    for _ in range(max_up):
        cand = os.path.join(cur, "生产战绩", "差异化候选.json")
        if os.path.exists(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def analyze(project):
    """novel-review 检测器契约：{ran, alerts, total, blocking(=0)}；缺候选文件优雅跳过。"""
    path = os.path.join(project, CANDIDATES_REL)
    if not os.path.exists(path):
        return {"ran": False,
                "skipped": (f"缺 {CANDIDATES_REL}——立项访谈给出 3 个差异化方向时请同步落盘"
                            f"（schema 见 premise_divergence_audit.py 模块注释），才有差异化机检")}
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        return {"ran": False, "skipped": f"{CANDIDATES_REL} 不可读：{exc}"}
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    alerts = audit_candidates(candidates or [])
    return {
        "ran": True,
        "thresholds": {"pair_sim_warn": PAIR_SIM_WARN, "min_candidates": MIN_CANDIDATES,
                       "ngram": NGRAM, "provenance": PROVENANCE,
                       "note": "advisory：字面近似初筛，语义级同质仍需人判；blocking 恒 0。"},
        "candidates": [str(c.get("id") or i + 1) for i, c in
                       enumerate(c for c in (candidates or []) if isinstance(c, dict))],
        "chosen": payload.get("chosen") if isinstance(payload, dict) else None,
        # 选题反哺闭环读端：存在即提示立项 agent 必读（高分白空间组合优先做推荐方向）
        "market_candidates_path": find_market_candidates(project),
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,  # advisory 纪律：恒 0
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="蓝图三方案差异化机检（advisory）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "premise_divergence_findings.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 蓝图三方案差异化机检：{len(res['candidates'])} 个候选，{res['total']} 条提示")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
