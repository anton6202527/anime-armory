#!/usr/bin/env python3
"""Audit raw episode boundaries before n2d-script stage-1 refinement.

Usage:
  python3 skills/n2d-script/scripts/boundary_audit.py <作品根> [start-end] [--strict] [--json]

This is a deterministic pre-check. It does not decide story quality by itself;
it flags episodes that need human/LLM boundary review before writing voiceover.

两层输出：
  ① 逐集体检表（粗胚右边界风险：软断/章内续切/弱钩/无闭环）。
  ② 剧级追更骨架（Gap1）：跨集断点强度分布 + 连续弱钩集群 + 开篇集群钩子梯度 +
     按 `变现模式`(免费/付费/海外) 的付费/AD 卡点集定位。题材词典按 `题材` 选择点切换(Gap3)。
完整方法论见 references/追更骨架.md。
"""
import json
import os
import re
import statistics
import sys
from pathlib import Path

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_const import boundary_buckets, boundary_lexicon  # noqa: E402
from n2d_settings import get_setting  # noqa: E402

CHAPTER_HEAD = re.compile(r"^第[一二三四五六七八九十百千万0-9]+章")
# 悬念收尾标点（强断点的"硬断"信号，与词钩叠加判强度）。
SUSPENSE_PUNCT = ("？", "！", "…", "——", "?", "!")


def build_res(genre_text):
    """题材感知：强钩收尾 + 冲突 + 爽点/反转 三正则（与 split_novel 同源，避免漂移）。"""
    strong, conflict, payoff = boundary_lexicon(genre_text)
    strong_re = re.compile(r"(" + "|".join(re.escape(t) for t in strong) + r")\s*$")
    conflict_re = re.compile(r"(" + "|".join(re.escape(t) for t in conflict) + r")")
    payoff_re = re.compile(r"(" + "|".join(re.escape(t) for t in payoff) + r")")
    return strong_re, conflict_re, payoff_re


def cjk_len(text):
    return len(re.findall(r"[㐀-鿿]", text))


def ep_num(path):
    m = re.search(r"第(\d+)集", path.name)
    return int(m.group(1)) if m else -1


def end_strength(text, soft_end, strong_re):
    """集尾断点强度：强(2)=悬念标点+词钩齐 / 中(1)=其一 / 弱(0)=无（软断恒判弱）。"""
    if soft_end:
        return 0
    tail = text[-160:]
    punct = bool(text and text.rstrip()[-1:] in "？！…—?!")
    word = bool(strong_re.search(tail))
    return 2 if (punct and word) else (1 if (punct or word) else 0)


STRENGTH_LABEL = {2: "强", 1: "中", 0: "弱"}


def load_rows(root, strong_re, conflict_re, payoff_re):
    script_root = Path(root) / "脚本"
    rows = []
    for d in sorted(script_root.glob("第*集"), key=ep_num):
        raw = d / "raw.txt"
        if not raw.exists():
            continue
        text = raw.read_text(encoding="utf-8").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        soft_end = bool(text and text[-1] in "，、；：")
        rows.append({
            "ep": ep_num(d),
            "chars": cjk_len(text),
            "chapter": bool(CHAPTER_HEAD.search(text)),
            "start": "".join(lines[:2])[:90] if lines else "",
            "end": "".join(lines[-3:])[-140:] if lines else "",
            "soft_end": soft_end,
            "strong_end": bool(strong_re.search(text[-160:])),
            "strength": end_strength(text, soft_end, strong_re),
            "has_conflict": bool(conflict_re.search(text)),
            "has_payoff": bool(payoff_re.search(text)),
        })
    for r in rows:
        r["closed_loop"] = r["has_conflict"] and r["has_payoff"]
    return rows


def weak_clusters(rows, threshold=0):
    """相邻弱钩(strength<=threshold)集群：≥2 连为流失高风险段。"""
    clusters, cur = [], []
    for r in rows:
        if r["strength"] <= threshold:
            cur.append(r["ep"])
        else:
            if len(cur) >= 2:
                clusters.append((cur[0], cur[-1]))
            cur = []
    if len(cur) >= 2:
        clusters.append((cur[0], cur[-1]))
    return clusters


def cliffhanger_positions(rows, monet):
    """按变现模式给"应是强卡点"的集号：付费/海外=前十集付费墙峰值 + 每 ~10 集；免费=不设硬卡点。"""
    eps = [r["ep"] for r in rows]
    if not eps:
        return []
    last = max(eps)
    if monet == "免费":
        return []  # 免费靠全程延续性，断点平均强即可，无单点付费墙
    # 付费/海外：经典付费墙在第 8-10 集附近，之后每 ~10 集一个续费卡点
    walls = [n for n in (8, 10) if n <= last]
    n = 20
    while n <= last:
        walls.append(n)
        n += 10
    return sorted(set(walls))


def series_arc(rows, monet):
    """剧级追更骨架体检（Gap1）。返回结构化 dict + 人读建议行。"""
    out = {"monetization": monet, "issues": [], "notes": []}
    if not rows:
        return out
    dist = {2: 0, 1: 0, 0: 0}
    for r in rows:
        dist[r["strength"]] += 1
    out["strength_dist"] = {STRENGTH_LABEL[k]: v for k, v in dist.items()}

    # 连续弱钩集群（断点流失高风险）
    clusters = weak_clusters(rows)
    out["weak_clusters"] = clusters
    for a, b in clusters:
        out["issues"].append(f"连续弱钩集群 第{a}-{b}集：断点平→观众易划走，并入相邻强断点集或补强集尾钩")

    # 无闭环集（P1·纯铺垫嫌疑）
    no_loop = [r["ep"] for r in rows if not r["closed_loop"]]
    out["no_closed_loop"] = no_loop
    if no_loop:
        out["issues"].append(
            f"疑似无闭环/纯铺垫集 第{'、'.join(map(str, no_loop[:12]))}集"
            f"{'…' if len(no_loop) > 12 else ''}：缺冲突或缺爽点/反转，复核是否并入相邻集（P1）")

    # 开篇集群钩子梯度（首 N 集留存投资）
    head_n = min(4, len(rows))
    head = rows[:head_n]
    weak_head = [r["ep"] for r in head if r["strength"] <= 0]
    out["opening_cluster"] = [r["ep"] for r in head]
    if weak_head:
        out["issues"].append(
            f"开篇集群第{'、'.join(map(str, weak_head))}集弱钩：前{head_n}集是留存投资最高区，"
            f"应世界观+主角欲望+系列总钩立稳且钩子递增（P6/前十集定律）")
    out["notes"].append(f"开篇集群=前{head_n}集（首集须扛 世界观+主角欲望+系列总钩，最该加权）")

    # 变现模式卡点定位
    walls = cliffhanger_positions(rows, monet)
    out["cliffhanger_targets"] = walls
    by_ep = {r["ep"]: r for r in rows}
    if monet == "免费":
        out["notes"].append("变现=免费：完播率导向，要全剧延续性、断点平均强；不设单点付费墙，重点消灭连续弱钩集群")
    else:
        weak_walls = [w for w in walls if w in by_ep and by_ep[w]["strength"] < 2]
        if weak_walls:
            out["issues"].append(
                f"变现={monet} 卡点集第{'、'.join(map(str, weak_walls))}集断点不够强（付费墙/续费点应是最强 cliffhanger）")
        out["notes"].append(
            f"变现={monet}：前十集卡点峰值，付费墙集（{'、'.join(map(str, walls)) or '—'}）须最强断点（危机悬置/反转预告）")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    strict = "--strict" in flags
    as_json = "--json" in flags
    if not args:
        print("用法: boundary_audit.py <作品根> [start-end] [--strict] [--json]")
        sys.exit(2)
    root = args[0]
    genre = get_setting(root, "题材", "")
    monet = get_setting(root, "变现模式", "免费") or "免费"
    buckets = boundary_buckets(genre)
    strong_re, conflict_re, payoff_re = build_res(genre)

    rows = load_rows(root, strong_re, conflict_re, payoff_re)
    if not rows:
        print("未找到 脚本/第N集/raw.txt")
        sys.exit(1)
    if len(args) >= 2:
        m = re.match(r"(\d+)-(\d+)$", args[1])
        if not m:
            print("范围格式应为 start-end，例如 2-10")
            sys.exit(2)
        a, b = map(int, m.groups())
        rows = [r for r in rows if a <= r["ep"] <= b]

    arc = series_arc(rows, monet)
    has_risk = False
    per_ep = []
    for r in rows:
        flags_e, advice = [], []
        risk = False
        if r["chars"] < 650:
            flags_e.append("短(提示)")
            advice.append("可保留短集，核闭环完整")
        if r["chars"] > 1100:
            flags_e.append("长(提示)")
            advice.append("可保留长集，核中段钩子密度")
        if r["soft_end"]:
            flags_e.append("软断")
            advice.append("右边界后移到完整钩子")
            risk = True
        if not r["chapter"]:
            flags_e.append("章内续切")
            risk = True
        if r["strength"] <= 0:
            flags_e.append("弱钩待判")
            advice.append("精修时补强集尾钩")
            risk = True
        if not r["closed_loop"]:
            miss = "缺冲突" if not r["has_conflict"] else "缺爽点/反转"
            flags_e.append(f"无闭环({miss})")
            advice.append("复核并入相邻集或补闭环(P1)")
            risk = True
        if risk:
            has_risk = True
        per_ep.append({**r, "flags": flags_e, "advice": advice})

    if as_json:
        print(json.dumps({"genre": genre, "buckets": buckets, "series_arc": arc,
                          "episodes": per_ep, "has_risk": has_risk},
                         ensure_ascii=False, indent=2))
        sys.exit(1 if (strict and has_risk) else 0)

    chars = [r["chars"] for r in rows]
    print(f"题材词典：{(genre or '未设')}→{'/'.join(buckets)}　变现模式：{monet}")
    print(f"episodes={len(rows)} chars_min={min(chars)} chars_max={max(chars)} "
          f"chars_avg={statistics.mean(chars):.1f} chars_median={statistics.median(chars):.0f}")
    print()
    print("| 集 | 字数 | 章头 | 断点 | 标记 | 处理建议 |")
    print("|---|---:|---|:--:|---|---|")
    for r in per_ep:
        print(f"| 第{r['ep']}集 | {r['chars']} | {'是' if r['chapter'] else '否'} | "
              f"{STRENGTH_LABEL[r['strength']]} | {'、'.join(r['flags']) or 'OK'} | "
              f"{'；'.join(r['advice']) or '保留'} |")

    print()
    print("## 剧级追更骨架（Gap1·跨集留存体检）")
    d = arc["strength_dist"]
    print(f"- 断点强度分布：强 {d['强']} / 中 {d['中']} / 弱 {d['弱']}")
    if arc["issues"]:
        for it in arc["issues"]:
            print(f"- ⚠️ {it}")
    else:
        print("- ✅ 未发现连续弱钩集群 / 无闭环集 / 卡点偏弱")
    for note in arc["notes"]:
        print(f"- ℹ️ {note}")
    print("> 方法论见 references/追更骨架.md；逐集集内留存见 n2d/references/导演节奏.md。")

    if strict and has_risk:
        print("\n⛔ boundary_audit strict: 存在高风险粗胚边界；先做 5-10 集窗口复核并写 脚本/_拆集复核.md。")
        sys.exit(1)


if __name__ == "__main__":
    main()
