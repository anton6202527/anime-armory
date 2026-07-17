#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a manuscript map from outline, scene cards, and drafted chapters."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from datetime import date
from typing import Any


MAP_KIND = "novel_manuscript_map"
CHECK_KIND = "novel_manuscript_map_check"
CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def output_paths(root: str) -> tuple[str, str, str]:
    setting_dir = os.path.join(root, "设定")
    return (
        os.path.join(setting_dir, "manuscript_map.json"),
        os.path.join(setting_dir, "manuscript_map.md"),
        os.path.join(setting_dir, "manuscript_map_check.json"),
    )


def parse_outline(root: str) -> dict[int, dict[str, str]]:
    path = os.path.join(root, "设定", "章纲.md")
    out: dict[int, dict[str, str]] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            m = CHAPTER_RE.search(raw)
            if not m:
                continue
            chapter = int(m.group(1))
            out[chapter] = {
                "title": (m.group(2) or "").strip(),
                "outline_beat": (m.group(3) or raw.strip()).strip(),
            }
    return out


def chapter_number_from_path(path: str) -> int | None:
    m = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(m.group(1)) if m else None


def chapter_files(root: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for path in sorted(glob.glob(os.path.join(root, "章节", "第*.md"))):
        number = chapter_number_from_path(path)
        if number is not None:
            out[number] = os.path.relpath(path, root).replace(os.sep, "/")
    return out


def _first_nonempty(values: list[Any]) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def build_map(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    outline = parse_outline(root)
    files = chapter_files(root)
    scene_payload = load_json(os.path.join(root, "设定", "scene_cards.json"), {}) or {}
    scenes = [s for s in scene_payload.get("scenes") or [] if isinstance(s, dict)]
    by_chapter: dict[int, list[dict[str, Any]]] = {}
    for scene in scenes:
        try:
            chapter = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            continue
        if chapter:
            by_chapter.setdefault(chapter, []).append(scene)
    chapters = sorted(set(outline) | set(files) | set(by_chapter))
    rows = []
    for chapter in chapters:
        chapter_scenes = sorted(by_chapter.get(chapter, []), key=lambda s: int(s.get("scene_no") or 0))
        row = {
            "chapter": chapter,
            "title": outline.get(chapter, {}).get("title", ""),
            "chapter_path": files.get(chapter, ""),
            "outline_beat": outline.get(chapter, {}).get("outline_beat", ""),
            "scene_count": len(chapter_scenes),
            "povs": sorted({str(s.get("pov")) for s in chapter_scenes if str(s.get("pov") or "").strip()}),
            "primary_desire": _first_nonempty([s.get("desire") for s in chapter_scenes]),
            "primary_obstacle": _first_nonempty([s.get("obstacle") for s in chapter_scenes]),
            "value_shift": _first_nonempty([s.get("value_shift") for s in chapter_scenes]),
            "turn": _first_nonempty([s.get("turn") for s in chapter_scenes]),
            "aftermath": _first_nonempty([s.get("aftermath") for s in chapter_scenes]),
            "reveal_or_payoff": [
                str(s.get("reveal_or_payoff")).strip()
                for s in chapter_scenes
                if str(s.get("reveal_or_payoff") or "").strip()
            ],
            "sensory_anchors": [
                str(s.get("sensory_anchor")).strip()
                for s in chapter_scenes
                if str(s.get("sensory_anchor") or "").strip()
            ],
            "scene_ids": [str(s.get("id") or "") for s in chapter_scenes if s.get("id")],
        }
        row["review_use"] = "确认本章是否推进读者承诺、人物选择和价值转折；若缺 turn/value_shift，先回章纲或场景卡。"
        rows.append(row)
    return {
        "schema_version": 1,
        "kind": MAP_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "chapter_count": len(rows),
        "source": {
            "outline": os.path.exists(os.path.join(root, "设定", "章纲.md")),
            "scene_cards": scene_payload.get("kind") == "novel_scene_cards",
            "chapter_files": len(files),
        },
        "chapters": rows,
    }


def check_map(report: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if report.get("kind") != MAP_KIND:
        findings.append({"id": "MANUSCRIPT-MAP-MISSING", "severity": "blocking", "message": "manuscript_map.json 缺失或格式错误"})
    if not report.get("chapters"):
        findings.append({"id": "MANUSCRIPT-MAP-EMPTY", "severity": "warning", "message": "结构地图没有章节；请先补章纲或场景卡。"})
    for row in report.get("chapters") or []:
        chapter = row.get("chapter")
        if not row.get("outline_beat") and not row.get("scene_ids"):
            findings.append({"id": "MANUSCRIPT-MAP-CHAPTER-UNPLANNED", "severity": "warning", "chapter": chapter, "message": "本章缺章纲和场景卡来源。"})
        if row.get("scene_count") and not row.get("turn"):
            findings.append({"id": "MANUSCRIPT-MAP-TURN-MISSING", "severity": "blocking", "chapter": chapter, "message": "本章场景卡缺 turn，无法判断价值转折。"})
        if row.get("scene_count") and not row.get("value_shift"):
            findings.append({"id": "MANUSCRIPT-MAP-VALUE-SHIFT-MISSING", "severity": "blocking", "chapter": chapter, "message": "本章场景卡缺 value_shift，review 无法判定推进。"})
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": report.get("project_root"),
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "passed": not blockers,
        "findings": findings,
    }


def render_markdown(report: dict[str, Any], check: dict[str, Any] | None = None) -> str:
    lines = [
        "# Manuscript Map",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- 章节数：{report.get('chapter_count')}",
        f"- 来源：{report.get('source')}",
        "",
        "| 章 | 标题 | 场景 | POV | 欲望/阻碍 | 转折 | 价值变化 | 揭示/回收 | 正文 |",
        "|---:|---|---:|---|---|---|---|---|---|",
    ]
    for row in report.get("chapters") or []:
        lines.append(
            "| "
            + " | ".join([
                str(row.get("chapter")),
                _cell(row.get("title")),
                str(row.get("scene_count")),
                _cell("、".join(row.get("povs") or [])),
                _cell(f"{row.get('primary_desire') or ''} / {row.get('primary_obstacle') or ''}"),
                _cell(row.get("turn")),
                _cell(row.get("value_shift")),
                _cell("；".join(row.get("reveal_or_payoff") or [])),
                _cell(row.get("chapter_path")),
            ])
            + " |"
        )
    if check and check.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in check["findings"]:
            chapter = f" 第{int(item['chapter']):02d}章" if item.get("chapter") else ""
            lines.append(f"- [{item.get('severity')}] {item.get('id')}{chapter}: {item.get('message')}")
    return "\n".join(lines).rstrip() + "\n"


def _cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


SEQUEL_GAP_RUN = 3  # 连续几章"有 turn 无 aftermath"算高压不落地


def detect_sequel_gaps(rows: list[dict[str, Any]], run_len: int = SEQUEL_GAP_RUN) -> list[dict[str, Any]]:
    """Scene-Sequel 落地拍检测（Swain 工艺）：连续 ≥run_len 章场景卡有 turn 却全无
    aftermath（反应→两难→决定）→ advisory。单章无 sequel 完全合法（高压续压是常用
    手法），**连续**多章不落地才是读者疲劳红旗。纯函数·可测。"""
    alerts: list[dict[str, Any]] = []
    run: list[int] = []

    def _flush():
        if len(run) >= run_len:
            alerts.append({
                "type": "SEQUEL-GAP-RUN", "severity": "建议级", "auto": True,
                "chapter": run[0], "chapters": list(run),
                "note": (f"第{run[0]}–{run[-1]}章连续 {len(run)} 章场景卡只有 turn（高压拍）、"
                         f"全无 aftermath（落地拍：反应→两难→决定）——Scene-Sequel 工艺：高潮连打"
                         f"不喘会麻木，情绪要落地读者才记得疼；在其中一章补一段 sequel"
                         f"（工艺见 novel-craft/references/scene-sequel.md）"),
            })
        run.clear()

    for row in rows:
        if row.get("scene_count") and str(row.get("turn") or "").strip() \
                and not str(row.get("aftermath") or "").strip():
            run.append(row.get("chapter"))
        else:
            _flush()
    _flush()
    return alerts


def analyze(root: str) -> dict[str, Any]:
    """consistency_audit 子检测器契约适配：build+check → {ran, alerts, blocking(=0)}。

    结构地图（McKee 价值转变 lint：缺 turn/value_shift/无计划来源）此前只被
    author_workflow/supervisor/pipeline 读，没进 review 汇总——中长篇容易漏跑，
    "连续几章无价值转折"这类传统结构问题到不了修订计划。manuscript_map 自身的
    blocking 语义保留给结构闸；进 review 链一律降 advisory（审稿链的职责是把结构
    缺口带进修订计划，不是拿计划期字段缺失硬挡审稿）。无任何计划源时优雅跳过。"""
    report = build_map(root)
    if not report.get("chapters"):
        return {"ran": False, "skipped": "无章纲/场景卡/正文——没有结构地图可检"}
    check = check_map(report)
    alerts = []
    for f in check.get("findings") or []:
        if f.get("id") == "MANUSCRIPT-MAP-MISSING":
            continue  # build_map 现算的 report 不会缺 kind；该项只对读盘态有意义
        sev = "建议级" if f.get("severity") == "blocking" else "info"
        alerts.append({"type": f.get("id"), "severity": sev, "auto": True,
                       "chapter": f.get("chapter"),
                       "note": f"{f.get('message')}（结构地图·价值转变 lint：每章该有 turn/value_shift，"
                               f"传统手艺是『无转折的场景删掉或合并』）"})
    alerts.extend(detect_sequel_gaps(report.get("chapters") or []))
    alerts.extend(detect_dropped_anchors(root, report.get("chapters") or []))
    return {"ran": True, "alerts": alerts, "total": len(alerts), "blocking": 0}


_ANCHOR_SEG_RE = re.compile(r"[一-鿿]{2,}")


def detect_dropped_anchors(root: str, rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    """意象锚对账（传统"道具戏眼/意象贯穿"手艺）：场景卡登记了 sensory_anchor（本场的
    五感戏眼），但对应章正文里**一个词段都没出现** → 计划的意象被成文丢弃（info）。

    传统手艺：意象锚是场景的记忆点与贯穿线（灶上的药味、指节上的旧疤），计划了不写
    等于场景失去质感抓手；写了别的意象也行——所以只在**完全无命中**时提示，命中任一
    ≥2 字段即视为兑现。读不到正文/锚为空一律跳过，宁缺毋滥。"""
    alerts: list[dict[str, Any]] = []
    for row in rows:
        anchors = [a for a in (row.get("sensory_anchors") or []) if str(a).strip()]
        path = row.get("chapter_path")
        if not anchors or not path:
            continue
        abs_path = path if os.path.isabs(path) else os.path.join(root, path)
        try:
            with open(abs_path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for anchor in anchors:
            segs = _ANCHOR_SEG_RE.findall(str(anchor))
            if not segs:
                continue
            if not any(seg in text for seg in segs):
                alerts.append({
                    "type": "SENSORY-ANCHOR-DROPPED", "severity": "info", "auto": True,
                    "chapter": row.get("chapter"),
                    "note": (f"第{row.get('chapter')}章场景卡登记的意象锚『{str(anchor)[:20]}』"
                             f"在正文零命中——计划的五感戏眼被成文丢弃；补进场景，或回卡改成"
                             f"实际用的意象（意象贯穿是廉价高效的质感手艺）"),
                })
                if len(alerts) >= limit:
                    return alerts
    return alerts


def write_outputs(root: str, report: dict[str, Any], check: dict[str, Any]) -> tuple[str, str, str]:
    json_path, md_path, check_path = output_paths(root)
    write_json(json_path, report)
    write_json(check_path, check)
    write_text(md_path, render_markdown(report, check))
    return json_path, md_path, check_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成/检查长篇结构地图")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_map(root)
    check = check_map(report)
    if args.write:
        json_path, md_path, check_path = write_outputs(root, report, check)
        print(f"[ok] manuscript map JSON → {json_path}")
        print(f"[ok] manuscript map MD   → {md_path}")
        print(f"[ok] manuscript map check→ {check_path}")
    if args.json:
        print(json.dumps({"map": report, "check": check}, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report, check))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
