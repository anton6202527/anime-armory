#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logic_sentry.py — 逻辑哨兵：拿《动态百科》确定性扫硬冲突（纯标准库）

跑真活，不是 mock：对目标章节扫多类**硬冲突**（确定性可机检，不靠 LLM）：
  1) 死人复活：百科里已 deceased 的角色，在其死亡章之后又"在场行动"（且非闪回/托梦语境）
  2) 弃置道具复用：百科里已 discarded/shattered/lost 的道具，又被"使用/催动/祭出"
  3) 位置跳变（保守）：角色在本章被写在与百科记录不同的已知地点，且无位移过渡词
  4) 数值/事实漂移（年龄）：角色卡声明了年龄锚点，本章却把同一角色写成不同年龄（非时间跳跃语境）

软冲突（性格突变、动机不合理）不在此列——交 novel-review 人判。
哨兵只报"硬冲突候选"，每条带证据 + auto 标志，最终由人/LLM 定夺（容错铁律：宁缺毋滥）。

  python3 logic_sentry.py <作品根> --chapter <章节号或文件路径>

测试：cd skills/novel-wiki/scripts && python3 -m pytest test_logic_sentry.py
"""
import os
import re
import sys
import json
import argparse

from wiki_builder import FLASHBACK_HINTS, _context, list_chapters, _CJK
from consistency_scaffold import resolve_character_card  # 同认 角色卡.md / 人物.md
from heuristic_gate import enforce, count_blocking  # B10：脆弱启发式不得硬阻断（单一收口）
try:
    # A1/A2·结构化原子事实确定性检测（同目录 graph_sentry）：只比台账枚举/章号/区间·可硬阻断。
    from graph_sentry import detect_lifecycle_conflicts, detect_fact_interval_conflicts, resolved_alias_map
except Exception:  # pragma: no cover - 部分 checkout 仍可用（结构化闸优雅缺席）
    detect_lifecycle_conflicts = detect_fact_interval_conflicts = resolved_alias_map = None

ITEM_USE_VERBS = ["用", "使", "催动", "祭出", "举起", "握", "拔", "挥", "取出", "拿出", "施展", "祭起"]
DISCARDED_STATUS = {"discarded", "shattered", "lost", "丢弃", "损毁", "破碎", "遗失", "摧毁"}
MOVE_HINTS = ["赶往", "前往", "来到", "回到", "抵达", "瞬移", "传送", "疾驰", "飞往", "动身", "启程", "赶赴"]

# 时间跳跃语境：合法地改变角色年龄，命中则豁免数值漂移（宁缺毋滥）。
TIMESKIP_HINTS = ["多年", "年后", "数年", "转眼", "岁月", "长大", "成年", "许多年", "光阴", "春秋", "几年后", "十年", "如今已"]
_AGE_NUM = r"(\d{1,3}|[〇零一二三四五六七八九十百两廿]{1,5})"
# 角色卡声明锚点：`年龄：17` / `年龄 十七` / `17岁` / `年方十八`
_CARD_AGE_RES = [
    re.compile(r"年龄[：:\s]*" + _AGE_NUM),
    re.compile(r"年方" + _AGE_NUM),
    re.compile(_AGE_NUM + r"\s*岁"),
]
# 正文年龄表达：`X岁` / `今年X` / `年方X` / `芳龄X`
_TEXT_AGE_RES = [
    re.compile(_AGE_NUM + r"\s*岁"),
    re.compile(r"(?:今年|年方|芳龄|年纪)\s*" + _AGE_NUM),
]

_CJK_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
               "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

# 关系温度计：单章波动 > 此度数视为突变（除非命中重大转折语境）。
REL_FLIP_THRESHOLD = 40
RELATIONSHIP_TURNING_POINTS = ["背叛", "反目", "决裂", "和解", "牺牲", "真相", "告白", "生死",
                               "救命", "翻脸", "结盟", "反水", "黑化", "洗白", "重逢", "诀别"]
# 张力账本规则阈值（与 tension-ledger.md 一致）。
HOOK_OVERDUE_GAP = 10      # urgency=high 钩子超过 此章数 未解 → 悬念发霉（建议级）
TENSION_FATIGUE_RUN = 3    # 连续 此章数 tension_score < 阈值 → 节奏塌陷预警（建议级）
TENSION_FATIGUE_SCORE = 5
PROMISE_KEPT_STATUSES = {"fulfilled", "kept", "resolved", "兑现", "已兑现", "达成"}
GUARDRAIL_EXEMPT_HINTS = ["被控制", "失控", "伪装", "冒充", "梦境", "噩梦", "幻境", "闪回", "假装", "演戏"]


def _as_list(value):
    """容错：None→[]，标量→[str]，列表→[str,...]（丢空串）。"""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    return [s] if s else []


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def scan_world_rules(world, text, chapter_index):
    """世界规则违背（阻断级）——只对作者显式声明的关键词判，宁缺毋滥。纯函数·可测。

    world_state_ledger.major_changes 每条可带结构化字段：
      forbidden_before: 该演进确立(chapter)**之前**不应出现的措辞（用了还没解锁的设定）。
      forbidden_after:  确立**之后**不应再出现的措辞（旧规则已废 / 物已毁，却又复用）。
    只给自由文本 impact、无 forbidden_* → 跳过该条（无法确定性判，交人判）。
    """
    alerts = []
    for change in (world or {}).get("major_changes", []):
        if not isinstance(change, dict):
            continue
        ch = change.get("chapter", 0) or 0
        event = change.get("event") or change.get("impact") or "世界演进"
        if chapter_index < ch:
            for kw in _as_list(change.get("forbidden_before")):
                if kw in text:
                    alerts.append({
                        "type": "world_rule_violation", "entity": event, "severity": "阻断级",
                        "chapter": chapter_index, "rule_chapter": ch,
                        "evidence": _context(text, text.find(kw), 24).strip(), "auto": True,
                        "note": f"本章用到「{kw}」，但该设定要到第{ch}章「{event}」才确立（用了尚未解锁的世界设定）",
                    })
                    break
        elif chapter_index > ch:
            for kw in _as_list(change.get("forbidden_after")):
                if kw in text:
                    alerts.append({
                        "type": "world_rule_violation", "entity": event, "severity": "阻断级",
                        "chapter": chapter_index, "rule_chapter": ch,
                        "evidence": _context(text, text.find(kw), 24).strip(), "auto": True,
                        "note": f"本章出现「{kw}」，但第{ch}章「{event}」后该旧规则/旧物已不成立（违反已确立的演进事实）",
                    })
                    break
    return alerts


def scan_relationship_flips(matrix_data, text, chapter_index):
    """关系温度计异常波动（建议级）——单章温度跳变 > 阈值且无重大转折语境。纯函数·可测。

    relationship_matrix.matrix[pair].history = [{chapter,temperature},...]（LLM/编辑经 state_delta 维护，
    与 character_changes/伏笔种子同一套纪律）。只在最新一笔落在本章、且与上一笔差值 > 阈值时报。
    无 history（≥2 笔）→ 跳过（不臆造）。
    """
    alerts = []
    matrix = (matrix_data or {}).get("matrix", {}) or {}
    has_turning = any(k in text for k in RELATIONSHIP_TURNING_POINTS)
    for pair, info in matrix.items():
        if not isinstance(info, dict):
            continue
        hist = [h for h in info.get("history", []) if isinstance(h, dict)]
        if len(hist) < 2:
            continue
        hist = sorted(hist, key=lambda h: h.get("chapter", 0))
        last, prev = hist[-1], hist[-2]
        if last.get("chapter") != chapter_index:
            continue
        a, b = _num(last.get("temperature")), _num(prev.get("temperature"))
        if a is None or b is None:
            continue
        delta = abs(a - b)
        if delta > REL_FLIP_THRESHOLD and not has_turning:
            alerts.append({
                "type": "relationship_flip", "entity": pair, "severity": "建议级",
                "chapter": chapter_index, "delta": round(delta, 1),
                "from_temp": b, "to_temp": a,
                "evidence": "；".join(_as_list(info.get("labels")))[:60],
                "auto": True,
                "note": f"{pair} 关系温度单章从 {b:g} 跳到 {a:g}（Δ{delta:g}>{REL_FLIP_THRESHOLD}）且本章无重大转折语境——疑突变/人设崩（请人判：是否缺铺垫）",
            })
    return alerts


# ── 动态关系图：从 state_delta 增量累积，检「关系突变无铺垫」（可阻断） ──────────────
def _normalize_pair(pair):
    """把关系对归一成有序元组键，使 A↔B == B↔A。接受 "A↔B"/"A-B"/"A,B" 或 {a,b}/[a,b]。"""
    if isinstance(pair, dict):
        a, b = pair.get("a") or pair.get("from"), pair.get("b") or pair.get("to")
        names = [a, b]
    elif isinstance(pair, (list, tuple)):
        names = list(pair)[:2]
    else:
        names = re.split(r"[↔<>~\-—–,，、和与&/|]+", str(pair))
    names = [str(n).strip() for n in names if n and str(n).strip()]
    if len(names) < 2:
        return None
    return tuple(sorted(names[:2]))


def build_relationship_graph(project_root):
    """从 `审稿/state_delta_第NN章.json` 的 `relationship_changes` 增量构建关系图。

    根治「关系矩阵全靠人工维护、实际没人填→机检空转」：关系温度本就和人物状态/伏笔同走
    state_delta 纪律，这里把它真正聚合成 `{pair: {history:[{chapter,temperature,label,turning_point}]}}`，
    作为派生单一真值源（落 `审稿/relationship_graph.json`）。每条 relationship_changes 形如
    `{"pair":"甲↔乙","temperature":-60,"label":"…","turning_point":true?}`。无数据返回空图。"""
    deltas_dir = os.path.join(project_root, "审稿")
    matrix = {}
    if not os.path.isdir(deltas_dir):
        return {"kind": "relationship_graph", "derived_from": "state_delta", "matrix": matrix}
    files = []
    for name in os.listdir(deltas_dir):
        m = re.match(r"state_delta_第0*(\d+)章\.json$", name)
        if m:
            files.append((int(m.group(1)), os.path.join(deltas_dir, name)))
    for chap, path in sorted(files):
        try:
            with open(path, encoding="utf-8") as f:
                delta = json.load(f)
        except Exception:
            continue
        for ch in delta.get("relationship_changes") or []:
            if not isinstance(ch, dict):
                continue
            key = _normalize_pair(ch.get("pair") or ch.get("entities") or ch.get("between"))
            temp = _num(ch.get("temperature"))
            if key is None or temp is None:
                continue
            label = str(ch.get("label") or ch.get("note") or "").strip()
            entry = matrix.setdefault("↔".join(key), {"history": [], "labels": []})
            entry["history"].append({
                "chapter": chap, "temperature": temp, "label": label,
                "turning_point": bool(ch.get("turning_point")),
            })
            if label:
                entry["labels"].append(label)
    return {"kind": "relationship_graph", "derived_from": "state_delta", "matrix": matrix}


def detect_relationship_breaks(graph, chapter_texts=None, total_chapters=None):
    """图驱动「关系突变无铺垫」检测——比 scan_relationship_flips 跨章、可升阻断。纯函数·可测。

    对每对关系按章排序，逐相邻两笔看温度跳变 |Δ|>阈值：在 (前章,后章] 的桥接窗口正文里找
    重大转折语境（铺垫可落在中间任一章，不止跳变章），或该笔自带 turning_point/label 即视为有铺垫。
    无铺垫 → 报警：
      - 阻断级：满级反转（|Δ|≥2×阈值）或正负翻面（朋友↔敌人）且非终章——这种突变无铺垫几乎必是人设崩。
      - 建议级：一般跳变，或落在终章（高潮揭示允许陡转，降级提示人复核）。
    chapter_texts={章号:正文}；total_chapters 缺省取图中最大章号（用于终章豁免）。"""
    alerts = []
    matrix = (graph or {}).get("matrix", {}) or {}
    texts = chapter_texts or {}
    if total_chapters is None:
        all_ch = [h.get("chapter", 0) for info in matrix.values()
                  for h in info.get("history", []) if isinstance(h, dict)]
        total_chapters = max(all_ch) if all_ch else 0
    for pair, info in matrix.items():
        hist = sorted([h for h in info.get("history", []) if isinstance(h, dict)],
                      key=lambda h: h.get("chapter", 0))
        for prev, cur in zip(hist, hist[1:]):
            a, b = _num(cur.get("temperature")), _num(prev.get("temperature"))
            cp, cc = prev.get("chapter", 0), cur.get("chapter", 0)
            if a is None or b is None:
                continue
            delta = abs(a - b)
            if delta <= REL_FLIP_THRESHOLD:
                continue
            # 铺垫：本笔自带转折标记，或桥接窗口任一章正文含重大转折语境。
            bridge = "".join(texts.get(i, "") for i in range(cp + 1, cc + 1))
            has_setup = (cur.get("turning_point") or bool(cur.get("label"))
                         or any(k in bridge for k in RELATIONSHIP_TURNING_POINTS))
            if has_setup:
                continue
            sign_flip = (a * b < 0)
            is_final = total_chapters and cc >= total_chapters
            if (delta >= 2 * REL_FLIP_THRESHOLD or sign_flip) and not is_final:
                severity = "阻断级"
            else:
                severity = "建议级"
            alerts.append({
                "type": "relationship_break", "entity": pair, "severity": severity,
                "chapter": cc, "from_chapter": cp, "delta": round(delta, 1),
                "from_temp": b, "to_temp": a, "auto": True,
                "evidence": "；".join(info.get("labels", []))[:60],
                "note": (f"{pair} 关系温度第{cp}→{cc}章从 {b:g} 跳到 {a:g}（Δ{delta:g}"
                         f"{'·正负翻面' if sign_flip else ''}），桥接章无重大转折语境/铺垫"
                         f"{'（终章高潮，降级复核）' if is_final else '——疑突变无铺垫/人设崩'}"),
            })
    return alerts


def scan_tension(ledger, text, chapter_index):
    """张力账本三规则（钩子过期=建议级 / 承诺违约=阻断级 / 张力疲劳=建议级）。纯函数·可测。"""
    alerts = []
    ledger = ledger or {}
    # 1) 钩子过期：urgency=high 且 introduced 后超过 GAP 章仍未 resolved
    for hook in ledger.get("unresolved_hooks", []):
        if not isinstance(hook, dict):
            continue
        if str(hook.get("urgency", "")).lower() != "high":
            continue
        if str(hook.get("status", "")).lower() in {"resolved", "dropped", "已解", "已回收"}:
            continue
        intro = hook.get("introduced_in_chapter", 0) or 0
        if chapter_index - intro > HOOK_OVERDUE_GAP:
            alerts.append({
                "type": "hook_stale", "entity": hook.get("id", "hook"), "severity": "建议级",
                "chapter": chapter_index, "introduced_in_chapter": intro,
                "evidence": str(hook.get("question", ""))[:60], "auto": True,
                "note": f"高悬念钩子「{hook.get('question','')}」自第{intro}章起已超 {HOOK_OVERDUE_GAP} 章未解（悬念发霉，请回收或调整章纲）",
            })
    # 2) 承诺违约（阻断级）：deadline_event 已在本章触发，但承诺未兑现
    for promise in ledger.get("reader_promises", []):
        if not isinstance(promise, dict):
            continue
        if str(promise.get("status", "")).lower() in PROMISE_KEPT_STATUSES:
            continue
        deadline = str(promise.get("deadline_event", "")).strip()
        if deadline and deadline in text:
            alerts.append({
                "type": "promise_broken", "entity": promise.get("id", "promise"), "severity": "阻断级",
                "chapter": chapter_index, "deadline_event": deadline,
                "evidence": str(promise.get("promise", ""))[:80], "auto": True,
                "note": f"读者承诺「{promise.get('promise','')}」的截止事件「{deadline}」已在本章发生，但承诺仍未兑现（读者承诺违约）",
            })
    # 3) 张力疲劳：截至本章的张力曲线末 RUN 章 score 全 < 阈值
    curve = [c for c in ledger.get("chapter_tension_curve", []) if isinstance(c, dict)]
    upto = sorted([c for c in curve if (c.get("chapter", 0) or 0) <= chapter_index],
                  key=lambda c: c.get("chapter", 0))
    if len(upto) >= TENSION_FATIGUE_RUN and upto[-1].get("chapter") == chapter_index:
        tail = upto[-TENSION_FATIGUE_RUN:]
        scores = [_num(c.get("tension_score")) for c in tail]
        if all(s is not None and s < TENSION_FATIGUE_SCORE for s in scores):
            alerts.append({
                "type": "tension_fatigue", "entity": "节奏", "severity": "建议级",
                "chapter": chapter_index,
                "evidence": "、".join(f"第{c.get('chapter')}章={c.get('tension_score')}" for c in tail),
                "auto": True,
                "note": f"连续 {TENSION_FATIGUE_RUN} 章张力 < {TENSION_FATIGUE_SCORE}（连续平淡，节奏塌陷预警——插冲突/钩子）",
            })
    return alerts


def scan_character_guardrails(guardrails, text, chapter_index):
    """角色底线/禁行护栏（显式登记才检查）。

    Schema:
      设定/character_guardrails.json
      {
        "characters": {
          "沈念": {
            "hard_limits": ["伤害无辜"],
            "forbidden_actions": ["背叛师门"],
            "allow_if_context": ["被控制", "幻境"]
          }
        }
      }

    hard_limits 是阻断级；forbidden_actions 是建议级。只有角色名与短语在同一近邻
    上下文里才报，避免把别人的行为算到该角色头上。
    """
    alerts = []
    chars = (guardrails or {}).get("characters", {})
    if isinstance(chars, list):
        chars = {str(item.get("name", "")).strip(): item for item in chars if isinstance(item, dict)}
    if not isinstance(chars, dict):
        return alerts
    for name, info in chars.items():
        name = str(name).strip()
        if not name or name not in text or not isinstance(info, dict):
            continue
        exemptions = GUARDRAIL_EXEMPT_HINTS + _as_list(info.get("allow_if_context"))
        checks = [
            ("character_hard_limit_violation", "阻断级", _as_list(info.get("hard_limits"))),
            ("character_forbidden_action", "建议级", _as_list(info.get("forbidden_actions"))),
        ]
        for alert_type, severity, phrases in checks:
            for phrase in phrases:
                for pos in (m.start() for m in re.finditer(re.escape(phrase), text)):
                    ctx = _context(text, pos, 48)
                    if name not in ctx:
                        continue
                    if any(hint in ctx for hint in exemptions):
                        continue
                    alerts.append({
                        "type": alert_type,
                        "entity": name,
                        "severity": severity,
                        "chapter": chapter_index,
                        "guardrail": phrase,
                        "evidence": ctx.strip(),
                        "auto": True,
                        "note": f"{name} 命中角色护栏「{phrase}」；若确为转折/伪装/失控，请在角色护栏或 state_delta 中补豁免语境。",
                    })
                    break
    return alerts


def cjk_to_int(token):
    """把年龄 token（阿拉伯或 0-999 中文数字）转 int；无法解析返回 None。

    支持 十七=17 / 二十=20 / 三十五=35 / 一百=100 / 廿=20。容错：只覆盖年龄常见量级。
    """
    token = (token or "").strip()
    if token.isdigit():
        return int(token)
    if token == "廿":
        return 20
    if not token or any(c not in _CJK_DIGITS and c not in "十百廿" for c in token):
        return None
    total = 0
    current = 0
    for ch in token:
        if ch in _CJK_DIGITS:
            current = _CJK_DIGITS[ch]
        elif ch == "十":
            current = current or 1
            total += current * 10
            current = 0
        elif ch == "百":
            current = current or 1
            total += current * 100
            current = 0
        elif ch == "廿":
            total += 20
        else:
            return None
    return total + current


def load_numeric_anchors(project_root):
    """从 设定/角色卡.md 抽取每个角色声明的年龄锚点 → {角色名: age_int}。

    角色卡按 `#`/`##` 标题分段，段标题=角色名；段内首个年龄声明即锚点。
    无角色卡 / 无年龄声明 → 返回空 dict（优雅跳过，不臆造）。
    """
    anchors = {}
    card = resolve_character_card(project_root)
    if not card:
        return anchors
    with open(card, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    cur_name = None
    body = []
    skip_titles = {"角色卡", "人物卡", "角色", "人物", "角色表"}

    def _flush(name, text):
        if not name or name in skip_titles:
            return
        for rgx in _CARD_AGE_RES:
            m = rgx.search(text)
            if m:
                val = cjk_to_int(m.group(1))
                if val is not None and 0 < val < 1000:
                    anchors[name] = val
                    return

    for ln in lines:
        h = re.match(r"^#{1,3}\s+(.+?)\s*$", ln)
        if h:
            _flush(cur_name, "\n".join(body))
            cur_name = h.group(1).strip()
            body = []
        else:
            body.append(ln)
    _flush(cur_name, "\n".join(body))
    return anchors


def _ages_in_text(text):
    """返回正文里所有年龄表达 (age_int, position)。"""
    out = []
    for rgx in _TEXT_AGE_RES:
        for m in rgx.finditer(text):
            val = cjk_to_int(m.group(1))
            if val is not None and 0 < val < 1000:
                out.append((val, m.start()))
    return out


def scan_numeric_drift(anchors, text, chapter_index):
    """角色卡年龄锚点 vs 本章年龄表达，邻近不一致即报候选（非时间跳跃语境）。"""
    alerts = []
    if not anchors:
        return alerts
    ages = _ages_in_text(text)
    if not ages:
        return alerts
    for name, canonical in anchors.items():
        if name not in text:
            continue
        name_positions = [m.start() for m in re.finditer(re.escape(name), text)]
        for age_val, age_pos in ages:
            if age_val == canonical:
                continue
            # 中文里年龄紧贴主语：名字须在年龄前 12 字内或后 8 字内（覆盖"沈念今年十七岁"
            # 与"年方十八的沈念"两种语序）。窗口收紧避免把邻句别的角色的年龄算到本角色头上。
            if not any(-12 <= (np - age_pos) <= 8 for np in name_positions):
                continue
            ctx = _context(text, age_pos, 24)
            if any(h in ctx for h in TIMESKIP_HINTS):
                continue  # 时间跳跃合法改年龄，豁免
            alerts.append({
                "type": "numeric_drift_age",
                "entity": name,
                "severity": "建议级",
                "chapter": chapter_index,
                "canonical_age": canonical,
                "found_age": age_val,
                "evidence": ctx.strip(),
                "auto": True,
                "note": f"角色卡声明 {name} 年龄 {canonical}，本章邻近写作 {age_val} 岁且无时间跳跃语境（候选，请人判：可能为虚岁/笔误/真漂移）",
            })
            break
    return alerts


def _resolve_chapter(project, chapter):
    """--chapter 可给章号或文件路径。返回 (idx, text)。"""
    if os.path.isfile(chapter):
        m = re.search(r"(\d+)", os.path.basename(chapter))
        idx = int(m.group(1)) if m else 0
        with open(chapter, "r", encoding="utf-8") as f:
            return idx, f.read()
    idx = int(re.search(r"(\d+)", str(chapter)).group(1))
    for cid, _, text in list_chapters(project):
        if cid == idx:
            return idx, text
    return idx, ""


def scan_chapter(wiki, text, chapter_index, project_root=None, numeric_anchors=None, foreshadow_report=None):
    """确定性扫描，返回 alerts 列表。纯函数，便于单测。

    numeric_anchors：{角色名: 年龄} 锚点；普通模式由 main 从角色卡加载，单测可直接传。
    """
    alerts = []

    for name, e in wiki.items():
        if e.get("category") == "item":
            continue
        if e.get("status") != "deceased":
            continue
        death_at = e.get("death_chapter", e.get("last_update", 0))
        if chapter_index <= death_at:
            continue
        for pos in (m.start() for m in re.finditer(re.escape(name), text)):
            ctx = _context(text, pos, 22)
            if any(h in ctx for h in FLASHBACK_HINTS):
                continue
            alerts.append({
                "type": "deceased_reactivation",
                "entity": name,
                "severity": "阻断级",
                "chapter": chapter_index,
                "death_chapter": death_at,
                "evidence": ctx.strip(),
                "auto": True,
                "note": "已标记阵亡的角色在死亡章之后再次在场行动；若为闪回/托梦请在百科加 FLASHBACK 语境或豁免",
            })
            break

    for name, e in wiki.items():
        if e.get("category") != "item":
            continue
        if e.get("status") not in DISCARDED_STATUS:
            continue
        gone_at = e.get("last_update", 0)
        if chapter_index <= gone_at:
            continue
        for pos in (m.start() for m in re.finditer(re.escape(name), text)):
            ctx = _context(text, pos, 14)
            if any(v in ctx for v in ITEM_USE_VERBS):
                alerts.append({
                    "type": "discarded_item_reuse",
                    "entity": name,
                    "severity": "阻断级",
                    "chapter": chapter_index,
                    "gone_chapter": gone_at,
                    "evidence": ctx.strip(),
                    "auto": True,
                    "note": "已弃置/损毁的道具又被使用",
                })
                break

    # 位置跳变（保守）
    known_locations = {e["location"] for e in wiki.values() if e.get("location")}
    has_move = any(h in text for h in MOVE_HINTS)
    for name, e in wiki.items():
        loc = e.get("location")
        if not loc or e.get("status") == "deceased":
            continue
        if name not in text or has_move:
            continue
        other = [l for l in known_locations if l != loc and l in text]
        for pos in (m.start() for m in re.finditer(re.escape(name), text)):
            ctx = _context(text, pos, 30)
            hit = [l for l in other if l in ctx]
            if hit:
                alerts.append({
                    "type": "location_jump",
                    "entity": name,
                    "severity": "建议级",
                    "chapter": chapter_index,
                    "wiki_location": loc,
                    "found_location": hit[0],
                    "evidence": ctx.strip(),
                    "auto": True,
                    "note": "角色出现在与百科记录不同的地点且全章无位移过渡词（保守候选，易误报，请人判）",
                })
                break

    # 数值/事实漂移（年龄）：角色卡声明锚点 vs 本章年龄表达
    alerts.extend(scan_numeric_drift(numeric_anchors, text, chapter_index))

    # 伏笔回收对账：委托 foreshadow_ledger.analyze() 为单一真值源。
    # logic_sentry 不再独立实现超期判定；analyze() 是 consistency_audit 子检测器，
    # 其 overdue 告警按 importance 自动分级（high/critical = 阻断级，low/medium = 建议级）。
    # sentry 通过 --foreshadow-report 接受预计算的 scan 报告，避免在逐章 sentry 循环
    # 内重复计算（perf/freshness 成本；analyze 是对整体进度的单次快照）。
    if project_root and foreshadow_report:
        try:
            fr = json.loads(foreshadow_report) if isinstance(foreshadow_report, str) else foreshadow_report
        except Exception:
            fr = None
        if isinstance(fr, dict) and fr.get("kind") == "foreshadow_report":
            for o in fr.get("overdue") or []:
                alerts.append({
                    "type": "foreshadowing_overdue",
                    "entity": o.get("id", ""),
                    "severity": "阻断级" if o.get("severity") == "阻断级" else "建议级",
                    "chapter": fr.get("through_chapter") or chapter_index,
                    "expected_at": o.get("expected_payoff_chapter"),
                    "evidence": o.get("description", ""),
                    "auto": True,
                    "note": o.get("note", "高价值伏笔已超过预期的回收窗口"),
                })

    # 世界规则违背（阻断级）：违反 world_state_ledger 已确立/未确立的演进事实
    if project_root:
        world = _load_setting_json(project_root, "world_state_ledger.json")
        if world is not None:
            alerts.extend(scan_world_rules(world, text, chapter_index))

    # 人物关系温度计异常波动（建议级）：单章温度跳变 > 阈值且无重大转折语境
    if project_root:
        matrix_data = _load_setting_json(project_root, "relationship_matrix.json")
        if matrix_data is not None:
            alerts.extend(scan_relationship_flips(matrix_data, text, chapter_index))

    # 张力账本（钩子过期/承诺违约/张力疲劳）：情绪 ROI 不只追事实，也追读者承诺与节奏
    if project_root:
        tension = _load_setting_json(project_root, "tension_ledger.json")
        if tension is not None:
            alerts.extend(scan_tension(tension, text, chapter_index))

    # 角色护栏（底线/禁行）：把 CHIRON 式 richer character sheet 中最可机检的部分结构化。
    if project_root:
        guardrails = _load_setting_json(project_root, "character_guardrails.json")
        if guardrails is not None:
            alerts.extend(scan_character_guardrails(guardrails, text, chapter_index))

    # B10 单一收口：标 confidence + 把脆弱启发式（关键词/子串/邻近扫正文）的 阻断级 降为 建议级。
    # 只有 DETERMINISTIC_TYPES（结构化台账整数比较·不扫正文，如 foreshadowing_overdue）保留硬阻断。
    # 在库函数边界生效 → 所有消费端（main / consistency_audit / 测试）看到的都是策略后的最终 severity。
    enforce(alerts)
    return alerts


def _load_setting_json(project_root, filename):
    """读 设定/<filename>；缺/坏 → None（哨兵据此优雅跳过该维度，不臆造）。"""
    path = os.path.join(project_root, "设定", filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def scan_structured_ledgers(project_root, chapter_index=None, include_world=None):
    """A1/A2·结构化原子事实确定性闸：state_ledger 生命周期(A1) + world_state_ledger 有效区间(A2)。

    只比作者 curated 台账的枚举/章号/区间（不扫正文）→ confidence=deterministic、可硬阻断（见 heuristic_gate
    DETERMINISTIC_TYPES）。缺台账/缺 graph_sentry → 返回 []（优雅缺席·不臆造·不误拦）。
    chapter_index 给定时 A1 只返回复现章==该章的冲突（post_write 单章闸）；世界事实区间冲突是全局台账健康项，
    默认只在全量/review 路径（chapter_index=None）跑，单章 post_write 不重复刷屏（include_world 可显式覆盖）。"""
    if detect_lifecycle_conflicts is None:
        return []
    if include_world is None:
        include_world = chapter_index is None
    out = []
    sl_path = os.path.join(project_root, "审稿", "state_ledger.json")
    if os.path.exists(sl_path):
        try:
            with open(sl_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except Exception:
            ledger = None
        if isinstance(ledger, dict):
            # 实体消解：合并 state_ledger 内联别名 + 设定/角色别名.json 已确认 curated 别名（人确认才入硬闸）。
            alias_map = resolved_alias_map(project_root, ledger) if resolved_alias_map else None
            out += detect_lifecycle_conflicts(ledger, chapter_index=chapter_index, alias_map=alias_map)
    if include_world:
        world = _load_setting_json(project_root, "world_state_ledger.json")
        if isinstance(world, dict):
            out += detect_fact_interval_conflicts(world)
    return out


def main():
    p = argparse.ArgumentParser(description="逻辑哨兵：确定性扫硬冲突候选")
    p.add_argument("project_path")
    p.add_argument("--chapter", required=True, help="章节号或文件路径")
    args = p.parse_args()

    wiki_path = os.path.join(args.project_path, "设定", "动态百科.json")
    if not os.path.exists(wiki_path):
        print(f"Error: 动态百科不存在 {wiki_path}，先跑 wiki_builder.py")
        return
    with open(wiki_path, "r", encoding="utf-8") as f:
        wiki = json.load(f)

    idx, text = _resolve_chapter(args.project_path, args.chapter)
    anchors = load_numeric_anchors(args.project_path)
    # scan_chapter 已在库边界跑过 B10 enforce（标 confidence + 降级脆弱启发式）。
    alerts = scan_chapter(wiki, text, idx, project_root=args.project_path, numeric_anchors=anchors)
    # A1·结构化生命周期确定性闸（本章复现）：已故/退场角色在 state_ledger 里更晚章节有非复活结构化事件 → 真硬阻断。
    alerts += scan_structured_ledgers(args.project_path, chapter_index=idx)
    enforce(alerts)  # 幂等：确定性 alerts 保留阻断级、关键词 alerts 已在 scan_chapter 降级
    downgraded = sum(1 for a in alerts if a.get("downgraded_from"))

    out_dir = os.path.join(args.project_path, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"logic_alerts_{idx}.json")
    blocking = count_blocking(alerts)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "clean" if not alerts else "conflicts",
            "chapter": idx,
            "blocking": blocking,
            "heuristic_downgraded": downgraded,  # B10 降级账：脆弱启发式候选数（已转建议级·不阻断）
            "alerts": alerts,
        }, f, ensure_ascii=False, indent=2)
    if alerts:
        tail = f"，其中 {downgraded} 条脆弱启发式按 B10 降为建议级" if downgraded else ""
        print(f"⚠️ 第{idx}章：{len(alerts)} 条逻辑冲突候选（阻断 {blocking}{tail}）→ {out_path}")
        for a in alerts:
            print(f"  [{a['severity']}] {a['type']} · {a['entity']} · {a['evidence']}")
    else:
        print(f"✅ 第{idx}章：0 硬冲突 → {out_path}")
    # 阻断级=硬矛盾必改：非零退出，让 post_write 的 check=True 真正硬挡。
    # B10（2026-06）后只有确定性证据闸（如 foreshadowing_overdue·伏笔台账整数比较）能留在阻断级；
    # 死人复活/弃置道具复用/世界规则等关键词扫正文的脆弱启发式已统一降为建议级，不再硬挡 post_write。
    if blocking:
        sys.exit(1)


if __name__ == "__main__":
    main()
