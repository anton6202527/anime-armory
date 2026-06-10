#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consistency_audit.py — novel-review 一键一致性审计 runner（确定性机检串跑）

把分散在三个 skill 的确定性检测器串成一次调用，对标 n2d-review/consistency_audit.py：
  1) novel-review/mechanical_check.py  —— 格式/字数/章号/视角"我"密度/术语漂移/原文照搬
  2) novel-wiki/logic_sentry.py        —— 死人复活/弃置道具复用/位置跳变（先 wiki_builder 建百科）
  3) novel-style/extract_style.py      —— 文风漂移（每章指纹 vs 锚点指纹）

凡某检测器输入缺失（如没角色卡 / 没锚点指纹）一律**优雅跳过并记录跳过原因**——
不静默略过（无声上限即谎报"全覆盖"，违 repo 留痕约定）。

  python3 consistency_audit.py <作品根> [--pov 角色名] [--anchor 设定/风格指纹.json] [--min 800 --max 1800]

输出：审稿/consistency_audit.json（汇总）+ 各子检测器自己的落盘。
语义项（OOC/节奏/锚点语义）不在此 runner，仍由 LLM 人判（见 SKILL 模式①）。
"""
import os
import re
import sys
import json
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_SKILLS, "novel-wiki", "scripts"))
sys.path.insert(0, os.path.join(_SKILLS, "novel-style", "scripts"))

try:
    import wiki_builder
    import logic_sentry
except Exception:  # pragma: no cover
    wiki_builder = logic_sentry = None
try:
    import extract_style
except Exception:  # pragma: no cover
    extract_style = None


def _chapters(project):
    cdir = os.path.join(project, "章节")
    if not os.path.isdir(cdir):
        return []
    out = []
    for name in os.listdir(cdir):
        if not name.lower().endswith((".md", ".txt")) or name.startswith("_"):
            continue
        m = re.search(r"(\d+)", name)
        out.append((int(m.group(1)) if m else 10 ** 6, os.path.join(cdir, name)))
    out.sort()
    return out


def run_mechanical(project, pov, mn, mx):
    script = os.path.join(_HERE, "mechanical_check.py")
    out_json = os.path.join(project, "审稿", "mechanical_findings.json")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    cmd = [sys.executable, script, project, "--min", str(mn), "--max", str(mx),
           "--json-out", out_json]
    if pov:
        cmd += ["--pov", pov]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {"ran": True, "returncode": r.returncode, "json": out_json,
                "tail": (r.stdout or r.stderr)[-400:]}
    except Exception as e:
        return {"ran": False, "skipped": f"mechanical_check 调用失败: {e}"}


def run_logic(project):
    if wiki_builder is None or logic_sentry is None:
        return {"ran": False, "skipped": "novel-wiki 脚本不可导入"}
    if not wiki_builder.parse_character_names(project):
        return {"ran": False, "skipped": "无 设定/角色卡.md，无法播种动态百科——先补角色卡"}
    wiki_path = os.path.join(project, "设定", "动态百科.json")
    existing = {}
    if os.path.exists(wiki_path):
        with open(wiki_path, encoding="utf-8") as f:
            existing = json.load(f)
    wiki = wiki_builder.build_wiki(project, existing=existing)
    os.makedirs(os.path.dirname(wiki_path), exist_ok=True)
    with open(wiki_path, "w", encoding="utf-8") as f:
        json.dump(wiki, f, ensure_ascii=False, indent=2)

    all_alerts = []
    for idx, path in _chapters(project):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        all_alerts += logic_sentry.scan_chapter(wiki, text, idx)
    summary = os.path.join(project, "审稿", "logic_alerts_summary.json")
    os.makedirs(os.path.dirname(summary), exist_ok=True)
    blocking = sum(1 for a in all_alerts if a["severity"] == "阻断级")
    with open(summary, "w", encoding="utf-8") as f:
        json.dump({"blocking": blocking, "total": len(all_alerts), "alerts": all_alerts},
                  f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": summary, "alerts": len(all_alerts), "blocking": blocking}


def run_style(project, anchor):
    if extract_style is None:
        return {"ran": False, "skipped": "novel-style 脚本不可导入"}
    anchor_path = anchor or os.path.join(project, "设定", "风格指纹.json")
    if not os.path.exists(anchor_path):
        return {"ran": False, "skipped": f"无锚点指纹 {anchor_path}——先跑 extract_style.py 提取锚点章指纹"}
    anchor_fp = extract_style._load_fp_or_text(anchor_path)
    drifts = []
    for idx, path in _chapters(project):
        with open(path, encoding="utf-8") as f:
            cand = extract_style.fingerprint(f.read(), source=f"第{idx}章")
        res = extract_style.compare(anchor_fp, cand)
        if res["drift_flag"]:
            drifts.append({"chapter": idx, "drift_score": res["drift_score"],
                           "flags": [fl["metric"] for fl in res["flags"]]})
    summary = os.path.join(project, "审稿", "style_drift_summary.json")
    with open(summary, "w", encoding="utf-8") as f:
        json.dump({"anchor": anchor_path, "drifted_chapters": drifts}, f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": summary, "drifted": len(drifts)}


def main():
    p = argparse.ArgumentParser(description="novel-review 一键一致性机检 runner")
    p.add_argument("project_path")
    p.add_argument("--pov", default=None, help="第三人称限定 POV 角色名")
    p.add_argument("--anchor", default=None, help="文风锚点指纹/章节路径")
    p.add_argument("--min", type=int, default=800)
    p.add_argument("--max", type=int, default=1800)
    args = p.parse_args()

    result = {
        "mechanical": run_mechanical(args.project_path, args.pov, args.min, args.max),
        "logic_sentry": run_logic(args.project_path),
        "style_drift": run_style(args.project_path, args.anchor),
    }
    out = os.path.join(args.project_path, "审稿", "consistency_audit.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"一致性机检汇总 → {out}")
    for name, r in result.items():
        if r.get("ran"):
            extra = {k: v for k, v in r.items() if k in ("alerts", "blocking", "drifted", "returncode")}
            print(f"  ✅ {name}: {extra or 'done'}")
        else:
            print(f"  ⏭️  {name} 跳过: {r.get('skipped')}")
    print("  （语义项 OOC/节奏/锚点语义不在机检内，仍需 LLM 人判——见 SKILL 模式①）")


if __name__ == "__main__":
    main()
