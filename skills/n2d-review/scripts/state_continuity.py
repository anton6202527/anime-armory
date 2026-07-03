#!/usr/bin/env python3
"""n2d 动态百科 / 状态哨兵（P1）。

检查会随剧情变化的视觉状态是否按镜头单调继承：

- `storyboard.json.visual_contract.角色状态演进`：伤、泪、乱发、觉醒态等从某镜开始保持。
- `出图/共享/visual_state_ledger.json`：跨集持续的可变状态锁（n2d-image 写方）——**角色与道具状态同源**：
  道具 lifecycle 数据质量（自由文本未结构化 / current_state 落后）+ 结构化 timeline 的状态演进泄露都在此机检。
- `出图/第N集/prompt/01_分镜出图.md`：逐镜 prompt 是否漏写 / 提前泄露角色或道具状态。

这是 review 侧只读机检，不修改 ledger，也不注入 prompt。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import VISUAL_STATE_LEDGER_KIND, production_dir, shared_asset_path  # noqa: E402

import semantic_continuity as sem  # 复用文本抽词/Markdown 分块

KIND = "n2d_state_continuity_report"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def episode_num(text: str) -> Optional[int]:
    m = re.search(r"第\s*([0-9０-９]+)\s*集", str(text))
    if not m:
        m = re.search(r"([0-9０-９]+)", str(text))
    if not m:
        return None
    raw = m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    try:
        return int(raw)
    except ValueError:
        return None


def shot_num(text: Any) -> Optional[int]:
    # 真实 producer 用 Clip 编号（storyboard 角色状态演进 `自:"Clip14"`、出图块 `## Clip 14`）；
    # 旧/手写状态句也可能是 镜N/镜头N/shotN/片段N。Clip 优先匹配。
    s = str(text)
    m = (re.search(r"(?:Clip|片段)\s*[_-]?\s*([0-9０-９]+)", s, re.I)
         or re.search(r"镜(?:头)?\s*([0-9０-９]+)", s)
         or re.search(r"shot\s*([0-9]+)", s, re.I))
    if not m:
        return None
    raw = m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return int(raw)


def range_end_shot(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if re.search(r"(?:集尾|全集|后续|跨集|长期|持续|未解除|until\s+end)", text, re.I):
        return None
    return shot_num(text)


def is_single_shot_keep(value: Any) -> bool:
    return bool(re.search(r"(本镜|单镜|仅本镜|当前镜|只本镜|本\s*shot|single\s*shot)", str(value or ""), re.I))


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def image_prompt_path(root: str, ep: str) -> str:
    return os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")


def ledger_path(root: str) -> str:
    return shared_asset_path(root, "visual_state_ledger.json")


def state_terms(text: Any) -> List[str]:
    terms = sem.salient_terms(text, limit=16)
    # 状态句经常写成“Clip3 起左颊新伤”，补几个更短的稳定片段。
    extra: List[str] = []
    for t in terms:
        extra.extend(re.findall(r"[\u4e00-\u9fff]{2,6}", t))
    out: List[str] = []
    seen = set()
    for t in terms + extra:
        key = sem.normalize_text(t)
        if key and key not in seen and len(key) >= 2:
            seen.add(key)
            out.append(t)
    return out[:12]


def state_leak_terms(text: Any) -> List[str]:
    """Terms strong enough to prove a state leaked outside its interval.

    Short words like "疲惫" or "压迫" are useful for missing-state hints inside
    the active interval, but too broad for BLOCK-level premature leakage.
    """
    raw_terms = sem.salient_terms(text, limit=12)
    out: List[str] = []
    seen = set()
    for term in raw_terms:
        key = sem.normalize_text(term)
        if not key or key in seen:
            continue
        if len(key) >= 4 or re.search(r"(伤|血|痕|水痕|湿|发光|金瞳|披衣|布袋|灵水|灵米|微光|变身|觉醒)", key):
            seen.add(key)
            out.append(term)
    return out or state_terms(text)[:2]


def states_from_storyboard(sb: Dict[str, Any]) -> List[Dict[str, Any]]:
    vc = sb.get("visual_contract") if isinstance(sb.get("visual_contract"), dict) else {}
    data = vc.get("角色状态演进") or vc.get("角色状态演进表") or {}
    states: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for char, entries in data.items():
            if isinstance(entries, str):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    status = entry.get("状态") or entry.get("status") or entry.get("description") or entry
                    start = shot_num(entry.get("自") or entry.get("from") or entry.get("start") or status) or 1
                    keep = entry.get("保持") or entry.get("until") or entry.get("keep") or "未声明"
                    end = range_end_shot(entry.get("至") or entry.get("until") or entry.get("end") or keep)
                    if end is None and is_single_shot_keep(keep):
                        end = start
                else:
                    status = str(entry)
                    start = shot_num(status) or 1
                    keep = "未声明"
                    end = range_end_shot(status)
                    if end is None and is_single_shot_keep(status):
                        end = start
                states.append({
                    "source": "storyboard.visual_contract",
                    "character": str(char),
                    "description": str(status),
                    "start_shot": start,
                    "end_shot": end,
                    "keep": str(keep),
                    "terms": state_terms(status),
                    "leak_terms": state_leak_terms(status),
                })
    return states


def states_from_visual_ledger(root: str, ep: str) -> List[Dict[str, Any]]:
    data = load_json(ledger_path(root))
    if not data:
        return []
    if data.get("kind") not in (None, VISUAL_STATE_LEDGER_KIND):
        return []
    current_ep = episode_num(ep) or 10**6
    states: List[Dict[str, Any]] = []
    chars = data.get("characters") if isinstance(data.get("characters"), dict) else {}
    for char, item in chars.items():
        mods = item.get("modifiers", []) if isinstance(item, dict) else []
        for mod in mods:
            if not isinstance(mod, dict) or not mod.get("active", True):
                continue
            added = episode_num(mod.get("added_in", "")) or 0
            if added > current_ep:
                continue
            removed = episode_num(mod.get("removed_in") or mod.get("ended_in") or mod.get("inactive_in") or "")
            if removed is not None and removed <= current_ep:
                continue
            desc = mod.get("description") or mod.get("mask_prompt") or mod.get("id")
            states.append({
                "source": "visual_state_ledger",
                "character": str(char),
                "description": str(desc),
                "start_shot": int(mod.get("start_shot") or 1),
                "end_shot": range_end_shot(mod.get("end_shot") or mod.get("until")),
                "keep": "跨集持续",
                "terms": state_terms(desc),
                "leak_terms": state_leak_terms(desc),
            })
    return states


# 会被剧情改变全身/服装外观的状态词典——区分「该锁的常态外观」与「剧情指定的外观演进」。
# COST(服装独立)/N1(服装配色) 据此对落在演进区间内的镜把 block 降 warn：根治「剧情指定换装/染血/
# 破损/变身被服装锁当漂移硬 block、强制回源头重出」的掣肘（服装锁此前盲比单一定妆、不读状态计划）。
COSTUME_AFFECTING_RE = re.compile(
    r"(换装|换衣|换上|穿上|披上|换回|脱(?:下|去|掉)?|外套|大衣|风衣|披风|斗篷|铠甲|盔甲|战甲|战袍|"
    r"礼服|婚纱|嫁衣|喜服|制服|长袍|戎装|便装|睡衣|泳装|戏服|盛装|"
    r"染血|沾血|血迹|浴血|血污|湿透|浸湿|淋湿|落水|溅泥|"
    r"破损|破碎|撕裂|褴褛|残破|脏污|弄脏|尘土|烧毁|焦黑|烧灼|衣衫不整|"
    r"变身|觉醒|化形|化身|易容|变装|乔装|改扮|蒙面|戴(?:上)?面具|摘(?:下)?面具|"
    r"受伤|负伤|绷带|包扎|伤痕|断臂|断肢)")
# 会被剧情改变「脸/五官」外观的状态词典——供 face 锁（G1）据此把落演进区间的镜 block 降 warn，
# 治「剧情指定易容/变身/毁容被脸锁当崩脸硬 block、强制回源头重出」。只含**脸面**改变（不含纯换装/染血），
# 与 COSTUME 各管各：换装区间不豁免脸锁、易容区间不豁免服装锁，互不越界。
FACE_AFFECTING_RE = re.compile(
    r"(易容|变装|乔装|改扮|蒙面|戴(?:上)?面具|摘(?:下)?面具|面具|换脸|易了容|"
    r"变身|化形|化身|觉醒|妖化|魔化|兽化|龙化|现出原形|现出真容|露出真容|揭下伪装|"
    r"毁容|破相|划伤脸|脸上.{0,4}(?:伤|疤|血)|面部.{0,4}(?:伤|疤|血)|刺青上脸|脸覆纹路|瞳色变|异瞳|"
    r"返老还童|老去|苍老|年迈|白发苍苍|变老|变年轻|易颜)")
# 会被剧情改变「发型/发色」的状态词典——供 hair 锁据此把落演进区间的镜 block 降 warn，
# 治「剧情指定黑化换发/染发/断发被发锁当漂移硬 block」。
HAIR_AFFECTING_RE = re.compile(
    r"(黑化|换发|改发|发型变|束发|散发|披发|挽发|盘发|结发|断发|剪发|削发|落发|"
    r"染发|白发|白头|华发|银发|霜染|戴(?:上)?发冠|摘(?:下)?发冠|束冠|戴冠|摘冠|加冠|"
    r"觉醒.{0,4}发|发色变|变身.{0,4}发)")
# 演进维度 → 词典：face/hair 锁各读各的区间；costume 默认（向后兼容旧无 kind 调用）。
_APPEARANCE_AFFECTING_RES = {
    "costume": COSTUME_AFFECTING_RE,
    "face": FACE_AFFECTING_RE,
    "hair": HAIR_AFFECTING_RE,
}


def appearance_change_intervals(root: str, ep: str, kind: str = "costume") -> Dict[str, List["tuple"]]:
    """剧情指定的「角色某维度外观会变」区间：{char: [(start_shot, end_shot|None, desc), ...]}。

    源同 P1 状态哨兵（storyboard 角色状态演进 + visual_state_ledger active modifiers）。kind 选维度词典：
    costume（默认·换装/染血/破损/变身）/ face（易容/变身/毁容）/ hair（黑化换发/染发/断发），各维度
    各管各——换装区间不豁免脸锁、易容区间不豁免服装锁。供对应锁把落区间内的镜 block 降 warn——surface
    而非硬阻断。纯读取·无副作用；缺 storyboard/ledger 或未知 kind → {}。"""
    affecting = _APPEARANCE_AFFECTING_RES.get(kind)
    if affecting is None:
        return {}
    sb = load_json(storyboard_path(root, ep)) or {}
    states = states_from_storyboard(sb) + states_from_visual_ledger(root, ep)
    intervals: Dict[str, List[tuple]] = {}
    for st in states:
        desc = str(st.get("description") or "")
        if not affecting.search(desc):
            continue
        char = str(st.get("character") or "").strip()
        if not char:
            continue
        start = int(st.get("start_shot") or 1)
        end = st.get("end_shot")
        end = int(end) if isinstance(end, int) else None
        intervals.setdefault(char, []).append((start, end, desc))
    # 与逐镜意图黑板的作者显式声明取并集：补回关键词漏检的有意改动（作者在 shot_intent.json 里 field-tag）。
    # 黑板缺/无对应声明时静默跳过，行为与未引入黑板时一致（非破坏性）。
    try:
        import n2d_intent  # _lib 已在 sys.path（见文件顶 COMMON）
        for char, rows in n2d_intent.explicit_evolution_for(root, ep, kind).items():
            intervals.setdefault(char, []).extend(rows)
    except Exception:
        pass
    return intervals


def appearance_change_at(intervals: Mapping[str, List["tuple"]], char: str,
                         shot_no: Optional[int]) -> Optional[str]:
    """该角色在该镜是否处于剧情指定的外观演进区间；是则返回演进描述，否则 None。
    shot_no 缺失（PNG 名解析不出 Clip 号）→ None：保守不豁免。纯函数·可测。"""
    if shot_no is None or not isinstance(intervals, Mapping):
        return None
    hit: Optional[str] = None
    for c, rows in intervals.items():
        if not (c == char or str(c).startswith(char) or char.startswith(str(c))):
            continue
        for start, end, desc in rows:
            if shot_no >= start and (end is None or shot_no <= end):
                hit = desc
    return hit


def downgrade_appearance_block(row: Dict[str, Any], intervals: Mapping[str, List["tuple"]],
                               char: str, shot_no: Optional[int],
                               expected_key: str = "costume_change_expected") -> Dict[str, Any]:
    """剧情指定外观演进区间内：标注 <expected_key>=演进描述，并把 block 降 warn（surface·不硬阻断）。
    warn/ok 不改判，仅 block 因「剧情就该变」降一档，留痕 abs_verdict。维度无关的通用版——costume/face/hair
    各传自己的 intervals（appearance_change_intervals(kind=…)）与 expected_key。原地改 row 并返回。纯函数·可测。"""
    desc = appearance_change_at(intervals, char, shot_no)
    if desc:
        row[expected_key] = desc
        if row.get("verdict") == "block":
            row.setdefault("abs_verdict", "block")
            row["verdict"] = "warn"
    return row


def downgrade_costume_block(row: Dict[str, Any], intervals: Mapping[str, List["tuple"]],
                            char: str, shot_no: Optional[int]) -> Dict[str, Any]:
    """COST/N1 服装锁专用包装（向后兼容）：等价 downgrade_appearance_block(..., 'costume_change_expected')。"""
    return downgrade_appearance_block(row, intervals, char, shot_no, expected_key="costume_change_expected")


def _prop_label(pid: str, p: Dict[str, Any]) -> str:
    name = p.get("name")
    return f"{name}（{pid}）" if name and str(name) != str(pid) else str(pid)


def _block_mentions_prop(block: Dict[str, Any], pid: str, name: Any) -> bool:
    body = block.get("body", "")
    return bool((pid and pid in body) or (name and str(name) in body))


def prop_alerts_from_ledger(root: str, ep: str, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """道具状态机检（消费与角色状态同一本 visual_state_ledger）。

    角色状态此前已机检；道具状态此前只建账不机检（声明但不验证）——这里补上：
    (a) registry 数据质量问题（自由文本未结构化 / current_state 落后于 transition / 引用未声明状态）；
    (b) 结构化 timeline 的状态演进泄露（转换镜前出现转换后状态 / 转换镜后仍写旧状态）。
    道具在 prompt 里靠名字/ID 提及（不像角色有 定妆_ 主参考锚），文本匹配较模糊，故一律 warn 不 block。
    """
    data = load_json(ledger_path(root))
    if not data or data.get("kind") not in (None, VISUAL_STATE_LEDGER_KIND):
        return []
    props = data.get("props") if isinstance(data.get("props"), dict) else {}
    alerts: List[Dict[str, Any]] = []
    for pid, p in props.items():
        if not isinstance(p, dict):
            continue
        label = _prop_label(str(pid), p)
        name = p.get("name")
        for issue in p.get("issues", []) or []:
            alerts.append({
                "verdict": "warn", "kind": "prop_lifecycle_issue",
                "source": "出图/共享/visual_state_ledger.json",
                "message": f"道具 {label} lifecycle：{issue}",
            })
        for tr in p.get("timeline") or []:
            if not isinstance(tr, dict):
                continue
            clip = tr.get("clip")
            if clip is None or not blocks:
                continue
            to_terms = state_terms(tr.get("to"))
            from_terms = state_terms(tr.get("from"))
            for blk in blocks:
                no = blk.get("shot")
                if no is None or not _block_mentions_prop(blk, str(pid), name):
                    continue
                body = blk.get("body", "")
                has_to = bool(to_terms) and has_any_term(body, to_terms)
                has_from = bool(from_terms) and has_any_term(body, from_terms)
                if no < clip and has_to:
                    alerts.append({
                        "verdict": "warn", "kind": "prop_state_premature_leak",
                        "source": f"出图/{ep}/prompt/01_分镜出图.md", "shot": no,
                        "message": f"道具 {label} 的 `{tr.get('to')}` 状态在转换镜（Clip{clip}）前的镜{no}提前出现。",
                    })
                elif no >= clip and has_from and not has_to:
                    alerts.append({
                        "verdict": "warn", "kind": "prop_state_regressed",
                        "source": f"出图/{ep}/prompt/01_分镜出图.md", "shot": no,
                        "message": f"道具 {label} 在 Clip{clip} 后应为 `{tr.get('to')}`，但镜{no} 仍写旧状态 `{tr.get('from')}`。",
                    })
    return alerts


def image_blocks(root: str, ep: str) -> List[Dict[str, Any]]:
    text = sem.read_text(image_prompt_path(root, ep))
    blocks: List[Dict[str, Any]] = []
    for blk in sem.split_md_blocks(text):
        no = shot_num(blk["heading"])
        if no is None:
            body_head = "\n".join(str(blk.get("body", "")).splitlines()[:3])
            no = shot_num(body_head)
        if no is None:
            continue
        body = blk["body"]
        chars = []
        for raw in re.findall(r"定妆_([^`\s，。、,）)]+)", body):
            name = raw[:-4] if raw.endswith(".png") else raw
            name = re.sub(r"_(侧|背|半身|全身|三视图|设定表|表情)$", "", name)
            if name not in chars:
                chars.append(name)
        blocks.append({"shot": no, "heading": blk["heading"], "body": body, "characters": chars})
    return blocks


def block_mentions_character(block: Dict[str, Any], char: str) -> bool:
    text = block.get("body", "")
    return char in text or any(str(c).startswith(char) or char.startswith(str(c)) for c in block.get("characters", []))


def has_any_term(text: str, terms: Sequence[str]) -> bool:
    nt = sem.normalize_text(text)
    return any(sem.normalize_text(t) in nt for t in terms if sem.normalize_text(t))


def state_pixel_sidecar_alerts(sidecar: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """state_pixel_<集>.json（SP1-V 像素契约）的 findings → 状态哨兵 alert 行（verdict=warn）。

    像素证据（OWLv2 等）对小标记/侧脸/遮挡噪声大，**一律 warn**（不硬 block，文本档仍是 BLOCK 权威），
    与本文本档互补：文本查「状态锁写没写进 prompt」，像素查「图里到底有没有该状态」——
    两个最危险的洞由像素兜：① 区间内像素缺该状态；② 区间起点前像素已提前泄露该状态（文本对、图错）。
    无 sidecar / 无 findings → []。纯函数·可测。"""
    if not isinstance(sidecar, Mapping):
        return []
    out: List[Dict[str, Any]] = []
    for f in sidecar.get("findings") or []:
        if not isinstance(f, Mapping):
            continue
        kind = str(f.get("kind") or "")
        shot = f.get("shot")
        state = f.get("state") or f.get("asset") or "状态"
        char = f.get("char")
        conf = f.get("confidence")
        ctx = f"（置信 {conf}）" if conf is not None else ""
        if kind == "state_pixel_premature_leak" or (f.get("expected") is False and f.get("present")):
            out.append({
                "verdict": "warn", "kind": "state_pixel_premature_leak", "character": char,
                "shot": shot, "state": state,
                "message": f"{shot}：状态『{state}』像素在该帧已检出，但该镜在状态起点之前——"
                           f"图可能提前泄露未到点的觉醒/伤/变身{ctx}（也可能误检/遮挡）。文本档若同时 block 以文本为准，人核对该帧。",
            })
        elif kind == "state_pixel_missing" or (f.get("expected") and not f.get("present")):
            out.append({
                "verdict": "warn", "kind": "state_pixel_missing", "character": char,
                "shot": shot, "state": state,
                "message": f"{shot}：区间内应保持状态『{state}』，像素在场检测未在该帧检出{ctx}——"
                           f"图里可能真没渲染该状态（也可能被遮挡/侧脸/标记过小漏检），人核对该帧。",
            })
    return out


def analyze(root: str, ep: str) -> Dict[str, Any]:
    root = root.rstrip("/")
    sb = load_json(storyboard_path(root, ep))
    notes: List[str] = []
    alerts: List[Dict[str, Any]] = []
    if not sb:
        return {
            "kind": KIND,
            "version": VERSION,
            "root": root,
            "episode": ep,
            "available": False,
            "states": [],
            "alerts": [],
            "verdicts": [],
            "notes": [f"缺 {storyboard_path(root, ep)}，状态哨兵跳过。"],
        }
    states = states_from_storyboard(sb) + states_from_visual_ledger(root, ep)
    if not states:
        notes.append("未发现角色状态演进或 visual_state_ledger active modifiers。")
    blocks = image_blocks(root, ep)
    if not blocks:
        notes.append("缺出图分镜 prompt，暂不验证状态继承。")

    for st in states:
        if not st.get("terms"):
            continue
        char = st["character"]
        start = int(st.get("start_shot") or 1)
        end = st.get("end_shot")
        end = int(end) if isinstance(end, int) else None
        for blk in blocks:
            no = blk.get("shot")
            if no is None or not block_mentions_character(blk, char):
                continue
            present = has_any_term(blk.get("body", ""), st["terms"])
            leak_present = has_any_term(blk.get("body", ""), st.get("leak_terms") or st["terms"])
            if no < start and leak_present:
                alerts.append({
                    "verdict": "block",
                    "kind": "premature_state_leak",
                    "character": char,
                    "shot": no,
                    "state": st["description"],
                    "message": f"{char} 的状态 `{st['description']}` 在镜{start}前提前泄露。",
                })
            elif end is not None and no > end:
                if leak_present:
                    alerts.append({
                        "verdict": "warn",
                        "kind": "state_leak_after_end",
                        "character": char,
                        "shot": no,
                        "state": st["description"],
                        "message": f"{char} 的状态 `{st['description']}` 声明至镜{end}，但镜{no} 仍保留。",
                    })
            elif no >= start and not present:
                alerts.append({
                    "verdict": "warn",
                    "kind": "state_missing_after_start",
                    "character": char,
                    "shot": no,
                    "state": st["description"],
                    "missing_terms": st["terms"],
                    "message": f"{char} 在镜{start}后应保持 `{st['description']}`，但镜{no} prompt 未见状态锁。",
                })

    alerts.extend(prop_alerts_from_ledger(root, ep, blocks))

    # 可选：状态像素 sidecar（state_pixel_contract 产；无则纯文本档，不假报）。像素证据一律 warn，
    # 文本档仍是 BLOCK 权威——兜「文本对、图里状态错」（提前泄露/区间内缺失）这两个像素层的洞。
    pixel_sidecar = load_json(os.path.join(root, "生产数据", f"state_pixel_{ep}.json"))
    pixel_alerts = state_pixel_sidecar_alerts(pixel_sidecar)
    if pixel_alerts:
        alerts.extend(pixel_alerts)
        notes.append(f"已合并状态像素 sidecar：{len(pixel_alerts)} 处（warn·人核对；像素噪声大不硬 block）。")

    verdicts = [a["verdict"] for a in alerts]
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": root,
        "episode": ep,
        "available": True,
        "states": states,
        "alerts": alerts,
        "verdicts": verdicts,
        "notes": notes,
        "summary": {
            "block": sum(1 for v in verdicts if v == "block"),
            "warn": sum(1 for v in verdicts if v == "warn"),
            "states": len(states),
        },
    }


def write_report(root: str, ep: str, data: Dict[str, Any]) -> str:
    safe_ep = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", ep)
    out = os.path.join(production_dir(root), f"state_continuity_{safe_ep}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root, ns.episode)
    if ns.write:
        res["written"] = write_report(ns.root.rstrip("/"), ns.episode, res)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"=== n2d 动态百科 / 状态哨兵（P1）：{ns.root} {ns.episode} ===")
        for note in res.get("notes", []):
            print("ℹ️ " + note)
        for a in res.get("alerts", []):
            icon = "⛔" if a["verdict"] == "block" else "⚠️"
            loc = f"镜{a['shot']} · " if a.get("shot") is not None else ""
            who = f"{a['character']}：" if a.get("character") else ""
            print(f"{icon} {loc}{who}{a.get('message')}")
        if not res.get("alerts"):
            print("✅ 角色/道具状态演进未发现提前泄露/漏继承/未结构化。")
    return 1 if any(v == "block" for v in res.get("verdicts", [])) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
