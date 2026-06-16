#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
n2d_readiness_check.py — 漫剧改编「就绪度」确定性机检（opt-in，给将流向 n2d 的小说）

为什么单列：红果头部短剧 70-80% 是番茄小说 IP 改编、番茄设「爆款之源奖」奖励为改编而生
的原著——小说→漫剧是主变现路径。`n2d-asset-aware.md` 已让作者在正文里**埋资产标签**
（`[CHAR/PROP/LOC/VFX/OUTFIT_*]`），但那只解决"标了什么"，不解决"这章够不够漫剧友好"。
本脚本把后者下沉成确定性候选线索，避免到 n2d-script 分镜阶段才发现细节不够、回小说返工。

诚实分工（同 mechanical_check / pacing 哲学）：脚本只算**确定性近似信号**，是候选线索不是定论；
"这段画面感到底够不够"由 LLM 读文本复核。就绪 4 维：
  1. 资产标签密度  —— 每章 [CHAR/PROP/LOC/VFX/OUTFIT_*] 去重数 / 千字。0 标签=n2d 盲猜资产。
  2. 对白占比      —— 引号内 CJK 字 / 全章 CJK 字。过低=纯旁白，难配音/难分镜。
  3. 视觉锚密度    —— PROMO_VISUAL_KW（血/光/剑/雾…）命中 / 千字。低=画面冲击弱。
  4. 场景锚        —— 去重 [LOC_*] 数。0=空间几何不清晰，分镜无处落景。

阈值用「绝对地板 + 本书自标定中位」混合：硬地板抓"完全缺失"（0 标签/0 场景锚），
相对中位抓"显著低于本书自身水准"的弱章——避免对不同文风一刀切。

  python3 n2d_readiness_check.py <作品根> [--range 1-100] [--json-out 审稿/n2d_readiness.json]

纯标准库，无第三方依赖。
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_LIB = os.path.join(_SKILLS, "novel", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
from project_io import parse_chapter_range, read_chapters  # noqa: E402
from keyword_banks import PROMO_VISUAL_KW  # noqa: E402  视觉高光词单一定义源

_CJK = r"一-鿿"
# 资产标签语法与 novel-craft/scripts/export.py 的导出正则同口径（单行内联，避免脆弱跨脚本 import）。
_ASSET_RE = re.compile(r"\[(CHAR|PROP|VFX|LOC|OUTFIT)_([^\]]+)\]")
_QUOTE_PAIRS = [("“", "”"), ("「", "」"), ("『", "』")]

# 漫剧友好绝对地板（候选线索，宁缺毋滥）。
DIALOGUE_FLOOR = 0.08   # 对白占比 < 8% → 旁白过重候选


def _cjk_len(s):
    return len(re.findall(f"[{_CJK}]", s))


def _density(text, kw):
    chars = _cjk_len(text) or 1
    return round(sum(text.count(w) for w in kw) / chars * 1000, 2)


def _dialogue_ratio(text):
    chars = _cjk_len(text) or 1
    total = 0
    for lq, rq in _QUOTE_PAIRS:
        for q in re.findall(re.escape(lq) + r"(.*?)" + re.escape(rq), text, re.DOTALL):
            total += _cjk_len(q)
    return round(total / chars, 3)


def _assets(text):
    """返回 (去重资产 key 集合, 去重 LOC 场景 key 集合)。"""
    assets, locs = set(), set()
    for kind, key in _ASSET_RE.findall(text):
        assets.add(f"{kind}_{key}")
        if kind == "LOC":
            locs.add(key)
    return assets, locs


def _median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def analyze(project, rng=None):
    rows = []
    for idx, _path, text in read_chapters(project, rng):
        assets, locs = _assets(text)
        kchars = (_cjk_len(text) or 1) / 1000
        rows.append({
            "chapter": idx,
            "chars": _cjk_len(text),
            "asset_tags": len(assets),
            "asset_tag_density": round(len(assets) / kchars, 2),
            "scene_anchors": len(locs),
            "dialogue_ratio": _dialogue_ratio(text),
            "visual_density": _density(text, PROMO_VISUAL_KW),
        })
    return rows


def flag_rows(rows):
    """逐章 + 全书自标定，标候选弱章。返回 (rows, summary)。"""
    if not rows:
        return rows, {}
    med_dlg = _median([r["dialogue_ratio"] for r in rows])
    med_vis = _median([r["visual_density"] for r in rows])
    for r in rows:
        flags = []
        if r["asset_tags"] == 0:
            flags.append("无资产标签（n2d 将盲猜定妆）")
        if r["scene_anchors"] == 0:
            flags.append("无场景锚 LOC（空间不清晰）")
        if r["dialogue_ratio"] < DIALOGUE_FLOOR or r["dialogue_ratio"] < med_dlg * 0.5:
            flags.append(f"对白偏少({r['dialogue_ratio']})")
        if r["visual_density"] < med_vis * 0.5:
            flags.append(f"画面感偏弱({r['visual_density']})")
        r["flags"] = flags
        r["ready"] = not flags
    weak = [r["chapter"] for r in rows if r["flags"]]
    summary = {
        "n_chapters": len(rows),
        "ready_chapters": sum(1 for r in rows if r["ready"]),
        "weak_chapters": weak,
        "median_dialogue_ratio": round(med_dlg, 3),
        "median_visual_density": round(med_vis, 2),
        "total_asset_tags": sum(r["asset_tags"] for r in rows),
    }
    return rows, summary


def main():
    ap = argparse.ArgumentParser(description="漫剧改编就绪度确定性机检（opt-in）")
    ap.add_argument("project_path", help="作品根（含 章节/）")
    ap.add_argument("--range", help="章节范围，如 1-100 或单章 12")
    ap.add_argument("--json-out", help="机读结果落盘路径（默认 审稿/n2d_readiness.json）")
    args = ap.parse_args()

    rows = analyze(args.project_path, parse_chapter_range(args.range))
    if not rows:
        print(f"Error: {args.project_path}/章节 下没有可读章节（或 --range 无命中）")
        return 1
    rows, summary = flag_rows(rows)
    date = datetime.now().strftime("%Y-%m-%d")
    out = args.json_out or os.path.join(args.project_path, "审稿", "n2d_readiness.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "date": date,
            "kind": "novel_n2d_readiness",
            "note": "漫剧改编就绪确定性候选线索；画面感/空间是否真够由 LLM 读文本复核。",
            "summary": summary,
            "chapters": rows,
        }, f, ensure_ascii=False, indent=2)

    print(f"漫剧就绪机检：{summary['n_chapters']} 章，{summary['ready_chapters']} 章就绪，"
          f"{len(summary['weak_chapters'])} 章有候选弱项")
    if summary["weak_chapters"]:
        head = "、".join(f"第{c}章" for c in summary["weak_chapters"][:8])
        print(f"  待复核弱章：{head}{' …' if len(summary['weak_chapters']) > 8 else ''}")
    print(f"  机读结果 → {out}")
    print("  ⚠️ 候选线索，非定论；漫剧改编就绪清单见 novel-craft/references/n2d-readiness.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
