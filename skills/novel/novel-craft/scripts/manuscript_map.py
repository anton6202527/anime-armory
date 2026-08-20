#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a manuscript map from outline, scene cards, and drafted chapters."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import date
from typing import Any


_HERE = os.path.dirname(os.path.abspath(__file__))
_NOVEL_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
if _NOVEL_LIB not in sys.path:
    sys.path.insert(0, _NOVEL_LIB)
from craft_profile import (  # noqa: E402
    NARRATIVE_FUNCTION_FIELDS,
    NARRATIVE_FUNCTION_LABELS,
    build_craft_contract_snapshot,
    is_supported_craft_profile,
    narrative_functions,
    requires_traditional_turn,
    resolve_craft_profile,
    validate_craft_contract_snapshot,
)
from project_io import load_project_settings  # noqa: E402

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
    craft_profile = resolve_craft_profile(load_project_settings(root))
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
            "povs": sorted({
                str(s.get(field)).strip()
                for s in chapter_scenes
                for field in ("pov", "viewpoint")
                if str(s.get(field) or "").strip()
            }),
            "unattributed_scene_ids": [
                str(s.get("id") or f"scene-{s.get('scene_no') or '?'}")
                for s in chapter_scenes
                if not str(s.get("pov") or "").strip() and not str(s.get("viewpoint") or "").strip()
            ],
            "primary_desire": _first_nonempty([s.get("desire") for s in chapter_scenes]),
            "primary_obstacle": _first_nonempty([s.get("obstacle") for s in chapter_scenes]),
            "value_shift": _first_nonempty([s.get("value_shift") for s in chapter_scenes]),
            "turn": _first_nonempty([s.get("turn") for s in chapter_scenes]),
            "revelation": _first_nonempty([s.get("revelation") for s in chapter_scenes]),
            "relation_drift": _first_nonempty([s.get("relation_drift") for s in chapter_scenes]),
            "perceptual_shift": _first_nonempty([s.get("perceptual_shift") for s in chapter_scenes]),
            "motif_return": _first_nonempty([s.get("motif_return") for s in chapter_scenes]),
            "deliberate_stasis": _first_nonempty([s.get("deliberate_stasis") for s in chapter_scenes]),
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
        row["narrative_functions"] = list(narrative_functions(row))
        if requires_traditional_turn(craft_profile):
            row["review_use"] = "确认本章是否推进读者承诺、人物选择和价值转折；若缺 turn/value_shift，先回章纲或场景卡。"
        else:
            row["review_use"] = (
                "确认本章登记的叙事功能是否真实成立；turn/value_shift 可由揭示、关系微移、"
                "感知变化、意象复现或有意停滞替代，不因缺传统转折自动判失败。"
            )
        rows.append(row)
    return {
        "schema_version": 1,
        "kind": MAP_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "craft_profile": craft_profile,
        "source_snapshot": build_craft_contract_snapshot(root, craft_profile),
        "chapter_count": len(rows),
        "source": {
            "outline": os.path.exists(os.path.join(root, "设定", "章纲.md")),
            "scene_cards": scene_payload.get("kind") == "novel_scene_cards",
            "chapter_files": len(files),
        },
        "chapters": rows,
    }


def check_map(report: dict[str, Any], project_root: str | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    root = os.path.abspath(project_root or str(report.get("project_root") or "")) if (project_root or report.get("project_root")) else ""
    current_settings = load_project_settings(root) if root and os.path.isdir(root) else {}
    craft_profile = resolve_craft_profile(current_settings if root else report.get("craft_profile"))
    snapshot_validation = (
        validate_craft_contract_snapshot(root, report.get("source_snapshot"), craft_profile)
        if root and os.path.isdir(root)
        else {"fresh": False, "issues": ["project_root_missing"], "current": None}
    )
    source_fresh = bool(snapshot_validation.get("fresh"))
    if not source_fresh:
        findings.append({
            "id": "MANUSCRIPT-MAP-SOURCE-STALE",
            "severity": "blocking",
            "confidence": "contract",
            "message": (
                "manuscript_map 的创作工艺/场景卡来源已变化或缺少快照（"
                + ", ".join(snapshot_validation.get("issues") or ["unknown"])
                + "）；请重跑 manuscript_map.py \"<作品根>\" --write，旧检查不得继续放行。"
            ),
        })
    profile_supported = is_supported_craft_profile(craft_profile)
    traditional = profile_supported and requires_traditional_turn(craft_profile)
    if not profile_supported:
        findings.append({
            "id": "MANUSCRIPT-MAP-CRAFT-PROFILE-UNSUPPORTED",
            "severity": "blocking",
            "confidence": "contract",
            "message": (
                f"创作工艺档={craft_profile} 尚无结构地图适配；请改用 commercial_serial / "
                "genre_novel / literary / experimental，或先补自定义适配。"
            ),
        })
    if report.get("kind") != MAP_KIND:
        findings.append({"id": "MANUSCRIPT-MAP-MISSING", "severity": "blocking", "message": "manuscript_map.json 缺失或格式错误"})
    if not report.get("chapters"):
        findings.append({"id": "MANUSCRIPT-MAP-EMPTY", "severity": "warning", "message": "结构地图没有章节；请先补章纲或场景卡。"})
    for row in report.get("chapters") or []:
        chapter = row.get("chapter")
        if not row.get("outline_beat") and not row.get("scene_ids"):
            findings.append({"id": "MANUSCRIPT-MAP-CHAPTER-UNPLANNED", "severity": "warning", "chapter": chapter, "message": "本章缺章纲和场景卡来源。"})
        if source_fresh and traditional and row.get("scene_count") and not row.get("turn"):
            findings.append({
                "id": "MANUSCRIPT-MAP-TURN-MISSING",
                "severity": "blocking",
                "confidence": "contract",
                "chapter": chapter,
                "message": f"创作工艺档={craft_profile}：本章场景卡缺 turn，无法完成传统转折合同。",
            })
        if source_fresh and traditional and row.get("scene_count") and not row.get("value_shift"):
            findings.append({
                "id": "MANUSCRIPT-MAP-VALUE-SHIFT-MISSING",
                "severity": "blocking",
                "confidence": "contract",
                "chapter": chapter,
                "message": f"创作工艺档={craft_profile}：本章场景卡缺 value_shift，无法完成传统价值变化合同。",
            })
        unattributed = row.get("unattributed_scene_ids")
        if unattributed is None and row.get("scene_count") and not row.get("povs"):
            unattributed = ["unknown"]
        if source_fresh and craft_profile == "literary" and unattributed:
            findings.append({
                "id": "MANUSCRIPT-MAP-VIEWPOINT-MISSING",
                "severity": "blocking",
                "confidence": "contract",
                "chapter": chapter,
                "message": (
                    "创作工艺档=literary：以下场景缺可归属的 POV/viewpoint："
                    + ", ".join(str(item) for item in unattributed)
                    + "；请明确叙述位置，不要求伪填欲望或冲突。"
                ),
            })
        if source_fresh and profile_supported and not traditional and row.get("scene_count") and not narrative_functions(row):
            findings.append({
                "id": "MANUSCRIPT-MAP-NARRATIVE-FUNCTION-MISSING",
                "severity": "warning",
                "confidence": "heuristic",
                "chapter": chapter,
                "message": (
                    f"创作工艺档={craft_profile}：本章未登记叙事功能；可填写 "
                    + " / ".join(NARRATIVE_FUNCTION_FIELDS)
                    + " 中至少一项。是否确实无功能需人工复核，不硬阻断。"
                ),
            })
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": report.get("project_root"),
        "craft_profile": craft_profile,
        "source_snapshot": report.get("source_snapshot"),
        "validated_snapshot": snapshot_validation.get("current"),
        "source_fresh": source_fresh,
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
        f"- 创作工艺档：{resolve_craft_profile(report.get('craft_profile'))}",
        f"- 来源：{report.get('source')}",
        "",
        "| 章 | 标题 | 场景 | POV | 欲望/阻碍 | 转折 | 价值变化 | 其它叙事功能 | 揭示/回收 | 正文 |",
        "|---:|---|---:|---|---|---|---|---|---|---|",
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
                _cell(_narrative_function_summary(row)),
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


def _narrative_function_summary(row: dict[str, Any]) -> str:
    parts = []
    for field, value in narrative_functions(row).items():
        if field in {"turn", "value_shift", "reveal_or_payoff"}:
            continue
        parts.append(f"{NARRATIVE_FUNCTION_LABELS.get(field, field)}={value}")
    return "；".join(parts)


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
# —— 第五轮（场景落地/巧合救场/正犯不避）阈值 ——
GROUNDING_HEAD_CHARS = int(os.environ.get("NOVEL_MM_GROUNDING_HEAD_CHARS", "250"))  # 章首锚定窗口
GROUNDING_MAX_ALERTS = int(os.environ.get("NOVEL_MM_GROUNDING_MAX_ALERTS", "8"))
REPEAT_JACCARD = float(os.environ.get("NOVEL_MM_REPEAT_JACCARD", "0.6"))        # 正犯判定 2-gram 相似度
REPEAT_MAX_ALERTS = int(os.environ.get("NOVEL_MM_REPEAT_MAX_ALERTS", "4"))


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
        sev = (
            "建议级"
            if f.get("severity") == "blocking"
            or f.get("id") == "MANUSCRIPT-MAP-NARRATIVE-FUNCTION-MISSING"
            else "info"
        )
        alerts.append({"type": f.get("id"), "severity": sev, "auto": True,
                       "chapter": f.get("chapter"),
                       "confidence": f.get("confidence") or "heuristic",
                       "note": f"{f.get('message')}（结构地图按创作工艺档检查；这是规划信号，"
                               f"进入审稿链后一律交人工/语义复核，不凭字段启发式硬挡。）"})
    alerts.extend(detect_sequel_gaps(report.get("chapters") or []))
    alerts.extend(detect_dropped_anchors(root, report.get("chapters") or []))
    scenes = _ordered_scenes(root)
    alerts.extend(detect_outcome_signals(scenes))
    alerts.extend(detect_plotline_long_runs(scenes))
    alerts.extend(detect_climax_no_afterwave(root, scenes))
    alerts.extend(detect_grounding_dropped(root, scenes))
    alerts.extend(detect_coincidence_rescue(scenes))
    alerts.extend(detect_repeat_no_variation(scenes))
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


def detect_grounding_dropped(root: str, scenes: list[dict[str, Any]],
                             head_chars: int = GROUNDING_HEAD_CHARS,
                             limit: int = GROUNDING_MAX_ALERTS) -> list[dict[str, Any]]:
    """场景落地对账（编辑实务：换场后前两段内锚定 who/where/when——Writers Helping
    Writers 口径）。场景卡登记了 pov+location(/time)，章首窗口却**谁和哪儿都没出现**
    → 读者悬空开场。与 SENSORY-ANCHOR-DROPPED 同构（计划字段 vs 正文对账）；与
    chapter_transition 的 orphan_chapter_opening 互补（那查与前章人物零交集，这查
    本章自己的计划锚定没写进开头）。故意迷失定向的开场（昏迷醒来）合法，恒 advisory。

    保守判据：pov 与 location/time 词段**双双**零命中才报（任一命中=已锚定）。"""
    files = chapter_files(root)
    first_by_chapter: dict[int, dict[str, Any]] = {}
    for scene in scenes:
        try:
            ch = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            continue
        if ch and ch not in first_by_chapter:
            first_by_chapter[ch] = scene
    alerts: list[dict[str, Any]] = []
    for ch in sorted(first_by_chapter):
        scene = first_by_chapter[ch]
        pov = str(scene.get("pov") or "").strip()
        place_segs = []
        for field in ("location", "time"):
            place_segs.extend(_ANCHOR_SEG_RE.findall(str(scene.get(field) or "")))
        path = files.get(ch)
        if not pov or not place_segs or not path:
            continue
        abs_path = path if os.path.isabs(path) else os.path.join(root, path)
        try:
            with open(abs_path, encoding="utf-8") as f:
                head = f.read()[:head_chars]
        except OSError:
            continue
        # 词段拆到 2-gram 再命中（"城南义庄"要能对上正文只写"义庄"）；误判方向是
        # 多算已锚定 → 压掉告警，保守安全（宁缺毋滥）。
        def _grams(segs):
            out = set()
            for seg in segs:
                out.update(seg[i:i + 2] for i in range(len(seg) - 1))
            return out

        pov_hit = pov in head or any(g in head for g in _grams(_ANCHOR_SEG_RE.findall(pov)))
        place_hit = any(g in head for g in _grams(place_segs))
        if not pov_hit and not place_hit:
            alerts.append({
                "type": "SCENE-GROUNDING-DROPPED", "severity": "info", "auto": True,
                "chapter": ch,
                "note": (f"第{ch}章场景卡登记 pov=「{pov}」、地点/时间=「{'、'.join(place_segs[:3])}」，"
                         f"章首 {head_chars} 字内两者均零命中——换场落地工艺：开场两段内要让读者"
                         f"知道谁在哪（时间跳变还要给时间锚）；补锚定，或确认是有意迷失定向的开场"),
            })
            if len(alerts) >= limit:
                break
    return alerts


_FAVORABLE_OUTCOMES = ("yes", "yes-but")


def detect_coincidence_rescue(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """巧合救场检测（Pixar 第 19 条：巧合送人**进**麻烦是好戏，巧合捞人**出**麻烦是
    作弊）。scene_cards.turn_source=「巧合」且 outcome 有利（yes/yes-but）→ 提示。
    巧合+失败（no-and/no-but）完全合法（制造麻烦），不报。字段只在填了时判定，
    无填充率门槛（枚举自证）。纯函数·可测。"""
    alerts: list[dict[str, Any]] = []
    for scene in scenes:
        if str(scene.get("turn_source") or "").strip() != "巧合":
            continue
        if _outcome(scene) in _FAVORABLE_OUTCOMES:
            alerts.append({
                "type": "TURN-COINCIDENCE-RESCUE", "severity": "建议级", "auto": True,
                "chapter": scene.get("chapter"), "scene_id": scene.get("id"),
                "note": (f"场景 {scene.get('id')} 的转折来源=巧合、结局有利"
                         f"（outcome={_outcome(scene)}）——巧合纪律：巧合可以把人物推进麻烦，"
                         f"不可以把人物捞出麻烦（读者会觉得被骗）；改为主角行动/付代价换来，"
                         f"或回头补一笔伏笔让它变成「伏笔兑现」"),
            })
    return alerts


def _char_2grams(text: str) -> set:
    t = re.sub(r"\s+", "", str(text or ""))
    return {t[i:i + 2] for i in range(len(t) - 1)}


def detect_repeat_no_variation(scenes: list[dict[str, Any]],
                               jaccard_min: float = REPEAT_JACCARD,
                               limit: int = REPEAT_MAX_ALERTS) -> list[dict[str, Any]]:
    """正犯不避检测（金圣叹「正犯法」：同题材重写必须各极其妙；毛宗岗「同树异枝、
    同枝异叶」——重复不是罪，重复而**不变化**才是罪，这正是 AI 长篇的头号病：自我
    复写同型场景）。与 plot_variety 的 beat_cycle 互补：那在正文词面层查桥段循环，
    这在**计划字段层**查场景设计撞车。

    保守判据（全部字段对字段，不做语义分型）：跨章两场景 pov 相同、location 相同
    （均非空）、outcome 相同（非空），且 desire+obstacle 的 char-2gram Jaccard
    ≥ jaccard_min → 同景同人同结局同目标 = 犯而不避。系列套路戏（每卷晋级战）是
    题材合约，人工豁免。纯函数·可测。"""
    keyed = []
    for scene in scenes:
        pov = str(scene.get("pov") or "").strip()
        loc = str(scene.get("location") or "").strip()
        outcome = _outcome(scene)
        grams = _char_2grams(str(scene.get("desire") or "") + str(scene.get("obstacle") or ""))
        try:
            ch = int(scene.get("chapter") or 0)
        except (TypeError, ValueError):
            ch = 0
        if pov and loc and outcome and grams and ch:
            keyed.append((scene, ch, pov, loc, outcome, grams))
    alerts: list[dict[str, Any]] = []
    for i, (sa, cha, pa, la, oa, ga) in enumerate(keyed):
        for sb, chb, pb, lb, ob, gb in keyed[i + 1:]:
            if cha == chb or pa != pb or la != lb or oa != ob:
                continue
            union = ga | gb
            if not union:
                continue
            jac = len(ga & gb) / len(union)
            if jac >= jaccard_min:
                alerts.append({
                    "type": "SCENE-REPEAT-NO-VARIATION", "severity": "建议级", "auto": True,
                    "chapter": chb, "scenes": [str(sa.get("id") or ""), str(sb.get("id") or "")],
                    "similarity": round(jac, 2),
                    "note": (f"第{cha}章 {sa.get('id')} 与第{chb}章 {sb.get('id')} 同 POV、同地点、"
                             f"同结局极性，且目标/阻碍相似度 {jac:.0%}——正犯法纪律（金圣叹）：同类"
                             f"场景可以再写，但须「同树异枝」（换手段/换对手型/换代价/换信息差），"
                             f"照原样重打一遍=自我复写；给后一场至少换两个维度，或删并"),
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
