#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chapter_transition.py — 章首承接/章间衔接 确定性机检（advisory·纯标准库）。

为什么：写作端 `draft_packets.py` 会把上一章末尾塞进"上一章承接"辅助写作，但**质检端
没有任何脚本验证相邻章开篇是否连贯承接**——hook_endings 只看章末钩子，没人看章首接不接
得住。时间/地点/人物硬跳切（上一章刀架在脖子上，下一章开篇突然在千里外喝茶、无任何
转场标记）是剧情衔接最常见的断裂形态，也是审稿抽查最容易漏的（审稿往往按章读，不对齐
章边界）。

两个信号（全部 advisory·blocking 恒 0）：
  ① abrupt_transition   上一章末尾与本章开篇**人物集合零交集**，且开篇**无任何转场标记**
                         （时间词/换线词/地点抵达词）→ 建议级"硬跳切候选"
  ② orphan_opening      本章开篇既无已知角色、又无转场标记（开篇悬空，读者不知在哪跟谁）→ info

口径纪律（宁缺毋滥）：
  - 有转场标记（翌日/与此同时/另一边/回到…）= 作者**有意**切线/跳时，一律豁免——挂起
    危机切 POV 是合法留钩手法，绝不当穿帮报。
  - 人物识别依赖角色卡名册（wiki_builder.parse_character_names 单一来源）；名册空则整体
    优雅跳过（ran=False），不拿噪音候选臆造衔接问题。
  - 判定只看章边界两小段（尾 TAIL_CHARS / 首 HEAD_CHARS），不整章扫描。
  - blocking 恒 0：衔接好坏最终是叙事判断，机检只出候选。

用法：
    python3 chapter_transition.py <作品根> [--json]
测试：cd skills/novel/novel-review/scripts && python3 -m pytest test_chapter_transition.py
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
if _WIKI not in sys.path:
    sys.path.insert(0, _WIKI)
try:
    from wiki_builder import list_chapters, parse_character_names
except Exception:  # 独立跑/测试桩兜底
    def list_chapters(project, *a, **k):  # type: ignore
        return []
    def parse_character_names(project):  # type: ignore
        return set()

TAIL_CHARS = int(os.environ.get("NOVEL_TRANSITION_TAIL", "200"))
HEAD_CHARS = int(os.environ.get("NOVEL_TRANSITION_HEAD", "200"))
PROVENANCE = "internal-heuristic·confidence=low"

# 转场标记：命中即视为"作者有意转场"，豁免一切衔接判定。
# 三类：时间推进 / 换线（POV 切换）/ 抵达新地点。
_TRANSITION_MARKERS = (
    # 时间推进
    "翌日", "次日", "第二天", "第二日", "三日后", "三天后", "数日后", "数天后", "半月后",
    "一个月后", "一月后", "月余", "半年后", "一年后", "当晚", "入夜", "夜里", "清晨",
    "黎明", "黄昏", "傍晚", "片刻后", "须臾", "转眼", "眨眼间", "不多时", "翌晨",
    # 换线 / POV 切换
    "与此同时", "同一时刻", "同一时间", "另一边", "另一头", "另一厢", "此时的", "而在",
    "视线转到", "镜头转到", "话分两头", "却说",
    # 抵达 / 空间转移
    "回到", "来到", "赶到", "抵达", "已至", "行至", "到了",
)
# 楔子/番外等非主线章：不参与承接判定（与 plot_variety_audit 同口径）。
_EXEMPT_TITLE_RE = re.compile(r"番外|楔子|序章|回顾|尾声|后记|人物志|设定集")


def has_transition_marker(head):
    return any(m in (head or "") for m in _TRANSITION_MARKERS)


def chars_in(text, roster):
    """段内出现的已知角色集合。roster 需按长度降序匹配可不必——集合成员独立判断。"""
    t = text or ""
    return {name for name in roster if name and name in t}


def judge_boundary(prev_tail, head, roster):
    """判定一条章边界。返回 (verdict, detail)：
      verdict ∈ {"ok", "abrupt", "orphan", "skip"}。纯函数·可测。"""
    if not prev_tail or not head:
        return "skip", "边界文本缺失"
    if has_transition_marker(head[:HEAD_CHARS]):
        return "ok", "开篇带转场标记（有意转场，豁免）"
    tail_chars_ = chars_in(prev_tail, roster)
    head_chars_ = chars_in(head[:HEAD_CHARS], roster)
    if not head_chars_:
        return "orphan", "开篇无已知角色亦无转场标记"
    if tail_chars_ and not (tail_chars_ & head_chars_):
        return "abrupt", (f"上一章末尾人物（{'、'.join(sorted(tail_chars_))}）与开篇人物"
                          f"（{'、'.join(sorted(head_chars_))}）零交集且无转场标记")
    return "ok", "承接正常"


def analyze(project):
    """逐条章边界跑承接判定。返回 novel-review 检测器契约：
    {ran, alerts, boundaries, total, blocking(=0)}；无章节/名册空 → 优雅跳过。"""
    chapters = [(cid, path, text) for cid, path, text in list_chapters(project)
                if not _EXEMPT_TITLE_RE.search(os.path.basename(str(path or "")))]
    if len(chapters) < 2:
        return {"ran": False, "skipped": "不足两章——没有章边界可查承接"}
    roster = set(parse_character_names(project) or [])
    if not roster:
        return {"ran": False,
                "skipped": "角色名册为空（缺 设定/角色卡.md 或 人物.md）——不拿噪音候选臆造衔接问题"}

    alerts, boundaries = [], []
    for (pcid, _pp, ptext), (cid, _cp, text) in zip(chapters, chapters[1:]):
        prev_tail = (ptext or "").rstrip()[-TAIL_CHARS:]
        head = (text or "").lstrip()[:HEAD_CHARS]
        verdict, detail = judge_boundary(prev_tail, head, roster)
        boundaries.append({"from_chapter": pcid, "to_chapter": cid,
                           "verdict": verdict, "detail": detail})
        if verdict == "abrupt":
            alerts.append({
                "type": "abrupt_chapter_transition", "severity": "建议级", "auto": True,
                "chapter": cid,
                "evidence": f"…{prev_tail[-40:]} ‖ {head[:40]}…",
                "note": (f"第{pcid}→第{cid}章疑硬跳切：{detail}——若是有意切线，"
                         f"开篇加一个转场标记（与此同时/翌日/另一边…）即可豁免；"
                         f"若非有意，补一句承接把读者带过去（{PROVENANCE}）"),
            })
        elif verdict == "orphan":
            alerts.append({
                "type": "orphan_chapter_opening", "severity": "info", "auto": True,
                "chapter": cid,
                "evidence": head[:40],
                "note": (f"第{cid}章开篇 {HEAD_CHARS} 字内无已知角色也无转场标记——"
                         f"读者不知此刻在哪、跟着谁；若开篇是环境铺陈属有意为之可忽略（{PROVENANCE}）"),
            })

    return {
        "ran": True,
        "thresholds": {"tail_chars": TAIL_CHARS, "head_chars": HEAD_CHARS,
                       "provenance": PROVENANCE,
                       "note": "advisory：转场标记=有意转场一律豁免；名册空整体跳过。"},
        "boundaries": boundaries,
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,  # advisory 纪律：恒 0
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="章首承接/章间衔接 机检（advisory）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "transition_findings.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        out = None

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    icon = "⚠️" if res["total"] else "✅"
    print(f"{icon} 章间承接机检：{len(res['boundaries'])} 条边界，{res['total']} 条提示 → {out}")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
