#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consistency_audit.py — novel-review 一键一致性审计 runner（确定性机检串跑）

把分散在三个 skill 的确定性检测器串成一次调用：
  1) novel-review/mechanical_check.py  —— 格式/字数/章号/视角"我"密度/术语漂移/原文照搬
  2) novel-wiki/logic_sentry.py        —— 死人复活/弃置道具复用/位置跳变（先 wiki_builder 建百科）
  3) novel-review/reader_contract_sentry.py —— 逐章读者契约推进/题旨对齐
  4) novel-style/extract_style.py      —— 文风漂移（每章指纹 vs 锚点指纹）

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
    from consistency_tools import load_style_tool, load_wiki_tools, load_power_system_tool
    wiki_builder, logic_sentry = load_wiki_tools()
except Exception:  # pragma: no cover
    wiki_builder = logic_sentry = None
    load_power_system_tool = None

# 2026 新增检测器：novel-review 同目录直接 import；novel-wiki 系（反派战力/时间线/配角）依赖
# load_wiki_tools 已把 novel-wiki/scripts 加进 sys.path。任一缺失优雅置 None（subrunner 报跳过）。
try:
    import hook_endings, voice_drift, tone_check, thread_resolution, reader_contract_sentry  # noqa: E401  (同目录)
except Exception:  # pragma: no cover
    hook_endings = voice_drift = tone_check = thread_resolution = reader_contract_sentry = None
try:
    import antagonist_scaling, timeline_check, minor_characters  # noqa: E401  (novel-wiki/scripts)
except Exception:  # pragma: no cover
    antagonist_scaling = timeline_check = minor_characters = None
try:
    import foreshadow_ledger  # noqa: E401  (novel-wiki/scripts) — 伏笔超期/烂尾预警
except Exception:  # pragma: no cover
    foreshadow_ledger = None
try:
    extract_style = load_style_tool()
except Exception:  # pragma: no cover
    extract_style = None
try:
    power_system = load_power_system_tool() if load_power_system_tool else None
except Exception:  # pragma: no cover
    power_system = None
try:
    _RESEARCH = os.path.join(_SKILLS, "novel-research", "scripts")
    if _RESEARCH not in sys.path:
        sys.path.insert(0, _RESEARCH)
    import research_pack  # noqa: E402
except Exception:  # pragma: no cover
    research_pack = None
try:
    from settings import get_setting
except Exception:  # pragma: no cover
    def get_setting(root, key, default=None):  # type: ignore
        return default
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
        "reader_contract_sentry": os.path.join(_HERE, "reader_contract_sentry.py"),
        "wiki_builder": getattr(wiki_builder, "__file__", "") if wiki_builder else "",
        "logic_sentry": getattr(logic_sentry, "__file__", "") if logic_sentry else "",
        "extract_style": getattr(extract_style, "__file__", "") if extract_style else "",
        "research_pack": getattr(research_pack, "__file__", "") if research_pack else "",
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
    for key in ("mechanical", "reader_contract", "logic_sentry", "style_drift", "research_fact_support"):
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

    # 传 project_root + 年龄锚点：让账本类检查（伏笔逾期/世界规则/关系温度计/张力账本）在 review 汇总也跑，
    # 不再只在 post_write 单章路径出现（此前 review 漏了这些 ledger 维度）。
    anchors = logic_sentry.load_numeric_anchors(project) if hasattr(logic_sentry, "load_numeric_anchors") else None
    all_alerts = []
    for idx, path in _chapters(project):
        text = read_text(path) if read_text else open(path, encoding="utf-8").read()
        all_alerts += logic_sentry.scan_chapter(wiki, text, idx, project_root=project, numeric_anchors=anchors)
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


def run_power_system(project):
    """力量体系自检（穿越/系统流/修仙的等级·成长值·战力逐章一致性）。

    受 `力量体系自检` 选择点控制：关闭→跳过；仅建议→全降建议级；其余→正常（退档/未知境界=阻断）。
    无 设定/power_system_registry.json 时引擎自身优雅跳过。"""
    if power_system is None:
        return {"ran": False, "skipped": "novel-wiki/power_system 不可导入"}
    mode = str(get_setting(project, "力量体系自检", "开启") or "开启")
    if "关闭" in mode:
        return {"ran": False, "skipped": "力量体系自检=关闭"}
    res = power_system.run(project, advisory_only=("仅建议" in mode))
    if not res.get("ran"):
        return res
    out = os.path.join(project, "审稿", "power_system_findings.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": out, "alerts": res["total"], "blocking": res["blocking"],
            "system_type": res.get("system_type")}


def run_reader_contract(project):
    if reader_contract_sentry is None:
        return {"ran": False, "skipped": "reader_contract_sentry 不可导入"}
    chapters = _chapters(project)
    if not chapters:
        return {"ran": False, "skipped": "无 章节/*.md"}
    summaries = []
    findings = []
    for idx, _path in chapters:
        report = reader_contract_sentry.analyze(project, idx)
        summaries.append({
            "chapter": idx,
            "status": report.get("status"),
            "blocking": report.get("blocking", 0),
            "warnings": report.get("warnings", 0),
        })
        for item in report.get("findings", []):
            item = dict(item)
            item.setdefault("chapter", idx)
            findings.append(item)
    blocking = sum(1 for item in findings if item.get("severity") == "阻断级")
    out = os.path.join(project, "审稿", "reader_contract_sentry_summary.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "blocking": blocking,
            "total": len(findings),
            "chapters": summaries,
            "findings": findings,
        }, f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": out, "alerts": len(findings), "blocking": blocking}


def run_research_fact_support(project):
    if research_pack is None:
        return {"ran": False, "skipped": "novel-research/research_pack.py 不可导入"}
    try:
        res = research_pack.check_project(project, write=True)
    except Exception as exc:  # pragma: no cover
        return {"ran": False, "skipped": f"专业资料包检查失败: {exc}"}
    return {
        "ran": True,
        "json": os.path.join(project, "审稿", "research_fact_support.json"),
        "alerts": int(res.get("total") or 0),
        "blocking": int(res.get("blocking") or 0),
        "detected_domains": res.get("detected_domains") or {},
    }


def _run_detector(label, module, project, out_name):
    """统一 subrunner：缺模块/缺输入优雅跳过；否则 module.analyze(project) → 写 审稿/<out_name>，
    汇总 alerts/blocking（阻断级计数）。新检测器 analyze 均以 project 为首参、其余有默认值。"""
    if module is None:
        return {"ran": False, "skipped": f"{label} 不可导入"}
    try:
        res = module.analyze(project)
    except Exception as exc:  # pragma: no cover
        return {"ran": False, "skipped": f"{label} 调用失败: {exc}"}
    if not isinstance(res, dict):
        return {"ran": False, "skipped": f"{label} 返回异常"}
    alerts = res.get("alerts") or []
    if res.get("ran") is False or (res.get("skipped") and not alerts):
        return {"ran": False, "skipped": res.get("skipped", "skipped")}
    blocking = sum(1 for a in alerts if isinstance(a, dict) and a.get("severity") == "阻断级")
    out = os.path.join(project, "审稿", out_name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    return {"ran": True, "json": out, "alerts": len(alerts), "blocking": blocking}


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
            "reader_contract": run_reader_contract(args.project_path),
            "logic_sentry": run_logic(args.project_path),
            "style_drift": run_style(args.project_path, args.anchor, cache=cache),
            "power_system": run_power_system(args.project_path),
            "research_fact_support": run_research_fact_support(args.project_path),
            # 2026 新增维度（断章钩子/角色语感/情绪曲线/支线收口/反派战力/时间线/配角连续性）
            "hook_endings": _run_detector("断章钩子", hook_endings, args.project_path, "hook_findings.json"),
            "voice_drift": _run_detector("角色语感", voice_drift, args.project_path, "voice_findings.json"),
            "tone_curve": _run_detector("情绪曲线", tone_check, args.project_path, "tone_findings.json"),
            "thread_resolution": _run_detector("支线收口", thread_resolution, args.project_path, "thread_findings.json"),
            "antagonist_scaling": _run_detector("反派战力", antagonist_scaling, args.project_path, "antagonist_findings.json"),
            "timeline": _run_detector("时间线", timeline_check, args.project_path, "timeline_findings.json"),
            "minor_characters": _run_detector("配角连续性", minor_characters, args.project_path, "minor_character_findings.json"),
            # 伏笔超期/烂尾预警：消费 novel-wiki 的伏笔台账，落 审稿/foreshadow_report.json（此前无人接）
            "foreshadow": _run_detector("伏笔超期", foreshadow_ledger, args.project_path, "foreshadow_report.json"),
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
