#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tone_check.py — 情绪曲线对账：实测章节主导情绪 vs 设定/tone_curve.json 目标弧线（确定性·纯标准库）

`设定/tone_curve.json` 持有每章/每段的**目标**情感基调（被 draft_packets 注入任务包），
但此前没有任何东西回过头检验每章**实际写出来的**主导情绪是否贴合目标弧线——
SCORE 研究把"情绪一致性"当核心指标，本检测器补上这一环。

机制（确定性，不靠 LLM；宁缺毋滥）：
  1) 用中文情绪词库对每章正文做关键词计数 → 票数最高的情绪即"实测主导情绪"（无信号 → None）。
  2) 把 tone_curve 的目标标签（中/英自由文本如 "Light, comedic" / "curiosity" / "悲伤"）
     映射到同一套规范情绪集（同义词容错）。
  3) 实测 vs 目标不符（且都判得出）→ 报 type="tone_deviation" 建议级 alert。
     允许"邻近情绪"容差（见 ADJACENT）：相邻情绪不报（如 紧张 vs 恐惧），避免吹毛求疵。

全程优雅跳过：无 tone_curve.json / 某章无情绪信号 / 某段无目标 → 记 note 跳过，绝不臆造。
情绪一致性是**建议级**软信号，主程序 exit 0（advisory，不硬挡）。

  python3 tone_check.py <作品根> [--json]

测试：cd skills/novel-review/scripts && python3 -m pytest test_tone_check.py
"""
import os
import re
import sys
import json
import argparse
from datetime import date

# ── 规范情绪集 + 中文关键词词库 ────────────────────────────────────────────
# 每个规范情绪挂一串中文触发词（子串匹配，计数即票数）。词库刻意保守、互斥度高，
# 避免一个词同时落进多个情绪（宁缺毋滥）。
DEFAULT_LEXICON = {
    "喜悦": ["笑", "喜", "欢", "甜", "乐", "雀跃", "兴奋", "欣喜", "畅快", "开怀", "窃喜"],
    "悲伤": ["泪", "哀", "痛", "绝望", "悲", "哭", "凄", "心碎", "哽咽", "黯然", "怆", "呜咽"],
    "愤怒": ["怒", "恨", "咬牙", "暴", "愤", "恼", "狰狞", "切齿", "震怒", "戾", "火冒"],
    "恐惧": ["惧", "颤", "慌", "惊恐", "惊惧", "战栗", "毛骨悚然", "胆寒", "畏", "瑟缩", "骇"],
    "紧张": ["急", "危", "逼近", "千钧", "屏息", "凝重", "剑拔弩张", "迫", "命悬", "紧绷", "压迫"],
    "温情": ["暖", "柔", "相拥", "守护", "温", "依偎", "怀里", "轻抚", "安心", "缱绻", "脉脉"],
    "好奇悬疑": ["为何", "究竟", "谜", "诡异", "蹊跷", "古怪", "疑", "费解", "扑朔", "隐秘", "玄机"],
}

# 邻近情绪：实测 vs 目标落在同一组里视为"接近"，不报偏离（容差，降误报）。
ADJACENT = [
    {"紧张", "恐惧"},          # 危机/惊惧常交织
    {"好奇悬疑", "紧张"},      # 悬疑推进自带张力
    {"悲伤", "温情"},          # 催泪与暖意一线之隔
]

# 目标标签 → 规范情绪 的同义词映射（中/英自由文本，子串小写匹配）。
# tone_curve 的 target_vibe 多为英文（"Light, comedic"）或 tension-ledger 风格英文情绪词
# （curiosity/relief…），也兼容直接写中文规范标签。
_SYNONYMS = {
    "喜悦": ["喜悦", "欢乐", "轻松", "搞笑", "喜剧", "甜", "joy", "happy", "light", "comedic",
            "comedy", "cheer", "playful", "fun", "relief", "relax", "uplift", "bright"],
    "悲伤": ["悲伤", "悲", "哀", "凄", "虐", "催泪", "sad", "sorrow", "grief", "melancholy",
            "tragic", "tragedy", "mourn", "despair", "bleak"],
    "愤怒": ["愤怒", "怒", "恨", "暴", "anger", "angry", "rage", "fury", "wrath", "furious"],
    "恐惧": ["恐惧", "惊恐", "惊悚", "恐怖", "fear", "afraid", "terror", "horror", "dread", "scary"],
    "紧张": ["紧张", "压抑", "沉重", "危机", "紧绷", "tense", "tension", "gritty", "oppressive",
            "suspense", "intense", "thriller", "urgent", "高潮", "climax"],
    "温情": ["温情", "温暖", "治愈", "暖", "柔", "守护", "warm", "tender", "gentle", "heartwarming",
            "cozy", "sweet", "soft", "healing", "intimate"],
    "好奇悬疑": ["好奇", "悬疑", "悬念", "谜", "诡异", "curiosity", "curious", "mystery",
              "mysterious", "intrigue", "eerie", "uncanny", "enigma", "puzzling"],
}


# ── 纯函数（pytest 覆盖）──────────────────────────────────────────────────
def emotion_scores(text, lexicon=None):
    """对 text 按词库做关键词计数，返回 {规范情绪: 命中次数}（只含 >0 的项）。纯函数。"""
    lex = lexicon or DEFAULT_LEXICON
    scores = {}
    if not text:
        return scores
    for emo, words in lex.items():
        cnt = 0
        for w in words:
            if not w:
                continue
            cnt += text.count(w)
        if cnt > 0:
            scores[emo] = cnt
    return scores


# 高唤醒情绪：算张力分时计入（温情/悲伤/好奇属低唤醒或中性，不计张力）
TENSION_EMOTIONS = ("紧张", "恐惧", "愤怒")


def tension_score(text, lexicon=None):
    """0-10 张力分：高唤醒情绪信号密度 + 急促节奏标点，归一到 0-10。纯函数。

    空正文 → None（缺信号优雅放过）；真正平淡的章返回 0.0（这是有效测量，供 logic_sentry
    的"连续 N 章张力塌陷"检测用，不能当缺失）。命中权重高于标点，避免纯排版拉高张力。
    """
    if not text or not text.strip():
        return None
    scores = emotion_scores(text, lexicon=lexicon)
    hits = sum(scores.get(e, 0) for e in TENSION_EMOTIONS)
    punct = (text.count("！") + text.count("!") + text.count("？") + text.count("?")
             + text.count("——") + text.count("…"))
    chars = max(1, len(re.sub(r"\s", "", text)))
    density = (hits * 2 + punct) / chars * 1000.0
    return round(min(10.0, density), 1)


def dominant_emotion(text, lexicon=None):
    """返回 text 票数最高的规范情绪；无任何情绪信号 → None。纯函数。

    平票时取 DEFAULT_LEXICON 声明序的第一个（确定性，便于测试与复现）。
    """
    scores = emotion_scores(text, lexicon=lexicon)
    if not scores:
        return None
    lex = lexicon or DEFAULT_LEXICON
    order = list(lex.keys())
    best = max(scores.values())
    for emo in order:
        if scores.get(emo) == best:
            return emo
    return None


def map_target_emotion(label):
    """把 tone_curve 的目标标签（中/英自由文本）映射到规范情绪；无法判 → None。纯函数。

    子串小写匹配：第一个命中其同义词的规范情绪即采用（按 _SYNONYMS 声明序）。
    """
    if not label:
        return None
    low = str(label).lower()
    for emo, syns in _SYNONYMS.items():
        for s in syns:
            if s.lower() in low:
                return emo
    return None


def _adjacent(a, b):
    return any(a in grp and b in grp for grp in ADJACENT)


def tone_band(realized, target):
    """对账实测 vs 目标情绪 → 'ok' / 'warn'。纯函数。

    - ok：realized==target，或任一为 None（缺信号优雅放过），或两者属邻近情绪（容差）。
    - warn：两者都判得出、不相等、且非邻近 → 真偏离。
    """
    if realized is None or target is None:
        return "ok"
    if realized == target:
        return "ok"
    if _adjacent(realized, target):
        return "ok"
    return "warn"


# ── tone_curve 加载（容多种 shape）────────────────────────────────────────
def _target_label_from_entry(entry):
    """从一条 tone_curve 记录里取目标情绪自由文本（容多键名）。"""
    if not isinstance(entry, dict):
        return None
    for key in ("target_emotion", "emotion", "target_vibe", "vibe", "dominant_emotion",
                "arc_name", "mood"):
        v = entry.get(key)
        if v:
            return str(v)
    return None


def target_for_chapter(tone_data, chapter_index):
    """按章号取目标情绪标签（原始自由文本）。兼容两种 shape，找不到 → None。

      A) {"arcs": [{"range": "1-50", "target_vibe": "..."}]}  —— 段映射
      B) [{"chapter": N, "target_emotion"/"emotion"/"vibe": "..."}]  —— 逐章
         （也兼容 {"chapters": [...]} 包一层）
    """
    if not tone_data:
        return None
    # shape A: arcs + range
    arcs = tone_data.get("arcs") if isinstance(tone_data, dict) else None
    if arcs:
        for arc in arcs:
            if not isinstance(arc, dict):
                continue
            rng = str(arc.get("range", "")).replace("—", "-").split("-")
            try:
                lo, hi = int(rng[0]), int(rng[1])
            except (ValueError, IndexError):
                continue
            if lo <= chapter_index <= hi:
                return _target_label_from_entry(arc)
        return None
    # shape B: 逐章列表
    rows = tone_data
    if isinstance(tone_data, dict):
        rows = tone_data.get("chapters") or tone_data.get("curve") or []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("chapter") == chapter_index:
                return _target_label_from_entry(row)
    return None


def _load_tone_curve(project):
    """读 设定/tone_curve.json；缺/坏 → None（据此优雅跳过整个检测器）。"""
    path = os.path.join(project, "设定", "tone_curve.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _list_chapters(project):
    """复用 novel-wiki/wiki_builder.list_chapters → [(idx, title|path, text)]。

    取每条三元组的首元素(章号)与末元素(正文)，对 (idx, path, text) 与 (idx, title, text) 两种
    返回布局都稳健。导入失败 → []（优雅跳过）。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    wiki_scripts = os.path.abspath(os.path.join(here, "..", "..", "novel-wiki", "scripts"))
    if wiki_scripts not in sys.path:
        sys.path.insert(0, wiki_scripts)
    try:
        from wiki_builder import list_chapters
    except Exception:
        return []
    out = []
    for row in list_chapters(project):
        if not row:
            continue
        idx = row[0]
        text = row[-1]
        out.append((idx, text))
    return out


# ── 主分析 ────────────────────────────────────────────────────────────────
def analyze(project):
    """逐章实测主导情绪 vs tone_curve 目标弧线 → {"alerts": [...], "chapters": [...]}。"""
    tone_data = _load_tone_curve(project)
    if tone_data is None:
        return {
            "ran": False,
            "skipped": "无 设定/tone_curve.json（情绪曲线未配置）——跳过情绪曲线对账",
            "alerts": [],
            "chapters": [],
        }

    alerts = []
    chapters = []
    for idx, text in _list_chapters(project):
        target_label = target_for_chapter(tone_data, idx)
        target = map_target_emotion(target_label)
        realized = dominant_emotion(text)
        band = tone_band(realized, target)
        chapters.append({
            "chapter": idx,
            "target": target,
            "target_label": target_label,
            "realized": realized,
            "tension_score": tension_score(text),
            "band": band,
        })
        if band == "warn":
            alerts.append({
                "type": "tone_deviation",
                "entity": f"第{idx}章情绪",
                "severity": "建议级",
                "chapter": idx,
                "target": target,
                "realized": realized,
                "evidence": f"目标基调「{target}」(原文标签: {target_label})，实测主导情绪「{realized}」",
                "auto": True,
                "note": (f"本章实测主导情绪「{realized}」与设定目标基调「{target}」明显不符"
                         f"（非邻近情绪）——情绪曲线偏离候选，请人判：是否写偏了 Arc 的情感基调"),
            })
    return {"ran": True, "alerts": alerts, "chapters": chapters}


def measure_chapters(project):
    """逐章确定性实测 (dominant_emotion, tension_score)，不依赖 tone_curve。纯读。"""
    rows = []
    for idx, text in _list_chapters(project):
        rows.append({
            "chapter": idx,
            "dominant_emotion": dominant_emotion(text),
            "tension_score": tension_score(text),
        })
    return rows


def write_progression(project):
    """把逐章实测的 dominant_emotion / tension_score 回填 设定/emotional_progression.json。

    此前该文件由 arc_memory.scaffold 建成空壳（dominant_emotion=""、tension_score=None），
    仓库内无任何脚本回填 → logic_sentry 的"张力塌陷"检测永久 no-op。这里把 tone_check 已能算的
    情绪/张力接到存储上：**只覆盖这两个确定性字段并标 auto_measured**，保留人工字段
    （reader_promise_progress / next_emotional_debt）。返回写入的章数。"""
    emo_path = os.path.join(project, "设定", "emotional_progression.json")
    try:
        with open(emo_path, encoding="utf-8") as f:
            emo = json.load(f)
    except (OSError, json.JSONDecodeError):
        emo = {}
    if emo.get("kind") != "novel_emotional_progression":
        emo = {"schema_version": 1, "kind": "novel_emotional_progression", "chapters": []}
    by_ch = {int(c.get("chapter") or 0): c for c in emo.get("chapters", []) if isinstance(c, dict)}
    measured = measure_chapters(project)
    for row in measured:
        ch = int(row["chapter"])
        node = by_ch.get(ch)
        if node is None:
            node = {"chapter": ch, "reader_promise_progress": "", "next_emotional_debt": ""}
            by_ch[ch] = node
        node["dominant_emotion"] = row["dominant_emotion"] or ""
        node["tension_score"] = row["tension_score"]
        node["auto_measured"] = True
    emo["chapters"] = [by_ch[k] for k in sorted(by_ch)]
    emo["updated_at"] = date.today().isoformat()
    os.makedirs(os.path.dirname(emo_path), exist_ok=True)
    tmp = emo_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(emo, f, ensure_ascii=False, indent=2)
    os.replace(tmp, emo_path)
    return len(measured)


def main(argv=None):
    p = argparse.ArgumentParser(description="情绪曲线对账：实测章节主导情绪 vs tone_curve 目标弧线")
    p.add_argument("project_path")
    p.add_argument("--json", action="store_true", help="把结果 JSON 打到 stdout")
    p.add_argument("--write-progression", action="store_true",
                   help="把逐章实测 dominant_emotion/tension_score 回填 设定/emotional_progression.json（激活 logic_sentry 张力塌陷检测）")
    args = p.parse_args(argv)

    if args.write_progression:
        n = write_progression(args.project_path)
        print(f"✅ 已回填情绪/张力实测到 设定/emotional_progression.json（{n} 章）")
        return 0

    result = analyze(args.project_path)

    out_dir = os.path.join(args.project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "tone_findings.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not result.get("ran"):
        print(f"⏭️  情绪曲线对账跳过：{result.get('skipped')} → {out_path}")
    else:
        n = len(result["alerts"])
        if n:
            print(f"⚠️ 情绪曲线对账：{n} 条偏离候选（建议级）→ {out_path}")
            for a in result["alerts"]:
                print(f"  [建议级] {a['type']} · {a['entity']} · {a['evidence']}")
        else:
            print(f"✅ 情绪曲线对账：实测情绪贴合目标弧线，0 偏离 → {out_path}")
    # 情绪一致性是建议级软信号，永不硬挡（advisory）。
    return 0


if __name__ == "__main__":
    sys.exit(main())
