#!/usr/bin/env python3
"""reference_pack.py — 无成本图片增强参考档规划器。

不考虑生图成本时，出图阶段最该增加的是“可被后端真实消费的参考资产”，而不是更多空泛 prompt。
本脚本读取 identity_registry / asset_registry / storyboard，生成
`生产数据/no_cost_reference_pack_第N集.json/md`：角色多角度、表情、动作姿态、场景 plates、道具/VFX sheets、
多人同框区域构建所需底板/遮罩/槽位，都列成明确缺口和目标路径。
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_no_cost_reference_pack"
BASE_VIEW_KEYS = ("front", "three_quarter", "side", "rear_three_quarter", "back")
BODY_VIEW_KEYS = ("half_body", "full_body")
EXPRESSION_MIN_CORE = 5
EXPRESSION_MIN_NORMAL = 3
ACTION_WORDS = re.compile(r"(打斗|追逐|飞行|法术|拥抱|拉扯|跪|拔剑|御剑|冲刺|受击|动作|fight|chase|action)")
CORE_RE = re.compile(r"全篇|全程|长线|核心|主角|女主|男主|主反派|常驻")
ASSET_PREFIXES = ("LOC_", "PROP_", "WEAPON_", "OUTFIT_", "VFX_")


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def _ref_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("path") or "").strip()
    return ""


def _ready(value: Any) -> bool:
    path = _ref_path(value)
    if not path:
        return False
    if isinstance(value, Mapping):
        return str(value.get("status") or "").strip() in {"ready", "registered", "review_pending"}
    return True


def _list_refs(value: Any) -> List[str]:
    if isinstance(value, list):
        return [p for p in (_ref_path(v) for v in value) if p]
    return []


def _ready_ref_path(value: Any) -> str:
    return _ref_path(value) if _ready(value) else ""


def _list_ready_refs(value: Any) -> List[str]:
    if isinstance(value, list):
        return [p for item in value if (p := _ready_ref_path(item))]
    return []


def _ref_items(value: Any) -> List[Any]:
    if isinstance(value, list):
        return [item for item in value if _ref_path(item)]
    return [value] if _ref_path(value) else []


def _preferred_ref(*values: Any) -> Tuple[str, bool, Any]:
    """Choose a registered ready ref, otherwise preserve its planned path."""
    items: List[Any] = []
    for value in values:
        items.extend(_ref_items(value))
    if not items:
        return "", False, None
    selected = next((item for item in items if _ready(item)), items[0])
    return _ref_path(selected), _ready(selected), selected


def _expression_capacity(item: Any) -> int:
    if not _ready(item):
        return 0
    path = _ref_path(item)
    layout = str(item.get("layout") or "") if isinstance(item, Mapping) else ""
    emotion = str(item.get("emotion") or "") if isinstance(item, Mapping) else ""
    if "two_by_three_expression_sheet" in layout or "六联表" in path or "六联表" in emotion:
        return 6
    return 1


def _first_ready_base_view(atlas: Mapping[str, Any], key: str) -> str:
    base = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    item = base.get(key) if isinstance(base, Mapping) else None
    return _ref_path(item) if _ready(item) else ""


def _forms(root: Path) -> List[Dict[str, Any]]:
    data = load_json(root / "出图" / "共享" / "identity_registry.json")
    out: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return out
    for char in data.get("characters") or []:
        if not isinstance(char, dict):
            continue
        core = bool(CORE_RE.search(flatten({k: char.get(k) for k in ("name", "scope", "tier", "role")})))
        for form in char.get("forms") or []:
            if not isinstance(form, dict):
                continue
            out.append({
                "character_id": char.get("id"),
                "name": char.get("name"),
                "form": form.get("form") or "常态",
                "core": core,
                "library_tier": (
                    form.get("library_tier")
                    or char.get("library_tier")
                    or (form.get("reference_atlas") or {}).get("build_tier")
                ),
                "reference_group": form.get("reference_group") or {},
                "reference_atlas": form.get("reference_atlas") or {},
                "performance_signature": form.get("performance_signature") or char.get("performance_signature"),
            })
    return out


def _assets(root: Path) -> List[Dict[str, Any]]:
    data = load_json(root / "出图" / "共享" / "asset_registry.json")
    raw: Any = []
    if isinstance(data, dict):
        raw = data.get("assets") or data.get("items") or []
        if isinstance(raw, dict):
            raw = [{**(v if isinstance(v, dict) else {}), "id": k} for k, v in raw.items()]
    elif isinstance(data, list):
        raw = data
    return [a for a in raw if isinstance(a, dict)]


def _storyboard(root: Path, ep: str) -> Tuple[List[dict], str]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    clips = [c for c in clips or [] if isinstance(c, dict)]
    return clips, flatten(clips)


def _used_ids(clips: Sequence[Mapping[str, Any]], blob: str) -> Tuple[set, set]:
    """Collect IDs from storyboard schema fields, never from prose blobs.

    IDs may legitimately contain Chinese (for example ``VFX_系统面板``), so a
    permissive prose regex greedily turns ``VFX_01退出清晰画面`` or
    ``CHAR_01与CHAR_02连线`` into fake assets.  Stage 2 already supplies structured
    entity fields; those are the only safe truth here.
    """
    del blob  # compatibility with the existing call signature
    chars: set = set()
    assets: set = set()

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if not text or any(ch.isspace() for ch in text):
            return
        if text.startswith("CHAR_") or text.startswith("BEAST_"):
            chars.add(text)
        elif text.startswith(ASSET_PREFIXES):
            assets.add(text)

    for clip in clips:
        for cid in clip.get("character_ids") or []:
            add(cid)
        for oid in clip.get("object_ids") or []:
            add(oid)
        add(clip.get("location_id"))
        schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
        for key in ("characters", "objects", "locations", "required_presence", "offscreen_presence", "forbidden_presence"):
            for value in schedule.get(key) or []:
                add(value)
    return chars, assets


def _expected_character_refs(form: Mapping[str, Any], action_needed: bool) -> List[Dict[str, Any]]:
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    cid = str(form.get("character_id") or "")
    form_name = str(form.get("form") or "常态")
    targets: List[Dict[str, Any]] = []

    def add(slot: str, ready: bool, path: str, reason: str) -> None:
        targets.append({
            "scope": "character",
            "owner": f"{cid}/{form_name}",
            "slot": slot,
            "status": "ready" if ready else "planned",
            "path": path or f"出图/共享/图片/定妆_{cid}_{form_name}_{slot}.png",
            "reason": reason,
        })

    for key in BASE_VIEW_KEYS:
        base = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
        path, ready, _item = _preferred_ref(base.get(key), rg.get(key))
        add(key, ready, path, "基础多角度视图；核心档不省正/前3/4/侧/后3/4/背。")
    turnaround_path, turnaround_ready, _turnaround_item = _preferred_ref(rg.get("turnaround"))
    if form.get("core") or form.get("library_tier") == "core_full" or turnaround_path:
        add(
            "turnaround",
            turnaround_ready,
            turnaround_path,
            "核心档五角 turnaround 人审总览：正面/前3/4/侧面/后3/4/背面同身高同景别对齐。",
        )
    body_values: List[Any] = []
    base = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    for key in BODY_VIEW_KEYS:
        body_values.extend((base.get(key), rg.get(key)))
    body_path, body_ready, _body_item = _preferred_ref(*body_values)
    add("half_body_or_full_body", body_ready, body_path, "服装/体态参考，防止镜头内换身材或换衣。")
    face_path, face_ready, _face_item = _preferred_ref(
        rg.get("face_anchor_refs"), atlas.get("face_anchor_refs")
    )
    add("face_anchor_refs", face_ready, face_path, "脸部特写锚，近景/反打/表情镜必用。")
    expression_items = _ref_items(rg.get("expressions")) or _ref_items(atlas.get("expression_refs"))
    expression_path, _expression_ready, _expression_item = _preferred_ref(expression_items)
    expression_capacity = sum(_expression_capacity(item) for item in expression_items)
    expr_min = EXPRESSION_MIN_CORE if form.get("core") else EXPRESSION_MIN_NORMAL
    add("expression_bank", expression_capacity >= expr_min, expression_path,
        f"同源情绪表情库至少 {expr_min} 档：中性/喜/怒/悲/惊；大表情近景首尾帧只插值。")
    if action_needed:
        action_path, action_ready, _action_item = _preferred_ref(rg.get("action_refs"), atlas.get("action_refs"))
        add("action_pose_pack", action_ready, action_path,
            "动作/打斗/拥抱/拉扯姿态参考；避免视频前首帧姿态不可读。")
    if not form.get("performance_signature"):
        add("performance_signature", False, "", "登记微表情/眼神/站姿/惯用手势/说话节奏，防演法漂。")
    return targets


def _expected_asset_refs(asset: Mapping[str, Any], used: bool) -> List[Dict[str, Any]]:
    aid = str(asset.get("id") or asset.get("asset_id") or "")
    typ = str(asset.get("type") or "")
    rg = asset.get("reference_group") if isinstance(asset.get("reference_group"), Mapping) else {}
    targets: List[Dict[str, Any]] = []

    def add(slot: str, ready: bool, path: str, reason: str) -> None:
        targets.append({
            "scope": "asset",
            "owner": aid,
            "slot": slot,
            "status": "ready" if ready else "planned",
            "path": path or f"出图/共享/图片/定妆_{aid}_{slot}.png",
            "reason": reason,
        })

    if not used:
        return targets
    if aid.startswith("LOC_") or typ in {"location", "scene", "场景"}:
        scene_sources = {
            "wide_plate": (rg.get("wide_plate"), rg.get("front"), rg.get("primary")),
            "reverse_angle": (rg.get("reverse_angle"), rg.get("reverse")),
            "empty_plate": (rg.get("empty_plate"),),
            "lighting_plate": (rg.get("lighting_plate"),),
        }
        for slot, values in scene_sources.items():
            path, ready, _item = _preferred_ref(*values)
            add(slot, ready, path,
                "场景 plate / 反打 / 空底板 / 光位锚；多人分区构建先用 empty_plate。")
        # 布局图 spatial_map + scene_atlas 多视角 base_views（此前声明却喂给零代码的死字段）——纳入参考清单，
        # 锁门窗朝向/floor_plan 几何 + 同一空间换机位一致（生成侧场景锚定·详见 scene_reference_planner.py）。
        if _ready_ref_path(rg.get("spatial_map")):
            add("spatial_map", True, _ready_ref_path(rg.get("spatial_map")),
                "布局图：锁门窗位置/floor_plan 几何，治反打把房间拍成另一个房间。")
        atlas = asset.get("scene_atlas") if isinstance(asset.get("scene_atlas"), Mapping) else {}
        base_views = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
        for bv_key in ("reverse", "side"):
            bv = _ready_ref_path(base_views.get(bv_key))
            if bv:
                add(f"base_view_{bv_key}", True, bv, f"scene_atlas {bv_key} 视角：锁同一空间换机位的一致性。")
    elif aid.startswith(("PROP_", "WEAPON_", "VFX_", "OUTFIT_")):
        asset_sources = {
            "primary": (rg.get("primary"),),
            "scale_reference": (rg.get("scale_reference"), rg.get("scale_ref")),
            "detail_closeup": (rg.get("detail_closeup"),),
        }
        for slot, values in asset_sources.items():
            path, ready, _item = _preferred_ref(*values)
            add(slot, ready, path,
                "道具/武器/VFX sheet，锁尺度、材质、细节与禁漂项。")
    return targets


def build_pack(root: Path, ep: str) -> Dict[str, Any]:
    clips, blob = _storyboard(root, ep)
    used_chars, used_assets = _used_ids(clips, blob)
    action_needed = bool(ACTION_WORDS.search(blob))
    targets: List[Dict[str, Any]] = []
    notes: List[str] = []
    for form in _forms(root):
        if not used_chars or str(form.get("character_id")) in used_chars or form.get("core"):
            targets.extend(_expected_character_refs(form, action_needed))
    for asset in _assets(root):
        aid = str(asset.get("id") or asset.get("asset_id") or "")
        targets.extend(_expected_asset_refs(asset, aid in used_assets))
    multi_clips = []
    for i, clip in enumerate(clips, 1):
        cids = {str(value).strip() for value in (clip.get("character_ids") or []) if str(value).strip()}
        if len(cids) >= 2:
            multi_clips.append(str(clip.get("id") or clip.get("label") or f"Clip_{i:02d}"))
    for clip_id in multi_clips:
        targets.append({
            "scope": "multi_subject",
            "owner": clip_id,
            "slot": "regional_construct_plate",
            "status": "planned",
            "path": f"出图/{ep}/区域构建/{clip_id}/empty_plate.png",
            "reason": "多人同框默认空场景底板 + 区域 inpaint / regional-prompt 分区构建。"
        })
        targets.append({
            "scope": "multi_subject",
            "owner": clip_id,
            "slot": "region_masks",
            "status": "planned",
            "path": f"出图/{ep}/区域构建/{clip_id}/masks.json",
            "reason": "逐主体 LEFT/RIGHT/FOREGROUND/BACKGROUND 槽位遮罩与构图绑定。"
        })
    missing = [t for t in targets if t.get("status") != "ready"]
    if not clips:
        notes.append("缺 storyboard clips[]；只能基于 registry 生成剧级参考包。")
    return {
        "kind": KIND,
        "episode": ep,
        "clip_count": len(clips),
        "used_characters": sorted(used_chars),
        "used_assets": sorted(used_assets),
        "multi_subject_clips": multi_clips,
        "targets": targets,
        "summary": {
            "total": len(targets),
            "ready": len(targets) - len(missing),
            "planned": len(missing),
            "character_targets": sum(1 for t in targets if t.get("scope") == "character"),
            "asset_targets": sum(1 for t in targets if t.get("scope") == "asset"),
            "multi_subject_targets": sum(1 for t in targets if t.get("scope") == "multi_subject"),
        },
        "notes": notes,
    }


def render_md(pack: Mapping[str, Any]) -> str:
    s = pack.get("summary") or {}
    lines = [
        "# 无成本图片增强参考档",
        "",
        f"- episode: {pack.get('episode')}",
        f"- total: {s.get('total')} ｜ ready: {s.get('ready')} ｜ planned: {s.get('planned')}",
        f"- multi_subject_clips: {'、'.join(pack.get('multi_subject_clips') or []) or '-'}",
        "",
        "| Scope | Owner | Slot | Status | Path | Reason |",
        "|---|---|---|---|---|---|",
    ]
    for t in pack.get("targets") or []:
        lines.append(
            f"| {t.get('scope')} | {t.get('owner')} | {t.get('slot')} | {t.get('status')} | "
            f"{t.get('path')} | {t.get('reason')} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, pack: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"no_cost_reference_pack_{ep}.json"
    mp = out / f"no_cost_reference_pack_{ep}.md"
    tmp = jp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, jp)
    tmp_md = mp.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(pack), encoding="utf-8")
    os.replace(tmp_md, mp)
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 无成本图片增强参考档规划器")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="有 planned 参考时退出码 1")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ns.episode if ns.episode.startswith("第") else f"第{ns.episode}集"
    pack = build_pack(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, pack)
        pack["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print(render_md(pack))
    planned = int((pack.get("summary") or {}).get("planned") or 0)
    return 1 if (ns.strict and planned) else 0


if __name__ == "__main__":
    raise SystemExit(main())
