#!/usr/bin/env python3
"""Audit source raw coverage in n2d script adaptation.

This is a cheap deterministic guard before image prompt generation. It checks
that high-salience source elements in `raw.txt` did not disappear when the
episode was adapted into `voiceover.txt` / storyboard. If the adaptation
intentionally rewrites/compresses a detail for short-drama pacing, the change
must be recorded in `adaptation_triage.json`; the audit will treat that as
tracked rework rather than silent omission.

Usage:
  python3 source_adaptation_audit.py <作品根> 第N集 [--strict] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

EVENT_RE = re.compile(
    r"(死|杀|伤|毒|醒|穿越|重生|系统|提示|升级|突破|发现|真相|背叛|逼|威胁|救|逃|"
    r"打|跪|反击|揭|暴露|秘密|证据|线索|婚|退婚|觉醒|血脉|法宝|灵力|境界|凶手|"
    r"告白|心动|误会|吃醋|分手|复合)"
)
BRACKET_RE = re.compile(r"(【[^】]{2,40}】|《[^》]{2,40}》)")
TITLE_RE = re.compile(
    r"([\u4e00-\u9fff]{1,4}(?:娘娘|王爷|师尊|陛下|公主|太子|小姐|少爷|夫人|长老|"
    r"师兄|师姐|宗主|皇后|贵妃|将军|侍卫|掌门))"
)
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
TITLE_SUFFIXES = (
    "娘娘", "王爷", "师尊", "陛下", "公主", "太子", "小姐", "少爷", "夫人", "长老",
    "师兄", "师姐", "宗主", "皇后", "贵妃", "将军", "侍卫", "掌门",
)
TITLE_FALSE_PREFIX_FRAGMENTS = {
    "要是", "就是", "不是", "还是", "若是", "可是", "但是", "叫", "让", "被", "把", "给",
    "向", "对", "跟", "同", "和", "在", "从", "到", "为", "替", "请", "问", "说", "喊",
    "看", "听", "见", "以为",
}
TITLE_GENERIC_PREFIXES = {"一个", "这个", "那个", "那位", "这位", "某个", "某位", "几位", "诸位"}

STOP_BIGRAMS = {
    "这个", "那个", "他们", "她们", "我们", "你们", "自己", "没有", "不是", "只是", "已经",
    "突然", "然后", "这里", "那里", "一个", "一种", "什么", "怎么", "还是", "因为", "所以",
    "但是", "如果", "时候", "眼前", "身后", "声音", "众人", "所有", "开始", "继续",
}

SCENE_FUNCTIONS: List[Tuple[str, str, re.Pattern[str], str]] = [
    ("motivation", "角色动机", re.compile(r"(为了|想要|必须|誓要|不能让|保护|复仇|活下去|查清|证明)"), "warn"),
    ("conflict_cause", "冲突原因", re.compile(r"(因为|逼|威胁|陷害|背叛|下毒|抢|杀|封锁|通缉)"), "warn"),
    ("setup", "伏笔/线索", re.compile(r"(伏笔|悬念|线索|秘密|信物|玉佩|令牌|印记|不对劲|另有隐情)"), "info"),
    ("payoff", "兑现/爽点", re.compile(r"(反击|打脸|夺回|突破|升级|赢|救出|揭穿|真相|兑现)"), "warn"),
    ("reversal", "反转", re.compile(r"(原来|竟然|没想到|反而|却|逆转|翻盘)"), "warn"),
    ("relationship_shift", "关系变化", re.compile(r"(信任|背叛|心动|误会|和解|决裂|告白|退婚|结盟|仇人)"), "warn"),
    ("world_rule", "世界/系统规则", re.compile(r"(系统|面板|规则|等级|境界|任务|奖励|代价|禁忌)"), "info"),
    ("choice", "角色选择", re.compile(r"(决定|选择|答应|拒绝|放弃|留下|离开|救|杀|公开|隐瞒)"), "warn"),
    ("consequence", "后果/代价", re.compile(r"(因此|于是|代价|后果|失去|得到|暴露|触发|受伤|被抓|关系破裂)"), "warn"),
]

TRIAGE_REWORK_DECISIONS = {
    "narrate", "defer", "merge", "omit",
    "rewrite", "rewrite_detail", "change_detail", "adapt", "rework",
    "compress", "reorder", "intensify", "upgrade_conflict", "add_hook",
}
TRIAGE_EVIDENCE_KEYS = (
    "reason", "delivery", "risk_if_removed", "adaptation_delta", "changed_from",
    "changed_to", "preserved_function", "short_drama_reason", "payoff_guard",
)


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def raw_path(root: str, ep: str) -> Path:
    return Path(root) / "脚本" / ep / "raw.txt"


def adaptation_paths(root: str, ep: str) -> List[Path]:
    base = Path(root) / "脚本" / ep
    return [
        base / "voiceover.txt",
        base / "分镜剧本.md",
        base / "故事板.md",
        base / "storyboard.json",
    ]


def triage_paths(root: str, ep: str) -> List[Path]:
    base = Path(root) / "脚本" / ep
    return [
        base / "adaptation_triage.json",
        Path(root) / "脚本" / "adaptation_triage.json",
    ]


# 全书级"主线提炼 + 支线剪枝"合同：被 spine 显式 cut/compress/fold 的支线，其源文内容
# 不必再在每集 adaptation_triage 里逐句登记——本审计据 story_spine 的 cut_keywords/source_spans
# 直接按"有账剪枝"处理，避免"裁一条支线要逐句免账"的摩擦。仅 status=confirmed 时生效。
SPINE_CUT_DECISIONS = {"cut", "compress", "fold_into_main"}


def load_spine_cuts(root: str) -> List[Dict[str, Any]]:
    path = Path(root) / "开发包" / "story_spine.json"
    if not path.exists():
        return []
    try:
        data = json.loads(read_text(path))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    if str(data.get("status") or "").strip().lower() != "confirmed":
        return []
    cuts: List[Dict[str, Any]] = []
    for t in data.get("threads") or []:
        if not isinstance(t, dict):
            continue
        if str(t.get("decision") or "").strip() not in SPINE_CUT_DECISIONS:
            continue
        keywords = [str(k).strip() for k in (t.get("cut_keywords") or []) if str(k).strip()]
        conn = t.get("connectivity") if isinstance(t.get("connectivity"), dict) else {}
        cuts.append({
            "thread_id": t.get("id"),
            "name": t.get("name"),
            "decision": str(t.get("decision") or "").strip(),
            "keywords": keywords,
            "reroute": str(conn.get("payoff_reroute") or "").strip(),
        })
    return cuts


def spine_authorizes(text: str, cuts: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """flagged 源文片段命中某条 spine-cut 线程的关键词 → 按有账剪枝授权。"""
    if not text:
        return None
    for cut in cuts:
        for kw in cut.get("keywords") or []:
            if kw and kw in text:
                return cut
    return None


# ── 章节锚授权（P4 配套·老项目路径）：keyword 之外的第二条免账通道 ──────────────
# P4 之后新拆的集根本不含被裁章源文；但 P4 之前已拆集的项目，被裁章还在 raw 里，
# 逐词补 cut_keywords 摩擦大。这里消费 story_spine.spine_cut_chapter_plan 的已解析
# 剔除章集合（冲突章已被剔出，天然保守）：被标记的名词/句子在 raw 中的**全部出现**
# 都落在被裁章内才免账——只要有一次出现落在保留章，缺失仍然可疑，不免。
try:
    from story_spine import chapter_heading_number, spine_cut_chapter_plan
except Exception:  # story_spine 不可用时本通道静默关闭，keyword 通道照旧。
    chapter_heading_number = None  # type: ignore
    spine_cut_chapter_plan = None  # type: ignore


def load_spine_cut_chapters(root: str) -> Dict[int, List[str]]:
    """已解析的整章剔除计划 {章号: [thread_id...]}；不可用/未确认/无 cut 线程 → {}。"""
    if spine_cut_chapter_plan is None:
        return {}
    try:
        plan = spine_cut_chapter_plan(Path(root))
    except Exception:
        return {}
    if plan.get("status") != "ok":
        return {}
    return {int(k): list(v) for k, v in (plan.get("cut_chapters") or {}).items()}


def raw_chapter_spans(raw: str) -> List[Tuple[Optional[int], int, int]]:
    """raw 按「第X章」标题切成 (章号, start, end) 偏移段；首个标题前的文本章号为 None。"""
    if chapter_heading_number is None:
        return []
    spans: List[Tuple[Optional[int], int, int]] = []
    current: Optional[int] = None
    seg_start = 0
    pos = 0
    for line in raw.splitlines(keepends=True):
        ch = chapter_heading_number(line)
        if ch is not None:
            if pos > seg_start:
                spans.append((current, seg_start, pos))
            current = ch
            seg_start = pos
        pos += len(line)
    if pos > seg_start:
        spans.append((current, seg_start, pos))
    return spans


def _chapter_at(spans: Sequence[Tuple[Optional[int], int, int]], pos: int) -> Optional[int]:
    for ch, start, end in spans:
        if start <= pos < end:
            return ch
    return None


def spine_chapter_authorizes(text: str, raw: str,
                             spans: Sequence[Tuple[Optional[int], int, int]],
                             cut_chapters: Dict[int, List[str]]) -> Optional[Dict[str, Any]]:
    """text 在 raw 中的全部出现都落在被裁章内 → 返回 {chapters, cut_threads}；否则 None。"""
    if not text or not cut_chapters or not spans:
        return None
    hit_chapters: Set[int] = set()
    pos = raw.find(text)
    if pos < 0:
        return None
    guard = 0
    while pos >= 0 and guard < 200:
        ch = _chapter_at(spans, pos)
        if ch is None or ch not in cut_chapters:
            return None
        hit_chapters.add(ch)
        pos = raw.find(text, pos + 1)
        guard += 1
    threads = sorted({t for ch in hit_chapters for t in cut_chapters.get(ch, [])})
    return {"chapters": sorted(hit_chapters), "cut_threads": threads, "via": "chapter_anchor"}


def spine_summary(cut: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "spine_thread": cut.get("thread_id"),
        "thread_name": cut.get("name"),
        "spine_decision": cut.get("decision"),
        "payoff_reroute": cut.get("reroute"),
    }
    return {k: v for k, v in out.items() if v not in (None, "")}


def adaptation_text(root: str, ep: str) -> Tuple[str, List[str]]:
    chunks: List[str] = []
    used: List[str] = []
    for path in adaptation_paths(root, ep):
        if path.exists():
            text = read_text(path)
            chunks.append(text)
            used.append(str(path))
    return "\n".join(chunks), used


def load_triage_items(root: str, ep: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    items: List[Dict[str, Any]] = []
    used: List[str] = []
    for path in triage_paths(root, ep):
        if not path.exists():
            continue
        try:
            data = json.loads(read_text(path))
        except Exception:
            continue
        used.append(str(path))
        raw_items = data.get("items") if isinstance(data, dict) else data
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if isinstance(item, dict):
                scope = str(item.get("scope") or item.get("episode") or "").strip()
                if scope and scope not in {ep, ep_label(scope)}:
                    continue
                items.append(item)
    return items, used


def triage_blob(item: Dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False)


def triage_has_evidence(item: Dict[str, Any]) -> bool:
    return any(str(item.get(key) or "").strip() for key in TRIAGE_EVIDENCE_KEYS)


def triage_is_rework(item: Dict[str, Any]) -> bool:
    decision = str(item.get("decision") or item.get("change_type") or "").strip().lower()
    change_type = str(item.get("change_type") or "").strip().lower()
    return (decision in TRIAGE_REWORK_DECISIONS or change_type in TRIAGE_REWORK_DECISIONS) and triage_has_evidence(item)


def triage_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "triage_id": item.get("id"),
        "decision": item.get("decision"),
        "change_type": item.get("change_type"),
        "delivery": item.get("delivery"),
        "reason": item.get("reason"),
    }
    return {k: v for k, v in out.items() if v not in (None, "")}


def triage_authorizes_term(term: str, items: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for item in items:
        if not triage_is_rework(item):
            continue
        blob = triage_blob(item)
        if present(term, blob):
            return item
    return None


def triage_authorizes_sentence(sentence: str, required_terms: Sequence[str], items: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for item in items:
        if not triage_is_rework(item):
            continue
        blob = triage_blob(item)
        if any(present(term, blob) for term in required_terms):
            return item
        if sentence_coverage(sentence, blob) >= 0.08:
            return item
    return None


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？!?；;])\s*|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 6]


def cjk_bigrams(text: str) -> Set[str]:
    chars = "".join(CJK_RE.findall(text))
    return {chars[i:i + 2] for i in range(max(0, len(chars) - 1)) if chars[i:i + 2] not in STOP_BIGRAMS}


def normalized_variants(token: str) -> Set[str]:
    token = token.strip()
    variants = {token}
    if token.startswith("【") and token.endswith("】"):
        variants.add(token[1:-1])
    if token.startswith("《") and token.endswith("》"):
        variants.add(token[1:-1])
    return {v for v in variants if v}


def present(token: str, text: str) -> bool:
    return any(v in text for v in normalized_variants(token))


def title_prefix(term: str) -> str:
    for suffix in TITLE_SUFFIXES:
        if term.endswith(suffix):
            return term[:-len(suffix)]
    return ""


def is_probable_title_term(term: str) -> bool:
    """Reject clause fragments accidentally captured before generic titles.

    The title regex intentionally stays lightweight, but Chinese prose often
    has fragments such as "画要是叫长老看见". Without this guard the audit
    treats that whole clause fragment as a required entity and forces awkward
    wording into adaptations.
    """
    term = term.strip()
    prefix = title_prefix(term)
    if not prefix:
        return False
    if prefix in TITLE_GENERIC_PREFIXES:
        return False
    return not any(fragment in prefix for fragment in TITLE_FALSE_PREFIX_FRAGMENTS)


def title_terms(text: str) -> List[str]:
    out: List[str] = []
    for m in TITLE_RE.finditer(text or ""):
        term = m.group(1).strip()
        if is_probable_title_term(term):
            out.append(term)
    return out


def has_important_marker(text: str) -> bool:
    return bool(BRACKET_RE.search(text or "") or title_terms(text or ""))


def important_terms(raw: str) -> List[str]:
    seen: Set[str] = set()
    terms: List[str] = []
    for m in BRACKET_RE.finditer(raw):
        term = m.group(1).strip()
        if term and term not in seen:
            terms.append(term)
            seen.add(term)
    for term in title_terms(raw):
        if term and term not in seen:
            terms.append(term)
            seen.add(term)
    return terms


# ── 反向防瞎编：改编稿里出现、源文没有、也没有有账改写引入的专名/称谓/设定 ──
# 前向 audit 只查 source→adaptation 覆盖（漏没漏）；本层查 adaptation→source（有没有瞎编）。
# 只认可确定性最高的信号：专名括注（【】《》）与称谓（王爷/长老/宗主…）——它们是
# "自造设定/凭空多出一个人物或法宝" 的高召回低误报代理。裸人名不查（无模型易误伤）。
FABRICATION_STOP_TERMS = {
    "系统", "面板", "任务", "奖励", "提示", "宿主", "警告", "检测",
}
# 称谓正则有时把前置连接词/动词一起吞进 term（"是玄冥长老"）；比对源文/授权前先剥掉，
# 得到真正的专名核（"玄冥长老"），避免误判成瞎编。
FAB_LEADING_CONNECTIVES = set("是这那有叫让被把请问说喊看听见和跟同对向从到为替给")


def entity_core(term: str) -> str:
    core = term.strip("【】《》").strip()
    while len(core) > 2 and core[0] in FAB_LEADING_CONNECTIVES:
        core = core[1:]
    return core


def narrative_adaptation_text(root: str, ep: str) -> str:
    """观众实际"听到/读到"的改编文本——只取 voiceover.txt（口播台词/旁白）。

    不取 storyboard 技术字段，避免把镜头/风格括注误判成瞎编专名（低误报优先）。"""
    return read_text(Path(root) / "脚本" / ep / "voiceover.txt")


def fabrication_findings(
    root: str,
    ep: str,
    raw: str,
    triage_items: Sequence[Dict[str, Any]],
    spine_cuts: Sequence[Dict[str, Any]],
    limit: int = 10,
) -> Tuple[List[Dict[str, Any]], int]:
    """改编稿出现、源文没有、也无有账改写引入的专名/设定 → 瞎编候选（report-first·warn）。"""
    narrative = narrative_adaptation_text(root, ep)
    findings: List[Dict[str, Any]] = []
    if not narrative.strip():
        return findings, 0
    candidates: List[str] = []
    seen: Set[str] = set()
    for term in important_terms(narrative):
        core = entity_core(term)
        if core in FABRICATION_STOP_TERMS or len(core) < 2 or core in seen:
            continue
        if present(term, raw) or present(core, raw):
            continue  # 源文有出处，不算瞎编
        seen.add(core)
        candidates.append(core)
    reported = 0
    for term in candidates[:limit]:
        auth = triage_authorizes_term(term, triage_items)
        if auth:
            add(findings, "info", "adaptation_new_term_accounted",
                f"改编稿新增专名/设定 `{term}` 源文未见，但 adaptation_triage 已登记有账改写（rewrite/intensify/combine_minor_role 等）；按有账改编处理。",
                {"term": term, **triage_summary(auth)})
            continue
        spine_auth = spine_authorizes(term, spine_cuts)
        if spine_auth:
            add(findings, "info", "adaptation_new_term_by_spine",
                f"改编稿新增专名 `{term}` 与 story_spine 已登记的改写线程相关；按全书级有账改编处理。",
                {"term": term, **spine_summary(spine_auth)})
            continue
        reported += 1
        add(findings, "warn", "fabricated_entity_candidate",
            f"改编稿出现源文没有的专名/称谓 `{term}`，且无 adaptation_delta 有账引入——疑似瞎编/自造设定；"
            f"确认它是源文别名/合并小角色（去 adaptation_triage 登记 change_type + adaptation_delta），还是应删除。",
            {"term": term})
    return findings, reported


def key_event_sentences(raw: str, limit: int = 10) -> List[str]:
    candidates = [s for s in split_sentences(raw) if EVENT_RE.search(s)]
    # Prefer sentences containing explicit system/name/title/bracket markers,
    # then longer event-heavy sentences. This keeps the report small.
    def score(sentence: str) -> Tuple[int, int]:
        marker = 1 if has_important_marker(sentence) else 0
        hits = len(EVENT_RE.findall(sentence))
        return (marker + hits, min(len(sentence), 160))
    return sorted(candidates, key=score, reverse=True)[:limit]


def scene_function_sentences(raw: str, limit: int = 12) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for sentence in split_sentences(raw):
        hits = [(code, label, severity) for code, label, rx, severity in SCENE_FUNCTIONS if rx.search(sentence)]
        if not hits:
            continue
        marker = 1 if has_important_marker(sentence) else 0
        candidates.append({
            "sentence": sentence,
            "functions": [h[0] for h in hits],
            "labels": [h[1] for h in hits],
            "severity": "warn" if any(h[2] == "warn" for h in hits) else "info",
            "score": len(hits) + len(EVENT_RE.findall(sentence)) + marker,
        })
    return sorted(candidates, key=lambda row: (row["score"], min(len(row["sentence"]), 160)), reverse=True)[:limit]


def function_marker_present(functions: Sequence[str], adapted: str) -> bool:
    by_code = {code: rx for code, _label, rx, _severity in SCENE_FUNCTIONS}
    return any(by_code[code].search(adapted) for code in functions if code in by_code)


def sentence_coverage(sentence: str, adapted: str) -> float:
    grams = cjk_bigrams(sentence)
    if not grams:
        return 1.0
    adapted_grams = cjk_bigrams(adapted)
    return len(grams & adapted_grams) / len(grams)


def local_required_terms(sentence: str) -> List[str]:
    terms = []
    for term in important_terms(sentence):
        if term not in terms:
            terms.append(term)
    return terms


def add(findings: List[Dict[str, Any]], severity: str, code: str, message: str,
        evidence: Optional[Dict[str, Any]] = None) -> None:
    row: Dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if evidence:
        row["evidence"] = evidence
    findings.append(row)


def audit(root: str, ep: str, *, check_fabrication: bool = False) -> Dict[str, Any]:
    ep = ep_label(ep)
    raw_file = raw_path(root, ep)
    findings: List[Dict[str, Any]] = []
    if not raw_file.exists():
        add(findings, "must", "missing_raw", f"缺 {raw_file}，无法核对源文覆盖。")
        return {"episode": ep, "ok": False, "stats": {}, "findings": findings}
    raw = read_text(raw_file)
    adapted, used_paths = adaptation_text(root, ep)
    if not adapted.strip():
        add(findings, "must", "missing_adaptation", f"{ep} 缺 voiceover/storyboard 改编产物，无法核对源文覆盖。")
        return {"episode": ep, "ok": False, "stats": {"raw_chars": len(raw)}, "findings": findings}
    triage_items, triage_used_paths = load_triage_items(root, ep)
    spine_cuts = load_spine_cuts(root)
    spine_cut_chapters = load_spine_cut_chapters(root)
    chapter_spans = raw_chapter_spans(raw) if spine_cut_chapters else []

    terms = important_terms(raw)
    missing_terms = [t for t in terms if not present(t, adapted)]
    triage_authorized_terms = 0
    spine_authorized = 0
    for term in missing_terms[:12]:
        auth = triage_authorizes_term(term, triage_items)
        if auth:
            triage_authorized_terms += 1
            add(findings, "info", "source_term_reworked_by_triage",
                f"源文关键名词 `{term}` 未直接出现在改编稿，但 adaptation_triage 已登记改写/压缩；按有账改编处理。",
                {"term": term, **triage_summary(auth)})
            continue
        spine_auth = spine_authorizes(term, spine_cuts)
        if spine_auth:
            spine_authorized += 1
            add(findings, "info", "source_term_cut_by_spine",
                f"源文关键名词 `{term}` 属 story_spine 已 {spine_auth.get('decision')} 的支线；按全书级有账剪枝处理。",
                {"term": term, **spine_summary(spine_auth)})
            continue
        chapter_auth = spine_chapter_authorizes(term, raw, chapter_spans, spine_cut_chapters)
        if chapter_auth:
            spine_authorized += 1
            add(findings, "info", "source_term_cut_by_spine",
                f"源文关键名词 `{term}` 的全部出现都在 story_spine 已裁的第 {chapter_auth['chapters']} 章内；"
                "按全书级有账剪枝（章节锚）处理。",
                {"term": term, **chapter_auth})
            continue
        sev = "warn"
        code = "source_term_missing"
        add(findings, sev, code, f"源文关键名词 `{term}` 未出现在 voiceover/storyboard；确认不是误删或需改写为等价表达。",
            {"term": term})

    event_sentences = key_event_sentences(raw)
    omitted_events = []
    for sentence in event_sentences:
        required = local_required_terms(sentence)
        if required and any(present(t, adapted) for t in required):
            continue
        cov = sentence_coverage(sentence, adapted)
        # Below 12% shared CJK bigrams means this event is probably absent, not
        # merely compressed. Keep this conservative to avoid punishing paraphrase.
        if cov < 0.12:
            auth = triage_authorizes_sentence(sentence, required, triage_items)
            if auth:
                add(findings, "info", "source_event_reworked_by_triage",
                    "源文关键事件未直接覆盖，但 adaptation_triage 已登记短剧化改写/后文带出；按有账改编处理。",
                    {"sentence": sentence[:120], "coverage": round(cov, 3), **triage_summary(auth)})
                continue
            spine_auth = spine_authorizes(sentence, spine_cuts)
            if spine_auth:
                spine_authorized += 1
                add(findings, "info", "source_event_cut_by_spine",
                    f"源文关键事件属 story_spine 已 {spine_auth.get('decision')} 的支线；按全书级有账剪枝处理。",
                    {"sentence": sentence[:120], "coverage": round(cov, 3), **spine_summary(spine_auth)})
                continue
            chapter_auth = spine_chapter_authorizes(sentence, raw, chapter_spans, spine_cut_chapters)
            if chapter_auth:
                spine_authorized += 1
                add(findings, "info", "source_event_cut_by_spine",
                    f"源文关键事件位于 story_spine 已裁的第 {chapter_auth['chapters']} 章内；按全书级有账剪枝（章节锚）处理。",
                    {"sentence": sentence[:120], "coverage": round(cov, 3), **chapter_auth})
                continue
            omitted_events.append({"sentence": sentence[:120], "coverage": round(cov, 3), "required_terms": required})
    for item in omitted_events[:8]:
        add(findings, "warn", "source_event_maybe_omitted",
            "源文关键事件在改编稿中覆盖率极低；确认没有漏掉动机/伏笔/反转。",
            item)

    function_items = scene_function_sentences(raw)
    lost_functions = []
    for item in function_items:
        sentence = str(item["sentence"])
        required = local_required_terms(sentence)
        cov = sentence_coverage(sentence, adapted)
        has_required_term = bool(required and any(present(t, adapted) for t in required))
        has_same_function = function_marker_present(item["functions"], adapted)
        if cov < 0.10 and not has_required_term and not has_same_function:
            auth = triage_authorizes_sentence(sentence, required, triage_items)
            if auth:
                add(findings, "info", "scene_function_reworked_by_triage",
                    "源文场景功能未直接覆盖，但 adaptation_triage 已登记压缩/重排/强化；按有账改编处理。",
                    {"sentence": sentence[:120], "functions": item["labels"], "coverage": round(cov, 3), **triage_summary(auth)})
                continue
            spine_auth = spine_authorizes(sentence, spine_cuts)
            if spine_auth:
                spine_authorized += 1
                add(findings, "info", "scene_function_cut_by_spine",
                    f"源文场景功能属 story_spine 已 {spine_auth.get('decision')} 的支线；按全书级有账剪枝处理。",
                    {"sentence": sentence[:120], "functions": item["labels"], "coverage": round(cov, 3), **spine_summary(spine_auth)})
                continue
            chapter_auth = spine_chapter_authorizes(sentence, raw, chapter_spans, spine_cut_chapters)
            if chapter_auth:
                spine_authorized += 1
                add(findings, "info", "scene_function_cut_by_spine",
                    f"源文场景功能位于 story_spine 已裁的第 {chapter_auth['chapters']} 章内；按全书级有账剪枝（章节锚）处理。",
                    {"sentence": sentence[:120], "functions": item["labels"], "coverage": round(cov, 3), **chapter_auth})
                continue
            lost_functions.append({
                "sentence": sentence[:120],
                "functions": item["labels"],
                "coverage": round(cov, 3),
            })
    for item in lost_functions[:8]:
        sev = "warn" if any(label in {"角色动机", "冲突原因", "兑现/爽点", "反转", "关系变化", "角色选择", "后果/代价"}
                            for label in item["functions"]) else "info"
        add(findings, sev, "scene_function_maybe_lost",
            "源文场景功能在改编稿中覆盖很低；确认压缩没有删掉剧情功能。",
            item)

    raw_event_count = len(event_sentences)
    adapted_event_count = len(EVENT_RE.findall(adapted))
    if raw_event_count >= 2 and adapted_event_count == 0:
        add(findings, "warn", "adaptation_has_no_event_signals",
            "源文有多个关键事件信号，但改编稿没有检测到冲突/反转/系统/爽点类词，疑似改得过平。",
            {"raw_event_sentences": raw_event_count})

    fabrication_count = 0
    if check_fabrication:
        fab_findings, fabrication_count = fabrication_findings(root, ep, raw, triage_items, spine_cuts)
        findings.extend(fab_findings)

    stats = {
        "raw_chars": len(raw),
        "adaptation_chars": len(adapted),
        "adaptation_paths": used_paths,
        "triage_paths": triage_used_paths,
        "triage_items": len(triage_items),
        "triage_authorized_terms": triage_authorized_terms,
        "spine_cut_threads": len(spine_cuts),
        "spine_cut_chapters": sorted(spine_cut_chapters),
        "spine_authorized_omissions": spine_authorized,
        "important_terms": len(terms),
        "missing_terms": len(missing_terms),
        "key_event_sentences": raw_event_count,
        "omitted_event_sentences": len(omitted_events),
        "scene_function_sentences": len(function_items),
        "lost_scene_functions": len(lost_functions),
        "fabrication_candidates": fabrication_count,
    }
    ok = not any(f["severity"] in {"must", "warn"} for f in findings)
    return {"episode": ep, "ok": ok, "stats": stats, "findings": findings}


def print_human(result: Dict[str, Any]) -> None:
    stats = result.get("stats") or {}
    print(f"# 源文改编覆盖校验 — {result.get('episode')}")
    print(
        f"raw={stats.get('raw_chars', 0)} chars  adapted={stats.get('adaptation_chars', 0)} chars  "
        f"terms_missing={stats.get('missing_terms', 0)}  events_omitted={stats.get('omitted_event_sentences', 0)}  "
        f"scene_functions_lost={stats.get('lost_scene_functions', 0)}"
    )
    findings = result.get("findings") or []
    if not findings:
        print("- PASS：未发现源文关键元素完全丢失。")
        return
    for row in findings:
        marker = {"must": "BLOCK", "warn": "WARN", "info": "INFO"}.get(row.get("severity"), "INFO")
        print(f"- {marker} [{row.get('code')}] {row.get('message')}")
        ev = row.get("evidence") or {}
        if ev.get("sentence"):
            print(f"  source: {ev['sentence']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d source-to-adaptation coverage audit")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check-fabrication", action="store_true",
                    help="额外跑反向防瞎编：改编稿出现源文没有且无有账改写引入的专名/设定 → warn（report-first）。")
    ns = ap.parse_args(argv)
    result = audit(ns.root.rstrip("/"), ep_label(ns.episode), check_fabrication=ns.check_fabrication)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    has_must = any(f["severity"] == "must" for f in result.get("findings") or [])
    has_warn = any(f["severity"] == "warn" for f in result.get("findings") or [])
    if ns.strict and (has_must or has_warn):
        return 1
    return 1 if has_must else 0


if __name__ == "__main__":
    raise SystemExit(main())
