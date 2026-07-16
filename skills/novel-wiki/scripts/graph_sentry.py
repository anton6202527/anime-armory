#!/usr/bin/env python3
# coding: utf-8
"""角色生命周期时序哨兵 — 退场/死亡角色跨章复现检测（确定性·非 mock）。

诚实命名（不吹）：这**不是 GraphRAG，也没有图/embedding/检索**——就是消费已有账本
审稿/state_ledger.json 的 chapter_deltas[*].character_changes（{name, change}），按章号排序
扫一遍，为每个角色记一个 `{name -> 退场事件}` 映射，检"已退场/死亡角色在更晚章节复现"。
它解决的是 GraphRAG 文献里那个标志性用例（dead character can't reappear），但用的是
排序字典扫描这种最朴素的确定性手段，够用且可机检即可，不必上图。

关键设计（借鉴 arXiv 2506.05939 的告诫——别把"随时间演变的角色"塌成单节点）：
- **保留时态侧写**：记录退场章 + 复现章两个 facet，不抹掉角色演变；
- **revive 感知**：复现说明里含 复活/重生/归来/涅槃/转世/借尸还魂 等 → 降级为 advisory（合法剧情，仅提示），
  不当作穿帮，避免对仙侠/系统流误伤。
- 检测质量完全取决于编辑/LLM 把 character_changes 写准；`_EXIT_RE`/`_REVIVE_RE` 是粗关键词，
  会漏会误（消失/失踪当退场、苏醒当复活），故本哨兵**只 advisory，从不当门控**。

**report-only**：blocking 恒为 0，绝不当门控（杜绝"哨兵恒 clean=静默假阴性"）。
账本缺失返回 status="no_ledger"（**不是** clean）——让调用方据实判断，不把"没数据"当"通过"。
可选 设定/动态百科.json / 设定/角色弧光.json 存在时并入角色名单（仅扩充识别，不改判定逻辑）。
"""

import os
import re
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

# 退场/死亡标记 与 复活/回归标记（复现侧若命中 revive → 合法，仅 advisory）
_EXIT_RE = re.compile(r"死|亡|殒|陨落|牺牲|阵亡|圆寂|离世|去世|退场|出局|被杀|遇害|消失|失踪")
_REVIVE_RE = re.compile(r"复活|重生|归来|回归|涅槃|转世|借尸还魂|诈死|假死|苏醒|复苏")

# A1·结构化生命周期事件枚举（state_ledger character_changes[*].event 的**受控取值**，非正文关键词扫描）。
# 作者/LLM 在 state_delta 里显式标 event 才走确定性硬闸；只给自由文本 change 的旧条目仍走 _EXIT_RE 关键词→advisory。
_DEATH_EXIT_EVENTS = {"death", "die", "died", "dead", "deceased", "killed", "kill", "exit", "exited",
                      "leave", "left", "departed", "退场", "死亡", "身亡", "阵亡", "战死", "离世", "出局", "下线"}
_REVIVAL_EVENTS = {"revival", "revive", "revived", "resurrect", "resurrected", "resurrection", "return",
                   "returned", "reborn", "rebirth", "复活", "重生", "归来", "回归", "转世", "涅槃", "复苏",
                   "诈死揭穿", "假死揭穿", "死而复生"}


def _norm_event(ev) -> str:
    return str(ev or "").strip().lower()


def _load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _chapter_no(key: str) -> int:
    m = re.search(r"(\d+)", str(key))
    return int(m.group(1)) if m else 0


def _iter_character_changes(ledger: Dict[str, Any]):
    """yield (chapter_no, name, change_text) 按章序。兼容 chapter_deltas 为 dict 或 list。"""
    deltas = ledger.get("chapter_deltas")
    items = []
    if isinstance(deltas, dict):
        items = sorted(deltas.items(), key=lambda kv: _chapter_no(kv[0]))
    elif isinstance(deltas, list):
        items = [(d.get("chapter") or d.get("chapter_key") or i, d) for i, d in enumerate(deltas)]
        items.sort(key=lambda kv: _chapter_no(kv[0]))
    for key, delta in items:
        # reconcile_ledger.merge 落库形如 chapter_deltas[key]={merged_at, summary:<delta>, verification}——
        # 真实 state_ledger 是 summary 包裹的；旧测试/手拼台账是裸 delta。两种都要认，否则本确定性生死闸
        # 在**生产合并后的台账上永久 no-op**（summary 包裹时 .get('character_changes') 恒 None）。
        if isinstance(delta, dict) and isinstance(delta.get("summary"), dict):
            delta = delta["summary"]
        ch = _chapter_no(key) or (delta.get("chapter") if isinstance(delta, dict) else 0) or 0
        for cc in (delta.get("character_changes") or []) if isinstance(delta, dict) else []:
            if isinstance(cc, dict):
                name = str(cc.get("name") or cc.get("character") or "").strip()
                change = str(cc.get("change") or cc.get("delta") or cc.get("note") or "").strip()
                event = _norm_event(cc.get("event") or cc.get("lifecycle"))
                if name:
                    yield ch, name, change, event


def build_alias_map(ledger: Dict[str, Any]) -> Dict[str, str]:
    """从台账的**结构化 curated** 别名登记构建 {别名/变体名 -> 规范名}（含规范名→自身·幂等·不扫正文）。

    实体消解是确定性一致性闸的强制前置（arXiv 2506.05939：未消解实体→自信地漏判）：同一角色用
    本名/封号/化名/旧名分别记台账时，逐角色字典会把死亡与复现分到两个 key，硬闸悄悄漏掉。这里只读
    作者 curated 的结构化别名源，绝不从正文猜：
      - ledger["character_aliases"]: {别名: 规范名}（最显式）
      - ledger["characters"]: [{name/canonical, aliases/别名/also_known_as: [...]}]
      - ledger["aliases"]: {规范名: [别名...]}（反向也支持）
    无结构化别名源 → 空 map（detect 退化为原 raw-name 行为·完全向后兼容）。纯函数·可测。"""
    out: Dict[str, str] = {}
    if not isinstance(ledger, dict):
        return out

    def _register(canonical, variants):
        canon = str(canonical or "").strip()
        if not canon:
            return
        out[canon] = canon
        for v in variants or []:
            vs = str(v or "").strip()
            if vs:
                out.setdefault(vs, canon)

    ca = ledger.get("character_aliases")
    if isinstance(ca, dict):
        for alias, canon in ca.items():
            a = str(alias or "").strip()
            c = str(canon or "").strip()
            if a and c:
                out[c] = c
                out.setdefault(a, c)
    chars = ledger.get("characters")
    if isinstance(chars, list):
        for c in chars:
            if isinstance(c, dict):
                _register(c.get("name") or c.get("canonical"),
                          c.get("aliases") or c.get("别名") or c.get("also_known_as"))
    al = ledger.get("aliases")
    if isinstance(al, dict):
        for canon, variants in al.items():
            _register(canon, variants if isinstance(variants, list) else [variants])
    return out


def load_curated_alias_map(project_root: str) -> Dict[str, str]:
    """读人工**已确认**的 curated 别名表 设定/角色别名.json → {别名 -> 规范名}。

    只在 status=='confirmed' 时返回（draft/候选不喂硬闸——自动抽取的别名若误并两个不同角色会让生命周期
    硬闸漏判/误判，必须人工确认后才允许参与确定性归一）。文件由 alias_scaffold.py 生成候选、人确认。
    缺文件/未确认/解析失败 → 空 map（消费端退化为仅用 state_ledger 内联别名·完全向后兼容）。"""
    data = _load_json(os.path.join(project_root, "设定", "角色别名.json"))
    if not isinstance(data, dict) or str(data.get("status") or "").strip().lower() != "confirmed":
        return {}
    return build_alias_map(data)  # 复用同一解析：character_aliases / characters[].aliases / aliases


def resolved_alias_map(project_root: str, ledger: Dict[str, Any]) -> Dict[str, str]:
    """合并 state_ledger 内联结构化别名 + 设定/角色别名.json 已确认 curated 别名（curated 优先）。

    供 logic_sentry.scan_structured_ledgers 在跑确定性生命周期闸前解析实体，闭合"抽取→人确认→入闸"环。"""
    merged = dict(build_alias_map(ledger))
    merged.update(load_curated_alias_map(project_root))  # curated 已确认者覆盖内联推断
    return merged


def _canonical(name: str, alias_map: Dict[str, str]) -> str:
    """别名 → 规范名（缺别名表或未登记 → 原样返回·幂等）。"""
    return alias_map.get(name, name) if alias_map else name


def detect_lifecycle_conflicts(ledger: Dict[str, Any], chapter_index=None,
                               alias_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """A1·结构化生命周期确定性检测（B10-earned 硬闸）。

    只消费 character_changes[*].event 的**结构化枚举**（death/exit/revival…），按章序追踪每角色生死态：
    death/exit → 标记退场章；revival → 解除；已退场角色在更晚章节出现**非复活类结构化 event** = 确定性矛盾
    （枚举×章号比较·绝不扫正文）。无结构化 event 的旧条目一律忽略（留给 check_graph_sentry 关键词 advisory 路径）。
    **实体消解**：用 alias_map 把本名/封号/化名归一到规范名再逐角色追踪（缺 alias_map 时从 ledger 结构化别名源
    自建；都没有则退化为 raw-name·向后兼容）——治"死亡记在本名、复现记在封号→硬闸漏判"。
    chapter_index 非空时只返回复现章==该章的冲突（供 post_write 单章闸）。alerts 字段与 logic_sentry 对齐。"""
    if not isinstance(ledger, dict):
        return []
    if alias_map is None:
        alias_map = build_alias_map(ledger)
    exited: Dict[str, Dict[str, Any]] = {}
    out: List[Dict[str, Any]] = []
    for ch, raw_name, change, event in _iter_character_changes(ledger):
        if not event:
            continue  # B10：硬闸权要靠结构化字段挣得，自由文本不参与确定性判定
        name = _canonical(raw_name, alias_map)
        if event in _REVIVAL_EVENTS:
            exited.pop(name, None)
            continue
        if event in _DEATH_EXIT_EVENTS:
            exited[name] = {"exit_chapter": ch, "exit_event": event, "exit_name": raw_name}
            continue
        prev = exited.get(name)
        if prev and ch > prev["exit_chapter"]:
            alias_note = ""
            if prev.get("exit_name") and prev["exit_name"] != raw_name:
                alias_note = f"（别名归一：退场记于「{prev['exit_name']}」、复现记于「{raw_name}」→ 同一角色「{name}」）"
            out.append({
                "type": "deceased_ledger_reactivation",
                "entity": name,
                "severity": "阻断级",
                "confidence": "deterministic",
                "chapter": ch,
                "exit_chapter": prev["exit_chapter"],
                "exit_event": prev["exit_event"],
                "reappear_event": event,
                "evidence": f"state_ledger：第{prev['exit_chapter']}章 event「{prev['exit_event']}」退场 → 第{ch}章 event「{event}」{alias_note}",
                "auto": True,
                "note": ("作者台账(state_ledger)记录已退场/已故角色在死亡章之后发生非复活类结构化事件——"
                         "确定性矛盾(枚举×章号·不扫正文)；若为合法剧情请在 state_delta 补一条 event=revival/复活"),
            })
    if chapter_index is not None:
        cidx = _chapter_no(chapter_index)
        out = [a for a in out if a["chapter"] == cidx]
    return out


def _fact_interval(fact: Dict[str, Any]):
    """原子事实有效区间 [established_at, invalidated_at)；缺省 established_at←chapter、invalidated_at←+∞。"""
    est = fact.get("established_at", fact.get("chapter"))
    inv = fact.get("invalidated_at")
    est = _chapter_no(est) if est not in (None, "") else 0
    inv = _chapter_no(inv) if inv not in (None, "") else float("inf")
    return est, inv


def _intervals_overlap(a, b) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def detect_fact_interval_conflicts(world_ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A2·世界设定原子事实有效区间确定性检测（FACTTRACK 式·不扫正文）。

    world_state_ledger.major_changes 里**带 key+value 的结构化原子事实**：同一 key 的两条事实若有效区间
    [established_at,invalidated_at) 重叠却 value 不同 → 同一属性在同一时间持两个值 = 确定性矛盾（纯区间运算）。
    只给自由文本/forbidden_* 的旧条目本函数忽略（留给 scan_world_rules 的关键词 advisory 路径）。"""
    facts = []
    changes = (world_ledger or {}).get("major_changes", []) if isinstance(world_ledger, dict) else []
    for entry in changes:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key") or "").strip()
        if not key or "value" not in entry:
            continue
        facts.append((key, str(entry.get("value")).strip(), _fact_interval(entry)))
    out: List[Dict[str, Any]] = []
    seen = set()
    for i in range(len(facts)):
        for j in range(i + 1, len(facts)):
            k1, v1, iv1 = facts[i]
            k2, v2, iv2 = facts[j]
            if k1 != k2 or v1 == v2 or not _intervals_overlap(iv1, iv2):
                continue
            sig = tuple(sorted((f"{v1}@{iv1}", f"{v2}@{iv2}")))
            if sig in seen:
                continue
            seen.add(sig)
            lo = max(iv1[0], iv2[0])
            hi = min(iv1[1], iv2[1])
            hi_s = "∞" if hi == float("inf") else int(hi)
            out.append({
                "type": "world_fact_interval_conflict",
                "entity": k1,
                "severity": "阻断级",
                "confidence": "deterministic",
                "chapter": lo,
                "evidence": f"「{k1}」在第{lo}–{hi_s}章同时被赋值「{v1}」与「{v2}」（有效区间重叠·值冲突）",
                "auto": True,
                "note": ("world_state_ledger 同一 key 的两条原子事实有效区间重叠但取值不同——确定性设定矛盾；"
                         "缩小其中一条的 [established_at,invalidated_at) 或修正 value"),
            })
    return out


def check_graph_sentry(project_root: str) -> Dict[str, Any]:
    """角色生命周期时序一致性检查。report-only，blocking 恒 0。"""
    ledger = _load_json(os.path.join(project_root, "审稿", "state_ledger.json"))
    if not isinstance(ledger, dict) or not ledger.get("chapter_deltas"):
        return {
            "status": "no_ledger",
            "blocking": 0,
            "report_only": True,
            "alerts": [],
            "note": "审稿/state_ledger.json 缺失或无 chapter_deltas；先跑 post_write 闭环建账本再检。",
        }

    # A1·结构化生命周期确定性 alerts（带 confidence=deterministic·可被上层 gate 升为硬阻断）。
    # graph_sentry 自身仍 report-only（blocking 恒 0），但把确定性候选与关键词 advisory 一并报出。
    alerts: List[Dict[str, Any]] = list(detect_lifecycle_conflicts(ledger))

    # 关键词 advisory 路径：只对**没有结构化 event** 的旧条目跑（结构化条目已由上面确定性路径覆盖，避免双报）。
    exited: Dict[str, Dict[str, Any]] = {}
    for ch, name, change, event in _iter_character_changes(ledger):
        if event:
            continue  # 结构化 event 走确定性路径，关键词路径跳过
        prev_exit = exited.get(name)
        if prev_exit and ch > prev_exit["exit_chapter"]:
            revived = bool(_REVIVE_RE.search(change))
            alerts.append({
                "type": "character_reappears_after_exit",
                "character": name,
                "entity": name,
                "exit_chapter": prev_exit["exit_chapter"],      # facet 1：退场时态
                "exit_change": prev_exit["exit_change"],
                "reappear_chapter": ch,                          # facet 2：复现时态
                "reappear_change": change,
                "severity": "advisory" if revived else "阻断级",
                "confidence": "heuristic",                       # 关键词扫描·脆弱→上层 enforce 会降为建议级
                "note": ("复现说明含复活/回归标记，按合法剧情仅提示；如非有意请补伏笔。"
                         if revived else
                         "已退场角色在更晚章节再次活动，且未见复活/回归交代——疑似跨章逻辑穿帮。"),
            })
            if revived:
                exited.pop(name, None)  # 合法复活：清掉退场态，恢复活跃（保留演变，不再重复报）
        if _EXIT_RE.search(change) and not _REVIVE_RE.search(change):
            exited[name] = {"exit_chapter": ch, "exit_change": change}

    hard = [a for a in alerts if a["severity"] == "阻断级"]
    deterministic = [a for a in alerts if a.get("confidence") == "deterministic"]
    return {
        "status": "conflicts" if hard else ("advisory" if alerts else "clean"),
        "blocking": 0,                       # report-only：永不门控，由人/上层 gate（logic_sentry）决定是否升级
        "deterministic_candidates": len(deterministic),  # 这些在 logic_sentry 闸里会真硬阻断
        "report_only": True,
        "characters_tracked": len({n for _, n, _, _ in _iter_character_changes(ledger)}),
        "alerts": alerts,
    }


def main():
    p = argparse.ArgumentParser(description="角色生命周期时序一致性哨兵（report-only）")
    p.add_argument("project_path")
    args = p.parse_args()
    result = check_graph_sentry(args.project_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
