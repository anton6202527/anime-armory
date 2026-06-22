#!/usr/bin/env python3
"""生产一致性补强检查器。

本脚本补足一致性审计里仍偏松的低成本维度：

* O3 物件常驻/对象持久性
* X2 视线轴线与视觉状态的可回读证据
* I1 交互/接触/持有因果图
* C1 成片统一证据（响度、混剪色彩、BGM/room tone）
* RCP 生成配方 hash
* PKG 系列包装一致性
* D1 台词语域一致性
* FP1 场景平面图/区域一致性
* K1 成本、后端、重试口径一致性
* ST1 状态转场视频证据
* POS 道具/资产跨镜持有账本
* I2 结构化交互图谱 schema
* FT1 成片时间线探针
* RCP2 强配方 schema
* CAL 人审校准集
* PROBE 项目一致性探针包

原则：纯标准库；有显式契约时硬验，缺契约先 WARN；能从 production_events 推导的
生成配方会落 `生产数据/generation_recipe_<集>.json`，作为后续复跑/审计的稳定证据。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
try:
    from n2d_contract import production_dir  # noqa: E402
except Exception:  # pragma: no cover - standalone fallback
    def production_dir(root: str) -> str:
        return os.path.join(root, "生产数据")


ASSET_RE = re.compile(r"\b(?:LOC|PROP|OUTFIT|VFX)_[\w\-\u4e00-\u9fff]+\b")
CHAR_RE = re.compile(r"\bCHAR_[\w\-\u4e00-\u9fff]+\b")
CLIP_RE = re.compile(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)")
CONTACT_WORDS = (
    "手持", "握", "拿", "抓", "递", "接过", "交给", "拉住", "拉扯", "扶", "搀扶", "抱",
    "拥抱", "按住", "碰", "触碰", "推开", "击中", "刺中", "格挡", "戴上", "摘下", "放下",
    "掉落", "松开", "hold", "grab", "touch", "hand", "give", "take", "push", "hit",
)
RELEASE_WORDS = ("放下", "丢下", "掉落", "松开", "收起", "消失", "脱手", "release", "drop")
TRANSFER_WORDS = ("递给", "交给", "给了", "递向", "移交", "hand over", "give")
AXIS_WORDS = ("视线", "轴线", "eyeline", "gaze", "看向", "画左", "画右", "正反打", "反打", "过肩")
STATE_WORDS = ("状态", "伤", "血", "泪", "湿", "破", "乱发", "持有", "获得", "丢失", "state", "status")
EXEMPT_WORDS = ("特写", "极近", "ECU", "CU", "细节", "局部", "空镜", "不入画", "画外", "遮挡", "虚焦")
REGISTER_WORDS = ("本宫", "朕", "臣妾", "妾身", "老子", "俺", "人家", "属下", "小的", "奴婢", "为师", "徒儿")
STATE_TRANSITION_WORDS = (
    "变成", "转为", "化作", "出现", "消失", "破裂", "碎裂", "断裂", "燃起", "熄灭", "点燃",
    "流血", "受伤", "愈合", "湿透", "觉醒", "变色", "打开", "关闭", "掉落", "拾起",
    "state_change", "transition", "becomes", "turns into", "appears", "disappears",
)
HIGH_RISK_INTERACTION_WORDS = (
    "打斗", "命中", "刺中", "格挡", "拥抱", "抓腕", "拉扯", "搀扶", "推开", "击中",
    "亲密互动", "physical_interaction", "contact_motion", "feature_melting_risk",
)
REVIEW_LABELS = {"true_positive", "false_positive", "accepted_intentional", "missed_by_machine"}
PROBE_SCENARIOS = (
    "character_turnaround",
    "core_prop_transfer",
    "same_scene_multiview",
    "physical_interaction",
    "state_transition",
    "native_av_dialogue",
)
ASSET_TAIL_ACTIONS = (
    "逼近", "走来", "走近", "转身", "冲向", "看向", "递给", "交给", "刺向", "砍向", "挥向",
    "靠近", "离开", "退到", "退后", "藏到", "藏入", "站起", "坐下", "跪下", "倒下", "落地", "入画", "出画",
)


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _load_first_json(root: str, rels: Sequence[str]) -> Tuple[Optional[Any], str]:
    for rel in rels:
        path = rel if os.path.isabs(rel) else os.path.join(root, rel)
        data = _load_json(path)
        if data is not None:
            return data, os.path.relpath(path, root)
    return None, ""


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def _write_json(path: str, payload: Mapping[str, Any]) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value or "")


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if value in (None, ""):
        return []
    return [value]


def _unique(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _clip_label(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or "").strip()
    if raw:
        m = CLIP_RE.search(raw)
        if m:
            return f"Clip_{int(m.group(1)):02d}"
        return raw
    return f"Clip_{idx:02d}"


def _clip_num(label: str) -> str:
    m = CLIP_RE.search(label)
    return f"Clip_{int(m.group(1)):02d}" if m else label


def _clip_index(label: str) -> int:
    m = CLIP_RE.search(label)
    return int(m.group(1)) if m else 10**9


def _storyboard(root: str, ep: str) -> Tuple[Optional[dict], List[dict]]:
    data = _load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    if not isinstance(data, dict):
        return None, []
    clips = data.get("clips") or data.get("shots") or []
    return data, [c for c in clips if isinstance(c, dict)]


def _sections_by_clip(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not text:
        return out
    blocks = re.split(r"(?m)(?=^#{1,4}\s+)", text)
    for block in blocks:
        head = block.splitlines()[0] if block.splitlines() else ""
        labels = _unique(_clip_num(f"Clip_{int(m.group(1)):02d}") for m in CLIP_RE.finditer(head + "\n" + block[:300]))
        for label in labels:
            out[label] = out.get(label, "") + "\n" + block
    return out


def _prompt_sections(root: str, ep: str) -> Dict[str, str]:
    merged: Dict[str, str] = defaultdict(str)
    for rel in (
        os.path.join("出图", ep, "prompt", "01_分镜出图.md"),
        os.path.join("出视频", ep, "prompt", "01_clips.md"),
    ):
        for clip, text in _sections_by_clip(_read(os.path.join(root, rel))).items():
            merged[clip] += "\n" + text
    return dict(merged)


def _clip_text(clip: Mapping[str, Any], label: str, prompt_sections: Mapping[str, str]) -> str:
    return _json_text(clip) + "\n" + str(prompt_sections.get(label) or "")


def _asset_ids(text: str) -> List[str]:
    def trim(raw: str) -> str:
        for marker in ASSET_TAIL_ACTIONS:
            pos = raw.find(marker)
            if pos > len("PROP_"):
                return raw[:pos]
        return raw
    return _unique(trim(m.group(0)) for m in ASSET_RE.finditer(text or ""))


def _char_ids(text: str) -> List[str]:
    return _unique(m.group(0) for m in CHAR_RE.finditer(text or ""))


def _loc_of(clip: Mapping[str, Any], text: str) -> str:
    for key in ("loc", "location", "scene_id", "scene"):
        raw = str(clip.get(key) or "").strip()
        if raw:
            loc = raw.split("/")[0].strip()
            if loc:
                return loc
    ids = [x for x in _asset_ids(text) if x.startswith("LOC_")]
    return ids[0] if ids else ""


def _is_exempt_view(text: str) -> bool:
    return any(w.lower() in (text or "").lower() for w in EXEMPT_WORDS)


def _artifact_exists(root: str, value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if re.match(r"^(?:https?|s3|gs)://", text):
        return True
    path = text if os.path.isabs(text) else os.path.join(root, text)
    return os.path.exists(path)


def _finding_hash(row: Mapping[str, Any]) -> str:
    stable = {
        "dimension": row.get("dimension") or row.get("dim") or "",
        "message": row.get("message") or row.get("msg") or row.get("reason") or "",
        "affected_shots": row.get("affected_shots") if isinstance(row.get("affected_shots"), list) else [],
        "affected_artifacts": row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else [],
        "loc": row.get("loc") or row.get("path") or "",
    }
    blob = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _registry_assets(root: str) -> List[dict]:
    data = _load_json(os.path.join(root, "出图", "共享", "asset_registry.json"))
    if isinstance(data, dict):
        raw = data.get("assets") or data.get("items") or data.get("registry") or []
        if isinstance(raw, dict):
            raw = [{**(v if isinstance(v, dict) else {}), "id": k} for k, v in raw.items()]
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    return [a for a in raw if isinstance(a, dict)]


def _persistent_assets(root: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for asset in _registry_assets(root):
        aid = str(asset.get("id") or asset.get("asset_id") or "").strip()
        if not aid or not (aid.startswith("PROP_") or aid.startswith("VFX_") or aid.startswith("OUTFIT_")):
            continue
        blob = _json_text(asset).lower()
        persistent = (
            asset.get("persistent") is True
            or asset.get("always_present") is True
            or asset.get("must_appear") is True
            or any(k in blob for k in ("常驻", "恒存", "不得丢", "drift_forbidden", "always_present", "persistent"))
        )
        if persistent:
            out[aid] = asset
    return out


def _row(verdict: str, message: str, *, shot: str = "", stage: str = "image",
         artifacts: Sequence[str] = (), **extra: Any) -> dict:
    row = {
        "verdict": verdict,
        "message": message,
        "return_to_stage": stage,
        "affected_shots": [shot] if shot else [],
        "affected_artifacts": list(artifacts),
    }
    row.update(extra)
    return row


def check_object_permanence(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，物件常驻检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    persistent = _persistent_assets(root)
    expected_by_loc: Dict[str, Dict[str, bool]] = defaultdict(dict)
    for aid, asset in persistent.items():
        loc = str(asset.get("location") or asset.get("loc") or asset.get("scene") or "").split("/")[0].strip()
        if loc:
            expected_by_loc[loc][aid] = True
    if persistent:
        res["notes"].append(f"asset_registry 登记常驻资产 {len(persistent)} 个，缺席按违锁检查。")

    seen_any = False
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        loc = _loc_of(clip, text)
        ids = [aid for aid in _asset_ids(text) if aid.startswith(("PROP_", "OUTFIT_", "VFX_"))]
        if ids:
            seen_any = True
        expected = expected_by_loc.get(loc, {}) if loc else {}
        missing = [aid for aid in expected if aid not in ids]
        if missing and not _is_exempt_view(text):
            for aid in missing:
                sev = "block" if expected.get(aid) else "warn"
                res["findings"].append(_row(
                    sev,
                    f"{loc or '同场景'} 常驻物件 {aid} 已建立但本镜未回读；若确实画外/被遮挡，请写明豁免原因。",
                    shot=label,
                    stage="image",
                    artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/asset_registry.json"),
                    asset=aid,
                    loc=loc,
                ))
        if loc:
            for aid in ids:
                expected_by_loc[loc].setdefault(aid, aid in persistent)
    if not seen_any and not persistent:
        res["notes"].append("未检测到 PROP/OUTFIT/VFX 资产 ID；物件常驻只能做人审，建议给常驻道具补 asset_registry id。")
    return res


def _visual_state_contract_text(sb: Optional[dict]) -> str:
    vc = (sb or {}).get("visual_contract") if isinstance(sb, dict) else {}
    if not isinstance(vc, dict):
        return ""
    return _json_text(vc.get("角色状态演进") or vc.get("character_state_progression") or "")


def _image_qc_precision(root: str, ep: str) -> str:
    data = _load_json(os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json"))
    if not isinstance(data, dict):
        return ""
    env = data.get("qc_environment") if isinstance(data.get("qc_environment"), dict) else {}
    return str(data.get("precision_level") or env.get("precision_level") or data.get("precision") or "").strip()


def check_axis_state_readback(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，视线/状态回读检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    state_contract = _visual_state_contract_text(sb)
    high_risk = 0
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        char_count = len(_char_ids(text))
        needs_axis = char_count >= 2 or any(w in text for w in ("对话", "反打", "过肩", "看向", "凝视"))
        needs_state = bool(state_contract) and char_count >= 1
        if needs_axis:
            high_risk += 1
            if not any(w.lower() in text.lower() for w in AXIS_WORDS):
                res["findings"].append(_row(
                    "warn",
                    "多人/对话镜缺视线/轴线可回读字段；像素 X1 误报或缺库时无法复核该镜越轴风险。",
                    shot=label,
                    stage="image",
                    artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md"),
                ))
        if needs_state and not any(w.lower() in text.lower() for w in STATE_WORDS):
            res["findings"].append(_row(
                "warn",
                "本集有角色状态演进契约，但该角色镜缺状态回读词；容易出现伤/泪/战损提前泄露或自愈。",
                shot=label,
                stage="image",
                artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md"),
            ))
    precision = _image_qc_precision(root, ep)
    if high_risk and precision and precision != "full":
        res["findings"].append(_row(
            "warn",
            f"{high_risk} 个视线/状态高风险镜当前 image_qc 精度为 {precision}；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。",
            stage="review",
            artifacts=(f"生产数据/image_qc/{ep}/image_qc_{ep}.json",),
        ))
    return res


def _state_transition_manifest(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"state_transition_manifest_{ep}.json"),
        os.path.join("生产数据", f"state_transition_{ep}.json"),
        os.path.join("脚本", ep, "state_transition_manifest.json"),
        os.path.join("设定库", "state_transition_manifest.json"),
    ))


def _transition_entries(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("transitions") or data.get("state_transitions") or data.get("items") or []
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _clip_has_state_transition(text: str, clip: Mapping[str, Any]) -> bool:
    if isinstance(clip.get("state_transition"), (dict, list)):
        return True
    cont = clip.get("continuity")
    if isinstance(cont, Mapping) and isinstance(cont.get("state_transition"), (dict, list)):
        return True
    low = (text or "").lower()
    return any(w.lower() in low for w in STATE_TRANSITION_WORDS)


def _entry_clip(entry: Mapping[str, Any]) -> str:
    return _clip_num(str(
        entry.get("clip")
        or entry.get("clip_id")
        or entry.get("shot")
        or entry.get("from_clip")
        or ""
    ))


def _entry_frames(entry: Mapping[str, Any]) -> List[Any]:
    frames: List[Any] = []
    for key in ("before_frame", "after_frame", "start_frame", "end_frame"):
        if entry.get(key):
            frames.append(entry.get(key))
    for item in _as_list(entry.get("evidence_frames") or entry.get("frames")):
        if isinstance(item, Mapping):
            frames.append(item.get("path") or item.get("frame") or item.get("image"))
        else:
            frames.append(item)
    return [f for f in frames if f]


def check_state_transition_verification(root: str, ep: str) -> dict:
    """状态变化从“prompt 写了”升级为“视频/帧证据能证明前后状态”的审计入口。"""
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，状态转场验证跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    candidate_clips: List[str] = []
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        if _clip_has_state_transition(text, clip):
            candidate_clips.append(label)
    data, manifest_rel = _state_transition_manifest(root, ep)
    if not candidate_clips and data is None:
        res["notes"].append("未检测到显式状态变化镜，ST1 跳过。")
        return res
    if data is None:
        res["findings"].append(_row(
            "warn",
            f"检测到 {len(candidate_clips)} 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。",
            stage="script_stage2",
            artifacts=(f"脚本/{ep}/storyboard.json", f"生产数据/state_transition_manifest_{ep}.json"),
        ))
        return res

    entries = _transition_entries(data)
    by_clip = {_entry_clip(e): e for e in entries if _entry_clip(e)}
    for label in candidate_clips:
        if label not in by_clip:
            res["findings"].append(_row(
                "warn",
                "本镜含状态变化语义，但 state_transition_manifest 未登记该 Clip 的 before/after 验证项。",
                shot=label,
                stage="script_stage2",
                artifacts=(manifest_rel, f"脚本/{ep}/storyboard.json"),
            ))
    for entry in entries:
        label = _entry_clip(entry)
        missing = []
        if not (entry.get("subject") or entry.get("asset") or entry.get("entity") or entry.get("character")):
            missing.append("subject/entity")
        if not (entry.get("from_state") or entry.get("before") or entry.get("initial_state")):
            missing.append("from_state")
        if not (entry.get("to_state") or entry.get("after") or entry.get("target_state")):
            missing.append("to_state")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"状态转场条目缺字段：{', '.join(missing)}。",
                shot=label,
                stage="script_stage2",
                artifacts=(manifest_rel,),
            ))
        frames = _entry_frames(entry)
        if len(frames) < 2:
            res["findings"].append(_row(
                "warn",
                "状态转场缺 before/after 证据帧；只靠文字无法证明视频完成了变化。",
                shot=label,
                stage="video",
                artifacts=(manifest_rel,),
            ))
        else:
            missing_frames = [str(f) for f in frames if not _artifact_exists(root, f)]
            if missing_frames:
                res["findings"].append(_row(
                    "warn",
                    f"状态转场证据帧不存在：{', '.join(missing_frames[:4])}。",
                    shot=label,
                    stage="video",
                    artifacts=(manifest_rel,),
                ))
        questions = entry.get("vqa_questions") or entry.get("checks") or entry.get("questions")
        if not _as_list(questions):
            res["findings"].append(_row(
                "warn",
                "状态转场缺 VQA/人审判断题；建议至少写“初始是否为 A / 最终是否为 B / 是否完成变化”。",
                shot=label,
                stage="review",
                artifacts=(manifest_rel,),
            ))
        if _final_cuts(root, ep) and str(entry.get("status") or entry.get("verdict") or "").lower() not in {"pass", "ok", "verified"} and entry.get("verified") is not True:
            res["findings"].append(_row(
                "warn",
                "成片已存在，但该状态转场尚未标记 verified/pass；交付前需要抽帧或人审签收。",
                shot=label,
                stage="review",
                artifacts=(manifest_rel, f"合成/{ep}"),
            ))
    return res


def _possession_ledger(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"possession_ledger_{ep}.json"),
        os.path.join("生产数据", f"asset_possession_{ep}.json"),
        os.path.join("脚本", ep, "possession_ledger.json"),
        os.path.join("设定库", "possession_ledger.json"),
    ))


def _possession_events(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("events") or data.get("possessions") or data.get("transfers") or data.get("items") or []
        if isinstance(raw, dict):
            rows = []
            for key, value in raw.items():
                if isinstance(value, dict):
                    rows.append({"asset": key, **value})
                else:
                    rows.append({"asset": key, "holder": value})
            raw = rows
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _pos_event_clip(event: Mapping[str, Any]) -> str:
    return _clip_num(str(event.get("clip") or event.get("clip_id") or event.get("shot") or ""))


def _pos_event_asset(event: Mapping[str, Any]) -> str:
    return str(event.get("asset") or event.get("prop") or event.get("item") or event.get("asset_id") or "").strip()


def _pos_event_action(event: Mapping[str, Any]) -> str:
    return str(event.get("action") or event.get("event") or event.get("type") or "").strip().lower()


def _pos_event_holder(event: Mapping[str, Any]) -> str:
    return str(event.get("holder") or event.get("owner") or event.get("to_holder") or event.get("to") or "").strip()


def check_possession_ledger(root: str, ep: str) -> dict:
    """跨镜/跨场跟踪道具持有状态，避免“道具瞬移”只被同镜交互规则偶然抓到。"""
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，持有账本检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    mentions: List[dict] = []
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        for asset, holder in _holder_mentions(text):
            if asset.startswith("PROP_"):
                mentions.append({"clip": label, "asset": asset, "holder": holder, "text": text})
    if not mentions:
        res["notes"].append("未检测到显式 PROP_ 持有描述，POS 跳过。")
        return res

    data, ledger_rel = _possession_ledger(root, ep)
    if data is None:
        res["findings"].append(_row(
            "warn",
            "本集存在道具持有镜，但缺 possession_ledger；跨场持有/交接/丢失只能靠上下文记忆，建议落持有账本。",
            stage="script_stage2",
            artifacts=(f"脚本/{ep}/storyboard.json", f"生产数据/possession_ledger_{ep}.json"),
        ))

    by_prop: Dict[str, List[dict]] = defaultdict(list)
    for item in mentions:
        by_prop[item["asset"]].append(item)
    transfer_events: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    if data is not None:
        for event in _possession_events(data):
            asset = _pos_event_asset(event)
            clip = _pos_event_clip(event)
            missing = []
            if not asset:
                missing.append("asset/prop")
            if not clip:
                missing.append("clip")
            if not (_pos_event_action(event) or _pos_event_holder(event)):
                missing.append("action/holder")
            if missing:
                res["findings"].append(_row(
                    "warn",
                    f"持有账本条目缺字段：{', '.join(missing)}。",
                    shot=clip,
                    stage="script_stage2",
                    artifacts=(ledger_rel,),
                ))
            if asset and clip:
                transfer_events[(asset, clip)].append(event)

    for asset, rows in by_prop.items():
        rows.sort(key=lambda r: _clip_index(r["clip"]))
        prev: Optional[dict] = None
        for row in rows:
            if data is not None and not transfer_events.get((asset, row["clip"])):
                res["findings"].append(_row(
                    "warn",
                    f"{asset} 在 {row['clip']} 有持有状态，但 possession_ledger 未登记本镜状态。",
                    shot=row["clip"],
                    stage="script_stage2",
                    artifacts=(ledger_rel, f"脚本/{ep}/storyboard.json"),
                    asset=asset,
                ))
            if prev and row["holder"] != prev["holder"]:
                text = row.get("text") or ""
                events = transfer_events.get((asset, row["clip"]), [])
                declared_transfer = any(_pos_event_action(e) in {"transfer", "handoff", "release", "drop", "pickup", "acquire", "move"} for e in events)
                if not declared_transfer and not any(w.lower() in text.lower() for w in TRANSFER_WORDS + RELEASE_WORDS):
                    res["findings"].append(_row(
                        "block",
                        f"{asset} 持有者从 {prev['holder']} 跳到 {row['holder']}，但缺 transfer/release/pickup 账本事件。",
                        shot=row["clip"],
                        stage="script_stage2",
                        artifacts=(ledger_rel or f"脚本/{ep}/storyboard.json",),
                        asset=asset,
                    ))
            prev = row
    return res


def _has_contact(text: str) -> bool:
    low = (text or "").lower()
    return any(w.lower() in low for w in CONTACT_WORDS)


def _has_interaction_graph(clip: Mapping[str, Any], text: str) -> bool:
    if isinstance(clip.get("interaction_graph"), (dict, list)):
        return True
    tc = clip.get("template_contract")
    if isinstance(tc, Mapping) and isinstance(tc.get("interaction_graph"), (dict, list)):
        return True
    return any(token in text for token in ("interaction_graph", "contact_graph", "接触图", "接触点", "持有状态", "左右手", "left_hand", "right_hand"))


def _holder_mentions(text: str) -> List[Tuple[str, str]]:
    mentions: List[Tuple[str, str]] = []
    direct = list(re.finditer(
        r"([一-龥A-Za-z0-9_]{2,12})(?:正|在|仍|依旧|双手|单手|左手|右手)?"
        r"(?:手持|握|拿|抓|举|抱着|持有|holds?|grabs?)\s*"
        r"(PROP_[\w\-\u4e00-\u9fff]+?)(?=$|[\"'，。；,;\s}]|"
        + "|".join(re.escape(x) for x in ASSET_TAIL_ACTIONS) + r")",
        text or "",
        re.I,
    ))
    for m in direct:
        mentions.append((_asset_ids(m.group(2))[0], m.group(1)))
    if mentions:
        return mentions
    for aid in _asset_ids(text):
        if not aid.startswith("PROP_"):
            continue
        before = text[: max(0, text.find(aid))]
        matches = list(re.finditer(
            r"([一-龥A-Za-z0-9_]{2,12})(?:正|在|仍|依旧|双手|单手|左手|右手)?"
            r"(?:手持|握|拿|抓|举|抱着|持有|holds?|grabs?)",
            before[-80:],
            re.I,
        ))
        if matches:
            mentions.append((aid, matches[-1].group(1)))
    return mentions


def _load_routes(root: str, ep: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for rel in (
        os.path.join("生产数据", "video_model_routes.json"),
        os.path.join("出视频", ep, "prompt", "video_model_routes.json"),
    ):
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            routes = data.get("routes") or data.get("clips") or []
            if isinstance(routes, dict):
                routes = [{**(v if isinstance(v, dict) else {}), "clip_id": k} for k, v in routes.items()]
        elif isinstance(data, list):
            routes = data
        else:
            routes = []
        for route in routes or []:
            if not isinstance(route, dict):
                continue
            cid = _clip_num(str(route.get("clip_id") or route.get("id") or route.get("clip") or ""))
            if cid:
                out[cid] = route
    return out


def check_interaction_graph(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，交互接触检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    routes = _load_routes(root, ep)
    holder_by_prop: Dict[str, str] = {}
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        if not _has_contact(text):
            continue
        if not _has_interaction_graph(clip, text):
            res["findings"].append(_row(
                "warn",
                "物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。",
                shot=label,
                stage="script_stage2",
                artifacts=(f"脚本/{ep}/storyboard.json",),
            ))
        route = routes.get(label)
        motion = route.get("motion_control") if isinstance(route, dict) else None
        if route and not isinstance(motion, Mapping):
            res["findings"].append(_row(
                "warn",
                "接触镜已有视频路由但缺 motion_control 契约；出视频 fallback 时接触/遮挡稳定性不可审计。",
                shot=label,
                stage="video_prompt",
                artifacts=(f"出视频/{ep}/prompt/video_model_routes.json",),
            ))
        releasing = any(w in text for w in RELEASE_WORDS)
        transfer = any(w in text for w in TRANSFER_WORDS)
        for aid, holder in _holder_mentions(text):
            prev = holder_by_prop.get(aid)
            if prev and holder != prev and not transfer:
                res["findings"].append(_row(
                    "block",
                    f"{aid} 持有者从 {prev} 变成 {holder}，但本镜缺递交/掉落/拾取因果；会造成道具瞬移。",
                    shot=label,
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json",),
                    asset=aid,
                ))
            holder_by_prop[aid] = "" if releasing else holder
    return res


def _interaction_graphs(clip: Mapping[str, Any]) -> List[dict]:
    raw = clip.get("interaction_graph") or clip.get("contact_graph")
    tc = clip.get("template_contract")
    if raw in (None, "") and isinstance(tc, Mapping):
        raw = tc.get("interaction_graph") or tc.get("contact_graph")
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _graph_has(graphs: Sequence[Mapping[str, Any]], *keys: str) -> bool:
    for graph in graphs:
        for key in keys:
            value = graph.get(key)
            if value not in (None, "", [], {}):
                return True
    return False


def check_interaction_schema(root: str, ep: str) -> dict:
    """把 I1 的自由文本 contact_graph 升级为可机器校验的交互图谱 schema。"""
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，结构化交互图谱检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        if not _has_contact(text):
            continue
        high_risk = any(w.lower() in text.lower() for w in HIGH_RISK_INTERACTION_WORDS)
        graphs = _interaction_graphs(clip)
        if not graphs:
            res["findings"].append(_row(
                "block" if high_risk else "warn",
                "接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。",
                shot=label,
                stage="script_stage2",
                artifacts=(f"脚本/{ep}/storyboard.json",),
            ))
            continue
        missing = []
        if len(_char_ids(text)) >= 2 and not _graph_has(graphs, "participants", "actors", "entities"):
            missing.append("participants")
        if not _graph_has(graphs, "contact_points", "contact_point", "body_contact", "touch_points"):
            missing.append("contact_points")
        if not _graph_has(graphs, "body_part_ownership", "body_parts", "left_hand", "right_hand", "holder_state"):
            missing.append("body_part_ownership/holder_state")
        if high_risk and not _graph_has(graphs, "occlusion_order", "depth_order", "layer_order"):
            missing.append("occlusion_order")
        if any(w in text for w in ("打斗", "命中", "刺中", "格挡", "推开", "击中")) and not _graph_has(graphs, "force_direction", "motion_vector", "impact_direction"):
            missing.append("force_direction")
        if any(w in text for w in TRANSFER_WORDS + RELEASE_WORDS) and not _graph_has(graphs, "transfer_event", "release_frame", "handoff", "pickup_frame"):
            missing.append("transfer_event/release_frame")
        if missing:
            res["findings"].append(_row(
                "block" if high_risk else "warn",
                f"interaction_graph 缺 schema 字段：{', '.join(missing)}。",
                shot=label,
                stage="script_stage2",
                artifacts=(f"脚本/{ep}/storyboard.json",),
            ))
    return res


def _final_cuts(root: str, ep: str) -> List[str]:
    import glob
    return sorted(glob.glob(os.path.join(root, "合成", ep, "成片_*.mp4")))


def _target_platform(root: str) -> str:
    settings = _read(os.path.join(root, "_设置.md"))
    m = re.search(r"(?m)^[\s\-*>|]*目标平台\s*[:：]\s*(.+?)\s*$", settings)
    return (m.group(1).strip().split("|")[0] if m else "default").lower()


def _run_loudness(root: str, ep: str) -> Optional[dict]:
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d-compose"))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    try:
        import loudness_conform  # type: ignore
        return loudness_conform.analyze(root, ep, platform=_target_platform(root))
    except Exception as exc:
        return {"available": False, "verdict": "ok", "notes": [f"响度检查调用失败：{exc}"]}


def _rhythm_variety(sb: Optional[dict]) -> bool:
    clips = (sb or {}).get("clips") or []
    values = {str(c.get("rhythm") or c.get("节奏") or "") for c in clips if isinstance(c, dict)}
    return len([v for v in values if v]) >= 2


def check_final_composite(root: str, ep: str) -> dict:
    sb, _ = _storyboard(root, ep)
    res = {"available": bool(_final_cuts(root, ep)), "findings": [], "notes": []}
    if not res["available"]:
        res["notes"].append("未检测到成片，成片统一检查等待 compose/review 阶段。")
        return res
    loud = _run_loudness(root, ep)
    if loud:
        for note in loud.get("notes", []) or []:
            res["notes"].append(str(note))
        verdict = str(loud.get("verdict") or "ok")
        if verdict in {"warn", "block"}:
            res["findings"].append(_row(
                verdict,
                f"成片响度不贴目标：LUFS={loud.get('measured_lufs')} target={loud.get('target')} true_peak={loud.get('true_peak')}",
                stage="compose",
                artifacts=(f"合成/{ep}",),
            ))
    routes = _load_routes(root, ep)
    providers = {str(r.get("primary_backend") or "") for r in routes.values() if r.get("primary_backend")}
    if len(providers) >= 2:
        evidence = any(os.path.isfile(os.path.join(root, rel)) for rel in (
            os.path.join("生产数据", f"color_match_{ep}.json"),
            os.path.join("合成", ep, "color_match_report.json"),
        ))
        if not evidence:
            res["findings"].append(_row(
                "warn",
                f"本集视频混用了 {len(providers)} 个 primary 后端，但缺色彩匹配报告；混剪易出现亮度/色温跳。",
                stage="compose",
                artifacts=(f"出视频/{ep}/prompt/video_model_routes.json", f"合成/{ep}"),
            ))
    if _rhythm_variety(sb) and not os.path.isfile(os.path.join(root, "生产数据", f"tension_mix_{ep}.json")):
        res["findings"].append(_row(
            "warn",
            "storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。",
            stage="compose",
            artifacts=(f"脚本/{ep}/storyboard.json", f"合成/{ep}"),
        ))
    if not any(os.path.isfile(os.path.join(root, rel)) for rel in (
        os.path.join("生产数据", f"room_tone_{ep}.json"),
        os.path.join("合成", ep, "room_tone.json"),
        os.path.join("生产数据", f"foley_{ep}.json"),
    )):
        res["findings"].append(_row(
            "warn",
            "缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。",
            stage="compose",
            artifacts=(f"合成/{ep}",),
        ))
    return res


def _final_timeline_probe(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"final_timeline_probe_{ep}.json"),
        os.path.join("合成", ep, "final_timeline_probe.json"),
        os.path.join("合成", ep, f"final_timeline_probe_{ep}.json"),
    ))


def _probe_rows(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("findings") or data.get("segments") or data.get("cuts") or data.get("scenarios") or data.get("rows") or data.get("items") or []
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _num(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def check_final_timeline_probe(root: str, ep: str) -> dict:
    """直接量成片时间线，补足“报告存在”但没量亮度/音量/静音缝的松动点。"""
    cuts = _final_cuts(root, ep)
    res = {"available": bool(cuts), "findings": [], "notes": []}
    if not cuts:
        res["notes"].append("未检测到成片，final timeline probe 等待 compose 阶段。")
        return res
    data, rel = _final_timeline_probe(root, ep)
    if data is None:
        res["findings"].append(_row(
            "warn",
            "成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。",
            stage="compose",
            artifacts=(f"合成/{ep}/final_timeline_probe.json", f"合成/{ep}"),
        ))
        return res
    rows = _probe_rows(data)
    if not rows:
        res["findings"].append(_row(
            "warn",
            "final_timeline_probe 缺 segments/cuts/findings 明细；只有总览无法定位具体剪点。",
            stage="compose",
            artifacts=(rel,),
        ))
        return res
    for row in rows:
        verdict = str(row.get("verdict") or row.get("severity") or "").lower()
        label = str(row.get("cut") or row.get("segment") or row.get("timecode") or row.get("clip") or "")
        if verdict in {"block", "fail", "red"}:
            res["findings"].append(_row("block", str(row.get("message") or "成片时间线探针发现阻断项。"), shot=label, stage="compose", artifacts=(rel,)))
            continue
        if verdict in {"warn", "yellow"}:
            res["findings"].append(_row("warn", str(row.get("message") or "成片时间线探针发现建议项。"), shot=label, stage="compose", artifacts=(rel,)))
        luma = _num(row.get("luma_delta") or row.get("brightness_delta"))
        color = _num(row.get("color_delta") or row.get("hue_delta") or row.get("temperature_delta"))
        lufs = _num(row.get("lufs_delta") or row.get("loudness_delta"))
        rms = _num(row.get("rms_delta_db") or row.get("volume_delta_db"))
        silence = _num(row.get("silence_gap_ms") or row.get("audio_gap_ms"))
        if luma is not None and luma > 0.18:
            res["findings"].append(_row("warn", f"剪点亮度跳变 luma_delta={luma:.3f}，需要色彩/曝光匹配。", shot=label, stage="compose", artifacts=(rel,)))
        if color is not None and color > 0.20:
            res["findings"].append(_row("warn", f"剪点色彩跳变 color_delta={color:.3f}，需要混剪色彩统一。", shot=label, stage="compose", artifacts=(rel,)))
        if lufs is not None and abs(lufs) > 3.0:
            res["findings"].append(_row("warn", f"剪点响度突变 lufs_delta={lufs:.1f}dB。", shot=label, stage="compose", artifacts=(rel,)))
        if rms is not None and abs(rms) > 6.0:
            res["findings"].append(_row("warn", f"剪点 RMS 音量突变 {rms:.1f}dB。", shot=label, stage="compose", artifacts=(rel,)))
        if silence is not None and silence > 250:
            res["findings"].append(_row("warn", f"剪点存在 {silence:.0f}ms 静音/空缝。", shot=label, stage="compose", artifacts=(rel,)))
    return res


def _load_events(root: str) -> List[dict]:
    path = os.path.join(production_dir(root), "production_events.jsonl")
    out: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    out.append(item)
    except FileNotFoundError:
        pass
    return out


def _event_asset(event: Mapping[str, Any]) -> str:
    gen = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    return str(gen.get("asset") or event.get("asset") or "").strip()


def _event_provider(event: Mapping[str, Any]) -> str:
    gen = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
    return str(cost.get("provider") or gen.get("provider") or event.get("provider") or "").strip()


def _event_meta(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("meta") if isinstance(event.get("meta"), Mapping) else {}


def _event_value(event: Mapping[str, Any], *keys: str) -> Any:
    gen = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    meta = _event_meta(event)
    cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
    for key in keys:
        for source in (event, gen, meta, cost):
            value = source.get(key) if isinstance(source, Mapping) else None
            if value not in (None, ""):
                return value
    return ""


def recipe_fingerprint(event: Mapping[str, Any]) -> str:
    meta = dict(_event_meta(event))
    gen = dict(event.get("generation") if isinstance(event.get("generation"), Mapping) else {})
    keys = (
        "stage", "event", "source",
        "provider", "asset", "status",
        "mode", "task", "shot", "codex_model", "model", "model_version", "model_id", "backend",
        "logical_seed", "requested_seed", "effective_seed", "seed_effective", "seed_strategy", "seed_support",
        "reference_manifest", "reference_bundle", "reference_bundle_sha256", "reference_input_count", "reference_input_paths",
        "prompt_hash", "prompt_sha256", "prompt_source_path", "negative_prompt_sha256",
        "adapter_version", "qc_version", "route_hash", "input_fingerprint",
        "resolution", "aspect_ratio", "duration_s", "fps", "scheduler", "steps", "cfg_scale",
        "submit_id",
    )
    stable: Dict[str, Any] = {}
    for key in keys:
        value = event.get(key)
        if value in (None, ""):
            value = gen.get(key)
        if value in (None, ""):
            value = meta.get(key)
        if value not in (None, ""):
            stable[key] = value
    blob = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_recipe_ledger(root: str, ep: str) -> dict:
    rows: List[dict] = []
    for event in _load_events(root):
        if str(event.get("episode") or "") != ep:
            continue
        if str(event.get("event") or "") not in {"generation", "redraw"}:
            continue
        asset = _event_asset(event)
        if not asset:
            continue
        meta = _event_meta(event)
        rows.append({
            "stage": event.get("stage"),
            "event": event.get("event"),
            "asset": asset,
            "provider": _event_provider(event),
            "status": (event.get("generation") or {}).get("status") if isinstance(event.get("generation"), Mapping) else "",
            "recipe_hash": str(meta.get("recipe_hash") or recipe_fingerprint(event)),
            "declared_recipe_hash": bool(meta.get("recipe_hash")),
            "seed": meta.get("logical_seed") or meta.get("requested_seed") or meta.get("effective_seed") or "",
            "seed_effective": _event_value(event, "seed_effective", "effective_seed"),
            "seed_support": _event_value(event, "seed_support", "seed_capability"),
            "seed_strategy": _event_value(event, "seed_strategy", "seed_policy", "seed_degrade"),
            "mode": meta.get("mode") or "",
            "reference_manifest": meta.get("reference_manifest") or meta.get("reference_bundle") or "",
            "reference_bundle_sha256": _event_value(event, "reference_bundle_sha256", "reference_sha256", "reference_digest"),
            "prompt_sha256": _event_value(event, "prompt_sha256", "prompt_hash", "prompt_digest"),
            "route_hash": _event_value(event, "route_hash"),
            "adapter_version": _event_value(event, "adapter_version", "adapter_commit", "adapter_rev"),
            "qc_version": _event_value(event, "qc_version", "qc_schema_version", "review_schema_version"),
        })
    return {
        "kind": "n2d_generation_recipe_ledger",
        "version": 1,
        "root": root,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "rows": rows,
        "summary": {"count": len(rows), "declared_hash": sum(1 for r in rows if r.get("declared_recipe_hash"))},
    }


def write_recipe_ledger(root: str, ep: str) -> str:
    return _write_json(os.path.join(production_dir(root), f"generation_recipe_{ep}.json"), build_recipe_ledger(root, ep))


def _existing_media(root: str, ep: str) -> List[str]:
    import glob
    out = []
    for pattern in (
        os.path.join(root, "出图", ep, "图片", "*.png"),
        os.path.join(root, "出视频", ep, "视频", "*.mp4"),
    ):
        out.extend(os.path.relpath(p, root) for p in glob.glob(pattern))
    return sorted(out)


def check_generation_recipe(root: str, ep: str) -> dict:
    res = {"available": True, "findings": [], "notes": []}
    ledger = build_recipe_ledger(root, ep)
    rows = ledger.get("rows", [])
    if not rows and _existing_media(root, ep):
        res["findings"].append(_row(
            "warn",
            "本集已有媒体文件但 production_events 无 generation/redraw 记录；无法复算后端、参考图、seed 与配方 hash。",
            stage="review",
            artifacts=("生产数据/production_events.jsonl", f"出图/{ep}", f"出视频/{ep}"),
        ))
        return res
    for row in rows:
        missing = []
        if not row.get("provider"):
            missing.append("provider")
        if not row.get("mode"):
            missing.append("mode")
        if not row.get("seed"):
            missing.append("seed/seed_degrade")
        if not row.get("declared_recipe_hash"):
            missing.append("declared_recipe_hash")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"{row.get('asset')} 生成事件缺配方字段：{', '.join(missing)}；已可推导 hash={row.get('recipe_hash')}，但复跑审计证据不完整。",
                stage="image" if row.get("stage") == "image" else "video",
                artifacts=("生产数据/production_events.jsonl",),
            ))
    return res


def check_recipe_schema(root: str, ep: str) -> dict:
    res = {"available": True, "findings": [], "notes": []}
    ledger = build_recipe_ledger(root, ep)
    rows = ledger.get("rows", [])
    if not rows and _existing_media(root, ep):
        res["findings"].append(_row(
            "warn",
            "本集已有媒体但缺 generation recipe rows；强配方 schema 无法校验 prompt/reference/route 指纹。",
            stage="review",
            artifacts=("生产数据/production_events.jsonl", f"出图/{ep}", f"出视频/{ep}"),
        ))
        return res
    for row in rows:
        missing = []
        if not row.get("prompt_sha256"):
            missing.append("prompt_sha256")
        if not (row.get("reference_bundle_sha256") or row.get("reference_manifest")):
            missing.append("reference_bundle_sha256/reference_manifest")
        if str(row.get("stage") or "") == "video" and not row.get("route_hash"):
            missing.append("route_hash")
        if not row.get("adapter_version"):
            missing.append("adapter_version")
        if not row.get("qc_version"):
            missing.append("qc_version")
        if not (row.get("seed") or row.get("seed_effective") or row.get("seed_support") in {"unsupported", "none", "not_supported"}):
            missing.append("seed_effective_or_unsupported")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"{row.get('asset')} 强配方 schema 缺字段：{', '.join(missing)}；recipe_hash 已有但还不能完整复现/归因。",
                stage="image" if row.get("stage") == "image" else "video",
                artifacts=("生产数据/production_events.jsonl", f"生产数据/generation_recipe_{ep}.json"),
            ))
    return res


def check_series_packaging(root: str, ep: str) -> dict:
    paths = [
        os.path.join(root, "设定库", "series_packaging.json"),
        os.path.join(root, "设定库", "包装规范.json"),
        os.path.join(root, "合成", "交付", "series_packaging.json"),
    ]
    data = next((x for x in (_load_json(p) for p in paths) if isinstance(x, dict)), None)
    res = {"available": data is not None, "findings": [], "notes": []}
    if data is None:
        res["findings"].append(_row(
            "warn",
            "缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。",
            stage="compose",
            artifacts=("设定库/series_packaging.json", "合成/交付"),
        ))
        return res
    required = {
        "title_treatment": ("title_treatment", "标题字", "title"),
        "subtitle_style": ("subtitle_style", "subtitle_font", "字幕字体", "font"),
        "cover": ("cover", "封面", "thumbnail"),
        "intro": ("intro", "片头"),
        "outro": ("outro", "片尾"),
        "transition_sfx": ("transition_sfx", "转场音效", "sfx"),
    }
    blob = _json_text(data)
    for key, aliases in required.items():
        if not any(alias in data or alias in blob for alias in aliases):
            res["findings"].append(_row(
                "warn",
                f"系列包装规范缺 {key}；建议在设定库/series_packaging.json 固化。",
                stage="compose",
                artifacts=("设定库/series_packaging.json",),
            ))
    return res


def _voice_lines(root: str, ep: str) -> List[Tuple[str, str]]:
    text = _read(os.path.join(root, "脚本", ep, "voiceover.txt"))
    rows = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        m = re.match(r"^([^:：]{1,24})[:：]\s*(.+)$", raw)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip()))
    return rows


def check_dialogue_register(root: str, ep: str) -> dict:
    rows = _voice_lines(root, ep)
    paths = [
        os.path.join(root, "设定库", "dialogue_register.json"),
        os.path.join(root, "设定库", "voice_register.json"),
        os.path.join(root, "设定库", "语域表.json"),
    ]
    data = next((x for x in (_load_json(p) for p in paths) if isinstance(x, dict)), None)
    res = {"available": bool(rows), "findings": [], "notes": []}
    if not rows:
        res["notes"].append("缺 voiceover 台词行，语域一致性跳过。")
        return res
    by_role: Dict[str, List[str]] = defaultdict(list)
    for role, text in rows:
        by_role[role].append(text)
    if data is None:
        for role, lines in by_role.items():
            used = sorted({w for w in REGISTER_WORDS if any(w in line for line in lines)})
            if len(used) >= 2:
                res["findings"].append(_row(
                    "warn",
                    f"角色「{role}」自称/语气词混用 {', '.join(used)}，但缺语域表判定是否合理。",
                    stage="script_stage1",
                    artifacts=(f"脚本/{ep}/voiceover.txt", "设定库/dialogue_register.json"),
                ))
        if not res["findings"]:
            res["findings"].append(_row(
                "warn",
                "缺 dialogue_register/语域表；目前只能查称谓，无法约束角色句式、尊卑语气和禁用词。",
                stage="script_stage1",
                artifacts=("设定库/dialogue_register.json",),
            ))
        return res
    for role, lines in by_role.items():
        spec = data.get(role) or data.get(str(role).strip()) or {}
        if not isinstance(spec, dict):
            continue
        forbidden = spec.get("forbidden") or spec.get("禁用") or []
        must = spec.get("must_use") or spec.get("must") or spec.get("口癖") or []
        for token in forbidden if isinstance(forbidden, list) else [forbidden]:
            if token and any(str(token) in line for line in lines):
                res["findings"].append(_row(
                    "warn",
                    f"角色「{role}」台词出现语域禁用词「{token}」。",
                    stage="script_stage1",
                    artifacts=(f"脚本/{ep}/voiceover.txt", "设定库/dialogue_register.json"),
                ))
        if must:
            tokens = must if isinstance(must, list) else [must]
            if not any(str(t) in line for t in tokens for line in lines):
                res["findings"].append(_row(
                    "warn",
                    f"角色「{role}」本集没有回读语域锚点 {tokens[:3]}；若本集戏份较多，可能口吻漂移。",
                    stage="script_stage1",
                    artifacts=(f"脚本/{ep}/voiceover.txt", "设定库/dialogue_register.json"),
                ))
    return res


def _floorplan_data(root: str) -> Optional[dict]:
    for rel in (
        os.path.join("设定库", "scene_floorplan.json"),
        os.path.join("设定库", "场景平面图.json"),
        os.path.join("出图", "共享", "scene_floorplan.json"),
    ):
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            return data
    return None


def check_floorplan(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，场景平面图检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    counts: Dict[str, int] = defaultdict(int)
    clip_texts: List[Tuple[str, str, str]] = []
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        loc = _loc_of(clip, text)
        if loc:
            counts[loc] += 1
            clip_texts.append((label, loc, text))
    fp = _floorplan_data(root)
    if fp is None:
        for loc, n in counts.items():
            if n >= 3:
                res["findings"].append(_row(
                    "warn",
                    f"场景 {loc} 本集出现 {n} 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。",
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json", "设定库/scene_floorplan.json"),
                ))
        return res
    scenes = fp.get("scenes") if isinstance(fp.get("scenes"), dict) else fp
    for label, loc, text in clip_texts:
        spec = scenes.get(loc) if isinstance(scenes, dict) else None
        if not isinstance(spec, dict):
            continue
        zones = spec.get("zones") or spec.get("区域") or []
        if isinstance(zones, dict):
            zones = list(zones.keys())
        if zones:
            zone_tokens = [str(z) for z in zones if z]
            if not any(z in text for z in zone_tokens) and not _is_exempt_view(text):
                res["findings"].append(_row(
                    "warn",
                    f"{loc} 有平面图区域 {zone_tokens[:5]}，但 {label} 未声明角色/机位所在区域；空间连续性难复核。",
                    shot=label,
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json", "设定库/scene_floorplan.json"),
                ))
    return res


def _finding_files(root: str, ep: str) -> List[str]:
    import glob
    paths = [
        os.path.join(root, "生产数据", f"consistency_findings_{ep}.json"),
        os.path.join(root, "生产数据", f"review_ui_findings_{ep}.json"),
    ]
    paths.extend(glob.glob(os.path.join(root, "生产数据", f"gate_findings_*_{ep}.json")))
    return [p for p in paths if os.path.isfile(p)]


def _active_finding_rows(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("findings") or data.get("details") or data.get("items") or []
    else:
        raw = data
    rows = []
    for item in _as_list(raw):
        if isinstance(item, dict) and str(item.get("verdict") or item.get("severity") or "").lower() in {"block", "warn", "red", "yellow"}:
            rows.append(item)
    return rows


def _jsonl_rows(path: str) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
    except FileNotFoundError:
        pass
    return rows


def _calibration_path(root: str) -> str:
    for rel in (
        os.path.join("生产数据", "consistency_calibration.jsonl"),
        os.path.join("设定库", "consistency_calibration.jsonl"),
    ):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return os.path.join(root, "生产数据", "consistency_calibration.jsonl")


def _threshold_path(root: str) -> str:
    for rel in (
        os.path.join("生产数据", "consistency_threshold_recommendations.json"),
        os.path.join("设定库", "consistency_threshold_recommendations.json"),
        os.path.join("生产数据", "consistency_thresholds.json"),
        os.path.join("设定库", "consistency_thresholds.json"),
    ):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return ""


def _row_has_threshold_advice(row: Mapping[str, Any]) -> bool:
    return any(row.get(key) not in (None, "", [], {}) for key in (
        "threshold_recommendation",
        "threshold_delta",
        "new_threshold",
        "suggested_threshold",
        "detector_patch",
        "rule_patch",
    ))


def _calibration_threshold_needs(rows: Sequence[Mapping[str, Any]]) -> List[Tuple[str, int, int]]:
    by_dim: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        label = str(row.get("label") or row.get("review_label") or "").strip()
        dim = str(row.get("dimension") or row.get("dim") or "(unknown)").strip()
        if label:
            by_dim[dim][label] += 1
    needs: List[Tuple[str, int, int]] = []
    for dim, counts in by_dim.items():
        false_positive = counts.get("false_positive", 0)
        missed = counts.get("missed_by_machine", 0)
        if false_positive >= 2 or missed >= 1:
            needs.append((dim, false_positive, missed))
    return needs


def check_review_calibration(root: str, ep: str) -> dict:
    """把一次性人审签收沉淀为全局校准集，供后续误报/漏报回归使用。"""
    res = {"available": True, "findings": [], "notes": []}
    finding_rows: List[dict] = []
    for path in _finding_files(root, ep):
        finding_rows.extend(_active_finding_rows(_load_json(path)))
    signoff_data, signoff_rel = _load_first_json(root, (
        os.path.join("生产数据", f"human_review_signoff_{ep}.json"),
        os.path.join("生产数据", f"review_signoff_{ep}.json"),
        os.path.join("质检", f"review_signoff_{ep}.json"),
    ))
    overrides = [
        e for e in _load_events(root)
        if str(e.get("episode") or "") == ep
        and (
            str(e.get("event") or "") in {"human_override", "review_signoff", "consistency_label"}
            or isinstance(e.get("review"), Mapping)
        )
    ]
    if not finding_rows and signoff_data is None and not overrides:
        res["notes"].append("未检测到人审签收/覆盖记录，CAL 跳过。")
        return res
    cal_path = _calibration_path(root)
    rows = _jsonl_rows(cal_path)
    if not rows:
        res["findings"].append(_row(
            "warn",
            "检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局校准集。",
            stage="review",
            artifacts=(os.path.relpath(cal_path, root), signoff_rel or "生产数据/consistency_findings_*.json"),
        ))
        return res
    covered_hashes = {str(r.get("finding_hash") or r.get("source_hash") or "") for r in rows if r.get("finding_hash") or r.get("source_hash")}
    for row in rows:
        label = str(row.get("label") or row.get("review_label") or "").strip()
        missing = []
        if label not in REVIEW_LABELS:
            missing.append("label")
        if label in {"false_positive", "accepted_intentional", "missed_by_machine"} and not row.get("reviewer"):
            missing.append("reviewer")
        if label in {"false_positive", "accepted_intentional", "missed_by_machine"} and not row.get("reason"):
            missing.append("reason")
        if not (row.get("dimension") or row.get("dim")):
            missing.append("dimension")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"校准集条目缺字段：{', '.join(missing)}。",
                stage="review",
                artifacts=(os.path.relpath(cal_path, root),),
            ))
    reviewed = [r for r in finding_rows if r.get("review_label") or r.get("human_verdict") or r.get("accepted_intentional")]
    for row in reviewed:
        h = str(row.get("finding_hash") or _finding_hash(row))
        if h not in covered_hashes:
            res["findings"].append(_row(
                "warn",
                f"已人审标注的 finding 未进入校准集：hash={h}。",
                stage="review",
                artifacts=(os.path.relpath(cal_path, root),),
            ))
    threshold_needs = _calibration_threshold_needs(rows)
    if threshold_needs:
        threshold_path = _threshold_path(root)
        embedded_advice = any(_row_has_threshold_advice(row) for row in rows)
        summary = "；".join(
            f"{dim}: false_positive={fp}, missed_by_machine={missed}"
            for dim, fp, missed in threshold_needs[:6]
        )
        if not threshold_path and not embedded_advice:
            res["findings"].append(_row(
                "warn",
                "校准集已有稳定误报/漏报样本，但缺 consistency_thresholds 或 threshold_recommendations；"
                f"阈值/规则没有形成可复跑学习闭环（{summary}）。可运行 calibrate_thresholds.py --write 生成建议。",
                stage="review",
                artifacts=(os.path.relpath(cal_path, root), "生产数据/consistency_threshold_recommendations.json"),
            ))
        else:
            rel = os.path.relpath(threshold_path, root) if threshold_path else os.path.relpath(cal_path, root)
            res["notes"].append(f"CAL 阈值学习样本：{summary}；已检测到阈值建议/配置 {rel}。")
    return res


def _episode_count(root: str) -> int:
    import glob
    return len([p for p in glob.glob(os.path.join(root, "脚本", "第*集")) if os.path.isdir(p)])


def _probe_pack(root: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", "consistency_probe_pack.json"),
        os.path.join("设定库", "consistency_probe_pack.json"),
        os.path.join("生产数据", "probe_pack", "consistency_probe_pack.json"),
    ))


def _probe_route_recommendations(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"video_route_recommendations_{ep}.json"),
        os.path.join("生产数据", "video_route_recommendations.json"),
        os.path.join("设定库", "video_route_recommendations.json"),
    ))


def _probe_scenario_name(row: Mapping[str, Any]) -> str:
    return str(row.get("scenario") or row.get("name") or row.get("id") or "").strip()


def _backend_score_value(row: Mapping[str, Any]) -> Optional[float]:
    for key in ("consistency_score", "score", "avg_score", "mean_score", "pass_rate", "quality_score"):
        num = _num(row.get(key))
        if num is not None:
            return num
    return None


def _backend_name(value: Mapping[str, Any]) -> str:
    for key in ("backend", "provider", "model", "model_id", "primary_backend", "selected_backend", "name"):
        text = str(value.get(key) or "").strip()
        if text:
            return text
    return ""


def _looks_like_backend_score(value: Mapping[str, Any]) -> bool:
    return bool(_backend_name(value)) or any(key in value for key in (
        "score", "consistency_score", "avg_score", "pass_rate", "passed", "verdict", "status",
    ))


def _collect_backend_scores(value: Any, *, scenario: str = "", backend: str = "") -> List[dict]:
    rows: List[dict] = []
    if isinstance(value, list):
        for item in value:
            rows.extend(_collect_backend_scores(item, scenario=scenario, backend=backend))
        return rows
    if not isinstance(value, dict):
        return rows
    current_scenario = str(value.get("scenario") or value.get("name") or value.get("id") or scenario or "").strip()
    current_backend = _backend_name(value) or backend
    if _looks_like_backend_score(value) and current_backend:
        row = dict(value)
        row.setdefault("scenario", current_scenario)
        row.setdefault("backend", current_backend)
        rows.append(row)
    for key, child in value.items():
        if key in {"scenario", "name", "id", "backend", "provider", "model", "model_id"}:
            continue
        if isinstance(child, dict):
            next_scenario = current_scenario
            next_backend = current_backend
            if key not in {"backend_scores", "backend_results", "scores", "results", "route_scores"}:
                if _looks_like_backend_score(child):
                    next_backend = key
                elif not next_scenario:
                    next_scenario = key
            rows.extend(_collect_backend_scores(child, scenario=next_scenario, backend=next_backend))
        elif isinstance(child, list):
            next_scenario = current_scenario if key in {"backend_scores", "backend_results", "scores", "results", "route_scores"} else (current_scenario or key)
            rows.extend(_collect_backend_scores(child, scenario=next_scenario, backend=current_backend))
    return rows


def _probe_backend_scores(data: Any, scenarios: Sequence[Mapping[str, Any]]) -> List[dict]:
    rows: List[dict] = []
    if isinstance(data, dict):
        for key in ("backend_scores", "backend_results", "route_scores", "model_scores", "results"):
            if key in data:
                rows.extend(_collect_backend_scores(data.get(key)))
    for scenario in scenarios:
        name = _probe_scenario_name(scenario)
        for key in ("backend_scores", "backend_results", "route_scores", "model_scores", "results"):
            if key in scenario:
                rows.extend(_collect_backend_scores(scenario.get(key), scenario=name))
    dedup: List[dict] = []
    seen = set()
    for row in rows:
        sig = (
            str(row.get("scenario") or ""),
            str(row.get("backend") or ""),
            str(_backend_score_value(row)),
            str(row.get("verdict") or row.get("status") or ""),
        )
        if sig in seen:
            continue
        seen.add(sig)
        dedup.append(row)
    return dedup


def _route_primary_backends(routes: Mapping[str, Mapping[str, Any]]) -> List[str]:
    names: List[str] = []
    for route in routes.values():
        if not isinstance(route, Mapping):
            continue
        name = _backend_name(route)
        if name:
            names.append(name)
    return _unique(names)


def _backend_match(a: str, b: str) -> bool:
    aa = re.sub(r"\s+", "", str(a or "").lower())
    bb = re.sub(r"\s+", "", str(b or "").lower())
    return bool(aa and bb and (aa in bb or bb in aa))


def check_probe_pack(root: str, ep: str) -> dict:
    """项目级哨兵小样：用固定 probe 保护后端/提示词/模板升级不把一致性打穿。"""
    res = {"available": True, "findings": [], "notes": []}
    data, rel = _probe_pack(root)
    should_have = _episode_count(root) >= 2 or bool(_load_events(root)) or bool(_existing_media(root, ep))
    if data is None:
        if should_have:
            res["findings"].append(_row(
                "warn",
                "项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。",
                stage="review",
                artifacts=("生产数据/consistency_probe_pack.json", "设定库/consistency_probe_pack.json"),
            ))
        else:
            res["notes"].append("项目尚未形成多集/媒体产物，PROBE 暂不强制。")
        return res
    scenarios = _probe_rows(data)
    names = {
        str(s.get("scenario") or s.get("name") or s.get("id") or "").strip()
        for s in scenarios
        if isinstance(s, dict)
    }
    missing = [name for name in PROBE_SCENARIOS if name not in names]
    if missing:
        res["findings"].append(_row(
            "warn",
            f"consistency_probe_pack 缺哨兵场景：{', '.join(missing)}。",
            stage="review",
            artifacts=(rel,),
        ))
    for row in scenarios:
        verdict = str(row.get("verdict") or row.get("status") or row.get("result") or "").lower()
        name = str(row.get("scenario") or row.get("name") or row.get("id") or "")
        if verdict in {"block", "fail", "failed", "red"}:
            res["findings"].append(_row(
                "block",
                f"一致性 probe 场景 {name or '(unknown)'} 未通过；升级/发布前需先修复哨兵小样。",
                stage="review",
                artifacts=(rel,),
            ))
        if not (row.get("input_fingerprint") or row.get("recipe_hash") or row.get("baseline_hash")):
            res["findings"].append(_row(
                "warn",
                f"一致性 probe 场景 {name or '(unknown)'} 缺 baseline/input 指纹，无法做升级前后对比。",
                stage="review",
                artifacts=(rel,),
            ))
    if isinstance(data, dict) and not (data.get("latest_result") or data.get("run_id") or data.get("last_run_at")):
        res["findings"].append(_row(
            "warn",
            "consistency_probe_pack 缺 latest_result/run_id；无法确认当前后端组合是否跑过哨兵。",
            stage="review",
            artifacts=(rel,),
        ))
    routes = _load_routes(root, ep)
    primary_backends = _route_primary_backends(routes)
    backend_rows = _probe_backend_scores(data, scenarios)
    if primary_backends and not backend_rows:
        res["findings"].append(_row(
            "warn",
            "项目已有视频模型路由，但 consistency_probe_pack 缺 backend_scores/backend_results；"
            "probe 仍停留在场景小样，未形成后端选择基准。",
            stage="review",
            artifacts=(rel, f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/video_model_routes.json"),
        ))
    elif backend_rows:
        measured_backends = _unique(str(row.get("backend") or "") for row in backend_rows)
        for backend in primary_backends:
            if not any(_backend_match(backend, measured) for measured in measured_backends):
                res["findings"].append(_row(
                    "warn",
                    f"当前 route.primary_backend={backend} 未出现在 probe backend_scores；路由没有哨兵基准兜底。",
                    stage="review",
                    artifacts=(rel, f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/video_model_routes.json"),
                ))
        scored: Dict[str, List[float]] = defaultdict(list)
        for row in backend_rows:
            backend = str(row.get("backend") or "").strip()
            score = _backend_score_value(row)
            if backend and score is not None:
                scored[backend].append(score)
        averages = {backend: sum(values) / len(values) for backend, values in scored.items() if values}
        if averages:
            best_backend, best_score = max(averages.items(), key=lambda item: item[1])
            allowed_delta = 0.05
            if isinstance(data, dict):
                allowed_delta = _num(data.get("route_score_delta_tolerance")) or allowed_delta
            route_blob = _json_text(routes)
            route_rec, route_rec_rel = _probe_route_recommendations(root, ep)
            has_selection_reason = bool(isinstance(data, dict) and (
                data.get("route_recommendations") or data.get("selected_backend") or data.get("selection_reason") or data.get("fallback_reason")
            )) or bool(route_rec) or any(token in route_blob for token in ("selection_reason", "fallback_reason", "fallback_allowed", "route_recommendation"))
            for backend in primary_backends:
                matched = next((name for name in averages if _backend_match(backend, name)), "")
                if not matched:
                    continue
                delta = best_score - averages[matched]
                if best_backend != matched and delta > allowed_delta and not has_selection_reason:
                    res["findings"].append(_row(
                        "warn",
                        f"probe benchmark 显示 {best_backend} 平均一致性分 {best_score:.3f} 高于当前路由 {backend} "
                        f"{delta:.3f}，但缺 selection_reason/fallback_reason；确认是否为成本/速度的显式取舍。"
                        "可运行 probe_route_recommend.py --write 生成路由建议。",
                        stage="review",
                        artifacts=(rel, f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/video_model_routes.json", route_rec_rel or f"生产数据/video_route_recommendations_{ep}.json"),
                    ))
        failing_backend = [
            row for row in backend_rows
            if str(row.get("verdict") or row.get("status") or row.get("result") or "").lower() in {"block", "fail", "failed", "red"}
        ]
        for row in failing_backend[:8]:
            res["findings"].append(_row(
                "block",
                f"probe 后端基准未通过：scenario={row.get('scenario') or '(unknown)'} backend={row.get('backend') or '(unknown)'}。",
                stage="review",
                artifacts=(rel,),
            ))
    return res


def check_cost_route(root: str, ep: str) -> dict:
    res = {"available": True, "findings": [], "notes": []}
    events = [e for e in _load_events(root) if str(e.get("episode") or "") == ep and str(e.get("event") or "") in {"generation", "redraw"}]
    by_asset: Dict[str, List[dict]] = defaultdict(list)
    for e in events:
        asset = _event_asset(e)
        if asset:
            by_asset[asset].append(e)
        if e.get("event") in {"generation", "redraw"} and not isinstance(e.get("cost"), Mapping):
            res["findings"].append(_row(
                "warn",
                f"{asset or '(unknown asset)'} 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。",
                stage=str(e.get("stage") or "review"),
                artifacts=("生产数据/production_events.jsonl",),
            ))
    for asset, rows in by_asset.items():
        providers = _unique(_event_provider(e) for e in rows)
        if len(providers) > 1:
            allowed = any(str((e.get("generation") or {}).get("redraw_category") or "").strip() in {"backend_migration", "face_consistency"} for e in rows)
            res["findings"].append(_row(
                "warn" if allowed else "block",
                f"{asset} 同一资产生成跨 provider：{providers}；未声明 backend_migration 会造成一致性和成本归因混乱。",
                stage="image" if asset.lower().endswith(".png") else "video",
                artifacts=("生产数据/production_events.jsonl",),
            ))
        passes = [e for e in rows if str((e.get("generation") or {}).get("status") or "").lower() == "pass"]
        if len(passes) > 1 and not any((e.get("generation") or {}).get("redraw_reason") for e in rows):
            res["findings"].append(_row(
                "warn",
                f"{asset} 有多次 pass 记录但缺 redraw_reason/验收选择原因；后续无法判断哪版是正片依据。",
                stage="review",
                artifacts=("生产数据/production_events.jsonl",),
            ))
    routes = _load_routes(root, ep)
    if routes:
        for asset, rows in by_asset.items():
            clip = _clip_num(os.path.splitext(os.path.basename(asset))[0])
            route = routes.get(clip)
            if not route:
                continue
            primary = str(route.get("primary_backend") or "").lower()
            provider = _event_provider(rows[-1]).lower()
            if primary and provider and primary not in provider and provider not in primary:
                res["findings"].append(_row(
                    "warn",
                    f"{clip} 最新生成 provider={provider} 与 route.primary_backend={primary} 不一致；确认是合法 fallback 还是路由漂移。",
                    shot=clip,
                    stage="video_prompt",
                    artifacts=(f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/production_events.jsonl"),
                ))
    return res


def analyze(root: str, ep: str) -> dict:
    sections = {
        "物件常驻(O3)": check_object_permanence(root, ep),
        "持有账本(POS)": check_possession_ledger(root, ep),
        "视线状态回读(X2)": check_axis_state_readback(root, ep),
        "状态转场视频证据(ST1)": check_state_transition_verification(root, ep),
        "交互接触(I1)": check_interaction_graph(root, ep),
        "结构化交互图谱(I2)": check_interaction_schema(root, ep),
        "成片统一(C1)": check_final_composite(root, ep),
        "成片时间线探针(FT1)": check_final_timeline_probe(root, ep),
        "生成配方(RCP)": check_generation_recipe(root, ep),
        "强配方Schema(RCP2)": check_recipe_schema(root, ep),
        "系列包装(PKG)": check_series_packaging(root, ep),
        "台词语域(D1)": check_dialogue_register(root, ep),
        "场景平面(FP1)": check_floorplan(root, ep),
        "成本路由(K1)": check_cost_route(root, ep),
        "人审校准集(CAL)": check_review_calibration(root, ep),
        "一致性探针包(PROBE)": check_probe_pack(root, ep),
    }
    return {"available": True, "sections": sections}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write-recipe", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.write_recipe:
        res["recipe_path"] = write_recipe_ledger(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for dim, sec in res["sections"].items():
            active = [r for r in sec.get("findings", []) if r.get("verdict") in {"block", "warn"}]
            print(f"{dim}: {len(active)} finding(s)")
            for row in active[:5]:
                print(f"  - {row.get('verdict')} {row.get('message')}")
    total_block = sum(1 for sec in res["sections"].values() for r in sec.get("findings", []) if r.get("verdict") == "block")
    return 1 if total_block else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
