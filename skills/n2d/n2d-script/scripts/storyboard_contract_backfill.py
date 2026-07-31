#!/usr/bin/env python3
"""Backfill older storyboard.json files to the current production gate schema.

This script only fills deterministic handoff contracts that can be inferred
from an existing storyboard. It does not rewrite plot beats or invent new shots.

Usage:
  python3 storyboard_contract_backfill.py <作品根> 第N集 --write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXPRESSION_SPAN_MAP = {"高": "大", "强": "大", "低": "微"}
N2D_LIB = Path(__file__).resolve().parents[2] / "_lib"
if N2D_LIB.exists() and str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
try:
    from n2d_contract import TEMPLATE_BASE_FIELDS, spectacle_required_fields  # type: ignore
except Exception:  # pragma: no cover - local fallback keeps the script usable in partial checkouts.
    TEMPLATE_BASE_FIELDS = ("template_id", "beats", "blocking", "camera_rule", "continuity_must", "negative")

    def spectacle_required_fields(kind: str) -> tuple[str, ...]:
        if kind == "fight_exchange":
            return TEMPLATE_BASE_FIELDS + (
                "attack_path",
                "impact_frame",
                "action_scope",
                "contact_points",
                "force_direction",
                "screen_direction",
                "speed_curve",
                "spatial_path",
                "camera_path",
                "readability_beats",
                "recovery_beat",
                "degrade_plan",
                "keyframe_plan",
                "post_cue_points",
                "physics_guard",
            )
        return ()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clean_token(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("id", "asset_id", "character_id", "object_id", "prop_id", "name", "label"):
            token = str(value.get(key) or "").strip()
            if token:
                return token
        return ""
    return str(value or "").strip()


def entity_key(token: str) -> str:
    return str(token or "").strip().split("/", 1)[0].strip()


def unique(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        token = clean_token(value)
        if token and token not in out:
            out.append(token)
    return out


def nonempty(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def first_text(*values: Any, default: str = "") -> str:
    for value in values:
        token = clean_token(value)
        if token:
            return token
    return default


def shot_parts(clip: Mapping[str, Any], *keys: str) -> list[str]:
    out: list[str] = []
    for shot in as_list(clip.get("shots")):
        if isinstance(shot, Mapping):
            for key in keys:
                token = clean_token(shot.get(key))
                if token and token not in out:
                    out.append(token)
        else:
            token = clean_token(shot)
            if token and token not in out:
                out.append(token)
    return out


def concise(values: Iterable[str], fallback: str, limit: int = 4) -> list[str]:
    out = [str(v).strip() for v in values if str(v).strip()]
    return out[:limit] if out else [fallback]


def derived_beats(clip: Mapping[str, Any]) -> list[str]:
    contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), Mapping) else {}
    existing = unique(as_list(contract.get("beats") if isinstance(contract, Mapping) else None))
    if existing:
        return existing
    shot_desc = shot_parts(clip, "desc", "description", "action", "visual")
    return concise(
        [
            first_text(clip.get("label"), clip.get("dramatic_function"), clip.get("story_function")),
            *shot_desc,
        ],
        fallback="按本镜 label/continuity 完成起幅、推进、尾帧交接",
    )


def derived_camera_rule(clip: Mapping[str, Any], cont: Mapping[str, Any]) -> str:
    cameras = shot_parts(clip, "camera", "lens", "composition")
    if cameras:
        return "；".join(cameras[:3])
    return first_text(cont.get("shot_size"), cont.get("transition"), default="按 continuity.shot_size 控制景别，保持既定轴线与视线。")


def derived_negative(clip: Mapping[str, Any]) -> list[str]:
    sched = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    forbidden = unique(as_list(sched.get("forbidden_presence") if isinstance(sched, Mapping) else None))
    negatives = [
        "不新增未登记角色/道具",
        "不越轴",
        "不烤字，文字交由后期 overlay",
        "不出现现代物件",
        "不改变角色脸型、服装主色和武器形态",
    ]
    if forbidden:
        negatives.append("禁止入画：" + "、".join(forbidden))
    return negatives


def fill_base_template_fields(clip: Mapping[str, Any], template: str, tc: dict[str, Any], setdefault: Any) -> None:
    cont = continuity(clip)
    sched = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    scene = first_text(clip.get("scene"), clip.get("location_id"), default="本场主场景")
    visible = unique(
        [
            *as_list(clip.get("character_ids")),
            *as_list(clip.get("object_ids")),
            *as_list(sched.get("required_presence") if isinstance(sched, Mapping) else None),
        ]
    )
    setdefault("template_id", template)
    setdefault("beats", derived_beats(clip))
    setdefault(
        "blocking",
        f"{scene}；可见主体={('、'.join(visible) if visible else '按 character_ids/object_ids 登记主体')}；"
        f"{first_text(cont.get('entry_exit'), default='按 continuity.entry_exit 完成入画/出画交接')}",
    )
    setdefault("camera_rule", derived_camera_rule(clip, cont))
    setdefault(
        "continuity_must",
        concise(
            [
                f"起：{cont.get('start_state')}" if nonempty(cont.get("start_state")) else "",
                f"止：{cont.get('end_state')}" if nonempty(cont.get("end_state")) else "",
                f"视线：{cont.get('eyeline')}" if nonempty(cont.get("eyeline")) else "",
                f"入出画：{cont.get('entry_exit')}" if nonempty(cont.get("entry_exit")) else "",
            ],
            fallback="保持本镜 continuity.start_state/end_state/eyeline/entry_exit，不重置上一镜状态。",
            limit=5,
        ),
    )
    setdefault("negative", derived_negative(clip))


def fill_fight_exchange_fields(clip: Mapping[str, Any], tc: dict[str, Any], setdefault: Any) -> None:
    cont = continuity(clip)
    beats = unique(as_list(tc.get("beats"))) or derived_beats(clip)
    axis = first_text(
        tc.get("axis"),
        cont.get("entry_exit"),
        cont.get("eyeline"),
        default="按本镜起手方向推进到命中/收势方向，禁止中途反向越轴。",
    )
    cameras = shot_parts(clip, "camera", "lens", "composition")
    keyframe = first_text(
        tc.get("keyframe_plan"),
        default="起幅锁主体位置；中段锁攻击轨迹；尾帧锁受力结果和下一镜交接。",
    )
    impact = first_text(
        tc.get("impact_frame"),
        default="命中/格挡/出招高光帧按 beats 中的撞点执行，画面克制不强化猎奇伤口。",
    )
    setdefault("attack_path", axis)
    setdefault("impact_frame", impact)
    setdefault("action_scope", "只执行本 clip 声明的起手、命中/格挡、反应/收势，不新增连招、新敌人或剧情结果。")
    setdefault("contact_points", unique(as_list(tc.get("contact_points"))) or ["刀锋/狼爪/妖气/地面尘土按本镜 beats 发生接触或视觉撞点。"])
    setdefault("force_direction", first_text(tc.get("force_direction"), tc.get("axis"), default=axis))
    setdefault("screen_direction", first_text(tc.get("screen_direction"), tc.get("axis"), cont.get("eyeline"), default=axis))
    setdefault("speed_curve", first_text(tc.get("speed_curve"), default="蓄力停顿 → 突进爆发 → 命中定格 → 余波收势"))
    setdefault("spatial_path", first_text(tc.get("spatial_path"), cont.get("entry_exit"), default=axis))
    setdefault("camera_path", "；".join(cameras[:3]) if cameras else derived_camera_rule(clip, cont))
    setdefault("readability_beats", beats)
    setdefault("recovery_beat", first_text(cont.get("end_state"), beats[-1] if beats else "", default="尾帧完成受力反应并交接下一镜。"))
    setdefault("degrade_plan", "动作生成不稳时降级为手部/刀爪特写 + 反应镜头 + 尘土/妖气遮挡，剧情结果不变。")
    setdefault("keyframe_plan", keyframe)
    setdefault("post_cue_points", [impact, "尾帧按 continuity.end_state 与下一镜 start_state 对齐。"])
    setdefault("physics_guard", "刀、爪、身体与妖气的受力方向必须与 force_direction/screen_direction 一致；伤势和站位只按 continuity 演进。")


def entity_keys(values: Iterable[Any]) -> set[str]:
    return {entity_key(v) for v in unique(values) if entity_key(v)}


def continuity(clip: Mapping[str, Any]) -> dict[str, Any]:
    cont = clip.get("continuity")
    if isinstance(cont, dict):
        return cont
    return {}


def schedule(clip: dict[str, Any]) -> dict[str, Any]:
    item = clip.get("entity_schedule")
    if isinstance(item, dict):
        return item
    item = {}
    clip["entity_schedule"] = item
    return item


def visible_entities(clip: Mapping[str, Any]) -> set[str]:
    sched = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
    values: list[Any] = []
    for key in ("character_ids", "characters", "object_ids", "objects", "props"):
        values.extend(as_list(clip.get(key)))
    if isinstance(sched, Mapping):
        for key in ("required_presence", "characters", "objects", "props"):
            values.extend(as_list(sched.get(key)))
    return entity_keys(values)


def append_unique_list(mapping: dict[str, Any], key: str, values: Iterable[str]) -> None:
    cur = unique(as_list(mapping.get(key)))
    for value in values:
        if value and value not in cur:
            cur.append(value)
    if cur:
        mapping[key] = cur


def screen_text_lines(clip: Mapping[str, Any]) -> list[Any]:
    return [x for x in as_list(clip.get("screen_text_lines")) if x]


def fill_template_contract(clip: dict[str, Any]) -> int:
    template = str(clip.get("template") or "").strip()
    if not template:
        return 0
    tc = clip.get("template_contract")
    if not isinstance(tc, dict):
        tc = {"template_id": template}
        clip["template_contract"] = tc
    changed = 0

    def setdefault(key: str, value: Any) -> None:
        nonlocal changed
        if tc.get(key) in (None, "", [], {}):
            tc[key] = value
            changed += 1

    cont = continuity(clip)
    eyeline = str(cont.get("eyeline") or "按本场轴线锁定视线接力")
    scene = str(clip.get("scene") or clip.get("location_id") or "本场主场景")
    text_count = len(screen_text_lines(clip))

    fill_base_template_fields(clip, template, tc, setdefault)

    if template == "system_panel":
        setdefault("motif_id", "MOTIF_百妖谱系统面板")
        setdefault("vfx_asset", "VFX_系统面板/百妖谱")
        setdefault("text_layer", "compose_overlay_only")
        setdefault("growth_ref", f"screen_text_lines[{text_count}] + motif_registry progression；具体文字由 compose overlay 渲染")
        setdefault("panel_tier", "gold_scroll_bestiary")
    elif template == "dialogue_shot_reverse":
        setdefault("axis", f"{scene} 左右轴线；反打不越轴")
        setdefault("eyeline", eyeline)
        setdefault("shot_pairing", "压迫方反打 ↔ 受压方反打；按 blocking 保持高低位和左右关系")
    elif template == "intimate_interaction":
        setdefault("consent_boundary", "非亲密悼别/照护动作；接触目的明确，禁止暧昧化")
        setdefault("contact_points", ["手掌轻合眼睑/额前区域", "另一手握刀或撑地保持距离"])
        setdefault("distance_boundary", "保持半臂以上距离，只拍合眼与侧脸反应")
        setdefault("body_overlap_limit", "无拥抱、无贴脸、无身体覆盖；只允许手部短接触")
        setdefault("occlusion_order", "姜月初手掌短暂遮住裴长青眼部；裴长青遗体不主动回应")
        setdefault("body_part_ownership", "姜月初=手掌/侧脸/握刀手；裴长青=闭眼遗体")
        setdefault("relationship_state", "欠命账与悼别，不是爱情亲密")
        setdefault("readability_beats", ["走回遗体", "伸手合眼", "低声记账", "握刀起身"])
        setdefault("degrade_plan", "若接触动作误判为暧昧，降级为手部特写 + 姜月初单人侧脸反应")
    elif template == "fight_exchange":
        fill_fight_exchange_fields(clip, tc, setdefault)
    return changed


def backfill(data: dict[str, Any]) -> dict[str, Any]:
    changes = {
        "policy": 0,
        "expression_span": 0,
        "start_state_chain": 0,
        "presence_chain": 0,
        "template_contract": 0,
    }
    policy = data.get("policy")
    if not isinstance(policy, dict):
        policy = {}
        data["policy"] = policy
    if policy.get("seam_taxonomy_version") != 1:
        policy["seam_taxonomy_version"] = 1
        changes["policy"] += 1
    policy.setdefault("midframe_default", False)

    clips = data.get("clips")
    if not isinstance(clips, list):
        return changes

    for clip in clips:
        if not isinstance(clip, dict):
            continue
        cont = continuity(clip)
        if not cont:
            cont = {}
            clip["continuity"] = cont
        span = cont.get("expression_span")
        if span in EXPRESSION_SPAN_MAP:
            cont["expression_span"] = EXPRESSION_SPAN_MAP[span]
            changes["expression_span"] += 1
        changes["template_contract"] += fill_template_contract(clip)

    for idx in range(1, len(clips)):
        prev = clips[idx - 1]
        cur = clips[idx]
        if not isinstance(prev, dict) or not isinstance(cur, dict):
            continue
        prev_cont = continuity(prev)
        cur_cont = continuity(cur)
        prev_end = prev_cont.get("end_state")
        old_start = cur_cont.get("start_state")
        if prev_end and old_start != prev_end:
            cur_cont["previous_start_state_note"] = old_start or ""
            cur_cont["start_state"] = prev_end
            changes["start_state_chain"] += 1

        prev_visible = visible_entities(prev)
        cur_visible = visible_entities(cur)
        disappeared = sorted(prev_visible - cur_visible)
        appeared = sorted(cur_visible - prev_visible)
        if not disappeared and not appeared:
            continue
        prev_sched = schedule(prev)
        cur_sched = schedule(cur)
        append_unique_list(cur_sched, "offscreen_presence", disappeared)
        append_unique_list(prev_sched, "offscreen_presence", appeared)
        notes: list[str] = []
        if disappeared:
            notes.append("出画/画外保留：" + "、".join(disappeared))
        if appeared:
            notes.append("入画/现身：" + "、".join(appeared))
        note = "；".join(notes)
        prev_cont["entry_exit"] = (str(prev_cont.get("entry_exit") or "").strip() + "；" + note).strip("；")
        cur_cont["entry_exit"] = (str(cur_cont.get("entry_exit") or "").strip() + "；" + note).strip("；")
        changes["presence_chain"] += 1

    return changes


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    ep = episode_label(ns.episode)
    path = root / "脚本" / ep / "storyboard.json"
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"storyboard.json missing or invalid: {path}")
    changes = backfill(data)
    payload = {"episode": ep, "path": str(path), "changes": changes}
    if ns.write:
        write_json_atomic(path, data)
        payload["written"] = True
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"storyboard contract backfill {ep}: {changes}" + (" (written)" if ns.write else " (dry-run)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
