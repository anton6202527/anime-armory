#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""power_system.py — 力量体系一致性引擎：穿越/系统流/修仙的等级·成长值·战力逐章机检（纯标准库）。

为什么：网文力量体系是命门——等级跳变、战力前后矛盾、属性突变、升级节奏崩（数值膨胀/越级无代价）
是高发穿帮，人脑记不住几百章。把 设定/power_system_registry.json 的成长 progression 结构化后确定性机检：
  · 等级/境界/战力**退档**（同角色后章 < 前章，且无 跌境/废修/封印 等剧情豁免）= 阻断级
  · **未知境界**（progression.tier 不在 registry tiers.sequence 里）= 阻断级
  · 面板**属性 > 7** / 未声明属性 = 建议级
  · **越级过快**（单章 tier 跳变 > pacing.max_tier_jump 且正文无代价/机缘词）= 建议级
  · 系统流但连续多章**无系统面板/升级桥段** = 建议级（爽点节拍断了）

阻断级=硬矛盾必改；建议级=节奏/设计提醒。`力量体系自检=仅建议` 时全降建议级；`关闭` 不跑。
软判（数值是否"爽"、平衡是否好）交 novel-score / 人判——本引擎只报确定性硬冲突，宁缺毋滥。

  python3 power_system.py <作品根> [--json]
测试：cd skills/novel-wiki/scripts && python3 -m pytest test_power_system.py
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
    from power_system_defs import (
        GENRE_KEYWORDS, GENRE_MIN_HITS, POWER_GENRES, MOTIF_KEYWORDS, MOTIF_MIN_HITS,
        ATTRS_MAX, REGRESS_EXEMPT_KEYWORDS, POWER_SYSTEM_REGISTRY_KIND,
        genre_needs_power_check,
    )
except Exception:  # 退化兜底（独立跑/测试桩）
    GENRE_KEYWORDS = (("系统流", ("系统", "面板", "等级", "升级")),)
    GENRE_MIN_HITS = 2
    POWER_GENRES = ("系统流", "修仙", "玄幻", "战神")
    MOTIF_KEYWORDS = (("system_panel", ("系统面板", "面板", "等级")), ("level_up", ("升级", "突破")))
    MOTIF_MIN_HITS = 1
    ATTRS_MAX = 7
    REGRESS_EXEMPT_KEYWORDS = ("跌境", "废修", "封印", "散功")
    POWER_SYSTEM_REGISTRY_KIND = "novel_power_system_registry"

    def genre_needs_power_check(genre):  # type: ignore
        return any(g in str(genre or "") for g in POWER_GENRES)

# 越级/突破的"代价/机缘"词：单章大跳但命中这些=有理由，不判越级过快（宁缺毋滥）。
LEAP_JUSTIFY_KEYWORDS = ("天材地宝", "丹药", "服下", "机缘", "传承", "血脉觉醒", "顿悟", "奇遇",
                         "突破", "代价", "反噬", "透支", "秘境", "灌顶", "渡劫", "因祸得福", "爆种")


# ── 纯函数：题材检测（与 motif_detector 同构）─────────────────────────────────

def detect_genre(text, *, min_hits=GENRE_MIN_HITS):
    """按 GENRE_KEYWORDS 命中数判题材。返回 {genre, hits, matched, by_genre}。纯函数·可测。"""
    by_genre = []
    for genre, kws in GENRE_KEYWORDS:
        matched = sorted({kw for kw in kws if kw in text})
        by_genre.append({"genre": genre, "hits": len(matched), "matched": matched})
    by_genre.sort(key=lambda r: r["hits"], reverse=True)
    top = by_genre[0] if by_genre else {"genre": None, "hits": 0, "matched": []}
    if top["hits"] < min_hits:
        return {"genre": None, "hits": top["hits"], "matched": top["matched"], "by_genre": by_genre}
    return {"genre": top["genre"], "hits": top["hits"], "matched": top["matched"], "by_genre": by_genre}


# genre_needs_power_check 从 power_system_defs 导入（单一真值源）。


# ── 纯函数：等级排序（tier 名 → 可比较序号）─────────────────────────────────

def tier_rank(tier, sequence, subtiers=()):
    """境界名（含子阶如"练气后期"）→ 序号 = 主境界序*子阶数 + 子阶序。

    sequence 命中=主境界前缀；subtiers 命中=子阶后缀（缺则按 0）。无法解析返回 None。纯函数·可测。"""
    if tier is None:
        return None
    t = str(tier)
    base_idx = None
    base_name = None
    for i, name in enumerate(sequence):
        if name and name in t:
            # 取最长匹配（避免"大乘"被"乘"类误配；这里子串命中，取最靠后/最长者更稳）
            if base_name is None or len(name) > len(base_name):
                base_idx, base_name = i, name
    if base_idx is None:
        return None
    sub_idx = 0
    span = max(1, len(subtiers))
    for j, sub in enumerate(subtiers):
        if sub and sub in t:
            sub_idx = j
            break
    return base_idx * span + sub_idx


def _alert(typ, entity, severity, chapter, evidence, note=""):
    return {"type": typ, "entity": entity, "severity": severity,
            "chapter": chapter, "evidence": evidence, "note": note, "auto": True}


def _num(value):
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(m.group()) if m else None


# ── 纯函数：progression 单调 + 未知境界 ────────────────────────────────────

def validate_progression(progression, tiers, *, demote_severity="阻断级"):
    """逐角色校验等级/境界/战力只增不减（退档=阻断，除非快照标 regress_reason 命中豁免词）+ 未知境界。

    progression: [{chapter, character, level?, tier?, 战力?/power?, regress_reason?}]。纯函数·可测。"""
    sequence = list((tiers or {}).get("sequence") or [])
    subtiers = list((tiers or {}).get("subtiers") or [])
    alerts = []
    by_char = {}
    for snap in progression or []:
        if not isinstance(snap, dict):
            continue
        by_char.setdefault(str(snap.get("character") or "主角"), []).append(snap)
    for char, snaps in by_char.items():
        snaps = sorted(snaps, key=lambda s: _num(s.get("chapter")) or 0)
        last_tier = last_level = last_power = None
        for snap in snaps:
            ch = snap.get("chapter")
            reason = str(snap.get("regress_reason") or "")
            exempt = any(k in reason for k in REGRESS_EXEMPT_KEYWORDS)
            # 未知境界
            if snap.get("tier") is not None and sequence:
                r = tier_rank(snap.get("tier"), sequence, subtiers)
                if r is None:
                    alerts.append(_alert("power_unknown_tier", char, "阻断级", ch,
                                         f"境界`{snap.get('tier')}`不在体系序列 {sequence}",
                                         "境界名拼写/层级与 power_system_registry.tiers.sequence 不符"))
                elif last_tier is not None and r < last_tier and not exempt:
                    alerts.append(_alert("power_tier_regress", char, demote_severity, ch,
                                         f"境界退档：第{ch}章`{snap.get('tier')}`(序{r}) < 之前(序{last_tier})",
                                         "境界只增不减；确属跌境/废修请在快照写 regress_reason"))
                if r is not None:
                    last_tier = r if (last_tier is None or r >= last_tier or exempt) else last_tier
            # 等级数值
            lv = _num(snap.get("level"))
            if lv is not None:
                if last_level is not None and lv < last_level and not exempt:
                    alerts.append(_alert("power_level_regress", char, demote_severity, ch,
                                         f"等级退档：第{ch}章 Lv.{snap.get('level')} < 之前 Lv.{last_level:g}",
                                         "等级只增不减；确属降级请写 regress_reason"))
                last_level = lv if (last_level is None or lv >= last_level or exempt) else last_level
            # 战力
            pw = _num(snap.get("战力") if snap.get("战力") is not None else snap.get("power"))
            if pw is not None:
                if last_power is not None and pw < last_power and not exempt:
                    alerts.append(_alert("power_combat_regress", char, demote_severity, ch,
                                         f"战力倒退：第{ch}章 {pw:g} < 之前 {last_power:g}",
                                         "战力跨章不应无理由变小；确有重伤/封印请写 regress_reason"))
                last_power = pw if (last_power is None or pw >= last_power or exempt) else last_power
    return alerts


# ── 纯函数：面板 schema（属性 ≤ 7）─────────────────────────────────────────

def validate_panel_schema(panel_schema):
    """系统流面板属性数 ≤ ATTRS_MAX、无重复。纯函数·可测。"""
    alerts = []
    attrs = list((panel_schema or {}).get("attrs") or [])
    if len(attrs) > ATTRS_MAX:
        alerts.append(_alert("power_panel_too_many_attrs", "面板", "建议级", None,
                             f"面板属性 {len(attrs)} 个 > 上限 {ATTRS_MAX}：{attrs}",
                             "属性过多=信息过载；5 核心+至多 2 特殊，删装饰位"))
    dup = sorted({a for a in attrs if attrs.count(a) > 1})
    if dup:
        alerts.append(_alert("power_panel_dup_attr", "面板", "建议级", None,
                             f"面板属性重复：{dup}", "去重"))
    return alerts


# ── 纯函数：越级过快（单章 tier 跳变 > 上限且正文无代价词）──────────────────

def check_pacing(progression, tiers, pacing, chapter_texts=None):
    """越级过快：同角色相邻快照 tier 跳变 > max_tier_jump_per_chapter/章 且对应正文无代价/机缘词。

    chapter_texts: {chapter:int -> text} 用于查代价词；缺则只按跳变幅度提示。纯函数·可测。"""
    sequence = list((tiers or {}).get("sequence") or [])
    subtiers = list((tiers or {}).get("subtiers") or [])
    span = max(1, len(subtiers))
    max_jump = int((pacing or {}).get("max_tier_jump_per_chapter", 1))
    chapter_texts = chapter_texts or {}
    alerts = []
    by_char = {}
    for snap in progression or []:
        if isinstance(snap, dict):
            by_char.setdefault(str(snap.get("character") or "主角"), []).append(snap)
    for char, snaps in by_char.items():
        snaps = sorted(snaps, key=lambda s: _num(s.get("chapter")) or 0)
        prev_rank = prev_ch = None
        for snap in snaps:
            r = tier_rank(snap.get("tier"), sequence, subtiers)
            ch = _num(snap.get("chapter"))
            if r is not None and prev_rank is not None and ch is not None and prev_ch is not None:
                chapters_span = max(1, int(ch - prev_ch))
                # 跨"大境界"跳数（按 span 折算），允许 max_jump * 章数
                major_jump = (r - prev_rank) / span
                allowed = max_jump * chapters_span
                if major_jump > allowed:
                    text = chapter_texts.get(int(ch), "")
                    justified = any(k in text for k in LEAP_JUSTIFY_KEYWORDS)
                    if not justified:
                        alerts.append(_alert("power_leap_too_fast", char, "建议级", int(ch),
                                             f"第{prev_ch:g}→{ch:g}章跨 {major_jump:.1f} 个大境界（限 {allowed}）",
                                             "越级过快疑似数值膨胀；越级须配代价/机缘（丹药/奇遇/反噬），否则放缓"))
            if r is not None:
                prev_rank, prev_ch = r, ch
    return alerts


# ── 纯函数：母题桥段在场（系统流爽点节拍）──────────────────────────────────

def check_scene_presence(chapter_texts, *, window=10, min_hits=MOTIF_MIN_HITS):
    """系统流：连续 window 章都没有系统面板/升级等母题桥段 → 爽点节拍断了（建议级）。

    chapter_texts: 有序 [(chapter:int, text), ...]。纯函数·可测。"""
    flags = []
    for ch, text in chapter_texts:
        hit = False
        for _mt, kws in MOTIF_KEYWORDS:
            if sum(1 for kw in kws if kw in text) >= min_hits:
                hit = True
                break
        flags.append((ch, hit))
    alerts = []
    run_start = None
    run_len = 0
    for ch, hit in flags:
        if not hit:
            run_start = ch if run_len == 0 else run_start
            run_len += 1
        else:
            if run_len >= window:
                alerts.append(_alert("power_motif_absent", "系统面板/升级", "建议级", run_start,
                                     f"第{run_start}~{ch-1}章连续 {run_len} 章无系统面板/升级桥段",
                                     "系统流读者要的升级爽点节拍断了，适时插面板/升级/签到/抽奖桥段"))
            run_len = 0
    if run_len >= window:
        last_ch = flags[-1][0]
        alerts.append(_alert("power_motif_absent", "系统面板/升级", "建议级", run_start,
                             f"第{run_start}~{last_ch}章连续 {run_len} 章无系统面板/升级桥段",
                             "系统流升级爽点节拍断了，适时插面板/升级桥段"))
    return alerts


# ── IO + run ───────────────────────────────────────────────────────────────

def registry_path(project):
    return os.path.join(project, "设定", "power_system_registry.json")


def load_registry(project):
    try:
        with open(registry_path(project), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("kind") == POWER_SYSTEM_REGISTRY_KIND:
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _load_chapters(project):
    """有序 [(chapter:int, text)]，best-effort 复用 project_io，缺则空。"""
    try:
        sys.path.insert(0, _LIB)
        from project_io import list_chapter_files, read_text
        out = []
        for idx, path in list_chapter_files(project):
            out.append((int(idx), read_text(path)))
        return out
    except Exception:
        return []


def run(project, *, advisory_only=False, window=10):
    """加载 registry + 章节，跑全部机检，返回 {ran, alerts, blocking, ...}。"""
    reg = load_registry(project)
    if reg is None:
        return {"ran": False, "skipped": "无 设定/power_system_registry.json——先 novel-create 立项脚手架或手建"}
    demote = "建议级" if advisory_only else "阻断级"
    tiers = reg.get("tiers") or {}
    progression = reg.get("progression") or []
    chapters = _load_chapters(project)
    chapter_texts_map = {ch: t for ch, t in chapters}
    alerts = []
    alerts += validate_progression(progression, tiers, demote_severity=demote)
    alerts += validate_panel_schema(reg.get("panel_schema") or {})
    alerts += check_pacing(progression, tiers, reg.get("pacing") or {}, chapter_texts_map)
    if str(reg.get("system_type") or "").find("系统") >= 0 and chapters:
        alerts += check_scene_presence(chapters, window=window)
    blocking = sum(1 for a in alerts if a["severity"] == "阻断级")
    return {"ran": True, "system_type": reg.get("system_type"),
            "alerts": alerts, "total": len(alerts), "blocking": blocking}


def main(argv=None):
    ap = argparse.ArgumentParser(description="力量体系一致性引擎")
    ap.add_argument("project_path")
    ap.add_argument("--advisory", action="store_true", help="全降建议级（力量体系自检=仅建议）")
    ap.add_argument("--window", type=int, default=10, help="母题缺席的连续章窗口")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = run(args.project_path, advisory_only=args.advisory, window=args.window)
    out = os.path.join(args.project_path, "审稿", "power_system_findings.json")
    if res.get("ran"):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if not res.get("ran"):
        print("ℹ️ " + res.get("skipped", "skipped"))
        return 0
    icon = "⛔" if res["blocking"] else ("⚠️" if res["total"] else "✅")
    print(f"{icon} 力量体系自检（{res.get('system_type')}）：{res['total']} 项（阻断 {res['blocking']}）→ {out}")
    for a in res["alerts"]:
        mark = "⛔" if a["severity"] == "阻断级" else "⚠️"
        print(f"  {mark} [{a['type']}] 第{a.get('chapter')}章 {a['entity']}：{a['evidence']}")
    return 1 if res["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
