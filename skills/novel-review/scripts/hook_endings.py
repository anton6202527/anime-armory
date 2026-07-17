#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hook_endings.py — 章末钩子/断章 确定性检查（纯标准库）。

为什么：网文留存第一指标是「断章」——每章结尾必须留钩子(悬念/反转/危机未决/疑问)，
读者才会点下一章。章末平淡收尾（把场景写圆满、情绪落地、无悬念）= 留存杀手，但现有
机检都只看正文一致性，没人盯结尾。本检测器只看每章**结尾那一小段**（断章区），用确定性
信号给收尾打分，平淡收尾报建议级；对「黄金三章」（前 3 章，决定追不追读）用更严的阈值。

只报**确定性弱钩子候选**（建议级），不阻断：断章是软留存信号，强弱很主观，确定性机检
只能逮「明显平淡」，逮不到「钩子假但形式对」——所以宁缺毋滥、绝不硬挡（见 main 说明）。
软判（钩子够不够爽、是不是好钩子）交 novel-score / 人判。

  python3 hook_endings.py <作品根> [--json]
测试：cd skills/novel-review/scripts && python3 -m pytest test_hook_endings.py
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# wiki_builder 在 novel-wiki/scripts 下（list_chapters 等公共助手的单一来源）。
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
if _WIKI not in sys.path:
    sys.path.insert(0, _WIKI)
try:
    from wiki_builder import list_chapters, _context  # noqa: F401  (_context 复用，保持同源)
except Exception:  # 退化兜底（独立跑/测试桩）——纯函数不依赖它，仍可单测。
    def list_chapters(project, *a, **k):  # type: ignore
        return []

# ── 可调常量（断章阈值/信号权重，都集中在这里方便调）─────────────────────────
TAIL_CHARS = 120          # 断章区取结尾多少字（约最后两三句，钩子就藏在这里）
WARN_THRESHOLD = 2        # 普通章：ending hook_score < 此值 → 建议级「平淡收尾」
GOLDEN_THRESHOLD = 3      # 黄金三章（前 3 章）更严：必须更强的钩子才算过
GOLDEN_MAX_CHAPTER = 3    # 前几章算「黄金三章」

# ── 信号词表（每类都是「断章常见钩子手法」，命中各 +1，可叠加）──────────────
# 1) 悬念/反转词：突然把情节扭转或抛出意外，最经典的断章钩。
# 注意「竟」不单列——会误命中「究竟」等中性词；「竟然」已覆盖反转语义。
SUSPENSE_WORDS = ("突然", "竟然", "没想到", "却见", "正是", "原来", "不料",
                  "赫然", "猛地", "蓦地", "岂料", "殊不知", "万万没想到")
# 4) 危机/动作未完词：结尾停在动作/危机半截（刀光已起、门被推开），逼读者想知道下一刻。
CRISIS_WORDS = ("刀光", "倒下", "黑暗", "坠落", "响起", "推开门", "推门", "袭来",
                "爆炸", "崩塌", "嘶吼", "尖叫", "鲜血", "断裂", "逼近", "扑来")
# 6) 揭示/身份钩：结尾抛出"某个旧信息/身份此刻对上了"的短句反转（掉马/认出/同款特征）。
#    生产实锤假阳性（金睛缉妖录第1章）："这眼睛……他当年，也有。"——强反转钩却被判 0 分：
#    无悬念词、无问号、省略号在句中不在句尾、无危机词、无登场式。这类钩的形态是
#    **揭示词 + 人物/往昔指涉**，单靠悬念词表逮不到。
REVEAL_WORDS = ("也有", "正是", "就是他", "就是她", "认出", "认得", "一模一样",
                "同样的", "熟悉的", "见过", "又是", "还是那", "当年")
# "竟是"单列用负向断言——否则"究竟是谁"这类**疑问句**会被误判成揭示（究竟≠竟是）。
_REVEAL_RE = re.compile(r"(?<!究)竟是")
# 人物/往昔指涉：与揭示词共现时构成"身份/旧事揭示"强钩（+2 而非 +1）。
_PERSON_PAST_RE = re.compile(r"他|她|那人|此人|当年|眼前这|那个人|那张脸|这双|这只|这枚|这块")


def ending_text(chapter_text, tail_chars=TAIL_CHARS):
    """取一章结尾的最后 tail_chars 个字（断章区），strip 掉尾部空白。纯函数·可测。

    断章只看结尾——把整章塞进打分会被正文里的悬念词污染，所以只截尾段。
    """
    s = (chapter_text or "").rstrip()
    if not s:
        return ""
    return s[-tail_chars:].strip()


def hook_score(ending):
    """给断章区结尾打分（int，0..N，越高钩子越强）。纯函数·可测。

    六类确定性信号，各命中 +1（同类只计一次，避免堆砌刷分；揭示钩最高 +2）：
      +1 悬念/反转词         SUSPENSE_WORDS（突然/竟然/没想到/却见/原来/不料/赫然/猛地…）
      +1 未决疑问            结尾含「？/?」（抛出问题不答 = 钩）
      +1 省略号/破折号留白   以 … / …… / —— / — 收尾，或句中带 …（话说半截）
      +1 危机/动作未完词     CRISIS_WORDS（刀光/倒下/黑暗/坠落/响起/推开门…）
      +1 新信息/人物登场     结尾出现「(某人)出现/登场/走来/开口」式新角色或新信息抛出
      +1/+2 揭示/身份钩      REVEAL_WORDS（也有/正是/竟是/认出/一模一样/当年…）；
                             叠加人物/往昔指涉（"他当年，也有"式掉马）再 +1
    """
    if not ending:
        return 0
    score = 0

    # +1 悬念/反转词
    if any(w in ending for w in SUSPENSE_WORDS):
        score += 1

    # +1 未决疑问：含中/英问号（结尾抛问题不答）
    if "？" in ending or "?" in ending:
        score += 1

    # +1 省略号/破折号留白：以 … / — 收束，**或句中带 …（话说半截）**——
    #    "这眼睛……他当年，也有。"这类句中省略号同样是留白钩形态，只认句尾会漏。
    tail = ending.rstrip("”\"』」）)】》")
    if (tail.endswith("…") or tail.endswith("……") or tail.endswith("—") or tail.endswith("——")
            or "……" in ending or "…" in ending):
        score += 1

    # +1 危机/动作未完词
    if any(w in ending for w in CRISIS_WORDS):
        score += 1

    # +1 直接抛新信息/人物登场：「…(谁)出现/登场/走来/现身/开口/说道/响起一个声音」
    #    结尾突然推个人/一句话进来，是常见「下章见分晓」钩。
    if re.search(r"(出现|登场|走来|现身|走出|站着|开口|说道|喝道|传来|响起)(?:了)?(?:一[个道])?", ending) \
            and re.search(r"(声音|身影|男子|女子|人影|来人|身后|门口|这时|此刻)", ending):
        score += 1

    # +1/+2 揭示/身份钩：揭示词命中 +1；同时带人物/往昔指涉（"他当年…也有"式掉马/认出）
    #    再 +1——身份揭示是网文最强钩型之一，此前完全无信号导致强反转钩被判 0 分（假阳性）。
    if any(w in ending for w in REVEAL_WORDS) or _REVEAL_RE.search(ending):
        score += 1
        if _PERSON_PAST_RE.search(ending):
            score += 1

    return score


def ending_band(score, is_golden_three):
    """把 hook_score 归档为 'ok' / 'warn'。纯函数·可测。

    普通章：score >= WARN_THRESHOLD → ok，否则 warn（平淡收尾，建议级）。
    黄金三章：用更严的 GOLDEN_THRESHOLD——前 3 章决定读者追不追，平淡开篇收尾对留存伤害更大。
    """
    threshold = GOLDEN_THRESHOLD if is_golden_three else WARN_THRESHOLD
    return "ok" if score >= threshold else "warn"


def analyze(project):
    """逐章取结尾打分，平淡收尾出 weak_chapter_ending 建议级 alert。返回汇总 dict。

    返回 {ran, alerts, scored:[{chapter,score,band,is_golden}], total, blocking(=0)}。
    无章节 → 优雅跳过（ran=False），不臆造。
    """
    chapters = list(list_chapters(project))
    if not chapters:
        return {"ran": False, "skipped": "无章节——先有正文再查断章"}

    alerts = []
    scored = []
    for cid, _path, text in chapters:
        ending = ending_text(text)
        score = hook_score(ending)
        is_golden = cid <= GOLDEN_MAX_CHAPTER
        band = ending_band(score, is_golden)
        scored.append({"chapter": cid, "score": score, "band": band, "is_golden": is_golden})
        if band == "warn":
            golden_note = ("（黄金三章，更严：开篇收尾平淡最劝退）" if is_golden else "")
            alerts.append({
                "type": "weak_chapter_ending",
                "entity": f"第{cid}章",
                "severity": "建议级",
                "chapter": cid,
                "evidence": ending[-40:] if ending else "(空结尾)",
                "auto": True,
                "note": (f"章末钩子分 {score}（阈值 "
                         f"{GOLDEN_THRESHOLD if is_golden else WARN_THRESHOLD}）偏低，疑平淡收尾"
                         f"{golden_note}——网文留存命门是断章，建议结尾留悬念/反转/危机未决/抛问题"),
            })

    return {
        "ran": True,
        "alerts": alerts,
        "scored": scored,
        "total": len(alerts),
        "blocking": 0,  # 断章是软留存信号，确定性机检永不硬挡（见模块/ main 说明）。
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="章末钩子/断章 确定性检查（建议级）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "hook_findings.json")
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
    print(f"{icon} 章末断章自检：{len(res['scored'])} 章，{res['total']} 章疑平淡收尾 → {out}")
    for a in res["alerts"]:
        print(f"  ⚠️ [{a['type']}] {a['entity']}（{a['note'].split('——')[0]}）")
    # 断章=软留存信号，确定性机检逮不到「形式对但钩假」，硬挡会误杀正常章——所以永远 exit 0。
    # 真正该不该改交 novel-score / 人判；这里只把候选写进报告供人/LLM 取舍。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
