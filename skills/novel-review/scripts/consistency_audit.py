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
import sys
import json
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_CRAFT = os.path.join(_SKILLS, "novel-craft", "scripts")
if _CRAFT not in sys.path:
    sys.path.insert(0, _CRAFT)
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

try:
    from consistency_tools import load_style_tool, load_wiki_tools
    wiki_builder, logic_sentry = load_wiki_tools()
except Exception:  # pragma: no cover
    wiki_builder = logic_sentry = None
try:
    extract_style = load_style_tool()
except Exception:  # pragma: no cover
    extract_style = None
try:
    from report_snapshot import rel_path, sha256_file, snapshot_chapters
except Exception:  # pragma: no cover
    rel_path = sha256_file = snapshot_chapters = None
try:
    from project_io import list_chapter_files, read_text
except Exception:  # pragma: no cover
    list_chapter_files = read_text = None


CACHE_SCHEMA_VERSION = 1
CACHE_FILE = "consistency_audit_cache.json"


def _chapters(project):
    if list_chapter_files:
        return list_chapter_files(project)
    return []


def _cache_path(project):
    return os.path.join(project, "审稿", CACHE_FILE)


def _load_cache(project):
    path = _cache_path(project)
    if not os.path.exists(path):
        return {"schema_version": CACHE_SCHEMA_VERSION}
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("schema_version") == CACHE_SCHEMA_VERSION:
            return payload
    except Exception:
        pass
    return {"schema_version": CACHE_SCHEMA_VERSION}


def _write_cache(project, cache):
    path = _cache_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cache["schema_version"] = CACHE_SCHEMA_VERSION
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _tool_fingerprint():
    files = {
        "consistency_audit": __file__,
        "mechanical_check": os.path.join(_HERE, "mechanical_check.py"),
        "wiki_builder": getattr(wiki_builder, "__file__", "") if wiki_builder else "",
        "logic_sentry": getattr(logic_sentry, "__file__", "") if logic_sentry else "",
        "extract_style": getattr(extract_style, "__file__", "") if extract_style else "",
    }
    out = {}
    for name, path in files.items():
        if path and os.path.exists(path) and sha256_file:
            out[name] = sha256_file(path)
        else:
            out[name] = ""
    return out


def _anchor_info(project, anchor):
    anchor_path = anchor or os.path.join(project, "设定", "风格指纹.json")
    info = {"path": os.path.abspath(anchor_path), "sha256": None}
    if os.path.exists(anchor_path) and sha256_file:
        info["sha256"] = sha256_file(anchor_path)
    return info


def _audit_options(project, pov, anchor, mn, mx):
    return {
        "pov": pov or "",
        "anchor": _anchor_info(project, anchor),
        "min": mn,
        "max": mx,
        "tool_hashes": _tool_fingerprint(),
    }


def _snapshot(project):
    if snapshot_chapters is None:
        return None
    return snapshot_chapters(project, mode="consistency_audit")


def _result_outputs_exist(result):
    if not isinstance(result, dict):
        return False
    for key in ("mechanical", "logic_sentry", "style_drift"):
        section = result.get(key) or {}
        path = section.get("json")
        if section.get("ran") and path and not os.path.exists(path):
            return False
    return True


def _cached_result(cache, snapshot, options):
    if not snapshot:
        return None
    cached_snapshot = cache.get("source_snapshot") or {}
    if cached_snapshot.get("aggregate_hash") != snapshot.get("aggregate_hash"):
        return None
    if cache.get("options") != options:
        return None
    result = cache.get("result")
    if not _result_outputs_exist(result):
        return None
    return result


def _chapter_sha(path):
    if sha256_file is None:
        return None
    return sha256_file(path)


def _chapter_rel(project, path):
    if rel_path:
        return rel_path(project, path)
    return os.path.relpath(os.path.abspath(path), os.path.abspath(project)).replace(os.sep, "/")


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
        text = read_text(path) if read_text else open(path, encoding="utf-8").read()
        all_alerts += logic_sentry.scan_chapter(wiki, text, idx)
    summary = os.path.join(project, "审稿", "logic_alerts_summary.json")
    os.makedirs(os.path.dirname(summary), exist_ok=True)
    blocking = sum(1 for a in all_alerts if a["severity"] == "阻断级")
    with open(summary, "w", encoding="utf-8") as f:
        json.dump({"blocking": blocking, "total": len(all_alerts), "alerts": all_alerts},
                  f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": summary, "alerts": len(all_alerts), "blocking": blocking}


def run_style(project, anchor, cache=None):
    if extract_style is None:
        return {"ran": False, "skipped": "novel-style 脚本不可导入"}
    anchor_path = anchor or os.path.join(project, "设定", "风格指纹.json")
    if not os.path.exists(anchor_path):
        return {"ran": False, "skipped": f"无锚点指纹 {anchor_path}——先跑 extract_style.py 提取锚点章指纹"}
    anchor_fp = extract_style._load_fp_or_text(anchor_path)
    drifts = []
    style_cache = None
    cache_hits = 0
    cache_misses = 0
    if cache is not None:
        style_cache = cache.setdefault("style_fingerprints", {})
    for idx, path in _chapters(project):
        rel = _chapter_rel(project, path)
        sha = _chapter_sha(path)
        cached = style_cache.get(rel) if style_cache is not None else None
        if cached and cached.get("sha256") == sha and cached.get("fingerprint"):
            cand = cached["fingerprint"]
            cache_hits += 1
        else:
            text = read_text(path) if read_text else open(path, encoding="utf-8").read()
            cand = extract_style.fingerprint(text, source=f"第{idx}章")
            if style_cache is not None:
                style_cache[rel] = {"sha256": sha, "fingerprint": cand}
            cache_misses += 1
        res = extract_style.compare(anchor_fp, cand)
        if res["drift_flag"]:
            drifts.append({"chapter": idx, "drift_score": res["drift_score"],
                           "flags": [fl["metric"] for fl in res["flags"]]})
    summary = os.path.join(project, "审稿", "style_drift_summary.json")
    with open(summary, "w", encoding="utf-8") as f:
        json.dump({"anchor": anchor_path, "drifted_chapters": drifts}, f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": summary, "drifted": len(drifts),
            "cache_hits": cache_hits, "cache_misses": cache_misses}


def main():
    p = argparse.ArgumentParser(description="novel-review 一键一致性机检 runner")
    p.add_argument("project_path")
    p.add_argument("--pov", default=None, help="第三人称限定 POV 角色名")
    p.add_argument("--anchor", default=None, help="文风锚点指纹/章节路径")
    p.add_argument("--min", type=int, default=800)
    p.add_argument("--max", type=int, default=1800)
    p.add_argument("--no-cache", action="store_true", help="忽略 consistency_audit_cache.json，强制重跑")
    args = p.parse_args()

    snapshot = _snapshot(args.project_path)
    options = _audit_options(args.project_path, args.pov, args.anchor, args.min, args.max)
    cache = _load_cache(args.project_path)
    result = None if args.no_cache else _cached_result(cache, snapshot, options)
    if result:
        result = dict(result)
        result["_cache"] = {"hit": True, "path": _cache_path(args.project_path)}
    else:
        result = {
            "mechanical": run_mechanical(args.project_path, args.pov, args.min, args.max),
            "logic_sentry": run_logic(args.project_path),
            "style_drift": run_style(args.project_path, args.anchor, cache=cache),
            "_cache": {"hit": False, "path": _cache_path(args.project_path)},
        }
        if snapshot:
            cache["source_snapshot"] = snapshot
            cache["options"] = options
            cache["result"] = result
            _write_cache(args.project_path, cache)
    out = os.path.join(args.project_path, "审稿", "consistency_audit.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"一致性机检汇总 → {out}")
    if result.get("_cache", {}).get("hit"):
        print(f"  ♻️  命中缓存：{result['_cache']['path']}")
    for name, r in result.items():
        if name.startswith("_"):
            continue
        if r.get("ran"):
            extra = {k: v for k, v in r.items() if k in ("alerts", "blocking", "drifted", "returncode", "cache_hits", "cache_misses")}
            print(f"  ✅ {name}: {extra or 'done'}")
        else:
            print(f"  ⏭️  {name} 跳过: {r.get('skipped')}")
    print("  （语义项 OOC/节奏/锚点语义不在机检内，仍需 LLM 人判——见 SKILL 模式①）")


if __name__ == "__main__":
    main()
