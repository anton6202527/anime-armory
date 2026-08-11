#!/usr/bin/env python3
"""story_spine.py — 编剧级"主线提炼 + 支线剪枝"层（P-1 · 拆集前的全书改编策略）。

真实编剧改编长篇小说时，不会把每条支线都逐集成戏，而是先提炼**主线骨架**，
再决定哪些**支线**服务主线（保留）、哪些是可压缩/折叠的服务线、哪些是偏离主线的
**旁枝**（可裁）。本 skill 把这套判断变成可审计、可机检、有连通性证明的合同：

  - `开发包/story_spine.json`：主线节点 + 线程分类(spine/supporting/tangent) +
    取舍决策(keep/compress/fold_into_main/cut) + **连通性证明**（裁剪后伏笔如何回收、
    主线是否仍衔接、有无孤儿伏笔）+ 不合理点修正(continuity_fixes)。

忠实底线（硬约束）：
  - 只对**已确认**的 `设定库/source_comprehension.json`（因果链 + 伏笔账）操作，禁止臆造。
  - 任何 cut/compress/fold 都必须证明**没有孤儿伏笔**且**主线仍衔接**。
  - 受保护功能（人物动机/选择后果/伏笔兑现/状态变化/系统规则）不得被裁。
  - 带 `do_not_drop_reason` 的伏笔若其唯一承载线程被 cut，必须写 payoff_reroute，否则 block。

强度由 `_设置.md` 的 `主线剪枝` 选择点决定：
  - 保守：story_spine 仅建议，不阻断（兼容老项目/已拆集项目）。
  - 突出主线(默认)：缺 confirmed + 通过校验的 story_spine 则阻断写词。
  - 激进精简：同上，且鼓励更大幅裁旁枝（校验规则一致）。

Usage:
  python3 story_spine.py <作品根> scaffold [--write] [--force]
  python3 story_spine.py <作品根> check [--json] [--markdown]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

N2D_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
try:  # 设置读取属同系列 _lib，缺失时降级为 advisory，不让主流程崩。
    from settings import load_settings  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover
    def load_settings(work_root: str) -> Dict[str, str]:  # type: ignore
        return {}

KIND = "n2d_story_spine"
CHECK_KIND = "n2d_story_spine_check"
VERSION = 1
PACK_DIR = "开发包"
SPINE_FILE = "story_spine.json"
COMPREHENSION_JSON = "设定库/source_comprehension.json"
ADAPTATION_STRATEGY = "开发包/adaptation_strategy.json"
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)

THREAD_CLASSES = {"spine", "supporting", "tangent"}
THREAD_DECISIONS = {"keep", "compress", "fold_into_main", "cut"}
NON_KEEP_DECISIONS = {"compress", "fold_into_main", "cut"}
DEFAULT_PROTECTED = ["人物动机", "选择后果", "伏笔兑现", "状态变化", "系统/力量规则"]

# 主线剪枝强度 → 是否把校验失败当阻断。
ENFORCE_MODES = {"突出主线", "激进精简"}
ADVISORY_MODES = {"保守"}

# ---------------------------------------------------------------------------
# 章节锚：source_spans 的机器可读子集（P4 · 让 cut 决策真正驱动拆集）
# ---------------------------------------------------------------------------
# 只严格认「第X章」「第X-Y章」「第X章-第Y章」（连接符 - – — ~ ～ 至 到；章/回/节/卷），
# 任何附加限定（"第3章前半"、"第3章打斗段"）都判不可解析——宁可不剔，不可误剔。
# 数字解析与 split_novel.parse_chapter_number 同口径（同线复制不 import，避免循环依赖）。
_CH_NUM = r"[0-9零〇一二三四五六七八九十百千万两]+"
_CHAPTER_UNIT = "章回囬囘廻节節卷"
_CHAPTER_SPAN_RANGE_RE = re.compile(
    rf"^第\s*({_CH_NUM})\s*[{_CHAPTER_UNIT}]?\s*(?:[-–—~～]|至|到)\s*(?:第\s*)?({_CH_NUM})\s*[{_CHAPTER_UNIT}]$"
)
_CHAPTER_SPAN_SINGLE_RE = re.compile(rf"^第\s*({_CH_NUM})\s*[{_CHAPTER_UNIT}]$")
_CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def _chapter_token_to_int(token: str) -> Optional[int]:
    token = str(token or "").strip()
    if token.isdigit():
        return int(token)
    if not token or any(ch not in _CN_DIGITS and ch not in _CN_UNITS and ch != "万" for ch in token):
        return None
    total = section = number = 0
    for ch in token:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            section += (number or 1) * _CN_UNITS[ch]
            number = 0
        elif ch == "万":
            total += ((section + number) or 1) * 10000
            section = number = 0
    return total + section + number


_CHAPTER_HEADING_RE = re.compile(rf"^\s*(?:\[编辑\]\s*)?第\s*({_CH_NUM})\s*[{_CHAPTER_UNIT}]")


def chapter_heading_number(line: str) -> Optional[int]:
    """一行文本若是「第X章」式标题则返回章号（供下游按章定位源文；非标题返回 None）。"""
    m = _CHAPTER_HEADING_RE.match(str(line or ""))
    return _chapter_token_to_int(m.group(1)) if m else None


def parse_chapter_span(text: str) -> Optional[Tuple[int, int]]:
    """严格解析一条 source_span 为闭区间 (start, end)；解析不了返回 None（fail-closed 不剔）。"""
    s = str(text or "").strip()
    m = _CHAPTER_SPAN_RANGE_RE.match(s)
    if m:
        a, b = _chapter_token_to_int(m.group(1)), _chapter_token_to_int(m.group(2))
        if a is not None and b is not None and 1 <= a <= b:
            return (a, b)
        return None
    m = _CHAPTER_SPAN_SINGLE_RE.match(s)
    if m:
        a = _chapter_token_to_int(m.group(1))
        return (a, a) if a is not None and a >= 1 else None
    return None


def parse_chapter_spans(spans: Sequence[Any]) -> Tuple[set, List[str]]:
    """spans 列表 → (可解析章号集合, 不可解析原文列表)。"""
    chapters: set = set()
    unparsed: List[str] = []
    for raw in spans or []:
        span = parse_chapter_span(raw)
        if span is None:
            if str(raw or "").strip():
                unparsed.append(str(raw).strip())
        else:
            chapters.update(range(span[0], span[1] + 1))
    return chapters, unparsed


def _thread_anchor_chapters(t: Mapping[str, Any]) -> Tuple[set, List[str]]:
    """线程的章节锚：显式 source_chapters（机器优先）∪ 可解析的 source_spans。"""
    chapters: set = set()
    explicit = t.get("source_chapters")
    if isinstance(explicit, list):
        for x in explicit:
            try:
                n = int(x)
            except (TypeError, ValueError):
                continue
            if n >= 1:
                chapters.add(n)
    parsed, unparsed = parse_chapter_spans(t.get("source_spans") or [])
    chapters.update(parsed)
    return chapters, unparsed


def spine_cut_chapter_plan(root: Path) -> Dict[str, Any]:
    """把 confirmed story_spine 的 cut 决策解析成拆集可执行的整章剔除计划。

    忠实底线：
      - 只有 decision=cut 的线程参与整章剔除；compress/fold_into_main 的内容部分保留，
        压缩发生在写词阶段，拆集不得整章丢其源文。
      - 冲突章（同时被主线 spine 节点 / 非 cut 线程 / 有实质 issue 的 continuity_fix
        锚定）不剔除，记入 conflicts —— 宁可多保留，不可误剔主线承载文本。
      - 不可解析的 span 产不出剔除（fail-closed），原文记入 unparsed_spans 供补锚。
    """
    mode, mode_source = spine_mode(root)
    out: Dict[str, Any] = {
        "kind": "n2d_spine_cut_chapter_plan",
        "source": f"{PACK_DIR}/{SPINE_FILE}",
        "mode": mode,
        "mode_source": mode_source,
        "status": "missing",
        "cut_chapters": {},
        "cut_threads": [],
        "conflicts": [],
        "unparsed_spans": [],
    }
    data = load_json(root / PACK_DIR / SPINE_FILE)
    if not isinstance(data, dict):
        return out
    if str(data.get("status") or "").strip().lower() != "confirmed":
        out["status"] = "not_confirmed"
        return out
    spine = [n for n in (data.get("spine") or []) if isinstance(n, Mapping)]
    threads = [t for t in (data.get("threads") or []) if isinstance(t, Mapping)]

    # 保护集：主线节点锚 + 非 cut 线程锚 + 有实质 issue 的修正锚。
    protected: Dict[int, List[str]] = {}

    def _protect(chapters: set, owner: str) -> None:
        for ch in chapters:
            protected.setdefault(ch, []).append(owner)

    spine_span_chapters, _ = parse_chapter_spans(
        [n.get("source_span") for n in spine if str(n.get("source_span") or "").strip()])
    _protect(spine_span_chapters, "spine")
    for t in threads:
        if str(t.get("decision") or "").strip() != "cut":
            chapters, _ = _thread_anchor_chapters(t)
            _protect(chapters, f"thread:{t.get('id')}")
    fixes = [f for f in (data.get("continuity_fixes") or []) if isinstance(f, Mapping)]
    fix_chapters, _ = parse_chapter_spans(
        [f.get("source_span") for f in fixes if str(f.get("issue") or "").strip()])
    _protect(fix_chapters, "continuity_fix")

    cut_map: Dict[int, List[str]] = {}
    for t in threads:
        if str(t.get("decision") or "").strip() != "cut":
            continue
        tid = str(t.get("id") or t.get("name") or "?")
        chapters, unparsed = _thread_anchor_chapters(t)
        for raw in unparsed:
            out["unparsed_spans"].append({"thread_id": tid, "span": raw})
        out["cut_threads"].append({
            "id": tid,
            "name": t.get("name"),
            "anchored_chapters": sorted(chapters),
        })
        for ch in chapters:
            cut_map.setdefault(ch, []).append(tid)

    if not out["cut_threads"]:
        out["status"] = "no_cut_threads"
        return out

    for ch in sorted(cut_map):
        if ch in protected:
            out["conflicts"].append({
                "chapter": ch,
                "cut_threads": sorted(set(cut_map[ch])),
                "protected_by": sorted(set(protected[ch])),
            })
        else:
            out["cut_chapters"][ch] = sorted(set(cut_map[ch]))
    out["status"] = "ok"
    return out


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# 上游读取
# ---------------------------------------------------------------------------

def _understanding_contract(root: Path) -> Dict[str, Any]:
    data = load_json(root / COMPREHENSION_JSON)
    if not isinstance(data, dict):
        return {}
    uc = data.get("understanding_contract")
    return uc if isinstance(uc, dict) else {}


def _foreshadow_ledger(root: Path) -> List[Dict[str, Any]]:
    uc = _understanding_contract(root)
    fl = uc.get("foreshadowing_ledger")
    return [r for r in fl if isinstance(r, dict)] if isinstance(fl, list) else []


def _causality_chain(root: Path) -> List[Dict[str, Any]]:
    uc = _understanding_contract(root)
    cc = uc.get("causality_chain")
    return [r for r in cc if isinstance(r, dict)] if isinstance(cc, list) else []


def _causal_id(row: Mapping[str, Any]) -> str:
    return str(row.get("trace_id") or row.get("id") or "").strip()


def _causal_ids(root: Path) -> set:
    """源理解合同因果链里的稳定 trace_id 全集（真值源·防臆造 depends_on/下游依赖 id）。"""
    return {cid for cid in (_causal_id(r) for r in _causality_chain(root)) if cid}


def _must_keep_cause_ids(root: Path) -> set:
    """因果链里标了 must_keep 的因果 trace_id——这类是主线衔接的硬承接点，裁剪必须 reroute。"""
    out = set()
    for r in _causality_chain(root):
        cid = _causal_id(r)
        if cid and str(r.get("must_keep") or "").strip():
            out.add(cid)
    return out


def _spine_ids(spine: Sequence[Mapping[str, Any]]) -> set:
    return {str(n.get("id") or "").strip() for n in spine if isinstance(n, Mapping) and str(n.get("id") or "").strip()}


def _spine_depends_on(spine: Sequence[Mapping[str, Any]]) -> List[Tuple[str, str]]:
    """(spine_node_id, dep_id) 对：主线节点声明它依赖的上游因果/伏笔/主线 id。"""
    out: List[Tuple[str, str]] = []
    for n in spine:
        if not isinstance(n, Mapping):
            continue
        nid = str(n.get("id") or "?").strip()
        for dep in n.get("depends_on") or []:
            dep = str(dep).strip()
            if dep:
                out.append((nid, dep))
    return out


def _mainline_dep_carriers(threads: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """dep_id → 声明「承载/喂给主线该依赖」的线程列表（connectivity.downstream_mainline_deps）。

    这一层此前只在 scaffold 里存在、从不被读取；激活它把「裁这条支线后主线还接得上吗」
    从 payoff_reroute 的散文断言，升级成可机检的依赖图边。"""
    out: Dict[str, List[Dict[str, Any]]] = {}
    for t in threads:
        if not isinstance(t, Mapping):
            continue
        conn = t.get("connectivity") if isinstance(t.get("connectivity"), Mapping) else {}
        reroute = str(conn.get("payoff_reroute") or "").strip()
        decision = str(t.get("decision") or "").strip()
        for dep in conn.get("downstream_mainline_deps") or []:
            dep = str(dep).strip()
            if not dep:
                continue
            out.setdefault(dep, []).append({
                "thread_id": t.get("id"),
                "name": t.get("name"),
                "decision": decision,
                "payoff_reroute": reroute,
            })
    return out


def _protected_functions(root: Path) -> List[str]:
    data = load_json(root / ADAPTATION_STRATEGY)
    if isinstance(data, dict):
        pf = data.get("protected_functions")
        if isinstance(pf, list) and pf:
            return [str(x) for x in pf]
    return list(DEFAULT_PROTECTED)


def _foreshadow_id(row: Mapping[str, Any]) -> str:
    return str(row.get("trace_id") or row.get("id") or "").strip()


def spine_mode(root: Path) -> Tuple[str, str]:
    """返回 (mode, source)：mode ∈ {enforce, advisory}。缺省/保守 → advisory。"""
    try:
        settings = load_settings(str(root))
    except Exception:
        settings = {}
    raw = str(settings.get("主线剪枝") or settings.get("主线聚焦") or settings.get("支线剪枝") or "").strip()
    if raw in ENFORCE_MODES:
        return "enforce", f"_设置.md:主线剪枝={raw}"
    if raw in ADVISORY_MODES:
        return "advisory", f"_设置.md:主线剪枝={raw}"
    return "advisory", "未设置（默认 advisory，仅建议不阻断）"


# ---------------------------------------------------------------------------
# scaffold
# ---------------------------------------------------------------------------

def _scaffold_payload(root: Path) -> Dict[str, Any]:
    ledger = _foreshadow_ledger(root)
    protected_ids = [_foreshadow_id(r) for r in ledger if str(r.get("do_not_drop_reason") or "").strip()]
    protected_ids = [x for x in protected_ids if x]
    return {
        "kind": KIND,
        "version": VERSION,
        "status": "draft",
        "generated_at": now_iso(),
        "mainline_logline": "待补：一句话主线——主角欲望 + 主矛盾 + 核心兑现（不含旁枝）。",
        "consumes": [COMPREHENSION_JSON, ADAPTATION_STRATEGY],
        "spine": [
            {
                "id": "SPINE_01",
                "beat": "待补：主线节点（起因/推进/转折/高潮/兑现之一）",
                "source_span": "待补：第X章 / 第X-Y章",
                "causal_role": "起因",
                # depends_on：本主线节点依赖的上游 id，引用 source_comprehension 因果链 SRC_CAUSE_*
                # 或伏笔账 SRC_FORESHADOW_* 或前序 SPINE_* —— 禁止臆造，check 会核对是否真实存在。
                "depends_on": [],
            }
        ],
        "threads": [
            {
                "id": "THREAD_A",
                "name": "待补：线程名（如 广武县狼患支线）",
                "class": "supporting",
                "serves_mainline": "待补：如何服务主线；若 tangent 写为什么偏离主线",
                "decision": "keep",
                "weight": "mid",
                # source_spans 写成严格的「第X章 / 第X-Y章」可被机读：decision=cut 的线程
                # 会在 split_novel 拆集时整章剔除（与主线/保留锚冲突的章除外）。
                # 也可用 source_chapters: [3, 4] 直接给整数章号（机器优先）。
                "source_spans": ["待补：第X-Y章"],
                "cut_keywords": [],
                "opens_foreshadow": [],
                "pays_foreshadow": [],
                "connectivity": {
                    # downstream_mainline_deps：本支线承载/喂给主线的因果依赖 id（SRC_CAUSE_*/SPINE_*）。
                    # 若本支线被 cut/fold/compress，check 会验证这些依赖有 payoff_reroute 承接，
                    # 否则判 mainline_dependency_orphaned（主线衔接断裂）。禁止臆造 id。
                    "downstream_mainline_deps": [],
                    "payoff_reroute": "",
                    "no_orphan_proof": "",
                },
            }
        ],
        "continuity_fixes": [
            {
                "id": "FIX_01",
                "issue": "待补：原著不合理/矛盾点（可留空数组表示无需修正）",
                "source_span": "待补：第X章",
                "fix": "待补：最小改动的世界观内修正",
                "no_contradiction_proof": "待补：证明不与后文已确认事件冲突（引用 SPINE/SRC_FORESHADOW id）",
                "touches_protected": False,
            }
        ],
        "protected_invariants": _protected_functions(root),
        "_source_foreshadow_ids": [_foreshadow_id(r) for r in ledger if _foreshadow_id(r)],
        "_source_protected_foreshadow_ids": protected_ids,
    }


def scaffold(root: Path, *, force: bool = False) -> Dict[str, Any]:
    path = root / PACK_DIR / SPINE_FILE
    created = False
    if force or not path.exists():
        write_json_atomic(path, _scaffold_payload(root))
        created = True
    return {
        "kind": KIND,
        "root": str(root),
        "file": f"{PACK_DIR}/{SPINE_FILE}",
        "created": created,
        "note": "补齐主线/线程/连通性证明后把 status 改为 confirmed，再跑 check。",
    }


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def _issue(rows: List[Dict[str, Any]], severity: str, code: str, message: str,
           evidence: Optional[Dict[str, Any]] = None) -> None:
    row: Dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if evidence:
        row["evidence"] = evidence
    rows.append(row)


def _referenced_foreshadows(threads: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """foreshadow_id → 引用它的线程列表（含 decision）。"""
    out: Dict[str, List[Dict[str, Any]]] = {}
    for t in threads:
        if not isinstance(t, Mapping):
            continue
        decision = str(t.get("decision") or "").strip()
        for key in ("opens_foreshadow", "pays_foreshadow"):
            for fid in t.get(key) or []:
                fid = str(fid).strip()
                if not fid:
                    continue
                out.setdefault(fid, []).append({
                    "thread_id": t.get("id"),
                    "name": t.get("name"),
                    "decision": decision,
                    "ref_kind": key,
                    "payoff_reroute": str((t.get("connectivity") or {}).get("payoff_reroute") or "").strip()
                        if isinstance(t.get("connectivity"), Mapping) else "",
                })
    return out


def check(root: Path, *, write_missing: bool = False) -> Dict[str, Any]:
    path = root / PACK_DIR / SPINE_FILE
    mode, mode_source = spine_mode(root)
    issues: List[Dict[str, Any]] = []

    if not path.exists():
        if write_missing:
            scaffold(root)
        _issue(issues, "block", "story_spine_missing",
                f"缺 {PACK_DIR}/{SPINE_FILE}（主线提炼 + 支线剪枝合同）。已写脚手架，补齐后 confirm。")
        return _finalize(root, mode, mode_source, issues, spine=None)

    data = load_json(path)
    if not isinstance(data, dict):
        _issue(issues, "block", "story_spine_unparseable", "story_spine.json 无法解析或不是 object。")
        return _finalize(root, mode, mode_source, issues, spine=None)

    blob = json.dumps(data, ensure_ascii=False)
    if PLACEHOLDER_RE.search(blob):
        _issue(issues, "block", "story_spine_has_placeholder", "story_spine.json 仍含 待补/TODO 占位。")
    if str(data.get("status") or "").strip().lower() != "confirmed":
        _issue(issues, "block", "story_spine_not_confirmed", "story_spine.json 的 status 不是 confirmed。")

    spine = data.get("spine") if isinstance(data.get("spine"), list) else []
    threads = [t for t in (data.get("threads") or []) if isinstance(t, Mapping)]
    fixes = [f for f in (data.get("continuity_fixes") or []) if isinstance(f, Mapping)]
    protected_invariants = [str(x) for x in (data.get("protected_invariants") or [])]

    if not spine:
        _issue(issues, "block", "spine_empty", "spine 主线节点为空——必须先提炼主线骨架。")
    if not threads:
        _issue(issues, "warn", "threads_empty", "threads 为空——至少登记主要支线的取舍（哪怕都是 keep）。")

    # 上游伏笔账（真值源，防臆造）
    ledger = _foreshadow_ledger(root)
    source_fids = {_foreshadow_id(r) for r in ledger if _foreshadow_id(r)}
    protected_fids = {_foreshadow_id(r) for r in ledger if str(r.get("do_not_drop_reason") or "").strip()}
    protected_fids = {x for x in protected_fids if x}
    if not source_fids:
        _issue(issues, "warn", "source_comprehension_missing_ledger",
               f"未从 {COMPREHENSION_JSON} 读到伏笔账；无法做孤儿伏笔机检，先确认源理解合同。")

    # 线程级校验
    for t in threads:
        tid = str(t.get("id") or t.get("name") or "?")
        cls = str(t.get("class") or "").strip()
        decision = str(t.get("decision") or "").strip()
        conn = t.get("connectivity") if isinstance(t.get("connectivity"), Mapping) else {}
        if cls not in THREAD_CLASSES:
            _issue(issues, "block", "thread_class_invalid",
                   f"线程 {tid} 的 class={cls or '空'} 非法（应为 {sorted(THREAD_CLASSES)}）。")
        if decision not in THREAD_DECISIONS:
            _issue(issues, "block", "thread_decision_invalid",
                   f"线程 {tid} 的 decision={decision or '空'} 非法（应为 {sorted(THREAD_DECISIONS)}）。")
        # 主线线程不得被裁
        if cls == "spine" and decision in {"cut", "fold_into_main"}:
            _issue(issues, "block", "spine_thread_cut",
                   f"线程 {tid} 属主线(class=spine)却 decision={decision}——主线不得裁剪/折叠。")
        # 非保留决策必须给连通性证明
        if decision in NON_KEEP_DECISIONS:
            reroute = str(conn.get("payoff_reroute") or "").strip()
            no_orphan = str(conn.get("no_orphan_proof") or "").strip()
            if not reroute:
                _issue(issues, "block", "cut_without_reroute",
                       f"线程 {tid} decision={decision} 但缺 connectivity.payoff_reroute（伏笔/因果由谁承接）。")
            if not no_orphan:
                _issue(issues, "block", "cut_without_orphan_proof",
                       f"线程 {tid} decision={decision} 但缺 connectivity.no_orphan_proof（证明裁后无孤儿伏笔/断裂因果）。")
            if bool(t.get("touches_protected")):
                _issue(issues, "block", "cut_touches_protected",
                       f"线程 {tid} 标了 touches_protected 却要 {decision}——受保护功能不得被裁。")
        # 防臆造：引用的伏笔 id 必须存在于源伏笔账
        if source_fids:
            for key in ("opens_foreshadow", "pays_foreshadow"):
                for fid in t.get(key) or []:
                    fid = str(fid).strip()
                    if fid and fid not in source_fids:
                        _issue(issues, "block", "foreshadow_id_fabricated",
                               f"线程 {tid} 引用的伏笔 {fid} 不在 source_comprehension 伏笔账里——禁止臆造 id。",
                               {"thread": tid, "foreshadow": fid})
        # 无源出处的 tangent-cut 提醒
        if decision in NON_KEEP_DECISIONS and not (t.get("source_spans") or t.get("cut_keywords")):
            _issue(issues, "warn", "cut_thread_no_source_anchor",
                   f"线程 {tid} 被 {decision} 但没给 source_spans/cut_keywords；下游 source_adaptation_audit 无法据此免账。")
        # 整章剔除锚可解析性：cut 线程给了 span 却无一条可机读时，split_novel 无法据此
        # 整章剔除源文（只剩 cut_keywords 事后免账）——提醒补成「第X章 / 第X-Y章」或 source_chapters。
        if decision == "cut" and (t.get("source_spans") or t.get("source_chapters")):
            chapters, unparsed = _thread_anchor_chapters(t)
            if not chapters and unparsed:
                _issue(issues, "warn", "cut_thread_spans_unparseable",
                       f"线程 {tid} decision=cut 但 source_spans 无一条可机读（需 '第X章'/'第X-Y章' 或补整数 "
                       f"source_chapters）；拆集无法据此整章剔除，仅剩 cut_keywords 事后免账。",
                       {"thread": tid, "unparsed": unparsed})

    # 孤儿伏笔机检（fail-closed）：受保护伏笔的所有承载线程都被 cut 且无 reroute → block
    refmap = _referenced_foreshadows(threads)
    for fid in sorted(protected_fids):
        refs = refmap.get(fid) or []
        if not refs:
            _issue(issues, "warn", "protected_foreshadow_unmapped",
                   f"受保护伏笔 {fid} 未被任何线程登记（opens/pays）；确认它落在主线或某保留线程上。",
                   {"foreshadow": fid})
            continue
        keeps = [r for r in refs if r["decision"] not in {"cut"}]
        cut_with_reroute = [r for r in refs if r["decision"] == "cut" and r["payoff_reroute"]]
        if not keeps and not cut_with_reroute:
            _issue(issues, "block", "protected_foreshadow_orphaned",
                   f"受保护伏笔 {fid} 的承载线程全部被 cut 且无 payoff_reroute——会产生孤儿伏笔，主线兑现断裂。",
                   {"foreshadow": fid, "refs": refs})
    # 非保护伏笔完全没被登记 → 仅 info（可能落在主线节点上）
    for fid in sorted(source_fids - protected_fids):
        if fid not in refmap:
            _issue(issues, "info", "foreshadow_unmapped",
                   f"伏笔 {fid} 未在 threads 中登记；若它落在主线 spine 节点上可忽略。", {"foreshadow": fid})

    # continuity_fixes 校验
    for f in fixes:
        fid = str(f.get("id") or "?")
        if not str(f.get("issue") or "").strip():
            continue  # 空 issue 视为"无需修正"占位
        if not str(f.get("fix") or "").strip():
            _issue(issues, "warn", "fix_without_fix", f"修正 {fid} 有 issue 却没给 fix。")
        if not str(f.get("no_contradiction_proof") or "").strip():
            _issue(issues, "block", "fix_without_no_contradiction_proof",
                   f"修正 {fid} 缺 no_contradiction_proof——改动必须证明不与后文已确认事件冲突。")
        if bool(f.get("touches_protected")) and not str(f.get("no_contradiction_proof") or "").strip():
            _issue(issues, "block", "fix_touches_protected",
                   f"修正 {fid} 触及受保护功能且无冲突证明。")

    # ── 主线衔接机检（"改了之后要能和后面主要情节衔接上"·机器验证而非散文断言）──
    # 消费源理解合同的因果链 + spine[].depends_on + threads[].connectivity.downstream_mainline_deps，
    # 把「裁一条支线后主线还接不接得上」从 payoff_reroute 的自由文本升级成可机检的依赖图。
    causal_ids = _causal_ids(root)
    must_keep_ids = _must_keep_cause_ids(root)
    spine_ids = _spine_ids(spine)
    known_dep_universe = causal_ids | source_fids | spine_ids
    carriers = _mainline_dep_carriers(threads)

    # (A) 防臆造：depends_on / downstream_mainline_deps 引用的 id 必须是源因果/伏笔/主线里真实存在的。
    #     只在有可对照的真值源（因果链或伏笔账）时才判，避免无源项目误报。
    if known_dep_universe:
        for nid, dep in _spine_depends_on(spine):
            if dep not in known_dep_universe:
                _issue(issues, "block", "causal_dep_fabricated",
                       f"主线节点 {nid} 的 depends_on 引用 {dep} 不在源因果链/伏笔账/主线 id 里——禁止臆造依赖。",
                       {"spine_node": nid, "dep": dep})
        for dep, refs in carriers.items():
            if dep not in known_dep_universe:
                for r in refs:
                    _issue(issues, "block", "causal_dep_fabricated",
                           f"线程 {r.get('thread_id')} 的 downstream_mainline_deps 引用 {dep} 不在源因果链/伏笔账/主线 id 里——禁止臆造依赖。",
                           {"thread": r.get("thread_id"), "dep": dep})

    # (B) 主线依赖孤儿（fail-closed）：某条被主线节点 depends_on 的源因果依赖，
    #     其所有承载线程都被 cut/fold 且无 payoff_reroute、也没有任何保留线程承载 → 主线衔接断裂。
    spine_dep_ids = {dep for _nid, dep in _spine_depends_on(spine)}
    for dep in sorted(spine_dep_ids & causal_ids):
        refs = carriers.get(dep) or []
        if not refs:
            _issue(issues, "info", "mainline_dep_uncarried",
                   f"主线依赖 {dep} 未被任何支线登记 downstream_mainline_deps；若它落在主线 spine 本体上可忽略。",
                   {"dep": dep})
            continue
        kept = [r for r in refs if r["decision"] not in NON_KEEP_DECISIONS]
        cut_with_reroute = [r for r in refs if r["decision"] in NON_KEEP_DECISIONS and r["payoff_reroute"]]
        if not kept and not cut_with_reroute:
            _issue(issues, "block", "mainline_dependency_orphaned",
                   f"主线依赖 {dep} 的承载线程全部被裁/折叠且无 payoff_reroute——裁后主线衔接断裂，后面主要情节接不上。",
                   {"dep": dep, "refs": refs})

    # (C) must_keep 因果硬承接：源因果链标了 must_keep 的承接点，被裁/折叠线程引用且无 reroute → block。
    for dep in sorted(must_keep_ids):
        for r in carriers.get(dep) or []:
            if r["decision"] in NON_KEEP_DECISIONS and not r["payoff_reroute"]:
                _issue(issues, "block", "must_keep_cause_cut_without_reroute",
                       f"因果承接点 {dep}（源理解标 must_keep）被线程 {r.get('thread_id')} {r['decision']} 却无 payoff_reroute——必删的主线因果不得无承接裁剪。",
                       {"dep": dep, "thread": r.get("thread_id")})

    # ── 整章剔除计划透明化（P4）：编剧在 check 时就能看到拆集将剔哪些章、哪些章因
    #    与主线/保留线程/修正锚冲突而被保留。计划本体由 split_novel 消费（enforce 才真剔）。
    cut_plan = spine_cut_chapter_plan(root)
    if cut_plan.get("status") == "ok":
        for c in cut_plan.get("conflicts") or []:
            _issue(issues, "warn", "spine_cut_chapter_conflict",
                   f"第{c['chapter']}章同时被 cut 线程 {c['cut_threads']} 与 {c['protected_by']} 锚定——"
                   f"拆集不会剔除该章（宁可多保留）；若确要剔，先解开锚冲突。", c)
        if cut_plan.get("cut_chapters"):
            chapters = sorted(int(k) for k in cut_plan["cut_chapters"])
            _issue(issues, "info", "spine_cut_chapters_resolved",
                   f"整章剔除计划已解析：第 {chapters} 章将在拆集时整章剔除"
                   f"（mode={cut_plan['mode']}；enforce 才真剔，advisory 只预览记账）。",
                   {"chapters": chapters})
            # 被裁章已进已拆集的集 → 提醒返工路径（重拆会移动后续边界；不 block——
            # 追溯返工是显式决策，走 seam_migrate/n2d-update 最小重制，宪法 F4 语义）。
            cut_set = set(chapters)
            hit_eps: List[Dict[str, Any]] = []
            for raw_file in sorted((root / "脚本").glob("第*集/raw.txt")):
                try:
                    found = sorted({
                        ch for ch in (
                            chapter_heading_number(line)
                            for line in raw_file.read_text(encoding="utf-8").splitlines()
                        ) if ch in cut_set
                    })
                except Exception:
                    continue
                if found:
                    hit_eps.append({"episode": raw_file.parent.name, "chapters": found})
            if hit_eps:
                _issue(issues, "warn", "spine_cut_chapter_already_split",
                       f"被裁章已存在于 {len(hit_eps)} 个已拆集的集里（{[h['episode'] for h in hit_eps]}）——"
                       "剔除只作用于之后的重拆；要让已拆集内容生效需重跑 split（会移动后续边界，"
                       "先做受影响范围返工计划）或走 seam_migrate 最小迁移。",
                       {"episodes": hit_eps})

    return _finalize(root, mode, mode_source, issues, spine=spine, threads=threads)


def _finalize(root: Path, mode: str, mode_source: str, issues: List[Dict[str, Any]],
              *, spine: Optional[Sequence[Any]] = None,
              threads: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    has_block = any(r["severity"] == "block" for r in issues)
    has_warn = any(r["severity"] == "warn" for r in issues)
    if mode == "enforce" and has_block:
        status = "block"
    elif has_block or has_warn:
        status = "advisory"
    else:
        status = "pass"
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "mode": mode,
        "mode_source": mode_source,
        "status": status,
        "summary": {
            "block": sum(1 for r in issues if r["severity"] == "block"),
            "warn": sum(1 for r in issues if r["severity"] == "warn"),
            "info": sum(1 for r in issues if r["severity"] == "info"),
            "spine_nodes": len(spine or []),
            "threads": len(threads or []),
        },
        "issues": issues,
        "scaffold_command": f"python3 skills/n2d/n2d-script/scripts/story_spine.py {root} scaffold --write",
        "next_when_blocked": (
            "补齐 story_spine.json：提炼主线 spine，登记每条支线的 class/decision，"
            "所有 compress/fold/cut 线程写 connectivity(payoff_reroute + no_orphan_proof + "
            "downstream_mainline_deps 引用 SRC_CAUSE_*/SPINE_* 声明它喂给主线的依赖)，"
            "修正不合理点写 no_contradiction_proof，把 status 改为 confirmed，再重跑 check。"
            "只对已确认的 因果链/伏笔账 操作，禁止臆造 id；被主线 depends_on 的 must_keep 因果被裁必须 reroute。"
        ),
    }
    out = root / "生产数据" / "story_spine_check.json"
    try:
        write_json_atomic(out, payload)
        payload["check_path"] = str(out)
    except Exception:
        pass
    return payload


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        "# 主线提炼 + 支线剪枝检查",
        "",
        f"- 状态：{report.get('status')}（mode={report.get('mode')} · {report.get('mode_source')}）",
        f"- 主线节点：{s.get('spine_nodes')}　支线：{s.get('threads')}　block/warn/info：{s.get('block')}/{s.get('warn')}/{s.get('info')}",
        "",
        "| 级别 | code | 说明 |",
        "|---|---|---|",
    ]
    for r in report.get("issues") or []:
        marker = {"block": "BLOCK", "warn": "WARN", "info": "INFO"}.get(r.get("severity"), "INFO")
        lines.append(f"| {marker} | `{r.get('code')}` | {r.get('message')} |")
    lines += ["", str(report.get("next_when_blocked") or "")]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 主线提炼 + 支线剪枝合同（scaffold/check）")
    ap.add_argument("root")
    sub = ap.add_subparsers(dest="command", required=True)
    p_sc = sub.add_parser("scaffold")
    p_sc.add_argument("--write", action="store_true", help="兼容显式写入语义；scaffold 默认即写入")
    p_sc.add_argument("--force", action="store_true", help="覆盖已有文件（谨慎）")
    p_ck = sub.add_parser("check")
    p_ck.add_argument("--json", action="store_true")
    p_ck.add_argument("--markdown", action="store_true")
    p_ck.add_argument("--write-missing", action="store_true", help="缺文件时先补 scaffold，再返回")
    ns = ap.parse_args(argv)

    root = Path(str(ns.root).rstrip("/"))
    if ns.command == "scaffold":
        print(json.dumps(scaffold(root, force=ns.force), ensure_ascii=False, indent=2))
        return 0
    report = check(root, write_missing=ns.write_missing)
    if ns.markdown:
        md = render_markdown(report)
        try:
            write_atomic(root / "生产数据" / "story_spine_check.md", md)
        except Exception:
            pass
        print(md)
    elif ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"主线剪枝检查：{report['status']}（mode={report['mode']}，"
              f"block={report['summary']['block']} warn={report['summary']['warn']}）")
        if report["status"] == "block":
            print(report["next_when_blocked"])
    # 退出码：仅 enforce+block 才非零，让老项目/保守档不因 advisory 报错阻断脚本编排。
    return 1 if report["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
