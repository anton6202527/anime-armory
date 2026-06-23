#!/usr/bin/env python3
"""novel-gate.py — novel 管线准入检查（Gate）。

检查项目在进入特定阶段前的“就绪度”，包括：
1. 细纲就绪：本章是否有细纲？
2. 动态百科新鲜度：百科是否落后于正文？
3. QA 阻断：统一调用 novel QA gate，含 rights/review/score。
4. 导出同步：导出文件是否与正文一致？

用法：
  python3 novel-gate.py <作品根> --chapter <章号> --stage drafting
  python3 novel-gate.py <作品根> --stage export
"""
import os
import sys
import json
import argparse
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(_HERE, "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_contract import get_product_path, parse_regions
from novel_route import parse_progress, cell_state, chapter_number as parse_chapter_number
from project_io import list_chapter_files, load_project_settings, read_text
from qa_gate import collect_gate_status
from report_snapshot import validate_snapshot

_STAGE_TABLE_MARKERS = ("novel-derived-stage-table", "novel-create-stage-table")

def check_wiki_freshness(root):
    wiki_path = get_product_path(root, "wiki")
    if not os.path.exists(wiki_path):
        return {"status": "missing", "reason": "动态百科.json 不存在"}

    snapshot_path = os.path.join(root, "设定", "动态百科.source_snapshot.json")
    if os.path.exists(snapshot_path):
        payload = _load_json(snapshot_path)
        if payload.get("mode") != "wiki:dynamic":
            return {"status": "stale", "reason": "动态百科 source_snapshot 不是全量 wiki:dynamic；请全量重建动态百科。"}
        ok, reason = validate_snapshot(root, payload)
        if ok:
            return {"status": "ok", "reason": "source_snapshot fresh"}
        return {"status": "stale", "reason": f"动态百科 source_snapshot 过期：{reason}"}

    wiki_mtime = os.path.getmtime(wiki_path)
    chapters = list_chapter_files(root, numbered_only=True)
    if chapters:
        latest_chapter_mtime = max(os.path.getmtime(path) for _idx, path in chapters)
        if latest_chapter_mtime > wiki_mtime:
            return {"status": "stale", "reason": "正文已更新，百科可能过期"}
            
    return {"status": "ok"}

def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}

def _is_stage_checklist(root):
    path = os.path.join(root, "_进度.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return False
    return any(marker in text for marker in _STAGE_TABLE_MARKERS)

def _file_nonempty(path):
    return os.path.exists(path) and os.path.getsize(path) > 0

def _outline_has_chapter(root, chapter_num):
    path = os.path.join(root, "设定", "章纲.md")
    if not _file_nonempty(path):
        return False, f"缺少或为空：{path}"
    text = read_text(path)
    pattern = re.compile(r"第\s*0*" + re.escape(str(chapter_num)) + r"\s*章")
    if not pattern.search(text):
        return False, f"章纲未找到第 {chapter_num:02d} 章条目：{path}"
    return True, ""

def _task_packets(root, chapter_num):
    task_dir = os.path.join(root, "写作任务")
    if not os.path.isdir(task_dir):
        return []
    prefix = f"第{chapter_num:02d}章"
    return sorted(name for name in os.listdir(task_dir) if name.startswith(prefix) and name.endswith(".md"))

def _check_progress_outline_done(root, chapter_label):
    blockers = []
    warnings = []
    try:
        header, rows = parse_progress(root)
    except Exception as exc:
        if not _is_stage_checklist(root):
            blockers.append(f"无法读取章节矩阵进度表: {exc}")
        return blockers, warnings

    row = next((r for r in rows if r.get("_ch") == chapter_label), None)
    if row is None:
        blockers.append(f"{chapter_label} 不在进度表")
        return blockers, warnings
    target_col = "细纲" if "细纲" in header else ("状态" if "状态" in header else None)
    if target_col is None:
        blockers.append("进度表缺少 细纲/状态 列，无法证明写作前置阶段完成")
    elif cell_state(row.get(target_col, "")) != "done":
        blockers.append(f"{chapter_label} {target_col}未完成")
    return blockers, warnings

def check_drafting_ready(root, chapter_label):
    blockers = []
    warnings = []
    if not chapter_label:
        return ["drafting gate 必须传 --chapter 第NN章"], warnings
    chapter_num = parse_chapter_number(chapter_label)
    if chapter_num is None:
        return [f"无法识别章节号：{chapter_label}"], warnings
    normalized_label = f"第{chapter_num:02d}章"

    progress_blockers, progress_warnings = _check_progress_outline_done(root, normalized_label)
    blockers.extend(progress_blockers)
    warnings.extend(progress_warnings)

    ok, reason = _outline_has_chapter(root, chapter_num)
    if not ok:
        blockers.append(reason)

    reader_contract = os.path.join(root, "设定", "读者契约.md")
    if not _file_nonempty(reader_contract):
        blockers.append(f"缺少或为空：{reader_contract}")

    meta = _load_json(os.path.join(root, "_meta.json"))
    demo_count = int(meta.get("demo_chapters") or 0)
    is_bulk_chapter = demo_count <= 0 or chapter_num > demo_count
    if is_bulk_chapter:
        if demo_count > 0:
            demo_gate = _load_json(os.path.join(root, "审稿", "demo_gate.json"))
            if demo_gate.get("status") != "passed":
                blockers.append("Demo gate 未通过；批量写章前必须有 审稿/demo_gate.json.status == passed")
        packets = _task_packets(root, chapter_num)
        if not packets:
            blockers.append(f"缺少写作任务包：写作任务/第{chapter_num:02d}章*.md")
        else:
            warnings.append(f"检测到写作任务包：{', '.join(packets)}")
    return blockers, warnings

def _export_formats(root):
    meta = _load_json(os.path.join(root, "_meta.json"))
    formats = []
    outputs = meta.get("outputs")
    if isinstance(outputs, list):
        formats.extend(str(item).strip() for item in outputs)
    elif isinstance(outputs, str):
        formats.extend(str(item).strip() for item in outputs.replace("+", ",").split(","))
    settings = load_project_settings(root)
    formats.extend(parse_regions(settings.get("输出格式", "").replace("+", ",")))
    return [fmt for fmt in formats if fmt]

def _score_required_for_stage(stage):
    # 还没写正文时没有可评分样本；score 的缺失只应在 export / go-no-go 节点阻断。
    if stage in {"drafting", "review", "score"}:
        return False
    return None


def check_qa_blockers(root, stage, chapter_label=None):
    chapter_num = parse_chapter_number(chapter_label) if chapter_label else None
    status = collect_gate_status(
        root,
        require_review_report=(stage == "export"),
        require_score_report=_score_required_for_stage(stage),
        export_formats=_export_formats(root) if stage == "export" else None,
        require_state_closure=(stage in {"review", "score", "export"}),
        state_chapter=chapter_num,
    )
    blockers = []
    for item in status.get("blockers") or []:
        bid = item.get("id") or "-"
        skill = item.get("skill") or "manual"
        reason = item.get("reason") or "未知阻断"
        blockers.append(f"{bid} [{skill}] {reason}")
    warnings = []
    for item in status.get("warnings") or []:
        wid = item.get("id") or "-"
        skill = item.get("skill") or "manual"
        reason = item.get("reason") or "未填写原因"
        warnings.append(f"{wid} [{skill}] {reason}")
    return blockers, warnings

def main():
    p = argparse.ArgumentParser(description="novel 管线准入检查")
    p.add_argument("root")
    p.add_argument("--chapter", help="检查特定章")
    p.add_argument("--stage", choices=["drafting", "review", "score", "export"], required=True)
    args = p.parse_args()

    root = os.path.abspath(args.root)
    results = {"stage": args.stage, "pass": True, "blockers": [], "warnings": []}

    # 1. 通用检查
    qa_blockers, qa_warnings = check_qa_blockers(root, args.stage, args.chapter)
    if qa_blockers:
        results["pass"] = False
        results["blockers"].extend(qa_blockers)
    results["warnings"].extend(qa_warnings)

    # 2. 阶段特定检查
    if args.stage == "drafting":
        drafting_blockers, drafting_warnings = check_drafting_ready(root, args.chapter)
        if drafting_blockers:
            results["pass"] = False
            results["blockers"].extend(drafting_blockers)
        results["warnings"].extend(drafting_warnings)

    if args.stage in ["review", "score"]:
        wiki_status = check_wiki_freshness(root)
        if wiki_status["status"] != "ok":
            results["warnings"].append(f"Wiki: {wiki_status['reason']}")

    # 3. 输出
    if not results["pass"]:
        print(f"❌ Gate Blocked ({args.stage})")
        for b in results["blockers"]:
            print(f"  - [BLOCK] {b}")
    else:
        print(f"✅ Gate Passed ({args.stage})")
        
    for w in results["warnings"]:
        print(f"  - [WARN] {w}")

    if not results["pass"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
