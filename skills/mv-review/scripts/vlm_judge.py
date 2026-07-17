#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 逐 clip VLM 并排判定任务包（CANVAS 口径·参照同仓漫画线 vlm_judge 的 MV 重实现，不跨线 import）。

为什么存在：mv 出图后的机检全是纯数值（脸余弦/dHash/ΔE），"画面内容对不对"
（主角是不是同一个人、接缝首末帧接不接得上）此前只有人判。同仓漫画线 2026-07-17
实证过该空档的代价：参考图全对、prompt 全对，出图仍把生物画错形态，任务包生成后
0 条裁决、无人报警。本脚本把"看图裁决"做成可审计合同：

  1) `--write` 生成任务包 `生产数据/vlm_judge/vlm_judge_tasks.json`：
     - 轴1 lead_identity：每个已出图 clip 的首帧 vs 其 reference_inputs 里的身份定妆组；
     - 轴2 seam_continuity：need_end_frame 的 clip 末帧 vs 下一 clip 首帧（接缝继承）。
  2) 多模态 agent 逐条看图打分，回填 `生产数据/vlm_judge/vlm_judge_verdicts.json`。
  3) 裁决必须原样复制任务里的 image_sha256 / task_sha256 / references_sha256，
     且带 evaluator{model,version}——重抽后 sha 不匹配的旧裁决自动作废，空壳裁决被丢弃。
  4) mv-craft gate 消费两个文件做覆盖率对账：任务包存在但 0 裁决 = 机检空转 warn；
     部分裁决 = 覆盖率不足 warn（advisory 铁律：永不 block）。

裁决只做相对排序/低分预警：score<=2 或 verdict=suspect 由 gate 转 warn 交人判。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

KIND_TASKS = "mv_vlm_judge_tasks"
KIND_VERDICTS = "mv_vlm_judge_verdicts"
AXES = ("lead_identity", "seam_continuity")
SCORE_GUIDE = (
    "score 取 1-5：5=与参考/前帧完全一致；4=细节小偏差不影响认人/接戏；"
    "3=可见偏差需人工确认；2=明显漂移（换脸/换装/接缝断裂）；1=完全不是同一个/主体缺失。"
    "只做同批次内相对排序，不追求绝对准确。"
)


def load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def report_dir(root: str) -> str:
    return os.path.join(root, "生产数据", "vlm_judge")


def tasks_path(root: str) -> str:
    return os.path.join(report_dir(root), "vlm_judge_tasks.json")


def verdicts_path(root: str) -> str:
    return os.path.join(report_dir(root), "vlm_judge_verdicts.json")


def file_sha256(path: str) -> str:
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def task_sha256(task: Dict[str, Any]) -> str:
    basis = {k: task.get(k) for k in ("task_id", "axis", "image", "subject", "references", "references_sha256", "question")}
    return hashlib.sha256(json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def identity_reference_paths(clip: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for item in clip.get("reference_inputs") or []:
        if not isinstance(item, dict):
            continue
        use = str(item.get("use") or "")
        path = str(item.get("path") or "").strip()
        if path and "identity" in use:
            out.append(path)
    return out


def build_tasks(root: str) -> Dict[str, Any]:
    clip_plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = load_json(clip_plan_path, {}) or {}
    clips = [c for c in (plan.get("clips") or []) if isinstance(c, dict) and c.get("clip_id")]
    tasks: List[Dict[str, Any]] = []

    def image_entry(rel: str) -> Optional[Dict[str, str]]:
        rel = str(rel or "").strip()
        if not rel:
            return None
        full = os.path.join(root, rel)
        if not os.path.exists(full):
            return None
        return {"path": rel, "sha256": file_sha256(full)}

    # 轴1：主角身份——已出图 clip 首帧 vs reference_inputs 身份定妆组。
    for clip in clips:
        cid = str(clip.get("clip_id"))
        entry = image_entry(str(clip.get("image_path") or ""))
        if not entry:
            continue
        refs = [rel for rel in identity_reference_paths(clip) if os.path.exists(os.path.join(root, rel))]
        if not refs:
            continue
        tasks.append({
            "task_id": f"{cid}__lead_identity",
            "axis": "lead_identity",
            "image": entry,
            "subject": "lead",
            "references": refs,
            "question": (
                f"并排对比 clip {cid} 首帧与主角定妆参考：这是同一个人吗？"
                "分三个子项打分：face（脸型/眼型/发际线/发型轮廓）、"
                "outfit（服装款式/主色/配饰）、build（体型比例）。" + SCORE_GUIDE
            ),
        })

    # 轴2：接缝连续——need_end_frame 的 clip 末帧 vs 下一 clip 首帧。
    for prev, cur in zip(clips, clips[1:]):
        if not prev.get("need_end_frame"):
            continue
        prev_end = image_entry(str(prev.get("end_frame_path") or ""))
        cur_first = image_entry(str(cur.get("image_path") or ""))
        if not prev_end or not cur_first:
            continue
        tasks.append({
            "task_id": f"{prev.get('clip_id')}__{cur.get('clip_id')}__seam",
            "axis": "seam_continuity",
            "image": cur_first,
            "subject": f"{prev.get('clip_id')}->{cur.get('clip_id')}",
            "references": [prev_end["path"]],
            "question": (
                f"这两帧是接缝对（{prev.get('clip_id')} 末帧 → {cur.get('clip_id')} 首帧，声明了硬接缝继承）。"
                "对比主体位置/朝向、场景结构、主光方向与冷暖是否可继承；MV 卡点硬切允许机位跳变，"
                "但同一主体不得换人换装、场景结构和光位不能翻转。" + SCORE_GUIDE
            ),
        })

    for task in tasks:
        refs = [str(item) for item in task.get("references") or []]
        task["references_sha256"] = {rel: file_sha256(os.path.join(root, rel)) for rel in refs}
        task["task_sha256"] = task_sha256(task)

    return {
        "kind": KIND_TASKS,
        "schema_version": 1,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "inputs_sha256": {"分镜/clip_plan.json": file_sha256(clip_plan_path)},
        "axes": list(AXES),
        "instructions": (
            "由多模态 agent 逐条执行：打开 image 与 references 并排看，按 question 打分，"
            "写入 verdict 文件（路径见 verdict_file）。裁决必须原样复制任务里的 image.sha256、"
            "task_sha256、references_sha256，并带 evaluator{model,version}；重抽后 sha 不匹配的旧裁决自动作废。"
        ),
        "verdict_file": "生产数据/vlm_judge/vlm_judge_verdicts.json",
        "verdict_schema": {
            "verdicts": [{
                "task_id": "<task_id>",
                "image_sha256": "<复制任务里的 image.sha256>",
                "task_sha256": "<复制任务里的 task_sha256>",
                "references_sha256": {"<reference path>": "<复制任务里的 sha256>"},
                "evaluator": {"model": "<具体模型名>", "version": "<版本或日期>", "reviewed_at": "<ISO-8601>"},
                "scores": {"face": "1-5（按轴要求的子项）"},
                "verdict": "pass | suspect",
                "notes": "一句话证据",
            }]
        },
        "task_count": len(tasks),
        "tasks": tasks,
    }


def write_tasks(root: str) -> str:
    payload = build_tasks(root)
    out = tasks_path(root)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return out


def load_verdicts(root: str) -> Dict[str, Dict[str, Any]]:
    """task_id → 合同有效的裁决记录；sha 过期（该 clip 已重抽）或缺 evaluator 的旧裁决被丢弃。"""
    tasks = load_json(tasks_path(root), {}) or {}
    verdict_payload = load_json(verdicts_path(root), {}) or {}
    expected = {
        str(t.get("task_id")): {
            "image_sha256": str((t.get("image") or {}).get("sha256") or ""),
            "task_sha256": str(t.get("task_sha256") or ""),
            "references_sha256": t.get("references_sha256") if isinstance(t.get("references_sha256"), dict) else {},
        }
        for t in (tasks.get("tasks") or [])
        if isinstance(t, dict)
    }
    out: Dict[str, Dict[str, Any]] = {}
    for record in verdict_payload.get("verdicts") or []:
        if not isinstance(record, dict):
            continue
        task_id = str(record.get("task_id") or "")
        contract = expected.get(task_id)
        if not contract:
            continue
        evaluator = record.get("evaluator") if isinstance(record.get("evaluator"), dict) else {}
        if str(record.get("image_sha256") or "") != contract["image_sha256"] or not contract["image_sha256"]:
            continue
        if str(record.get("task_sha256") or "") != contract["task_sha256"]:
            continue
        refs = record.get("references_sha256") if isinstance(record.get("references_sha256"), dict) else None
        if refs is None or refs != contract["references_sha256"]:
            continue
        if not str(evaluator.get("model") or "").strip() or not str(evaluator.get("version") or "").strip():
            continue
        out[task_id] = record
    return out


def suspect_verdicts(root: str) -> List[Dict[str, Any]]:
    tasks = load_json(tasks_path(root), {}) or {}
    verdicts = load_verdicts(root)
    out: List[Dict[str, Any]] = []
    for task in tasks.get("tasks") or []:
        record = verdicts.get(str(task.get("task_id")))
        if not record:
            continue
        scores = record.get("scores") if isinstance(record.get("scores"), dict) else {}
        low = [f"{k}={v}" for k, v in scores.items() if isinstance(v, (int, float)) and v <= 2]
        if str(record.get("verdict") or "").lower() == "suspect" or low:
            out.append({"task": task, "verdict": record, "low_scores": low})
    return out


def judge_status(root: str) -> Dict[str, Any]:
    tasks = load_json(tasks_path(root), {}) or {}
    task_list = tasks.get("tasks") or []
    verdicts = load_verdicts(root)
    return {
        "task_count": len(task_list),
        "verdict_count": sum(1 for t in task_list if isinstance(t, dict) and str(t.get("task_id")) in verdicts),
        "tasks_file": "生产数据/vlm_judge/vlm_judge_tasks.json",
        "verdict_file": "生产数据/vlm_judge/vlm_judge_verdicts.json",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root")
    parser.add_argument("--write", action="store_true", help="生成/刷新任务包")
    parser.add_argument("--status", action="store_true", help="输出裁决覆盖率 JSON")
    args = parser.parse_args(argv)
    if args.write:
        out = write_tasks(args.root)
        print(f"[ok] tasks: {out}")
    if args.status or not args.write:
        print(json.dumps(judge_status(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
