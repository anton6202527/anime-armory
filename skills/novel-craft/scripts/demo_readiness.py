#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-batch demo readiness gate for novel projects.

This deterministic gate does not judge prose by itself. It verifies that the
semantic demo gate, commercial score, and literary/aesthetic anchors have been
recorded before a project moves from demo chapters into bulk drafting.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import date
from typing import Any

_LIB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "novel", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
try:
    from keyword_banks import FLASHBACK_MARKERS
except Exception:
    FLASHBACK_MARKERS = []


READINESS_KIND = "novel_demo_readiness"


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


def commercial_project(root: str, meta: dict[str, Any]) -> bool:
    settings = ""
    path = os.path.join(root, "_设置.md")
    if os.path.exists(path):
        settings = open(path, encoding="utf-8", errors="replace").read()
    text = " ".join([
        str(meta.get("purpose") or ""),
        str(meta.get("target_platform") or ""),
        settings,
    ])
    return any(key in text for key in ("商业连载", "红果", "番茄", "抖音", "漫剧", "短剧", "微短剧", "KDP", "出海", "平台"))


def add_issue(items: list[dict[str, str]], issue_id: str, severity: str, message: str, path: str = "") -> None:
    items.append({"id": issue_id, "severity": severity, "message": message, "path": path})


# ── 黄金三章硬对表（阅文作家专区口径：前三章立矛盾、亮卖点）────────────────────
# 只在 demo 阶段查前 3 章；输入缺失一律优雅跳过（不臆造），慢热文人工豁免。
GOLDEN_CHAPTERS = 3
_TOKEN_STOPWORDS = {"主角", "读者", "故事", "本书", "作品", "开始", "最终", "他们", "自己",
                    "一个", "以及", "或者", "但是", "因为", "所以", "如果", "这个", "那个"}
# 早期闪回闸（Jane Friedman：读者尚未投资当前场景前禁止闪回；编辑退稿实务：开篇
# backstory 过载是标准退稿信号）。判据：前 3 章内单章 ≥N 个段落命中强闪回引导形态
# （词表 keyword_banks.FLASHBACK_MARKERS + "N年前"数量词型）→ warning。
# 单个"想起"不算（太常见）；倒叙框架结构是 premise 级设计，人工豁免。
FLASHBACK_PARAS_WARN = int(os.environ.get("NOVEL_DEMO_FLASHBACK_PARAS", "2"))
_YEARS_AGO_RE = re.compile(r"[一二三五六七八九十几多百\d]+年前")


def _promise_tokens(text: str) -> set[str]:
    """从承诺句抽 2 字以上 CJK 词面 token（长 run 另拆 2-gram），滤停用词。"""
    tokens: set[str] = set()
    for run in re.findall(r"[一-鿿]{2,}", str(text or "")):
        if run not in _TOKEN_STOPWORDS:
            tokens.add(run)
        if len(run) >= 4:
            tokens.update(run[i:i + 2] for i in range(len(run) - 1))
    return {t for t in tokens if t not in _TOKEN_STOPWORDS}


def flashback_paragraphs(text: str) -> int:
    """命中强闪回引导形态的段落数。纯函数·可测。"""
    n = 0
    for para in str(text or "").splitlines():
        p = para.strip()
        if not p:
            continue
        if any(m in p for m in FLASHBACK_MARKERS) or _YEARS_AGO_RE.search(p):
            n += 1
    return n


def golden_chapter_issues(root: str, demo_gate: dict[str, Any], chapters: list[str]) -> list[dict[str, str]]:
    """黄金三章两项硬对表：开端矛盾（scene_cards conflict）+ 核心卖点铺垫（reader_promises 词面）。

    返回 issue 列表（全 warning——开篇好不好终归人判，这里只逮"完全没立/零铺垫"的确定性形态）。
    """
    issues: list[dict[str, str]] = []
    # ① 开端矛盾：前 3 章 scene_cards 的 conflict 字段 ≥ 半数为空 → 矛盾未立
    cards = load_json(os.path.join(root, "设定", "scene_cards.json"), {}) or {}
    if cards.get("kind") == "novel_scene_cards":
        early = [s for s in cards.get("scenes") or []
                 if isinstance(s, dict) and int(s.get("chapter") or 0) in range(1, GOLDEN_CHAPTERS + 1)]
        if early:
            hollow = [s for s in early if not str(s.get("conflict") or "").strip()]
            if len(hollow) * 2 >= len(early):
                add_issue(issues, "DEMO-OPENING-CONFLICT-HOLLOW", "warning",
                          f"黄金三章硬对表：前 {GOLDEN_CHAPTERS} 章 {len(early)} 张场景卡中 {len(hollow)} 张"
                          f" conflict 为空——开端矛盾未立是弃读第一诱因（阅文口径：前三章须立开端矛盾）。",
                          "设定/scene_cards.json")
    # ② 核心卖点铺垫：reader_promises 的词面在前 3 章正文零命中 → 卖点太晚
    reader_contract = demo_gate.get("reader_contract") if isinstance(demo_gate.get("reader_contract"), dict) else {}
    promises = [str(p) for p in (reader_contract.get("reader_promises") or demo_gate.get("reader_promises") or [])
                if str(p or "").strip()]
    if promises and chapters:
        text = ""
        for path in chapters[:GOLDEN_CHAPTERS]:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    text += f.read()
            except OSError:
                pass
        anchor_tokens: set[str] = set()
        for p in promises:
            anchor_tokens |= _promise_tokens(p)
        if anchor_tokens and text and not any(tok in text for tok in anchor_tokens):
            add_issue(issues, "DEMO-SELLING-POINT-LATE", "warning",
                      f"黄金三章硬对表：reader_promises（{len(promises)} 条）的词面在前 "
                      f"{GOLDEN_CHAPTERS} 章正文零命中——核心卖点前三章零铺垫，读者看不到买点"
                      f"（金手指/核心设定至少要强预告）；慢热文请人工豁免。", "审稿/demo_gate.json")
    # ③ 早期闪回：前 3 章任一章 ≥N 段命中强闪回引导 → 开篇回忆杀（第五轮，Q13）
    for i, path in enumerate(chapters[:GOLDEN_CHAPTERS], 1):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                fb = flashback_paragraphs(f.read())
        except OSError:
            continue
        if fb >= FLASHBACK_PARAS_WARN:
            add_issue(issues, "DEMO-EARLY-FLASHBACK", "warning",
                      f"第{i}章有 {fb} 个段落命中强闪回引导（思绪回到/回想起/N年前…，"
                      f"阈 {FLASHBACK_PARAS_WARN}）——开篇回忆杀是标准退稿信号：读者尚未投资"
                      f"当前场景，闪回=把刚点着的火按灭；身世信息推迟或拆进冲突按需露出。"
                      f"倒叙框架结构请人工豁免。", os.path.relpath(path, root))
            break  # 报最早一章即可，避免同病三连报
    return issues


def build_readiness(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    demo_gate = load_json(os.path.join(root, "审稿", "demo_gate.json"), {}) or {}
    score = load_json(os.path.join(root, "评分", "score_report.json"), {}) or {}
    aesthetic = load_json(os.path.join(root, "设定", "aesthetic_bank.json"), {}) or {}
    chapters = sorted(glob.glob(os.path.join(root, "章节", "第*.md")))
    commercial = commercial_project(root, meta)
    issues: list[dict[str, str]] = []

    if demo_gate.get("status") != "passed":
        add_issue(issues, "DEMO-GATE-NOT-PASSED", "blocking", "审稿/demo_gate.json status 不是 passed。", "审稿/demo_gate.json")
    reader_contract = demo_gate.get("reader_contract") if isinstance(demo_gate.get("reader_contract"), dict) else {}
    style_anchor = demo_gate.get("style_anchor") if isinstance(demo_gate.get("style_anchor"), dict) else {}
    if not style_anchor.get("summary"):
        add_issue(issues, "DEMO-STYLE-ANCHOR-WEAK", "warning", "demo_gate 缺少 style_anchor.summary，后续写章文风锚弱。", "审稿/demo_gate.json")
    if not reader_contract:
        add_issue(issues, "DEMO-READER-CONTRACT-MISSING", "warning", "demo_gate 未同步 reader_contract。", "审稿/demo_gate.json")

    decision = (score.get("production_decision") or {}).get("decision") if isinstance(score, dict) else ""
    verdict = score.get("verdict") if isinstance(score, dict) else ""
    if commercial and not score:
        add_issue(issues, "DEMO-COMMERCIAL-SCORE-MISSING", "blocking", "商业/平台项目 Demo 后必须有 opening/full score_report。", "评分/score_report.json")
    elif decision == "kill" or verdict in {"弃稿重立", "kill"}:
        add_issue(issues, "DEMO-COMMERCIAL-SCORE-KILL", "blocking", f"score 结论为 {verdict or decision}，不应批量写。", "评分/score_report.json")
    elif decision in {"revise", "major_rewrite"} or verdict in {"大改", "小改"}:
        add_issue(issues, "DEMO-COMMERCIAL-SCORE-REVISE", "warning", f"score 结论为 {verdict or decision}，批量写前应确认开篇已修。", "评分/score_report.json")

    issues.extend(golden_chapter_issues(root, demo_gate, chapters))

    samples = aesthetic.get("samples") if isinstance(aesthetic, dict) else []
    literary_score = 0
    literary_score += 25 if reader_contract.get("theme") else 0
    literary_score += 20 if reader_contract.get("aesthetic_register") else 0
    literary_score += 20 if style_anchor.get("summary") else 0
    literary_score += 20 if isinstance(samples, list) and samples else 0
    literary_score += 15 if chapters else 0
    if literary_score < 60:
        add_issue(issues, "DEMO-LITERARY-ANCHOR-WEAK", "warning", f"文学/审美锚点分 {literary_score}/100；建议补 reader_contract.aesthetic_register 或 aesthetic_bank。", "设定/aesthetic_bank.json")

    blockers = [item for item in issues if item["severity"] == "blocking"]
    warnings = [item for item in issues if item["severity"] != "blocking"]
    return {
        "schema_version": 1,
        "kind": READINESS_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": root,
        "commercial_project": commercial,
        "demo_chapter_count": len(chapters),
        "ready_for_batch": not blockers,
        "commercial_gate": {
            "score_present": bool(score),
            "decision": decision,
            "verdict": verdict,
            "status": "block" if any(item["id"].startswith("DEMO-COMMERCIAL") and item["severity"] == "blocking" for item in issues) else "pass",
        },
        "literary_gate": {
            "score": literary_score,
            "status": "pass" if literary_score >= 60 else "warning",
            "has_aesthetic_bank": isinstance(samples, list) and bool(samples),
            "has_style_anchor": bool(style_anchor.get("summary")),
            "has_reader_contract": bool(reader_contract),
        },
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "issues": issues,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Demo Readiness",
        "",
        f"- 生成日期：{report.get('generated_at')}",
        f"- commercial_project：{report.get('commercial_project')}",
        f"- ready_for_batch：{report.get('ready_for_batch')}",
        f"- commercial_gate：{report.get('commercial_gate')}",
        f"- literary_gate：{report.get('literary_gate')}",
        "",
        "## Issues",
        "",
    ]
    for item in report.get("issues") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('id')}: {item.get('message')} {item.get('path') or ''}".rstrip())
    if not report.get("issues"):
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_readiness(root: str, report: dict[str, Any]) -> tuple[str, str]:
    json_path = os.path.join(root, "审稿", "demo_readiness.json")
    md_path = os.path.join(root, "审稿", "demo_readiness.md")
    write_json(json_path, report)
    write_text(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查 Demo 章批量写作前准备度")
    parser.add_argument("project_root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    report = build_readiness(root)
    if args.write:
        json_path, md_path = write_readiness(root, report)
        print(f"[ok] demo readiness JSON → {json_path}")
        print(f"[ok] demo readiness MD   → {md_path}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(report))
    return 0 if report.get("ready_for_batch") else 1


if __name__ == "__main__":
    raise SystemExit(main())
