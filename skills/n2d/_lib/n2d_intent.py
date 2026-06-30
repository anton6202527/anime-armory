#!/usr/bin/env python3
"""逐镜创作意图黑板（shot_intent.json）—— 作者意图 override 单一源 + 派生投影（2026-06-26）。

掣肘根因＝意图散在 5 处（storyboard continuity / state_continuity / asset_registry / _设置.md /
series_bible），冲突只能事后两两对消（打地鼠）。本模块收敛**作者显式意图 override** 到一个
**script 写、下游只读** 的权威对象 `脚本/<集>/shot_intent.json`。

**名实边界（2026-06-26 归正·诚实分层，勿再宣称「全意图单源」）：**
  ① **派生投影**：expression_span / need_endframe / motion_intensity / action_beat / closeup—
     从 storyboard 逐镜派生。**storyboard 仍是这些字段的源**；黑板只是只读投影，重建即覆盖（不持久化
     手改）。故强制这些字段的 BLOCK 闸（gate.py）读 storyboard 是**正确的**，不经黑板——黑板不override它们。
  ② **作者 override（黑板的真权威所在）**：allowed_evolution——作者**显式声明**「这一镜某角色的脸/发/
     服装/道具就该变」，补回关键词漏检的有意改动。**仅此通道是黑板独有、storyboard 没有的真值**；
     state_continuity 的 face/hair/costume 锁经 explicit_evolution_for 消费 field-tagged 条目，
     把该镜 block 降 warn（与关键词派生取并集）。

**陈旧自失效**：黑板派生自某次 storyboard 快照；若 storyboard 后续改了镜数，黑板的 allowed_evolution
  的 from_shot/to_shot 会指错镜 → 据其降级会**误豁免真崩**。故 explicit_evolution_for 在黑板与当前
  storyboard 镜数不符时返回 {}（不据陈旧声明降级，回退关键词检测=安全方向）；定稿后应重跑 write_shot_intent。

写：write_shot_intent → 脚本/<集>/shot_intent.json（原子·保留作者已声明条目；已接进 finalize_storyboard）。
读：load_shot_intent / shot_intent_for / explicit_evolution_for（陈旧自失效）。
纯 stdlib·builder/reader 纯函数可测。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

SHOT_INTENT_KIND = "n2d_shot_intent"
SHOT_INTENT_VERSION = 1
# 允许 author 把 allowed_evolution 条目的 field 标到这些维度，强制路由给对应锁；"" = 交关键词自动分类。
EVOLUTION_FIELDS = ("costume", "face", "hair", "prop")

_CLOSEUP_MARKERS = ("CU", "ECU", "MCU", "BCU", "特写", "近景", "反打", "OTS", "过肩")


def shot_intent_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "shot_intent.json")


def _clip_no(text: Any) -> Optional[int]:
    m = re.search(r"(\d+)", str(text or ""))
    return int(m.group(1)) if m else None


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _storyboard_clips(root: str, ep: str) -> List[Dict[str, Any]]:
    data = _load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    clips = data.get("clips") if isinstance(data, dict) else None
    return [c for c in clips or [] if isinstance(c, dict)]


def _storyboard_fingerprint(root: str, ep: str) -> str:
    """当前 storyboard.json 的内容指纹（sha256，缺文件=""）。

    黑板派生自某次 storyboard 快照；只比镜数会漏掉「等镜数内容改」（改写/换镜/调 continuity），
    陈旧的 allowed_evolution 仍据其降级真崩。内容指纹任一字段变即变，是比镜数更强的陈旧判据。
    用 canonical json（sort_keys）规避格式化抖动；解析失败回退原始字节。纯读取·永不抛。"""
    path = os.path.join(root, "脚本", ep, "storyboard.json")
    data = _load_json(path)
    try:
        if data is not None:
            blob = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
        else:
            with open(path, "rb") as f:
                blob = f.read()
    except Exception:
        return ""
    return hashlib.sha256(blob).hexdigest()


def _clip_blob(clip: Mapping[str, Any]) -> str:
    parts = [str(clip.get(k) or "") for k in ("template", "label", "shot_type", "description", "scene")]
    for shot in clip.get("shots") or []:
        if isinstance(shot, dict):
            parts += [str(shot.get(k) or "") for k in ("lens", "desc", "shot_size")]
    return " ".join(parts)


def _derive_shot(clip: Mapping[str, Any], idx: int) -> Dict[str, Any]:
    """逐镜意图条目（纯函数·可测）：从 storyboard clip 派生稳定意图字段。"""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    blob = _clip_blob(clip)
    return {
        "clip": str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}"),
        "clip_no": idx,
        "expression_span": str(cont.get("expression_span") or "").strip(),
        "need_endframe": cont.get("need_endframe") is True,
        "motion_intensity": str(cont.get("motion_intensity") or "").strip(),
        "action_beat": bool(cont.get("action_beat") is True or cont.get("spectacle") is True),
        "closeup": any(m in blob for m in _CLOSEUP_MARKERS),
        "identity_requirement": str(clip.get("identity_requirement") or cont.get("identity_requirement") or "").strip(),
    }


def _seed_allowed_evolution(root: str, ep: str) -> List[Dict[str, Any]]:
    """从 storyboard.visual_contract.角色状态演进 播种 allowed_evolution 脚手架（field=""·交关键词分类）。

    仅作可见脚手架：field="" 的条目**不**被 explicit_evolution_for 消费（仍由关键词派生处理，行为不变），
    作者把 field 改成 costume/face/hair/prop 并填 from_shot/to_shot 后才被对应锁强制消费。"""
    data = _load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    vc = data.get("visual_contract") if isinstance(data, dict) else {}
    eng = vc.get("角色状态演进") or vc.get("角色状态演进表") or {} if isinstance(vc, dict) else {}
    out: List[Dict[str, Any]] = []
    if not isinstance(eng, dict):
        return out
    for char, entries in eng.items():
        if isinstance(entries, (str, dict)):
            entries = [entries]
        if not isinstance(entries, list):
            continue
        for e in entries:
            desc = (e.get("状态") or e.get("status") or e.get("description")) if isinstance(e, dict) else e
            frm = _clip_no((e.get("自") or e.get("from")) if isinstance(e, dict) else desc)
            out.append({
                "character": str(char),
                "from_shot": frm,
                "to_shot": None,
                "field": "",          # 作者改成 costume/face/hair/prop 才被对应锁强制消费
                "desc": str(desc or ""),
                "source": "seed",     # 作者新增/改动的条目请置 source="author" 以免重建时被覆盖
            })
    return out


def build_shot_intent(root: str, ep: str, *, prior: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """构建逐镜意图黑板对象（纯函数·可测）。prior=已存在黑板时，保留其 source=="author" 的 allowed_evolution。"""
    shots = [_derive_shot(c, i) for i, c in enumerate(_storyboard_clips(root, ep), 1)]
    allowed = _seed_allowed_evolution(root, ep)
    if isinstance(prior, Mapping):
        authored = [e for e in (prior.get("allowed_evolution") or [])
                    if isinstance(e, dict) and str(e.get("source") or "") == "author"]
        allowed = authored + allowed
    return {
        "kind": SHOT_INTENT_KIND,
        "version": SHOT_INTENT_VERSION,
        "episode": ep,
        "storyboard_sha": _storyboard_fingerprint(root, ep),
        "shots": shots,
        "allowed_evolution": allowed,
        "notes": [
            "派生字段只是 storyboard 快照投影：expression_span/need_endframe/motion_intensity/action_beat/closeup "
            "以 storyboard.json 为权威，手改本文件不会覆盖 gate 或生成侧行为。",
            "allowed_evolution 是唯一作者 override 通道：把 field 标成 costume/face/hair/prop 并填 from_shot/to_shot、"
            "置 source=\"author\"，即可显式声明『这一镜某角色该维度就该变』，对应一致性锁会把该镜 block 降 warn"
            "（补回关键词漏检的有意改动）。",
        ],
    }


def write_shot_intent(root: str, ep: str) -> str:
    """构建并原子写 脚本/<集>/shot_intent.json（保留作者已声明条目）。返回路径。"""
    path = shot_intent_path(root, ep)
    obj = build_shot_intent(root, ep, prior=_load_json(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return path


def load_shot_intent(root: str, ep: str) -> Optional[Dict[str, Any]]:
    data = _load_json(shot_intent_path(root, ep))
    return data if isinstance(data, dict) and data.get("kind") == SHOT_INTENT_KIND else None


def shot_intent_for(root: str, ep: str, clip_no: Optional[int]) -> Optional[Dict[str, Any]]:
    """取某镜的逐镜意图条目（下游只读派生用）。缺黑板/缺镜 → None。"""
    bb = load_shot_intent(root, ep)
    if not bb or clip_no is None:
        return None
    for s in bb.get("shots") or []:
        if isinstance(s, dict) and s.get("clip_no") == clip_no:
            return s
    return None


def blackboard_is_stale(root: str, ep: str, bb: Optional[Mapping[str, Any]] = None) -> bool:
    """黑板是否与当前 storyboard 脱节（storyboard 改过、黑板未重建）。

    陈旧时其 allowed_evolution 的 from_shot/to_shot 会指错镜（或指向已改写的镜），据其降级会误豁免
    真崩——故视为不可信。优先用 storyboard 内容指纹（抓「等镜数内容改」）；旧黑板无指纹时回退镜数比对
    （只能抓增删镜）。纯读取·无副作用。bb 缺省时自行加载。"""
    bb = bb if isinstance(bb, Mapping) else load_shot_intent(root, ep)
    if not bb:
        return False  # 无黑板不算陈旧（explicit_evolution_for 早返回 {}）
    recorded_sha = str(bb.get("storyboard_sha") or "").strip()
    if recorded_sha:
        return recorded_sha != _storyboard_fingerprint(root, ep)
    shots = bb.get("shots") if isinstance(bb.get("shots"), list) else []
    return len(shots) != len(_storyboard_clips(root, ep))


def explicit_evolution_for(root: str, ep: str, kind: str) -> Dict[str, List[Tuple[int, Optional[int], str]]]:
    """作者在黑板里显式声明的某维度演进区间：{char: [(from_shot, to_shot|None, desc), ...]}。

    只取 field==kind 且 from_shot 可解析的 field-tagged 条目（field="" 的脚手架不消费，留给关键词派生·防双源）。
    供 state_continuity.appearance_change_intervals 与关键词派生取并集。纯读取·无副作用。

    **陈旧自失效**：黑板与当前 storyboard 镜数不符（storyboard 改过未重建）→ 返回 {}，不据可能错位的
    声明降级真崩（回退关键词检测=安全方向）。定稿后 finalize_storyboard 会重跑 write_shot_intent。"""
    bb = load_shot_intent(root, ep)
    out: Dict[str, List[Tuple[int, Optional[int], str]]] = {}
    if not bb or kind not in EVOLUTION_FIELDS:
        return out
    if blackboard_is_stale(root, ep, bb):
        return out
    for e in bb.get("allowed_evolution") or []:
        if not isinstance(e, dict) or str(e.get("field") or "") != kind:
            continue
        char = str(e.get("character") or "").strip()
        frm = e.get("from_shot")
        if not char or not isinstance(frm, int):
            continue
        to = e.get("to_shot")
        to = to if isinstance(to, int) else None
        out.setdefault(char, []).append((frm, to, str(e.get("desc") or "")))
    return out
