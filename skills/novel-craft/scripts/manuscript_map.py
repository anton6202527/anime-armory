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

# —— try-fail / 情节线 / 獭尾 检测阈值（env 可标定）——
OUTCOME_FILL_MIN = float(os.environ.get("NOVEL_MM_OUTCOME_FILL_MIN", "0.5"))    # outcome 填充率低于此整组跳过
OUTCOME_YES_RUN = int(os.environ.get("NOVEL_MM_YES_RUN", "3"))                  # 连续 yes 场景数
OUTCOME_RATIO_MIN_N = int(os.environ.get("NOVEL_MM_YES_RATIO_MIN_N", "10"))     # yes 占比判定最少已填样本
OUTCOME_YES_RATIO = float(os.environ.get("NOVEL_MM_YES_RATIO", "0.6"))          # yes 占比上限
PLOTLINE_FILL_MIN = float(os.environ.get("NOVEL_MM_PLOTLINE_FILL_MIN", "0.5"))  # plotline 填充率下限
PLOTLINE_RUN = int(os.environ.get("NOVEL_MM_PLOTLINE_RUN", "6"))                # 同线连续场景数
CLIMAX_TOPK = int(os.environ.get("NOVEL_MM_CLIMAX_TOPK", "2"))                  # 取张力峰值章数
CLIMAX_MIN_CURVE = int(os.environ.get("NOVEL_MM_CLIMAX_MIN_CURVE", "6"))        # 张力曲线最少章数


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
    scenes = _ordered_scenes(root)
    alerts.extend(detect_outcome_signals(scenes))
    alerts.extend(detect_plotline_long_runs(scenes))
    alerts.extend(detect_climax_no_afterwave(root, scenes))
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


def _ordered_scenes(root: str) -> list[dict[str, Any]]:
    """读 scene_cards.json 并按 (章, 场景号) 排成全书场景序列。纯读·可测。"""
    payload = load_json(os.path.join(root, "设定", "scene_cards.json"), {}) or {}
    if payload.get("kind") != "novel_scene_cards":
        return []
    scenes = [s for s in payload.get("scenes") or [] if isinstance(s, dict)]

    def _key(s: dict[str, Any]):
        try:
            ch = int(s.get("chapter") or 0)
        except (TypeError, ValueError):
            ch = 0
        try:
            no = int(s.get("scene_no") or 0)
        except (TypeError, ValueError):
            no = 0
        return (ch, no, str(s.get("id") or ""))

    return sorted(scenes, key=_key)


def _outcome(scene: dict[str, Any]) -> str:
    return str(scene.get("outcome") or "").strip().lower()


def detect_outcome_signals(scenes: list[dict[str, Any]], run_len: int = OUTCOME_YES_RUN,
                           fill_min: float = OUTCOME_FILL_MIN,
                           ratio_min_n: int = OUTCOME_RATIO_MIN_N,
                           yes_ratio: float = OUTCOME_YES_RATIO) -> list[dict[str, Any]]:
    """try-fail 循环检测（Swain/Sanderson：中段场景结局应以 yes-but / no-and 为主）。

    a) OUTCOME-YES-RUN：连续 ≥run_len 个场景 outcome=yes（干净达成、无代价）——无阻力
       连胜=张力自由落体；中间夹未填 outcome 的场景视为断开（宁漏勿误）。
    b) OUTCOME-NO-COST-CLIMB：全书已填 outcome 中 yes 占比 >yes_ratio（已填样本
       ≥ratio_min_n 才算）——整体无对抗感。
    outcome 是可选引擎字段：填充率 <fill_min 说明本书未启用该纪律，整组优雅跳过
    （对齐 character_arc_audit 的引擎空跳过惯例）。纯函数·可测。"""
    if not scenes:
        return []
    filled = [s for s in scenes if _outcome(s)]
    if len(filled) / len(scenes) < fill_min:
        return []
    alerts: list[dict[str, Any]] = []
    run: list[dict[str, Any]] = []

    def _flush():
        if len(run) >= run_len:
            chapters = sorted({int(s.get("chapter") or 0) for s in run})
            alerts.append({
                "type": "OUTCOME-YES-RUN", "severity": "建议级", "auto": True,
                "chapter": chapters[0],
                "scenes": [str(s.get("id") or "") for s in run],
                "note": (f"第{chapters[0]}–{chapters[-1]}章连续 {len(run)} 个场景 outcome=yes"
                         f"（干净达成、零代价）——try-fail 工艺：中段应以 yes-but（达成但付代价）"
                         f"/ no-and（失败且恶化）为主，无阻力连胜会让张力自由落体；"
                         f"给其中一场加代价或让一场失败"),
            })
        run.clear()

    for scene in scenes:
        if _outcome(scene) == "yes":
            run.append(scene)
        else:
            _flush()
    _flush()
    yes_count = sum(1 for s in filled if _outcome(s) == "yes")
    if len(filled) >= ratio_min_n and yes_count / len(filled) > yes_ratio:
        alerts.append({
            "type": "OUTCOME-NO-COST-CLIMB", "severity": "建议级", "auto": True,
            "chapter": None,
            "note": (f"全书已填 outcome 的 {len(filled)} 个场景中 yes 占比 "
                     f"{yes_count / len(filled):.0%}（>{yes_ratio:.0%}）——主角一路白赢、"
                     f"从不付代价=整体无对抗感；把部分场景改成 yes-but/no-and，"
                     f"胜利要有账单"),
        })
    return alerts


def detect_plotline_long_runs(scenes: list[dict[str, Any]], run_len: int = PLOTLINE_RUN,
                              fill_min: float = PLOTLINE_FILL_MIN) -> list[dict[str, Any]]:
    """横云断山检测（金圣叹：两打祝家庄间插解珍解宝，"恐文字太长便累坠"）。

    同一 plotline 连续 ≥run_len 个场景、无他线插入 → "文长无断"，建议插间笔
    （切支线一场或换视角，回来再续）。plotline 是可选标签：填充率 <fill_min 说明
    本书未启用多线标注，优雅跳过；未填场景视为断开（宁漏勿误）。纯函数·可测。"""
    if not scenes:
        return []
    labels = [str(s.get("plotline") or "").strip() for s in scenes]
    if sum(1 for x in labels if x) / len(scenes) < fill_min:
        return []
    alerts: list[dict[str, Any]] = []
    run: list[dict[str, Any]] = []
    current = ""

    def _flush():
        if current and len(run) >= run_len:
            chapters = sorted({int(s.get("chapter") or 0) for s in run})
            alerts.append({
                "type": "PLOTLINE-LONG-RUN", "severity": "建议级", "auto": True,
                "chapter": chapters[0],
                "scenes": [str(s.get("id") or "") for s in run],
                "note": (f"情节线「{current}」自第{chapters[0]}章起连续 {len(run)} 个场景"
                         f"无他线插入——横云断山工艺：文长无断则累坠，单线连打读者疲劳；"
                         f"插一场支线/换视角间笔再续（高潮连击段可豁免，人工判断）"),
            })
        run.clear()

    for scene, label in zip(scenes, labels):
        if label and label == current:
            run.append(scene)
        else:
            _flush()
            current = label
            if label:
                run.append(scene)
    _flush()
    return alerts


def detect_climax_no_afterwave(root: str, scenes: list[dict[str, Any]],
                               topk: int = CLIMAX_TOPK,
                               min_curve: int = CLIMAX_MIN_CURVE) -> list[dict[str, Any]]:
    """獭尾法检测（金圣叹："一段大文字后，不好寂然便住，须作余波演漾"）——弧线级，
    区别于场景级 SEQUEL-GAP-RUN（那管连续高压不落地，这管**大高潮**后的整章缓冲）。

    读 设定/emotional_progression.json（tone_check --write-progression 回填）取全书
    tension_score top-k 峰值章（峰值须 ≥ 均值+1σ 才算大高潮）；若峰值章最后一个场景无
    aftermath 且下一章第一个场景 conflict 非空（开场即新冲突）→ 高潮无余波。
    曲线不足 min_curve 章 / 无场景卡数据 / 曲线无显著峰 → 优雅跳过。"""
    rows = (load_json(os.path.join(root, "设定", "emotional_progression.json"), {}) or {}).get("chapters") or []
    curve: list[tuple[int, float]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        score = row.get("tension_score")
        if isinstance(score, (int, float)):
            try:
                curve.append((int(row.get("chapter") or 0), float(score)))
            except (TypeError, ValueError):
                continue
    if len(curve) < min_curve or not scenes:
        return []
    values = [v for _, v in curve]
    mean = sum(values) / len(values)
    std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    if std <= 0:
        return []
    peaks = [ch for ch, v in sorted(curve, key=lambda x: -x[1])[:topk] if v >= mean + std]
    by_chapter: dict[int, list[dict[str, Any]]] = {}
    for scene in scenes:
        try:
            ch = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            continue
        by_chapter.setdefault(ch, []).append(scene)
    alerts: list[dict[str, Any]] = []
    for peak in sorted(peaks):
        peak_scenes = by_chapter.get(peak)
        next_scenes = by_chapter.get(peak + 1)
        if not peak_scenes or not next_scenes:
            continue
        last = peak_scenes[-1]
        first_next = next_scenes[0]
        if not str(last.get("aftermath") or "").strip() \
                and str(first_next.get("conflict") or "").strip():
            alerts.append({
                "type": "CLIMAX-NO-AFTERWAVE", "severity": "建议级", "auto": True,
                "chapter": peak,
                "note": (f"第{peak}章是全书张力峰值（大高潮），末场景无 aftermath、"
                         f"第{peak + 1}章开场即新冲突——獭尾法：一段大文字后不好寂然便住，"
                         f"须作余波演漾；给峰值章补一段余波（反应/代价/回望），"
                         f"或让下一章缓开场"),
            })
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
