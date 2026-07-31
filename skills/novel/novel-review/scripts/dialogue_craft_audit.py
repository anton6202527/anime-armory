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

2026-07 第五轮增（对白**归属**工艺三信号，出处见 novel/Q&A.md Q13）：
  ⑤ said_bookism           华丽说话动词（Elmore Leonard 第 3 条 / Browne & King
                           checklist）——"咆哮道/娇嗔道/咬牙切齿道"把情绪塞进 tag，
                           台词与动作节拍失职。中文口径：说/道/笑道/叹道等传统
                           朴素与白话惯用 tag 合法，只逮词表内华丽形态的章内密度
                           （词表 keyword_banks.SAID_BOOKISM_KW，全 X…道 复合形，
                           词面即 tag 零歧义）。与 prose_craft 的 adverb_dialogue_tag
                           正交：那查"副词+说"，这查动词本身被替换。
  ⑥ untagged_dialogue_run  长对话无归属跟丢（Self-Editing 实务：几行内须重新锚定
                           说话人）——连续 ≥N 行**纯引语**（引号外零叙述字）读者
                           数不清谁在说。生产实锤：王敦外传第20章 3-5 轮无标签
                           问答已近失锚。两人快节奏对峙故意去 tag 合法，故阈值
                           取保守 8 行、恒 advisory。
  ⑦ talking_heads_run      悬浮头对话 / white-room（K.M. Weiland talking heads；
                           编辑判据：对白必须周期性被动作/环境/内心 beat 打断）——
                           连续 ≥N 行对话行、每行引号外叙述字 <beat 下限（tag 本身
                           不算 beat），人物成了白房间里的两颗悬浮头。电话/审讯
                           场景合法，恒 advisory。

诚实声明：对白质量是最"软"的工艺，本模块只逮确定性形态（词面共现），逮不到
"形式有摩擦但假"或"直给得恰到好处"（有时直给正是高潮的正确写法——所以恒
advisory、宁缺毋滥、绝不阻断）。

用法：
    python3 dialogue_craft_audit.py <作品根> [--json]
测试：cd skills/novel/novel-review/scripts && python3 -m pytest test_dialogue_craft_audit.py
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WIKI = os.path.abspath(os.path.join(_HERE, "..", "..", "novel-wiki", "scripts"))
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
for _p in (_WIKI, _LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from wiki_builder import list_chapters
except Exception:
    def list_chapters(project, *a, **k):  # type: ignore
        return []
try:
    from keyword_banks import (EMOTION_LABEL_KW, FRICTION_KW, AS_YOU_KNOW_MARKERS,
                               SAID_BOOKISM_KW)
except Exception:
    EMOTION_LABEL_KW = FRICTION_KW = AS_YOU_KNOW_MARKERS = SAID_BOOKISM_KW = []
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
BOOKISM_PER_CH = int(os.environ.get("NOVEL_DIALOGUE_BOOKISM_PER_CH", "4"))     # 华丽说话动词/章 上限
UNTAGGED_RUN = int(os.environ.get("NOVEL_DIALOGUE_UNTAGGED_RUN", "8"))         # 连续纯引语行（零归属）
BEAT_MIN_CHARS = int(os.environ.get("NOVEL_DIALOGUE_BEAT_MIN_CHARS", "6"))     # 引号外叙述字≥此数算 beat
TALKING_HEADS_RUN = int(os.environ.get("NOVEL_DIALOGUE_HEADS_RUN", "12"))      # 连续无 beat 对话行
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


def said_bookism_counts(text):
    """{华丽说话动词: 次数}（只留 >0 项）。纯函数。词表全为 X…道 复合形——词面即
    对话 tag，不必再判引号邻接（"咆哮道"不会出现在非 tag 语境）。"""
    t = text or ""
    out = {}
    for w in SAID_BOOKISM_KW:
        c = t.count(w)
        if c:
            out[w] = c
    return out


_QUOTE_SPAN_RE = re.compile(r"[「『][^」』]*[」』]?|“[^”]*”?|\"[^\"]*\"")
_CJK_CHAR_RE = re.compile(r"[一-鿿]")
# 对话行判定与 prose_craft 同口径（引号开头，可带 ≤12 字前置人名短语）。
_DIALOGUE_HEAD_RE = re.compile(r"^[^「“\"『]{0,12}[「“\"『]")


def dialogue_beat_runs(text):
    """按行序扫描，返回 (最长纯引语连续行数, 最长无 beat 对话连续行数)。纯函数·可测。

    对每个对话行剥掉引号内内容，数**引号外**剩余 CJK 字：
      =0        → 纯引语行（零归属：没有 tag、没有动作、没有前置人名）
      <BEAT_MIN → 无 beat 行（"他说"式裸 tag 有归属但无场景锚定，不算 beat）
    叙述行两个 run 都清零（一段叙述既是归属锚也是 beat）；空行跳过不断 run
    （md 段间空行不是叙述）。两信号阈值不同、语义不同：untagged 管"谁在说"
    跟丢，talking heads 管"人在哪"悬浮。"""
    untagged_run = untagged_best = 0
    beatless_run = beatless_best = 0
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if _DIALOGUE_HEAD_RE.match(s):
            outside = len(_CJK_CHAR_RE.findall(_QUOTE_SPAN_RE.sub("", s)))
            untagged_run = untagged_run + 1 if outside == 0 else 0
            beatless_run = beatless_run + 1 if outside < BEAT_MIN_CHARS else 0
        else:
            untagged_run = beatless_run = 0
        untagged_best = max(untagged_best, untagged_run)
        beatless_best = max(beatless_best, beatless_run)
    return untagged_best, beatless_best


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

        bookisms = said_bookism_counts(text)
        bookism_n = sum(bookisms.values())
        if bookism_n >= BOOKISM_PER_CH:
            top = sorted(bookisms.items(), key=lambda kv: -kv[1])[:4]
            alerts.append({"type": "said_bookism", "severity": "建议级", "auto": True,
                           "chapter": cid, "top": [{"verb": v, "count": c} for v, c in top],
                           "note": (f"第{cid}章华丽说话动词 {bookism_n} 处"
                                    f"（{'、'.join(f'{v}×{c}' for v, c in top)}，阈 {BOOKISM_PER_CH}）——"
                                    f"Leonard 手艺：对话动词只留朴素的说/道（笑道/叹道等白话惯用合法），"
                                    f"『咆哮道/娇嗔道』是把情绪塞进标签喊出来；情绪该由台词内容和"
                                    f"动作节拍承载（{PROVENANCE}）")})

        untagged_best, beatless_best = dialogue_beat_runs(text)
        if untagged_best >= UNTAGGED_RUN:
            alerts.append({"type": "untagged_dialogue_run", "severity": "建议级", "auto": True,
                           "chapter": cid, "run": untagged_best,
                           "note": (f"第{cid}章连续 {untagged_best} 行纯引语（引号外零字：无 tag、"
                                    f"无动作、无前置人名，阈 {UNTAGGED_RUN}）——长对话无归属跟丢：读者"
                                    f"数不清谁在说，回读即弃感；传统实务是每几行用 tag 或动作 beat "
                                    f"重新锚定说话人（两人快节奏对峙故意去 tag 合法，人工取舍）"
                                    f"（{PROVENANCE}）")})
        elif beatless_best >= TALKING_HEADS_RUN:
            alerts.append({"type": "talking_heads_run", "severity": "建议级", "auto": True,
                           "chapter": cid, "run": beatless_best,
                           "note": (f"第{cid}章连续 {beatless_best} 行对话每行引号外叙述 <{BEAT_MIN_CHARS} 字"
                                    f"（裸 tag 不算 beat，阈 {TALKING_HEADS_RUN}）——talking heads/白房间：人物"
                                    f"只剩两颗悬浮头在真空里说话；每隔几轮给一个动作/环境/内心 beat，"
                                    f"让对话落回身体和房间（电话/审讯等场景合法，人工取舍）（{PROVENANCE}）")})

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
                       "bookism_per_ch": BOOKISM_PER_CH, "untagged_run": UNTAGGED_RUN,
                       "beat_min_chars": BEAT_MIN_CHARS, "talking_heads_run": TALKING_HEADS_RUN,
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
