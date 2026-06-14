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

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import load_project_settings  # noqa: E402

from contract import scale_profile
from store import atomic_write_json, atomic_write_text, file_lock
from waivers import append_waiver, make_waiver


CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")
TRIO_STEPS = ("architect", "ghostwriter", "editor")

COMMON_SOURCE_PATHS = (
    "设定/章纲.md",
    "设定/读者契约.md",
    "审稿/demo_gate.json",
    "审稿/state_ledger.json",
)

SOURCE_PATHS_BY_KIND = {
    "create": (
        "设定/创作蓝图.md",
        "设定/设定圣经.md",
        "设定/角色卡.md",
        "设定/世界观.md",
    ),
    "rewrite": (
        "原作.txt",
        "设定/改动spec.md",
        "设定/新设定.md",
        "设定/角色卡.md",
        "设定/世界观.md",
    ),
    "spinoff": (
        "原作.txt",
        "设定/锚点表.json",
        "设定/角色卡.md",
        "设定/世界观.md",
    ),
    "continue": (
        "原作.txt",
        "设定/人物.md",
        "设定/世界观.md",
        "设定/主线骨架.json",
        "设定/末章状态.md",
        "设定/作者口吻.md",
        "设定/续写方向.md",
    ),
    "expand": (
        "原作.txt",
        "设定/事件骨架.json",
        "设定/人物.md",
        "设定/世界观.md",
        "设定/章节映射.md",
    ),
    "condense": (
        "原作.txt",
        "设定/主线骨架.json",
        "设定/章节映射.md",
    ),
}


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


def fmt_list(value):
    if not value:
        return "未填写"
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(items) if items else "未填写"
    return str(value).strip() or "未填写"


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


def state_ledger_path(root):
    return os.path.join(root, "审稿", "state_ledger.json")


def state_ledger_lock_path(root):
    return os.path.join(root, "审稿", "state_ledger.lock")


def default_state_ledger():
    return {
        "schema_version": 1,
        "kind": "novel_state_ledger",
        "updated_at": date.today().isoformat(),
        "characters": {},
        "setting_facts": [],
        "open_threads": [],
        "resolved_threads": [],
        "chapter_deltas": {},
    }


def _ensure_state_ledger_unlocked(root):
    path = os.path.join(root, "审稿", "state_ledger.json")
    if os.path.exists(path):
        return load_json(path, {})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = default_state_ledger()
    atomic_write_json(path, data)
    return data


def ensure_state_ledger(root):
    with file_lock(state_ledger_lock_path(root)):
        return _ensure_state_ledger_unlocked(root)


def record_ledger_waiver(root, waiver):
    path = state_ledger_path(root)
    with file_lock(state_ledger_lock_path(root)):
        ledger = _ensure_state_ledger_unlocked(root)
        waivers = ledger.setdefault("waivers", [])
        if not any(w.get("id") == waiver.get("id") for w in waivers):
            waivers.append(waiver)
            ledger["updated_at"] = date.today().isoformat()
            atomic_write_json(path, ledger)


def previous_chapter_excerpt(root, chapter):
    if chapter <= 1:
        return "（无上一章）"
    path = chapter_path(root, chapter - 1)
    text = read_text(path)
    if not text:
        return f"（缺上一章文件：章节/第{chapter - 1:02d}章.md）"
    return clip(text[-1800:], 1800)


def setting_value(root, key):
    return load_project_settings(root).get(key, "")


def draft_mode_from_settings(root, meta):
    value = setting_value(root, "小说生成模式")
    if value:
        return value
    return meta.get("draft_mode") or "稳妥初稿"


def draft_workflow_from_settings(root, meta):
    value = setting_value(root, "小说生成工作流")
    if value:
        return value
    return meta.get("draft_workflow") or meta.get("writing_workflow") or ""


def use_trio_pipeline(root, meta):
    mode = draft_mode_from_settings(root, meta)
    workflow = draft_workflow_from_settings(root, meta)
    return mode in {"商业连载", "漫剧源书"} or "三步" in workflow or "trio" in workflow.lower()


def packet_steps_for_request(root, requested_step):
    if requested_step == "trio":
        return list(TRIO_STEPS)
    if requested_step != "auto":
        return [requested_step]
    meta = load_json(os.path.join(root, "_meta.json"), {})
    return list(TRIO_STEPS) if use_trio_pipeline(root, meta) else ["full"]


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


def source_paths_for_kind(kind):
    """Return the context files a chapter packet must make the writer read."""
    paths = list(SOURCE_PATHS_BY_KIND.get(kind or "", SOURCE_PATHS_BY_KIND["create"]))
    paths.extend(COMMON_SOURCE_PATHS)
    out = []
    seen = set()
    for path in paths:
        if path not in seen:
            out.append(path)
            seen.add(path)
    return out


def build_packet(root, chapter, *, allow_missing_demo=False, step="full"):
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
    plot_loops = load_json(os.path.join(root, "设定", "剧情环.json"), {}).get("loops", [])
    pending_loops = [L for L in plot_loops if L.get("status") in ("buried", "teasing")]
    
    char_voices = load_json(os.path.join(root, "设定", "角色语感.json"), {})
    
    words = target_words(meta)
    outline_item = outline.get(chapter, {"title": "", "beat": "（章纲未写本章条目）", "raw": ""})
    title = outline_item.get("title") or ""
    beat_text = outline_item.get("beat") or ""
    
    active_voices = []
    for char_name, vfp in char_voices.items():
        if char_name in title or char_name in beat_text:
            active_voices.append((char_name, vfp))
            
    voice_section = ""
    if active_voices:
        voice_section = "\n## 角色语感约束\n"
        for name, fp in active_voices:
            sp = fp.get("syntax_profile", {})
            voice_section += f"- **{name}**: 句均长 {sp.get('avg_sentence_length')} 字，短句比 {sp.get('short_sentence_ratio')}，长句比 {sp.get('long_sentence_ratio')}。词频特征: {', '.join(x['term'] for x in fp.get('lexicon_anchor', [])[:5])}\n"
    
    draft_mode = draft_mode_from_settings(root, meta)
    
    # Workflow step adjustments
    step_note = ""
    out_file = f"章节/第{chapter:02d}章.md"
    
    # Tension & Tone logic injection
    tension_ledger_path = os.path.join(root, "设定", "tension_ledger.json")
    tension_note = ""
    if os.path.exists(tension_ledger_path):
        try:
            with open(tension_ledger_path, "r", encoding="utf-8") as f:
                tension_data = json.load(f)
                tension_note = f"\n## Tension Ledger (情绪 ROI)\n- 未解决悬念钩子 (Unresolved Hooks): {len(tension_data.get('unresolved_hooks', []))}个\n"
                for hook in tension_data.get("unresolved_hooks", [])[:3]:
                    tension_note += f"  - [{hook.get('urgency', 'normal')}] {hook.get('question')}\n"
        except Exception: pass
        
    tone_curve_path = os.path.join(root, "设定", "tone_curve.json")
    vibe_note = ""
    if os.path.exists(tone_curve_path):
        try:
            with open(tone_curve_path, "r", encoding="utf-8") as f:
                tone_data = json.load(f)
                for arc in tone_data.get("arcs", []):
                    rng = arc.get("range", "").split("-")
                    if len(rng) == 2 and int(rng[0]) <= chapter <= int(rng[1]):
                        vibe_note = f"\n## Semantic Vibe (当前 Arc: {arc.get('arc_name', '未知')})\n- Target Vibe: {arc.get('target_vibe')}\n- 请严格遵循该语境的情感基调，不要偏离。\n"
                        break
        except Exception: pass

    source_paths = source_paths_for_kind(meta.get("kind"))

    if step == "architect":
        step_note = "\n## 当前子任务：Architect Pass (剧情架构师)\n- **目标**：将骨干章纲转化为「节拍与潜台词(Beats & Subtext)」脚本。\n- **禁止**：禁止写优美的文学散文，纯干货输出。\n- **字数**：约 300-500 字。"
        words = [300, 600]
        out_file = f"写作任务/第{chapter:02d}章_beats.md"
    elif step == "ghostwriter":
        step_note = "\n## 当前子任务：Ghostwriter Pass (代笔枪手)\n- **前提**：已完成 Architect 节拍脚本。\n- **目标**：基于节拍脚本，填充环境描写、心理活动，输出流畅的初稿正文。\n- **注意**：请严格复刻文风指纹，并使用 `[CHAR_xx]`、`[PROP_xx]` 等标签标记N2D视觉资产。"
        out_file = f"写作任务/第{chapter:02d}章_draft.md"
        source_paths.append(f"写作任务/第{chapter:02d}章_beats.md")
    elif step == "editor":
        step_note = "\n## 当前子任务：Senior Editor Pass (主编润色)\n- **前提**：已完成 Ghostwriter 初稿。\n- **目标**：专门进行「五感丰富」与「去AI味」的滤网打磨（杀掉抽象词、动词升级、环境映衬）。\n- **输出**：最终交付正文。"
        out_file = f"章节/第{chapter:02d}章.md"
        source_paths.append(f"写作任务/第{chapter:02d}章_draft.md")

    if step != "full" and step != "editor":
        pass # Out file already set above
    
    # Optional dynamic injections
    step_note += tension_note + vibe_note

    demo_anchor = gate.get("style_anchor", {}) if gate else {}
    promises = gate.get("reader_promises", []) if gate else []
    constraints = gate.get("setting_constraints", []) if gate else []
    banned = gate.get("banned_drift", []) if gate else []
    reader_contract = gate.get("reader_contract", {}) if gate else {}
    contract_path = os.path.join(root, "设定", "读者契约.md")
    contract_text = read_text(contract_path)
    contract_promises = reader_contract.get("reader_promises") or promises
    contract_banned = reader_contract.get("banned_drift") or banned
    contract_section = f"""
## 题旨与读者契约
- 核心题旨：{reader_contract.get("theme") or "未填写；写前先补 `设定/读者契约.md`"}
- 核心戏剧问题：{reader_contract.get("dramatic_question") or "未填写"}
- 终局必须回答：{fmt_list(reader_contract.get("must_answer"))}
- 读者承诺：{fmt_list(contract_promises)}
- 好看机制：{fmt_list(reader_contract.get("delight_engine"))}
- 文学质感：{reader_contract.get("aesthetic_register") or "未填写"}
- 禁偏清单：{fmt_list(contract_banned)}

### `设定/读者契约.md` 摘录
{clip(contract_text, 1600) if contract_text else "（缺 `设定/读者契约.md`；至少按 reader-contract.md 模板补齐题旨、读者承诺、文学质感和禁偏清单。）"}
"""
    delta_path = f"审稿/state_delta_第{chapter:02d}章.json"
    waiver_section = ""
    if demo_waiver:
        waiver_section = f"""
## 显式豁免
- {demo_waiver['id']} [{demo_waiver['type']}] {demo_waiver['reason']}
- 风险：缺少已通过 Demo gate 的文风锚点、读者承诺和禁止漂移项；本任务包只能作为准备包，不能替代正式批量写章 gate。
"""
    loop_section = ""
    if pending_loops:
        loop_section = "\n## 剧情环提醒（伏笔/钩子）\n"
        for L in pending_loops:
            loop_section += f"- **{L['title']}** ({L['id']}): {L['description']} [状态: {L['status']}, 埋于: {L.get('buried_in', '未知')}, 预计回收: {L.get('expected_recovery', '未知')}]\n"

    return f"""# 第 {chapter:02d} 章写作任务包 ({step if step != "full" else "完整稿"})

## 任务
- 输出文件：`{out_file}`
- 标题：{title or "按章纲拟一个短标题"}
- 目标字数：{words[0]}-{words[1]} 字
- 人称视角：{meta.get("person", "未指定")}
- 目标平台：{meta.get("target_platform", "未指定")}
- 小说生成模式：{draft_mode}{step_note}

## 必读源文件
{chr(10).join(f"- `{p}`" for p in source_paths)}

## 本章章纲
{outline_item.get("raw") or outline_item.get("beat")}

## 上一章承接
{previous_chapter_excerpt(root, chapter)}
{loop_section}{voice_section}
## Demo 风格锚点
- 来源章节：{demo_anchor.get("source_chapter", "未指定")}
- 风格要点：{demo_anchor.get("summary", "未填写；写前先从 Demo 章抽取")}
- 读者承诺：{", ".join(promises) if promises else "未填写"}
- 设定硬约束：{", ".join(constraints) if constraints else "未填写"}
- 禁止漂移：{", ".join(banned) if banned else "未填写"}
{waiver_section}
{contract_section}

## 当前状态账本摘录
```json
{json.dumps(ledger, ensure_ascii=False, indent=2)[:2400]}
```

## 写作要求
- 只输出一章正文，第一行必须是 `# 第{chapter}章 {title or "<标题>"}`。
- 第二行写 meta 注释：`<!-- meta: demo=false; packet=写作任务/第{chapter:02d}章.md; step={step} -->`。
- 本章必须兑现章纲里的戏剧节拍，至少保留一个钩子或承诺。
- 本章必须推进 `读者契约` 中的至少一项：核心题旨、读者承诺、关系弧光、秘密揭示、能力代价或文学质感；不能只刷事件。
- 不新增会推翻必读设定/骨架文件的能力、关系、地点规则；新增设定必须写入章末状态增量。
- 写完后填写 `{delta_path}`，再跑 `python3 skills/novel-review/scripts/mechanical_check.py "{root}"`。

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
  "reader_contract_progress": [],
  "theme_alignment": "",
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
    ap.add_argument(
        "--step",
        default="auto",
        choices=["auto", "full", "trio", "architect", "ghostwriter", "editor"],
        help="工作流步骤；auto 会让 商业连载/漫剧源书/三步迭代 默认生成 trio 三段任务包",
    )
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        chapters = resolve_chapters(args, root)
        steps = packet_steps_for_request(root, args.step)
        packets = [
            (chapter, step, build_packet(root, chapter, allow_missing_demo=args.allow_missing_demo, step=step))
            for chapter in chapters
            for step in steps
        ]
    except Exception as e:
        print(f"[err] {e}", file=sys.stderr)
        sys.exit(2)

    if args.stdout:
        for idx, (chapter, step, packet) in enumerate(packets):
            if idx:
                print("\n\n" + "=" * 60 + "\n")
            print(packet)
        return

    out_dir = os.path.abspath(args.out_dir or os.path.join(root, "写作任务"))
    os.makedirs(out_dir, exist_ok=True)
    wrote_steps = []
    for chapter, step, packet in packets:
        suffix = f"_{step}" if step != "full" else ""
        path = os.path.join(out_dir, f"第{chapter:02d}章{suffix}.md")
        atomic_write_text(path, packet)
        wrote_steps.append(step)
        print(f"[ok] 写作任务包：{path}")
    if any(step in TRIO_STEPS for step in wrote_steps):
        print("[next] 三步迭代顺序：先按 _architect 产 beats，再按 _ghostwriter 产 draft，最后按 _editor 写入 章节/第NN章.md；完成后填写 state_delta 并跑 novel-review。")
    else:
        print("[next] 按任务包写入 章节/第NN章.md，填写 审稿/state_delta_第NN章.json，再跑 novel-review 机检/人判。")


if __name__ == "__main__":
    main()
