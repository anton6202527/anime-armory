#!/usr/bin/env python3
"""漫画开发包与分话合同 v2。

实证空档：金瓶梅 10 回只拆 1 回、红楼梦 120 回只拆序章——**没有系列级开发层**，
拆分/编剧直接从"眼前一话"开始，第 2 话就断供。同仓成熟生产线的解法是开发包 gate：拆集写词前
先落系列圣经、改编策略、追更弧、可行性与绿灯签收。漫画裁剪版保留四件套 + 签收
（删掉源模式的时长/配音/视频路由可行性——条漫无时长轴）：

  开发包/adaptation_strategy.json   改编策略：改编边界、爽点承诺账、因果链主干、伏笔账
                                    （补齐 source_semantics 只管语言归一化、不管理解的缺口）
  开发包/season_arc.json            前 3-5 话追更弧：每话核心冲突/结尾模式/承诺兑现位
  脚本/split_blueprint.json         全书拆分蓝图：结构化 source_spans + 每话创作/状态合同
                                    （chapter_beat_audit 的 split_blueprint_missing 检查同一文件）
  开发包/signoff.json               绿灯签收：reviewer/role/time + 对上述文件的 SHA 绑定

默认 report-only；`check --strict` 对缺件/占位/签收过期 exit 2。scaffold 只补缺失文件、
永不覆盖已有内容（草稿由人/上层 agent 填，脚本不自我签收——与源模式同纪律）。

用法：
  cd skills/comic-script/scripts
  python3 development_pack.py <作品根> scaffold --write
  python3 development_pack.py <作品根> check [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chapter_contract import (
    SCHEMA_VERSION,
    parse_numbered_label,
    source_units,
    validate_blueprint,
)

VERSION = 2
KIND = "comic_development_pack_check"
PLACEHOLDER_RE = re.compile(r"待补|待填|TODO|TBD|<[^>]*>|__待", re.IGNORECASE)

STRATEGY_TEMPLATE: Dict[str, Any] = {
    "kind": "comic_adaptation_strategy",
    "version": 2,
    "status": "draft",
    "adaptation_boundary": "待补：哪些内容不改编/如何镜外化（露骨/敏感/超纲情节的处理边界）",
    "promise_ledger": [
        {"promise_id": "PRM_001", "promise": "待补：向读者立的第一个核心悬念/欲望承诺",
         "opened_chapter": "第1话", "payoff_chapter": "待补", "status": "open"},
    ],
    "causality_spine": [
        "待补：全书因果链主干（事件A→导致B→逼出选择C…，改编时不可断的链）",
    ],
    "foreshadowing_ledger": [
        {"setup_id": "FSH_001", "setup": "待补：伏笔内容", "planted_chapter": "第1话",
         "payoff_chapter": "待补", "status": "planted"},
    ],
}

SEASON_ARC_TEMPLATE: Dict[str, Any] = {
    "kind": "comic_season_arc",
    "version": 2,
    "status": "draft",
    "chapters": [
        {"chapter": f"第{i}话", "core_conflict": "待补", "ending_mode": "待补",
         "ending_intent": "待补：悬置/揭示/决定/情绪落点/完整闭合等具体效果",
         "promise_refs": []} for i in range(1, 4)
    ],
}

BLUEPRINT_TEMPLATE: Dict[str, Any] = {
    "kind": "comic_split_blueprint",
    "version": 2,
    "status": "draft",
    "policy": "按戏剧闭环切话，不按字数、格数或源回目硬切；budget 只作软容量意图。",
    "chapters": [
        {
            "chapter": "第1话",
            "chapter_type": "serial",
            "format_profile": "vertical_serial",
            "source_mode": "adapted",
            "source_spans": [
                {"source_path": "源本/待补.txt", "start": "第1章", "end": "第1章"}
            ],
            "reader_promise": "待补：本话向读者承诺什么体验/答案",
            "core_conflict": "待补：谁想要什么、什么在阻止",
            "turning_point": "待补：选择、反转或认知变化",
            "payoff": "待补：本话兑现的爽点/情绪/信息",
            "ending_mode": "cliffhanger",
            "budget": {"unit": "panels", "target": 36, "soft_range": [24, 48]},
            "entry_state": {"story": "待补：本话进入时的剧情状态"},
            "continuity_delta": [
                {
                    "entity_id": "CHAR_MAIN",
                    "field": "story_state",
                    "from": "待补：进入状态",
                    "to": "待补：不可逆新状态",
                    "panel_id": "P001",
                    "reason": "待补：哪个可见事件造成变化",
                }
            ],
            "exit_state": {"story": "待补：下话必须继承的退出状态"},
            "status": "draft"
        },
    ],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def pack_files(root: Path) -> Dict[str, Path]:
    return {
        "adaptation_strategy": root / "开发包" / "adaptation_strategy.json",
        "season_arc": root / "开发包" / "season_arc.json",
        "split_blueprint": root / "脚本" / "split_blueprint.json",
        "signoff": root / "开发包" / "signoff.json",
    }


def scaffold(root: Path, *, write: bool) -> List[str]:
    created: List[str] = []
    templates = {
        "adaptation_strategy": STRATEGY_TEMPLATE,
        "season_arc": SEASON_ARC_TEMPLATE,
        "split_blueprint": BLUEPRINT_TEMPLATE,
    }
    files = pack_files(root)
    for key, template in templates.items():
        path = files[key]
        if path.is_file():
            continue
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(str(path.relative_to(root)))
    return created


def contains_placeholder(value: Any) -> bool:
    return bool(PLACEHOLDER_RE.search(json.dumps(value, ensure_ascii=False)))


def _coverage_issues(blueprint: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Check deterministic gaps/overlaps in declared source ranges.

    A deliberate gap/overlap remains possible, but it must be documented on
    the later span as ``coverage_exception``.  No prose heuristic is used.
    """
    issues: List[Dict[str, str]] = []
    previous: Dict[tuple[str, str], tuple[int, int, str]] = {}
    whole_file_seen: Dict[str, str] = {}
    chapters = blueprint.get("chapters") if isinstance(blueprint.get("chapters"), list) else []
    for entry in chapters:
        if not isinstance(entry, Mapping) or entry.get("source_mode", "adapted") != "adapted":
            continue
        chapter = str(entry.get("chapter") or "?")
        for span in entry.get("source_spans") or []:
            if not isinstance(span, Mapping):
                continue
            if span.get("whole_file") is True:
                source_path = str(span.get("source_path") or "")
                prior_chapter = whole_file_seen.get(source_path)
                if prior_chapter and not str(span.get("coverage_exception") or "").strip():
                    issues.append({
                        "code": "source_coverage_whole_file_overlap",
                        "message": f"{source_path} 已由 {prior_chapter} 整文件消费，{chapter} 再次消费须写 coverage_exception。",
                    })
                whole_file_seen[source_path] = chapter
                continue
            start = parse_numbered_label(span.get("start"))
            end = parse_numbered_label(span.get("end") or span.get("start"))
            source_path = str(span.get("source_path") or "")
            if not start or not end or start[1] != end[1]:
                continue
            key = (source_path, start[1])
            prior = previous.get(key)
            exception = str(span.get("coverage_exception") or "").strip()
            if prior:
                prior_start, prior_end, prior_chapter = prior
                if start[0] <= prior_end and not exception:
                    issues.append({
                        "code": "source_coverage_overlap",
                        "message": f"{source_path} {prior_chapter} 与 {chapter} 的 {start[1]}范围重叠；"
                                   "确需复用时在后者写 coverage_exception。",
                    })
                elif start[0] > prior_end + 1 and not exception:
                    issues.append({
                        "code": "source_coverage_gap",
                        "message": f"{source_path} 从第{prior_end + 1}{start[1]}到第{start[0] - 1}{start[1]}"
                                   "未被话次覆盖；删改/延后必须写 coverage_exception。",
                    })
                if start[0] < prior_start and not exception:
                    issues.append({
                        "code": "source_coverage_order_reversed",
                        "message": f"{source_path} 在 {chapter} 的源范围早于 {prior_chapter}；"
                                   "如为倒叙复用请写 coverage_exception。",
                    })
            previous[key] = (start[0], max(end[0], prior[1] if prior else end[0]), chapter)
    return issues


def _read_source_text(path: Path) -> str | None:
    """Read a declared source file with the semantic gate's reader (TXT/MD/JSON/DOCX)."""
    try:
        from source_semantics_gate import read_text
    except Exception:
        return None
    try:
        return read_text(path)
    except Exception:
        return None


def _planned_units(blueprint: Mapping[str, Any]) -> tuple[Dict[str, set[int]], Dict[str, set[str]], set[str]]:
    """Collect planned unit numbers per source_path, plus declared kinds and whole-file sources."""
    planned: Dict[str, set[int]] = {}
    kinds: Dict[str, set[str]] = {}
    whole_file: set[str] = set()
    for entry in blueprint.get("chapters") or []:
        if not isinstance(entry, Mapping) or entry.get("source_mode", "adapted") != "adapted":
            continue
        for span in entry.get("source_spans") or []:
            if not isinstance(span, Mapping):
                continue
            source_path = str(span.get("source_path") or "").strip()
            if not source_path:
                continue
            if span.get("whole_file") is True:
                whole_file.add(source_path)
                continue
            start = parse_numbered_label(span.get("start"))
            end = parse_numbered_label(span.get("end") or span.get("start"))
            if not start or not end or start[1] != end[1]:
                continue
            planned.setdefault(source_path, set()).update(range(start[0], end[0] + 1))
            kinds.setdefault(source_path, set()).add(start[1])
    return planned, kinds, whole_file


def _coverage_scope_for(blueprint: Mapping[str, Any], source_path: str) -> Mapping[str, Any] | None:
    """Return an explicit partial-coverage declaration applying to ``source_path``."""
    scope = blueprint.get("coverage_scope")
    if not isinstance(scope, Mapping):
        return None
    declared_path = str(scope.get("source_path") or "").strip()
    if declared_path and declared_path != source_path:
        return None
    return scope


def _breadth_issues(root: Path, blueprint: Mapping[str, Any]) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Compare the whole source against what the blueprint actually plans.

    ``_coverage_issues`` only compares *declared* spans against each other, so a
    blueprint that plans 第1话 out of a 120-章 source is internally consistent and
    passes.  Planning breadth can only be judged against the source itself: read
    each declared source, count its units, and subtract the planned union.

    Partial first batches stay legal, but must be declared on the blueprint as
    ``coverage_scope: {planned_through, reason}`` — an explicit, reviewable
    statement instead of silence.  Holes *inside* the declared scope are gaps.
    """
    gaps: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    planned, kinds, whole_file = _planned_units(blueprint)
    for source_path in sorted(planned):
        if source_path in whole_file:
            continue
        path = (root / source_path)
        if not path.is_file():
            continue  # _source_path_issues already reports this
        text = _read_source_text(path)
        if text is None:
            continue
        units = source_units(text)
        declared_kinds = kinds.get(source_path) or set()
        available = {int(unit["number"]) for unit in units if unit.get("kind") in declared_kinds}
        if not available:
            continue  # source has no unit markers in the declared kind — cannot judge breadth
        kind = sorted(declared_kinds)[0]
        uncovered = sorted(available - planned[source_path])
        if not uncovered:
            continue
        scope = _coverage_scope_for(blueprint, source_path)
        through = parse_numbered_label(scope.get("planned_through")) if scope else None
        reason = str(scope.get("reason") or "").strip() if scope else ""
        if scope and through and through[1] == kind and reason:
            inside = [number for number in uncovered if number <= through[0]]
            if inside:
                gaps.append({
                    "code": "source_coverage_incomplete",
                    "message": f"{source_path} 声明 planned_through=第{through[0]}{kind}，但范围内第"
                               f"{'、'.join(str(number) for number in inside[:8])}{kind}未被任何话次规划"
                               f"（共 {len(inside)} 个）。",
                })
            beyond = len(uncovered) - len(inside)
            if beyond:
                warnings.append({
                    "code": "source_beyond_planned_scope",
                    "message": f"{source_path} 共 {len(available)} {kind}，本批规划到第{through[0]}{kind}；"
                               f"其后 {beyond} {kind}尚未规划（已由 coverage_scope 声明：{reason}）。",
                })
            continue
        if scope and not reason:
            gaps.append({
                "code": "coverage_scope_reason_missing",
                "message": f"{source_path} 写了 coverage_scope 却缺 reason——部分覆盖必须说明理由。",
            })
        if scope and through and through[1] != kind:
            gaps.append({
                "code": "coverage_scope_unit_mismatch",
                "message": f"{source_path} 的 coverage_scope.planned_through 用「{through[1]}」，"
                           f"但源的单位是「{kind}」。",
            })
        gaps.append({
            "code": "source_coverage_incomplete",
            "message": f"{source_path} 共 {len(available)} {kind}，只有 {len(planned[source_path] & available)} "
                       f"{kind}进入话次规划；第{'、'.join(str(number) for number in uncovered[:8])}"
                       f"{kind}等 {len(uncovered)} 个未规划。首批只做一部分是合法的，"
                       f"但要在 split_blueprint 顶层写 coverage_scope:{{planned_through, reason}} 明示。",
        })
    return gaps, warnings


def _source_path_issues(root: Path, blueprint: Mapping[str, Any]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    for entry in blueprint.get("chapters") or []:
        if not isinstance(entry, Mapping) or entry.get("source_mode", "adapted") != "adapted":
            continue
        chapter = str(entry.get("chapter") or "?")
        for span in entry.get("source_spans") or []:
            if not isinstance(span, Mapping):
                continue
            raw = str(span.get("source_path") or "").strip()
            if not raw:
                continue
            path = (root / raw).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError:
                issues.append({"code": "source_path_outside_project", "message": f"{chapter} 的 source_path 越出作品根：{raw}"})
                continue
            if not path.is_file():
                issues.append({"code": "source_file_missing", "message": f"{chapter} 声明的源文件不存在：{raw}"})
    return issues


def check_pack(root: Path) -> Dict[str, Any]:
    files = pack_files(root)
    gaps: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    file_status: Dict[str, str] = {}
    hashes: Dict[str, str] = {}
    for key in ("adaptation_strategy", "season_arc", "split_blueprint"):
        path = files[key]
        if not path.is_file():
            gaps.append({"code": f"{key}_missing", "message": f"缺 {path.relative_to(root)}——先 scaffold --write 再填内容。"})
            file_status[key] = "missing"
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            gaps.append({"code": f"{key}_invalid", "message": f"{path.relative_to(root)} 不是合法 JSON。"})
            file_status[key] = "invalid"
            continue
        hashes[key] = sha256_file(path)
        try:
            version = int(data.get("version") or 1) if isinstance(data, Mapping) else 1
        except (TypeError, ValueError):
            version = 0
            gaps.append({"code": f"{key}_version_invalid",
                         "message": f"{path.relative_to(root)} version 必须是整数。"})
        if version < SCHEMA_VERSION:
            gaps.append({"code": f"{key}_migration_required",
                         "message": f"{path.relative_to(root)} 是 v{version}；兼容读取但 strict 放行前须迁移到 v{SCHEMA_VERSION}。"})
        status = str(data.get("status") or "draft")
        if status != "confirmed":
            gaps.append({"code": f"{key}_not_confirmed",
                         "message": f"{path.relative_to(root)} status={status}——内容填完后置 confirmed。"})
        elif contains_placeholder(data):
            gaps.append({"code": f"{key}_placeholder_in_confirmed",
                         "message": f"{path.relative_to(root)} 声明 confirmed 却仍含『待补/TODO』占位——反声明。"})
        if key == "split_blueprint" and isinstance(data, Mapping):
            gaps.extend(validate_blueprint(data))
            gaps.extend(_coverage_issues(data))
            gaps.extend(_source_path_issues(root, data))
            breadth_gaps, breadth_warnings = _breadth_issues(root, data)
            gaps.extend(breadth_gaps)
            warnings.extend(breadth_warnings)
            if status == "confirmed":
                for entry in data.get("chapters") or []:
                    if isinstance(entry, Mapping) and entry.get("status") not in {"confirmed", "locked"}:
                        gaps.append({
                            "code": "chapter_contract_not_confirmed",
                            "message": f"{entry.get('chapter', '?')} status={entry.get('status', 'missing')}；"
                                       "开发包签收前每话合同须 confirmed/locked。",
                        })
        file_status[key] = status
    # 签收：内容 confirmed ≠ 绿灯；还需 reviewer 对当前文件 SHA 签收（脚本不自我签收）
    signoff_path = files["signoff"]
    if not signoff_path.is_file():
        gaps.append({"code": "signoff_missing",
                     "message": "缺 开发包/signoff.json 绿灯签收（reviewer/role/time + 三件套 SHA 绑定）。"})
    else:
        try:
            signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
        except Exception:
            signoff = {}
            gaps.append({"code": "signoff_invalid", "message": "signoff.json 不是合法 JSON。"})
        if signoff:
            if not str(signoff.get("reviewer") or "").strip() or not str(signoff.get("role") or "").strip():
                gaps.append({"code": "signoff_reviewer_missing", "message": "signoff 缺 reviewer/role。"})
            if not str(signoff.get("time") or "").strip():
                gaps.append({"code": "signoff_time_missing", "message": "signoff 缺 time。"})
            bound = signoff.get("file_sha256") if isinstance(signoff.get("file_sha256"), Mapping) else {}
            for key, digest in hashes.items():
                if str(bound.get(key) or "") != digest:
                    gaps.append({"code": f"signoff_stale_{key}",
                                 "message": f"signoff 对 {key} 的 SHA 已过期/缺失——内容改动后须重新签收。"})
    return {
        "kind": KIND, "version": VERSION, "generated_at": now_iso(),
        "files": file_status,
        "file_sha256": hashes,
        "status": "confirmed" if not gaps else "blocked",
        "gaps": gaps,
        "warnings": warnings,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("command", choices=("scaffold", "check"))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="check 缺件/占位/签收过期时 exit 2")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    if ns.command == "scaffold":
        created = scaffold(root, write=ns.write)
        payload = {"created": created, "write": ns.write}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    report = check_pack(root)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"# 漫画开发包体检 · {report['status']}")
        for gap in report["gaps"]:
            print(f"- ⚠️ [{gap['code']}] {gap['message']}")
        if not report["gaps"]:
            print("- ✅ 四件套齐、内容 confirmed、签收 SHA 绑定当前版本")
    if ns.strict and report["status"] != "confirmed":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
