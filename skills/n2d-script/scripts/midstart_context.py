#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold/check the context pack required when n2d starts from a middle chapter.

Usage:
  python3 skills/n2d-script/scripts/midstart_context.py <作品根> scaffold --target 第48章 --window 第45-52章
  python3 skills/n2d-script/scripts/midstart_context.py <作品根> check [--json] [--strict]

The script is deterministic and does not infer story facts. It creates a fill-in
pack, then blocks stage-1 refinement while required lines still contain
placeholders. Filling a field with "无" is valid when the story truly has none.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List

PACK_REL = Path("设定库") / "中段开工前情资产包.md"

REQUIRED_FIELDS = (
    ("target_start", "目标起点"),
    ("window", "制作窗口"),
    ("normal_identity", "主角常态定妆基准"),
    ("current_form", "主角当前章节形态"),
    ("identity_anchors", "主角禁漂锚点"),
    ("power_state", "主角当前战力/境界"),
    ("relationship_state", "主角当前关系状态"),
    ("recap", "前情摘要"),
    ("current_goal", "当前目标"),
    ("main_conflict", "主矛盾"),
    ("open_threads", "未兑现伏笔"),
    ("key_characters", "关键角色卡"),
    ("key_locations", "关键场景卡"),
    ("key_assets", "关键道具/法宝/系统资产"),
    ("boundary_window", "边界复核窗口"),
    ("cold_open", "目标集冷开场"),
    ("go_decision", "允许开工结论"),
)

PLACEHOLDER_RE = re.compile(
    r"(待补|未填写|TODO|TBD|FIXME|待确认|待定|【\s*】|<[^>\n]+>|^\s*[—-]\s*$)",
    re.IGNORECASE,
)


def pack_path(root: Path) -> Path:
    return root / PACK_REL


def template(target: str, window: str, note: str) -> str:
    target = target or "【待补：如 第48章 / 第17集 / 原文 23%-27%】"
    window = window or "【待补：如 第45-52章，至少覆盖前后关键承接】"
    note = f"\n> 开工说明：{note}\n" if note else ""
    return f"""# 中段开工前情资产包

> 用途：当 n2d 不从第1章开始，而从中间章节/中间集开始制作时，先补齐本文件。
> 本文件通过 `midstart_context.py check` 后，再进入正式拆脚本/精修 voiceover。
> 能填“无”的字段请写“无”，不要留“待补”。{note}

## 0. 起点
- 目标起点：{target}
- 制作窗口：{window}
- 起点选择理由：【待补：为什么从这里开始做，是否用于打样/爆点/投放测试】

## 1. 主角角色卡 / 身份基准
- 主角常态定妆基准：【待补：常态年龄、脸型五官、发型、服装、配色、身份阶层；不得混入当前章节临时伤/泪/觉醒态】
- 主角当前章节形态：【待补：本窗口开始时主角身上已有的伤、服装、觉醒态、战损、境界外显等；无则写无】
- 主角禁漂锚点：【待补：3-5 个绝不能漂的识别锚点，如凤眼薄唇/半披黑发/月白旧宫装/左腕淡疤】
- 主角当前战力/境界：【待补：等级、系统数值、武器/法宝、能力限制；无体系则写无】
- 主角当前关系状态：【待补：与男主/反派/同伴/家族/宗门/系统的关系温度与敌友状态】

## 2. 角色形象生命周期
- 生命周期文件：`设定库/characters/_生命周期.md`
- 当前窗口前已发生变化：【待补：按 章节/集 -> 角色 -> 变化 -> 定妆动作 列出；无则写无】
- 当前窗口内预计变化：【待补：哪些角色会换装、觉醒、受伤、变体、年龄跳；无则写无】
- 下游定妆动作：【待补：哪些形态要先建常态定妆，哪些要建当前形态/变体定妆】

## 3. 前情摘要
- 前情摘要：【待补：压缩到 300-800 字，说明到目标起点前主角经历、关键选择、当前处境】
- 当前目标：【待补：目标起点这一段主角想要什么】
- 主矛盾：【待补：目标起点这一段谁阻拦/什么危机/什么误会或谜团】
- 未兑现伏笔：【待补：观众需要知道但本窗口不能提前泄露的伏笔、真相、系统规则；无则写无】

## 4. 关键角色 / 场景 / 道具卡
- 关键角色卡：【待补：列出本窗口会出现的具名角色，说明已建卡路径或待建卡摘要】
- 关键场景卡：【待补：列出本窗口会出现的主场景，说明已建卡路径或待建卡摘要】
- 关键道具/法宝/系统资产：【待补：列出武器、法宝、证物、系统面板、特效 VFX；无则写无】

## 5. 目标章节前后窗口
- 边界复核窗口：{window}
- 窗口前承接点：【待补：目标起点前一幕停在哪里，人物姿态/情绪/信息状态是什么】
- 目标集冷开场：【待补：0-3 秒能抓人的画面/台词/危机；不是过渡交代】
- 窗口后钩子：【待补：本次制作窗口末端准备断在哪里，下一集怎么起】
- 边界决策：【待补：保留 / 并入前集 / 并入后集 / 前后挪段；写原因】

## 6. 开工结论
- 允许开工结论：【待补：可以从该起点开工 / 先补第X章前情 / 先建定妆变体 / 先调整边界】
- 风险备注：【待补：例如主角当前形态易污染常态定妆、关系反转不能提前剧透、战力状态需锁等；无则写无】
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def field_values(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, label in REQUIRED_FIELDS:
        pat = re.compile(rf"^\s*[-*]\s*(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*[:：]\s*(.*)$")
        for line in text.splitlines():
            m = pat.match(line)
            if m:
                out[key] = m.group(1).strip()
                break
    return out


def is_unfilled(value: str) -> bool:
    if not value:
        return True
    stripped = value.strip()
    if stripped in {"", "无"}:
        return False
    return bool(PLACEHOLDER_RE.search(stripped))


def finding(severity: str, code: str, message: str, path: str = "") -> Dict[str, str]:
    item = {"severity": severity, "code": code, "message": message}
    if path:
        item["path"] = path
    return item


def _has_character_card(root: Path) -> bool:
    cdir = root / "设定库" / "characters"
    if not cdir.exists():
        return False
    for p in cdir.glob("*.md"):
        if p.name.startswith("_"):
            continue
        txt = read_text(p)
        if "角色卡" in txt or "锚点" in txt or "定妆" in txt:
            return True
    roster = cdir / "_角色总表.md"
    if roster.exists():
        txt = read_text(roster)
        return bool(re.search(r"^##\s+\S+", txt, re.M)) and "待补" not in txt
    return False


def check(root: Path) -> Dict[str, object]:
    path = pack_path(root)
    findings: List[Dict[str, str]] = []
    if not path.exists():
        findings.append(finding(
            "block",
            "missing_midstart_pack",
            f"缺少中段开工前情资产包：{PACK_REL}；先运行 scaffold 并补齐字段。",
            str(PACK_REL),
        ))
        return {
            "kind": "n2d_midstart_context_check",
            "verdict": "block",
            "path": str(PACK_REL),
            "findings": findings,
        }

    text = read_text(path)
    values = field_values(text)
    for key, label in REQUIRED_FIELDS:
        if key not in values:
            findings.append(finding("block", "missing_field", f"缺字段：{label}", str(PACK_REL)))
        elif is_unfilled(values[key]):
            findings.append(finding("block", "unfilled_field", f"{label} 仍是待补/占位内容。", str(PACK_REL)))

    lifecycle = root / "设定库" / "characters" / "_生命周期.md"
    if not lifecycle.exists():
        findings.append(finding(
            "warn",
            "missing_lifecycle_file",
            "缺角色形象生命周期文件；中段开工建议先建/刷新 `设定库/characters/_生命周期.md`。",
            "设定库/characters/_生命周期.md",
        ))
    if not _has_character_card(root):
        findings.append(finding(
            "warn",
            "character_cards_not_detected",
            "未检测到已填写的角色卡文件；可先把主角和本窗口关键角色拆成独立角色卡。",
            "设定库/characters/",
        ))

    has_block = any(f["severity"] == "block" for f in findings)
    has_warn = any(f["severity"] == "warn" for f in findings)
    verdict = "block" if has_block else ("warn" if has_warn else "pass")
    return {
        "kind": "n2d_midstart_context_check",
        "verdict": verdict,
        "path": str(PACK_REL),
        "findings": findings,
    }


def print_human(report: Dict[str, object]) -> None:
    print(f"中段开工前情资产包：{report['verdict']} ({report['path']})")
    findings = report.get("findings") or []
    if not findings:
        print("通过：必填前情、角色身份、生命周期、窗口边界字段均已填写。")
        return
    for f in findings:
        print(f"- {f['severity'].upper()} {f['code']}: {f['message']}")


def scaffold(root: Path, target: str, window: str, note: str, force: bool) -> Path:
    path = pack_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise FileExistsError(f"{path} 已存在；如需覆盖，加 --force")
    path.write_text(template(target, window, note), encoding="utf-8")
    return path


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="作品根")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="创建中段开工前情资产包模板")
    sc.add_argument("--target", default="", help="目标起点，如 第48章 / 第12集")
    sc.add_argument("--window", default="", help="前后复核窗口，如 第45-52章")
    sc.add_argument("--note", default="", help="写进模板顶部的开工说明")
    sc.add_argument("--force", action="store_true", help="覆盖已有模板")

    ck = sub.add_parser("check", help="检查模板是否仍有待补字段")
    ck.add_argument("--json", action="store_true", help="输出 JSON")
    ck.add_argument("--strict", action="store_true", help="warn 也返回非零")

    args = ap.parse_args(list(argv) if argv is not None else None)
    root = Path(args.root)
    if args.cmd == "scaffold":
        try:
            path = scaffold(root, args.target, args.window, args.note, args.force)
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"已创建：{path}")
        print("下一步：补齐所有【待补】字段，然后运行 check。")
        return 0

    report = check(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    verdict = str(report.get("verdict"))
    if verdict == "block" or (args.strict and verdict == "warn"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
