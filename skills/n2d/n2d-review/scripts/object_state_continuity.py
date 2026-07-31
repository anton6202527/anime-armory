#!/usr/bin/env python3
"""物件状态一致性机检（OST·未声明的道具状态互斥翻转）。

补一个真实空白：道具的**已声明**状态演进（满→空、完好→破碎…）已由 state_continuity 的
`prop_alerts_from_ledger` 机检（提前泄露 / 旧态残留），经 状态百科(P1) 进闸。但**未声明**的状态
翻转没人盯——同一道具在 Clip A 写「满」、Clip B 写「空」，中间却没有任何 ledger timeline 转换：
要么是写手漏登记，要么是 AI 出图/分镜把状态画飞了。前者该补 timeline、后者是穿帮。

机制（纯文本/结构·零重依赖·永不降级跳过）：
  道具来源 = visual_state_ledger.props ∪ asset_registry 里 type∈{道具/prop/法宝/weapon} 的资产。
  互斥状态词典 STATE_PAIRS：每对是一组同义词 vs 反义同义词（满↔空、完好↔破碎、点燃↔熄灭…）。
  对每条道具、每对互斥状态：若它在某镜文本里被断言为 A 态、在另一镜被断言为 B 态，且两镜之间
  **没有**覆盖该状态对的已声明 ledger 转换 → 🟡warn（未声明的道具状态翻转，登记 timeline 或修穿帮）。

诚实边界：文本匹配「道具名 + 状态词同现于一镜」较粗（不做指代消解），故一律 warn 不 block，与
prop_alerts_from_ledger（声明态）互补。已声明转换覆盖的翻转一律豁免（不与 P1 重复报）。无道具登记
/无 storyboard → available=False 优雅跳过，不假报。

用法：python3 object_state_continuity.py <作品根> 第N集 [--json]
纯 stdlib；纯函数（状态词命中/互斥冲突判定/声明转换覆盖）带 pytest 覆盖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import state_continuity as stc  # 复用 prop 来源 / shot_num / 已声明转换 timeline

KIND = "n2d_object_state_consistency"
VERSION = 1
DIM = "物件状态(OST)"

# 互斥状态词典：(A标签, [A同义词], B标签, [B同义词])。只放**道具/物件**层面真正互斥、且
# 文本里会明写的状态对；角色服装/伤情归 costume/state_continuity，不在此列（避免重复误伤）。
STATE_PAIRS: Tuple[Tuple[str, Tuple[str, ...], str, Tuple[str, ...]], ...] = (
    ("满", ("满", "盛满", "斟满", "倒满", "装满", "全满"), "空", ("空", "空了", "见底", "喝光", "倒空", "饮尽", "空空")),
    ("完好", ("完好", "崭新", "完整", "无损", "锃亮"), "破损", ("破损", "破碎", "碎裂", "残破", "裂开", "断裂", "摔碎", "破了",
                                                          "烧毁", "焚毁", "炸毁", "粉碎", "化为灰烬", "灰飞烟灭")),
    ("点燃", ("点燃", "燃着", "亮着", "通明", "明亮", "烛火摇曳"), "熄灭", ("熄灭", "灭了", "熄了", "暗下", "黯淡", "吹灭", "掐灭")),
    ("开启", ("打开", "开启", "敞开", "拉开"), "关闭", ("关闭", "合上", "紧闭", "关上", "扣上")),
    ("干燥", ("干燥", "干的", "干爽"), "湿润", ("湿透", "潮湿", "湿润", "淋湿", "浸湿")),
    ("全新", ("全新", "崭新"), "陈旧", ("陈旧", "破旧", "磨损", "斑驳", "锈蚀", "残旧")),
    ("封缄", ("封缄", "未拆", "完封", "火漆完好"), "拆封", ("拆封", "拆开", "已拆", "撕开封口")),
)

# 物理不可逆终态（世界模型/物理一致性·P2-10）：到达后无法自发回到对侧——玻璃碎了不会自己复原、
# 烧毁不会自燃复生。这类对里，**终态先出现、对侧（完好）后出现**且后镜无修复/闪回解释 = 物理穿帮
# （比泛义未声明翻转更硬的信号）。只标真正不可逆的：破损（含烧毁/粉碎）。满↔空/点燃↔熄灭/开↔关 等
# 可自发逆转（再斟满/重新点燃/再关上），不算物理不可逆。
IRREVERSIBLE_TERMINAL_LABELS = {"破损"}
# 合法复原/非违规解释：显式修复/重铸/换新，或闪回/倒叙（后镜其实是更早时间）→ 豁免物理违规。
# 只放显式的复原**动作**/时间倒错标记；不放「完好如初/崭新如初」这类**描述终态**的词——后者只是把
# 可疑结果说得好听，并不解释如何复原，放进来会反而掩盖真穿帮。
RESTORE_OR_FLASHBACK_MARKERS = (
    "修复", "修补", "重铸", "重塑", "复原", "修好", "换新", "换了新", "新的", "另一", "另一个", "替换",
    "重新", "焕新", "翻新", "法术", "术法", "神通", "灵力修复",
    "回忆", "闪回", "倒叙", "回到", "昔日", "当年", "曾经", "先前", "之前的", "flashback", "repair", "replace",
)


def has_restore_marker(text: str) -> bool:
    t = str(text or "")
    return any(m in t for m in RESTORE_OR_FLASHBACK_MARKERS)


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def prop_tokens(pid: str, name: Any) -> Set[str]:
    """道具的机检搜索词：name ∪ pid 去 PROP_ 前缀，≥2 字（单字易误命中，剔除）。纯函数·可测。"""
    toks: Set[str] = set()
    for raw in (str(name or ""), str(pid or "")):
        t = raw.strip()
        if t.upper().startswith("PROP_"):
            t = t[5:]
        for part in re.split(r"[_\-/、,，\s]+", t):
            if len(part) >= 2 and not part.isdigit():
                toks.add(part)
    return toks


def text_mentions_prop(text: str, tokens: Set[str]) -> bool:
    t = str(text or "")
    return any(tok in t for tok in tokens)


def state_hit(text: str, synonyms: Sequence[str]) -> Optional[str]:
    """文本命中的首个状态同义词（用于留痕具体措辞）；无命中→None。纯函数·可测。"""
    t = str(text or "")
    for w in synonyms:
        if w in t:
            return w
    return None


def declared_pair_transition(timeline: Sequence[Mapping[str, Any]],
                             a_syn: Sequence[str], b_syn: Sequence[str]) -> bool:
    """ledger timeline 是否已声明覆盖该互斥状态对的转换（任一 from/to 落在 A/B 同义词内）。
    已声明的翻转由 prop_alerts_from_ledger 负责，OST 豁免不重复报。纯函数·可测。"""
    a = set(a_syn)
    b = set(b_syn)
    for tr in timeline or []:
        if not isinstance(tr, Mapping):
            continue
        frm = str(tr.get("from") or "")
        to = str(tr.get("to") or "")
        froms = {w for w in (a | b) if w in frm}
        tos = {w for w in (a | b) if w in to}
        # 一端落 A、另一端落 B（任意方向）= 已声明这对互斥状态的演进
        if (froms & a and tos & b) or (froms & b and tos & a):
            return True
    return False


def conflicts_for_prop(clip_texts: Sequence[Tuple[Any, str]],
                       tokens: Set[str],
                       timeline: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """单条道具的未声明状态冲突：在不同镜被断言为互斥两态、且无已声明转换覆盖 → 冲突行。

    clip_texts: [(clip_id, 该镜文本), ...]（已按出现顺序）。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    for a_label, a_syn, b_label, b_syn in STATE_PAIRS:
        if declared_pair_transition(timeline, a_syn, b_syn):
            continue  # 已声明的演进，交 prop_alerts_from_ledger，不重复
        a_hits: List[Tuple[int, Any, str, str]] = []  # (idx, cid, word, text)
        b_hits: List[Tuple[int, Any, str, str]] = []
        for idx, (cid, text) in enumerate(clip_texts):
            if not text_mentions_prop(text, tokens):
                continue
            ah = state_hit(text, a_syn)
            bh = state_hit(text, b_syn)
            if ah and not bh:
                a_hits.append((idx, cid, ah, text))
            elif bh and not ah:
                b_hits.append((idx, cid, bh, text))
            # 同镜同时出现两态（如"把空杯斟满"）= 镜内动作，非跨镜穿帮，跳过
        if not (a_hits and b_hits):
            continue
        row = {
            "pair": (a_label, b_label),
            "a_clip": a_hits[0][1], "a_word": a_hits[0][2],
            "b_clip": b_hits[0][1], "b_word": b_hits[0][2],
        }
        # 物理不可逆违规（P2-10）：终态(破损)先出现、完好态后出现（物件自发复原），且后镜无修复/闪回解释。
        if b_label in IRREVERSIBLE_TERMINAL_LABELS:
            first_terminal_idx = min(h[0] for h in b_hits)
            # 终态之后出现的「完好」断言里，找第一条没有修复/闪回标记的 → 物理穿帮
            reverted = next(((idx, cid, w) for (idx, cid, w, text) in a_hits
                             if idx > first_terminal_idx and not has_restore_marker(text)), None)
            if reverted:
                first_terminal = next(h for h in b_hits if h[0] == first_terminal_idx)
                row["physics_violation"] = True
                row["terminal_clip"] = first_terminal[1]
                row["terminal_word"] = first_terminal[2]
                row["reverted_clip"] = reverted[1]
                row["reverted_word"] = reverted[2]
        out.append(row)
    return out


# ── 装载 + 编排（best-effort I/O） ─────────────────────────────────────────────

def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


_PROP_TYPES = {"道具", "prop", "props", "法宝", "weapon", "兵器", "器物", "物件"}


def collect_props(root: str) -> Dict[str, Dict[str, Any]]:
    """道具来源：visual_state_ledger.props ∪ asset_registry 中 type∈道具类 的资产。
    返回 {pid: {name, timeline}}。timeline 仅 ledger props 带（asset 无→[]）。"""
    out: Dict[str, Dict[str, Any]] = {}
    ledger = _load_json(os.path.join(root, "出图", "共享", "visual_state_ledger.json")) or {}
    props = ledger.get("props") if isinstance(ledger.get("props"), dict) else {}
    for pid, p in props.items():
        if isinstance(p, dict):
            out[str(pid)] = {"name": p.get("name"), "timeline": p.get("timeline") or []}
    reg = _load_json(os.path.join(root, "出图", "共享", "asset_registry.json")) or {}
    for a in reg.get("assets") or []:
        if not isinstance(a, dict):
            continue
        if str(a.get("type") or "").strip().lower() in _PROP_TYPES:
            aid = str(a.get("id") or "")
            if aid and aid not in out:
                out[aid] = {"name": a.get("name"), "timeline": []}
    return out


def _clip_texts(root: str, ep: str) -> List[Tuple[Any, str]]:
    """每镜可搜索文本 = storyboard 镜文本 ⊕ 出图分镜 prompt 段（与 marks_consistency 同源）。"""
    sb = _load_json(os.path.join(root, "脚本", ep, "storyboard.json")) or {}
    clips = sb.get("clips") or sb.get("shots") or []
    md = ""
    try:
        with open(os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md"), encoding="utf-8") as f:
            md = f.read()
    except Exception:
        pass
    sections = _split_prompt(md)
    out: List[Tuple[Any, str]] = []
    for idx, clip in enumerate(clips):
        if not isinstance(clip, Mapping):
            continue
        cid = str(clip.get("id") or clip.get("label") or f"Clip{idx+1:02d}")
        parts = [str(clip.get("label") or ""), str(clip.get("scene") or "")]
        cont = clip.get("continuity") or {}
        if isinstance(cont, Mapping):
            parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or "")]
        for s in (clip.get("shots") or []):
            if isinstance(s, Mapping):
                parts += [str(s.get("desc") or ""), str(s.get("video_prompt") or "")]
        parts.append(_section_for(str(clip.get("id") or ""), idx, sections))
        out.append((cid, " ".join(parts)))
    return out


def _split_prompt(md_text: str) -> List[Tuple[Optional[str], str]]:
    if not md_text:
        return []
    blocks: List[Tuple[Optional[str], str]] = []
    for chunk in re.split(r"(?m)^##\s+Clip\b", md_text)[1:]:
        m = re.search(r"(EP\d+_CLIP\d+)", chunk)
        blocks.append((m.group(1) if m else None, chunk))
    return blocks


def _section_for(clip_id: str, idx: int, sections: Sequence[Tuple[Optional[str], str]]) -> str:
    cid = str(clip_id or "").strip()
    if cid:
        for sid, text in sections:
            if sid == cid:
                return text
    return sections[idx][1] if 0 <= idx < len(sections) else ""


def analyze(root: str, ep: str) -> Dict[str, Any]:
    props = collect_props(root)
    if not props:
        return {"available": False, "shots": [],
                "notes": ["无道具登记（visual_state_ledger.props / asset_registry 道具类资产均空）——物件状态机检跳过。"]}
    clip_texts = _clip_texts(root, ep)
    if not clip_texts:
        return {"available": False, "shots": [],
                "notes": [f"{ep} storyboard.json 缺失/无 clips——先跑 n2d-script 分镜设计再机检物件状态。"]}
    shots: List[Dict[str, Any]] = []
    for pid, p in props.items():
        tokens = prop_tokens(pid, p.get("name"))
        if not tokens:
            continue
        for c in conflicts_for_prop(clip_texts, tokens, p.get("timeline") or []):
            a_lbl, b_lbl = c["pair"]
            label = str(p.get("name") or pid)
            if c.get("physics_violation"):
                # 物理不可逆违规：终态先、完好后、无修复/闪回解释——世界模型一致性（碎了不会自己复原）。
                shots.append({
                    "shot": str(c["reverted_clip"]),
                    "verdict": "warn",  # 文本匹配较粗故仍 warn，但 code/physics_violation 标识更硬信号
                    "dimension": DIM,
                    "prop": label,
                    "code": "physics_irreversible_reversion",
                    "physics_violation": True,
                    "message": (f"道具『{label}』物理不可逆穿帮：{c['terminal_clip']} 已「{c['terminal_word']}」（{b_lbl}·不可逆终态），"
                                f"其后 {c['reverted_clip']} 又「{c['reverted_word']}」（{a_lbl}）却无修复/重铸/换新/闪回交代——"
                                f"碎/毁的物件不会自发复原。若是修复请在文本/ledger 写明，若是闪回标注倒叙，否则修穿帮。"),
                })
            else:
                shots.append({
                    "shot": str(c["b_clip"]),
                    "verdict": "warn",
                    "dimension": DIM,
                    "prop": label,
                    "message": (f"道具『{label}』状态前后矛盾：{c['a_clip']} 写「{c['a_word']}」（{a_lbl}），"
                                f"{c['b_clip']} 写「{c['b_word']}」（{b_lbl}），中间无已声明的状态转换——"
                                f"若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。"),
                })
    notes: List[str] = []
    if not shots:
        notes.append(f"已检 {len(props)} 件道具的未声明状态翻转，无矛盾。")
    return {"available": True, "shots": shots, "notes": notes}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="物件状态一致性机检（OST）")
    ap.add_argument("root")
    ap.add_argument("ep")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = analyze(args.root, args.ep)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not report.get("available"):
        print("· " + "；".join(report.get("notes", []) or ["跳过"]))
        return 0
    warns = [s for s in report["shots"] if s.get("verdict") == "warn"]
    print(f"# 物件状态一致性（OST）：🟡未声明状态翻转 {len(warns)}")
    for s in warns:
        print(f"🟡 {s.get('message')}")
    for n in report.get("notes", []):
        print(f"· {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
