#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
timeline_check.py — 时间线哨兵：确定性扫时间顺序矛盾（纯标准库）

跑真活，不是 mock：补 logic_sentry 的缺口——它只查年龄漂移，没有事件日期/时间线顺序校验。
本脚本对**连续章节**做时间标记对账，只报两类**确定性可机检**的硬候选（容错铁律：宁缺毋滥）：

  1) 时间线倒流（建议级，timeline_backward）：连续叙事里出现"明确且可比较的绝对时间标记"
     比上一个绝对标记更早（绝对年份递减，或同纪元内 冬→春 之类季节倒退），且邻近无闪回语境。
     仅当**前后标记都可比较且为绝对**时才报；相对跳转（"三天后"）只用来推进，不单独判矛盾。

  2) 台账事件乱序（阻断级，timeline_event_disorder）：可选 设定/timeline.json 存在时——
     若某 order=O 的事件落在第 A 章，而另一 order<O 的事件却落在更晚的第 B 章（B>A），
     即"先发生的事被写在后面的章"，按硬矛盾阻断（台账=作者显式声明的事实序）。

什么可比较、什么不可比较（诚实声明）：
  - 绝对年份（"三年""第七年""庆元三年"被归一为整数纪年）→ 可比较。
  - 季节（春夏秋冬→0..3）→ 仅在同一"绝对年锚"或相邻连续叙事内可比较；跨年/跨纪元不比较。
  - 相对跳转（三天后/次日/翌日/一年后/数月后/十年后）→ 只表"向前推进"，**不**用于倒流判定
    （方向已知但绝对锚未知，无法和别的标记可靠比较；强判=误报，故保守跳过）。

  python3 timeline_check.py <作品根> [--json]

测试：cd skills/novel-wiki/scripts && python3 -m pytest test_timeline_check.py
"""
import os
import re
import sys
import json
import argparse

from wiki_builder import FLASHBACK_HINTS, _context, list_chapters
from logic_sentry import cjk_to_int

# 季节 → 0..3（春夏秋冬）。
_SEASONS = {"春": 0, "夏": 1, "秋": 2, "冬": 3}

_NUM = r"(\d{1,4}|[〇零一二三四五六七八九十百两廿]{1,6})"

# 绝对年份纪年：`三年` / `第七年` / `庆元三年`（取末尾数字段做纪年序；非真实公历，只求相对可比）。
_ABS_YEAR_RES = [
    re.compile(r"第" + _NUM + r"年"),
    re.compile(_NUM + r"年(?![后前])"),  # "三年" 是纪年；"三年后" 是相对跳转，靠 (?![后前]) 排除
]

# 相对时间跳转：方向已知（向前），但无绝对锚——只标方向，不参与倒流判定。
_REL_FORWARD_RES = [
    re.compile(r"次日"),
    re.compile(r"翌日"),
    re.compile(_NUM + r"(?:天|日|月|年|载|纪)后"),
    re.compile(r"数(?:日|月|年)后"),
    re.compile(r"多年(?:后|以后)"),
]


def season_rank(season):
    """春夏秋冬 → 0..3；非季节字 → None。纯函数·可测。"""
    return _SEASONS.get((season or "").strip())


def parse_time_markers(text):
    """抽本章所有时间信号 → 归一列表（按出现位置排序）。纯函数·可测。

    每条 marker 是 dict：
      {"kind": "abs_year",  "value": int,  "comparable": True,  "pos": int, "raw": str}
      {"kind": "season",    "value": 0..3, "comparable": True,  "pos": int, "raw": str}
      {"kind": "rel_fwd",   "value": None, "comparable": False, "pos": int, "raw": str}

    comparable=True 才进倒流判定；rel_fwd 仅说明"向前推进"，不可与他者可靠比较（见模块 docstring）。
    """
    markers = []
    for rgx in _ABS_YEAR_RES:
        for m in rgx.finditer(text):
            val = cjk_to_int(m.group(1))
            if val is not None and 0 < val < 10000:
                markers.append({"kind": "abs_year", "value": val, "comparable": True,
                                "pos": m.start(), "raw": m.group(0)})
    for ch, rank in _SEASONS.items():
        for m in re.finditer(re.escape(ch) + r"(?:天|日|季|意)?", text):
            markers.append({"kind": "season", "value": rank, "comparable": True,
                            "pos": m.start(), "raw": ch})
    for rgx in _REL_FORWARD_RES:
        for m in rgx.finditer(text):
            markers.append({"kind": "rel_fwd", "value": None, "comparable": False,
                            "pos": m.start(), "raw": m.group(0)})
    markers.sort(key=lambda mk: mk["pos"])
    return markers


def timeline_conflict(prev_marker, cur_marker):
    """两个时间标记是否构成明确倒流。返回 (bool, reason)。纯函数·可测。

    保守判定——只在**两者都可比较且同类绝对量**时判倒流；任一不可比较 / 异类 → (False, "")：
      - abs_year vs abs_year：cur 年份 < prev 年份 → 倒流。
      - season  vs season ：cur 季节 rank < prev rank → 同纪元内季节倒退（如 冬→春）。
    跨类（年 vs 季）无共同标度 → 不判（不臆造换算）。
    """
    if not prev_marker or not cur_marker:
        return (False, "")
    if not prev_marker.get("comparable") or not cur_marker.get("comparable"):
        return (False, "")
    pk, ck = prev_marker.get("kind"), cur_marker.get("kind")
    if pk != ck:
        return (False, "")
    pv, cv = prev_marker.get("value"), cur_marker.get("value")
    if pv is None or cv is None:
        return (False, "")
    if pk == "abs_year" and cv < pv:
        return (True, f"绝对纪年从「第{pv}年」退到「第{cv}年」（年份递减）")
    if pk == "season" and cv < pv:
        names = "春夏秋冬"
        return (True, f"季节从「{names[pv]}」退到「{names[cv]}」（同纪元内季节倒退）")
    return (False, "")


def _last_comparable(markers):
    """本章最后一个 comparable 标记（用于和下一章首个 comparable 标记接力比较）。"""
    comp = [m for m in markers if m.get("comparable")]
    return comp[-1] if comp else None


def _first_comparable(markers):
    comp = [m for m in markers if m.get("comparable")]
    return comp[0] if comp else None


def _near_flashback(text, pos, radius=22):
    """标记邻近是否有闪回语境（命中则豁免倒流，避免把回忆/梦境误判为矛盾）。"""
    ctx = _context(text, pos, radius)
    return any(h in ctx for h in FLASHBACK_HINTS)


def check_ledger_order(ledger, chapter_of_event):
    """台账事件乱序（阻断级）。纯函数·可测。

    ledger = {"events":[{"name":..,"chapter":N,"order":int}, ...]}。
    chapter_of_event：{name: chapter}，普通模式由 analyze 据台账自身 chapter 字段填充
    （台账即声明"事件 E 应在第 N 章"），单测可直接传以独立验证。

    乱序定义：order 大的事件落在更早的章，而 order 小的事件落在更晚的章——
    即按 order 升序排列后，章号不是非递减（出现 后序事件章 < 前序事件章）→ 报每个逆序对。
    """
    alerts = []
    events = [e for e in (ledger or {}).get("events", []) if isinstance(e, dict)]
    norm = []
    for e in events:
        name = str(e.get("name", "")).strip()
        order = e.get("order")
        ch = chapter_of_event.get(name, e.get("chapter"))
        if not name or not isinstance(order, int) or not isinstance(ch, int):
            continue
        norm.append({"name": name, "order": order, "chapter": ch})
    norm.sort(key=lambda x: x["order"])
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            earlier, later = norm[i], norm[j]  # earlier.order < later.order
            if earlier["order"] == later["order"]:
                continue
            if later["chapter"] < earlier["chapter"]:
                alerts.append({
                    "type": "timeline_event_disorder",
                    "entity": f"{earlier['name']} → {later['name']}",
                    "severity": "阻断级",
                    "chapter": later["chapter"],
                    "evidence": (f"事件「{earlier['name']}」(order={earlier['order']}) 在第{earlier['chapter']}章，"
                                 f"但更晚的「{later['name']}」(order={later['order']}) 却在更早的第{later['chapter']}章"),
                    "auto": True,
                    "note": "时间线台账声明的事件顺序与实际成章顺序矛盾（先发生的事被写在后面的章），请人判：调整章序或修正台账 order",
                })
    return alerts


def _load_ledger(project_root):
    """读 设定/timeline.json；缺/坏 → None（哨兵据此优雅跳过台账维度，不臆造）。"""
    path = os.path.join(project_root, "设定", "timeline.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def analyze(project, ledger=None):
    """按章序走全书，做时间线倒流（建议级）+ 可选台账乱序（阻断级）。返回 {"alerts":[...]}。

    优雅跳过：无可比较绝对标记 → 不报倒流；无 timeline.json → 不跑台账维度。
    ledger 参数可注入以便单测；普通模式由 main 从 设定/timeline.json 加载。
    """
    alerts = []
    chapters = list_chapters(project)

    last_comp = None       # 上一处可比较标记
    last_comp_chapter = None
    for idx, _, text in chapters:
        markers = parse_time_markers(text)
        first = _first_comparable(markers)
        if first is not None and last_comp is not None:
            conflict, reason = timeline_conflict(last_comp, first)
            if conflict and not _near_flashback(text, first["pos"]):
                alerts.append({
                    "type": "timeline_backward",
                    "entity": f"第{last_comp_chapter}章→第{idx}章",
                    "severity": "建议级",
                    "chapter": idx,
                    "evidence": _context(text, first["pos"], 24).strip(),
                    "auto": True,
                    "note": f"跨章时间线疑似倒流：{reason}，且邻近无闪回语境（保守候选，请人判：可能为闪回未标注/纪年笔误/真倒流）",
                })
        cur_last = _last_comparable(markers)
        if cur_last is not None:
            last_comp = cur_last
            last_comp_chapter = idx

    if ledger is not None:
        chapter_of_event = {}
        for e in ledger.get("events", []):
            if isinstance(e, dict) and str(e.get("name", "")).strip() and isinstance(e.get("chapter"), int):
                chapter_of_event[str(e["name"]).strip()] = e["chapter"]
        alerts.extend(check_ledger_order(ledger, chapter_of_event))

    return {"alerts": alerts}


def main(argv=None):
    p = argparse.ArgumentParser(description="时间线哨兵：确定性扫时间顺序矛盾")
    p.add_argument("project_path")
    p.add_argument("--json", action="store_true", help="只把结果 JSON 打到 stdout（不另存文件外仍会写报告）")
    args = p.parse_args(argv)

    ledger = _load_ledger(args.project_path)
    result = analyze(args.project_path, ledger=ledger)
    alerts = result["alerts"]
    blocking = sum(1 for a in alerts if a["severity"] == "阻断级")

    out_dir = os.path.join(args.project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "timeline_findings.json")
    payload = {
        "status": "clean" if not alerts else "conflicts",
        "blocking": blocking,
        "ledger_present": ledger is not None,
        "alerts": alerts,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif alerts:
        print(f"⚠️ 时间线：{len(alerts)} 条候选（阻断 {blocking}）→ {out_path}")
        for a in alerts:
            print(f"  [{a['severity']}] {a['type']} · {a['entity']} · {a['evidence']}")
    else:
        print(f"✅ 时间线：0 矛盾 → {out_path}")

    # 阻断级（台账乱序）= 硬矛盾必改：非零退出，让 post_write 的 check=True 真正硬挡（与 logic_sentry/power_system 同约定）。
    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
