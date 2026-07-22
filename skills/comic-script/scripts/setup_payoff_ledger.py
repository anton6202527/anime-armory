#!/usr/bin/env python3
"""伏笔种下→兑现跨话账本（2026-07 标准审计·参照同仓成熟生产线 SP1 模式的漫画重实现，不跨线 import）。

为什么在 comic-script：`development_pack` 的 `foreshadowing_ledger` 是**立项期一次性**的静态清单，
拆完话、逐话写分格脚本后，没有任何机制回头核对「这个坑第几话兑现了、有没有被忘掉、兑现有没有早于种下」。
条漫是长线连载，实证空档正是「后续话次断供」——伏笔埋了不收，读者追更动力流失。SP1 是另一条正交轴：
`source_semantics` 管语言归一化、`visual_contract/scene_anchor` 管视觉状态跨格继承、`chapter_beat_audit`
管单话节拍，而**叙事坑跨话**（planted→payoff）此前无人兜底。业界共识（2026 实搜）：foreshadowing 是
setup + payoff 两个同等重要的半场，unpaid setup 是「未兑现的承诺」，长线追更第一劝退。

诚实边界（与源模式同纪律）：
- **不自动判定哪句是伏笔**（文本自动识别伏笔不可靠）——只按**显式悬念/钩子标记**捞 `open` 坑（进 gate），
  另按**挖坑句式弱信号**捞 `candidate`（只提示、不拦流水线，交编剧确认升 open 或删）。
- 已有账本**不覆盖已填的 payoff_chapter**：默认只增量补未登记候选。
- 立项期 `development_pack.adaptation_strategy.foreshadowing_ledger` 里 reviewer 手填的坑作为**种子**并入，
  两层账本合一，不再各记各的。

默认 report-only（与 chapter_beat_audit/redundancy_audit 同：gate 里以 advisory 并入，不阻断付费出图）。
`--strict` 时本话检出的显式伏笔若未登记/未填兑现话/兑现早于种下则 exit 1，供想开硬闸的团队用。

用法：
  cd skills/comic-script/scripts
  python3 setup_payoff_ledger.py <作品根> 第N话 [--write] [--json] [--strict]
  python3 setup_payoff_ledger.py <作品根> --all [--write]      # 扫全部已拆话、刷新账本
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

VERSION = 1
KIND = "comic_setup_payoff_audit"
LEDGER_KIND = "comic_setup_payoff_ledger"
LEDGER_REL = os.path.join("设定库", "setup_payoff_ledger.json")

# 显式悬念标记（只捞 open 坑·进 gate）。与 development_pack 语义同口径（独立线·复制不 import）。
# 刻意不含「钩子/话尾/cliffhanger」这类**结构术语**——它们高频出现在 art_notes 制作指令里（"底部留黑场给下话钩子"），
# 会把画面指导误当叙事坑。只认语义强的埋坑词，且只扫故事面文本（台词/旁白/音效），不扫 art_notes/description。
FORESHADOW_MARKERS = (
    "伏笔", "悬念", "埋下", "留下疑问", "未解", "成谜", "卖关子", "悬而未决",
    "意味深长", "别有深意", "暗藏", "似乎另有", "不为人知", "🪝",
)
# 无显式标记、但句式本身就是「挖坑」的弱信号——交编剧确认后才算坑（status=candidate·不进 gate）。
AUTO_FORESHADOW_RE = re.compile(
    r"(到底是谁|究竟是谁|会是谁|是谁.{0,4}[？?]|为什么.{0,12}[？?]|为何.{0,12}[？?]|"
    r"不知道.{0,10}(是|为|会)|不明白|想不通|另有.{0,4}隐情|另有.{0,4}图谋|身世|来历|真实身份|"
    r"神秘的?(信物|令牌|玉佩|盒子|信|纸条|声音|人影)|古怪的|蹊跷|反常|不对劲|总觉得.{0,8}不|"
    r"那个.{0,6}(到底|究竟)|留作后用|日后必有|日后再|来日方长)")
PLACEHOLDER_RE = re.compile(r"待补|待填|TODO|TBD|<[^>]*>|__待", re.IGNORECASE)


# ── 纯函数（无依赖·可测） ─────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    """'第3话' / 'ch3' / '3' → '第3话'；解析不出原样返回。"""
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("话"):
        return raw
    m = re.search(r"\d+", raw)
    return f"第{int(m.group(0))}话" if m else raw


def chapter_num(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def is_placeholder(line: str) -> bool:
    return bool(PLACEHOLDER_RE.search(str(line or "")))


def clean_desc(text: str, limit: int = 80) -> str:
    line = str(text or "").strip()
    line = re.sub(r"^[#>\-*\s]+", "", line).strip()
    line = re.sub(r"\s*[⚡💥🪝]\s*$", "", line).strip()
    return line[:limit]


def panel_text_lines(panel: Mapping[str, Any]) -> List[str]:
    """一格里参与伏笔检测的**故事面**文本：台词（text_target 优先）+ 旁白 + 音效。纯函数·可测。

    刻意不含 art_notes/description——那是给出图/收尾的制作指令（含「留黑场给下话钩子」等craft术语），
    不是读者读到的叙事内容，扫它只会把画面指导误当伏笔。"""
    out: List[str] = []
    for item in panel.get("dialogue") or []:
        if isinstance(item, Mapping):
            text = str(item.get("text_target") or item.get("text") or "").strip()
        else:
            text = str(item or "").strip()
        if text:
            out.append(text)
    for key in ("narration_target", "narration", "sfx"):
        text = str(panel.get(key) or "").strip()
        if text:
            out.append(text)
    return out


def detect_setups(panels: Sequence[Mapping[str, Any]], chapter: str) -> List[Dict[str, Any]]:
    """从一话的所有格里捞**显式**候选伏笔（命中标记的文本行）。payoff_chapter 留空交编剧填。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for panel in panels:
        pid = str(panel.get("panel_id") or "?")
        for line in panel_text_lines(panel):
            if is_placeholder(line) or not any(m in line for m in FORESHADOW_MARKERS):
                continue
            desc = clean_desc(line)
            if not desc or desc in seen:
                continue
            seen.add(desc)
            out.append({
                "id": f"{chapter}-伏笔{len(out) + 1}",
                "setup_chapter": chapter,
                "payoff_chapter": "",     # 交编剧填：哪一话兑现这个坑
                "desc": desc,
                "panel": pid,
                "status": "open",          # open=待规划兑现；ongoing=长线进行中；done=已兑现
            })
    return out


def detect_auto_candidates(panels: Sequence[Mapping[str, Any]], chapter: str,
                           limit: int = 8) -> List[Dict[str, Any]]:
    """无显式标记、但句式像挖坑的弱信号候选（status=candidate·交编剧确认/删除）。纯函数·可测。

    与 detect_setups 互补：那个认显式标记（→open 坑·进 gate），这个认句式（→candidate·只提示不拦）。
    只命中身世/凶手/神秘信物/未解之谜类强句式，去重限量，避免误把每句疑问都当伏笔。"""
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for panel in panels:
        pid = str(panel.get("panel_id") or "?")
        for line in panel_text_lines(panel):
            for clause in re.split(r"[\n。！？!?]", line):
                clause = clause.strip()
                if not clause or is_placeholder(clause) or len(clause) < 4:
                    continue
                if not AUTO_FORESHADOW_RE.search(clause):
                    continue
                if any(m in clause for m in FORESHADOW_MARKERS):
                    continue  # 已被显式标记捞走
                desc = clause[:40]
                if desc in seen:
                    continue
                seen.add(desc)
                out.append({
                    "id": f"{chapter}-候选{len(out) + 1}",
                    "setup_chapter": chapter,
                    "payoff_chapter": "",
                    "desc": desc,
                    "panel": pid,
                    "status": "candidate",   # 待编剧确认：升为 open 或删
                    "auto": True,
                })
                if len(out) >= limit:
                    return out
    return out


def seed_from_development_pack(strategy: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """把立项期 development_pack.adaptation_strategy.foreshadowing_ledger 的手填坑作为种子。纯函数·可测。

    两层账本合一：立项手填的长线大坑 + 逐话机检捞出的坑，共用一份 setup_payoff_ledger.json。"""
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(strategy.get("foreshadowing_ledger") or [], 1):
        if not isinstance(item, Mapping):
            continue
        desc = clean_desc(str(item.get("setup") or item.get("desc") or ""))
        if not desc or is_placeholder(desc):
            continue
        planted = normalize_chapter(str(item.get("planted_chapter") or item.get("setup_chapter") or ""))
        payoff = str(item.get("payoff_chapter") or "")
        payoff = normalize_chapter(payoff) if payoff and not is_placeholder(payoff) else ""
        status = str(item.get("status") or "open")
        if status == "planted":
            status = "open"
        out.append({
            "id": str(item.get("setup_id") or f"DEV-伏笔{i}"),
            "setup_chapter": planted,
            "payoff_chapter": payoff,
            "desc": desc,
            "panel": "",
            "status": status,
            "from_development_pack": True,
        })
    return out


def merge_candidates(existing: Sequence[Mapping[str, Any]],
                     candidates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """已有账本 + 新候选 → 按 desc 去重合并（绝不覆盖已填的 payoff_chapter/status）。纯函数·可测。"""
    merged: List[Dict[str, Any]] = [dict(p) for p in existing if isinstance(p, Mapping)]
    have = {str(p.get("desc") or p.get("id")) for p in merged}
    for c in candidates:
        key = str(c.get("desc") or c.get("id"))
        if key not in have:
            merged.append(dict(c))
            have.add(key)
    return merged


def build_ledger(pairs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {"kind": LEDGER_KIND, "version": VERSION, "generated_at": now_iso(),
            "pairs": [dict(p) for p in pairs]}


def _is_open_unfilled(p: Mapping[str, Any]) -> bool:
    """这条坑是否「显式伏笔但兑现话没填」（candidate 弱信号、ongoing/done 不计入 gate）。"""
    if p.get("status") in ("ongoing", "done", "candidate", "进行中"):
        return False
    return not str(p.get("payoff_chapter") or "").strip()


def audit_chapter(chapter: str, detected: Sequence[Mapping[str, Any]],
                  ledger_pairs: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """本话 SP1 检查（纯函数·可测）。severity: must/warn/info。

    ① setup_unlogged：本话检出显式伏笔但账本未登记。
    ② payoff_unfilled：本话种下的坑在账本里但没填兑现话。
    ③ payoff_overdue：账本里某坑的兑现话 <= 本话但仍 open（该收没收=断供/忘坑）。
    ④ payoff_before_setup：兑现话早于种下话（账本填错）。
    ⑤ payoff_due_here：某坑兑现话==本话（info 提醒：本话必须把它收掉）。"""
    findings: List[Dict[str, Any]] = []
    by_desc = {str(p.get("desc") or p.get("id")): p for p in ledger_pairs if isinstance(p, Mapping)}
    cur = chapter_num(chapter)
    unfilled_flagged: set[str] = set()
    for d in detected:
        match = by_desc.get(d["desc"])
        if match is None:
            findings.append({"severity": "must", "code": "setup_unlogged", "desc": d["desc"],
                             "message": f"本话检出伏笔/悬念钩「{d['desc']}」但 setup_payoff_ledger 未登记——"
                                        "跑 setup_payoff_ledger.py --write 建账并填兑现话。"})
        elif _is_open_unfilled(match):
            findings.append({"severity": "must", "code": "payoff_unfilled", "desc": d["desc"],
                             "message": f"伏笔「{d['desc']}」在账本里但没填兑现话（payoff_chapter 空）——"
                                        "补 payoff_chapter（哪话兑现）或标 status=ongoing。"})
            unfilled_flagged.add(d["desc"])
    for p in ledger_pairs:
        if not isinstance(p, Mapping):
            continue
        desc = str(p.get("desc") or p.get("id"))
        setup_n = chapter_num(str(p.get("setup_chapter") or ""))
        payoff_raw = str(p.get("payoff_chapter") or "").strip()
        payoff_n = chapter_num(payoff_raw)
        status = str(p.get("status") or "open")
        # H1 carry-forward: an open setup that never got a planned payoff chapter
        # must stay visible in EVERY chapter at/after its planting chapter — the
        # detected-loop `payoff_unfilled` above only fires in the planting chapter
        # (or never, for development_pack-seeded foreshadows that are never
        # re-detected from panels), so it would otherwise go silent forever.
        if _is_open_unfilled(p) and desc not in unfilled_flagged and (
            cur is None or setup_n is None or cur >= setup_n
        ):
            findings.append({"severity": "warn", "code": "payoff_unplanned_open", "desc": desc,
                             "message": f"伏笔「{desc}」始终没填兑现话（payoff_chapter 空）且未 done/ongoing——"
                                        "长线埋了不收的风险；补 payoff_chapter（计划哪话兑现）或标 status=ongoing/done。"})
        if payoff_n is not None and setup_n is not None and payoff_n < setup_n:
            findings.append({"severity": "warn", "code": "payoff_before_setup", "desc": desc,
                             "message": f"伏笔「{desc}」兑现话 {payoff_raw} 早于种下话 第{setup_n}话——账本填反了，核对。"})
        if cur is not None and payoff_n is not None and status not in ("done", "ongoing"):
            if payoff_n == cur:
                findings.append({"severity": "info", "code": "payoff_due_here", "desc": desc,
                                 "message": f"伏笔「{desc}」计划本话（{chapter}）兑现——确认本话已把它收掉并标 status=done。"})
            elif payoff_n < cur:
                findings.append({"severity": "warn", "code": "payoff_overdue", "desc": desc,
                                 "message": f"伏笔「{desc}」兑现话 {payoff_raw} 已早于本话 {chapter} 但仍 open——"
                                            "坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。"})
    return findings


# ── IO（best-effort·缺则空） ──────────────────────────────────────────────────

def load_panels(root: Path, chapter: str) -> List[Dict[str, Any]]:
    path = root / "脚本" / chapter / "panel_script.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    panels = data.get("panels") if isinstance(data, Mapping) else None
    return [p for p in (panels or []) if isinstance(p, Mapping)]


def load_existing_ledger(root: Path) -> List[Dict[str, Any]]:
    path = root / LEDGER_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    pairs = data.get("pairs") or data.get("setups") if isinstance(data, Mapping) else None
    return [p for p in (pairs or []) if isinstance(p, Mapping)]


def load_development_strategy(root: Path) -> Dict[str, Any]:
    path = root / "开发包" / "adaptation_strategy.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def discover_chapters(root: Path) -> List[str]:
    base = root / "脚本"
    if not base.is_dir():
        return []
    chapters = [d.name for d in base.glob("第*话") if d.is_dir()]
    return sorted(chapters, key=lambda c: chapter_num(c) or 0)


def refresh_ledger(root: Path, chapters: Sequence[str]) -> Dict[str, Any]:
    """扫指定话次 + development_pack 种子，增量刷新账本（不覆盖已填）。返回 ledger dict。"""
    candidates: List[Dict[str, Any]] = seed_from_development_pack(load_development_strategy(root))
    for chapter in chapters:
        panels = load_panels(root, chapter)
        candidates.extend(detect_setups(panels, chapter))
        candidates.extend(detect_auto_candidates(panels, chapter))
    merged = merge_candidates(load_existing_ledger(root), candidates)
    return build_ledger(merged)


def build_report(root: Path, chapter: str) -> Dict[str, Any]:
    """单话 SP1 报告：刷新账本（内存态）→ 审本话。写盘在 main 里做。"""
    ledger = refresh_ledger(root, discover_chapters(root) or [chapter])
    detected = detect_setups(load_panels(root, chapter), chapter)
    findings = audit_chapter(chapter, detected, ledger["pairs"])
    return {
        "kind": KIND, "version": VERSION, "chapter": chapter, "generated_at": now_iso(),
        "provenance": "SP1·显式标记进 gate/弱信号只提示·development_pack 种子并入·2026-07",
        "summary": {
            "detected_setups": len(detected),
            "ledger_pairs": len(ledger["pairs"]),
            "must": sum(1 for f in findings if f["severity"] == "must"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
        "ledger": ledger,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [f"# 伏笔兑现账本机检 · {report.get('chapter')}", "",
             f"- 本话显式伏笔 {s.get('detected_setups')} · 账本共 {s.get('ledger_pairs')} 坑 · "
             f"must {s.get('must')} · warn {s.get('warn')} · info {s.get('info')}", ""]
    icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 本话伏笔账健康（显式坑均已登记且兑现话在轨）")
    return "\n".join(lines) + "\n"


def write_ledger(root: Path, ledger: Mapping[str, Any]) -> None:
    path = root / LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter", nargs="?", default="", help="第N话；配合 --all 时可省略")
    ap.add_argument("--all", action="store_true", help="扫全部已拆话、刷新账本（不做单话 gate）")
    ap.add_argument("--write", action="store_true", help="落盘账本 + 单话报告（不覆盖已填 payoff_chapter）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="本话 must 级（未登记/未填/兑现早于种下）exit 1")
    ns = ap.parse_args(argv)
    root = Path(ns.root)

    if ns.all or not ns.chapter:
        ledger = refresh_ledger(root, discover_chapters(root))
        if ns.write:
            write_ledger(root, ledger)
        pairs = ledger["pairs"]
        n_open = sum(1 for p in pairs if _is_open_unfilled(p))
        n_cand = sum(1 for p in pairs if p.get("status") == "candidate")
        payload = {"kind": LEDGER_KIND, "pairs": pairs,
                   "summary": {"total": len(pairs), "unfilled_open": n_open, "candidates": n_cand}}
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"# 伏笔账本刷新 · 共 {len(pairs)} 坑（待填兑现话 {n_open} · 弱信号候选 {n_cand}）"
                  + ("（已写盘）" if ns.write else "（未写盘，加 --write）"))
            for p in pairs:
                flag = ("🔍弱信号·确认是否伏笔" if p.get("status") == "candidate"
                        else "⚠待填兑现话" if _is_open_unfilled(p) else "")
                print(f"  [{p.get('setup_chapter')}→{p.get('payoff_chapter') or '?'}] {p.get('desc')} {flag}")
        return 0

    chapter = normalize_chapter(ns.chapter)
    report = build_report(root, chapter)
    if ns.write:
        write_ledger(root, report["ledger"])
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comic_setup_payoff_audit_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"comic_setup_payoff_audit_{chapter}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    if ns.strict and report["summary"]["must"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
