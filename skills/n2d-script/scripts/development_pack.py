#!/usr/bin/env python3
"""P-1 development pack gate for n2d.

This is the pre-production layer before script adaptation.  It scaffolds and
checks the five project-level documents that a short-drama producer would lock
before downstream script/image/video work starts.

Usage:
  python3 development_pack.py <作品根> scaffold --write
  python3 development_pack.py <作品根> check --json --write-missing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from signoff_contract import (  # noqa: E402
    load_manifest as load_signoff_manifest,
    new_manifest as new_signoff_manifest,
    profile_spec as signoff_profile_spec,
    validate_manifest as validate_signoff_manifest,
    write_manifest as write_signoff_manifest,
)

KIND = "n2d_development_pack"
CHECK_KIND = "n2d_development_pack_check"
VERSION = 1
PACK_DIR = "开发包"
PLACEHOLDER_RE = re.compile(r"(待补|待填写|TODO|TBD|__.+?__|<[^>]+>)", re.I)
CONFIRMED_RE = re.compile(r"(?im)^\s*(?:status|状态)\s*[:：]\s*(?:confirmed|已确认|pass|通过)\s*$")

REQUIRED_FILES = (
    "series_bible.md",
    "adaptation_strategy.json",
    "season_arc.json",
    "production_feasibility.json",
    "pilot_greenlight.md",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_if_absent(path: Path, text: str, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_atomic(path, text)
    return True


def write_json_if_absent(path: Path, payload: Mapping[str, Any], *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_json_atomic(path, payload)
    return True


def _source_title(root: Path) -> str:
    for p in sorted((root / "小说").glob("*.txt")):
        return p.stem
    return root.name


def _series_bible(title: str) -> str:
    return f"""---
kind: n2d_development_series_bible
version: 1
status: draft
---
# {title} — P-1 剧集开发圣经

> 这是拆集/写词前的制片开发包。填完后把 `status: draft` 改为 `status: confirmed`。

## 一句话卖点
待补：这部小说改成漫剧后，观众为什么点开并追下去。

## 目标受众
待补：年龄/性别/题材偏好/目标平台/发行地区。

## 主角欲望
待补：主角外在目标、内在缺口、第一季/首批集要解决的核心问题。

## 长线悬念
待补：全剧或首季最大的未解问题、反派/系统/真相/关系钩子。

## 世界观规则
待补：力量体系、系统规则、社会秩序、不可破坏的设定边界。

## 核心爽感
待补：反杀/打脸/升级/复仇/恋爱拉扯/悬疑解谜等可重复爽感机制。

## 关键角色弧
待补：主角、对手、情感线/搭档的 want/need/flaw/arc。
"""


def _adaptation_strategy() -> Dict[str, Any]:
    return {
        "kind": "n2d_development_adaptation_strategy",
        "version": VERSION,
        "status": "draft",
        "generated_at": now_iso(),
        "principles": [
            "待补：改编时保留的核心承诺，例如爽点、人物弧、世界观规则。",
        ],
        "triage_policy": {
            "dramatize": "待补：必须成戏拍出来的段落标准",
            "narrate": "待补：可用 1-2 句旁白带过的信息标准",
            "defer": "待补：后文通过行为/道具/对话带出的信息标准",
            "merge": "待补：并入相邻强戏的过渡段标准",
            "omit": "待补：可删除且不伤动机/因果/伏笔/状态的重复内容标准",
            "rewrite": "待补：允许短剧化改写的边界和必须落账的字段",
        },
        "protected_functions": [
            "人物动机",
            "选择后果",
            "伏笔兑现",
            "状态变化",
            "系统/力量规则",
        ],
        "forbidden_changes": [
            "待补：不能破坏的角色关系、核心设定、价值边界或合规边界",
        ],
    }


def _season_arc() -> Dict[str, Any]:
    return {
        "kind": "n2d_development_season_arc",
        "version": VERSION,
        "status": "draft",
        "generated_at": now_iso(),
        "series_promise": "待补：首季/首批集给观众的追更承诺",
        "front_arc": [
            {
                "episode": "第1集",
                "purpose": "待补：立主角欲望 + 系列总钩",
                "cold_open": "待补：0-3 秒视觉钩",
                "payoff_or_reversal": "待补：本集兑现/反转",
                "cliffhanger": "待补：集尾断点",
            },
            {
                "episode": "第2集",
                "purpose": "待补：承接第1集钩子并抬高代价",
                "cold_open": "待补",
                "payoff_or_reversal": "待补",
                "cliffhanger": "待补",
            },
            {
                "episode": "第3集",
                "purpose": "待补：首个小弧兑现/付费或关注卡点候选",
                "cold_open": "待补",
                "payoff_or_reversal": "待补",
                "cliffhanger": "待补",
            },
        ],
        "monetization_or_follow_points": [
            {
                "position": "待补：第几集/第几秒",
                "promise_before_gate": "待补：卡点前必须先兑现或抬高的承诺",
                "continue_path": "待补：关注/解锁/追更路径",
            }
        ],
        "signature_scenes": [
            "待补：原著名场面/封面级镜头/必须打样的高光段落",
        ],
    }


def _production_feasibility() -> Dict[str, Any]:
    return {
        "kind": "n2d_development_production_feasibility",
        "version": VERSION,
        "status": "draft",
        "generated_at": now_iso(),
        "core_characters": [
            {
                "name": "待补",
                "risk": "脸/服装/形态/表演一致性风险",
                "lock_strategy": "参考图派生 / face_embedding / 主体库 / LoRA",
            }
        ],
        "core_locations": [
            {
                "name": "待补",
                "risk": "空间/光色/复用/转场风险",
                "asset_strategy": "场景卡 + 空镜 + 多机位参考",
            }
        ],
        "props_vfx_spectacle": [
            {
                "name": "待补",
                "risk": "法宝/系统面板/打斗/奇观/VFX 可执行风险",
                "degrade_plan": "拆镜 / overlay / motion control / 人审",
            }
        ],
        "voice_and_music": {
            "voice_risk": "待补：克隆授权、角色音色、占位转真音风险",
            "music_motif": "待补：主角/反派/情绪主题动机",
        },
        "model_route_risks": [
            "待补：生图主体一致性、生视频首尾帧/多帧/原生音画能力、后端 smoke 风险",
        ],
        "compliance_risks": [
            "待补：版权/改编权/角色肖像/声音克隆/平台审核/境内备案/出海本地化",
        ],
    }


def _pilot_greenlight(title: str) -> str:
    return f"""---
kind: n2d_development_pilot_greenlight
version: 1
status: draft
---
# {title} — P-1 试播打样绿灯

> 填完并通过后把 `status: draft` 改为 `status: confirmed`。绿灯前不要批量烧图/烧视频。

## 打样范围
- 待补：第1集完整链路，或第1-3集文字链路 + 高风险 Clip。

## 高风险 Clip 打样清单
| 优先级 | 集/Clip | 为什么必须先打样 | 通过标准 | 失败回退 |
|---|---|---|---|---|
| P0 | 待补 | 主角脸/说话镜/打斗/奇观/核心场景/系统面板等 | 待补 | 待补 |

## 绿灯标准
- 待补：剧本追更承诺成立。
- 待补：主角定妆/身份锁稳定。
- 待补：声音/字幕/口型路线可执行。
- 待补：模型路由与成本在预算内。
- 待补：review-ui / score / dashboard 没有阻断项。

## 小批量放量条件
- 待补：第 1 集或 1-3 集打样通过后，下一批推进到几集、在哪些 gate 停审。
"""


def scaffold(root: Path, *, title: str = "", force: bool = False) -> Dict[str, Any]:
    title = title or _source_title(root)
    base = root / PACK_DIR
    created: List[str] = []
    changed = write_if_absent(base / "series_bible.md", _series_bible(title), force=force)
    if changed:
        created.append(f"{PACK_DIR}/series_bible.md")
    for name, payload in (
        ("adaptation_strategy.json", _adaptation_strategy()),
        ("season_arc.json", _season_arc()),
        ("production_feasibility.json", _production_feasibility()),
    ):
        if write_json_if_absent(base / name, payload, force=force):
            created.append(f"{PACK_DIR}/{name}")
    if write_if_absent(base / "pilot_greenlight.md", _pilot_greenlight(title), force=force):
        created.append(f"{PACK_DIR}/pilot_greenlight.md")
    manifest = {
        "kind": KIND,
        "version": VERSION,
        "status": "draft",
        "generated_at": now_iso(),
        "root": str(root),
        "title": title,
        "required_files": [f"{PACK_DIR}/{name}" for name in REQUIRED_FILES],
        "gate": "run.py script_stage1 prework requires all required files to be confirmed.",
    }
    write_json_atomic(base / "development_pack.json", manifest)
    signoff_spec = signoff_profile_spec(root, "p1")
    signoff_path = root / signoff_spec["signoff_path"]
    if not signoff_path.exists():
        write_signoff_manifest(signoff_path, new_signoff_manifest(
            root,
            artifact_scope=signoff_spec["artifact_scope"],
            author_id="automation:n2d",
            input_paths=signoff_spec["input_paths"],
            evidence_paths=signoff_spec["evidence_paths"],
            required_role_groups=signoff_spec["required_role_groups"],
        ))
    return {"kind": KIND, "root": str(root), "pack_dir": str(base), "created": created, "manifest": f"{PACK_DIR}/development_pack.json"}


def _signoff_status(root: Path) -> Dict[str, Any]:
    spec = signoff_profile_spec(root, "p1")
    path = root / spec["signoff_path"]
    issues = validate_signoff_manifest(
        load_signoff_manifest(path),
        root,
        artifact_scope=spec["artifact_scope"],
        input_paths=spec["input_paths"],
        evidence_paths=spec["evidence_paths"],
        required_role_groups=spec["required_role_groups"],
    )
    return {"rel": spec["signoff_path"], "status": "pass" if not issues else "block", "issues": issues}


def _json_status(path: Path) -> Tuple[str, List[str]]:
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        return "block", ["JSON 无法解析或不是 object"]
    if str(data.get("status") or "").strip().lower() != "confirmed":
        issues.append("status 不是 confirmed")
    blob = json.dumps(data, ensure_ascii=False)
    if PLACEHOLDER_RE.search(blob):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def _md_status(path: Path) -> Tuple[str, List[str]]:
    text = read_text(path)
    issues: List[str] = []
    if not text.strip():
        return "block", ["文件为空"]
    if not CONFIRMED_RE.search(text):
        issues.append("缺 status: confirmed / 状态: confirmed")
    if PLACEHOLDER_RE.search(text):
        issues.append("仍含待补/TODO 占位")
    return ("pass" if not issues else "block"), issues


def check(root: Path, *, write_missing: bool = False) -> Dict[str, Any]:
    if write_missing:
        scaffold(root)
    base = root / PACK_DIR
    rows: List[Dict[str, Any]] = []
    for name in REQUIRED_FILES:
        path = base / name
        rel = f"{PACK_DIR}/{name}"
        if not path.exists():
            rows.append({"rel": rel, "status": "missing", "issues": ["文件缺失"]})
            continue
        status, issues = _json_status(path) if path.suffix == ".json" else _md_status(path)
        rows.append({"rel": rel, "status": status, "issues": issues})
    rows.append(_signoff_status(root))
    blockers = [r for r in rows if r["status"] != "pass"]
    payload = {
        "kind": CHECK_KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": str(root),
        "status": "pass" if not blockers else "block",
        "summary": {
            "required": len(rows),
            "pass": len(rows) - len(blockers),
            "block": len(blockers),
        },
        "files": rows,
        "scaffold_command": f"python3 skills/n2d-script/scripts/development_pack.py {root} scaffold --write",
        "next_when_blocked": (
            "补齐开发包五件套并把内容 status 改为 confirmed；再用 signoff.py 让创意与制片角色分别签收当前文件哈希。"
            "之后重跑 check，再进入首批粗切/阶段1写词。"
        ),
    }
    out = root / "生产数据" / "development_pack_check.json"
    write_json_atomic(out, payload)
    payload["check_path"] = str(out)
    return payload


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# P-1 开发包检查",
        "",
        f"- 状态：{report.get('status')}",
        f"- 通过：{(report.get('summary') or {}).get('pass')}/{(report.get('summary') or {}).get('required')}",
        "",
        "| 文件 | 状态 | 问题 |",
        "|---|---|---|",
    ]
    for row in report.get("files") or []:
        issues = "；".join(row.get("issues") or []) or "-"
        lines.append(f"| `{row.get('rel')}` | {row.get('status')} | {issues} |")
    lines += ["", str(report.get("next_when_blocked") or "")]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    sub = ap.add_subparsers(dest="command", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--write", action="store_true", help="兼容显式写入语义；scaffold 默认即写入")
    p_scaffold.add_argument("--force", action="store_true", help="覆盖已有模板（谨慎）")
    p_scaffold.add_argument("--title", default="")
    p_check = sub.add_parser("check")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--markdown", action="store_true")
    p_check.add_argument("--write-missing", action="store_true", help="缺文件时先补 scaffold，再返回 block")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    if ns.command == "scaffold":
        payload = scaffold(root, title=ns.title, force=ns.force)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    report = check(root, write_missing=ns.write_missing)
    if ns.markdown:
        md = render_markdown(report)
        path = root / "生产数据" / "development_pack_check.md"
        write_atomic(path, md)
        print(md)
    elif ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"P-1 开发包检查：{report['status']} ({report['summary']['pass']}/{report['summary']['required']})")
        if report["status"] != "pass":
            print(report["next_when_blocked"])
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
