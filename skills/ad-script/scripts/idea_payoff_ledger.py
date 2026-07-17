#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创意承诺 → 分镜兑现 账本（ad 线编剧轴 P1·参照同仓成熟生产线的 setup→payoff 模式重实现，不跨线 import）。

为什么存在：
    `创意/concept.json` 里的 big idea / 一句话主张 / 卖点 / KV 方向 / 故事线是**创意期的承诺**，
    但全线**无人回头核对分镜兑现了没有**。实证：`ad-craft/producer_pack.build_pack` 只把
    concept 的 Big Idea 段落**抄进 pack**（`_extract_section(concept, "Big Idea")`）就完事，
    此后 storyboard 怎么写都没有任何机制比对；`finalize_storyboard.py` 只做时长算术 + 强制项
    （logo/slogan/legal/CTA）落镜；`score_pre.py` 只算钩子/露出/CTA 的确定性 prescore。
    没有一处问过：**「主张有没有哪一镜承载？登记的卖点落镜了吗？分镜里那个卖点 concept 登记过吗？」**

治什么根因：
    「big idea/key message 定完就没人管」——策略与执行脱节的两个方向都无人兜底：
      · 承诺没兑现（unrealized）：主张/卖点/KV/故事线段落在分镜里消失了；
      · 兑现没承诺（off-ledger）：分镜冒出 concept 未登记的卖点 = **临时加戏 / 创意漂移**，
        这是广告最贵的一类返工（卖点变了，KV、法务 claim 依据、投放素材全得跟着改）。

诚实边界（照抄源模式的纪律）：
    - **不自动宣判**。文本匹配不可靠，所以分两层置信度：
        ① **显式绑定优先**：shot 有结构化 `usp_ids` / `claim_ids` / `section` → 直接对账（高置信）；
        ② 无结构化字段时才退到 char n-gram 弱匹配 → **只产 `candidate`**，只提示不拦，交编剧确认。
    - **增量合并，绝不覆盖已填的 `payoff_shots`**：编剧手填的对账结果是真值，机器只补未登记的。
      手工标成 `done` 的条目也不被机器降级。
    - 严重度分层按**判据是否确定性**给，不按「我觉得多严重」：
        · `usp_offledger` = block：shot 自己声明了一个 concept 没登记的 usp id，纯结构比对，无启发式；
        · `usp_unrealized` / `storyline_section_missing`：**仅当分镜确实在用结构化绑定**（说明该项目
          有绑定纪律）才 block；否则退 warn（此时结论建立在弱文本匹配上，不该硬拦）；
        · `key_message_unrealized` / `kv_unrealized` 永远 warn——「这一镜算不算承载了主张」没有
          确定性判据，机器无权硬拦。
    - 默认 exit 0（本检是「审」不是「门」）；`--strict` 且 block>0 才 exit 1。
    - 缺 `创意/concept.json` → `available=false` + warn，**不崩**（承诺都没落档，谈不上对账兑现）。
    - 广告不拆集：粒度是 shot，无集/话参数。

用法：
    cd skills/ad-script/scripts
    python3 idea_payoff_ledger.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

VERSION = 1
KIND = "ad_idea_payoff_audit"
LEDGER_KIND = "ad_idea_payoff_ledger"
LEDGER_REL = os.path.join("创意", "idea_payoff_ledger.json")
REPORT_REL = os.path.join("生产数据", "ad_idea_payoff_audit.json")

# 弱匹配阈值（内部启发式·env 可标定·confidence=low）。
# 用**包含率**（承诺的 n-gram 有多少落在镜头文本里）而非 Jaccard：镜头文本远长于一句卖点，
# 对称的 Jaccard 会被长度差压到极低，永远匹配不上。
WEAK_CONTAIN_MIN = float(os.environ.get("AD_PAYOFF_CONTAIN_MIN", "0.6"))
WEAK_MIN_CHARS = int(os.environ.get("AD_PAYOFF_MIN_CHARS", "4"))
NGRAM = 2

PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
_PLACEHOLDER_RE = re.compile(r"待补|待填|TODO|TBD", re.IGNORECASE)
PENDING_TOKENS = {"", "未记录", "待补", "待填", "待填写", "tbd", "todo", "未填", "未定", "n/a"}


# ── 纯函数（无 IO·可测） ──────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str) -> Dict[str, str]:
    """ad gate 消费 `msg` 键（见 ad-craft/gate.py:52）。"""
    return {"severity": severity, "code": code, "msg": msg}


def is_pending(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        raw = value.strip()
        return raw.lower() in PENDING_TOKENS or bool(_PLACEHOLDER_RE.search(raw))
    if isinstance(value, (list, tuple, dict)):
        return not value
    return False


def shingles(text: str, n: int = NGRAM) -> Set[str]:
    """去噪后的 char n-gram 集合。纯函数·可测。"""
    clean = _NOISE_RE.sub("", str(text or ""))
    if len(clean) < n:
        return {clean} if clean else set()
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def containment(needle: str, haystack: str) -> float:
    """needle 的 n-gram 有多大比例出现在 haystack 里（0..1）。纯函数·可测。

    非对称是刻意的：问的是「这句卖点被这一镜提到了吗」，不是「两段文本像不像」。"""
    a = shingles(needle)
    if not a:
        return 0.0
    b = shingles(haystack)
    if not b:
        return 0.0
    return len(a & b) / len(a)


def shot_id(shot: Mapping[str, Any], pos: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{pos:02d}")


def shot_texts(shot: Mapping[str, Any]) -> str:
    """一镜里参与弱匹配的**可读文本**（递归抽字符串字段）。纯函数·可测。

    与 finalize_storyboard._collect_storyboard_text 同思路（本线自包含·复制不 import）：广告分镜
    没有稳定的字段名约定（frame/desc/vo/字幕/end_card 各项目不一），逐字段列举必漏。"""
    parts: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for v in node.values():
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            if node.strip():
                parts.append(node)

    walk(shot)
    return "\n".join(parts)


def _id_set(shot: Mapping[str, Any], key: str) -> Set[str]:
    raw = shot.get(key) or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        return set()
    return {str(v).strip() for v in raw if str(v).strip()}


def uses_structured_binding(shots: Sequence[Mapping[str, Any]]) -> bool:
    """分镜是否**在用**结构化绑定（任一镜有非空 usp_ids/claim_ids）。纯函数·可测。

    这是严重度分层的开关：项目有绑定纪律 → 缺绑定是确定性漏洞（block）；
    项目根本没在用 → 结论只能靠弱文本匹配，无权硬拦（warn）。"""
    return any(_id_set(s, "usp_ids") or _id_set(s, "claim_ids") for s in shots)


def uses_sections(shots: Sequence[Mapping[str, Any]]) -> bool:
    return any(str(s.get("section") or "").strip() for s in shots)


def build_setups(pack: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """concept.json → 账本条目骨架（payoff_shots 留空交对账填）。纯函数·可测。

    kind: key_message | usp | kv | storyline_beat。"""
    out: List[Dict[str, Any]] = []
    km = pack.get("key_message")
    if not is_pending(km):
        out.append({"id": "KM_01", "kind": "key_message", "desc": str(km).strip(),
                    "payoff_shots": [], "status": "open"})
    for row in pack.get("usps") or []:
        if isinstance(row, Mapping):
            uid = str(row.get("id") or "").strip()
            text = str(row.get("text") or "").strip()
        else:
            uid, text = "", str(row or "").strip()
        if is_pending(text):
            continue
        uid = uid or f"USP_{sum(1 for x in out if x['kind'] == 'usp') + 1:02d}"
        entry = {"id": uid, "kind": "usp", "desc": text, "payoff_shots": [], "status": "open"}
        if isinstance(row, Mapping) and str(row.get("claim_id") or "").strip():
            entry["claim_id"] = str(row["claim_id"]).strip()
        out.append(entry)
    kv = pack.get("kv_direction")
    if not is_pending(kv):
        out.append({"id": "KV_01", "kind": "kv", "desc": str(kv).strip(),
                    "payoff_shots": [], "status": "open"})
    for i, beat in enumerate(pack.get("storyline") or [], 1):
        if not isinstance(beat, Mapping):
            continue
        section = str(beat.get("section") or "").strip()
        if is_pending(section):
            continue
        out.append({"id": f"BEAT_{i:02d}", "kind": "storyline_beat", "desc": section,
                    "section": section, "detail": str(beat.get("desc") or "").strip(),
                    "payoff_shots": [], "status": "open"})
    return out


def match_setup(entry: Mapping[str, Any], shots: Sequence[Mapping[str, Any]],
                vo_text: str = "") -> Dict[str, Any]:
    """一条承诺 → 兑现镜头。返回 {"explicit": [...], "candidate": [...]}。纯函数·可测。

    显式（高置信·直接对账）：
      · usp：shot.usp_ids 含本条 id，或 shot.claim_ids 含本条 claim_id；
      · storyline_beat：shot.section == 本段 section；
      · key_message：shot.delivers_key_message 为真；
      · kv：shot.is_kv / shot.kv 为真。
    弱匹配（低置信·只产 candidate）：承诺文本的 n-gram 包含率 ≥ 阈值。VO 文本并入镜头文本一起看
    （广告 VO 常是卖点的实际载体，只看 storyboard 字段会漏）。"""
    explicit: List[str] = []
    candidate: List[str] = []
    kind = entry.get("kind")
    eid = str(entry.get("id") or "")
    claim_id = str(entry.get("claim_id") or "")
    section = str(entry.get("section") or "")
    desc = str(entry.get("desc") or "")

    for pos, shot in enumerate(shots, 1):
        sid = shot_id(shot, pos)
        hit = False
        if kind == "usp":
            hit = eid in _id_set(shot, "usp_ids") or (bool(claim_id) and claim_id in _id_set(shot, "claim_ids"))
        elif kind == "storyline_beat":
            hit = bool(section) and str(shot.get("section") or "").strip() == section
        elif kind == "key_message":
            hit = bool(shot.get("delivers_key_message"))
        elif kind == "kv":
            hit = bool(shot.get("is_kv") or shot.get("kv"))
        if hit:
            explicit.append(sid)
            continue
        if len(_NOISE_RE.sub("", desc)) < WEAK_MIN_CHARS:
            continue
        haystack = shot_texts(shot)
        if kind in ("key_message", "usp"):
            haystack = haystack + "\n" + vo_text
        if containment(desc, haystack) >= WEAK_CONTAIN_MIN:
            candidate.append(sid)
    return {"explicit": explicit, "candidate": candidate}


def merge_ledger(existing: Sequence[Mapping[str, Any]],
                 fresh: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """已有账本 + 新扫描结果 → 按 id 增量合并。纯函数·可测。

    纪律（照抄源模式）：**绝不覆盖已填的 payoff_shots**，也不把人手标的 status 降级。
    机器只做两件事：给**空的** payoff_shots 填机检结果；补登记 concept 新增、账本还没有的条目。
    人删掉的字段不复活、人填的内容不动——账本是编剧的，不是脚本的。"""
    by_id: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in existing:
        if not isinstance(row, Mapping):
            continue
        rid = str(row.get("id") or "")
        if not rid:
            continue
        by_id[rid] = dict(row)
        order.append(rid)
    for row in fresh:
        rid = str(row.get("id") or "")
        if not rid:
            continue
        cur = by_id.get(rid)
        if cur is None:
            by_id[rid] = dict(row)
            order.append(rid)
            continue
        # desc 跟随 concept 更新（承诺改了账本要知道），但兑现结果绝不动。
        cur["kind"] = row.get("kind", cur.get("kind"))
        cur["desc"] = row.get("desc", cur.get("desc"))
        if row.get("section"):
            cur["section"] = row["section"]
        if row.get("claim_id"):
            cur["claim_id"] = row["claim_id"]
        if not cur.get("payoff_shots"):
            cur["payoff_shots"] = list(row.get("payoff_shots") or [])
            cur["status"] = row.get("status", cur.get("status", "open"))
    return [by_id[i] for i in order]


def scan(pack: Mapping[str, Any], shots: Sequence[Mapping[str, Any]],
         vo_text: str = "") -> List[Dict[str, Any]]:
    """concept + storyboard → 本次机检得到的账本条目（未与旧账本合并）。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    for entry in build_setups(pack):
        m = match_setup(entry, shots, vo_text)
        row = dict(entry)
        if m["explicit"]:
            row["payoff_shots"] = m["explicit"]
            row["status"] = "done"
            row["confidence"] = "explicit"
        elif m["candidate"]:
            row["payoff_shots"] = []          # candidate 不算兑现，交编剧确认后填
            row["candidate_shots"] = m["candidate"]
            row["status"] = "candidate"
            row["confidence"] = "weak_text_match"
        else:
            row["status"] = "open"
        out.append(row)
    return out


def offledger_usp_ids(pack: Mapping[str, Any], shots: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """分镜声明了、但 concept 没登记的 usp id = 临时加戏/创意漂移。纯函数·可测。

    纯结构比对，零启发式 → 唯一有资格进 block 的判据。"""
    known = set()
    for row in pack.get("usps") or []:
        if isinstance(row, Mapping) and str(row.get("id") or "").strip():
            known.add(str(row["id"]).strip())
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for pos, shot in enumerate(shots, 1):
        for uid in sorted(_id_set(shot, "usp_ids")):
            if uid in known or uid in seen:
                continue
            seen.add(uid)
            out.append({"usp_id": uid, "shot": shot_id(shot, pos)})
    return out


def audit(ledger: Sequence[Mapping[str, Any]], pack: Mapping[str, Any],
          shots: Sequence[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """账本 → findings。纯函数·可测。严重度分层理由见模块 docstring。"""
    findings: List[Dict[str, str]] = []
    structured = uses_structured_binding(shots)
    sectioned = uses_sections(shots)
    if not shots:
        findings.append(finding("warn", "storyboard_unavailable",
                                "缺 脚本/storyboard.json 或其 shots[] 为空——没有分镜可对账"
                                "（insufficient_data，不代表创意已兑现）。"))
        return findings

    for row in ledger:
        kind = str(row.get("kind") or "")
        rid = str(row.get("id") or "?")
        desc = str(row.get("desc") or "")[:40]
        status = str(row.get("status") or "open")
        done = bool(row.get("payoff_shots")) or status == "done"
        if done:
            continue
        if status == "candidate":
            cands = "、".join(str(s) for s in (row.get("candidate_shots") or [])[:4])
            findings.append(finding("info", "payoff_candidate_unconfirmed",
                                    f"{rid}『{desc}』疑似由镜头 {cands} 承载（弱文本匹配·低置信）——"
                                    "机器无权宣判；确认后把镜号填进账本 payoff_shots 并标 status=done，"
                                    "或给该镜加结构化 usp_ids/section 让下次直接对账。"))
            continue
        if kind == "key_message":
            findings.append(finding("warn", "key_message_unrealized",
                                    f"一句话主张『{desc}』在分镜里找不到任何承载镜——观众看完记不住主张，"
                                    "策略与执行脱节。给承载它的镜标 delivers_key_message=true，"
                                    "或改分镜让主张真的落地（它该能落到 KV 和片尾）。"))
        elif kind == "usp":
            sev = "block" if structured else "warn"
            extra = ("（本项目分镜已在用 usp_ids 绑定，缺绑定即确定性漏洞）" if structured
                     else "（本项目分镜未用 usp_ids 绑定，此结论基于弱文本匹配，仅供复核）")
            findings.append(finding(sev, "usp_unrealized",
                                    f"登记的卖点 {rid}『{desc}』没有任何镜头承载{extra}——"
                                    "要么补镜兑现，要么从 concept.json 的 usps[] 删掉这条空头承诺。"))
        elif kind == "kv":
            findings.append(finding("warn", "kv_unrealized",
                                    f"KV 方向『{desc}』没有对应的主视觉镜——KV 是 ad-image 定妆库的锚，"
                                    "落不到镜就等于没定 KV。给主视觉镜标 is_kv=true 或补一镜。"))
        elif kind == "storyline_beat":
            sev = "block" if sectioned else "warn"
            extra = ("（本项目分镜已在用 section 字段，缺该段即确定性漏洞）" if sectioned
                     else "（本项目分镜未标 section，此结论基于弱文本匹配，仅供复核）")
            findings.append(finding(sev, "storyline_section_missing",
                                    f"故事线段落「{desc}」在分镜里没有对应镜头{extra}——"
                                    "创意期定的段落级结构（钩子/痛点/卖点/CTA）被拆镜头时丢了。"))

    for row in offledger_usp_ids(pack, shots):
        findings.append(finding("block", "usp_offledger",
                                f"镜头 {row['shot']} 声明了卖点 {row['usp_id']}，但 concept.json 的 usps[] "
                                "没有登记它——分镜临时加戏 = 创意漂移；卖点变了，KV/法务 claim 依据/"
                                "投放素材都得跟着改。回 concept 补登记（并声明 supports_key_message），"
                                "或把这一镜改回已登记的卖点。"))
    return findings


# ── IO（best-effort·缺则空） ──────────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_pack(root: Path) -> Optional[Dict[str, Any]]:
    data = load_json(root / "创意" / "concept.json")
    return data if isinstance(data, dict) else None


def load_shots(root: Path) -> List[Dict[str, Any]]:
    sb = load_json(root / "脚本" / "storyboard.json", {}) or {}
    if not isinstance(sb, Mapping):
        return []
    rows = sb.get("shots") or sb.get("clips") or []
    return [s for s in rows if isinstance(s, Mapping)]


def load_vo_text(root: Path) -> str:
    try:
        return (root / "脚本" / "voiceover.txt").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def load_existing_ledger(root: Path) -> List[Dict[str, Any]]:
    data = load_json(root / LEDGER_REL, {}) or {}
    rows = data.get("entries") if isinstance(data, Mapping) else None
    return [r for r in (rows or []) if isinstance(r, Mapping)]


def build_ledger_payload(entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {"kind": LEDGER_KIND, "schema_version": VERSION, "generated_at": now_iso(),
            "note": "payoff_shots / status 是编剧真值——机器只补空条目，绝不覆盖已填内容。",
            "entries": [dict(e) for e in entries]}


def build(root: Path) -> Dict[str, Any]:
    """契约形状（findings 用 `msg` 键，ad gate 可直接消费）：

        {"schema_version":1,"kind":"ad_idea_payoff_audit","available":bool,
         "summary":{"block","warn","info"},"findings":[{"severity","code","msg"}]}

    另附 `ledger`（合并后的账本，供 --write 落盘）。"""
    root = Path(root)
    pack = load_pack(root)
    shots = load_shots(root)
    available = pack is not None
    findings: List[Dict[str, str]] = []

    if not available:
        findings.append(finding("warn", "concept_pack_missing",
                                "缺 创意/concept.json——创意承诺没有机器真值，无法对账分镜是否兑现了 "
                                "big idea/主张/卖点/KV/故事线。先跑 ad-concept/scripts/concept_pack.py "
                                "把创意结构化落档（insufficient_data）。"))
        ledger = build_ledger_payload(load_existing_ledger(root))
    else:
        fresh = scan(pack, shots, load_vo_text(root))
        entries = merge_ledger(load_existing_ledger(root), fresh)
        ledger = build_ledger_payload(entries)
        findings.extend(audit(entries, pack, shots))

    entries = ledger["entries"]
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "thresholds": {"weak_contain_min": WEAK_CONTAIN_MIN, "weak_min_chars": WEAK_MIN_CHARS,
                       "ngram": NGRAM, "provenance": PROVENANCE,
                       "note": "显式绑定=高置信直接对账；弱匹配只产 candidate，永不自动宣判兑现。"},
        "summary": {
            "entries": len(entries),
            "done": sum(1 for e in entries if e.get("payoff_shots")),
            "candidates": sum(1 for e in entries if e.get("status") == "candidate"),
            "open": sum(1 for e in entries if e.get("status") == "open" and not e.get("payoff_shots")),
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
        "ledger": ledger,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 创意承诺→分镜兑现 账本机检", ""]
    if not report.get("available"):
        lines += ["- ⚠️ 未找到 `创意/concept.json`（available=false·降级为建议，不阻断）", ""]
    lines += [f"- 承诺 {s.get('entries')} 条 · 已兑现 {s.get('done')} · 待确认候选 {s.get('candidates')}"
              f" · 未兑现 {s.get('open')}",
              f"- block {s.get('block')} · warn {s.get('warn')} · info {s.get('info')}", ""]
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 创意承诺均有镜头承载，且分镜未出现未登记卖点")
    ledger = (report.get("ledger") or {}).get("entries") or []
    if ledger:
        lines += ["", "## 账本", "", "| id | 类型 | 承诺 | 兑现镜 | 状态 |", "|---|---|---|---|---|"]
        for e in ledger:
            shots = "、".join(str(x) for x in (e.get("payoff_shots") or [])) or "—"
            lines.append(f"| {e.get('id')} | {e.get('kind')} | {str(e.get('desc') or '')[:28]} | "
                         f"{shots} | {e.get('status')} |")
    return "\n".join(lines) + "\n"


def write_ledger(root: Path, ledger: Mapping[str, Any]) -> None:
    path = root / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="作品根")
    ap.add_argument("--write", action="store_true",
                    help=f"落盘 {LEDGER_REL} + {REPORT_REL}（不覆盖已填的 payoff_shots）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true", help="block>0 时 exit 1（默认 exit 0：本检是审不是门）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build(root)
    if ns.write:
        write_ledger(root, report["ledger"])
        write_report(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["block"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
