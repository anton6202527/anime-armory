#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CANVAS 三轴 VLM 并排判定任务包（漫画线自包含实现）。

三轴取自 CANVAS ContinuityEval 协议：
  1. character_identity   角色一致（脸 / 服装 / 体型）
  2. background_continuity 背景连续（同场景锚相邻格的布局 / 光位 / 轴线）
  3. prop_identity        道具身份与位置

本脚本只产任务包和回读裁决，不调用任何 VLM API：任务由 agent（Claude/Codex
等多模态模型）逐条看图执行，把裁决写回 verdict 文件。裁决只做**相对排序 /
低分预警**（跨 VLM judge 一致性有限，绝对分不可信），score<=2 或
verdict=suspect 的任务由消费方（character/scene-prop 一致性报告）转成 warn。

任务内嵌出图 sha256；重抽该格后旧裁决自动失效。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
AXES = ("character_identity", "background_continuity", "prop_identity")
SCORE_GUIDE = (
    "score 取 1-5：5=与参考/前格完全一致；4=细节小偏差不影响认脸/认景/认物；"
    "3=可见偏差需人工确认；2=明显漂移（换脸/换景布局/道具变形）；1=完全不是同一个。"
    "只做同批次内相对排序，不追求绝对准确。"
)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(str(raw or ""))
    return path if path.is_absolute() else root / path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_panel_image(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for suffix in IMAGE_EXTS:
        path = base / f"{panel_id}{suffix}"
        if path.is_file():
            return path
    matches = sorted(base.glob(f"{panel_id}.*"))
    return next((item for item in matches if item.suffix.lower() in IMAGE_EXTS), None)


def tasks_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"comic_vlm_judge_tasks_{chapter}.json"


def verdicts_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"comic_vlm_judge_verdicts_{chapter}.json"


def panel_ref_ids(panel: dict[str, Any], prefixes: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw or "").strip()
            if ref_id.startswith(prefixes) and ref_id not in out:
                out.append(ref_id)
    return out


def asset_reference_paths(root: Path, registry: dict[str, Any], ref_id: str, limit: int = 4) -> list[str]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
    candidates: list[str] = []
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append(raw)
        views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
        for key in ("face", "front", "three_quarter", "side", "back"):
            raw = views.get(key) if isinstance(views, dict) else ""
            if isinstance(raw, str) and raw.strip():
                candidates.append(raw)
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                candidates.append(raw)
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png"):
        candidates.append(str(shared / f"{ref_id}{suffix}"))
    out: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        path = resolve_path(root, raw)
        if path.is_file():
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                out.append(rel(root, path))
        if len(out) >= limit:
            break
    return out


def panel_scene_anchor(panel: dict[str, Any]) -> str:
    for key in ("scene_anchor_id", "scene_id", "location_id"):
        value = str(panel.get(key) or "").strip()
        if value:
            return value
    for ref_id in panel_ref_ids(panel, ("LOC_",)):
        return ref_id
    return ""


def build_tasks(root: Path, chapter: str) -> dict[str, Any]:
    root = root.resolve()
    script = load_json(root / "脚本" / chapter / "panel_script.json", {})
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    registry = registry if isinstance(registry, dict) else {}
    panels = [p for p in (script.get("panels") or []) if isinstance(p, dict) and p.get("panel_id")]
    tasks: list[dict[str, Any]] = []
    sha_cache: dict[str, str] = {}

    def panel_entry(pid: str) -> dict[str, str] | None:
        path = find_panel_image(root, chapter, pid)
        if not path:
            return None
        key = str(path.resolve())
        if key not in sha_cache:
            sha_cache[key] = file_sha256(path)
        return {"panel_id": pid, "path": rel(root, path), "sha256": sha_cache[key]}

    # 轴1：角色一致（脸/服装/体型）——含 MON_，一格一角色一任务。
    for panel in panels:
        pid = str(panel.get("panel_id"))
        entry = panel_entry(pid)
        if not entry:
            continue
        for char_id in panel_ref_ids(panel, ("CHAR_", "MON_")):
            refs = asset_reference_paths(root, registry, char_id)
            if not refs:
                continue
            tasks.append(
                {
                    "task_id": f"{pid}__{char_id}__character",
                    "axis": "character_identity",
                    "panel": entry,
                    "subject": char_id,
                    "references": refs,
                    "question": (
                        f"并排对比 panel 图与 {char_id} 的定妆参考：这是同一个角色吗？"
                        "分三个子项打分：face（脸型/眼型/发际线/发型轮廓）、"
                        "outfit（领型/纽扣/花纹/配饰）、build（体型比例）。" + SCORE_GUIDE
                    ),
                }
            )

    # 轴2：背景连续——同场景锚在阅读顺序上相邻的两格。
    prev_by_anchor: dict[str, dict[str, str]] = {}
    for panel in panels:
        pid = str(panel.get("panel_id"))
        anchor = panel_scene_anchor(panel)
        if not anchor:
            continue
        entry = panel_entry(pid)
        if not entry:
            continue
        prev = prev_by_anchor.get(anchor)
        if prev:
            tasks.append(
                {
                    "task_id": f"{prev['panel_id']}__{pid}__background",
                    "axis": "background_continuity",
                    "panel": entry,
                    "subject": anchor,
                    "references": [prev["path"]],
                    "reference_sha256": prev["sha256"],
                    "question": (
                        f"这两格同属场景锚 {anchor}（前格 {prev['panel_id']} → 本格 {pid}）。"
                        "对比空间布局（门窗/家具方位）、主光方向与冷暖、轴线方向是否继承；"
                        "机位可以变，场景结构和光位不能翻转。" + SCORE_GUIDE
                    ),
                }
            )
        prev_by_anchor[anchor] = entry

    # 轴3：道具身份与位置——有参考图的 PROP_/SYS_/FX_ 资产逐格核对。
    for panel in panels:
        pid = str(panel.get("panel_id"))
        entry = panel_entry(pid)
        if not entry:
            continue
        for prop_id in panel_ref_ids(panel, ("PROP_", "SYS_", "FX_")):
            refs = asset_reference_paths(root, registry, prop_id, limit=2)
            if not refs:
                continue
            tasks.append(
                {
                    "task_id": f"{pid}__{prop_id}__prop",
                    "axis": "prop_identity",
                    "panel": entry,
                    "subject": prop_id,
                    "references": refs,
                    "question": (
                        f"本格应出现道具/物件 {prop_id}。对照参考图：该物件是否出现在画面、"
                        "结构与材质是否为同一个（不是同类替代品）、位置与人物的持有/接触关系是否合理。" + SCORE_GUIDE
                    ),
                }
            )

    payload = {
        "schema_version": 1,
        "kind": "comic_vlm_judge_tasks",
        "protocol": "CANVAS-ContinuityEval-3axis",
        "chapter": chapter,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "axes": list(AXES),
        "instructions": (
            "由多模态 agent 逐条执行：打开 panel 与 references 图片并排看，"
            "按 question 打分，写入 verdict 文件（路径见 verdict_file）。"
            "只做相对排序与低分预警；score<=2 或 verdict=suspect 会转成 warn finding。"
            "verdict 记录必须复制任务里的 panel.sha256——重抽后 sha 不匹配的旧裁决会被自动作废。"
        ),
        "verdict_file": rel(root, verdicts_path(root, chapter)),
        "verdict_schema": {
            "verdicts": [
                {
                    "task_id": "<task_id>",
                    "panel_sha256": "<复制任务里的 panel.sha256>",
                    "scores": {"face": "1-5（按轴要求的子项）"},
                    "verdict": "pass | suspect",
                    "notes": "一句话证据",
                }
            ]
        },
        "task_count": len(tasks),
        "tasks": tasks,
    }
    return payload


def write_tasks(root: Path, chapter: str) -> Path:
    payload = build_tasks(root, chapter)
    out = tasks_path(root, chapter)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def load_verdicts(root: Path, chapter: str) -> dict[str, dict[str, Any]]:
    """task_id → verdict 记录；跳过 sha 已过期（该格已重抽）的旧裁决。"""
    tasks = load_json(tasks_path(root, chapter), {})
    verdict_payload = load_json(verdicts_path(root, chapter), {})
    if not isinstance(verdict_payload, dict):
        return {}
    task_sha = {
        str(task.get("task_id")): str((task.get("panel") or {}).get("sha256") or "")
        for task in (tasks.get("tasks") or [])
        if isinstance(task, dict)
    }
    out: dict[str, dict[str, Any]] = {}
    for record in verdict_payload.get("verdicts") or []:
        if not isinstance(record, dict):
            continue
        task_id = str(record.get("task_id") or "")
        if not task_id:
            continue
        recorded_sha = str(record.get("panel_sha256") or "")
        expected = task_sha.get(task_id, "")
        if expected and recorded_sha and recorded_sha != expected:
            continue  # 该格已重抽，旧裁决作废
        out[task_id] = record
    return out


def suspect_verdicts(root: Path, chapter: str, axis: str) -> list[dict[str, Any]]:
    tasks = load_json(tasks_path(root, chapter), {})
    verdicts = load_verdicts(root, chapter)
    out: list[dict[str, Any]] = []
    for task in tasks.get("tasks") or [] if isinstance(tasks, dict) else []:
        if not isinstance(task, dict) or task.get("axis") != axis:
            continue
        record = verdicts.get(str(task.get("task_id")))
        if not record:
            continue
        scores = record.get("scores") if isinstance(record.get("scores"), dict) else {}
        low = [f"{key}={value}" for key, value in scores.items() if isinstance(value, (int, float)) and value <= 2]
        if str(record.get("verdict") or "").lower() == "suspect" or low:
            out.append({"task": task, "verdict": record, "low_scores": low})
    return out


def judge_status(root: Path, chapter: str) -> dict[str, Any]:
    tasks = load_json(tasks_path(root, chapter), {})
    task_list = tasks.get("tasks") or [] if isinstance(tasks, dict) else []
    verdicts = load_verdicts(root, chapter)
    return {
        "task_count": len(task_list),
        "verdict_count": sum(1 for task in task_list if isinstance(task, dict) and str(task.get("task_id")) in verdicts),
        "tasks_file": rel(root, tasks_path(root, chapter)),
        "verdict_file": rel(root, verdicts_path(root, chapter)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成/查看漫画 VLM 并排判定任务包（CANVAS 三轴）")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--status", action="store_true", help="只输出任务/裁决完成度，不重建任务包")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if args.status:
        print(json.dumps(judge_status(root, args.chapter), ensure_ascii=False, indent=2))
        return 0
    out = write_tasks(root, args.chapter)
    status = judge_status(root, args.chapter)
    print(f"[ok] {out}")
    print(f"[info] tasks={status['task_count']} verdicts={status['verdict_count']}；由多模态 agent 看图执行后写 {status['verdict_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
