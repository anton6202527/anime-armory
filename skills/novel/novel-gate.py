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

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(_HERE, "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from novel_contract import get_product_path, parse_regions
from novel_route import parse_progress, cell_state
from project_io import load_project_settings
from qa_gate import collect_gate_status

def check_wiki_freshness(root):
    wiki_path = get_product_path(root, "wiki")
    if not os.path.exists(wiki_path):
        return {"status": "missing", "reason": "动态百科.json 不存在"}
    
    # 简单的时效检查：百科修改时间 vs 章节目录修改时间
    wiki_mtime = os.path.getmtime(wiki_path)
    chap_dir = os.path.join(root, "章节")
    if os.path.exists(chap_dir):
        chap_mtime = os.path.getmtime(chap_dir)
        if chap_mtime > wiki_mtime:
            return {"status": "stale", "reason": "正文已更新，百科可能过期"}
            
    return {"status": "ok"}

def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {}

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

def check_qa_blockers(root, stage):
    status = collect_gate_status(
        root,
        require_review_report=(stage == "export"),
        export_formats=_export_formats(root) if stage == "export" else None,
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
    qa_blockers, qa_warnings = check_qa_blockers(root, args.stage)
    if qa_blockers:
        results["pass"] = False
        results["blockers"].extend(qa_blockers)
    results["warnings"].extend(qa_warnings)

    # 2. 阶段特定检查
    if args.stage == "drafting" and args.chapter:
        # 检查细纲是否 ✅
        try:
            header, rows = parse_progress(root)
            row = next((r for r in rows if r.get("_ch") == args.chapter), None)
            if row:
                # 兼容不同列名：优先 细纲，次之 状态
                target_col = "细纲" if "细纲" in header else ("状态" if "状态" in header else None)
                if target_col and cell_state(row.get(target_col, "")) != "done":
                    results["pass"] = False
                    results["blockers"].append(f"{args.chapter} {target_col}未完成")
        except Exception as e:
            results["warnings"].append(f"无法读取进度表: {e}")

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
