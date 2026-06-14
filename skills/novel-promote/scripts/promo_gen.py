#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate promotion drafts from an actual novel chapter.

This is deterministic scaffolding, not an LLM writer: it reads the requested
chapter, mines high-signal snippets, then writes both platform copy and the
finished-artifact n2d handoff skeleton documented by novel-promote.
"""
import argparse
import os
import re
import sys
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import chapter_label, find_chapter_file, read_text  # noqa: E402
from keyword_banks import (  # noqa: E402  单一定义源
    PROMO_CONFLICT_KW as CONFLICT_KW,
    PROMO_EMOTION_KW as EMOTION_KW,
    PROMO_HOOK_KW as HOOK_KW,
    PROMO_VISUAL_KW as VISUAL_KW,
)
from settings import get_setting  # noqa: E402


# `目标平台`（起点/红果/晋江/抖音漫剧…）→ 宣发投放平台默认值。
# 仅作 --platform 缺省回退，用户显式 --platform 永远优先。
TARGET_TO_PROMO_PLATFORM = (
    ("xiaohongshu", ("晋江", "情感", "言情")),
    ("douyin", ("红果", "抖音", "漫剧", "番茄", "短剧")),
    ("bilibili", ("b站", "bilibili", "历史")),
)


def default_promo_platform(project):
    """从项目 `目标平台` 选择点推断默认宣发平台；推不出落 tiktok。"""
    target = str(get_setting(project, "目标平台") or "").strip().lower()
    if not target:
        return "tiktok"
    for promo_platform, markers in TARGET_TO_PROMO_PLATFORM:
        if any(marker.lower() in target for marker in markers):
            return promo_platform
    return "tiktok"

PLATFORM_PROFILES = {
    "tiktok": {
        "label": "抖音/TikTok 高燃引流",
        "opening": "3秒内抛冲突或视觉奇观，结尾留悬念",
        "cta": "点击下方看后续",
        "tags": "#小说推文 #高燃反转 #短剧预告",
    },
    "douyin": {
        "label": "抖音高燃引流",
        "opening": "3秒内抛冲突或视觉奇观，结尾留悬念",
        "cta": "点主页看后续",
        "tags": "#小说推文 #高燃反转 #短剧预告",
    },
    "xiaohongshu": {
        "label": "小红书情绪氛围",
        "opening": "先给氛围感和关系张力，再补冲突",
        "cta": "想看后续可以收藏",
        "tags": "#小说安利 #宿命感 #氛围感",
    },
    "bilibili": {
        "label": "B站伏笔解读",
        "opening": "先抛伏笔疑问，再拆本章冲突链",
        "cta": "三连后继续拆下一章",
        "tags": "#小说解读 #剧情伏笔 #网文安利",
    },
}


def _chapter_number(value):
    m = re.search(r"\d+", str(value or ""))
    if not m:
        raise argparse.ArgumentTypeError("--chapter 需要包含数字章号")
    n = int(m.group(0))
    if n < 1:
        raise argparse.ArgumentTypeError("--chapter 必须大于 0")
    return n


def _strip_markup(text):
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or set(s) <= set("-=*"):
            continue
        lines.append(s)
    return "\n".join(lines)


def _clip(text, limit=70):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。！？；：,.!?;: ") + "…"


def split_segments(text):
    text = _strip_markup(text)
    raw_segments = re.split(r"\n{2,}|(?<=[。！？!?])\s*", text)
    segments = []
    for seg in raw_segments:
        seg = re.sub(r"\s+", " ", seg).strip()
        if len(seg) < 8:
            continue
        if len(seg) > 180:
            parts = re.split(r"(?<=[。！？!?；;])", seg)
            segments.extend(p.strip() for p in parts if len(p.strip()) >= 8)
        else:
            segments.append(seg)
    return segments


def _score(seg, keywords):
    return sum(seg.count(k) for k in keywords)


def _rank_segments(segments):
    scored = []
    for idx, seg in enumerate(segments):
        score = (
            3 * _score(seg, CONFLICT_KW)
            + 2 * _score(seg, VISUAL_KW)
            + 2 * _score(seg, HOOK_KW)
            + _score(seg, EMOTION_KW)
        )
        quote_bonus = 3 if re.search(r"[“「『\"].{4,60}[”」』\"]", seg) else 0
        scored.append((score + quote_bonus, idx, seg))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [seg for _, _, seg in scored]


def extract_quotes(text):
    quotes = []
    for lq, rq in (("“", "”"), ("「", "」"), ("『", "』"), ('"', '"')):
        pattern = re.escape(lq) + r"(.{4,60}?)" + re.escape(rq)
        quotes.extend(q.strip() for q in re.findall(pattern, text, re.S))
    seen = set()
    out = []
    for quote in quotes:
        q = re.sub(r"\s+", " ", quote).strip()
        if q and q not in seen:
            out.append(q)
            seen.add(q)
    return out


def extract_characters(project, text):
    names = []
    card = os.path.join(project, "设定", "角色卡.md")
    if os.path.exists(card):
        card_text = read_text(card)
        for line in card_text.splitlines():
            for pat in (r"^#{1,4}\s*([\u4e00-\u9fff·]{2,6})\s*$",
                        r"(?:姓名|名字|角色)[:：]\s*([\u4e00-\u9fff·]{2,6})"):
                m = re.search(pat, line.strip())
                if m and m.group(1) not in names:
                    names.append(m.group(1))
    used = [name for name in names if name in text]
    return used[:4] or ["本章主角", "对手/阻力"]


def mine_highlights(text):
    segments = split_segments(text)
    ranked = _rank_segments(segments)
    if not ranked and text.strip():
        ranked = [_clip(text, 120)]
    beats = ranked[:3]
    while len(beats) < 3:
        beats.append(beats[-1] if beats else "本章高光片段待补")
    quotes = extract_quotes(text)
    visual = max(segments or beats, key=lambda s: (_score(s, VISUAL_KW), len(s)))
    emotion = max(segments or beats, key=lambda s: (_score(s, EMOTION_KW), len(s)))
    return {
        "beats": beats,
        "quote": quotes[0] if quotes else _clip(beats[0], 36),
        "visual": visual,
        "emotion": emotion,
    }


def build_platform_script(project, chapter, platform, chapter_path, text):
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["tiktok"])
    rel_chapter = os.path.relpath(chapter_path, project).replace(os.sep, "/")
    highlights = mine_highlights(text)
    beats = highlights["beats"]
    quote = highlights["quote"]
    label = chapter_label(chapter)
    lines = [
        f"# 宣发引流脚本 - {label} ({profile['label']})",
        "",
        f"- 来源章节：`{rel_chapter}`",
        f"- 生成日期：{date.today().isoformat()}",
        f"- 平台策略：{profile['opening']}",
        "",
        "## 爆点提取",
        f"- **视觉高光**：{_clip(highlights['visual'], 90)}",
        f"- **金句钩子**：\"{_clip(quote, 54)}\"",
        f"- **情绪爆点**：{_clip(highlights['emotion'], 90)}",
        "",
        "## 推荐脚本",
        f"1. **黄金3秒**：{_clip(beats[0], 64)}",
        f"2. **核心冲突**：{_clip(beats[1], 72)}",
        f"3. **悬念留白**：{_clip(beats[2], 72)}",
        "",
        "## 字幕/封面文案",
        f"- 封面钩子：{_clip(quote, 28)}",
        f"- 结尾引导：{profile['cta']}",
        f"- 标签：{profile['tags']}",
        "",
        "## 剧透红线",
        "- 不揭最终真相、不提前说出幕后身份、不把本章之后的反转写进标题。",
        "",
    ]
    return "\n".join(lines)


def build_n2d_ready(project, chapter, chapter_path, text):
    rel_chapter = os.path.relpath(chapter_path, project).replace(os.sep, "/")
    highlights = mine_highlights(text)
    beats = highlights["beats"]
    chars = "、".join(extract_characters(project, text))
    quote = highlights["quote"]
    label = chapter_label(chapter)
    beat_specs = [
        ("Beat 1 [0-3s]", beats[0], 3),
        ("Beat 2 [3-10s]", beats[1], 7),
        ("Beat 3 [10-15s]", beats[2], 5),
    ]
    lines = [
        f"# 预告片底稿 · {label}",
        "",
        f"- 来源章节: `{rel_chapter}`",
        "- 视觉风格建议: 对齐本项目 `设定/风格指纹.json` 或 Demo 文风锚点；若缺失，由 n2d 接手前补齐。",
        f"- 角色卡指针: `设定/角色卡.md`（本章候选角色：{chars}）",
        "- 禁剧透项: 幕后身份、终局真相、金手指最终代价。",
        "",
    ]
    for name, seg, seconds in beat_specs:
        lines.append(
            f"- {name}: 场景=本章高光片段 角色={chars} 动作={_clip(seg, 48)} "
            f"字幕=\"{_clip(quote if name.startswith('Beat 1') else seg, 28)}\" 时长≈{seconds}s"
        )
    lines += [
        "",
        "> 这是 novel → n2d 的 finished-artifact 交接底稿；本脚本不调用任何 n2d-* skill。",
        "",
    ]
    return "\n".join(lines)


def write_outputs(project, chapter, platform):
    chapter_path = find_chapter_file(project, chapter)
    text = read_text(chapter_path)
    if not _strip_markup(text).strip():
        raise ValueError(f"章节为空：{chapter_path}")

    out_dir = os.path.join(project, "导出", "宣发")
    os.makedirs(out_dir, exist_ok=True)
    label = chapter_label(chapter)
    promo_path = os.path.join(out_dir, f"{label}_引流脚本_{platform}.md")
    n2d_path = os.path.join(out_dir, f"{label}_n2d_ready.md")

    with open(promo_path, "w", encoding="utf-8") as f:
        f.write(build_platform_script(project, chapter, platform, chapter_path, text))
    with open(n2d_path, "w", encoding="utf-8") as f:
        f.write(build_n2d_ready(project, chapter, chapter_path, text))
    return promo_path, n2d_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate promotion scripts for novel chapters.")
    parser.add_argument("project_path", help="Path to the novel project root")
    parser.add_argument("--chapter", required=True, type=_chapter_number, help="Chapter number to analyze")
    parser.add_argument("--platform", default=None,
                        help="投放平台 tiktok/douyin/xiaohongshu/bilibili；"
                             "缺省按项目 `目标平台` 选择点推断")
    args = parser.parse_args(argv)

    project = os.path.abspath(args.project_path)
    if args.platform is None:
        # 未显式传 → 从 `目标平台` 选择点推断（_设置.md → 全局默认 → tiktok）。
        platform = default_promo_platform(project)
        print(f"[info] 未指定 --platform，按目标平台推断为 {platform}（可用 --platform 覆盖）",
              file=sys.stderr)
    else:
        platform = args.platform.strip().lower()
    if platform not in PLATFORM_PROFILES:
        known = ", ".join(sorted(PLATFORM_PROFILES))
        print(f"[warn] 未知平台 {args.platform!r}，按 tiktok 模板生成；可选：{known}", file=sys.stderr)
        platform = "tiktok"

    promo_path, n2d_path = write_outputs(project, args.chapter, platform)
    print(f"Promotion script generated at {promo_path}")
    print(f"n2d-ready draft generated at {n2d_path}")


if __name__ == "__main__":
    main()
