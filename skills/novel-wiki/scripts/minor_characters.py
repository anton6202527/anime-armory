#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
minor_characters.py — 配角连续性盲区报告（建议级·纯标准库）

动态百科只从 设定/角色卡.md（主角们）播种，**未进角色卡的配角**状态/称谓漂移全程无人跟踪：
配角反复出场却没建卡 → logic_sentry 的死人复活/位置跳变等也覆盖不到他。本脚本扫全书，把
「反复出场（≥N 章）却没建角色卡」的配角候选挑出来，提示建卡/纳入百科，闭合这个盲区。

判据（保守·宁缺毋滥，命中只作"建卡候选→人判"）：
  候选名 = ① 对话归属式：`<名>说/道/问/答/笑道/喝道/冷笑/叹道` 前的 2-4 字 CJK 专名
          ② 称谓式：老X / 小X / X姑娘/公子/大人/将军/嬷嬷/掌柜/大夫/道长/管家/老板…
  过滤：去掉 角色卡 已有名、停用词（他/她/众人/有人…）；只留**出现在 ≥min_chapters 个不同章**的，
  靠"跨章复现"压掉一次性误报（随机噪声不会在 3+ 章里同名复现）。

第二类信号 `major_character_absent`（配角失踪，braided-stories 编辑实务）：反复出场的具名角色
（角色卡名+别名归一，或高频配角候选）从最后出场章起连续缺席超阈值 → 提醒。多线长篇的高发病是
支线角色一挂就是几十章，读者回来时已忘光；持有未闭合线索（open_threads 提及）的角色失踪加重措辞。
已按 state_ledger 结构化生命周期事件（death/exit 未被 revival 解除）或动态百科亡故记录退场者豁免；
关键词式退场（_EXIT_RE 级）不可靠故不豁免——有意退场请忽略该条或补登结构化退场事件。

软冲突——纯启发式 NER（无模型），只报建议级候选，绝不阻断。
依赖 wiki_builder（list_chapters/parse_character_names/_CJK）与 graph_sentry（别名归一/退场账）。
纯函数（抽取/聚合/定档/缺席判定）带 pytest。

  python3 minor_characters.py <作品根> [--min-chapters 3] [--json]

阈值 env：NOVEL_ABSENT_MIN_APPEARANCES（累计出场≥此章数才纳入失踪监控，默认 5）
        NOVEL_ABSENT_RUN（高频角色缺席≥此章数报警，默认 8）
        NOVEL_ABSENT_RUN_MINOR（低频角色的放宽阈值，默认 15）
        NOVEL_ABSENT_MAJOR_FLOOR（出场≥此章数按高频阈值，否则按放宽阈值，默认 10）
"""
import os
import re
import sys
import json
import argparse
from collections import defaultdict

from wiki_builder import list_chapters, parse_character_names, _CJK
from graph_sentry import (_iter_character_changes, resolved_alias_map, _canonical,
                          _DEATH_EXIT_EVENTS, _REVIVAL_EVENTS, _load_json)

DEFAULT_MIN_CHAPTERS = 3

# 配角失踪阈值（env 可标定，见模块 docstring）
ABSENT_MIN_APPEARANCES = int(os.environ.get("NOVEL_ABSENT_MIN_APPEARANCES", "5"))
ABSENT_RUN = int(os.environ.get("NOVEL_ABSENT_RUN", "8"))
ABSENT_RUN_MINOR = int(os.environ.get("NOVEL_ABSENT_RUN_MINOR", "15"))
ABSENT_MAJOR_FLOOR = int(os.environ.get("NOVEL_ABSENT_MAJOR_FLOOR", "10"))
ABSENT_MAX_ALERTS = 6  # 每书最多报此数条，按缺席时长降序取头部

# ① 对话归属式：2-3 字名 + 说话动词。名非贪婪、动词用 lookahead（多字动词在前），
#    避免贪婪把动词首字吃进名里（治"钱五笑道"误抽成"钱五笑"）。
# 高精度对话归属式：名须在句首/标点/引号收尾后（真主语），紧跟**多字说话动词**。
# 只用多字 speech 动词——单字 道/说 会误吞 知道/听说/味道/难道，故排除；"低声"等会被并入动词、不漏成名。
_SPEECH = (r"(?:说道|笑道|冷笑道|喝道|怒喝道|怒道|叹道|轻叹道|沉声道|低声道|轻声道|柔声道|"
           r"冷声道|淡淡道|问道|答道|应道|回道|开口道|抬眼道|拱手道)")
_ATTR_RE = re.compile(r"(?:^|[，。！？；：、\n　“”\"「」『』（）()])([" + _CJK + r"]{2,3})" + _SPEECH)

# 宫廷位号式（高精度·补"只被提及不开口"的配角）：**单字姓 + 罕见封号/职称**，整体即实体
# （张才人/安美人/王嬷嬷）。只取恰好 1 个姓字（避免"替张才人"误吞成"替张才人"），且姓字不在
# 角色位号停用集（滤掉"掌事姑姑/老嬷嬷"这类描述性而非人名）。office 类(尚书/侍郎)易与机构混，不取。
_RANK_RE = re.compile(
    r"([" + _CJK + r"])(才人|美人|贵人|贵妃|淑妃|德妃|贤妃|惠妃|丽妃|婕妤|昭仪|嬷嬷|公公|姑姑)")
_RANK_NAME_STOP = {"老", "小", "那", "这", "众", "的", "本", "大", "掌", "事", "一", "二", "三",
                   "某", "贴", "管", "首", "总", "副", "亲", "干", "义", "婆"}

# 停用词：代词/泛称（即便接说话动词也不是专名）。
_STOPWORDS = {
    "他", "她", "它", "我", "你", "您", "咱", "谁", "众人", "有人", "那人", "这人", "众", "大家",
    "旁人", "路人", "对方", "二人", "两人", "三人", "几人", "此人", "来人", "众侍", "侍卫", "宫人",
    "那女", "那男", "那老", "妇人", "老者", "少年", "少女", "男子", "女子", "众妃", "众臣", "左右",
}


def extract_name_candidates(text):
    """单章文本 → 配角候选名集合（高精度对话归属：名+多字说话动词，去代词/泛称）。纯函数·可测。"""
    cands = set()
    for m in _ATTR_RE.finditer(text):
        nm = m.group(1)
        if nm not in _STOPWORDS:
            cands.add(nm)
    for m in _RANK_RE.finditer(text):
        if m.group(1) not in _RANK_NAME_STOP:
            cands.add(m.group(1) + m.group(2))   # 单字姓+位号 即实体
    return cands


def aggregate_candidates(per_chapter):
    """[(chapter_idx, {names})] → {name: [chapters...]}（每名出现的不同章列表，升序）。纯函数·可测。"""
    seen = defaultdict(set)
    for idx, names in per_chapter:
        for n in names:
            seen[n].add(idx)
    return {n: sorted(chs) for n, chs in seen.items()}


def recurring_untracked(agg, tracked_names, min_chapters=DEFAULT_MIN_CHAPTERS):
    """聚合表 → 反复出场（≥min_chapters 章）却不在角色卡的配角候选。纯函数·可测。

    剔除：① 已在角色卡的名 ② 作为已跟踪名子串/超串的（老张 vs 张三 不强配，但完全等于角色卡名才剔）。
    返回 [(name, [chapters])] 按出现章数降序。"""
    tracked = set(tracked_names or [])
    out = []
    for name, chs in agg.items():
        if name in tracked:
            continue
        if len(chs) >= min_chapters:
            out.append((name, chs))
    out.sort(key=lambda kv: (-len(kv[1]), kv[0]))
    return out


def build_presence(chapter_texts, name_groups):
    """{规范名: {变体名}} × [(章号, 正文)] → {规范名: [出场章升序]}（任一变体子串命中即在场）。

    子串在场判定故意宽松（宁把"被提及"当在场）：在场误判只会**压掉**失踪告警，方向保守。纯函数·可测。"""
    presence = {canon: [] for canon in name_groups}
    for idx, text in chapter_texts:
        for canon, variants in name_groups.items():
            if any(v in text for v in variants):
                presence[canon].append(idx)
    return {c: sorted(set(chs)) for c, chs in presence.items() if chs}


def absent_characters(presence, last_chapter, *, min_appearances=ABSENT_MIN_APPEARANCES,
                      run_major=ABSENT_RUN, run_minor=ABSENT_RUN_MINOR,
                      major_floor=ABSENT_MAJOR_FLOOR, exited=None, open_thread_names=None):
    """出场分布 → 失踪角色清单 [(名, last_seen, 缺席章数, 出场章数, 持线索否)]，缺席降序。纯函数·可测。

    出场 ≥min_appearances 章才纳入监控；高频（≥major_floor 章）缺 run_major 章即报，
    低频放宽到 run_minor 章；已登记退场者豁免。"""
    exited = exited or set()
    open_thread_names = open_thread_names or set()
    out = []
    for name, chapters in presence.items():
        if len(chapters) < min_appearances or name in exited:
            continue
        last_seen = chapters[-1]
        absent = last_chapter - last_seen
        required = run_major if len(chapters) >= major_floor else run_minor
        if absent >= required:
            out.append((name, last_seen, absent, len(chapters), name in open_thread_names))
    out.sort(key=lambda t: (-t[2], t[0]))
    return out


def _exited_characters(project, alias_map):
    """已退场角色规范名集合：state_ledger 结构化生命周期事件（death/exit 未被 revival 解除）
    ∪ 动态百科亡故记录。只认结构化登记（与 graph_sentry 硬闸同口径），关键词退场不豁免。"""
    exited = set()
    ledger = _load_json(os.path.join(project, "审稿", "state_ledger.json")) or {}
    if isinstance(ledger, dict):
        for _ch, raw_name, _change, event in _iter_character_changes(ledger):
            if not event:
                continue
            name = _canonical(raw_name, alias_map)
            if event in _REVIVAL_EVENTS:
                exited.discard(name)
            elif event in _DEATH_EXIT_EVENTS:
                exited.add(name)
    wiki = _load_json(os.path.join(project, "设定", "动态百科.json"))
    if isinstance(wiki, dict):
        for name, ent in wiki.items():
            if isinstance(ent, dict) and ent.get("status") in ("deceased", "dead"):
                exited.add(_canonical(name, alias_map))
    return exited


def _open_thread_holders(project, name_groups):
    """open_threads 文本里被点名的规范名集合（持有未闭合线索的角色失踪要加重措辞）。"""
    ledger = _load_json(os.path.join(project, "审稿", "state_ledger.json")) or {}
    threads = ledger.get("open_threads") if isinstance(ledger, dict) else None
    blob = "；".join(json.dumps(t, ensure_ascii=False) if isinstance(t, (dict, list)) else str(t)
                    for t in (threads if isinstance(threads, list) else []))
    if not blob:
        return set()
    return {canon for canon, variants in name_groups.items() if any(v in blob for v in variants)}


def absence_alerts(project, chapter_texts, tracked, candidate_names):
    """配角失踪检测入口：别名归一 → 出场分布 → 缺席判定 → alert 列表（≤ABSENT_MAX_ALERTS 条）。"""
    if not chapter_texts:
        return []
    last_chapter = max(idx for idx, _ in chapter_texts)
    ledger = _load_json(os.path.join(project, "审稿", "state_ledger.json")) or {}
    alias_map = resolved_alias_map(project, ledger if isinstance(ledger, dict) else {})
    name_groups = {}
    for name in set(tracked) | set(candidate_names):
        if len(name) < 2:
            continue
        name_groups.setdefault(_canonical(name, alias_map), set()).add(name)
    presence = build_presence(chapter_texts, name_groups)
    flagged = absent_characters(
        presence, last_chapter,
        exited=_exited_characters(project, alias_map),
        open_thread_names=_open_thread_holders(project, name_groups))
    alerts = []
    for name, last_seen, absent, count, holds_thread in flagged[:ABSENT_MAX_ALERTS]:
        thread_note = ("——且 open_threads 里仍点着他的名：持有未闭合线索的角色失踪，"
                       "读者等他回来时早忘了前情" if holds_thread else "")
        alerts.append({
            "type": "major_character_absent", "entity": name, "severity": "建议级",
            "chapter": last_chapter, "last_seen_chapter": last_seen,
            "absent_chapters": absent, "appearance_count": count,
            "holds_open_thread": holds_thread, "auto": True,
            "evidence": f"累计出场 {count} 章，最后见于第{last_seen}章，已连续缺席 {absent} 章",
            "note": (f"角色「{name}」出场 {count} 章后自第{last_seen}章起连续缺席 {absent} 章{thread_note}。"
                     "多线长篇建议回访或让他人提及一次；若已有意退场，请忽略本条或在 state_delta "
                     "character_changes 补登结构化退场事件（event=exit/death）以豁免"),
        })
    return alerts


def analyze(project, min_chapters=DEFAULT_MIN_CHAPTERS):
    chapters = list(list_chapters(project))
    if not chapters:
        return {"ran": False, "skipped": "无章节可扫", "alerts": []}
    tracked = parse_character_names(project)
    per_chapter = [(idx, extract_name_candidates(text)) for idx, _title, text in chapters]
    agg = aggregate_candidates(per_chapter)
    flagged = recurring_untracked(agg, tracked, min_chapters)
    alerts = []
    for name, chs in flagged:
        alerts.append({
            "type": "untracked_minor_character", "entity": name, "severity": "建议级",
            "chapter": chs[-1], "appears_in_chapters": chs[:12], "appearance_count": len(chs),
            "evidence": f"出现于第 {('、'.join(str(c) for c in chs[:8]))} 章",
            "auto": True,
            "note": f"配角「{name}」在 {len(chs)} 个不同章反复出场却未建角色卡——建议建卡/纳入动态百科，否则其状态/称谓漂移无人跟踪",
        })
    chapter_texts = [(idx, text) for idx, _title, text in chapters]
    alerts.extend(absence_alerts(project, chapter_texts, tracked, agg.keys()))
    return {"ran": True, "alerts": alerts, "tracked": sorted(tracked),
            "flagged": [{"name": n, "chapters": chs} for n, chs in flagged]}


def main(argv=None):
    p = argparse.ArgumentParser(description="配角连续性盲区报告：反复出场却未建卡的配角候选")
    p.add_argument("project_path")
    p.add_argument("--min-chapters", type=int, default=DEFAULT_MIN_CHAPTERS,
                   help=f"出现于 ≥此数个不同章才报（默认 {DEFAULT_MIN_CHAPTERS}，越大越保守）")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    res = analyze(args.project_path, args.min_chapters)
    if res.get("ran"):
        out = os.path.join(args.project_path, "审稿", "minor_character_findings.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print(f"ℹ️ {res.get('skipped')}")
        return 0
    if res["alerts"]:
        print(f"⚠️ {len(res['alerts'])} 条配角连续性提示（建议级）：")
        for a in res["alerts"]:
            if a.get("type") == "major_character_absent":
                print(f"  · [失踪] {a['entity']}：最后见于第{a['last_seen_chapter']}章，已缺席 {a['absent_chapters']} 章")
            else:
                print(f"  · [未建卡] {a['entity']}（{a['appearance_count']} 章）")
    else:
        print("✅ 未发现反复出场却失跟踪、或长期失踪的配角")
    return 0


if __name__ == "__main__":
    sys.exit(main())
