#!/usr/bin/env python3
"""追更再入前情机检（reader re-entry orientation·advisory）——参照同仓成熟视频线
midstart_context / antecedent_audit / narrative_state_audit 的漫画重实现，合三为一。

为什么存在：条漫是**长线周更连载**，读者隔一周回来看第 N 话。现有机检里——
`continuity_audit` 只查**声明态**链（exit_state↔entry_state 的字段是否吻合），
`development_pack._breadth_issues` 只查**源覆盖广度**，`chapter_beat_audit` 只查本话
首格有没有 opening_hook 这个「功能位」——**没有任何脚本查「读者进入第 N 话时接不接得上」**：
开场有没有前情锚（旁白回顾 / 常驻角色再登场 / 承接上一话退出场景），中段会不会突然冒出一个
从没在留存话次里交代过的角色让读者断片「这谁啊」。视频线用 midstart_context（前情包）+
antecedent_audit（删集致前因缺失）+ narrative_state_audit（跨集叙事态）三件治这条轴；漫画线
数据是**结构化的**（character_bindings.character_id / characters[] / entry_state），一个脚本即可
低误报覆盖，省掉视频线那套自由文本 NER。

两查（都只对 N≥2 的连载话有意义；standalone/oneshot/四格自足话跳过 A，B 亦跳过）：

  ① 前情锚不足（reentry_context_thin·warn）：开场窗口（前 K 格）里，以下**全都没有** →
     追更读者可能接不上：(a) 旁白含回顾标记（话说/却说/上一话/之前/原来/自从/回到…）；
     (b) 有一个上一话出现过的常驻角色在开场再登场；(c) 开场某格 story_function 属回顾/建立类；
     (d) 开场 scene_anchor_id 承接上一话最后的场景锚（读者落回离开时的地方）。
  ② 未交代实体（unintroduced_entity·warn）：本话引用的某角色（结构化 character_id / characters），
     既不在 identity 登记表、又没在任何**留存前话**出现过、也不在本话合同 entry_state 里，
     且它在本话的**首次出现格**落在开场窗口之外、story_function 又不是登场/介绍类 →
     读者不知这是谁（其引入疑似漏写或被跨话遗忘）。开场窗口内或登场功能格首现 = 正常新角，不报。

诚实边界（写死）：看不到「读者脑内记忆」，只能从结构化在场 + 开场文本信号推断，命中=warn 交人判；
**本检是「审」不是「门」**——脆弱启发式不得硬阻断付费，gate 里以 advisory 并入，`--strict` 仅供人手排查。

用法（与本线其它 advisory 机检同签名）：
  python3 reentry_context_audit.py <作品根> 第N话 [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

VERSION = 1
KIND = "comic_reentry_context_audit"

# 开场窗口格数：前几格算「再入前情区」。env 可调，默认 3。
OPENING_WINDOW = int(os.environ.get("COMIC_REENTRY_OPENING_WINDOW", "3"))

# 旁白回顾标记：条漫最常用的前情装置（说书体/连载体）。
RECAP_MARKERS = (
    "话说", "却说", "且说", "上一话", "上回", "前情", "之前", "先前", "原来", "自从", "自打",
    "再说", "回到", "话分两头", "上文", "承接", "接上", "此前",
)
_RECAP_RE = re.compile("|".join(RECAP_MARKERS))

# 回顾/建立类 story_function（开场用来重新锚定读者）。
RECAP_FUNCS = {
    "recap", "previously", "cold_open", "opening_hook", "hook", "establishing_hook",
    "establishing", "reestablish", "reintroduction", "flashback",
}
# 登场/介绍类 story_function（新角色在此首现属正常引入，不算断片）。
INTRO_FUNCS = {
    "introduction", "character_intro", "reveal", "reintroduction",
    "establishing", "establishing_hook", "cold_open", "opening_hook",
}
# 自足话形态：不吃前情，跳过再入检查。
STANDALONE_TYPES = {"standalone", "oneshot", "one_shot", "gag", "四格", "single"}
STANDALONE_FORMATS = {"four_panel", "yonkoma", "gag", "oneshot", "one_shot"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    value = str(value or "").strip()
    return value if value.startswith("第") else f"第{value}话"


def chapter_num(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_panels(root: Path, chapter: str) -> List[Dict[str, Any]]:
    data = load_json(root / "脚本" / chapter / "panel_script.json", {})
    panels = data.get("panels") if isinstance(data, Mapping) else None
    return [p for p in panels if isinstance(p, Mapping)] if isinstance(panels, list) else []


def discover_chapters(root: Path) -> List[str]:
    base = root / "脚本"
    if not base.is_dir():
        return []
    chapters = [p.parent.name for p in base.glob("第*话/panel_script.json")]
    return sorted(chapters, key=lambda c: chapter_num(c) or 0)


def panel_char_ids(panel: Mapping[str, Any]) -> List[str]:
    """一格里出场的结构化角色 id（character_bindings 优先，兼容 characters[]）。纯函数·可测。"""
    ids: List[str] = []
    seen: Set[str] = set()

    def add(cid: str) -> None:
        cid = str(cid or "").strip()
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)

    for b in panel.get("character_bindings") or []:
        if isinstance(b, Mapping):
            add(b.get("character_id"))
    for c in panel.get("characters") or []:
        if isinstance(c, str):
            add(c)
        elif isinstance(c, Mapping):
            add(c.get("character_id") or c.get("id") or c.get("name"))
    return ids


def registry_known_ids(root: Path) -> Set[str]:
    """identity 登记表里已登记的角色 id 与显示名。纯函数语义（仅读一个文件）。"""
    data = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    known: Set[str] = set()
    assets = data.get("assets") if isinstance(data, Mapping) else None
    items: Sequence[Any]
    if isinstance(assets, Mapping):
        items = list(assets.values())
    elif isinstance(assets, list):
        items = assets
    else:
        items = []
    for asset in items:
        if not isinstance(asset, Mapping):
            continue
        if str(asset.get("type") or "").strip() and str(asset.get("type")).strip() != "character":
            continue
        for key in ("id", "asset_id", "display_name"):
            val = str(asset.get(key) or "").strip()
            if val:
                known.add(val)
    return known


def contract_entities(contract: Optional[Mapping[str, Any]]) -> Set[str]:
    """本话合同里声明为已知的实体：entry_state 里登记的实体 + continuity_delta 的 entity_id。"""
    known: Set[str] = set()
    if not isinstance(contract, Mapping):
        return known
    entry = contract.get("entry_state")
    if isinstance(entry, Mapping):
        entities = entry.get("entities")
        if isinstance(entities, Mapping):
            known.update(str(k) for k in entities.keys())
    for tr in contract.get("continuity_delta") or []:
        if isinstance(tr, Mapping) and str(tr.get("entity_id") or "").strip():
            known.add(str(tr.get("entity_id")).strip())
    return known


def blueprint_contract(root: Path, chapter: str) -> Optional[Mapping[str, Any]]:
    bp = load_json(root / "脚本" / "split_blueprint.json", {})
    if not isinstance(bp, Mapping):
        return None
    for entry in bp.get("chapters") or []:
        if isinstance(entry, Mapping) and str(entry.get("chapter")) == chapter:
            return entry
    return None


def is_standalone(contract: Optional[Mapping[str, Any]]) -> bool:
    if not isinstance(contract, Mapping):
        return False
    ctype = str(contract.get("chapter_type") or "").strip().lower()
    fmt = str(contract.get("format_profile") or "").strip().lower()
    return ctype in STANDALONE_TYPES or fmt in STANDALONE_FORMATS


def last_scene_anchor(panels: Sequence[Mapping[str, Any]]) -> str:
    for panel in reversed(panels):
        anchor = str(panel.get("scene_anchor_id") or "").strip()
        if anchor:
            return anchor
    return ""


def finding(code: str, panel: str, message: str, *, severity: str = "warn", **extra: Any) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "severity": severity,
        "confidence": "heuristic",
        "code": code,
        "panel": panel,
        "message": message,
    }
    item.update(extra)
    return item


def check_reentry_context(
    chapter: str,
    panels: Sequence[Mapping[str, Any]],
    prev_chapter_ids: Set[str],
    prev_last_anchor: str,
) -> List[Dict[str, Any]]:
    """① 前情锚是否够。纯函数·可测。"""
    window = list(panels[:OPENING_WINDOW])
    if not window:
        return []
    has_recap_narration = any(
        _RECAP_RE.search(str(p.get("narration_target") or p.get("narration") or ""))
        for p in window
    )
    has_returning_char = any(
        cid in prev_chapter_ids for p in window for cid in panel_char_ids(p)
    )
    has_recap_func = any(
        str(p.get("story_function") or "").strip().lower() in RECAP_FUNCS for p in window
    )
    anchor_continues = bool(prev_last_anchor) and any(
        str(p.get("scene_anchor_id") or "").strip() == prev_last_anchor for p in window
    )
    if has_recap_narration or has_returning_char or has_recap_func or anchor_continues:
        return []
    return [finding(
        "reentry_context_thin",
        str(window[0].get("panel_id") or "?"),
        f"{chapter} 开场前 {len(window)} 格没有任何前情锚（无旁白回顾、无上一话常驻角色再登场、"
        f"无回顾/建立类功能格、也不承接上一话最后场景 {prev_last_anchor or '（未知）'}）——"
        f"追更读者隔周回来可能接不上。补一格旁白回顾、让常驻角色带出前情，或让开场承接上话退出场景。",
        signals={
            "recap_narration": has_recap_narration,
            "returning_char": has_returning_char,
            "recap_function": has_recap_func,
            "anchor_continues": anchor_continues,
        },
    )]


def check_unintroduced_entities(
    chapter: str,
    panels: Sequence[Mapping[str, Any]],
    known_ids: Set[str],
) -> List[Dict[str, Any]]:
    """② 中段冒出的未交代实体。纯函数·可测。"""
    findings: List[Dict[str, Any]] = []
    first_seen: Dict[str, int] = {}
    first_panel: Dict[str, str] = {}
    first_func: Dict[str, str] = {}
    for index, panel in enumerate(panels):
        for cid in panel_char_ids(panel):
            if cid not in first_seen:
                first_seen[cid] = index
                first_panel[cid] = str(panel.get("panel_id") or "?")
                first_func[cid] = str(panel.get("story_function") or "").strip().lower()
    for cid, index in sorted(first_seen.items(), key=lambda kv: kv[1]):
        if cid in known_ids:
            continue
        if index < OPENING_WINDOW:
            continue  # 开场窗口内首现 = 有机会正常引入，不报
        if first_func.get(cid) in INTRO_FUNCS:
            continue  # 明确登场功能格 = 正常引入
        findings.append(finding(
            "unintroduced_entity",
            first_panel[cid],
            f"{chapter} 中段（第 {index + 1} 格 {first_panel[cid]}）首次出现角色 {cid}，"
            f"但它不在 identity 登记表、留存前话、也不在本话合同 entry_state——读者不知这是谁。"
            f"确认是漏写引入还是跨话遗忘：补一格登场介绍，或在 registry / entry_state 登记。",
            entity=cid,
        ))
    return findings


def audit(root: Path, chapter: str) -> Dict[str, Any]:
    chapter = normalize_chapter(chapter)
    cur_num = chapter_num(chapter)
    panels = load_panels(root, chapter)
    contract = blueprint_contract(root, chapter)
    findings: List[Dict[str, Any]] = []

    all_chapters = discover_chapters(root)
    prior_chapters = [c for c in all_chapters if (chapter_num(c) or 0) < (cur_num or 0)]

    # 留存前话的角色在场集 + 上一话最后场景锚
    prior_ids: Set[str] = set()
    prev_last_anchor = ""
    for c in prior_chapters:
        c_panels = load_panels(root, c)
        for p in c_panels:
            prior_ids.update(panel_char_ids(p))
    if prior_chapters:
        prev_last_anchor = last_scene_anchor(load_panels(root, prior_chapters[-1]))
    # 上一话（紧邻）出现过的常驻角色——用于「再登场」判定
    prev_chapter_ids: Set[str] = set()
    if prior_chapters:
        for p in load_panels(root, prior_chapters[-1]):
            prev_chapter_ids.update(panel_char_ids(p))

    known_ids = registry_known_ids(root) | prior_ids | contract_entities(contract)

    standalone = is_standalone(contract)
    first_chapter = (cur_num or 1) <= 1 or not prior_chapters
    skipped_reason = ""
    if first_chapter:
        skipped_reason = "首话/无前话——无再入前情问题"
    elif standalone:
        skipped_reason = "自足话（standalone/oneshot/四格）——不吃前情"
    else:
        findings.extend(check_reentry_context(chapter, panels, prev_chapter_ids, prev_last_anchor))
        findings.extend(check_unintroduced_entities(chapter, panels, known_ids))

    chapter_entities = sorted({cid for p in panels for cid in panel_char_ids(p)})
    summary = {
        "panels": len(panels),
        "prior_chapters": len(prior_chapters),
        "known_entities": len(known_ids),
        "chapter_entities": len(chapter_entities),
        "must": 0,  # advisory·审不是门
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "skipped": bool(skipped_reason),
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "chapter": chapter,
        "prior_chapter": prior_chapters[-1] if prior_chapters else "",
        "skipped_reason": skipped_reason,
        "thresholds": {"opening_window": OPENING_WINDOW},
        "summary": summary,
        "findings": findings,
    }


def render_md(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        f"# 漫画追更再入前情机检 · {report.get('chapter')}",
        "",
        f"- 格 {s.get('panels')} · 前话 {s.get('prior_chapters')} · 已知实体 {s.get('known_entities')}"
        f" · 本话实体 {s.get('chapter_entities')} · warn {s.get('warn')}",
    ]
    if report.get("skipped_reason"):
        lines.append(f"- 跳过：{report.get('skipped_reason')}")
    lines += ["", "## Findings", ""]
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 开场前情锚齐、无中段未交代实体。")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    chapter = str(report.get("chapter") or "第1话")
    base = root / "生产数据"
    base.mkdir(parents=True, exist_ok=True)
    (base / f"comic_reentry_context_audit_{chapter}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (base / f"comic_reentry_context_audit_{chapter}.md").write_text(render_md(report), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="人手排查用：有 warn 即 exit 1；正式 gate 从不用它硬拦（advisory·审不是门）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = audit(root, ns.chapter)
    if ns.write:
        write_report(root, report)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report), end="")
    return 1 if ns.strict and report["summary"]["warn"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
