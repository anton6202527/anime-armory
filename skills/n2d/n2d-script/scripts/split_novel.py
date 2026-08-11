#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_novel.py — 把长篇小说自动拆分成粗胚分块，并搭好 AI漫剧/短剧 生产目录骨架。
（注意：拆分只是脚手架，最终「集」边界由导演按戏剧节拍重切，一章≠一集。）

用法:
    python3 split_novel.py <小说路径> [选项]

常用选项:
    --by-chapter       按「第X章」+ 强钩候选切（更贴戏剧节拍）
    --per-chapter      每章独立成一集（最贴节拍；长章保持整章，精修时再拆）
    --start-chapter N  从第N章开始粗切（可写 48 / 第48章 / 第四十八章；中段开工仍需先补前情资产包）
    --limit N          首批只落地 N 集；缺省为 10 集
    --all              显式全篇粗切
    --legacy-plan-v2   回退写逐段内嵌的 verbose v2；默认写紧凑 v3
    --compact-existing-plan  原位把既有 v2 存储迁移为 v3，不重拆、不碰 raw/进度/人工复核
    --keep-frontmatter 保留开头简介/标签/看点（默认自动剥离）
    --out 目录          作品根（默认=小说同级；小说在 …/小说/ 下时自动取其父）
    --target 高级参数：粗胚字数参考（仅用于报告/人工复核，不参与默认切点决策）
    --min/--max 旧参数兼容（仅作历史命令占位，不再作为硬性上下限）
    --name 标题         素材文件头用的标题（默认取小说文件名）

支持 .txt / .docx 输入。默认输出布局：
    <作品根>/_进度.md
    <作品根>/设定库/global_style.md
    <作品根>/设定库/characters/_角色总表.md
    <作品根>/设定库/locations/_场景总表.md
    <作品根>/小说/<剧名>.txt 规范源副本（供 source_check.py --record）
    <作品根>/脚本/split_plan.json（v3 紧凑全书 source-unit 轴 / arc / 候选边界）
    <作品根>/脚本/_拆集机器索引.md + _拆集复核.md（机器/人工分离，续切不覆人工）
    <作品根>/脚本/第N集/{raw.txt 分镜剧本.md 故事板.md 素材清单.md
                         voiceover.txt bgm.txt 封面.md 字幕_中文.srt}
（出图/ 与 出视频/ 由 n2d-image 与 n2d-video 在后续阶段创建。）
开头的简介/标签/看点等元数据默认自动剥离（见 strip_frontmatter）。
"""
import argparse
import datetime as _dt
import gzip
import hashlib
import json
import os
import re
import uuid
import sys
import zipfile
from pathlib import Path

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_const import GENRE_MIN_HITS, boundary_buckets, boundary_lexicon
from n2d_contract import PROGRESS_COLUMNS
from n2d_settings import DEFAULTS, get_setting, project_setting_source
from n2d_visual_styles import (
    format_style_contract_markdown,
    format_style_recommendation_markdown,
    recommend_style,
    style_options_text,
)
from source_analyze import render_character_roster, write_analysis
from work_card_meta import (
    backfill_synopsis as backfill_work_card_synopsis,
    ensure_work_card_fields,
)

try:
    from motif_detector import detect_genre
except Exception:  # 题材检测不可用时不拖垮拆集；推荐器自动退化到通用默认。
    detect_genre = None  # type: ignore

try:
    from development_pack import scaffold as scaffold_development_pack
except Exception:  # P-1 开发包缺失不拖垮历史拆集；run.py 会在阶段1前 fail-closed。
    scaffold_development_pack = None  # type: ignore

try:
    # P4：confirmed story_spine 的 cut 决策 → 拆集整章剔除计划（单向依赖：split 消费 spine）。
    from story_spine import spine_cut_chapter_plan
except Exception:  # story_spine 缺失不拖垮历史拆集；剪枝退化为不生效。
    spine_cut_chapter_plan = None  # type: ignore


DEFAULT_FIRST_SPLIT_LIMIT = 10


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return read_docx(path)
    # 纯文本，尝试多种编码
    raw = open(path, "rb").read()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    # 段落 </w:p> 转换为换行，去掉所有标签
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    # 还原常见 XML 实体
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        xml = xml.replace(a, b)
    return xml


def normalize_paragraphs(text):
    paras = [p.strip() for p in re.split(r"\r?\n+", text)]
    return [p for p in paras if p]


# 章回体古籍常见“囬/囘/廻”异体回字与繁体“節”；统一视为章节单位，
# 避免明清刻本/维基文库转写在 --by-chapter 下退化成章内碎切。
CHAPTER_RE = re.compile(r"^\s*(?:\[编辑\]\s*)?第\s*([0-9零〇一二三四五六七八九十百千万两]+)\s*[章回囬囘廻节節卷]")
CHINESE_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}

# 开头常见的"非正文"元数据行（简介/标签/看点等），自动剥离
META_PREFIX = ("【", "✅", "☑", "★", "#", "—")
META_LABELS = {
    "简介", "内容简介", "作品简介", "标准简介", "一句话简介",
    "标签", "作品标签", "主要看点", "看点", "一句话剧透", "剧透", "作者", "字数",
}


def strip_frontmatter(paras):
    """剥离开头的简介/标签/看点/书名等非正文块。

    优先：若开头 40 段内出现首个章节标题，则从该标题起算正文（丢弃之前所有元数据）。
    退化：无章节标题时，逐行丢弃开头的元数据行（书名《…》、【…】、✅…、纯标签词等）。
    """
    if not paras:
        return paras
    head = paras[:40]
    first_ch = next((i for i, p in enumerate(head) if CHAPTER_RE.match(p)), None)
    if first_ch is not None:
        return paras[first_ch:]
    start = 0
    while start < len(paras) and start < 40:
        p = paras[start]
        pn = re.sub(r"[《》【】\s]", "", p)
        is_title = bool(re.match(r"^《.+》$", p))
        is_meta = (
            p.startswith(META_PREFIX)
            or pn in META_LABELS
            or any(pn.startswith(lbl) for lbl in ("一句话简介", "标准简介", "内容简介", "一句话剧透"))
        )
        if is_title or is_meta:
            start += 1
        else:
            break
    return paras[start:] or paras


def parse_chapter_number(value):
    """Parse Arabic or common Chinese chapter numbers."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    m = re.search(r"第\s*([0-9零〇一二三四五六七八九十百千万两]+)\s*[章回囬囘廻节節卷]", text)
    token = m.group(1) if m else text
    token = re.sub(r"^第", "", token)
    token = re.sub(r"[章回囬囘廻节節卷]$", "", token)
    token = re.sub(r"[\s,，_、.-]", "", token)
    if token.isdigit():
        return int(token)
    if not token or any(ch not in CHINESE_DIGITS and ch not in CHINESE_UNITS and ch != "万" for ch in token):
        return None

    total = 0
    section = 0
    number = 0
    for ch in token:
        if ch in CHINESE_DIGITS:
            number = CHINESE_DIGITS[ch]
        elif ch in CHINESE_UNITS:
            unit = CHINESE_UNITS[ch]
            section += (number or 1) * unit
            number = 0
        elif ch == "万":
            section_value = section + number
            total += (section_value or 1) * 10000
            section = 0
            number = 0
    return total + section + number


def chapter_number_from_heading(para):
    m = CHAPTER_RE.match(para or "")
    if not m:
        return None
    return parse_chapter_number(m.group(1))


def trim_before_chapter(paras, chapter_spec):
    """Return paragraphs starting at the first chapter >= requested chapter."""
    target = parse_chapter_number(chapter_spec)
    if target is None or target < 1:
        raise ValueError(f"无法解析起始章节: {chapter_spec}")

    seen_chapter = False
    for i, para in enumerate(paras):
        chapter = chapter_number_from_heading(para)
        if chapter is None:
            continue
        seen_chapter = True
        if chapter >= target:
            return paras[i:], {
                "requested": target,
                "matched": chapter,
                "skipped_paras": i,
                "exact": chapter == target,
            }
    if not seen_chapter:
        raise ValueError("未识别到「第X章」章节标题，无法使用 --start-chapter")
    raise ValueError(f"未找到第{target}章或之后的章节标题")


def split_sentences(para):
    # 在句末标点后切句，保留标点
    parts = re.split(r"(?<=[。！？!?…”])", para)
    return [s for s in (p.strip() for p in parts) if s]


def build_boundary_res(genre_text=None):
    """按题材构建 (强钩收尾, 冲突, 爽点/反转) 三条正则。

    词面来自 `n2d_const.boundary_lexicon`（base ∪ 命中题材桶），治"古言爽文词典对
    女频情感/悬疑/都市退化成无闭环"。未识别题材时复刻历史覆盖（base ∪ 古装动作）。
    """
    strong, conflict, payoff = boundary_lexicon(genre_text)
    strong_re = re.compile(r"(" + "|".join(re.escape(t) for t in strong) + r")\s*$")
    conflict_re = re.compile(r"(" + "|".join(re.escape(t) for t in conflict) + r")")
    payoff_re = re.compile(r"(" + "|".join(re.escape(t) for t in payoff) + r")")
    return strong_re, conflict_re, payoff_re


# 模块级默认（题材=None：复刻历史古言/修仙覆盖）。main() 解析 _设置.md `题材` 后按题材重建。
STRONG_EPISODE_END_RE, CONFLICT_RE, PAYOFF_OR_REVERSAL_RE = build_boundary_res(None)

SCENE_BREAK_RE = re.compile(
    r"^\s*(?:[-—*]{3,}|[一二三四五六七八九十0-9]+[、.．]\s*|【[^】]{1,24}】|"
    r"(?:翌日|次日|当夜|与此同时|另一边|片刻后|三日后|半个时辰后))"
)


def strong_episode_end(text):
    """启发式识别可作为粗胚右边界的强钩。

    这不是最终剧情判断；它只避免 split 阶段在普通段落末尾按字数硬切。
    """
    return bool(STRONG_EPISODE_END_RE.search((text or "")[-180:]))


def has_conflict(text):
    return bool(CONFLICT_RE.search(text or ""))


def has_payoff_or_reversal(text):
    return bool(PAYOFF_OR_REVERSAL_RE.search(text or ""))


def natural_scene_break(next_para, chapter_only=False):
    """下一段是否构成自然幕界。

    chapter_only=True（章节感知粗切·--by-chapter）：只认「第X章」章界，
    不把章内的场景分隔（---、【…】、翌日…）当幕界——否则系统流爽文里满屏的
    系统面板行 `【妖化：虎山神】` 会被误判成集边界，粗切成上千个百字微集。
    """
    if not next_para:
        return False
    if CHAPTER_RE.match(next_para):
        return True
    return not chapter_only and bool(SCENE_BREAK_RE.match(next_para))


def boundary_candidate(end_para, next_para=None, chapter_only=False):
    # 章节感知模式：章是原子粗胚单元，只在章界落点；不让章内的强钩句把一章劈碎
    # （古装动作的强钩词典很宽，否则一章会被切成多个百字微集）。
    if chapter_only:
        return natural_scene_break(next_para, chapter_only=True)
    return strong_episode_end(end_para) or natural_scene_break(next_para, chapter_only)


def loop_ready(text, end_para, next_para=None, chapter_only=False):
    """粗胚闭环启发式：有冲突、有释放/反转，并落在章节/场景/强钩候选处。"""
    return (
        boundary_candidate(end_para, next_para, chapter_only)
        and has_conflict(text)
        and has_payoff_or_reversal(text)
    )


def chunk_text(paras, target=None, hi=None, lo=None, chapter_aware=False):
    """连续性优先粗切：默认不锚字数，target/hi/lo 为旧参数兼容与报告参考。

    不再因为超过 max 或低于 min 硬切/硬并，也不再等到 target 才允许切。
    只有当前窗口出现「冲突→释放/反转→章节/场景/强钩候选」，才落一个粗胚分块；
    否则继续并入后文，交给精修阶段按 P0→P6 重切。

    chapter_aware=True（--by-chapter）：只在章界/强钩处落粗胚，忽略章内场景分隔，
    避免系统流满屏 `【…】` 系统行被当幕界而过度切碎。
    """
    episodes = []
    buf = []

    def flush():
        nonlocal buf
        if buf:
            episodes.append("\n".join(buf))
            buf = []

    for i, para in enumerate(paras):
        buf.append(para)
        text = "\n".join(buf)
        next_para = paras[i + 1] if i + 1 < len(paras) else None
        if loop_ready(text, para, next_para, chapter_only=chapter_aware):
            flush()
    flush()
    return episodes


def split_by_chapter(paras, target=None, hi=None, lo=None):
    """按「第X章」边界 + 强钩候选切粗胚：

    - 章是候选场，不等于集；章节/场景/强钩候选若形成「冲突→释放/反转」才落集；
    - target 只作报告参考，不参与默认切点决策；
    - 未形成闭环时继续并入下一章/场景。
    无章节标题时退回强钩候选切分。
    """
    if any(CHAPTER_RE.match(p) for p in paras):
        return chunk_text(paras, target, hi, lo, chapter_aware=True)
    return chunk_text(paras, target, hi, lo)


def split_per_chapter(paras, min_chars=100):
    """每章独立成一集（最贴戏剧节拍）；过短章节（疑似误判的标题行）并入上一集。

    无「第X章」标题时返回 None（由调用方退回强钩候选切分）。
    """
    chapters, cur = [], []
    for p in paras:
        if CHAPTER_RE.match(p) and cur:
            chapters.append(cur)
            cur = [p]
        else:
            cur.append(p)
    if cur:
        chapters.append(cur)
    if len(chapters) <= 1:
        return None
    episodes = []
    for ch in chapters:
        text = "\n".join(ch)
        body_len = sum(len(p) for p in ch)
        if episodes and body_len < min_chars:
            episodes[-1] = episodes[-1] + "\n" + text
        else:
            episodes.append(text)
    return episodes


def chapter_heading_count(paras):
    return sum(1 for p in paras if CHAPTER_RE.match(p or ""))


def should_auto_chapter_aware(episodes, paras):
    """Default split guard: retry chapter-aware mode when strong-hook splitting shatters a chaptered novel.

    System/xianxia sources often contain short lines and bracketed panels; the old default could
    treat those as scene boundaries and create thousands of 30-300 char "episodes". If the source
    clearly has chapter headings and the first pass is mostly tiny fragments, chapter-aware split is
    the safer scaffold. Explicit --by-chapter/--per-chapter bypasses this guard.
    """
    if not episodes:
        return False
    chapters = chapter_heading_count(paras)
    if chapters < 3:
        return False
    lengths = [len((ep or "").replace("\n", "")) for ep in episodes]
    tiny_ratio = sum(1 for n in lengths if n < 300) / len(lengths)
    over_split = len(episodes) > max(chapters * 2, DEFAULT_FIRST_SPLIT_LIMIT * 4)
    very_tiny = min(lengths or [0]) < 80 and tiny_ratio >= 0.35
    return over_split and very_tiny


def length_hint(chars):
    """字数只作复核提示，不参与切点决策。"""
    if chars < 650:
        return "偏短，复核闭环完整"
    if chars > 1100:
        return "偏长，复核中段钩子密度"
    return ""


PLACEHOLDERS = {
    "分镜剧本.md": "# {title}_第{n}集_分镜剧本\n\n> 待精修：参考 references/formats.md「分镜剧本」格式逐镜头填写。\n",
    "故事板.md": "# {title}_第{n}集_故事板\n\n> 待精修：参考 references/formats.md「故事板 Clip 表」格式，供 AI 视频生成（具体生视频后端在 n2d-video 阶段由 router/probe 决定；平台档案见 references/platforms.md）。\n",
    "素材清单.md": "# {title}_第{n}集_素材清单\n\n> 待精修：参考 references/formats.md「素材清单」格式，供 AI 图片生成（中文为主+英文备用；平台档案见 references/platforms.md）。\n",
    "voiceover.txt": "# {title}_第{n}集_配音文案\n# 待精修：按镜头顺序填写旁白/台词，标注角色与情绪。\n",
    "bgm.txt": "# {title}_第{n}集_BGM与音效\n# 待精修：填写整体情绪、BGM风格、关键音效点。\n",
    "封面.md": "# {title}_第{n}集_封面/首图\n\n> 待精修：一张高点击率封面 prompt（中文+英文），含本集最大爽点/钩子。\n",
    "字幕_中文.srt": "1\n00:00:00,000 --> 00:00:03,000\n（待精修：依据 voiceover.txt 台词 + 故事板.md 镜头时长生成带时间码的中文字幕）\n",
}


def write_if_absent(path, content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def write_source_snapshot(root, title, source_text):
    """Keep a canonical txt copy under 小说/ so source_check can baseline it."""
    novel_dir = os.path.join(root, "小说")
    os.makedirs(novel_dir, exist_ok=True)
    path = os.path.join(novel_dir, f"{title}.txt")
    if not os.path.exists(path) or open(path, encoding="utf-8", errors="replace").read() != source_text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(source_text.rstrip() + "\n")
    return path


def relpath(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def sha256_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def summarize_text(text, limit=72):
    compact = re.sub(r"\s+", " ", (text or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "…"


SOURCE_UNIT_SIGNAL_BITS = {
    "chapter_heading": 1,
    "scene_or_time_break": 2,
    "suspense_punctuation": 4,
    "conflict_hint": 8,
    "payoff_or_reversal_hint": 16,
}
COMPACT_SOURCE_UNITS_ENCODING = "normalized_source_reference_v1"


def source_unit_signals(text):
    """Return advisory signals for one normalized source paragraph."""
    text = str(text or "")
    signals = []
    if CHAPTER_RE.match(text):
        signals.append("chapter_heading")
    if SCENE_BREAK_RE.match(text):
        signals.append("scene_or_time_break")
    if text.rstrip().endswith(("？", "！", "…", "——", "?", "!")):
        signals.append("suspense_punctuation")
    # Lexical matches are metadata for human/optimizer inspection only. They
    # never hard-exclude a candidate boundary.
    if has_conflict(text):
        signals.append("conflict_hint")
    if has_payoff_or_reversal(text):
        signals.append("payoff_or_reversal_hint")
    return signals


def build_source_units(paras):
    """Build the legacy v2 full-unit objects (rollback/on-demand compatibility)."""
    units = []
    cursor = 0
    for index, para in enumerate(paras, 1):
        text = str(para or "")
        start = cursor
        end = start + len(text)
        signals = source_unit_signals(text)
        units.append({
            "source_unit_id": f"U{index:06d}",
            "index": index,
            "normalized_char_span": [start, end],
            "chars": len(text),
            "sha256": sha256_text(text),
            "preview": summarize_text(text, 96),
            "signals": signals,
        })
        cursor = end + 1  # normalized units are joined by one newline
    return units


def build_compact_source_units(paras):
    """Build a source-referenced v3 unit axis without embedding paragraph text.

    The canonical source snapshot plus normalization contract reconstructs all
    v2 fields on demand. Only sparse signal rows remain in the plan, preventing
    per-paragraph dict/SHA/preview duplication for 100k-unit novels.
    """
    digest = hashlib.sha256()
    normalized_chars = 0
    signal_index = []
    for index, para in enumerate(paras, 1):
        text = str(para or "")
        encoded = text.encode("utf-8")
        if index > 1:
            digest.update(b"\n")
            normalized_chars += 1
        digest.update(encoded)
        normalized_chars += len(text)
        signals = source_unit_signals(text)
        if signals:
            mask = sum(SOURCE_UNIT_SIGNAL_BITS[name] for name in signals)
            signal_index.append([index, mask])
    return {
        "encoding": COMPACT_SOURCE_UNITS_ENCODING,
        "count": len(paras),
        "id_format": "U%06d",
        "normalization": "nonempty stripped paragraphs joined by one newline",
        "normalized_char_count": normalized_chars,
        "normalized_text_sha256": digest.hexdigest(),
        "derived_fields": [
            "source_unit_id", "index", "normalized_char_span", "chars", "sha256", "preview"
        ],
        "signal_bits": SOURCE_UNIT_SIGNAL_BITS,
        "signal_index": signal_index,
        "signal_count": len(signal_index),
    }


def compact_source_units_from_legacy(source_units, paras):
    """Validate a verbose v2 source axis and losslessly compact its signals.

    Migration deliberately preserves the v2 signal decisions instead of
    recomputing them with today's genre lexicon. Every source-derived field is
    checked first, so a stale/mismatched source snapshot fails closed.
    """
    if not isinstance(source_units, list):
        raise ValueError("旧 split_plan source_units 不是 verbose v2 列表")
    paras = list(paras or [])
    if len(source_units) != len(paras):
        raise ValueError("旧 source_units 数量与规范化源段落数不一致")
    digest = hashlib.sha256()
    normalized_chars = 0
    signal_index = []
    cursor = 0
    for index, (unit, para) in enumerate(zip(source_units, paras), 1):
        if not isinstance(unit, dict):
            raise ValueError(f"旧 source_units 第 {index} 项不是对象")
        text = str(para or "")
        start, end = cursor, cursor + len(text)
        expected = {
            "source_unit_id": f"U{index:06d}",
            "index": index,
            "normalized_char_span": [start, end],
            "chars": len(text),
            "sha256": sha256_text(text),
            "preview": summarize_text(text, 96),
        }
        for key, value in expected.items():
            if unit.get(key) != value:
                raise ValueError(f"旧 source_units[{index}] 的 {key} 与规范化源不一致")
        signals = list(unit.get("signals") or [])
        unknown = [name for name in signals if name not in SOURCE_UNIT_SIGNAL_BITS]
        if unknown:
            raise ValueError(f"旧 source_units[{index}] 含未知 signals: {unknown}")
        if len(signals) != len(set(signals)):
            raise ValueError(f"旧 source_units[{index}] signals 重复")
        if signals:
            mask = sum(SOURCE_UNIT_SIGNAL_BITS[name] for name in signals)
            signal_index.append([index, mask])
        encoded = text.encode("utf-8")
        if index > 1:
            digest.update(b"\n")
            normalized_chars += 1
        digest.update(encoded)
        normalized_chars += len(text)
        cursor = end + 1
    return {
        "encoding": COMPACT_SOURCE_UNITS_ENCODING,
        "count": len(paras),
        "id_format": "U%06d",
        "normalization": "nonempty stripped paragraphs joined by one newline",
        "normalized_char_count": normalized_chars,
        "normalized_text_sha256": digest.hexdigest(),
        "derived_fields": [
            "source_unit_id", "index", "normalized_char_span", "chars", "sha256", "preview"
        ],
        "signal_bits": SOURCE_UNIT_SIGNAL_BITS,
        "signal_index": signal_index,
        "signal_count": len(signal_index),
    }


def source_unit_count(plan):
    """Count source units in either verbose v2 or compact v3 plans."""
    units = plan.get("source_units") if isinstance(plan, dict) else plan
    if isinstance(units, list):
        return len(units)
    if isinstance(units, dict):
        return int(units.get("count") or 0)
    return 0


def source_signal_count(plan):
    units = plan.get("source_units") if isinstance(plan, dict) else plan
    if isinstance(units, list):
        return sum(1 for unit in units if isinstance(unit, dict) and unit.get("signals"))
    if isinstance(units, dict):
        return int(units.get("signal_count") or len(units.get("signal_index") or []))
    return 0


def iter_source_units(plan, source_paras=None):
    """Yield legacy-shaped unit dicts from v2 or v3 storage.

    Compact plans require normalized source paragraphs. Integrity is checked
    against the plan hash before any derived unit is yielded.
    """
    units = plan.get("source_units") if isinstance(plan, dict) and "source_units" in plan else plan
    if isinstance(units, list):
        yield from units
        return
    if not isinstance(units, dict) or units.get("encoding") != COMPACT_SOURCE_UNITS_ENCODING:
        raise ValueError("不支持的 source_units 存储格式")
    paras = list(source_paras or [])
    if len(paras) != int(units.get("count") or 0):
        raise ValueError("source_units count 与规范化源段落数不一致")
    expected_sha = str(units.get("normalized_text_sha256") or "")
    actual_sha = sha256_text("\n".join(str(p or "") for p in paras))
    if expected_sha and actual_sha != expected_sha:
        raise ValueError("source_units 规范化源哈希不一致，拒绝派生")
    signal_bits = units.get("signal_bits") or SOURCE_UNIT_SIGNAL_BITS
    signal_by_index = {
        int(row[0]): int(row[1])
        for row in (units.get("signal_index") or [])
        if isinstance(row, list) and len(row) == 2
    }
    ordered_signals = sorted(signal_bits.items(), key=lambda item: int(item[1]))
    cursor = 0
    for index, para in enumerate(paras, 1):
        text = str(para or "")
        start, end = cursor, cursor + len(text)
        mask = signal_by_index.get(index, 0)
        signals = [name for name, bit in ordered_signals if mask & int(bit)]
        yield {
            "source_unit_id": f"U{index:06d}",
            "index": index,
            "normalized_char_span": [start, end],
            "chars": len(text),
            "sha256": sha256_text(text),
            "preview": summarize_text(text, 96),
            "signals": signals,
        }
        cursor = end + 1


def iter_arc_anchors(plan, source_paras=None):
    """Yield the legacy combined source/development anchor view for v2/v3."""
    units = plan.get("source_units") if isinstance(plan, dict) else None
    if isinstance(units, dict):
        for unit in iter_source_units(plan, source_paras):
            if unit.get("signals"):
                yield {
                    "anchor_type": "source_signal",
                    "source_unit_id": unit["source_unit_id"],
                    "signals": unit["signals"],
                    "preview": unit["preview"],
                }
    for anchor in (plan.get("arc_anchors") or []):
        yield anchor


def episode_unit_spans(episodes, paras, start_cursor=0, unit_indices=None):
    """Map machine episode chunks back to the full normalized source-unit axis.

    unit_indices：集内容来自非连续源单元时（主线剪枝整章剔除），给出每个入集段落在
    **完整源单元轴**上的 0 基索引；span 的 start/end 引用真实源单元，剔除处形成 gap
    并标 `contains_spine_cut_gaps`，源单元轴本身不缺号。
    """
    spans = []
    if unit_indices is not None:
        cursor = 0
        for i, episode in enumerate(episodes, 1):
            parts = str(episode or "").split("\n") if episode else []
            count = len(parts)
            idxs = list(unit_indices[cursor:cursor + count])
            exact = len(idxs) == count and [paras[j] for j in idxs] == parts
            span = {
                "episode": i,
                "start_source_unit_id": f"U{idxs[0] + 1:06d}" if idxs else None,
                "end_source_unit_id": f"U{idxs[-1] + 1:06d}" if idxs else None,
                "start_index": idxs[0] + 1 if idxs else 0,
                "end_index": idxs[-1] + 1 if idxs else 0,
                "mapping_exact": exact,
            }
            if idxs and idxs != list(range(idxs[0], idxs[0] + count)):
                span["contains_spine_cut_gaps"] = True
                span["unit_count"] = count
            spans.append(span)
            cursor += count
        return spans
    cursor = max(0, int(start_cursor or 0))
    for i, episode in enumerate(episodes, 1):
        parts = str(episode or "").split("\n") if episode else []
        count = len(parts)
        # Normal path is exact because all splitters join normalized paragraphs.
        # If a future splitter rewrites text, fall back to monotonic unit counts
        # rather than silently inventing a source hash.
        exact = paras[cursor:cursor + count] == parts
        start = cursor + 1 if count else cursor
        end = cursor + count
        spans.append({
            "episode": i,
            "start_source_unit_id": f"U{start:06d}" if count else None,
            "end_source_unit_id": f"U{end:06d}" if count else None,
            "start_index": start,
            "end_index": end,
            "mapping_exact": exact,
        })
        cursor += count
    return spans


def apply_spine_chapter_cuts(paras, offset, cut_plan, apply=True):
    """按 story_spine 整章剔除计划处理选定窗口段落（P4）。

    apply=True（主线剪枝 enforce 档）：被剔章节的段落不进集内容；
    apply=False（advisory 预览）：不剔任何段落，只产记账行让编剧看到会剔什么。
    无论哪档，源单元轴（split_plan.source_units）都保持完整——剔除只发生在集内容层，
    每一章剔了多少单元/多少字、归哪条 cut 线程，全部逐章记账，绝不静默删。
    """
    cut_map = {int(k): v for k, v in (cut_plan.get("cut_chapters") or {}).items()}
    kept_paras, kept_indices = [], []
    removed = {}
    current = None
    for i, p in enumerate(paras):
        ch = chapter_number_from_heading(p)
        if ch is not None:
            current = ch
        abs_index = int(offset) + i
        if current in cut_map:
            row = removed.setdefault(current, {
                "chapter": current,
                "cut_threads": sorted(set(cut_map[current])),
                "units": 0,
                "chars": 0,
                "first_source_unit_id": f"U{abs_index + 1:06d}",
            })
            row["units"] += 1
            row["chars"] += len(p)
            row["last_source_unit_id"] = f"U{abs_index + 1:06d}"
            if apply:
                continue
        kept_paras.append(p)
        kept_indices.append(abs_index)
    rows = [removed[ch] for ch in sorted(removed)]
    outside = sorted(set(cut_map) - set(removed))
    return {
        "applied": bool(apply and rows),
        "cut_chapters_outside_window": outside,
        "mode": cut_plan.get("mode"),
        "mode_source": cut_plan.get("mode_source"),
        "source": cut_plan.get("source"),
        "removed_chapters": rows,
        "removed_unit_total": sum(r["units"] for r in rows),
        "removed_char_total": sum(r["chars"] for r in rows),
        "conflicts_skipped": list(cut_plan.get("conflicts") or []),
        "unparsed_spans": list(cut_plan.get("unparsed_spans") or []),
        "kept_paras": kept_paras,
        "kept_indices": kept_indices,
    }


def boundary_quality(paras, position):
    """Score a boundary between units ``position`` and ``position+1``.

    Structural and sentence-shape evidence drive the score. Lexicon hits are
    deliberately absent so a genre dictionary can never hard-veto a cut.
    """
    if position <= 0 or position >= len(paras):
        return {"score": 0.0, "features": []}
    left, right = str(paras[position - 1] or ""), str(paras[position] or "")
    score, features = 0.0, []
    if CHAPTER_RE.match(right):
        score += 3.0
        features.append("chapter_transition")
    elif SCENE_BREAK_RE.match(right):
        score += 2.0
        features.append("scene_or_time_transition")
    if left.rstrip().endswith(("。", "？", "！", "…", "——", ".", "?", "!")):
        score += 1.0
        features.append("complete_sentence")
    if left.rstrip().endswith(("？", "！", "…", "——", "?", "!")):
        score += 0.75
        features.append("suspense_shape")
    if re.match(r"^\s*(翌日|次日|三日后|与此同时|另一边|话说|回忆|从前)", right):
        score -= 0.75
        features.append("slow_opening_shape")
    return {"score": round(score, 3), "features": features}


def build_boundary_candidates(paras, episode_spans, radius=3):
    """Return local Top-K alternatives around every machine split boundary."""
    out = []
    for left, right in zip(episode_spans, episode_spans[1:]):
        current = int(left.get("end_index") or 0)
        options = []
        for position in range(max(1, current - radius), min(len(paras) - 1, current + radius) + 1):
            quality = boundary_quality(paras, position)
            options.append({
                "after_source_unit_id": f"U{position:06d}",
                "before_source_unit_id": f"U{position + 1:06d}",
                "position": position,
                "score": quality["score"],
                "features": quality["features"],
                "distance_from_machine_cut": position - current,
            })
        options.sort(key=lambda row: (-row["score"], abs(row["distance_from_machine_cut"]), row["position"]))
        out.append({
            "boundary_id": f"E{int(left['episode']):04d}-E{int(right['episode']):04d}",
            "machine_position": current,
            "top_candidates": options[:3],
            "status": "advisory_needs_semantic_review",
        })
    return out


def optimize_boundary_paths(
    paras, episode_count, top_k=3, beam_width=24, unit_offset=0,
    preferred_positions=None,
):
    """Advisory full-book beam search over boundary positions.

    This does not rewrite ``raw.txt``. It offers globally coherent alternatives
    while keeping segment size a soft balance term and structural boundary
    quality as evidence. Human semantic review remains authoritative.
    """
    n = len(paras)
    k = max(1, min(int(episode_count or 1), n or 1))
    if n == 0:
        return []
    mean = n / k
    preferred = {int(v) for v in (preferred_positions or [])}
    states = [(0.0, 0, [])]  # score, last position, completed boundary positions
    for step in range(1, k + 1):
        expanded = []
        for score, last, boundaries in states:
            remaining_segments = k - step
            if step == k:
                positions = [n] if last < n else []
            else:
                expected = round(step * n / k)
                radius = max(3, int(mean * 0.75 + 0.5))
                low = max(last + 1, step, expected - radius)
                high = min(n - remaining_segments, expected + radius)
                positions = range(low, high + 1)
            for pos in positions:
                segment_units = pos - last
                balance_penalty = abs(segment_units - mean) / max(mean, 1.0) * 0.65
                structural = boundary_quality(paras, pos)["score"] if pos < n else 0.0
                if pos + int(unit_offset or 0) in preferred:
                    structural += 2.5
                expanded.append((score + structural - balance_penalty, pos, boundaries + [pos]))
        # deterministic dedupe + bounded beam
        best = {}
        for state in expanded:
            key = tuple(state[2])
            if key not in best or state[0] > best[key][0]:
                best[key] = state
        states = sorted(best.values(), key=lambda s: (-s[0], s[2]))[:beam_width]
        if not states:
            break
    paths = []
    for rank, (score, _last, positions) in enumerate(sorted(states, key=lambda s: (-s[0], s[2]))[:top_k], 1):
        paths.append({
            "rank": rank,
            "score": round(score, 3),
            "boundary_after_source_units": [f"U{p + unit_offset:06d}" for p in positions[:-1]],
            "segment_end_positions": [p + unit_offset for p in positions],
            "status": "advisory_needs_semantic_review",
        })
    return paths


def load_development_arc_contract(root):
    """Load confirmed season-arc intent and any explicit source-unit anchors."""
    path = Path(root) / "开发包" / "season_arc.json"
    if not path.exists():
        return {"status": "missing", "sha256": "", "anchors": [], "preferred_positions": []}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as exc:
        return {"status": "invalid", "sha256": "", "anchors": [], "preferred_positions": [], "error": str(exc)}
    anchors, preferred = [], []
    rows = []
    if isinstance(data.get("front_arc"), list):
        rows.extend(row for row in data["front_arc"] if isinstance(row, dict))
    if isinstance(data.get("arc_anchors"), list):
        rows.extend(row for row in data["arc_anchors"] if isinstance(row, dict))
    for row in rows:
        meaningful = {
            key: value for key, value in row.items()
            if str(value or "").strip() and "待补" not in str(value)
        }
        if meaningful:
            anchors.append({"anchor_type": "development_arc", **meaningful})
        source_unit = (
            row.get("boundary_after_source_unit_id")
            or row.get("source_unit_id")
            or ((row.get("source_unit_span") or {}).get("end_source_unit_id")
                if isinstance(row.get("source_unit_span"), dict) else None)
        )
        match = re.search(r"\d+", str(source_unit or ""))
        if match:
            preferred.append(int(match.group()))
    for scene in data.get("signature_scenes") or []:
        if str(scene or "").strip() and "待补" not in str(scene):
            anchors.append({"anchor_type": "signature_scene", "description": str(scene).strip()})
    return {
        "status": str(data.get("status") or "draft"),
        "path": relpath(path, root),
        "sha256": sha256_text(raw),
        "series_promise": data.get("series_promise") if "待补" not in str(data.get("series_promise") or "") else "",
        "anchors": anchors,
        "preferred_positions": sorted(set(preferred)),
    }


def render_machine_split_review(plan):
    partial = plan.get("scope") == "partial"
    title_scope = "首批粗切索引" if partial else "全篇粗切索引"
    status_scope = "机器首批粗切索引" if partial else "机器全篇粗切索引"
    if partial:
        scope_note = (
            f"- 范围：已落地前 {plan['target_episode_count']} 集；"
            f"全本候选断点约估 {plan.get('estimated_total_episode_count', plan['target_episode_count'])} 集。"
        )
        principle_note = "- 原则：先用首批（默认 10 集）验证节拍、压缩率、画风和角色卡；满意后再用 `--limit N` 续切或 `--all` 补全。"
    else:
        scope_note = f"- 粗切范围：{plan['target_episode_count']} 集"
        principle_note = "- 原则：已有全篇统筹索引，后续仍按小批精修；不得把 raw 当最终口播稿。"
    lines = [
        f"# {plan['title']} — {title_scope}",
        "",
        f"- 生成时间：{plan['generated_at']}",
        scope_note,
        f"- 生成方式：{plan['split_mode']}",
        f"- 状态：{status_scope}；不是导演定稿。阶段1 精修仍需按 5-10 集窗口复核边界、冷开场、核心看点和集尾钩。",
        principle_note,
        "",
        "## 分集索引",
        "",
        "| 集 | 字数 | 开头摘要 | 结尾摘要 | raw |",
        "|---|---:|---|---|---|",
    ]
    visible_eps = [ep for ep in plan.get("episodes", []) if ep.get("materialized")]
    for ep in visible_eps:
        lines.append(
            "| {episode_label} | {source_chars} | {opening_preview} | {ending_preview} | `{raw_rel}` |".format(**ep)
        )
    pruning = plan.get("spine_pruning") or {}
    if pruning.get("removed_chapters"):
        lines.append("")
        lines.append("## 主线剪枝整章剔除" + ("" if pruning.get("applied") else "（预览·未生效）"))
        lines.append("")
        state = "已剔除（不进集内容）" if pruning.get("applied") else \
            "预览记账：advisory 档/显式逃生口未剔除；设 `主线剪枝: 突出主线/激进精简` 并重跑 split 生效"
        lines.append(f"- 状态：{state}；依据 `{pruning.get('source')}`（{pruning.get('mode_source')}）。")
        lines.append("")
        lines.append("| 章 | cut 线程 | 源单元 | 单元数 | 字数 |")
        lines.append("|---|---|---|---:|---:|")
        for row in pruning["removed_chapters"]:
            lines.append(
                "| 第{chapter}章 | {threads} | {first}–{last} | {units} | {chars} |".format(
                    chapter=row.get("chapter"), threads="/".join(row.get("cut_threads") or []),
                    first=row.get("first_source_unit_id"), last=row.get("last_source_unit_id"),
                    units=row.get("units"), chars=row.get("chars"),
                )
            )
        for c in pruning.get("conflicts_skipped") or []:
            lines.append(
                f"- 冲突保留：第{c.get('chapter')}章同时被 {c.get('cut_threads')} 与 "
                f"{c.get('protected_by')} 锚定，未剔除。"
            )
        if pruning.get("unparsed_spans"):
            lines.append(f"- 不可机读的 cut 锚（未剔）：{pruning['unparsed_spans']}")
    lines.append("")
    lines.append("## 精修提醒")
    lines.append("")
    lines.append("- `raw.txt` 是取材脚手架，不是最终口播稿。")
    lines.append("- 每次精修先看前后 5-10 集窗口，再决定保留、并入、前后挪段或重写断点。")
    lines.append("- 已进入出图/出视频的集不要被粗切续跑覆盖；如边界改变，先做受影响范围返工计划。")
    lines.append(
        f"- 全书结构事实保存在 `split_plan.json` v{plan.get('schema_version')}: "
        f"source_units={source_unit_count(plan)} / "
        f"source_signals={source_signal_count(plan)} / "
        f"boundary_candidates={len(plan.get('boundary_candidates') or [])} / "
        f"beam_paths={len((plan.get('boundary_optimization') or {}).get('top_paths') or [])}。"
    )
    approved_windows = plan.get("human_approved_windows") or []
    if approved_windows:
        lines.extend(["", "## 已实施的人工批准窗口", ""])
        for window in approved_windows:
            lines.append(
                "- 第{start_episode}–{end_episode}集：{start_source_unit_id}–{end_source_unit_id}；"
                "批准人 `{reviewer}`；实施收据 `{receipt}`。".format(**window)
            )
    return "\n".join(lines) + "\n"


def render_human_split_review_scaffold(plan):
    return (
        f"# {plan['title']} — 人工拆集复核\n\n"
        "> 本文件只写人工/导演决策；续切不会覆盖。机器事实与候选见 "
        "`split_plan.json` 和 `_拆集机器索引.md`。\n\n"
        "## 当前复核窗口\n\n"
        "- 范围：待填写（建议每次 5-10 集）\n"
        "- 复核人：\n"
        "- 日期：\n\n"
        "## 边界决策\n\n"
        "| boundary_id | blocker/candidate | 决策 | 左右 source unit 映射 | 备注 |\n"
        "|---|---|---|---|---|\n"
    )


def write_split_plan(
    root, title, source_snapshot, episodes, n_make, *, split_mode, genre_note,
    partial, start_info=None, source_paras=None, selected_source_paras=None,
    source_unit_offset=0, legacy_plan_v2=False, unit_indices=None, spine_pruning=None,
):
    """Write a full-series rough split index without overwriting reviewed episode content."""
    script_dir = os.path.join(root, "脚本")
    os.makedirs(script_dir, exist_ok=True)
    source_paras = list(source_paras or [])
    selected_source_paras = list(selected_source_paras if selected_source_paras is not None else source_paras)
    if legacy_plan_v2:
        source_units = build_source_units(source_paras)
        source_arc_anchors = [
            {"anchor_type": "source_signal", "source_unit_id": unit["source_unit_id"],
             "signals": unit["signals"], "preview": unit["preview"]}
            for unit in source_units if unit.get("signals")
        ]
    else:
        source_units = build_compact_source_units(source_paras)
        source_arc_anchors = []
    unit_spans = episode_unit_spans(
        episodes, source_paras, start_cursor=source_unit_offset, unit_indices=unit_indices)
    development_arc = load_development_arc_contract(root)
    plan_episodes = []
    for i, machine_episode in enumerate(episodes, 1):
        raw_path = os.path.join(script_dir, f"第{i}集", "raw.txt")
        materialized = i <= n_make and os.path.exists(raw_path)
        if materialized:
            try:
                raw_text = open(raw_path, encoding="utf-8").read()
            except OSError:
                raw_text = machine_episode
        else:
            raw_text = machine_episode
        raw_text = raw_text.rstrip()
        span = unit_spans[i - 1] if i - 1 < len(unit_spans) else {}
        plan_episodes.append({
            "episode": i,
            "episode_label": f"第{i}集",
            "source_chars": len(raw_text.replace("\n", "")),
            "opening_preview": summarize_text(raw_text[:400]),
            "ending_preview": summarize_text(raw_text[-400:]),
            "raw_rel": relpath(raw_path, root),
            "raw_sha256": sha256_text(raw_text),
            "machine_source_sha256": sha256_text(machine_episode.rstrip()),
            "materialized": materialized,
            "source_unit_span": span,
            "boundary_status": "machine_scaffold_needs_window_review",
            "adaptation_policy": "raw 是取材脚手架；阶段1 voiceover 必须按漫剧节奏重写，保留冲突、选择、反转、集尾钩，不逐字照搬。",
        })
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    plan = {
        "schema_version": 2 if legacy_plan_v2 else 3,
        "kind": "n2d_machine_split_plan",
        "generated_at": now,
        "project_root": os.path.abspath(root),
        "title": title,
        "source_text": relpath(source_snapshot, root),
        "source_text_sha256": sha256_text(open(source_snapshot, encoding="utf-8").read().rstrip()),
        "split_mode": split_mode,
        "genre_basis": genre_note,
        "scope": "partial" if partial else "full",
        "target_episode_count": n_make,
        "estimated_total_episode_count": len(episodes),
        "start_chapter": start_info,
        "basis": [
            "全本源文本",
            "split_novel.py 机器粗切候选",
            "n2d-script references/拆集法.md：每集冲突→看点→钩子闭环，章不等于集",
            "n2d-script references/追更骨架.md：先做首批窗口复核，再按确认后的边界策略续切或全篇补全",
        ],
        "global_boundary_decision": (
            "机器粗切索引已落地；后续阶段1必须按 5-10 集窗口做导演复核，"
            "确认冷开场、核心看点、兑现/反转和集尾钩后再写 voiceover；"
            "长篇项目先验证首批压缩率与边界策略，再续切或全篇补全。"
        ),
        "source_unit_model": "normalized_paragraph_v1",
        "source_unit_scope": "full_normalized_source_after_frontmatter",
        "source_units_storage": "verbose_v2" if legacy_plan_v2 else COMPACT_SOURCE_UNITS_ENCODING,
        "source_units_compatibility": (
            "v2 原对象直接可读"
            if legacy_plan_v2 else
            "用 split_novel.iter_source_units(plan, normalized_source_paras) 按需派生 v2 字段；"
            "重跑时加 --legacy-plan-v2 可回退 verbose v2"
        ),
        "selected_window": {
            "start_source_unit_index": int(source_unit_offset) + 1 if selected_source_paras else None,
            "source_unit_count": len(selected_source_paras),
            "optimization_scope": "selected_window" if source_unit_offset else "full_source",
        },
        "source_units": source_units,
        "source_signal_anchor_count": source_signal_count({"source_units": source_units}),
        "arc_anchors": source_arc_anchors + list(development_arc.get("anchors") or []),
        "development_arc_contract": {
            key: value for key, value in development_arc.items() if key not in {"anchors", "preferred_positions"}
        },
        "boundary_candidates": build_boundary_candidates(source_paras, unit_spans),
        "boundary_optimization": {
            "method": "full_book_beam_search_v1",
            "enforcement": "advisory_needs_semantic_review",
            "dictionary_hard_veto": False,
            "development_arc_constraints_applied": bool(
                development_arc.get("status") == "confirmed" and development_arc.get("preferred_positions")
            ),
            "development_arc_unmapped_note": (
                "confirmed season_arc 已纳入意图/哈希审计，但未提供 source_unit 映射，故不伪造边界约束。"
                if development_arc.get("status") == "confirmed" and not development_arc.get("preferred_positions") else ""
            ),
            # 整章剔除后集内容来自非连续源单元，统一 unit_offset 无法表达 beam 路径的
            # 真实单元号——诚实跳过而不产出错位建议（boundary_candidates 仍基于真实 span 有效）。
            "spine_pruning_note": (
                "已应用主线剪枝整章剔除，beam 建议按剔除后轴无法用统一 offset 表示，跳过。"
                if unit_indices is not None else ""
            ),
            "top_paths": [] if unit_indices is not None else optimize_boundary_paths(
                selected_source_paras,
                len(episodes),
                top_k=3,
                unit_offset=int(source_unit_offset or 0),
                preferred_positions=development_arc.get("preferred_positions"),
            ),
        },
        "episodes": plan_episodes,
    }
    if spine_pruning is not None:
        plan["spine_pruning"] = {
            key: value for key, value in spine_pruning.items()
            if key not in {"kept_paras", "kept_indices"}
        }
        plan["spine_pruning"]["axis_note"] = (
            "source_units 轴保持完整（含被剔章节的单元号）；剔除只作用于集内容，"
            "episode.source_unit_span 在剔除处形成 gap 并标 contains_spine_cut_gaps。"
        )
    json_path = os.path.join(script_dir, "split_plan.json")
    md_path = os.path.join(script_dir, "_拆集机器索引.md")
    human_path = os.path.join(script_dir, "_拆集复核.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_machine_split_review(plan))
    # Human decisions are append/edit-owned and must survive --limit continuation.
    if not os.path.exists(human_path):
        with open(human_path, "w", encoding="utf-8") as f:
            f.write(render_human_split_review_scaffold(plan))
    return plan


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path, payload):
    """Durably replace one machine artifact without a shared temp filename."""
    path = os.fspath(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    try:
        with open(temp, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def _gzip_backup(source_path, backup_path):
    """Create/reuse a deterministic compressed backup and verify round-trip."""
    source_sha = sha256_file(source_path)
    source_size = os.path.getsize(source_path)
    backup_path = os.fspath(backup_path)
    if not os.path.exists(backup_path):
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        temp = f"{backup_path}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
        try:
            with open(source_path, "rb") as src, open(temp, "wb") as raw_out:
                with gzip.GzipFile(
                    filename="", mode="wb", fileobj=raw_out, compresslevel=9, mtime=0
                ) as gz_out:
                    for chunk in iter(lambda: src.read(1024 * 1024), b""):
                        gz_out.write(chunk)
                raw_out.flush()
                os.fsync(raw_out.fileno())
            os.replace(temp, backup_path)
        finally:
            if os.path.exists(temp):
                os.remove(temp)
    restored_digest = hashlib.sha256()
    restored_size = 0
    with gzip.open(backup_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            restored_digest.update(chunk)
            restored_size += len(chunk)
    if restored_digest.hexdigest() != source_sha or restored_size != source_size:
        raise ValueError("split_plan v2 压缩备份回读校验失败")
    return {
        "path": backup_path,
        "compression": "gzip",
        "bytes": os.path.getsize(backup_path),
        "sha256": sha256_file(backup_path),
        "uncompressed_bytes": source_size,
        "uncompressed_sha256": source_sha,
    }


def _restore_gzip_backup(backup_path, target_path):
    temp = f"{target_path}.restore.{os.getpid()}.{uuid.uuid4().hex}"
    try:
        with gzip.open(backup_path, "rb") as src, open(temp, "wb") as out:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, target_path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def _protected_split_artifact_snapshot(root):
    """Fingerprint user-owned split artifacts; migration may not touch them."""
    root_path = Path(root)
    candidates = [root_path / "_进度.md", root_path / "脚本" / "_拆集复核.md"]
    candidates.extend(sorted((root_path / "脚本").glob("第*集/raw.txt")))
    snapshot = {}
    for path in candidates:
        if path.is_file():
            stat = path.stat()
            snapshot[relpath(path, root)] = {
                "bytes": stat.st_size,
                "sha256": sha256_file(path),
                "mtime_ns": stat.st_mtime_ns,
            }
    return snapshot


def _canonical_sha(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(payload)


def compact_existing_split_plan(root, source_path, source_text, *, keep_frontmatter=False):
    """Migrate a verbose v2 plan to compact v3 without recomputing story cuts.

    Only `split_plan.json`, its machine Markdown view, a compressed v2 backup,
    and a machine-readable receipt may change. Raw, human boundary review, and
    progress are fingerprinted before/after and any mismatch rolls the plan
    back to the verified gzip backup.
    """
    root = os.path.abspath(os.fspath(root))
    plan_path = os.path.join(root, "脚本", "split_plan.json")
    machine_index_path = os.path.join(root, "脚本", "_拆集机器索引.md")
    if not os.path.isfile(plan_path):
        raise FileNotFoundError(f"找不到既有计划: {plan_path}")
    protected_before = _protected_split_artifact_snapshot(root)
    old_machine_index = (
        Path(machine_index_path).read_bytes() if os.path.isfile(machine_index_path) else None
    )
    before_size = os.path.getsize(plan_path)
    before_sha = sha256_file(plan_path)
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    if plan.get("kind") != "n2d_machine_split_plan" or int(plan.get("schema_version") or 0) != 2:
        raise ValueError("--compact-existing-plan 只接受 n2d_machine_split_plan schema v2")
    # write_split_plan hashes `open(..., encoding=...).read()`, whose text-mode
    # universal-newline handling maps CRLF/CR to LF. `read_text()` intentionally
    # decodes raw bytes, so mirror that historical hash contract here.
    source_for_plan_hash = str(source_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if plan.get("source_text_sha256") != sha256_text(source_for_plan_hash.rstrip()):
        raise ValueError("传入源文本与旧 split_plan.source_text_sha256 不一致")

    paras = normalize_paragraphs(source_text)
    if not keep_frontmatter:
        paras = strip_frontmatter(paras)
    legacy_units = plan.get("source_units")
    compact_units = compact_source_units_from_legacy(legacy_units, paras)
    legacy_signal_count = int(compact_units["signal_count"])

    # v2 duplicated every source signal as an arc anchor. Validate that mirror
    # before dropping it; non-source/development anchors remain byte-semantically
    # represented in the migrated plan.
    development_anchors = []
    legacy_anchor_count = 0
    for anchor in plan.get("arc_anchors") or []:
        if not isinstance(anchor, dict):
            raise ValueError("旧 arc_anchors 含非对象项")
        if anchor.get("anchor_type") != "source_signal":
            development_anchors.append(anchor)
            continue
        legacy_anchor_count += 1
        match = re.fullmatch(r"U(\d+)", str(anchor.get("source_unit_id") or ""))
        if not match:
            raise ValueError("旧 source_signal anchor 缺有效 source_unit_id")
        index = int(match.group(1))
        if index < 1 or index > len(legacy_units):
            raise ValueError("旧 source_signal anchor 越出 source_units 范围")
        unit = legacy_units[index - 1]
        if (
            anchor.get("signals") != unit.get("signals")
            or anchor.get("preview") != unit.get("preview")
        ):
            raise ValueError("旧 source_signal anchor 与对应 source_unit 不一致")
    if legacy_anchor_count != legacy_signal_count:
        raise ValueError("旧 source_signal anchors 未完整镜像 source_units signals")

    semantic_fields = (
        "kind", "title", "source_text", "source_text_sha256", "split_mode", "scope",
        "target_episode_count", "estimated_total_episode_count", "start_chapter",
        "selected_window", "development_arc_contract", "boundary_candidates",
        "boundary_optimization", "episodes",
    )
    semantic_before = {key: plan.get(key) for key in semantic_fields}
    semantic_before["development_arc_anchors"] = development_anchors
    semantic_before_sha = _canonical_sha(semantic_before)

    receipt_dir = os.path.join(root, "生产数据", "迁移收据")
    backup_name = f"split_plan.v2.{before_sha[:12]}.json.gz"
    backup_path = os.path.join(receipt_dir, backup_name)
    backup = _gzip_backup(plan_path, backup_path)
    migrated_at = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt_path = os.path.join(receipt_dir, f"split_plan_storage_migration_{stamp}.json")

    plan["schema_version"] = 3
    plan["source_units_storage"] = COMPACT_SOURCE_UNITS_ENCODING
    plan["source_units_compatibility"] = (
        "用 split_novel.iter_source_units(plan, normalized_source_paras) 按需派生 v2 字段；"
        "重跑时加 --legacy-plan-v2 可回退 verbose v2"
    )
    plan["source_units"] = compact_units
    plan["source_signal_anchor_count"] = legacy_signal_count
    plan["arc_anchors"] = development_anchors
    plan["storage_migration"] = {
        "from_schema_version": 2,
        "migrated_at": migrated_at,
        "method": "validated_in_place_storage_compaction_v1",
        "source_plan_sha256": before_sha,
        "backup": relpath(backup_path, root),
        "receipt": relpath(receipt_path, root),
    }

    # Exact legacy view must still be derivable before replacing anything.
    hydrated_count = 0
    for hydrated, legacy in zip(iter_source_units(plan, paras), legacy_units):
        if hydrated != legacy:
            raise ValueError("compact v3 rehydrate 与 legacy v2 source_unit 不一致")
        hydrated_count += 1
    if hydrated_count != len(legacy_units):
        raise ValueError("compact v3 rehydrate 数量不完整")
    semantic_after = {key: plan.get(key) for key in semantic_fields}
    semantic_after["development_arc_anchors"] = plan.get("arc_anchors") or []
    semantic_after_sha = _canonical_sha(semantic_after)
    if semantic_after_sha != semantic_before_sha:
        raise ValueError("存储迁移意外改变拆集/边界生产语义")

    plan_bytes = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n\n").encode("utf-8")
    after_size = len(plan_bytes)
    after_sha = hashlib.sha256(plan_bytes).hexdigest()
    if after_size >= before_size:
        raise ValueError("compact v3 未取得体积收益，拒绝替换旧计划")
    machine_index_bytes = render_machine_split_review(plan).encode("utf-8")
    plan_replaced = False
    try:
        atomic_write_bytes(plan_path, plan_bytes)
        plan_replaced = True
        atomic_write_bytes(machine_index_path, machine_index_bytes)
        protected_after = _protected_split_artifact_snapshot(root)
        if protected_after != protected_before:
            raise ValueError("迁移触碰了 raw、_拆集复核.md 或 _进度.md")
        receipt = {
            "schema_version": 1,
            "kind": "n2d_split_plan_storage_migration_receipt",
            "status": "pass",
            "migrated_at": migrated_at,
            "project_root": root,
            "source_text": relpath(source_path, root),
            "migration": {
                "from_schema_version": 2,
                "to_schema_version": 3,
                "method": "validated_in_place_storage_compaction_v1",
                "source_units_encoding": COMPACT_SOURCE_UNITS_ENCODING,
            },
            "before": {
                "path": relpath(plan_path, root),
                "bytes": before_size,
                "sha256": before_sha,
                "source_unit_count": len(legacy_units),
                "source_signal_anchor_count": legacy_anchor_count,
                "estimated_total_episode_count": plan.get("estimated_total_episode_count"),
                "production_semantic_sha256": semantic_before_sha,
            },
            "after": {
                "path": relpath(plan_path, root),
                "bytes": after_size,
                "sha256": after_sha,
                "source_unit_count": source_unit_count(plan),
                "source_signal_anchor_count": source_signal_count(plan),
                "estimated_total_episode_count": plan.get("estimated_total_episode_count"),
                "production_semantic_sha256": semantic_after_sha,
            },
            "reduction": {
                "bytes_saved": before_size - after_size,
                "fraction": round(1.0 - after_size / before_size, 6),
                "factor": round(before_size / after_size, 4),
            },
            "backup": {
                **{key: value for key, value in backup.items() if key != "path"},
                "path": relpath(backup["path"], root),
            },
            "checks": {
                "source_hash_matches_v2_plan": True,
                "all_v2_source_units_validated": True,
                "rehydrated_v2_units_equal": True,
                "rehydrated_source_unit_count": hydrated_count,
                "source_signal_anchors_equal": legacy_anchor_count == legacy_signal_count,
                "estimated_episode_count_unchanged": True,
                "production_semantics_unchanged": semantic_after_sha == semantic_before_sha,
                "protected_artifacts_unchanged": True,
            },
            "protected_artifacts": protected_after,
            "allowed_mutations": [
                "脚本/split_plan.json",
                "脚本/_拆集机器索引.md",
                relpath(backup_path, root),
                relpath(receipt_path, root),
            ],
            "rollback": {
                "backup": relpath(backup_path, root),
                "expected_restored_sha256": before_sha,
            },
        }
        receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        atomic_write_bytes(receipt_path, receipt_bytes)
    except Exception:
        if plan_replaced:
            _restore_gzip_backup(backup_path, plan_path)
        if old_machine_index is None:
            if os.path.exists(machine_index_path):
                os.remove(machine_index_path)
        else:
            atomic_write_bytes(machine_index_path, old_machine_index)
        raise
    return receipt, receipt_path


def progress_extra_sections(path):
    """Preserve human-authored status sections after the progress table."""
    if not os.path.exists(path):
        return ""
    lines = open(path, encoding="utf-8").read().splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            return "\n".join(lines[idx:]).rstrip() + "\n"
    return ""


def existing_episode_numbers(root):
    nums = set()
    progress = os.path.join(root, "_进度.md")
    if os.path.exists(progress):
        for line in open(progress, encoding="utf-8"):
            m = re.match(r"\|\s*第(\d+)集\s*\|", line)
            if m:
                nums.add(int(m.group(1)))
    script_dir = os.path.join(root, "脚本")
    if os.path.isdir(script_dir):
        for name in os.listdir(script_dir):
            m = re.match(r"第(\d+)集$", name)
            if m and os.path.exists(os.path.join(script_dir, name, "raw.txt")):
                nums.add(int(m.group(1)))
    return nums


def global_style_scaffold(title, root, recommendation=None):
    # 私有选择优先：_设置.md/全局默认里任何「非裸默认」的明确选择都尊重，不被推荐覆盖。
    # 只有「没人选过」（解析值 == 裸默认 且项目无 source）时，才用题材感知推荐填这个预选。
    resolved = get_setting(root, "基础视觉风格", DEFAULTS["基础视觉风格"])
    explicit = bool(project_setting_source(root, "基础视觉风格")) or resolved != DEFAULTS["基础视觉风格"]
    if explicit:
        base_style, origin = resolved, "来自 _设置.md/全局默认"
    elif recommendation and recommendation.get("recommended"):
        base_style, origin = recommendation["recommended"], "题材感知推荐（预选·可改）"
    else:
        base_style, origin = resolved, "全局默认"
    style_note = f"{base_style}（{origin}；可选 {style_options_text()}）"
    rec_block = ""
    if recommendation:
        rec_block = (
            "## 风格推荐依据\n"
            f"{format_style_recommendation_markdown(recommendation)}\n\n"
        )
    return (
        f"# {title} — 全局画风与世界观\n\n"
        "## 视频模型路由\n自动按镜头路由（首跑不选择具体生视频后端；n2d-video 阶段按 `video_model_routes.json` + CLI/API 探测决定 primary/fallback）\n\n"
        "## 生视频后端决策\n延后到 n2d-video 出视频前；若用户明确固定后端或账号/交付只能单后端，再写 `_设置.md` 的 `视频模型路由/生视频模型/生视频渠道`。\n\n"
        f"## 基础视觉风格\n{style_note}\n\n"
        f"{rec_block}"
        "## 画风\n高质量AI漫剧风格，统一色调，高细节；具体提示词随「基础视觉风格」派生。\n\n"
        "## 基础视觉风格契约（style_contract 源头）\n"
        f"{format_style_contract_markdown(base_style)}\n\n"
        "## 世界观\n（待精修）\n\n"
        "## 统一负面词\n（画风漂移、多余文字水印、多指错手、脸/妆造漂移；其余禁忌按「基础视觉风格」派生，例如未选Q版才禁低幼Q版，写实电影感才禁插画化）\n"
    )


def build_style_recommendation(paras, title, genre_setting):
    """题材感知风格推荐：detect_genre(正文) + 书名/题材自由文本 → 一个预选默认。

    纯产物用于 global_style_scaffold；检测器缺失时退化到通用默认（不阻断拆集）。
    """
    body = "\n".join(paras)
    genres = []
    if detect_genre is not None:
        try:
            gd = detect_genre(body)
            genres = [r["genre"] for r in gd.get("by_genre", []) if r.get("hits", 0) >= GENRE_MIN_HITS]
        except Exception:
            genres = []
    genre_text = " ".join([title or "", genre_setting or "", body[:20000]])
    return recommend_style(genres, genre_text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("novel")
    ap.add_argument("--out", default=None,
                    help="作品根（直接包含 脚本/ 出图/ 出视频/ + 全局文件）。缺省：小说在 .../小说/<X> 下→取其父；否则落到最近仓库根的 创作区/制漫剧/<剧名>/（找不到才回退小说同级并告警）")
    ap.add_argument("--target", type=int, default=None, help="高级参数：粗胚字数参考（仅用于报告/人工复核，不参与默认切点决策）")
    ap.add_argument("--min", type=int, default=None, help="旧参数兼容：不再作为硬性下限")
    ap.add_argument("--max", type=int, default=None, help="旧参数兼容：不再作为硬性上限")
    ap.add_argument("--name", default=None, help="标题（用于各素材文件头），默认取小说文件名")
    ap.add_argument("--by-chapter", action="store_true",
                    help="优先按「第X章」+ 强钩候选切集（更贴戏剧节拍）；无章节标题时自动退回强钩候选切")
    ap.add_argument("--per-chapter", action="store_true",
                    help="每章独立成一集（最贴戏剧节拍，一章=一集；长章保持整章，精修时按上/下集再拆）；无章节标题时自动退回强钩候选切")
    ap.add_argument("--start-chapter", default=None,
                    help="从第N章开始粗切（可写 48 / 第48章 / 第四十八章）。仅裁本次 raw 脚手架；中段开工仍需先补 设定库/中段开工前情资产包.md")
    ap.add_argument("--keep-frontmatter", action="store_true",
                    help="保留开头的简介/标签/看点等元数据（默认自动剥离）")
    ap.add_argument("--no-spine-cuts", action="store_true",
                    help="逃生口：即使 story_spine 已 confirmed 且主线剪枝为 enforce 档，也不做整章剔除（仍会预览记账）")
    ap.add_argument("--limit", type=int, default=None,
                    help=f"首批粗切：只落地前 N 集（仍按全本估总集数）；缺省={DEFAULT_FIRST_SPLIT_LIMIT}。续切=重跑加大 --limit（已存在集与进度勾选保留）")
    ap.add_argument("--all", action="store_true",
                    help="显式全篇粗切；只在边界策略稳定、准备批量推进时使用。")
    ap.add_argument("--legacy-plan-v2", action="store_true",
                    help="回退输出 verbose split_plan v2（逐段 SHA/preview 全内嵌，体积和加载内存显著更大）；默认写紧凑 v3")
    ap.add_argument("--compact-existing-plan", action="store_true",
                    help="仅把既有 split_plan v2 原位压紧为 v3；保留拆集/边界语义，备份并落迁移收据，不重写 raw/_进度/人工复核")
    args = ap.parse_args()

    if args.all and args.limit is not None:
        sys.exit("--all 与 --limit 只能二选一。")
    if args.limit is not None and args.limit < 1:
        sys.exit("--limit 必须是正整数；全篇粗切请用 --all。")
    if args.compact_existing_plan and (
        args.all or args.limit is not None or args.by_chapter or args.per_chapter
        or args.start_chapter or args.legacy_plan_v2
    ):
        sys.exit("--compact-existing-plan 是纯存储迁移，不能与拆集/回退参数组合。")

    if not os.path.exists(args.novel):
        sys.exit(f"找不到文件: {args.novel}")

    title = args.name or os.path.splitext(os.path.basename(args.novel))[0]
    # 新布局：作品根直接铺各阶段子文件夹（脚本/ 出图/ 出视频/）+ 全局文件。
    # 若小说位于 .../小说/<X>.docx，作品根 = 小说目录的父级；否则 = 小说同级目录。
    if args.out:
        root = args.out
    else:
        novel_dir = os.path.dirname(os.path.abspath(args.novel))
        if os.path.basename(novel_dir) == "小说":
            root = os.path.dirname(novel_dir)
        else:
            # n2d 产物应落 创作区/制漫剧/<剧名>/：向上找最近的归属锚，
            # 避免把作品根误建在输入文件同级。区分两类锚，别把 创作区/ 当仓库根再拼一层：
            #   - d 含 创作区/制漫剧 或 skills → d 是仓库根 → root = d/创作区/制漫剧/title
            #   - d 直接含 制漫剧（即 d 本身就是 创作区/ 目录）→ root = d/制漫剧/title
            d, root = novel_dir, None
            while True:
                if (
                    os.path.isdir(os.path.join(d, "创作区", "制漫剧"))
                    or os.path.isdir(os.path.join(d, "skills"))
                ):
                    root = os.path.join(d, "创作区", "制漫剧", title)
                    break
                if os.path.isdir(os.path.join(d, "制漫剧")):
                    root = os.path.join(d, "制漫剧", title)
                    break
                parent = os.path.dirname(d)
                if parent == d:
                    break
                d = parent
            if root is None:
                root = novel_dir
                print(f"[warn] 未找到含『创作区/制漫剧/』的仓库根，作品根回退到小说同级：{root}"
                      f"（建议用 --out 指定 创作区/制漫剧/<剧名>/）", file=sys.stderr)
    text = read_text(args.novel)
    if args.compact_existing_plan:
        try:
            receipt, receipt_path = compact_existing_split_plan(
                root, args.novel, text, keep_frontmatter=args.keep_frontmatter
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            sys.exit(f"split_plan 存储迁移失败：{exc}")
        print(f"作品根: {root}")
        print(
            "split_plan v2→v3 存储迁移完成："
            f"{receipt['before']['bytes']} → {receipt['after']['bytes']} bytes；"
            "raw / _拆集复核.md / _进度.md 哈希与 mtime 均未变化。"
        )
        print(f"迁移收据: {receipt_path}")
        print(f"v2 压缩备份: {receipt['backup']['path']}")
        return
    meta_path = os.path.join(root, "_meta.json")
    if not os.path.exists(meta_path):
        os.makedirs(root, exist_ok=True)
        project_id = f"n2d_{uuid.uuid4().hex[:16]}"
        # 作品卡片契约：立项当刻 series_bible 尚未产出，synopsis 先占位空串、
        # cover 先 null；bible 产出后由 work_card_meta.backfill_synopsis / 封面步骤
        # 的 backfill_cover 用确定性方式回填，不覆盖用户已填内容。
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1, "kind": "n2d_project", "project_id": project_id,
                "line": "n2d", "title": title, "created_at": _dt.date.today().isoformat(),
                "synopsis": "", "cover": None,
            }, f, ensure_ascii=False, indent=2)
            f.write("\n")
        catalog_path = os.path.join(root, "生产数据", "artifact_catalog.json")
        os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1, "kind": "artifact_catalog", "status": "bootstrap",
                "generated_at": _dt.date.today().isoformat(),
                "project": {"project_id": project_id, "line": "n2d", "title": title, "root_rel": "."},
                "summary": {"artifact_count": 0, "total_bytes": 0, "disposable_bytes": 0, "invalid_count": 0},
                "event_sources": [], "view_sources": [], "artifacts": [], "duplicates": [],
            }, f, ensure_ascii=False, indent=2)
            f.write("\n")
    source_snapshot = write_source_snapshot(root, title, text)
    dev_pack = None
    if scaffold_development_pack is not None:
        try:
            dev_pack = scaffold_development_pack(Path(root), title=title)
        except Exception as exc:
            print(f"[warn] P-1 开发包 scaffold 失败：{exc}", file=sys.stderr)
    # 作品卡片字段：补齐旧项目缺失的 synopsis/cover（write_if_absent），并在 bible
    # 已有一句话卖点时确定性回填 synopsis（占位/空串才写，不覆盖用户内容）。
    try:
        ensure_work_card_fields(root)
        backfill_work_card_synopsis(root)
    except Exception as exc:
        print(f"[warn] 作品卡片 synopsis 回填跳过：{exc}", file=sys.stderr)
    paras = normalize_paragraphs(text)
    if not paras:
        sys.exit("未读到正文内容。")

    dropped = 0
    if not args.keep_frontmatter:
        before = len(paras)
        paras = strip_frontmatter(paras)
        dropped = before - len(paras)

    # split_plan v2/v3 both keep the full normalized source-unit axis even when
    # this invocation starts from a middle chapter. The selected window is
    # mapped by an offset; no earlier source units disappear from the contract.
    full_source_paras = list(paras)

    start_info = None
    if args.start_chapter:
        try:
            paras, start_info = trim_before_chapter(paras, args.start_chapter)
        except ValueError as exc:
            sys.exit(str(exc))

    # ── P4 主线剪枝整章剔除：confirmed story_spine 的 cut 线程章节锚 → 集内容剔除 ──
    # enforce 档（主线剪枝=突出主线/激进精简）真剔；advisory（缺省/保守）只预览记账不剔；
    # --no-spine-cuts 显式逃生口。源单元轴始终保持完整，剔除逐章记账进 split_plan。
    window_offset = int((start_info or {}).get("skipped_paras") or 0)
    spine_pruning = None
    unit_indices = None
    if spine_cut_chapter_plan is not None:
        try:
            cut_plan = spine_cut_chapter_plan(Path(root))
        except Exception as exc:
            cut_plan = None
            print(f"[warn] 主线剪枝计划解析失败（跳过整章剔除）：{exc}", file=sys.stderr)
        if cut_plan and cut_plan.get("status") == "ok" and cut_plan.get("cut_chapters"):
            enforce = cut_plan.get("mode") == "enforce" and not args.no_spine_cuts
            spine_pruning = apply_spine_chapter_cuts(paras, window_offset, cut_plan, apply=enforce)
            if args.no_spine_cuts:
                spine_pruning["opted_out_by_flag"] = True
            if spine_pruning["applied"]:
                if max(existing_episode_numbers(root) or {0}) > 0:
                    print("[warn] 本项目已有粗切集目录；整章剔除会移动后续边界，"
                          "已进入出图/出视频的集需先做受影响范围返工计划。", file=sys.stderr)
                paras = spine_pruning["kept_paras"]
                unit_indices = spine_pruning["kept_indices"]
                if not paras:
                    sys.exit("主线剪枝整章剔除后没有剩余正文——检查 story_spine 的 cut 章节锚是否误覆盖全书。")

    # 题材感知边界词典：读 _设置.md `题材`（弱选择点；未设则 base ∪ 古装动作=历史默认）→
    # 重建模块级强钩/冲突/爽点正则，治女频情感/悬疑/都市粗切退化成无闭环。
    global STRONG_EPISODE_END_RE, CONFLICT_RE, PAYOFF_OR_REVERSAL_RE
    genre = get_setting(root, "题材", "")
    buckets = boundary_buckets(genre)
    STRONG_EPISODE_END_RE, CONFLICT_RE, PAYOFF_OR_REVERSAL_RE = build_boundary_res(genre)

    auto_chapter_retry = False
    if args.per_chapter:
        episodes = split_per_chapter(paras) or chunk_text(paras, args.target, args.max, args.min)
    elif args.by_chapter:
        episodes = split_by_chapter(paras, args.target, args.max, args.min)
    else:
        episodes = chunk_text(paras, args.target, args.max, args.min)
        if should_auto_chapter_aware(episodes, paras):
            retried = split_by_chapter(paras, args.target, args.max, args.min)
            if retried and len(retried) < len(episodes):
                episodes = retried
                auto_chapter_retry = True

    settings = os.path.join(root, "设定库")
    os.makedirs(os.path.join(settings, "characters"), exist_ok=True)
    os.makedirs(os.path.join(settings, "locations"), exist_ok=True)
    character_library = os.path.join(root, "角色库")
    os.makedirs(character_library, exist_ok=True)
    os.makedirs(os.path.join(root, "脚本"), exist_ok=True)
    source_analysis = write_analysis(root, title, "\n".join(paras), episodes)

    style_rec = build_style_recommendation(paras, title, genre)
    write_if_absent(
        os.path.join(settings, "global_style.md"),
        global_style_scaffold(title, root, recommendation=style_rec),
    )
    write_if_absent(
        os.path.join(settings, "characters", "_角色总表.md"),
        render_character_roster(title, source_analysis),
    )
    write_if_absent(
        os.path.join(settings, "locations", "_场景总表.md"),
        f"# {title} — 场景卡总表\n\n> 全篇首次出现即建卡，后续镜头保持一致。格式见 references/formats.md。\n",
    )
    write_if_absent(
        os.path.join(character_library, "README.md"),
        "# 角色库\n\n"
        "本目录只存本作品的角色生产资产包；世界观、角色圣经、角色卡和场景语义仍在 `设定库/`。\n\n"
        "- `core_full`：主角、核心长线、或计划出场 10 集及以上。\n"
        "- `recurring_standard`：多集复现配角。\n"
        "- `named_minimal`：具名短线角色。\n"
        "- `restricted_partial`：只露局部或群像剪影。\n\n"
        "跨作品复用时显式导出自包含 asset pack 到 `创作区/制漫剧/_资产库/`，其它作品不得直接依赖本目录。\n",
    )
    write_if_absent(
        os.path.join(settings, "characters", "_生命周期.md"),
        f"# {title} — 角色形象生命周期时间线（跨集·全局产物）\n\n"
        "> 跨集造型/年龄/服装/形态里程碑的**全局产物**（Gap2）。第2步建卡后跑：\n"
        "> `python3 skills/n2d/n2d-script/scripts/lifecycle_scan.py <作品根> --write` 自动扫候选→人确认。\n"
        "> 用途：提前规划定妆库何时派生新『形态变体』；作 n2d-identity 跨集漂移的预期变化基线。\n"
        "> 格式见 references/formats.md §1.1。\n",
    )

    total_est = len(episodes)
    # 首批默认只落地 10 集，避免超长书一开局铺出上千个目录；显式 --all 才全篇粗切。
    requested_limit = None if args.all else (args.limit or DEFAULT_FIRST_SPLIT_LIMIT)
    requested_n_make = total_est if requested_limit is None else max(1, min(requested_limit, total_est))
    # 不收缩已存在的粗切目录/进度行；默认 10 只影响新项目或未超过 10 集的项目。
    existing_max = max(existing_episode_numbers(root) or {0})
    n_make = min(max(requested_n_make, existing_max), total_est)

    lengths = []
    for i, ep in enumerate(episodes[:n_make], 1):
        ep_dir = os.path.join(root, "脚本", f"第{i}集")
        os.makedirs(ep_dir, exist_ok=True)
        write_if_absent(os.path.join(ep_dir, "raw.txt"), ep)
        for fname, tmpl in PLACEHOLDERS.items():
            write_if_absent(os.path.join(ep_dir, fname), tmpl.format(title=title, n=i))
        lengths.append(len(ep.replace("\n", "")))

    # 进度表：部分先切 / 已存在进度时合并续写——保留已勾选的旧行，只追加新粗切的集。
    prog_path = os.path.join(root, "_进度.md")
    partial = n_make < total_est
    existing_rows = {}
    extra_sections = progress_extra_sections(prog_path)
    if os.path.exists(prog_path):
        for line in open(prog_path, encoding="utf-8"):
            m = re.match(r"\|\s*第(\d+)集\s*\|", line)
            if m:
                existing_rows[int(m.group(1))] = line.rstrip("\n")
    subtitle_lang = get_setting(root, "字幕语言", "中文")
    wants_en = "英" in subtitle_lang or "en" in subtitle_lang.lower()
    fresh = {}
    for i, ln in enumerate(lengths, 1):
        cells = [f"第{i}集", str(ln), "✅"] + ["⬜"] * (len(PROGRESS_COLUMNS) - 3)
        if "字幕英" in PROGRESS_COLUMNS and not wants_en:
            cells[PROGRESS_COLUMNS.index("字幕英")] = "—"
        # 奇观连续性默认 —（na·不挡 flow）：拆集时未知本集有无奇观镜，image_prompt prework
        # 生成序列总账后回写 ✅（有奇观且覆盖）或保持 —（无奇观）。
        if "奇观连续性" in PROGRESS_COLUMNS:
            cells[PROGRESS_COLUMNS.index("奇观连续性")] = "—"
        fresh[i] = "| " + " | ".join(cells) + " |"
    rows = {**fresh, **existing_rows}  # 旧勾选优先，保留人工进度
    made = max(rows) if rows else n_make
    start_header = ""
    if start_info:
        start_header = f"（从第{start_info['matched']}章起）"
    est_scope = "本窗口" if start_info else "全本"
    if partial:
        status_line = (
            f"已粗切 **{made}** 集{start_header}"
            f"（{est_scope}约估 {total_est} 集；首批/部分先切，精修验证后重跑 split 加大 --limit 续切，或用 --all 补全）。\n"
        )
    else:
        status_line = (
            f"全篇粗切索引已落地 **{made}** 集{start_header}；"
            "阶段1 仍按 5-10 集窗口做导演边界复核后再写 voiceover。\n"
        )
    header = (f"# {title} — 生产进度\n", status_line)
    prog_lines = [*header,
        "| " + " | ".join(PROGRESS_COLUMNS) + " |",
        "|" + "|".join("---" for _ in PROGRESS_COLUMNS) + "|"]
    prog_lines += [rows[i] for i in sorted(rows)]
    if extra_sections:
        prog_lines += ["", extra_sections.rstrip()]
    with open(prog_path, "w", encoding="utf-8") as f:
        f.write("\n".join(prog_lines) + "\n")

    if args.per_chapter:
        mode = "每章一集"
    elif args.by_chapter:
        mode = "按章节+强钩候选"
    elif auto_chapter_retry:
        mode = "按章节+强钩候选（默认强钩过碎自动回退）"
    else:
        mode = "按强钩候选"
    genre_note = f"{genre}→{'/'.join(buckets)}" if genre else f"未设题材→{'/'.join(buckets)}(默认)"
    write_split_plan(
        root,
        title,
        source_snapshot,
        episodes,
        n_make,
        split_mode=mode,
        genre_note=genre_note,
        partial=partial,
        start_info=start_info,
        source_paras=full_source_paras,
        selected_source_paras=paras,
        source_unit_offset=window_offset,
        legacy_plan_v2=args.legacy_plan_v2,
        unit_indices=unit_indices,
        spine_pruning=spine_pruning,
    )

    print(f"作品根: {root}")
    if dev_pack:
        print("P-1 开发包：已创建/刷新 开发包/（默认 draft；阶段1 写词前需补齐并置 confirmed）")
    target_note = f"；字数参考 {args.target}（仅报告，不参与切点）" if args.target else "；未设置字数参考"
    print(f"切分方式：{mode}；边界词典题材：{genre_note}；剥离开头元数据 {dropped} 段。")
    if spine_pruning and spine_pruning.get("removed_chapters"):
        cut_desc = "、".join(
            f"第{r['chapter']}章({'/'.join(r['cut_threads'])}·{r['chars']}字)"
            for r in spine_pruning["removed_chapters"]
        )
        if spine_pruning.get("applied"):
            print(f"主线剪枝：已整章剔除 {cut_desc}；逐章账见 split_plan.json spine_pruning / _拆集机器索引.md。")
        else:
            reason = "--no-spine-cuts 逃生口" if spine_pruning.get("opted_out_by_flag") else "主线剪枝=advisory 档"
            print(f"主线剪枝（预览·未剔除·{reason}）：{cut_desc}；设 `主线剪枝: 突出主线` 并重跑 split 生效。")
        for c in spine_pruning.get("conflicts_skipped") or []:
            print(f"主线剪枝冲突保留：第{c.get('chapter')}章被 {c.get('cut_threads')} 与 {c.get('protected_by')} 同时锚定，未剔除。")
    if start_info:
        approx_note = "" if start_info["exact"] else f"（未找到精确章号，使用之后最近的第{start_info['matched']}章）"
        print(f"起始章节：请求第{start_info['requested']}章，实际从第{start_info['matched']}章开始，跳过 {start_info['skipped_paras']} 段{approx_note}。")
    if partial:
        est_scope = "本窗口" if start_info else "全本"
        default_note = "默认首批" if args.limit is None and not args.all else "部分先切"
        print(f"{default_note}：已落地前 {n_make} 集（{est_scope}按候选断点约估 {total_est} 集）。"
              f"字数范围 {min(lengths)}~{max(lengths)}{target_note}；无硬上下限")
        print(f"下一步：精修第1集验证节拍/画风/角色卡；满意后重跑 split 加大 --limit 续切，或用 --all 补全（旧集与进度勾选保留）。")
    else:
        scope_note = "本窗口共" if start_info else "共"
        print(f"{scope_note} {n_make} 集，字数范围 {min(lengths)}~{max(lengths)}{target_note}；无硬上下限")
        print("目录骨架已生成。下一步：精修每集素材。")
    hints = [f"第{i}集 {length_hint(n)}" for i, n in enumerate(lengths, 1) if length_hint(n)]
    if hints:
        tail = "；…" if len(hints) > 8 else ""
        print("字数提示（仅复核，不参与切点）： " + "；".join(hints[:8]) + tail)


if __name__ == "__main__":
    main()
