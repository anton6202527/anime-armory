#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reader-contract sentry for one finished chapter.

The draft packet already asks the writer to fill `reader_contract_progress` and
`theme_alignment` in `state_delta_第NN章.json`. This script turns that request into
a deterministic post-write gate so long projects cannot drift into "events only"
chapters without acknowledging the book's promise to the reader.
"""
import argparse
import json
import os
import re
import sys
from datetime import date


_CJK_TOKEN = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}")
_STOPWORDS = {
    "本章", "读者", "契约", "推进", "核心", "题旨", "承诺", "必须", "回答",
    "文学", "质感", "好看", "机制", "禁止", "不要", "不能", "未填写",
}


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _chapter_num(value):
    match = re.search(r"(\d+)", str(value))
    if not match:
        raise ValueError(f"无法识别章节号：{value}")
    return int(match.group(1))


def _chapter_file(root, chapter):
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return ""
    pat = re.compile(rf"第\s*0*{chapter}\s*章")
    for name in sorted(os.listdir(chdir)):
        if name.endswith(".md") and pat.search(name):
            return os.path.join(chdir, name)
    fallback = os.path.join(chdir, f"第{chapter:02d}章.md")
    return fallback if os.path.exists(fallback) else ""


def _delta_path(root, chapter):
    return os.path.join(root, "审稿", f"state_delta_第{chapter:02d}章.json")


def _contract_sources(root):
    demo = {}
    demo_path = os.path.join(root, "审稿", "demo_gate.json")
    if os.path.exists(demo_path):
        try:
            demo = _load_json(demo_path)
        except Exception:
            demo = {}
    reader_contract = demo.get("reader_contract") if isinstance(demo.get("reader_contract"), dict) else {}
    contract_text = _read_text(os.path.join(root, "设定", "读者契约.md"))
    return demo, reader_contract, contract_text


def _flatten_contract_items(demo, reader_contract, contract_text):
    items = []
    for key in ("theme", "dramatic_question", "aesthetic_register"):
        if reader_contract.get(key):
            items.append(str(reader_contract[key]))
    for key in ("must_answer", "reader_promises", "delight_engine"):
        items.extend(_as_list(reader_contract.get(key)))
    items.extend(_as_list(demo.get("reader_promises")))
    if contract_text:
        for line in contract_text.splitlines():
            clean = re.sub(r"^[#>\-\*\s\d.、]+", "", line).strip()
            if clean:
                items.append(clean)
    return items


def _banned_items(demo, reader_contract):
    out = []
    out.extend(_as_list(reader_contract.get("banned_drift")))
    out.extend(_as_list(demo.get("banned_drift")))
    seen = set()
    deduped = []
    for item in out:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _tokens(text):
    out = set()
    for tok in _CJK_TOKEN.findall(text or ""):
        if tok in _STOPWORDS:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]{3,}", tok):
            out.add(tok)
            out.update(tok[i:i + 2] for i in range(len(tok) - 1))
        else:
            out.add(tok)
    return out


def _overlap_warning(progress_text, contract_items):
    anchor_tokens = set()
    for item in contract_items:
        anchor_tokens |= _tokens(item)
    if not anchor_tokens:
        return None
    progress_tokens = _tokens(progress_text)
    if progress_tokens & anchor_tokens:
        return None
    return {
        "severity": "建议级",
        "type": "weak_contract_trace",
        "message": "state_delta 写了读者契约推进，但与已登记的题旨/承诺/好看机制缺少明显词面交集；请人工确认不是泛泛而谈。",
        "evidence": progress_text[:160],
    }


def analyze(root, chapter):
    root = os.path.abspath(root)
    blocks = []
    warnings = []

    chapter_path = _chapter_file(root, chapter)
    if not chapter_path:
        blocks.append({
            "severity": "阻断级",
            "type": "chapter_missing",
            "message": f"缺失章节正文：章节/第{chapter:02d}章.md",
        })
        chapter_text = ""
    else:
        chapter_text = _read_text(chapter_path)

    delta_path = _delta_path(root, chapter)
    delta = {}
    if not os.path.exists(delta_path):
        blocks.append({
            "severity": "阻断级",
            "type": "state_delta_missing",
            "message": f"缺失状态增量：审稿/state_delta_第{chapter:02d}章.json",
        })
    else:
        try:
            delta = _load_json(delta_path)
        except json.JSONDecodeError as exc:
            blocks.append({
                "severity": "阻断级",
                "type": "state_delta_invalid_json",
                "message": f"状态增量 JSON 不合法：{exc}",
            })
        if delta and not isinstance(delta, dict):
            blocks.append({
                "severity": "阻断级",
                "type": "state_delta_not_object",
                "message": "状态增量必须是 JSON object。",
            })
            delta = {}

    if delta.get("chapter") is not None:
        try:
            got = int(delta.get("chapter"))
        except (TypeError, ValueError):
            blocks.append({
                "severity": "阻断级",
                "type": "state_delta_chapter_invalid",
                "message": "state_delta.chapter 必须是数字。",
            })
        else:
            if got != chapter:
                blocks.append({
                    "severity": "阻断级",
                    "type": "state_delta_chapter_mismatch",
                    "message": f"state_delta.chapter={got}，但本次检查第{chapter:02d}章。",
                })

    demo, reader_contract, contract_text = _contract_sources(root)
    contract_items = _flatten_contract_items(demo, reader_contract, contract_text)

    progress = _as_list(delta.get("reader_contract_progress"))
    theme_alignment = str(delta.get("theme_alignment") or "").strip()
    if delta and not progress:
        blocks.append({
            "severity": "阻断级",
            "type": "reader_contract_progress_missing",
            "message": "state_delta 缺少 reader_contract_progress；本章必须说明推进了哪项题旨/承诺/关系弧光/秘密揭示/能力代价/文学质感。",
        })
    if delta and not theme_alignment:
        blocks.append({
            "severity": "阻断级",
            "type": "theme_alignment_missing",
            "message": "state_delta 缺少 theme_alignment；本章必须说明它如何对齐核心题旨，不能只记录事件。",
        })

    progress_text = " ".join(progress + ([theme_alignment] if theme_alignment else []))
    if progress_text:
        weak = _overlap_warning(progress_text, contract_items)
        if weak:
            warnings.append(weak)

    for banned in _banned_items(demo, reader_contract):
        if not banned:
            continue
        if banned in progress_text:
            warnings.append({
                "severity": "建议级",
                "type": "banned_drift_in_delta",
                "message": f"state_delta 提到了禁偏项「{banned}」；请确认是在规避它，而不是承认本章已偏。",
                "evidence": banned,
            })
        elif chapter_text and banned in chapter_text:
            warnings.append({
                "severity": "建议级",
                "type": "banned_drift_in_chapter_text",
                "message": f"正文出现禁偏项「{banned}」的精确短语；请人工确认是否误触禁偏清单。",
                "evidence": banned,
            })

    return {
        "schema_version": 1,
        "kind": "reader_contract_sentry",
        "checked_at": date.today().isoformat(),
        "chapter": chapter,
        "chapter_file": chapter_path,
        "state_delta": delta_path,
        "status": "blocked" if blocks else ("warnings" if warnings else "clean"),
        "blocking": len(blocks),
        "warnings": len(warnings),
        "findings": blocks + warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="逐章读者契约机检：防止长篇写作跑题")
    parser.add_argument("root")
    parser.add_argument("--chapter", required=True, help="章号，如 3 或 第03章")
    parser.add_argument("--json-out", help="输出 JSON 路径；默认写入 审稿/reader_contract_sentry_第NN章.json")
    parser.add_argument("--advisory", action="store_true", help="只报告，不用非零退出阻断流程")
    args = parser.parse_args()

    try:
        chapter = _chapter_num(args.chapter)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        sys.exit(2)

    report = analyze(args.root, chapter)
    out_path = args.json_out or os.path.join(
        os.path.abspath(args.root), "审稿", f"reader_contract_sentry_第{chapter:02d}章.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if report["blocking"]:
        print(f"❌ 第{chapter:02d}章读者契约检查阻断 {report['blocking']} 项 → {out_path}")
        for item in report["findings"]:
            if item.get("severity") == "阻断级":
                print(f"  [阻断级] {item['type']}: {item['message']}")
        if not args.advisory:
            sys.exit(1)
    elif report["warnings"]:
        print(f"⚠️ 第{chapter:02d}章读者契约检查有建议 {report['warnings']} 项 → {out_path}")
    else:
        print(f"✅ 第{chapter:02d}章读者契约检查通过 → {out_path}")


if __name__ == "__main__":
    main()
