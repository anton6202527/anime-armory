#!/usr/bin/env python3
"""P-3 production handoff pack for n2d.

This is the production-management layer after the stage-2 storyboard and before
image prompt generation. It translates the director/storyboard intent into the
documents a small crew would need before shooting: scene breakdown, continuity
breakdown, and an AI call sheet.

Usage:
  python3 production_breakdown.py <作品根> 第N集 scaffold --write
  python3 production_breakdown.py <作品根> 第N集 check --json --write-missing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

KIND = "n2d_production_handoff_pack"
CHECK_KIND = "n2d_production_handoff_pack_check"
VERSION = 1
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)
CONFIRMED_RE = re.compile(r"(?im)^\s*(?:status|状态)\s*[:：]\s*(?:confirmed|已确认|pass|通过)\s*$")

REQUIRED_FILES = (
    "production_breakdown.json",
    "continuity_breakdown.json",
    "ai_call_sheet.md",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_json_if_absent(path: Path, payload: Mapping[str, Any], *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_json_atomic(path, payload)
    return True


def write_text_if_absent(path: Path, text: str, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_atomic(path, text)
    return True


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _episode_dir(root: Path, ep: str) -> Path:
    return root / "脚本" / ep


def _clips(root: Path, ep: str) -> List[Dict[str, Any]]:
    data = load_json(_episode_dir(root, ep) / "storyboard.json")
    if not isinstance(data, dict):
        return []
    clips = data.get("clips") or data.get("shots") or []
    return [c for c in clips if isinstance(c, dict)]


def _clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or f"Clip_{idx:02d}")


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_items(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for value in values:
        if isinstance(value, Mapping):
            text = str(value.get("id") or value.get("text") or value).strip()
        else:
            text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _clip_continuity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    return clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}


def _clip_entity(clip: Mapping[str, Any]) -> Mapping[str, Any]:
    return clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), dict) else {}


def _clip_template(clip: Mapping[str, Any]) -> str:
    return str(clip.get("template") or clip.get("rhythm") or "standard_scene").strip()


def _screen_texts(clip: Mapping[str, Any]) -> List[Any]:
    return [x for x in _as_list(clip.get("screen_text_lines")) if x]


def _vfx_assets(clip: Mapping[str, Any]) -> List[str]:
    assets = []
    for item in _clean_items(_as_list(clip.get("object_ids"))):
        if item.startswith("VFX_") or "百妖谱" in item or "overlay" in item.lower():
            assets.append(item)
    return assets


def _overlay_policy(clip: Mapping[str, Any]) -> str:
    if _screen_texts(clip):
        return "所有可读系统文字、数值和状态面板只交 compose overlay；生图/视频只画空面板与安全留白。"
    if _vfx_assets(clip):
        return "VFX 可画形状/光效；若出现可读文字或数值，一律改由 compose overlay。"
    return "本镜无可读画中文字；字幕、花字和临时说明统一在 compose 层处理。"


def _backend_risk(clip: Mapping[str, Any]) -> str:
    template = _clip_template(clip)
    continuity = _clip_continuity(clip)
    anchors = _as_list(continuity.get("anchors"))
    risks: List[str] = []
    if anchors:
        risks.append(f"多锚帧 {len(anchors)} 个，按首/中/尾关键帧拆分控制。")
    if any(token in template for token in ("fight", "action", "追逐", "打斗")):
        risks.append("高运动镜头，动作线、命中点和收势要拆清，失败时降级为更短 Clip。")
    if "system" in template or _screen_texts(clip):
        risks.append("系统面板镜头禁止烤字，保留干净面板区给后期叠字。")
    if "dialogue" in template or "CU" in str(continuity.get("shot_size") or ""):
        risks.append("近景/对话镜优先锁脸和视线，口型只做视觉占位。")
    return " ".join(risks) if risks else "常规镜头：继承本场轴线、光位和身份参考，按首尾帧接力。"


def _department_notes(clip: Mapping[str, Any]) -> Dict[str, str]:
    continuity = _clip_continuity(clip)
    characters = ", ".join(_clean_items(_as_list(clip.get("character_ids")))) or "无具名角色"
    objects = ", ".join(_clean_items(_as_list(clip.get("object_ids")))) or "无关键道具"
    shot_size = str(continuity.get("shot_size") or "").strip() or "按 storyboard 景别"
    eyeline = str(continuity.get("eyeline") or "").strip() or "按本场轴线接力"
    transition = str(continuity.get("transition") or "").strip() or "cut"
    return {
        "art": f"场景 {clip.get('location_id') or clip.get('scene') or '本场主场景'}；入画角色 {characters}；关键物件 {objects}。",
        "camera": f"景别/机位：{shot_size}；视线/轴线：{eyeline}；模板：{_clip_template(clip)}。",
        "post": f"转场 {transition}；{_overlay_policy(clip)}",
    }


def _sfx_notes(clip: Mapping[str, Any]) -> str:
    template = _clip_template(clip)
    notes = ["荒野风声/环境底噪按场景 AMBIENT 延续"]
    objects = " ".join(_clean_items(_as_list(clip.get("object_ids"))))
    if "WEAPON" in objects or "刀" in objects:
        notes.append("横刀出鞘、刀锋破风、金纹灌刀")
    if "fight" in template:
        notes.append("冲撞、妖风、命中点、收势重音")
    if "system" in template or _screen_texts(clip):
        notes.append("百妖谱面板亮起/计数跳变 UI 音效")
    return "；".join(notes) + "。"


def _wardrobe_state(clip: Mapping[str, Any]) -> str:
    entity = _clip_entity(clip)
    required = _clean_items(_as_list(entity.get("required_presence")))
    if not required:
        required = _clean_items(_as_list(clip.get("character_ids")))
    state = "、".join(required) if required else "按 storyboard 入画角色"
    return f"按本镜 required_presence 锁定：{state}；血尘、战损、泪痕和形态只按 start_state→end_state 演进。"


def _props_continuity(clip: Mapping[str, Any]) -> str:
    objects = _clean_items(_as_list(clip.get("object_ids")))
    if not objects:
        return "本镜无关键持物；场景常驻物按 LOC 布局延续。"
    return "关键物件保持可追踪：" + "、".join(objects) + "；位置变化必须由动作或转场解释。"


def _screen_direction(clip: Mapping[str, Any]) -> str:
    continuity = _clip_continuity(clip)
    eyeline = str(continuity.get("eyeline") or "").strip()
    transition = str(continuity.get("transition") or "").strip() or "cut"
    return f"守本场左右轴线；视线接力：{eyeline or '按角色对手/目标方向'}；转场方式：{transition}。"


def _production_breakdown(root: Path, ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> Dict[str, Any]:
    scenes = []
    for idx, clip in enumerate(clips, start=1):
        vfx_assets = _vfx_assets(clip)
        scenes.append({
            "clip_id": _clip_id(clip, idx),
            "label": clip.get("label") or "",
            "scene": clip.get("scene") or "",
            "location_id": clip.get("location_id") or "",
            "characters": _as_list(clip.get("character_ids")),
            "props_and_objects": _as_list(clip.get("object_ids")),
            "wardrobe_makeup_state": _wardrobe_state(clip),
            "vfx_or_overlay": {
                "system_panels": [x for x in _as_list(clip.get("screen_text_lines")) if x],
                "vfx_assets": vfx_assets or ["场景风沙、血尘、光位变化按本场视觉契约继承"],
                "compose_overlay_only": _overlay_policy(clip),
            },
            "sound_needs": {
                "dialogue_indices": _as_list(clip.get("dialogue_indices")),
                "narration_indices": _as_list(clip.get("narration_indices")),
                "sfx": _sfx_notes(clip),
            },
            "image_video_requirements": {
                "firstframe": clip.get("firstframe_png") or "",
                "endframe": clip.get("endframe_png") or "",
                "anchors": _as_list((clip.get("continuity") or {}).get("anchors") if isinstance(clip.get("continuity"), dict) else []),
                "backend_risk": _backend_risk(clip),
            },
            "department_notes": _department_notes(clip),
        })
    return {
        "kind": "n2d_production_breakdown",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "inputs": {
            "storyboard": f"脚本/{ep}/storyboard.json",
            "director_blocking_pack": f"脚本/{ep}/director_blocking_pack.json",
            "script_quality_contract": f"生产数据/script_quality_contract_{ep}.json",
        },
        "summary": {
            "clip_count": len(clips),
            "locations": sorted({str(c.get("location_id") or "") for c in clips if c.get("location_id")}),
            "characters": sorted({str(x) for c in clips for x in _as_list(c.get("character_ids")) if x}),
            "objects": sorted({str(x) for c in clips for x in _as_list(c.get("object_ids")) if x}),
        },
        "scene_breakdowns": scenes or [{
            "clip_id": "Clip_01",
            "label": "待补：storyboard.json 未提供 clips[]，请人工拆解",
            "scene": "待补",
            "location_id": "待补",
            "characters": "待补",
            "props_and_objects": "待补",
        }],
    }


def _continuity_breakdown(ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> Dict[str, Any]:
    rows = []
    for idx, clip in enumerate(clips, start=1):
        continuity = _clip_continuity(clip)
        entity = _clip_entity(clip)
        rows.append({
            "clip_id": _clip_id(clip, idx),
            "location_id": clip.get("location_id") or "",
            "required_presence": _as_list(entity.get("required_presence")),
            "start_state": continuity.get("start_state") or "待补：入点人物/道具/空间状态",
            "end_state": continuity.get("end_state") or "待补：出点人物/道具/空间状态",
            "eyeline": continuity.get("eyeline") or "按本场轴线/主体目标方向接力",
            "screen_direction": _screen_direction(clip),
            "wardrobe_makeup_continuity": _wardrobe_state(clip),
            "props_continuity": _props_continuity(clip),
            "knowledge_state": entity.get("knowledge_state") or "待补：角色此刻知道/不知道什么",
            "transition_guard": continuity.get("transition") or "按 storyboard 默认 cut 处理",
        })
    return {
        "kind": "n2d_continuity_breakdown",
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "continuity_owner": "script_supervisor",
        "rows": rows or [{
            "clip_id": "Clip_01",
            "start_state": "待补",
            "end_state": "待补",
            "eyeline": "待补",
            "wardrobe_makeup_continuity": "待补",
            "props_continuity": "待补",
        }],
    }


def _ai_call_sheet(root: Path, ep: str, clips: List[Dict[str, Any]], *, confirmed: bool = False) -> str:
    rows = []
    for idx, clip in enumerate(clips, start=1):
        continuity = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        rows.append(
            "| {order} | {clip_id} | {scene} | {duration} | {risk} | {hold} |".format(
                order=idx,
                clip_id=_clip_id(clip, idx),
                scene=str(clip.get("scene") or "").replace("|", "/"),
                duration=clip.get("duration") or "",
                risk=str(clip.get("template") or clip.get("rhythm") or "standard_scene").replace("|", "/"),
                hold="尾帧" if continuity.get("need_endframe") else "无尾帧要求",
            )
        )
    body = "\n".join(rows) if rows else "| 1 | Clip_01 | 待补 | 待补 | 待补 | 待补 |"
    return f"""---
kind: n2d_ai_call_sheet
version: 1
episode: {ep}
status: {'confirmed' if confirmed else 'draft'}
---
# {ep} — AI 拍摄通告单

> 这是 Stage 2 分镜之后、出图 prompt 之前的制片交接单。confirmed 表示已按 storyboard / continuity / 合规包完成出图 prompt 前交接。

## 生产日目标
- 本轮目标：先生成第 2 层出图 prompt；共享定妆已存在时优先打样高风险动作镜与系统面板镜，再进入全集出图。

## 放行前依赖
- P-1 开发包 confirmed；P-2 导演排戏包 confirmed；本 P-3 包 confirmed 后才进入出图 prompt。
- 角色/场景/道具/VFX 参考从共享 identity_registry / asset_registry 继承；新增缺口由出图 prompt 标为 reference plan。
- 系统文字、状态数值、字幕和花字走 compose overlay；生图/视频只留空面板与安全区。
- 合规包按 internal_only demo 使用，平台审核/备案/出海本地化留到转投放前补齐。

## 拍摄顺序
| 顺序 | Clip | 场景 | 秒数 | 风险/模板 | 保持项 |
|---|---|---|---|---|---|
{body}

## 人工停审点
- 动作/打斗/追逐/高运动镜必须优先审动作线、命中点、收势和可读性。
- 系统面板、状态数值、标题卡和任何文字镜必须确认留白与 overlay 安全区，不允许 AI 烤字。
- 集尾钩、关系转折和高情绪近景必须确认情绪转折与下一集问题清楚。

## 后期交接
- BGM hit 对齐本集爽点、反转、系统信息和集尾钩；J/L cut 用环境声、动作声和 UI 音效衔接。
- 真实配音在先出视频后补，compose 前必须替换 rough timing 并复核字幕/镜头时长。
- 全集保持冷灰写实 3D 国风漫剧，百妖谱金色光只作为剧情信息焦点，不改角色定妆。
"""


def _write_overview(root: Path, ep: str, report: Mapping[str, Any] | None = None) -> str:
    out = root / "生产数据" / f"production_handoff_pack_{ep}.md"
    lines = [
        f"# P-3 制片拆解包 — {ep}",
        "",
        "本包位于 Stage 2 分镜之后、出图 prompt 之前，用来把导演分镜翻译成可执行的制片交接。",
        "",
        "## Required Files",
        "",
    ]
    lines.extend(f"- `脚本/{ep}/{name}`" for name in REQUIRED_FILES)
    if report:
        lines.extend([
            "",
            "## Check",
            "",
            f"- 状态：{report.get('status')}",
            f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
            "",
            "| 文件 | 状态 | 问题 |",
            "|---|---|---|",
        ])
        for row in report.get("files") or []:
            issues = "；".join(row.get("issues") or []) or "-"
            lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    write_atomic(out, "\n".join(lines).rstrip() + "\n")
    return str(out)


def scaffold(root: Path, ep: str, *, force: bool = False, confirmed: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    ep_dir = _episode_dir(root, ep)
    clips = _clips(root, ep)
    created: List[str] = []
    payloads: Tuple[Tuple[str, Mapping[str, Any]], ...] = (
        ("production_breakdown.json", _production_breakdown(root, ep, clips, confirmed=confirmed)),
        ("continuity_breakdown.json", _continuity_breakdown(ep, clips, confirmed=confirmed)),
    )
    for name, payload in payloads:
        if write_json_if_absent(ep_dir / name, payload, force=force):
            created.append(f"脚本/{ep}/{name}")
    if write_text_if_absent(ep_dir / "ai_call_sheet.md", _ai_call_sheet(root, ep, clips, confirmed=confirmed), force=force):
        created.append(f"脚本/{ep}/ai_call_sheet.md")
    manifest = {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "status": "confirmed" if confirmed else "draft",
        "generated_at": now_iso(),
        "root": str(root),
        "required_files": [f"脚本/{ep}/{name}" for name in REQUIRED_FILES],
        "gate": "run.py image_prompt prework requires all P-3 production handoff files to be confirmed.",
    }
    write_json_atomic(ep_dir / "production_handoff_pack.json", manifest)
    overview = _write_overview(root, ep)
    return {
        "kind": KIND,
        "root": str(root),
        "episode": ep,
        "episode_dir": str(ep_dir),
        "created": created,
        "manifest": f"脚本/{ep}/production_handoff_pack.json",
        "overview_path": overview,
    }


def _json_status(path: Path) -> Tuple[str, List[str]]:
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        return "block", ["JSON 无法解析或不是 object"]
    if str(data.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed")
    blob = json.dumps(data, ensure_ascii=False)
    if PLACEHOLDER_RE.search(blob):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def _md_status(path: Path) -> Tuple[str, List[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    issues: List[str] = []
    if not text.strip():
        return "block", ["文件为空"]
    if not CONFIRMED_RE.search(text):
        issues.append("缺 status: confirmed / 状态: confirmed")
    if PLACEHOLDER_RE.search(text):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def check(root: Path, ep: str, *, write_missing: bool = False) -> Dict[str, Any]:
    ep = episode_label(ep)
    if write_missing:
        scaffold(root, ep)
    ep_dir = _episode_dir(root, ep)
    rows: List[Dict[str, Any]] = []
    for name in REQUIRED_FILES:
        path = ep_dir / name
        rel = f"脚本/{ep}/{name}"
        if not path.exists():
            rows.append({"rel": rel, "status": "missing", "issues": ["文件缺失"]})
            continue
        status, issues = _json_status(path) if path.suffix == ".json" else _md_status(path)
        rows.append({"rel": rel, "status": status, "issues": issues})
    blockers = [row for row in rows if row["status"] != "pass"]
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "episode": ep,
        "status": "pass" if not blockers else "block",
        "summary": {
            "required": len(REQUIRED_FILES),
            "pass": len(rows) - len(blockers),
            "block": len(blockers),
        },
        "files": rows,
        "scaffold_command": f"python3 skills/n2d-script/scripts/production_breakdown.py {root} {ep} scaffold --write",
        "next_when_blocked": (
            "补齐 P-3 制片拆解三件套，删除待补/TODO 占位，并把每个文件 status 改为 confirmed；"
            "之后重跑 check，再进入出图 prompt。"
        ),
    }
    out = root / "生产数据" / f"production_breakdown_check_{ep}.json"
    write_json_atomic(out, payload)
    payload["check_path"] = str(out)
    payload["overview_path"] = _write_overview(root, ep, payload)
    return payload


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# P-3 制片拆解包检查 — {report.get('episode')}",
        "",
        f"- 状态：{report.get('status')}",
        f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
        "",
        "| 文件 | 状态 | 问题 |",
        "|---|---|---|",
    ]
    for row in report.get("files") or []:
        issues = "；".join(row.get("issues") or []) or "-"
        lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    lines += ["", str(report.get("next_when_blocked") or "")]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    sub = ap.add_subparsers(dest="command", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--write", action="store_true", help="兼容显式写入语义；scaffold 默认即写入")
    p_scaffold.add_argument("--force", action="store_true", help="覆盖已有模板（谨慎）")
    p_scaffold.add_argument("--confirm", action="store_true", help="用 storyboard 可推导字段生成 confirmed 交接包；若仍含占位，check 仍会阻断")
    p_check = sub.add_parser("check")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--markdown", action="store_true")
    p_check.add_argument("--write-missing", action="store_true", help="缺文件时先补 scaffold，再返回 block")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    ep = episode_label(ns.episode)
    if ns.command == "scaffold":
        payload = scaffold(root, ep, force=ns.force, confirmed=ns.confirm)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    report = check(root, ep, write_missing=ns.write_missing)
    if ns.markdown:
        md = render_markdown(report)
        path = root / "生产数据" / f"production_breakdown_check_{ep}.md"
        write_atomic(path, md)
        print(md)
    elif ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"P-3 制片拆解包检查：{report['status']} ({report['summary']['pass']}/{report['summary']['required']})")
        if report["status"] != "pass":
            print(report["next_when_blocked"])
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
