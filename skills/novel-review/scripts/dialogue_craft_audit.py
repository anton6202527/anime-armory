#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dialogue_craft_audit.py — 对白工艺机检（advisory·纯标准库）。

为什么：对白是网文阅读时间占比最高的成分，此前机检只有 voice_drift（口头禅漂移）
和 prose_craft 的对话占比——**对白本身的戏剧质量完全没有确定性信号**。本模块把
三条传统对白手艺变成可测信号（全 advisory，对白好坏终归人判）：

  ① on_the_nose_dialogue   直给对白（编剧术语 on-the-nose）——角色把情绪和动机原样
                           说出口（"我很生气，因为你背叛了我"）。判据：引号内
                           情绪标签词 + 因果连词（因为/所以）同句共现。真人说话
                           会绕、会岔、会咽回去；潜台词为零的对白是台词朗读。
  ② frictionless_dialogue  零摩擦章（Donald Maass 微张力）——line 级张力不靠情节
                           冲突，靠对话里的**抵抗**：顶回去/岔开/反问/收住不说。
                           一整章对话量足够却一个摩擦标记都没有=全员合作直答，
                           微张力为零，读者在"平路"上走。词表 keyword_banks.FRICTION_KW。
  ③ as_you_know_dialogue   信息播报对白——"你也知道，我们家三代单传……"：说话人向
                           本来就知道的对方复述设定，实为对读者广播（对白味 info
                           dump，与 prose_craft 的叙述侧 info_dump_opening 互补）。
                           判据：AS_YOU_KNOW_MARKERS 命中 + 同段陈述够长。
  ④ subtext_spoken_aloud   潜台词被说破——scene_cards 里登记了 subtext（这场戏的
                           水面下），正文对白却把它原样念出来=潜台词升到水面，
                           设计报废。与 manuscript_map 的 SENSORY-ANCHOR-DROPPED
                           互为镜像：意象锚该出现而没出现；潜台词**不该**出现而出现。

诚实声明：对白质量是最"软"的工艺，本模块只逮确定性形态（词面共现），逮不到
"形式有摩擦但假"或"直给得恰到好处"（有时直给正是高潮的正确写法——所以恒
advisory、宁缺毋滥、绝不阻断）。

用法：
    python3 dialogue_craft_audit.py <作品根> [--json]
测试：cd skills/novel-review/scripts && python3 -m pytest test_dialogue_craft_audit.py
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "novel", "_lib"))
for _p in (_WIKI, _LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from wiki_builder import list_chapters
except Exception:
    def list_chapters(project, *a, **k):  # type: ignore
        return []
try:
    from keyword_banks import EMOTION_LABEL_KW, FRICTION_KW, AS_YOU_KNOW_MARKERS
except Exception:
    EMOTION_LABEL_KW = FRICTION_KW = AS_YOU_KNOW_MARKERS = []
# 对话行拆分复用 prose_craft_audit 的单一实现（同目录），避免两套引号口径漂移。
try:
    from prose_craft_audit import split_narration_dialogue
except Exception:
    def split_narration_dialogue(text):  # type: ignore
        return [], []

# ── 阈值（internal-heuristic·env 可标定·全 advisory）─────────────────────────
ONTN_PER_CH = int(os.environ.get("NOVEL_DIALOGUE_ONTN_PER_CH", "3"))       # 直给句/章 上限
FRICTION_MIN_LINES = int(os.environ.get("NOVEL_DIALOGUE_FRICTION_MIN", "24"))  # 零摩擦判定的对话行下限
AYK_MIN_CHARS = int(os.environ.get("NOVEL_DIALOGUE_AYK_MIN_CHARS", "40"))  # 播报句最短长度
SUBTEXT_MIN_LEN = int(os.environ.get("NOVEL_DIALOGUE_SUBTEXT_MIN_LEN", "4"))  # 潜台词短语最短匹配长度
PROVENANCE = "internal-heuristic·confidence=low"

_CAUSAL_RE = re.compile(r"因为|所以|由于|正因")
# 情绪自陈形态："我(真/好/很/太/非常/实在)?<情绪标签词>"——第一人称把情绪直接命名。
_SELF_EMOTION_RE = None  # 延迟编译（依赖词库导入结果）
_EXEMPT_TITLE_RE = re.compile(r"番外|楔子|序章|回顾|尾声|后记|人物志|设定集")


def _self_emotion_re():
    global _SELF_EMOTION_RE
    if _SELF_EMOTION_RE is None:
        words = "|".join(map(re.escape, EMOTION_LABEL_KW)) or "$^"
        _SELF_EMOTION_RE = re.compile(r"我(?:真|好|很|太|非常|实在|只是)?(?:感到|觉得)?(?:" + words + r")")
    return _SELF_EMOTION_RE


def on_the_nose_hits(dialogue_lines):
    """直给对白句：引号内 情绪自陈("我很生气") 且 同句带因果连词。返回命中句列表。纯函数。

    双条件共现才计——只情绪自陈可能是合法直给（人类也直说"我怕"），
    情绪 + 因果链条完整说出口（"我很生气，因为…"）才是教科书式 on-the-nose。
    """
    hits = []
    pat = _self_emotion_re()
    for line in dialogue_lines or []:
        for sent in re.split(r"[。！？!?]", line):
            if pat.search(sent) and _CAUSAL_RE.search(sent):
                hits.append(sent.strip()[:40])
    return hits


def friction_count(dialogue_lines):
    """对话行中摩擦标记（顶回去/岔开/反问/拒绝）总次数。纯函数。"""
    text = "\n".join(dialogue_lines or [])
    return sum(text.count(w) for w in FRICTION_KW)


def as_you_know_hits(dialogue_lines):
    """信息播报句：AS_YOU_KNOW_MARKERS 命中且该行足够长（短句寒暄不算）。纯函数。"""
    hits = []
    for line in dialogue_lines or []:
        if len(line) >= AYK_MIN_CHARS and any(m in line for m in AS_YOU_KNOW_MARKERS):
            hits.append(line[:40])
    return hits


def _load_scene_subtexts(project):
    """{chapter: [subtext 短语]}——scene_cards.json 里登记的水面下设计。缺文件→{}。"""
    path = os.path.join(project, "设定", "scene_cards.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    out = {}
    for sc in (data.get("scenes") or []):
        if not isinstance(sc, dict):
            continue
        sub = str(sc.get("subtext") or "").strip()
        ch = sc.get("chapter")
        if sub and isinstance(ch, int):
            out.setdefault(ch, []).append(sub)
    return out


def subtext_spoken_hits(dialogue_lines, subtexts):
    """潜台词短语（≥SUBTEXT_MIN_LEN 字，取最长片段）在对白中逐字出现 → 被说破。纯函数。

    subtext 卡片常是整句设计（"他其实早认出她，但不能认"），对白不会全句照抄——
    取其中最长的连续短语片段（按标点切）做子串匹配，够长才可信。
    """
    hits = []
    joined = "\n".join(dialogue_lines or [])
    for sub in subtexts or []:
        frags = [f.strip() for f in re.split(r"[，。；、！？,;!?\s]", sub) if len(f.strip()) >= SUBTEXT_MIN_LEN]
        for frag in sorted(frags, key=len, reverse=True):
            if frag in joined:
                hits.append({"subtext": sub[:30], "fragment": frag})
                break
    return hits


def analyze(project):
    """novel-review 检测器契约：{ran, alerts, chapters, total, blocking(=0)}。"""
    chapters = [(cid, path, text) for cid, path, text in list_chapters(project)
                if not _EXEMPT_TITLE_RE.search(os.path.basename(str(path or "")))]
    if not chapters:
        return {"ran": False, "skipped": "无章节——先有正文再查对白工艺"}
    subtext_by_ch = _load_scene_subtexts(project)

    alerts, rows = [], []
    for cid, _path, text in chapters:
        _, dialogue = split_narration_dialogue(text or "")
        n_lines = len(dialogue)
        fric = friction_count(dialogue)
        rows.append({"chapter": cid, "dialogue_lines": n_lines, "friction": fric})

        ontn = on_the_nose_hits(dialogue)
        if len(ontn) >= ONTN_PER_CH:
            alerts.append({"type": "on_the_nose_dialogue", "severity": "建议级", "auto": True,
                           "chapter": cid, "evidence": "；".join(ontn[:2]),
                           "note": (f"第{cid}章 {len(ontn)} 句直给对白（情绪自陈+因果连词同句，如「{ontn[0]}」）"
                                    f"——on-the-nose：角色把心里话原样念出来，潜台词为零；真人会绕、会岔、"
                                    f"会咽回去。改法：让情绪走动作/岔开/反话，把因果链留给读者拼（{PROVENANCE}）")})

        if n_lines >= FRICTION_MIN_LINES and fric == 0:
            alerts.append({"type": "frictionless_dialogue", "severity": "建议级", "auto": True,
                           "chapter": cid,
                           "note": (f"第{cid}章 {n_lines} 行对话零摩擦标记——全员合作直答（有问必答、"
                                    f"无人顶撞/岔开/反问/拒绝）。Maass 微张力手艺：每页张力不靠情节，"
                                    f"靠对话里的抵抗——谁在隐瞒、谁在误读、谁在顶回去；至少给一处"
                                    f"（{PROVENANCE}）")})

        ayk = as_you_know_hits(dialogue)
        if ayk:
            alerts.append({"type": "as_you_know_dialogue", "severity": "info", "auto": True,
                           "chapter": cid, "evidence": ayk[0],
                           "note": (f"第{cid}章 {len(ayk)} 处播报式对白（「你也知道…」+长段陈述）——"
                                    f"说话人向已知情的对方复述设定=对读者广播；改法：让不知情者问出来，"
                                    f"或拆进冲突按需露出（{PROVENANCE}）")})

        spoken = subtext_spoken_hits(dialogue, subtext_by_ch.get(cid))
        for h in spoken:
            alerts.append({"type": "subtext_spoken_aloud", "severity": "建议级", "auto": True,
                           "chapter": cid, "subtext": h["subtext"], "fragment": h["fragment"],
                           "note": (f"第{cid}章场景卡潜台词「{h['subtext']}」的片段「{h['fragment']}」被角色"
                                    f"在对白里说破——潜台词升到水面=这场戏的水下设计报废；要么让它继续"
                                    f"沉着（言行侧漏），要么改场景卡承认这场就是摊牌戏（{PROVENANCE}）")})

    return {
        "ran": True,
        "thresholds": {"ontn_per_ch": ONTN_PER_CH, "friction_min_lines": FRICTION_MIN_LINES,
                       "ayk_min_chars": AYK_MIN_CHARS, "subtext_min_len": SUBTEXT_MIN_LEN,
                       "provenance": PROVENANCE,
                       "note": "advisory：直给有时是高潮的正确写法，恒不阻断，取舍归人判。"},
        "chapters": rows,
        "alerts": alerts,
        "total": len(alerts),
        "blocking": 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="对白工艺机检（advisory）")
    ap.add_argument("project_path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = analyze(args.project_path)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "dialogue_craft_findings.json")
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
    print(f"{icon} 对白工艺机检：{len(res['chapters'])} 章，{res['total']} 条提示")
    for a in res["alerts"]:
        print(f"  - [{a['severity']}] {a['type']}: {a['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
