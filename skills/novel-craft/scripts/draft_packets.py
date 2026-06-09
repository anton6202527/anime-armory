#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build per-chapter drafting packets for novel-* projects.

This script does not call an AI model. It makes the draft stage repeatable by
materializing the context packet an agent/sub-agent should use before writing a
chapter, plus a state-delta template to fill after the chapter is written.

Usage:
    python3 skills/novel-craft/scripts/draft_packets.py <作品根> --chapter 4
    python3 skills/novel-craft/scripts/draft_packets.py <作品根> --range 4-8
    python3 skills/novel-craft/scripts/draft_packets.py <作品根> --next
"""
import argparse
import json
import os
import re
import sys
from datetime import date

from contract import scale_profile
from waivers import append_waiver, make_waiver


CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")


def read_text(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clip(text, limit=2200):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...（已截断；写章时按路径读取原文件）"


def chapter_path(root, chapter):
    return os.path.join(root, "章节", f"第{chapter:02d}章.md")


def existing_chapters(root):
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return set()
    nums = set()
    for name in os.listdir(chdir):
        m = re.search(r"第0*(\d+)章", name)
        if m and name.endswith(".md"):
            nums.add(int(m.group(1)))
    return nums


def parse_outline(root):
    text = read_text(os.path.join(root, "设定", "章纲.md"))
    outline = {}
    for raw in text.splitlines():
        m = CHAPTER_RE.search(raw)
        if not m:
            continue
        chapter = int(m.group(1))
        title = (m.group(2) or "").strip()
        beat = (m.group(3) or raw).strip()
        outline.setdefault(chapter, {"title": title, "beat": beat, "raw": raw.strip()})
    return outline


def load_demo_gate(root, allow_missing=False):
    path = os.path.join(root, "审稿", "demo_gate.json")
    data = load_json(path, None)
    if not data:
        if allow_missing:
            return {}
        raise RuntimeError("缺少 审稿/demo_gate.json；Demo gate 通过前不要批量写章。可加 --allow-missing-demo 只生成准备包。")
    status = data.get("status")
    if status != "passed" and not allow_missing:
        raise RuntimeError(f"Demo gate 未通过：status={status!r}；不能进入批量写章。")
    return data


def ensure_state_ledger(root):
    path = os.path.join(root, "审稿", "state_ledger.json")
    if os.path.exists(path):
        return load_json(path, {})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "schema_version": 1,
        "kind": "novel_state_ledger",
        "updated_at": date.today().isoformat(),
        "characters": {},
        "setting_facts": [],
        "open_threads": [],
        "resolved_threads": [],
        "chapter_deltas": {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def record_ledger_waiver(root, waiver):
    path = os.path.join(root, "审稿", "state_ledger.json")
    ledger = ensure_state_ledger(root)
    waivers = ledger.setdefault("waivers", [])
    if not any(w.get("id") == waiver.get("id") for w in waivers):
        waivers.append(waiver)
        ledger["updated_at"] = date.today().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)


def previous_chapter_excerpt(root, chapter):
    if chapter <= 1:
        return "（无上一章）"
    path = chapter_path(root, chapter - 1)
    text = read_text(path)
    if not text:
        return f"（缺上一章文件：章节/第{chapter - 1:02d}章.md）"
    return clip(text[-1800:], 1800)


def draft_mode_from_settings(root, meta):
    settings = read_text(os.path.join(root, "_设置.md"))
    m = re.search(r"(?:\*\*)?小说生成模式(?:\*\*)?[：:]\s*([^\n]+)", settings)
    if m:
        return m.group(1).strip()
    return meta.get("draft_mode") or "稳妥初稿"


def target_words(meta):
    if meta.get("target_words_per_chapter"):
        return meta["target_words_per_chapter"]
    scale = meta.get("scale")
    if scale:
        try:
            return scale_profile(scale)["words_per_chapter"]
        except KeyError:
            pass
    return [1000, 1800]


def build_packet(root, chapter, *, allow_missing_demo=False):
    meta = load_json(os.path.join(root, "_meta.json"), {})
    if not meta:
        raise RuntimeError("缺少 _meta.json")
    outline = parse_outline(root)
    gate = load_demo_gate(root, allow_missing=allow_missing_demo)
    demo_waiver = None
    if allow_missing_demo and (not gate or gate.get("status") != "passed"):
        demo_waiver = make_waiver(
            "missing_demo_gate",
            reason="explicit --allow-missing-demo while generating draft packet",
            affected_gate="demo_gate",
            source="novel-craft/scripts/draft_packets.py",
            details={"chapter": chapter, "demo_gate_status": gate.get("status") if gate else None},
        )
        append_waiver(root, demo_waiver)
        record_ledger_waiver(root, demo_waiver)
    ledger = ensure_state_ledger(root)
    words = target_words(meta)
    outline_item = outline.get(chapter, {"title": "", "beat": "（章纲未写本章条目）", "raw": ""})
    title = outline_item.get("title") or ""
    draft_mode = draft_mode_from_settings(root, meta)
    out_file = f"章节/第{chapter:02d}章.md"
    project_rel = lambda *p: os.path.join(*p)
    source_paths = [
        project_rel("设定", "创作蓝图.md"),
        project_rel("设定", "设定圣经.md"),
        project_rel("设定", "角色卡.md"),
        project_rel("设定", "世界观.md"),
        project_rel("设定", "章纲.md"),
        project_rel("审稿", "demo_gate.json"),
        project_rel("审稿", "state_ledger.json"),
    ]
    demo_anchor = gate.get("style_anchor", {}) if gate else {}
    promises = gate.get("reader_promises", []) if gate else []
    constraints = gate.get("setting_constraints", []) if gate else []
    banned = gate.get("banned_drift", []) if gate else []
    delta_path = f"审稿/state_delta_第{chapter:02d}章.json"
    waiver_section = ""
    if demo_waiver:
        waiver_section = f"""
## 显式豁免
- {demo_waiver['id']} [{demo_waiver['type']}] {demo_waiver['reason']}
- 风险：缺少已通过 Demo gate 的文风锚点、读者承诺和禁止漂移项；本任务包只能作为准备包，不能替代正式批量写章 gate。
"""
    return f"""# 第 {chapter:02d} 章写作任务包

## 任务
- 输出文件：`{out_file}`
- 标题：{title or "按章纲拟一个短标题"}
- 目标字数：{words[0]}-{words[1]} 字
- 人称视角：{meta.get("person", "未指定")}
- 目标平台：{meta.get("target_platform", "未指定")}
- 小说生成模式：{draft_mode}

## 必读源文件
{chr(10).join(f"- `{p}`" for p in source_paths)}

## 本章章纲
{outline_item.get("raw") or outline_item.get("beat")}

## 上一章承接
{previous_chapter_excerpt(root, chapter)}

## Demo 风格锚点
- 来源章节：{demo_anchor.get("source_chapter", "未指定")}
- 风格要点：{demo_anchor.get("summary", "未填写；写前先从 Demo 章抽取")}
- 读者承诺：{", ".join(promises) if promises else "未填写"}
- 设定硬约束：{", ".join(constraints) if constraints else "未填写"}
- 禁止漂移：{", ".join(banned) if banned else "未填写"}
{waiver_section}

## 当前状态账本摘录
```json
{json.dumps(ledger, ensure_ascii=False, indent=2)[:2400]}
```

## 写作要求
- 只输出一章正文，第一行必须是 `# 第{chapter}章 {title or "<标题>"}`。
- 第二行写 meta 注释：`<!-- meta: demo=false; packet=写作任务/第{chapter:02d}章.md -->`。
- 本章必须兑现章纲里的戏剧节拍，至少保留一个钩子或承诺。
- 不新增会推翻设定圣经的能力、关系、地点规则；新增设定必须写入章末状态增量。
- 写完后填写 `{delta_path}`，再跑 `novel-review/scripts/mechanical_check.py`。

## 状态增量模板
```json
{{
  "schema_version": 1,
  "kind": "novel_state_delta",
  "chapter": {chapter},
  "chapter_file": "{out_file}",
  "new_facts": [],
  "character_changes": [],
  "relationship_changes": [],
  "open_threads_added": [],
  "threads_resolved": [],
  "setting_constraints_added": [],
  "next_chapter_carry": []
}}
```
"""


def resolve_chapters(args, root):
    if args.chapter:
        return [args.chapter]
    if args.range:
        m = re.fullmatch(r"(\d+)-(\d+)", args.range)
        if not m:
            raise RuntimeError("--range 格式应为 4-8")
        start, end = int(m.group(1)), int(m.group(2))
        if end < start:
            raise RuntimeError("--range 结束章不能小于开始章")
        return list(range(start, end + 1))
    meta = load_json(os.path.join(root, "_meta.json"), {})
    target = int(meta.get("target_chapters") or 0)
    done = existing_chapters(root)
    start = 1
    demo_count = int(meta.get("demo_chapters") or 0)
    if args.next and demo_count:
        start = demo_count + 1
    for chapter in range(start, target + 1):
        if chapter not in done:
            return [chapter]
    raise RuntimeError("未找到待写章节；可用 --chapter 指定。")


def main():
    ap = argparse.ArgumentParser(description="生成 novel 批量写章任务包")
    ap.add_argument("project_root")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--chapter", type=int)
    group.add_argument("--range", dest="range", default=None, help="例如 4-8")
    group.add_argument("--next", action="store_true", help="按 _meta/demo_chapters 和现有章节找下一章")
    ap.add_argument("--out-dir", default=None, help="缺省 <作品根>/写作任务")
    ap.add_argument("--stdout", action="store_true", help="只打印，不写文件")
    ap.add_argument("--allow-missing-demo", action="store_true", help="Demo gate 未通过时也允许生成准备包")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        chapters = resolve_chapters(args, root)
        packets = [(chapter, build_packet(root, chapter, allow_missing_demo=args.allow_missing_demo))
                   for chapter in chapters]
    except Exception as e:
        print(f"[err] {e}", file=sys.stderr)
        sys.exit(2)

    if args.stdout:
        for idx, (chapter, packet) in enumerate(packets):
            if idx:
                print("\n\n" + "=" * 60 + "\n")
            print(packet)
        return

    out_dir = os.path.abspath(args.out_dir or os.path.join(root, "写作任务"))
    os.makedirs(out_dir, exist_ok=True)
    for chapter, packet in packets:
        path = os.path.join(out_dir, f"第{chapter:02d}章.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(packet)
        print(f"[ok] 写作任务包：{path}")
    print("[next] 按任务包写入 章节/第NN章.md，填写 审稿/state_delta_第NN章.json，再跑 novel-review 机检/人判。")


if __name__ == "__main__":
    main()
