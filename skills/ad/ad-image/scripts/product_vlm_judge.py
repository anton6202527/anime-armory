#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告产品/品牌 VLM 并排裁决任务包（参照同仓漫画线 vlm_judge 的广告重实现，不跨线 import）。

为什么存在：product_qc 的像素三项（ΔE/dHash/NCC）与 prompt-lint 治"参数对不对"，
contact sheet 归人签收——**没有 agent 看图判"产品长对了没有"**。同仓漫画线 2026-07-17
实证过该空档：参考图全对、prompt 全对，出图仍把主体画错形态；裁决任务包生成后 0 条执行、
无人报警。广告线"产品画错"= 漫画线"虎妖画错"，是最贵的翻车面。

合同（与漫画线同源语义）：
  1) `--write` 按 storyboard 产品镜生成 `生产数据/ad_vlm_judge_tasks.json`：
     每 (产品镜, PROD_/BRAND_ 资产) 一条 product_identity 任务——出图帧 vs registry 定妆参考。
  2) 多模态 agent 逐条并排打分，回填 `生产数据/ad_vlm_judge_verdicts.json`。
  3) 裁决必须原样复制 image_sha256 / task_sha256 / references_sha256，且带
     evaluator{model,version}；重出后 sha 不匹配的旧裁决自动作废，空壳裁决被丢弃。
  4) product_qc.run_qc 消费：suspect/低分→warn finding；任务包有任务但 0 有效裁决→
     `vlm_product_unadjudicated` warn（机检空转）；部分裁决→`vlm_product_partial_coverage` warn。
     经既有 gate/consistency_findings 链自动透出，gate 零改动。

注意：shot_variety 的"有意重复镜豁免"只豁免构图重复维度，不豁免产品身份维度——
hero/endcard 重复镜正应逐镜核对产品长对了没有。裁决只做相对排序/低分预警，
suspect→warn 不→block（启发式不硬挡付费，与 ad score_findings 同纪律）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

KIND_TASKS = "ad_vlm_judge_tasks"
KIND_VERDICTS = "ad_vlm_judge_verdicts"
SCORE_GUIDE = (
    "score 取 1-5：5=与定妆参考完全同一产品；4=细节小偏差不影响认品；"
    "3=可见偏差需人工确认；2=明显漂移（包装/logo/形态变了）；1=完全不是同一个产品/缺席。"
    "只做同批次内相对排序，不追求绝对准确。"
)


def _pq():
    import product_qc  # 延迟 import：product_qc.run_qc 亦延迟 import 本模块，双向惰性避免环
    return product_qc


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def file_sha256(path: Path) -> str:
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


def tasks_path(root: Path) -> Path:
    return Path(root) / "生产数据" / "ad_vlm_judge_tasks.json"


def verdicts_path(root: Path) -> Path:
    return Path(root) / "生产数据" / "ad_vlm_judge_verdicts.json"


def registry_reference_map(root: Path) -> Dict[str, List[str]]:
    """asset_id → 定妆参考图相对路径（存在于盘上的）。快照优先，母本兜底。"""
    root = Path(root)
    out: Dict[str, List[str]] = {}
    for reg_path in (root / "出图" / "共享" / "asset_registry.json", root / "设定库" / "asset_registry.json"):
        data = load_json(reg_path)
        if not isinstance(data, dict):
            continue
        entries: List[Dict[str, Any]] = []
        brand = data.get("brand")
        if isinstance(brand, dict):
            entries.append(brand)
        for key in ("products", "characters", "locations", "assets"):
            entries.extend(x for x in (data.get(key) or []) if isinstance(x, dict))
        for entry in entries:
            aid = str(entry.get("id") or "").strip()
            if not aid or aid in out:
                continue
            raw = entry.get("reference_images") or entry.get("references") or entry.get("reference_paths") or []
            if isinstance(raw, str):
                raw = [raw]
            refs = []
            for item in raw if isinstance(raw, (list, tuple)) else []:
                rel = str(item.get("path") if isinstance(item, dict) else item or "").strip()
                if rel and (root / rel).exists() and rel not in refs:
                    refs.append(rel)
            if refs:
                out[aid] = refs
    return out


def build_tasks(stage_dir: Path, storyboard_arg: Optional[str] = None) -> Dict[str, Any]:
    pq = _pq()
    paths = pq.resolve_paths(Path(stage_dir), storyboard_arg)
    root = paths["root"]
    sb = load_json(paths["storyboard"], {}) or {}
    shot_map = pq.storyboard_shot_by_label(sb)
    ref_map = registry_reference_map(root)
    tasks: List[Dict[str, Any]] = []
    for label in pq.product_shots(sb):
        png = pq._resolve_shot_png(paths["stage_dir"], label)
        if png is None:
            continue
        rel_png = str(png.resolve().relative_to(root.resolve())).replace("\\", "/")
        entry = {"path": rel_png, "sha256": file_sha256(png)}
        for aid in pq.product_asset_ids(shot_map.get(label, {})):
            refs = ref_map.get(aid) or []
            if not refs:
                continue
            tasks.append({
                "task_id": f"{label}__{aid}__product",
                "axis": "product_identity",
                "image": entry,
                "subject": aid,
                "references": refs,
                "question": (
                    f"本镜（{label}）应出现产品/品牌资产 {aid}。并排对照定妆参考："
                    "该资产是否出现在画面、包装结构/logo 位置/品牌色/形态是否为同一个"
                    "（不是同类替代品）、与人物/场景的接触持有关系是否合理。"
                    "分三个子项打分：presence（在场）、structure（结构/包装/logo）、relation（持有/接触关系）。" + SCORE_GUIDE
                ),
            })
    for task in tasks:
        task["references_sha256"] = {rel: file_sha256(root / rel) for rel in task["references"]}
        task["task_sha256"] = task_sha256(task)
    return {
        "kind": KIND_TASKS,
        "schema_version": 1,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "inputs_sha256": {"storyboard": file_sha256(paths["storyboard"])},
        "instructions": (
            "由多模态 agent 逐条执行：打开 image 与 references 并排看，按 question 打分，"
            "写入 verdict 文件。裁决必须原样复制任务里的 image.sha256、task_sha256、"
            "references_sha256，并带 evaluator{model,version}；重出后 sha 不匹配的旧裁决自动作废。"
        ),
        "verdict_file": "生产数据/ad_vlm_judge_verdicts.json",
        "verdict_schema": {
            "verdicts": [{
                "task_id": "<task_id>",
                "image_sha256": "<复制任务里的 image.sha256>",
                "task_sha256": "<复制任务里的 task_sha256>",
                "references_sha256": {"<reference path>": "<复制任务里的 sha256>"},
                "evaluator": {"model": "<具体模型名>", "version": "<版本或日期>", "reviewed_at": "<ISO-8601>"},
                "scores": {"presence": "1-5", "structure": "1-5", "relation": "1-5"},
                "verdict": "pass | suspect",
                "notes": "一句话证据",
            }]
        },
        "task_count": len(tasks),
        "tasks": tasks,
    }


def write_tasks(stage_dir: Path, storyboard_arg: Optional[str] = None) -> Path:
    payload = build_tasks(stage_dir, storyboard_arg)
    root = _pq().resolve_paths(Path(stage_dir), storyboard_arg)["root"]
    out = tasks_path(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def load_verdicts(root: Path) -> Dict[str, Dict[str, Any]]:
    """task_id → 合同有效裁决；sha 过期（重出）或缺 evaluator 的记录被丢弃。"""
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
        tid = str(record.get("task_id") or "")
        contract = expected.get(tid)
        if not contract or not contract["image_sha256"]:
            continue
        evaluator = record.get("evaluator") if isinstance(record.get("evaluator"), dict) else {}
        refs = record.get("references_sha256") if isinstance(record.get("references_sha256"), dict) else None
        if (str(record.get("image_sha256") or "") == contract["image_sha256"]
                and str(record.get("task_sha256") or "") == contract["task_sha256"]
                and refs == contract["references_sha256"]
                and str(evaluator.get("model") or "").strip()
                and str(evaluator.get("version") or "").strip()):
            out[tid] = record
    return out


def judge_status(root: Path) -> Dict[str, Any]:
    tasks = load_json(tasks_path(root), {}) or {}
    task_list = tasks.get("tasks") or []
    verdicts = load_verdicts(root)
    return {
        "task_count": len(task_list),
        "verdict_count": sum(1 for t in task_list if isinstance(t, dict) and str(t.get("task_id")) in verdicts),
        "tasks_file": "生产数据/ad_vlm_judge_tasks.json",
        "verdict_file": "生产数据/ad_vlm_judge_verdicts.json",
    }


def qc_findings(root: Path) -> List[Dict[str, Any]]:
    """折进 product_qc.json 的 findings（用其权威 schema {severity,shot,check,reason,detail}）。"""
    tasks_payload = load_json(tasks_path(root), {}) or {}
    task_list = [t for t in (tasks_payload.get("tasks") or []) if isinstance(t, dict)]
    if not task_list:
        return []
    valid = load_verdicts(root)
    findings: List[Dict[str, Any]] = []
    if not valid:
        findings.append({
            "severity": "warn", "shot": "-", "check": "vlm_product_unadjudicated",
            "reason": (f"VLM 产品裁决空转：任务包已生成 {len(task_list)} 条但 0 条有效裁决——"
                       "产品/品牌身份内容级机检形同虚设，由多模态 agent 逐条看图打分写回 "
                       "生产数据/ad_vlm_judge_verdicts.json"),
            "detail": {"task_count": len(task_list), "verdict_count": 0},
        })
        return findings
    if len(valid) < len(task_list):
        findings.append({
            "severity": "warn", "shot": "-", "check": "vlm_product_partial_coverage",
            "reason": f"VLM 产品裁决覆盖率不足：{len(valid)}/{len(task_list)}——未裁决镜无内容级保障",
            "detail": {"task_count": len(task_list), "verdict_count": len(valid)},
        })
    for task in task_list:
        record = valid.get(str(task.get("task_id")))
        if not record:
            continue
        scores = record.get("scores") if isinstance(record.get("scores"), dict) else {}
        low = [f"{k}={v}" for k, v in scores.items() if isinstance(v, (int, float)) and v <= 2]
        if str(record.get("verdict") or "").lower() == "suspect" or low:
            shot = str(task.get("task_id") or "").split("__", 1)[0]
            findings.append({
                "severity": "warn", "shot": shot, "check": "vlm_product_identity",
                "reason": (f"VLM 并排裁决存疑（{task.get('subject')}）："
                           + ("、".join(low) if low else "verdict=suspect")
                           + (("；" + str(record.get("notes"))) if record.get("notes") else "")
                           + "——并排人审，确认漂移则回 ad-image 重出该镜"),
                "detail": {"task_id": task.get("task_id"), "scores": scores},
            })
    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stage_dir", help="出图/分镜 目录")
    parser.add_argument("--storyboard", default=None)
    parser.add_argument("--write", action="store_true", help="生成/刷新任务包")
    parser.add_argument("--status", action="store_true", help="输出裁决覆盖率 JSON")
    args = parser.parse_args(argv)
    root = _pq().resolve_paths(Path(args.stage_dir), args.storyboard)["root"]
    if args.write:
        out = write_tasks(Path(args.stage_dir), args.storyboard)
        print(f"[ok] tasks: {out}")
    if args.status or not args.write:
        print(json.dumps(judge_status(root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
